"""
课堂行为快速采集与训练脚本
==========================

功能：
1. 从你的视频中自动提取姿态序列
2. 自动数据增强（旋转、缩放、时序抖动）
3. 快速训练LSTM模型（30-60分钟）
4. 自动评估和导出模型

使用方法：
1. 录制视频并分类放入 data/ 目录
2. 运行: python quick_collect_and_train.py
3. 等待训练完成，模型自动保存

所需数据量（最小可行）：
- 每类 10-20 个短视频（3-5秒 each）
- 总共 50-100 个视频即可训练！
"""

import os
import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from ultralytics import YOLO
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import json
from tqdm import tqdm
from datetime import datetime
import random
import argparse

# ==================== 配置 ====================
BEHAVIOR_NAMES = {
    0: "专注学习",
    1: "查看手机",
    2: "与他人交谈",
    3: "睡觉",
    4: "离开座位"
}

# 最小数据量要求
MIN_SAMPLES_PER_CLASS = 5  # 每类至少5个样本

# ==================== LSTM模型（和yolo.py保持一致）====================
class BehaviorLSTM(nn.Module):
    def __init__(self, input_size=34, hidden_size=128, num_layers=2, 
                 num_classes=5, dropout=0.3):
        super(BehaviorLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )
    
    def forward(self, x):
        lstm_out, (hidden, cell) = self.lstm(x)
        hidden_forward = hidden[-2]
        hidden_backward = hidden[-1]
        hidden_concat = torch.cat((hidden_forward, hidden_backward), dim=1)
        return self.classifier(hidden_concat)


# ==================== 数据增强 ====================
class PoseAugmentation:
    """姿态序列数据增强"""
    
    @staticmethod
    def temporal_jitter(sequence, max_shift=2):
        """时序抖动：随机前后移动几帧"""
        shift = random.randint(-max_shift, max_shift)
        if shift > 0:
            return np.pad(sequence[:-shift], ((shift, 0), (0, 0)), mode='edge')
        elif shift < 0:
            return np.pad(sequence[-shift:], ((0, -shift), (0, 0)), mode='edge')
        return sequence
    
    @staticmethod
    def spatial_noise(sequence, noise_level=0.01):
        """空间噪声：添加小幅随机扰动"""
        noise = np.random.normal(0, noise_level, sequence.shape)
        return np.clip(sequence + noise, 0, 1)
    
    @staticmethod
    def random_scale(sequence, scale_range=(0.9, 1.1)):
        """随机缩放：模拟不同距离"""
        scale = random.uniform(*scale_range)
        # 以中心为基准缩放
        center = 0.5
        return (sequence - center) * scale + center
    
    @staticmethod
    def random_flip(sequence):
        """水平翻转：模拟左右对称"""
        if random.random() > 0.5:
            # 假设偶数索引是x坐标
            flipped = sequence.copy()
            for i in range(0, 34, 2):  # 每两个值中的第一个是x
                flipped[:, i] = 1 - flipped[:, i]
            return flipped
        return sequence
    
    @staticmethod
    def augment(sequence, num_augmentations=3):
        """应用多种增强"""
        augmented = [sequence]  # 原始数据
        
        for _ in range(num_augmentations):
            seq = sequence.copy()
            
            # 随机应用增强
            if random.random() > 0.3:
                seq = PoseAugmentation.temporal_jitter(seq)
            if random.random() > 0.3:
                seq = PoseAugmentation.spatial_noise(seq)
            if random.random() > 0.5:
                seq = PoseAugmentation.random_scale(seq)
            if random.random() > 0.5:
                seq = PoseAugmentation.random_flip(seq)
            
            augmented.append(seq)
        
        return augmented


# ==================== 数据集 ====================
class BehaviorDataset(Dataset):
    def __init__(self, sequences, labels, augment=False):
        self.sequences = []
        self.labels = []
        
        if augment:
            # 数据增强
            print("🔄 应用数据增强...")
            for seq, label in zip(sequences, labels):
                aug_seqs = PoseAugmentation.augment(seq, num_augmentations=3)
                for aug_seq in aug_seqs:
                    self.sequences.append(aug_seq)
                    self.labels.append(label)
        else:
            self.sequences = sequences
            self.labels = labels
        
        self.sequences = torch.FloatTensor(self.sequences)
        self.labels = torch.LongTensor(self.labels)
        
        print(f"数据集大小: {len(self.sequences)} 个样本")
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]


