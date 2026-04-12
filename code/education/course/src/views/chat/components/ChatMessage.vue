<script setup>
  import { renderMarkdown } from '@/utils/markdown';
  import { submitChatFeedback } from '@/api/rag';
  import { useSettingStore } from '@/store/setting';
  import { ArrowDown, Document } from '@element-plus/icons-vue';
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  // 导入图片资源
  import copyIcon from '@/assets/photo/复制.png';
  import successIcon from '@/assets/photo/成功.png';
  import thinkingIcon from '@/assets/photo/深度思考.png';
  import likeIcon from '@/assets/photo/赞.png';
  import likeActiveIcon from '@/assets/photo/赞2.png';
  import dislikeIcon from '@/assets/photo/踩.png';
  import dislikeActiveIcon from '@/assets/photo/踩2.png';
  import regenerateIcon from '@/assets/photo/重新生成.png';
  import humanizeAgentReasoning from '@/utils/humanizeAgentReasoning';
  import AgentThoughtCard from '@/views/chat/components/AgentThoughtCard.vue';

  // 定义props
  const props = defineProps({
    message: {
      type: Object,
      required: true,
    },
    isLastAssistantMessage: {
      type: Boolean,
      default: false,
    },
  });

  // 点赞和踩的状态
  const isLiked = ref(false);
  const isDisliked = ref(false);

  // 添加复制状态
  const isCopied = ref(false);

  /** 流式回复：正文 / 思考过程追赶式「打字机」 */
  const streamTypeLen = ref(0);
  const streamReasonLen = ref(0);
  let streamTypeTick = null;

  const isStreamingAssistantBubble = () =>
    props.message.role === 'assistant' &&
    props.message.loading &&
    props.isLastAssistantMessage;

  watch(
    () => [
      props.message.content,
      props.message.reasoning_content,
      props.message.loading,
      props.isLastAssistantMessage,
      props.message.role,
    ],
    () => {
      const fullLen = (props.message.content || '').length;
      const reasonFull = humanizeAgentReasoning(
        props.message.reasoning_content || ''
      ).length;
      if (!isStreamingAssistantBubble()) {
        streamTypeLen.value = fullLen;
        streamReasonLen.value = reasonFull;
        if (streamTypeTick) {
          clearInterval(streamTypeTick);
          streamTypeTick = null;
        }
        return;
      }
      if (streamTypeLen.value > fullLen) streamTypeLen.value = 0;
      if (streamReasonLen.value > reasonFull) streamReasonLen.value = 0;
      if (!streamTypeTick) {
        streamTypeTick = setInterval(() => {
          const targetC = (props.message.content || '').length;
          if (streamTypeLen.value < targetC) {
            const behind = targetC - streamTypeLen.value;
            const step = Math.max(1, Math.min(28, Math.ceil(behind / 4)));
            streamTypeLen.value = Math.min(targetC, streamTypeLen.value + step);
          }
          const plainR = humanizeAgentReasoning(
            props.message.reasoning_content || ''
          );
          const targetR = plainR.length;
          if (streamReasonLen.value < targetR) {
            const behind = targetR - streamReasonLen.value;
            const step = Math.max(1, Math.min(36, Math.ceil(behind / 4)));
            streamReasonLen.value = Math.min(
              targetR,
              streamReasonLen.value + step
            );
          }
        }, 28);
      }
    },
    { immediate: true }
  );

  // 添加重新生成的事件
  const emit = defineEmits(['regenerate', 'resumeAction', 'suggestion']);

  const handleSuggestionClick = (text) => {
    if (!text) return;
    emit('suggestion', text);
  };

  // 添加展开/折叠状态控制
  const isReasoningExpanded = ref(true);
  const isPipelineExpanded = ref(true);

  // 切换展开/折叠状态
  const toggleReasoning = () => {
    isReasoningExpanded.value = !isReasoningExpanded.value;
  };
  const togglePipeline = () => {
    isPipelineExpanded.value = !isPipelineExpanded.value;
  };

  // 处理复制函数
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(props.message.content);
      isCopied.value = true;

      // 1.5秒后恢复原始图标
      setTimeout(() => {
        isCopied.value = false;
      }, 2500);
    } catch (err) {
      // console.error('复制失败:', err);
    }
  };

  const settingStore = useSettingStore();

  // 处理点赞
  const handleLike = async () => {
    if (isDisliked.value) isDisliked.value = false;
    isLiked.value = !isLiked.value;
    if (isLiked.value) {
      try {
        await submitChatFeedback({
          record_id: props.message.id,
          rating: 'up',
          prompt_key: settingStore.settings.promptKey || 'tutor',
        });
      } catch {
        // silently ignore — backend may not support feedback yet
      }
    }
  };

  // 处理踩
  const handleDislike = async () => {
    if (isLiked.value) isLiked.value = false;
    isDisliked.value = !isDisliked.value;
    if (isDisliked.value) {
      try {
        await submitChatFeedback({
          record_id: props.message.id,
          rating: 'down',
          prompt_key: settingStore.settings.promptKey || 'tutor',
        });
      } catch {
        // silently ignore — backend may not support feedback yet
      }
    }
  };

  // 添加重新生成的事件
  const handleRegenerate = () => {
    emit('regenerate');
  };

  const handleResumeAction = (approve) => {
    emit('resumeAction', {
      pendingActionId: props.message.pending_action_id,
      approve,
    });
  };

  // 处理代码块的复制
  const handleCodeCopy = async (event) => {
    const codeBlock = event.target.closest('.code-block');
    const code = codeBlock.querySelector('code').textContent;

    try {
      await navigator.clipboard.writeText(code);
      // 可以添加复制成功的提示
    } catch (err) {
      // console.error('复制失败:', err);
    }
  };

  // 处理代码块主题切换
  const handleThemeToggle = (event) => {
    // 确保我们获取到正确的元素
    const codeBlock = event.target.closest('.code-block');
    // 修改获取图标元素的方式
    const themeBtn = event.target.closest('[data-action="theme"]');
    const themeIcon = themeBtn.querySelector('img');
    // const lightIcon = themeIcon.dataset.lightIcon;
    // const darkIcon = themeIcon.dataset.darkIcon;
    const { lightIcon, darkIcon } = themeIcon.dataset;

    // 添加调试日志
    // console.log('切换主题', {
    //   codeBlock,
    //   themeIcon,
    //   lightIcon,
    //   darkIcon,
    //   isDark: codeBlock.classList.contains('dark-theme'),
    // })

    codeBlock.classList.toggle('dark-theme');

    // 切换图标
    themeIcon.src = codeBlock.classList.contains('dark-theme')
      ? lightIcon
      : darkIcon;
  };

  // 修改事件监听的方式
  onMounted(() => {
    // 使用 MutationObserver 来监听 DOM 变化
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.addedNodes.length) {
          const codeBlocks = document.querySelectorAll('.code-block');
          codeBlocks.forEach((block) => {
            const copyBtn = block.querySelector('[data-action="copy"]');
            const themeBtn = block.querySelector('[data-action="theme"]');

            if (copyBtn && !copyBtn._hasListener) {
              copyBtn.addEventListener('click', handleCodeCopy);
              copyBtn._hasListener = true;
            }
            if (themeBtn && !themeBtn._hasListener) {
              themeBtn.addEventListener('click', handleThemeToggle);
              themeBtn._hasListener = true;
              // console.log('添加主题切换监听器', { block, themeBtn })
            }
          });
        }
      });
    });

    // 开始观察
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    // 组件卸载时清理
    onUnmounted(() => {
      observer.disconnect();
      const codeBlocks = document.querySelectorAll('.code-block');
      codeBlocks.forEach((block) => {
        const copyBtn = block.querySelector('[data-action="copy"]');
        const themeBtn = block.querySelector('[data-action="theme"]');

        copyBtn?.removeEventListener('click', handleCodeCopy);
        themeBtn?.removeEventListener('click', handleThemeToggle);
      });
      if (streamTypeTick) {
        clearInterval(streamTypeTick);
        streamTypeTick = null;
      }
    });
  });

  // 将消息内容转换为 HTML
  const renderedContent = computed(() => {
    let raw = props.message.content || '';
    if (isStreamingAssistantBubble()) {
      raw = raw.slice(0, streamTypeLen.value);
    }
    return renderMarkdown(raw);
  });

  /** 仅模型侧链式推理；多智能体流水线单独用 AgentThoughtCard（message.thoughts） */
  const effectiveReasoning = computed(() => {
    const r = props.message.reasoning_content;
    if (r && String(r).trim()) return String(r);
    return '';
  });

  const showAgentPipeline = computed(
    () =>
      props.message.role === 'assistant' &&
      ((props.message.thoughts && props.message.thoughts.length > 0) ||
        props.message.loading)
  );

  const effectiveReasoningTrimmed = computed(() =>
    effectiveReasoning.value.trim()
  );

  const displayReasoningPlain = computed(() =>
    humanizeAgentReasoning(effectiveReasoning.value)
  );

  const renderedReasoning = computed(() => {
    let s = displayReasoningPlain.value;
    if (!s || !String(s).trim()) return '';
    if (isStreamingAssistantBubble()) {
      s = s.slice(0, streamReasonLen.value);
    }
    return renderMarkdown(s);
  });

  const showReasoningToggle = computed(
    () =>
      props.message.role === 'assistant' &&
      (effectiveReasoningTrimmed.value.length > 0 || props.message.loading)
  );
