<template>
  <a-card
    class="general-card behavior-detection-card"
    :title="$t('monitor.behaviorDetection.title')"
  >
    <template #extra>
      <a-tag :color="detectionStatus === 'running' ? 'arcoblue' : 'gray'">
        {{ detectionStatus === 'running' ? '检测中' : '未启动' }}
      </a-tag>
    </template>

    <div class="detection-content">
      <!-- 实时视频预览区域 -->
      <div class="video-preview-area">
        <div v-if="detectionStatus === 'running' || hasAnalyzedImage || hasAnalyzedVideo" class="video-container">
          <!-- 上传的图片/视频预览帧 -->
          <img
            v-if="currentFrame"
            ref="previewImage"
            :src="currentFrame"
            alt="实时检测画面"
            class="preview-image"
            @load="onImageLoad"
          />
          <div v-else class="placeholder">
            <IconVideoCamera class="icon" />
            <span>等待视频流...</span>
          </div>

          <!-- Canvas 绘制检测框（覆盖在 video/img 之上） -->
          <canvas
            v-if="(detectionStatus === 'running' || currentFrame) && currentResult?.persons?.length > 0"
            ref="detectionCanvas"
            class="detection-canvas"
          ></canvas>

          <!-- 检测结果叠加层 -->
          <div v-if="currentResult" class="detection-overlay">
            <div
              class="score-badge"
              :style="{
                backgroundColor: getScoreColor(currentResult.overall_score),
              }"
            >
              {{ currentResult.learning_status }}
            </div>
          </div>
        </div>

        <div v-else class="video-placeholder">
          <IconVideoCamera class="icon" />
          <span>点击"开启课堂行为检测"或"上传图片分析"开始分析</span>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="control-buttons">
        <a-button
          long
          type="primary"
          :loading="isStarting"
          :disabled="detectionStatus === 'running'"
          @click="startDetection"
        >
          <template #icon>
            <IconPlayCircle />
          </template>
          {{ $t('monitor.behaviorDetection.start') }}
        </a-button>

        <a-button
          long
          status="danger"
          :disabled="detectionStatus !== 'running'"
          @click="stopDetection"
        >
          <template #icon>
            <IconPauseCircle />
          </template>
          {{ $t('monitor.behaviorDetection.stop') }}
        </a-button>
      </div>

      <!-- 上传分析 -->
      <div style="margin-top: 12px; display: flex; gap: 8px;">
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display: none"
          @change="handleFileUpload"
        />
        <input
          ref="videoInput"
          type="file"
          accept="video/mp4,video/avi,video/mov,video/webm"
          style="display: none"
          @change="handleVideoUpload"
        />
        <a-button
          style="flex: 1"
          type="outline"
          :loading="isUploading"
          @click="fileInput?.click()"
        >
          <template #icon>
            <IconUpload />
          </template>
          图片
        </a-button>
        <a-button
          style="flex: 1"
          type="outline"
          status="success"
          :loading="isUploadingVideo"
          @click="videoInput?.click()"
        >
          <template #icon>
            <IconVideoCamera />
          </template>
          视频
        </a-button>
      </div>

      <!-- 实时统计 -->
      <div
        v-if="currentResult"
        class="realtime-stats"
      >
        <a-divider orientation="center">{{
          $t('monitor.behaviorDetection.realtimeStats')
        }}</a-divider>

        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">综合评分</div>
            <div
              class="stat-value"
              :style="{ color: getScoreColor(currentResult.overall_score) }"
            >
              {{ currentResult.overall_score.toFixed(2) }}
            </div>
          </div>

          <div class="stat-item">
            <div class="stat-label">检测人数</div>
            <div class="stat-value">{{ currentResult.persons?.length || 0 }}</div>
          </div>
        </div>

        <!-- 行为列表 -->
        <div class="behavior-list">
          <div
            v-for="(behavior, index) in currentResult.behaviors"
            :key="index"
            class="behavior-item"
          >
            <div class="behavior-name">{{ behavior.behavior }}</div>
            <div class="behavior-confidence" style="display: flex; align-items: center; gap: 8px; flex: 1;">
              <a-progress 
                :percent="Math.min(100, Math.round(behavior.confidence <= 1 ? behavior.confidence * 100 : behavior.confidence))" 
                :color="getBehaviorColor(behavior.behavior)"
                size="small"
                style="flex: 1;"
                :show-text="false"
              />
              <span style="font-size: 12px; color: #666; min-width: 40px; text-align: right;">
                {{ Math.round(behavior.confidence <= 1 ? behavior.confidence * 100 : behavior.confidence) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史记录快捷入口 -->
      <div v-if="recentRecords.length > 0" class="recent-records">
        <a-divider orientation="center">{{
          $t('monitor.behaviorDetection.recentRecords')
        }}</a-divider>
        <a-list :bordered="false" size="small">
          <a-list-item
            v-for="record in recentRecords.slice(0, 3)"
            :key="record.id"
          >
            <div class="record-item">
              <span class="record-time">{{
                formatTime(record.timestamp)
              }}</span>
              <a-tag :color="getStatusColor(record.overall_status)">
                {{ record.overall_status }}
              </a-tag>
            </div>
          </a-list-item>
        </a-list>
        <a-button type="text" long @click="viewAllRecords">
          {{ $t('monitor.behaviorDetection.viewAll') }}
        </a-button>
      </div>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { Message } from '@arco-design/web-vue';
import {
  IconVideoCamera,
  IconPlayCircle,
  IconPauseCircle,
  IconUpload,
} from '@arco-design/web-vue/es/icon';
import {
  startRealtimeAnalysis,
  getAnalysisRecords,
  getBehaviorDefinitions,
  analyzeImage,
  analyzeVideo,
  type AnalysisRecord,
  type BehaviorDefinitionsResponse,
  type ImageAnalysisResult,
  type Person,
} from '@/api/behavior-analysis';

  const props = defineProps<{
    courseId?: string;
  }>();

  const emit = defineEmits<{
    (e: 'update:result', result: ImageAnalysisResult | null): void;
  }>();

// 状态
const detectionStatus = ref<'idle' | 'running'>('idle');
const isStarting = ref(false);
const isUploading = ref(false);
const isUploadingVideo = ref(false);
const currentFrame = ref<string>('');
const currentResult = ref<ImageAnalysisResult | null>(null);
const recentRecords = ref<AnalysisRecord[]>([]);
const behaviorDefinitions = ref<BehaviorDefinitionsResponse | null>(null);
const sessionId = ref<string>('');
const fileInput = ref<HTMLInputElement | null>(null);
const videoInput = ref<HTMLInputElement | null>(null);
const previewImage = ref<HTMLImageElement | null>(null);
const detectionCanvas = ref<HTMLCanvasElement | null>(null);

// 是否有分析过的图片或视频
const hasAnalyzedImage = ref(false);
const hasAnalyzedVideo = ref(false);
const videoFrameUrl = ref<string>('');  // 视频分析时的预览图（提取第一帧）

// 最近一次上传的文件（待分析）
const lastUploadedFile = ref<File | null>(null);
const lastUploadedType = ref<'image' | 'video' | null>(null);

// 定时器
let refreshInterval: any = null;

// （结果仅在面板内展示）

// 获取行为定义
const loadBehaviorDefinitions = async () => {
  try {
    const res = await getBehaviorDefinitions();
    behaviorDefinitions.value = res.data;
  } catch (error) {
    console.error('加载行为定义失败:', error);
  }
};

// 获取历史记录
const loadRecentRecords = async () => {
  if (!props.courseId) return;
  try {
    const res = await getAnalysisRecords(props.courseId, 0, 10);
    recentRecords.value = res.data.data;
  } catch (error) {
    console.error('加载历史记录失败:', error);
  }
};

// 开始检测（分析最近一次上传的文件）
const startDetection = async () => {
  if (!props.courseId) {
    Message.warning('请先选择课程');
    return;
  }
  if (!lastUploadedFile.value) {
    Message.warning('请先上传图片或视频');
    return;
  }

  detectionStatus.value = 'running';

  if (lastUploadedType.value === 'image') {
    isUploading.value = true;
    Message.loading('正在分析图片...');
    try {
      const res = await analyzeImage(lastUploadedFile.value);
      if (res.data?.status === 'error') {
        throw new Error(res.data?.error || '分析失败');
      }
      currentResult.value = res.data;
      hasAnalyzedImage.value = true;
      hasAnalyzedVideo.value = false;
      setTimeout(() => drawDetectionBoxes(), 100);
      Message.success('分析完成！检测到 ' + (res.data.persons?.length || 0) + ' 人');
    } catch (error: any) {
      console.error('图片分析失败:', error);
      Message.error(error?.message || '分析失败');
    } finally {
      isUploading.value = false;
      detectionStatus.value = 'idle';
    }
  } else if (lastUploadedType.value === 'video') {
    isUploadingVideo.value = true;
    Message.loading('正在分析视频，请稍候...');
    try {
      const res = await analyzeVideo(lastUploadedFile.value, props.courseId || undefined, 30);
      if (res.data?.status === 'error') {
        throw new Error(res.data?.error || '分析失败');
      }
      const summary = res.data.summary;
      const personsFromVideo = res.data.persons || [];
      const videoInfo = res.data.video_info || {};
      currentResult.value = {
        status: 'success',
        behaviors: [],
        persons: personsFromVideo,
        overall_score: summary?.average_score || 0,
        learning_status: summary?.overall_status || '无法评估',
        timestamp: new Date().toISOString(),
        image_width: videoInfo.image_width || 0,
        image_height: videoInfo.image_height || 0,
      };
      hasAnalyzedVideo.value = true;
      hasAnalyzedImage.value = false;
      setTimeout(() => drawDetectionBoxes(), 200);
      Message.success(`视频分析完成！检测到 ${personsFromVideo.length} 人`);
      loadRecentRecords();
    } catch (error: any) {
      console.error('视频分析失败:', error);
      Message.error(error?.message || '视频分析失败');
      hasAnalyzedVideo.value = false;
    } finally {
      isUploadingVideo.value = false;
      detectionStatus.value = 'idle';
    }
  }
};

// 停止检测
const stopDetection = () => {
  detectionStatus.value = 'idle';
  // 只清空实时检测的状态，不清空上传图片/视频的结果
  if (!hasAnalyzedImage.value && !hasAnalyzedVideo.value) {
    currentFrame.value = '';
    currentResult.value = null;
  }
  Message.success('分析已停止');
};

// （实时分析逻辑已移至主舞台页面组件）

// 获取分数颜色（优先使用后端返回的评分区间，未加载时走默认兜底）
const getScoreColor = (score: number): string => {
  const ranges = behaviorDefinitions.value?.score_ranges || [];
  for (const r of ranges) {
    if (score >= r.min && score <= r.max) {
      return r.color;
    }
  }
  if (score >= 0.7) return '#52c41a';
  if (score >= 0.3) return '#1890ff';
  if (score >= -0.3) return '#faad14';
  if (score >= -0.7) return '#fa541c';
  return '#f5222d';
};

// 获取行为颜色
const getBehaviorColor = (behaviorName: string): string => {
  const behavior = behaviorDefinitions.value?.behaviors.find(b => b.name === behaviorName);
  return behavior?.color || '#1890ff';
};

// 获取状态颜色
const getStatusColor = (status: string): string => {
  if (status.includes('优秀')) return 'arcoblue';
  if (status.includes('良好')) return 'blue';
  if (status.includes('一般')) return 'orange';
  if (status.includes('较差')) return 'red';
  return 'gray';
};

// 格式化时间
const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// 查看所有记录
const viewAllRecords = () => {
  Message.info('查看所有历史记录功能待实现');
};

// 处理文件上传（仅保存，不立即分析）
const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  
  if (!file) return;
  
  if (!file.type.startsWith('image/')) {
    Message.error('请选择图片文件');
    return;
  }
  
  lastUploadedFile.value = file;
  lastUploadedType.value = 'image';
  hasAnalyzedImage.value = false;
  hasAnalyzedVideo.value = false;
  detectionStatus.value = 'idle';
  currentResult.value = null;
  
  // 显示图片预览
  const reader = new FileReader();
  reader.onload = (e) => {
    currentFrame.value = e.target?.result as string;
  };
  reader.readAsDataURL(file);
  
  Message.info('图片已上传，点击"开启课堂行为检测"开始分析');
  target.value = '';
};

// 从视频文件提取第一帧作为预览图
const extractVideoFirstFrame = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    video.preload = 'metadata';
    video.crossOrigin = 'anonymous';
    
    video.onloadeddata = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg');
      resolve(dataUrl);
    };
    
    video.onerror = () => {
      reject(new Error('无法加载视频'));
    };
    
    video.src = URL.createObjectURL(file);
    video.currentTime = 0.1; // 跳到第一帧之后
  });
};

