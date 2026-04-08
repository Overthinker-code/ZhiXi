<template>
  <div class="video-page">
    <!-- 主内容区 -->
    <div class="video-main">
      <!-- 左侧：视频播放器 + 时间轴 -->
      <div class="video-left">
        <!-- 播放器 -->
        <div class="player-wrapper">
          <video
            ref="videoEl"
            class="video-player"
            controls
            poster="@/assets/images/AI.jpg"
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onMetaLoaded"
          >
            <source src="" type="video/mp4" />
            您的浏览器不支持视频标签。
          </video>
          <!-- 当前章节覆盖提示 -->
          <transition name="chapter-toast">
            <div v-if="currentChapter" class="chapter-toast">
              <span class="chapter-toast-icon">📌</span>
              {{ currentChapter.title }}
            </div>
          </transition>
        </div>

        <!-- 知识点时间轴 -->
        <div class="timeline-section">
          <div class="timeline-header">
            <span class="timeline-title">内容时段划分</span>
            <span class="timeline-hint">点击知识点可跳转视频时间戳</span>
          </div>

          <!-- 时间轴轨道 -->
          <div class="timeline-track-wrapper">
            <div class="timeline-track" @click="onTrackClick">
              <!-- 进度条 -->
              <div
                class="timeline-progress"
                :style="{ width: progressPercent + '%' }"
              ></div>
              <!-- 章节标记点 -->
              <div
                v-for="chapter in chapters"
                :key="chapter.id"
                class="chapter-marker"
                :class="{ active: chapter.id === currentChapterId }"
                :style="{ left: getChapterPosition(chapter.startTime) + '%' }"
                @click.stop="seekToChapter(chapter)"
              >
                <div class="marker-dot"></div>
                <div class="marker-label">{{ chapter.title }}</div>
              </div>
            </div>
          </div>

          <!-- 重要度ECharts图表 -->
          <div ref="importanceChartRef" class="importance-chart"></div>
        </div>
      </div>

      <!-- 右侧：知识点列表 + AI助手问答 -->
      <div class="video-right">
        <!-- 功能 Tab -->
        <a-tabs v-model:active-key="activeTab" type="rounded" class="right-tabs">
          <!-- 章节导航 -->
          <a-tab-pane key="chapters" title="章节导航">
            <div class="chapter-list">
              <div
                v-for="chapter in chapters"
                :key="chapter.id"
                class="chapter-item"
                :class="{ active: chapter.id === currentChapterId }"
                @click="seekToChapter(chapter)"
              >
                <div class="chapter-time-badge">{{ formatTime(chapter.startTime) }}</div>
                <div class="chapter-meta">
                  <span class="chapter-title-text">{{ chapter.title }}</span>
                  <span class="chapter-desc">{{ chapter.description }}</span>
                </div>
                <icon-right class="chapter-arrow" />
              </div>
            </div>
          </a-tab-pane>

          <!-- AI 上下文问答 -->
          <a-tab-pane key="ai" title="AI伴学">
            <div class="ai-chat-area">
              <!-- 当前上下文提示 -->
              <div class="context-badge" v-if="currentChapter">
                <icon-clock-circle class="ctx-icon" />
                当前位置: {{ currentChapter.title }} · {{ formatTime(currentTime) }}
              </div>

              <!-- 消息列表 -->
              <div class="ai-messages" ref="aiMsgContainer">
                <div
                  v-for="msg in aiMessages"
                  :key="msg.id"
                  class="ai-msg"
                  :class="`ai-msg-${msg.role}`"
                >
                  <div class="msg-avatar">
                    <a-avatar
                      v-if="msg.role === 'assistant'"
                      :size="28"
                      :style="{ backgroundColor: '#165DFF' }"
                    >AI</a-avatar>
                    <a-avatar v-else :size="28" :style="{ backgroundColor: '#7C3AED' }">
                      我
                    </a-avatar>
                  </div>
                  <div class="msg-bubble">
                    <div class="msg-context" v-if="msg.context">
                      <icon-link class="ctx-link-icon" />{{ msg.context }}
                    </div>
                    <div class="msg-content">{{ msg.content }}</div>
                  </div>
                </div>
                <!-- 加载态 -->
                <div v-if="aiLoading" class="ai-msg ai-msg-assistant">
                  <div class="msg-avatar">
                    <a-avatar :size="28" :style="{ backgroundColor: '#165DFF' }">AI</a-avatar>
                  </div>
                  <div class="msg-bubble loading-bubble">
                    <span class="dot-bounce"></span>
                    <span class="dot-bounce" style="animation-delay: 0.15s"></span>
                    <span class="dot-bounce" style="animation-delay: 0.3s"></span>
                  </div>
                </div>
              </div>

              <!-- 输入框 -->
              <div class="ai-input-area">
                <a-textarea
                  v-model="userQuestion"
                  placeholder="基于当前视频时间戳提问..."
                  :auto-size="{ minRows: 2, maxRows: 4 }"
                  :disabled="aiLoading"
                  @keydown.enter.exact.prevent="sendAIQuestion"
                />
                <a-button
                  type="primary"
                  :loading="aiLoading"
                  @click="sendAIQuestion"
                  class="send-btn"
                >
                  发送
                </a-button>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>

    <!-- 底部：课程章节菜单（原有功能保留） -->
    <div class="course-menu">
      <a-menu
        :style="{ width: '250px', height: '100%' }"
        :default-open-keys="['0']"
        :default-selected-keys="['0_1']"
        show-collapse-button
      >
        <a-menu-item key="0_0_0" disabled>人工智能</a-menu-item>
        <a-sub-menu key="0">
          <template #icon><icon-apps></icon-apps></template>
          <template #title>Chapter 1</template>
          <a-menu-item key="0_0" @click="navigateChapter('ch1')">人工智能发展史</a-menu-item>
          <a-menu-item key="0_1" @click="navigateChapter('ch2')">人工智能主要应用领域</a-menu-item>
          <a-menu-item key="0_2" @click="navigateChapter('ch3')">人工智能常见术语</a-menu-item>
        </a-sub-menu>
        <a-sub-menu key="1">
          <template #icon><icon-bug></icon-bug></template>
          <template #title>Chapter 2</template>
          <a-menu-item key="1_0">监督学习与无监督学习</a-menu-item>
          <a-menu-item key="1_1">常见机器学习算法</a-menu-item>
          <a-menu-item key="1_2">模型评估与优化</a-menu-item>
        </a-sub-menu>
        <a-sub-menu key="2">
          <template #icon><icon-bulb></icon-bulb></template>
          <template #title>Chapter 3</template>
          <a-menu-item-group title="神经网络基础">
            <a-menu-item key="2_0">感知机与前馈神经网络</a-menu-item>
            <a-menu-item key="2_1">反向传播算法</a-menu-item>
          </a-menu-item-group>
          <a-menu-item-group title="深度学习应用">
            <a-menu-item key="2_2">卷积神经网络</a-menu-item>
            <a-menu-item key="2_3">循环神经网络</a-menu-item>
          </a-menu-item-group>
        </a-sub-menu>
      </a-menu>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {
    ref,
    computed,
    onMounted,
    onUnmounted,
    nextTick,
    watch,
  } from 'vue';
  import * as echarts from 'echarts';
  import { IconApps, IconBug, IconBulb } from '@arco-design/web-vue/es/icon';

  // ========== 类型定义 ==========
  interface Chapter {
    id: string;
    title: string;
    description: string;
    startTime: number; // 秒
    endTime: number;
    importance: number; // 0-100
  }

  interface AiMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    context?: string;
    timestamp: number;
  }

  // ========== 视频相关 ==========
  const videoEl = ref<HTMLVideoElement | null>(null);
  const currentTime = ref(0);
  const duration = ref(0);

  const progressPercent = computed(() =>
    duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
  );

  function onTimeUpdate() {
    if (videoEl.value) currentTime.value = videoEl.value.currentTime;
  }

  function onMetaLoaded() {
    if (videoEl.value) duration.value = videoEl.value.duration;
  }

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  // ========== 章节数据 ==========
  // TODO: 替换为 GET /api/v1/video/:id/chapters
  const chapters = ref<Chapter[]>([
    { id: 'ch1', title: '开场介绍', description: 'AI发展背景与课程目标', startTime: 0, endTime: 120, importance: 30 },
    { id: 'ch2', title: 'AI发展史', description: '从图灵测试到深度学习', startTime: 120, endTime: 360, importance: 75 },
    { id: 'ch3', title: '核心概念', description: '机器学习、深度学习术语解释', startTime: 360, endTime: 660, importance: 90 },
    { id: 'ch4', title: '应用领域', description: '计算机视觉、NLP、语音识别', startTime: 660, endTime: 900, importance: 85 },
    { id: 'ch5', title: '案例分析', description: '实际产业应用案例讲解', startTime: 900, endTime: 1080, importance: 70 },
    { id: 'ch6', title: '总结回顾', description: '重要知识点梳理与作业说明', startTime: 1080, endTime: 1200, importance: 55 },
  ]);

  const currentChapterId = computed(() => {
    const t = currentTime.value;
    return (
      chapters.value.find((c) => t >= c.startTime && t < c.endTime)?.id || null
    );
  });

  const currentChapter = computed(() =>
    chapters.value.find((c) => c.id === currentChapterId.value) || null
  );

  function getChapterPosition(startTime: number): number {
    if (duration.value <= 0) return (startTime / 1200) * 100;
    return (startTime / duration.value) * 100;
  }

  function seekToChapter(chapter: Chapter) {
    if (videoEl.value) {
      videoEl.value.currentTime = chapter.startTime;
      videoEl.value.play();
      currentTime.value = chapter.startTime;
    }
  }

  function navigateChapter(id: string) {
    const chapter = chapters.value.find((c) => c.id === id);
    if (chapter) seekToChapter(chapter);
  }

  function onTrackClick(e: MouseEvent) {
    const target = e.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const totalDuration = duration.value || 1200;
    const targetTime = ratio * totalDuration;
    if (videoEl.value) {
      videoEl.value.currentTime = targetTime;
      currentTime.value = targetTime;
    }
  }

  // ========== 重要度图表 ==========
  const importanceChartRef = ref<HTMLElement | null>(null);
  let importanceChart: echarts.ECharts | null = null;

  function initImportanceChart() {
    if (!importanceChartRef.value) return;
    importanceChart = echarts.init(importanceChartRef.value);

    const timeLabels = chapters.value.map((c) => formatTime(c.startTime));
    const importanceValues = chapters.value.map((c) => c.importance);

    importanceChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1d1d1f',
        borderColor: 'transparent',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params: any) => {
          const idx = params[0].dataIndex;
          const chapter = chapters.value[idx];
          return `<b>${chapter.title}</b><br/>重要度: ${chapter.importance}%<br/>${chapter.description}`;
        },
        extraCssText: 'border-radius: 8px; padding: 10px 14px;',
      },
      grid: { top: 10, right: 10, bottom: 24, left: 40 },
      xAxis: {
        type: 'category',
        data: timeLabels,
        boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(0,0,0,0.1)' } },
        axisTick: { show: false },
        axisLabel: { color: '#86909c', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%', color: '#86909c', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
      },
      series: [
        {
          name: '重要度',
          type: 'line',
          smooth: 0.4,
          symbol: 'circle',
          symbolSize: 8,
          data: importanceValues,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(22, 93, 255, 0.25)' },
              { offset: 1, color: 'rgba(22, 93, 255, 0.02)' },
            ]),
          },
          itemStyle: { color: '#165DFF', borderWidth: 2, borderColor: '#fff' },
          lineStyle: { width: 2.5, color: '#165DFF' },
          emphasis: {
            scale: 1.4,
            itemStyle: { shadowBlur: 12, shadowColor: 'rgba(22, 93, 255, 0.5)' },
          },
        },
      ],
    });

    // 点击图表跳转章节
    importanceChart.on('click', (params: any) => {
      const chapter = chapters.value[params.dataIndex];
      if (chapter) seekToChapter(chapter);
    });
  }

  // ========== AI伴学 ==========
  const activeTab = ref('chapters');
  const userQuestion = ref('');
  const aiLoading = ref(false);
  const aiMsgContainer = ref<HTMLElement | null>(null);
  const aiMessages = ref<AiMessage[]>([
    {
      id: '0',
      role: 'assistant',
      content: '👋 你好！我是你的AI学习助手。你可以基于当前视频内容向我提问，我会结合视频时间戳为你解答。',
      timestamp: Date.now(),
    },
  ]);

  async function sendAIQuestion() {
    if (!userQuestion.value.trim() || aiLoading.value) return;

    const question = userQuestion.value.trim();
    userQuestion.value = '';

    // 添加用户消息
    aiMessages.value.push({
      id: String(Date.now()),
      role: 'user',
      content: question,
      context: currentChapter.value
        ? `${currentChapter.value.title} · ${formatTime(currentTime.value)}`
        : undefined,
      timestamp: Date.now(),
    });

    await nextTick();
    scrollAiToBottom();

    aiLoading.value = true;
    try {
      // TODO: 调用真实API POST /api/v1/chat/video-context
      // const response = await askWithVideoContext({
      //   videoId: videoId,
      //   timestamp: currentTime.value,
      //   chapterId: currentChapterId.value,
      //   question,
      // });

      // Mock回复
      await new Promise((resolve) => setTimeout(resolve, 1200));
      const mockAnswers: Record<string, string> = {
        default: `关于"${question}"，结合视频 ${formatTime(currentTime.value)} 处的内容：这是${currentChapter.value?.title || '当前章节'}的核心知识点。建议你结合视频反复回顾这个时间段的讲解，加深理解。`,
      };

      aiMessages.value.push({
        id: String(Date.now()),
        role: 'assistant',
        content: mockAnswers.default,
        timestamp: Date.now(),
      });
    } finally {
      aiLoading.value = false;
      await nextTick();
      scrollAiToBottom();
    }
  }

  function scrollAiToBottom() {
    if (aiMsgContainer.value) {
      aiMsgContainer.value.scrollTop = aiMsgContainer.value.scrollHeight;
    }
  }

  const resizeObserver = new ResizeObserver(() => {
    importanceChart?.resize();
  });

  onMounted(() => {
    initImportanceChart();
    if (importanceChartRef.value) resizeObserver.observe(importanceChartRef.value);
  });

  onUnmounted(() => {
    importanceChart?.dispose();
    resizeObserver.disconnect();
  });