# ==================== 视频处理 ====================
def extract_pose_from_video(video_path, pose_model, seq_length=16):
    """
    从视频提取姿态序列
    返回多个序列（滑动窗口）
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ 无法打开视频: {video_path}")
        return []
    
    all_keypoints = []
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 每3帧采样1帧（加速处理）
    sample_interval = max(1, total_frames // 90)  # 保证最多30个采样点
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % sample_interval == 0:
            results = pose_model(frame, verbose=False)
            
            if results[0].keypoints is not None and len(results[0].keypoints) > 0:
                # 取第一个人
                kp = results[0].keypoints.xy[0].cpu().numpy()
                h, w = frame.shape[:2]
                
                # 归一化
                kp_norm = kp.copy()
                kp_norm[:, 0] /= w
                kp_norm[:, 1] /= h
                
                all_keypoints.append(kp_norm.flatten())
        
        frame_count += 1
    
    cap.release()
    
    if len(all_keypoints) < seq_length:
        return []
    
    # 滑动窗口生成序列
    sequences = []
    stride = seq_length // 2
    
    for start in range(0, len(all_keypoints) - seq_length + 1, stride):
        seq = np.array(all_keypoints[start:start + seq_length])
        sequences.append(seq)
    
    return sequences


def prepare_data_from_videos(data_dir, pose_model, seq_length=16):
    """
    从视频目录准备数据
    目录结构:
    data/
    ├── 0_focused/     -> 标签0
    ├── 1_phone/       -> 标签1
    ├── 2_talking/     -> 标签2
    ├── 3_sleeping/    -> 标签3
    └── 4_away/        -> 标签4
    """
    print("\n" + "="*60)
    print("步骤1: 提取姿态序列")
    print("="*60)
    
    all_sequences = []
    all_labels = []
    
    for label_id, label_name in BEHAVIOR_NAMES.items():
        # 查找对应目录（支持多种命名）
        possible_dirs = [
            f"{label_id}_{label_name}",
            f"{label_id}_",
            str(label_id),
            label_name,
            label_name.lower().replace(" ", "_"),
        ]
        
        video_dir = None
        for d in possible_dirs:
            path = os.path.join(data_dir, d)
            if os.path.exists(path):
                video_dir = path
                break
        
        if video_dir is None:
            print(f"⚠️ 跳过类别 {label_id} ({label_name}): 找不到目录")
            continue
        
        print(f"\n📁 处理 {label_name} ({video_dir})")
        
        # 查找视频文件
        video_files = []
        for ext in ['*.mp4', '*.avi', '*.mov', '*.MP4', '*.AVI']:
            video_files.extend(list(Path(video_dir).glob(ext)))
        
        print(f"   找到 {len(video_files)} 个视频")
        
        if len(video_files) < MIN_SAMPLES_PER_CLASS:
            print(f"   ⚠️ 警告: 样本数不足 (需要至少{MIN_SAMPLES_PER_CLASS}个)")
        
        # 提取姿态
        for video_file in tqdm(video_files, desc=f"提取{label_name}"):
            sequences = extract_pose_from_video(str(video_file), pose_model, seq_length)
            
            for seq in sequences:
                all_sequences.append(seq)
                all_labels.append(label_id)
        
        print(f"   ✅ 提取了 {len([l for l in all_labels if l == label_id])} 个序列")
    
    if len(all_sequences) == 0:
        raise ValueError("没有提取到任何有效数据！")
    
    return np.array(all_sequences), np.array(all_labels)


# ==================== 训练器 ====================
class QuickTrainer:
    def __init__(self, model, device, lr=0.001):
        self.model = model.to(device)
        self.device = device
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='max', patience=5, factor=0.5
        )
    
    def train_epoch(self, train_loader):
        self.model.train()
        total_loss = 0
        all_preds = []
        all_labels = []
        
        for sequences, labels in train_loader:
            sequences = sequences.to(self.device)
            labels = labels.to(self.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(sequences)
            loss = self.criterion(outputs, labels)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            preds = torch.argmax(outputs, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
        
        avg_loss = total_loss / len(train_loader)
        accuracy = accuracy_score(all_labels, all_preds)
        return avg_loss, accuracy
    
    def validate(self, val_loader):
        self.model.eval()
        total_loss = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for sequences, labels in val_loader:
                sequences = sequences.to(self.device)
                labels = labels.to(self.device)
                
                outputs = self.model(sequences)
                loss = self.criterion(outputs, labels)
                
                total_loss += loss.item()
                preds = torch.argmax(outputs, dim=1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        avg_loss = total_loss / len(val_loader)
        accuracy = accuracy_score(all_labels, all_preds)
        return avg_loss, accuracy, all_labels, all_preds


# ==================== 主函数 ====================
def main():
    parser = argparse.ArgumentParser(description='快速采集与训练')
    parser.add_argument('--data_dir', type=str, default='./data',
                       help='视频数据目录')
    parser.add_argument('--output_dir', type=str, default='./quick_model',
                       help='模型输出目录')
    parser.add_argument('--epochs', type=int, default=50,
                       help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='批次大小')
    parser.add_argument('--seq_length', type=int, default=16,
                       help='序列长度')
    parser.add_argument('--device', type=str, default='auto',
                       help='设备 (auto/cuda/cpu)')
    args = parser.parse_args()
    
    # 确定设备
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    
    print("="*60)
    print("🚀 课堂行为快速采集与训练")
    print("="*60)
    print(f"设备: {device}")
    print(f"数据目录: {args.data_dir}")
    print(f"输出目录: {args.output_dir}")
    print()
    
    # 检查数据目录
    if not os.path.exists(args.data_dir):
        print("❌ 数据目录不存在!")
        print(f"请创建 {args.data_dir}/ 目录，并按以下结构放入视频:")
        print("""