// 处理视频上传（仅保存，不立即分析）
const handleVideoUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  
  if (!file) return;
  
  if (!file.type.startsWith('video/')) {
    Message.error('请选择视频文件');
    return;
  }
  
  // 限制100MB
  if (file.size > 100 * 1024 * 1024) {
    Message.error('视频文件不能超过100MB');
    return;
  }
  
  lastUploadedFile.value = file;
  lastUploadedType.value = 'video';
  hasAnalyzedImage.value = false;
  hasAnalyzedVideo.value = false;
  detectionStatus.value = 'idle';
  currentResult.value = null;
  
  // 提取视频第一帧作为预览图
  try {
    const firstFrameUrl = await extractVideoFirstFrame(file);
    videoFrameUrl.value = firstFrameUrl;
    currentFrame.value = firstFrameUrl;
    Message.info('视频已上传，点击"开启课堂行为检测"开始分析');
  } catch (error: any) {
    Message.error('视频预览生成失败');
  }
  
  target.value = '';
};

// 图片加载完成后绘制检测框
const onImageLoad = () => {
  console.log('图片加载完成，准备绘制检测框');
  setTimeout(drawDetectionBoxes, 50);
};

// 窗口大小变化时重绘检测框
const onResize = () => {
  if (currentFrame.value && currentResult.value?.persons) {
    drawDetectionBoxes();
  }
};