</script>

<style scoped lang="less">
  .video-page {
    display: flex;
    flex-direction: column;
    gap: 0;
    width: 100%;
    padding: 0;
    background: var(--color-bg-1);
  }

  // 主内容区
  .video-main {
    display: flex;
    gap: 16px;
    padding: 20px 20px 12px;
    min-height: 0;
  }

  // 左侧
  .video-left {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  // 播放器
  .player-wrapper {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #0a0a0f;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: rgba(0, 0, 0, 0.2) 0 8px 32px;
  }

  .video-player {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  // 当前章节提示
  .chapter-toast {
    position: absolute;
    top: 14px;
    left: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(8px);
    color: #fff;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: -0.1px;
    pointer-events: none;
  }

  .chapter-toast-enter-active,
  .chapter-toast-leave-active {
    transition: all 0.25s ease;
  }

  .chapter-toast-enter-from,
  .chapter-toast-leave-to {
    opacity: 0;
    transform: translateY(-6px);
  }

  // 时间轴区域
  .timeline-section {
    background: var(--color-bg-2);
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid var(--color-border-1);
  }

  .timeline-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .timeline-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--color-text-1);
    letter-spacing: -0.2px;
  }

  .timeline-hint {
    font-size: 12px;
    color: var(--color-text-3);
  }

  // 时间轴轨道
  .timeline-track-wrapper {
    padding: 24px 0 12px;
  }

  .timeline-track {
    position: relative;
    height: 4px;
    background: var(--color-fill-3);
    border-radius: 999px;
    cursor: pointer;

    &:hover {
      background: var(--color-fill-4);
    }
  }

  .timeline-progress {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    background: #165dff;
    border-radius: 999px;
    transition: width 0.5s linear;
    pointer-events: none;
  }

  .chapter-marker {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;
    cursor: pointer;

    &:hover .marker-dot {
      transform: scale(1.5);
      box-shadow: 0 0 0 4px rgba(22, 93, 255, 0.2);
    }

    &.active .marker-dot {
      background: #165dff;
      transform: scale(1.3);
      box-shadow: 0 0 0 4px rgba(22, 93, 255, 0.25);
    }

    &.active .marker-label {
      color: #165dff;
      font-weight: 600;
    }
  }

  .marker-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--color-fill-4);
    border: 2px solid var(--color-bg-2);
    margin: 0 auto;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s;
  }

  .marker-label {
    position: absolute;
    top: 14px;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
    font-size: 11px;
    color: var(--color-text-3);
    pointer-events: none;
    transition: color 0.2s;
    max-width: 80px;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  // 重要度图表
  .importance-chart {
    width: 100%;
    height: 140px;
    margin-top: 8px;
  }

  // 右侧
  .video-right {
    width: 320px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }

  .right-tabs {
    flex: 1;
    height: 100%;

    :deep(.arco-tabs-content) {
      height: calc(100% - 46px);
    }

    :deep(.arco-tabs-pane) {
      height: 100%;
    }
  }

  // 章节列表
  .chapter-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 580px;
    overflow-y: auto;
    padding-right: 4px;

    &::-webkit-scrollbar {
      width: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--color-fill-3);
      border-radius: 999px;
    }
  }

  .chapter-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.1s ease;
    border: 1px solid transparent;

    &:hover {
      background: var(--color-fill-1);
      transform: translateX(2px);
    }

    &.active {
      background: rgba(22, 93, 255, 0.07);
      border-color: rgba(22, 93, 255, 0.2);

      .chapter-title-text {
        color: #165dff;
        font-weight: 600;
      }

      .chapter-time-badge {
        background: #165dff;
        color: #fff;
      }
    }
  }

  .chapter-time-badge {
    flex-shrink: 0;
    padding: 2px 7px;
    background: var(--color-fill-2);
    border-radius: 6px;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-2);
    font-weight: 500;
    transition: background 0.2s, color 0.2s;
  }

  .chapter-meta {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .chapter-title-text {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text-1);
    letter-spacing: -0.1px;
    transition: color 0.2s;
  }

  .chapter-desc {
    font-size: 11px;
    color: var(--color-text-3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .chapter-arrow {
    flex-shrink: 0;
    font-size: 12px;
    color: var(--color-text-4);
  }

  // AI伴学区
  .ai-chat-area {
    display: flex;
    flex-direction: column;
    height: 100%;
    gap: 10px;
  }

  .context-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: rgba(22, 93, 255, 0.07);
    border: 1px solid rgba(22, 93, 255, 0.15);
    border-radius: 8px;
    font-size: 12px;
    color: #165dff;

    .ctx-icon {
      font-size: 13px;
    }
  }

  .ai-messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 360px;
    padding: 4px 2px;

    &::-webkit-scrollbar {
      width: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--color-fill-3);
      border-radius: 999px;
    }
  }

  .ai-msg {
    display: flex;
    gap: 8px;
    align-items: flex-start;

    &.ai-msg-user {
      flex-direction: row-reverse;

      .msg-bubble {
        background: #165dff;
        color: #fff;
        border-radius: 12px 4px 12px 12px;
      }
    }

    &.ai-msg-assistant {
      .msg-bubble {
        background: var(--color-fill-1);
        border-radius: 4px 12px 12px 12px;
      }
    }
  }

  .msg-bubble {
    max-width: 230px;
    padding: 10px 12px;
    font-size: 13px;
    line-height: 1.6;
    letter-spacing: -0.1px;
  }

  .msg-context {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    opacity: 0.6;
    margin-bottom: 4px;

    .ctx-link-icon {
      font-size: 11px;
    }
  }

  .msg-content {
    color: inherit;
  }

  // Loading气泡
  .loading-bubble {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 12px 16px;
    min-width: 60px;
  }

  .dot-bounce {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--color-text-3);
    animation: bounce 0.9s ease-in-out infinite;
  }

  @keyframes bounce {
    0%, 80%, 100% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }

  // AI输入区
  .ai-input-area {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .send-btn {
    align-self: flex-end;
  }

  // 底部菜单
  .course-menu {
    box-sizing: border-box;
    margin-top: 0;
    margin-right: 20px;
    background-color: var(--color-neutral-2);
    padding: 12px 20px;
    border-top: 1px solid var(--color-border-1);
  }
</style>