</script>

<template>
  <div class="message-item" :class="{ 'is-mine': message.role === 'user' }">
    <div class="content" :class="{ 'is-user-content': message.role === 'user' }">
      <!-- 文件预览区域 -->
      <div
        v-if="message.files && message.files.length > 0"
        class="files-container"
      >
        <div v-for="file in message.files" :key="file.url" class="file-item">
          <!-- 图片预览 -->
          <div v-if="file.type === 'image'" class="image-preview">
            <img :src="file.url" :alt="file.name" />
          </div>
          <!-- 文件预览 -->
          <div v-else class="file-preview">
            <el-icon><Document /></el-icon>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ (file.size / 1024).toFixed(1) }}KB</span>
          </div>
        </div>
      </div>

      <!-- 多智能体流水线（与「深度思考」分离，随 SSE thought 实时追加） -->
      <div
        v-if="showAgentPipeline"
        class="pipeline-toggle"
        @click="togglePipeline"
      >
        <span class="pipeline-dot" />
        <span>{{
          message.loading ? '多智能体协作进行中' : '多智能体协作过程'
        }}</span>
        <el-icon
          class="toggle-icon"
          :class="{ 'is-expanded': isPipelineExpanded }"
        >
          <ArrowDown />
        </el-icon>
      </div>
      <AgentThoughtCard
        v-if="showAgentPipeline"
        :thoughts="message.thoughts || []"
        :streaming="!!message.loading"
        :collapsed="!isPipelineExpanded"
      />

      <!-- 消息内容 -->
      <div
        v-if="message.loading && message.role === 'assistant'"
        class="thinking-text"
      >
        <img
          src="@/assets/photo/加载中.png"
          alt="loading"
          class="loading-icon"
        />
        <span>内容生成中...</span>
      </div>
      <!-- 仅保留「深度思考」：与技术向思维链卡片合并，避免重复 -->
      <div
        v-if="showReasoningToggle"
        class="reasoning-toggle"
        @click="toggleReasoning"
      >
        <span
          v-if="message.loading"
          class="reasoning-spinner"
          aria-hidden="true"
        />
        <img v-else :src="thinkingIcon" alt="" />
        <span>{{
          message.loading && !effectiveReasoningTrimmed
            ? '正在梳理答案思路…'
            : '我的思考过程'
        }}</span>
        <el-icon
          class="toggle-icon"
          :class="{ 'is-expanded': isReasoningExpanded }"
        >
          <ArrowDown />
        </el-icon>
      </div>
      <div
        v-if="showReasoningToggle && isReasoningExpanded"
        class="reasoning markdown-body"
      >
        <div
          v-if="message.loading && !effectiveReasoningTrimmed"
          class="reasoning-wait"
        >
          <span class="wait-dot" />
          <span class="wait-dot" />
          <span class="wait-dot" />
          <span class="wait-text">正在整理思路</span>
        </div>
        <div v-else-if="renderedReasoning" v-html="renderedReasoning"></div>
      </div>
      <!-- content -->
      <div
        class="bubble-row"
        :class="{ 'bubble-row--user': message.role === 'user' }"
      >
        <div class="bubble markdown-body" v-html="renderedContent" />
        <span
          v-if="message.role === 'assistant' && message.loading"
          class="stream-tail-caret"
          aria-hidden="true"
        />
      </div>
      <div
        v-if="
          message.role === 'assistant' &&
          message.suggestions &&
          message.suggestions.length > 0
        "
        class="suggestions-row"
      >
        <button
          v-for="s in message.suggestions"
          :key="s"
          class="suggestion-pill"
          @click="handleSuggestionClick(s)"
        >
          {{ s }}
        </button>
      </div>
      <div v-if="message.requires_confirmation" class="hitl-card">
        <p>系统生成了学习计划，是否确认写入你的学习日历？</p>
        <div class="hitl-actions">
          <button class="action-btn" @click="handleResumeAction(true)"
            >确认</button
          >
          <button class="action-btn reject" @click="handleResumeAction(false)">
            取消
          </button>
        </div>
      </div>
      <!-- 只在 AI 助手消息中显示操作按钮和 tokens 信息 -->
      <div
        v-if="message.role === 'assistant' && message.loading === false"
        class="message-actions"
      >
        <button
          v-if="isLastAssistantMessage"
          class="action-btn"
          @click="handleRegenerate"
          data-tooltip="重新生成"
        >
          <img :src="regenerateIcon" alt="regenerate" />
        </button>
        <button class="action-btn" @click="handleCopy" data-tooltip="复制">
          <img :src="isCopied ? successIcon : copyIcon" alt="copy" />
        </button>
        <button class="action-btn" @click="handleLike" data-tooltip="喜欢">
          <img :src="isLiked ? likeActiveIcon : likeIcon" alt="like" />
        </button>
        <button class="action-btn" @click="handleDislike" data-tooltip="不喜欢">
          <img
            :src="isDisliked ? dislikeActiveIcon : dislikeIcon"
            alt="dislike"
          />
        </button>

        <!-- 添加 tokens 信息 -->
        <span v-if="message.completion_tokens" class="tokens-info">
          tokens: {{ message.completion_tokens }}, speed:
          {{ message.speed }} tokens/s
        </span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
  .message-item {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 1rem;
    animation: message-rise 0.24s ease both;

    &.is-mine {
      justify-content: flex-end;

      .content {
        .bubble.markdown-body {
          border: 1px solid rgba(255, 255, 255, 0.35);
          background: linear-gradient(
            135deg,
            #6366f1 0%,
            #8b5cf6 52%,
            #2563eb 100%
          );
          box-shadow: 0 12px 32px rgba(99, 102, 241, 0.35);
          color: #fff;

          /* 覆盖内部 markdown 样式为白色 */
          :deep(p), :deep(li), :deep(td), :deep(th) { color: rgba(255,255,255,0.95); }
          :deep(code:not(pre code)) {
            background: rgba(255,255,255,0.18);
            color: #fff;
          }
          :deep(a) { color: #e0e7ff; }
          :deep(blockquote) {
            border-left-color: rgba(255,255,255,0.4);
            background: rgba(255,255,255,0.10);
            color: rgba(255,255,255,0.85);
          }
        }
      }
    }

    .content {
      width: fit-content;
      max-width: min(92%, 860px);
      min-width: 0;

      .reasoning-spinner {
        flex-shrink: 0;
        width: 0.88rem;
        height: 0.88rem;
        border: 2px solid rgba(99, 102, 241, 0.2);
        border-top-color: #6366f1;
        border-radius: 50%;
        animation: reasoning-spin 0.65s linear infinite;
      }

      .reasoning-toggle {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.28rem 0.56rem;
        margin: 0 0 0.5rem 0.5rem;
        border-radius: 999px;
        /* 品牌绿 toggle */
        border: 1px solid rgba(99, 102, 241, 0.25);
        background: linear-gradient(
          135deg,
          rgba(99, 102, 241, 0.12),
          rgba(99, 102, 241, 0.04)
        );
        cursor: pointer;
        transition: all 0.2s ease;

        img {
          width: 0.88rem;
          height: 0.88rem;
        }

        span {
          color: #4f46e5;
          font-size: 0.78rem;
          font-weight: 600;
        }

        .toggle-icon {
          color: #4f46e5;
          font-size: 0.75rem;
          transition: transform 0.2s ease;

          &.is-expanded {
            transform: rotate(180deg);
          }
        }

        &:hover {
          transform: translateY(-1px);
          border-color: rgba(99, 102, 241, 0.45);
        }
      }

      .pipeline-toggle {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.28rem 0.56rem;
        margin: 0 0 0.45rem 0.5rem;
        border-radius: 999px;
        border: 1px solid rgba(51, 65, 85, 0.2);
        background: rgba(241, 245, 249, 0.9);
        cursor: pointer;

        .pipeline-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #64748b;
        }

        span {
          color: #334155;
          font-size: 0.78rem;
          font-weight: 600;
        }

        .toggle-icon {
          color: #334155;
          font-size: 0.75rem;
          transition: transform 0.2s ease;

          &.is-expanded {
            transform: rotate(180deg);
          }
        }
      }

      .reasoning {
        margin: 0 0 0.6rem 1.4rem;
        padding: 0.65rem 0.8rem;
        /* 品牌绿左边框 */
        border-left: 3px solid rgba(99, 102, 241, 0.40);
        border-radius: 0 10px 10px 0;
        background: #f5f3ff;
        color: #64748b;
        font-size: 0.85rem;
        line-height: 1.65;

        .reasoning-wait {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          min-height: 1.5rem;
          color: #64748b;
          font-size: 0.82rem;

          .wait-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #6366f1;
            opacity: 0.35;
            animation: reasoning-dot 1.1s ease-in-out infinite;

            &:nth-child(2) {
              animation-delay: 0.18s;
            }

            &:nth-child(3) {
              animation-delay: 0.36s;
            }
          }

          .wait-text {
            margin-left: 0.25rem;
          }
        }

        :deep(p) {
          margin: 0;

          &:not(:last-child) {
            margin-bottom: 0.5rem;
          }
        }
      }

      @keyframes reasoning-spin {
        to {
          transform: rotate(360deg);
        }
      }

      @keyframes reasoning-dot {
        0%,
        100% {
          opacity: 0.3;
          transform: scale(0.85);
        }

        50% {
          opacity: 1;
          transform: scale(1.15);
        }
      }

      .bubble-row {
        display: flex;
        align-items: flex-end;
        gap: 6px;
        width: 100%;
        max-width: min(92%, 860px);

        &--user {
          flex-direction: row-reverse;
        }
      }

      .is-user-content .bubble-row {
        margin-left: auto;
      }

      .stream-tail-caret {
        flex-shrink: 0;
        width: 10px;
        height: 10px;
        margin-bottom: 0.65rem;
        border-radius: 50%;
        background: radial-gradient(circle, #c4b5fd 0%, #6366f1 45%, transparent 72%);
        box-shadow: 0 0 14px rgba(129, 140, 248, 0.95);
        animation: caretPulse 1.1s ease-in-out infinite;
      }

      @keyframes caretPulse {
        0%,
        100% {
          opacity: 1;
          transform: scale(1);
        }
        50% {
          opacity: 0.55;
          transform: scale(0.92);
        }
      }

      .bubble.markdown-body {
        display: block;
        flex: 1;
        min-width: 0;
        padding: 0.82rem 1rem;
        border-radius: 0 16px 16px 16px;
        border: 1px solid rgba(99, 102, 241, 0.18);
        border-left: 3px solid #6366f1;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 28px rgba(99, 102, 241, 0.12);
        color: #0f172a;
        font-size: 0.95rem;
        line-height: 1.65;
        word-break: break-word;
        overflow: hidden;

        :deep(p) {
          margin: 0;

          &:not(:last-child) {
            margin-bottom: 0.52rem;
          }
        }

        :deep(code:not(pre code)) {
          padding: 0.16em 0.38em;
          border-radius: 0.3rem;
          font-size: 0.86em;
          background: #eef2ff;
          color: #4338ca;
          font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
        }

        :deep(ul),
        :deep(ol) {
          margin: 0.5rem 0;
          padding-left: 1.3rem;
        }

        :deep(blockquote) {
          margin: 0.55rem 0;
          padding: 0.4rem 0.75rem;
          border-left: 3px solid rgba(99, 102, 241, 0.35);
          background: #f5f3ff;
          color: #64748b;
          border-radius: 0 8px 8px 0;
        }

        :deep(table) {
          width: 100%;
          border-collapse: collapse;
          margin: 0.5rem 0;

          th,
          td {
            padding: 0.45rem;
            border: 1px solid #dce6f4;
          }

          th {
            background: #f4f8ff;
          }
        }

        :deep(a) {
          color: #145cc4;
          text-decoration: none;

          &:hover {
            text-decoration: underline;
          }
        }

        :deep(img) {
          max-width: 100%;
          border-radius: 0.55rem;
        }

        :deep(.code-block) {
          margin: 0.65rem 0;
          border-radius: 12px;
          border: 1px solid #d6e2f1;
          overflow: hidden;

          > pre {
            margin: 0 !important;
          }

          .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.45rem 0.75rem;
            background: #eff5ff;
            border-bottom: 1px solid #d6e2f1;

            .code-lang {
              color: #4f6382;
              font-size: 0.78rem;
              font-weight: 600;
              text-transform: uppercase;
              letter-spacing: 0.03em;
              font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
            }

            .code-actions {
              display: flex;
              gap: 0.3rem;

              .code-action-btn {
                width: 1.45rem;
                height: 1.45rem;
                border: none;
                border-radius: 6px;
                background: transparent;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;

                img {
                  width: 0.9rem;
                  height: 0.9rem;
                }

                &:hover {
                  background: rgba(20, 92, 196, 0.12);
                }
              }
            }
          }

          pre.hljs {
            margin: 0 !important;
            padding: 0.8rem 0.9rem;
            overflow-x: auto;
            white-space: pre;

            code {
              white-space: pre;
              font-size: 0.86rem;
              line-height: 1.5;
              font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
            }
          }

          &:not(.dark-theme) pre.hljs {
            background: #f8fbff;
            color: #1b2e4a;
          }

          &.dark-theme {
            border-color: #223b66;

            .code-header {
              background: #10233f;
              border-color: #223b66;

              .code-lang {
                color: #c8d9f5;
              }

              .code-action-btn:hover {
                background: rgba(255, 255, 255, 0.13);
              }
            }

            pre.hljs {
              background: #0f172a;
              color: #d7e3ff;
            }
          }
        }
      }

      .hitl-card {
        margin-top: 8px;
        padding: 10px;
        border: 1px solid rgba(99, 102, 241, 0.20);
        border-radius: 10px;
        background: #f5f3ff;

        p {
          margin: 0 0 8px;
          font-size: 13px;
          color: #0f172a;
        }

        .hitl-actions {
          display: flex;
          gap: 8px;

          .action-btn {
            border: none;
            border-radius: 6px;
            padding: 4px 10px;
            background: #6366f1;
            color: #fff;
            cursor: pointer;
            font-size: 12px;

            &.reject {
              background: #64748b;
            }
          }
        }
      }

      .message-actions {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        margin-top: 0.45rem;
        padding-left: 0.65rem;

        .action-btn {
          width: 1.55rem;
          height: 1.55rem;
          border: 1px solid transparent;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.85);
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          position: relative;
          transition: all 0.18s ease;

          img {
            width: 0.95rem;
            height: 0.95rem;
          }

          &::after {
            content: attr(data-tooltip);
            position: absolute;
            left: 50%;
            bottom: calc(100% + 6px);
            transform: translateX(-50%);
            padding: 0.2rem 0.45rem;
            font-size: 0.68rem;
            border-radius: 6px;
            color: #fff;
            background: rgba(15, 23, 42, 0.82);
            opacity: 0;
            visibility: hidden;
            white-space: nowrap;
            transition: all 0.2s ease;
          }

          &:hover {
            border-color: rgba(20, 92, 196, 0.2);
            transform: translateY(-1px);
          }

          &:hover::after {
            opacity: 1;
            visibility: visible;
          }
        }

        .tokens-info {
          margin-left: 0.2rem;
          padding: 0.2rem 0.5rem;
          border-radius: 999px;
          background: #eff4fb;
          color: #61738f;
          font-size: 0.72rem;
          white-space: nowrap;
        }
      }
    }

    .thinking-text {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.62rem 0.84rem;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid #d8e3f2;
      color: #546986;
      font-size: 0.82rem;

      .loading-icon {
        width: 0.92rem;
        height: 0.92rem;
        animation: spin 1s linear infinite;
      }
    }
  }

  .suggestions-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
  }

  .suggestion-pill {
    border: 1px solid rgba(25, 103, 210, 0.22);
    background: rgba(25, 103, 210, 0.08);
    color: #11458e;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
  }

  .files-container {
    margin-bottom: 0.55rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;

    .file-item {
      .image-preview {
        max-width: 196px;
        border-radius: 10px;
        border: 1px solid rgba(15, 23, 42, 0.08);
        overflow: hidden;

        img {
          display: block;
          max-width: 100%;
          height: auto;
        }
      }

      .file-preview {
        padding: 0.45rem 0.55rem;
        border-radius: 10px;
        border: 1px solid rgba(15, 23, 42, 0.08);
        background: #f8fbff;
        display: flex;
        align-items: center;
        gap: 0.45rem;

        .file-name {
          max-width: 124px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 0.82rem;
          color: #1d3353;
        }

        .file-size {
          color: #6e829f;
          font-size: 0.72rem;
        }
      }
    }
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes message-rise {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 760px) {
    .message-item {
      margin-bottom: 0.85rem;

      .content {
        max-width: 100%;

        .bubble.markdown-body {
          padding: 0.74rem 0.85rem;
          border-radius: 14px;
          font-size: 0.91rem;
        }

        .reasoning {
          margin-left: 0.9rem;
          margin-right: 0.2rem;
          padding: 0.55rem 0.62rem;
        }

        .message-actions {
          flex-wrap: wrap;
          padding-left: 0.35rem;

          .tokens-info {
            white-space: normal;
          }
        }
      }
    }
  }
</style>