// 绘制检测框
const drawDetectionBoxes = () => {
  if (!detectionCanvas.value || !previewImage.value || !currentResult.value?.persons) {
    console.log('无法绘制：缺少 canvas、图片或人员数据', {
      hasCanvas: !!detectionCanvas.value,
      hasImage: !!previewImage.value,
      hasPersons: !!currentResult.value?.persons,
      personsCount: currentResult.value?.persons?.length
    });
    return;
  }
  
  const canvas = detectionCanvas.value;
  const img = previewImage.value;
  const ctx = canvas.getContext('2d');
  
  if (!ctx) {
    console.log('无法获取 canvas context');
    return;
  }
  
  // 等待图片完全加载
  if (!img.complete || img.naturalWidth === 0) {
    console.log('图片尚未完全加载，稍后重试');
    setTimeout(drawDetectionBoxes, 100);
    return;
  }
  
  // 设置 canvas 尺寸与图片显示尺寸一致
  const rect = img.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  
  console.log('Canvas尺寸:', canvas.width, 'x', canvas.height);
  console.log('图片原始尺寸:', img.naturalWidth, 'x', img.naturalHeight);
  console.log('图片显示尺寸:', rect.width, 'x', rect.height);
  console.log('后端返回尺寸:', currentResult.value.image_width, 'x', currentResult.value.image_height);
  console.log('人员数量:', currentResult.value.persons.length);
  
  // 计算缩放比例
  const imgWidth = currentResult.value.image_width || img.naturalWidth;
  const imgHeight = currentResult.value.image_height || img.naturalHeight;
  const scaleX = canvas.width / imgWidth;
  const scaleY = canvas.height / imgHeight;
  
  // 清空画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 绘制每个人的检测框
  currentResult.value.persons.forEach((person: any, index: number) => {
    console.log(`绘制人员 ${index}:`, person);
    const [x1, y1, x2, y2] = person.bbox;
    
    // 缩放坐标
    const sx1 = x1 * scaleX;
    const sy1 = y1 * scaleY;
    const sx2 = x2 * scaleX;
    const sy2 = y2 * scaleY;
    const width = sx2 - sx1;
    const height = sy2 - sy1;
    
    console.log(`检测框 ${index}:`, { sx1, sy1, width, height, color: person.color });
    
    // 绘制矩形框
    ctx.strokeStyle = person.color || '#6366f1';
    ctx.lineWidth = 3;
    ctx.strokeRect(sx1, sy1, width, height);
    
    // 绘制标签背景
    const label = `${person.behavior} (${Math.round(person.confidence * 100)}%)`;
    ctx.font = 'bold 14px Arial';
    const textWidth = ctx.measureText(label).width;
    const textHeight = 20;
    
    ctx.fillStyle = person.color || '#6366f1';
    ctx.fillRect(sx1, sy1 - textHeight - 4, textWidth + 10, textHeight + 4);
    
    // 绘制标签文字
    ctx.fillStyle = '#fff';
    ctx.fillText(label, sx1 + 5, sy1 - 6);
  });
};