data/
├── 0_focused/          # 专注学习视频
├── 1_phone/            # 看手机视频
├── 2_talking/          # 交谈视频
├── 3_sleeping/         # 睡觉视频
└── 4_away/             # 离开视频
        """)
        return
    
    # 加载YOLO模型
    print("加载YOLOv8-Pose...")
    pose_model = YOLO('yolov8n-pose.pt')
    
    # 提取数据
    try:
        sequences, labels = prepare_data_from_videos(
            args.data_dir, pose_model, args.seq_length
        )
    except ValueError as e:
        print(f"\n❌ {e}")
        return
    
    print("\n" + "="*60)
    print("步骤2: 准备训练")
    print("="*60)
    
    # 划分训练集和验证集
    X_train, X_val, y_train, y_val = train_test_split(
        sequences, labels, test_size=0.2, random_state=42, stratify=labels
    )
    
    print(f"训练集: {len(X_train)} 个样本")
    print(f"验证集: {len(X_val)} 个样本")
    
    # 数据增强
    print("\n应用数据增强...")
    train_dataset = BehaviorDataset(X_train, y_train, augment=True)
    val_dataset = BehaviorDataset(X_val, y_val, augment=False)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, 
                             shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size,
                           shuffle=False, num_workers=0)
    
    # 创建模型
    print("\n创建LSTM模型...")
    model = BehaviorLSTM(
        input_size=34,
        hidden_size=128,
        num_layers=2,
        num_classes=5,
        dropout=0.3
    )
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"模型参数量: {total_params:,}")
    
    # 训练
    print("\n" + "="*60)
    print("步骤3: 开始训练")
    print("="*60)
    
    trainer = QuickTrainer(model, device)
    os.makedirs(args.output_dir, exist_ok=True)
    
    best_acc = 0
    patience_counter = 0
    max_patience = 15
    
    for epoch in range(args.epochs):
        train_loss, train_acc = trainer.train_epoch(train_loader)
        val_loss, val_acc, y_true, y_pred = trainer.validate(val_loader)
        
        trainer.scheduler.step(val_acc)
        
        # 保存最佳模型
        if val_acc > best_acc:
            best_acc = val_acc
            patience_counter = 0
            torch.save(model.state_dict(), 
                      os.path.join(args.output_dir, 'behavior_lstm.pth'))
        else:
            patience_counter += 1
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch [{epoch+1:3d}/{args.epochs}] "
                  f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
                  f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")
        
        # 早停
        if patience_counter >= max_patience:
            print(f"\n⏹️  早停: {max_patience} 轮未提升")
            break
    
    # 最终评估
    print("\n" + "="*60)
    print("步骤4: 最终评估")
    print("="*60)
    
    model.load_state_dict(torch.load(os.path.join(args.output_dir, 'behavior_lstm.pth')))
    _, _, y_true, y_pred = trainer.validate(val_loader)
    
    print(f"\n最佳验证准确率: {best_acc:.4f}")
    print("\n分类报告:")
    print(classification_report(
        y_true, y_pred,
        target_names=[BEHAVIOR_NAMES[i] for i in range(5)]
    ))
    
    # 保存配置
    config = {
        'input_size': 34,
        'hidden_size': 128,
        'num_layers': 2,
        'num_classes': 5,
        'seq_length': args.seq_length,
        'best_acc': float(best_acc),
        'trained_at': datetime.now().isoformat()
    }
    with open(os.path.join(args.output_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n" + "="*60)
    print("✅ 训练完成!")
    print("="*60)
    print(f"模型已保存: {args.output_dir}/behavior_lstm.pth")
    print(f"\n使用方式:")
    print(f"  1. 复制模型: cp {args.output_dir}/behavior_lstm.pth ./behavior_lstm.pth")
    print(f"  2. 启动服务: uvicorn yolo:app --port 8000")
    print()
    
    if best_acc < 0.6:
        print("⚠️  警告: 准确率较低，建议:")
        print("   - 增加每类视频数量（至少10-20个）")
        print("   - 确保视频质量（清晰、光线充足）")
        print("   - 检查标签是否正确")


if __name__ == '__main__':
    main()
