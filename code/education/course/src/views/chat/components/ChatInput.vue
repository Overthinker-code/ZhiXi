<script setup>
  import { Close, Document } from '@element-plus/icons-vue';
  import { ref } from 'vue';

  // 输入框的值，使用 ref 实现响应式
  const inputValue = ref('');
  const fileList = ref([]); // 存储上传的文件列表

  // 定义组件的 props，接收 loading 状态
  const props = defineProps({
    loading: {
      type: Boolean, // loading 的类型为布尔值
      default: false, // 默认值为 false
    },
  });

  // 定义组件的事件，这里声明了一个 send 事件
  const emit = defineEmits(['send']);

  // 处理发送消息的方法
  const handleSend = () => {
    if (!inputValue.value.trim() || props.loading) return;

    // 构建消息对象
    const messageContent = {
      text: inputValue.value.trim(),
      files: fileList.value,
    };

    // 触发 send 事件，将消息内容作为参数传递
    emit('send', messageContent);

    // 清空输入框和文件列表
    inputValue.value = '';
    fileList.value = [];
  };

  // 处理换行的方法（Shift + Enter）
  const handleNewline = (e) => {
    e.preventDefault(); // 阻止默认的 Enter 发送行为
    inputValue.value += '\n'; // 在当前位置添加换行符
  };

  // 处理文件上传
  const handleFileUpload = (uploadFile) => {
    // 确保获取到的是文件对象
    const file = uploadFile.raw;
    if (!file) return false;

    fileList.value.push({
      name: file.name,
      url: URL.createObjectURL(file),
      type: file.type.startsWith('image/') ? 'image' : 'file',
      size: file.size,
    });
    return false; // 阻止自动上传
  };

  // 移除文件
  const handleFileRemove = (file) => {
    const index = fileList.value.findIndex((item) => item.url === file.url);
    if (index !== -1) {
      URL.revokeObjectURL(fileList.value[index].url);
      fileList.value.splice(index, 1);
    }
  };
</script>

<template>
  <div class="chat-input-wrapper">
    <!-- 文件预览区域 -->
    <div v-if="fileList.length > 0" class="preview-area">
      <div v-for="file in fileList" :key="file.url" class="preview-item">
        <!-- 图片预览 -->
        <div v-if="file.type === 'image'" class="image-preview">
          <img :src="file.url" :alt="file.name" />
          <div class="remove-btn" @click="handleFileRemove(file)">
            <el-icon><Close /></el-icon>
          </div>
        </div>
        <!-- 文件预览 -->
        <div v-else class="file-preview">
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ (file.size / 1024).toFixed(1) }}KB</span>
          <div class="remove-btn" @click="handleFileRemove(file)">
            <el-icon><Close /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <el-input
      v-model="inputValue"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 6 }"
      placeholder="输入消息，Enter 发送，Shift + Enter 换行"
      resize="none"
      @keydown.enter.exact.prevent="handleSend"
      @keydown.enter.shift="handleNewline"
    />
    <div class="button-group">
      <el-upload
        class="upload-btn"
        :auto-upload="false"
        :show-file-list="false"
        :on-change="handleFileUpload"
        accept=".pdf,.doc,.docx,.txt,.md,.markdown"
      >
        <button class="action-btn">
          <img src="@/assets/photo/附件.png" alt="link" />
        </button>
      </el-upload>
      <el-upload
        class="upload-btn"
        :auto-upload="false"
        :show-file-list="false"
        :on-change="handleFileUpload"
        accept="image/*"
      >
        <button class="action-btn">
          <img src="@/assets/photo/图片.png" alt="picture" />
        </button>
      </el-upload>
      <div class="divider"></div>
      <button
        class="action-btn send-btn"
        :disabled="props.loading"
        @click="handleSend"
      >
        <img src="@/assets/photo/发送.png" alt="send" />
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
  .chat-input-wrapper {
    --input-border: #d4e1f2;
    --input-bg: rgba(255, 255, 255, 0.95);
    --input-action-bg: #f2f7ff;
    --input-action-hover: #e3efff;
    --input-send-start: #1b6fe1;
    --input-send-end: #0f4db8;
    padding: 0.75rem;
    border-radius: 18px;
    border: 1px solid var(--input-border);
    background: var(--input-bg);
    backdrop-filter: blur(8px);
    box-shadow: 0 14px 24px rgba(15, 23, 42, 0.11);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;

    &:focus-within {
      border-color: rgba(27, 111, 225, 0.34);
      box-shadow: 0 16px 30px rgba(15, 23, 42, 0.14);
    }

    .preview-area {
      margin-bottom: 0.55rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;

      .preview-item {
        position: relative;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: #fff;

        .image-preview {
          width: 66px;
          height: 66px;

          img {
            width: 100%;
            height: 100%;
            object-fit: cover;
          }
        }

        .file-preview {
          min-height: 42px;
          padding: 0 0.55rem;
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          background: #f8fbff;

          .file-name {
            max-width: 130px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #1a2f4d;
            font-size: 0.83rem;
          }

          .file-size {
            color: #6a7f9e;
            font-size: 0.74rem;
          }
        }

        .remove-btn {
          position: absolute;
          top: 4px;
          right: 4px;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: rgba(15, 23, 42, 0.58);
          color: #fff;
          cursor: pointer;
          transition: background 0.2s ease;

          &:hover {
            background: rgba(15, 23, 42, 0.8);
          }
        }
      }
    }

    :deep(.el-textarea__inner) {
      border: none;
      box-shadow: none;
      border-radius: 12px;
      padding: 0.7rem 0.8rem;
      background: #f8fbff;
      color: #132743;
      font-size: 0.95rem;
      line-height: 1.55;

      &::placeholder {
        color: #7c8ea8;
      }

      &:focus {
        border: none;
        box-shadow: none;
      }
    }

    .button-group {
      margin-top: 0.55rem;
      margin-left: auto;
      width: fit-content;
      padding: 0.3rem 0.45rem;
      border-radius: 999px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      background: var(--input-action-bg);
      display: flex;
      align-items: center;
      gap: 0.4rem;

      .upload-btn {
        display: inline-block;
      }

      .divider {
        width: 1px;
        height: 1rem;
        background: linear-gradient(
          180deg,
          transparent,
          rgba(90, 107, 132, 0.38),
          transparent
        );
      }

      .action-btn {
        width: 1.8rem;
        height: 1.8rem;
        border: none;
        background: transparent;
        border-radius: 999px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;

        img {
          width: 1rem;
          height: 1rem;
        }

        &:hover {
          background: var(--input-action-hover);
        }

        &.send-btn {
          width: 2rem;
          height: 2rem;
          background: linear-gradient(
            135deg,
            var(--input-send-start),
            var(--input-send-end)
          );
          box-shadow: 0 8px 16px rgba(15, 77, 184, 0.28);

          img {
            width: 1.15rem;
            height: 1.15rem;
          }

          &:hover {
            transform: translateY(-1px);
            filter: saturate(1.05);
          }

          &:disabled {
            opacity: 0.55;
            cursor: not-allowed;
            box-shadow: none;
          }
        }
      }
    }
  }

  @media (max-width: 760px) {
    .chat-input-wrapper {
      padding: 0.65rem;
      border-radius: 14px;

      .button-group {
        width: 100%;
        justify-content: flex-end;
      }
    }
  }
</style>