// 组件挂载
onMounted(() => {
  loadBehaviorDefinitions();
  loadRecentRecords();

  refreshInterval = setInterval(() => {
    if (detectionStatus.value !== 'running') {
      loadRecentRecords();
    }
  }, 30000);

  window.addEventListener('resize', onResize);
});

// 组件卸载
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  window.removeEventListener('resize', onResize);
});
</script>

<style scoped lang="less">
  .behavior-detection-card {
    .detection-content {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .video-preview-area {
      .video-container {
        position: relative;
        width: 100%;
        min-height: 150px;
        max-height: 220px;
        object-fit: contain;
      }

      .preview-image,
      .preview-video {
        display: block;
        width: 100%;
        height: auto;
        max-height: 220px;
        object-fit: contain;
        background: #000;
        border-radius: 8px;
      }
      
      .detection-canvas {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
      }

      .video-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 150px;
        background: #f5f5f5;
        border-radius: 8px;
        color: #999;

        .icon {
          font-size: 40px;
          margin-bottom: 8px;
        }
      }
    }

    .control-buttons {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .realtime-stats {
      .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 12px;

        .stat-item {
          text-align: center;
          padding: 8px;
          background: #f5f5f5;
          border-radius: 8px;

          .stat-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
          }

          .stat-value {
            font-size: 20px;
            font-weight: 600;
          }
        }
      }

      .behavior-list {
        .behavior-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 0;
          border-bottom: 1px solid #f0f0f0;

          &:last-child {
            border-bottom: none;
          }

          .behavior-name {
            width: 80px;
            font-size: 12px;
            color: #333;
          }

          .behavior-confidence {
            flex: 1;
          }
        }
      }
    }

    .recent-records {
      .record-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;

        .record-time {
          font-size: 12px;
          color: #666;
        }
      }
    }
  }
</style>
