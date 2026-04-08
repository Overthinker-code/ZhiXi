<template>
  <a-card class="general-card studio-card" :bordered="false">
    <template #title>
      <a-space :size="10">
        <span>{{ $t('monitor.title.studioPreview') || '课堂直播' }}</span>
        <a-tag color="green" class="live-badge">
          <span class="live-dot"></span> LIVE
        </a-tag>
      </a-space>
    </template>
    <template #extra>
      <a-space :size="8">
        <!-- 行为检测开关 -->
        <a-tooltip :content="detectionEnabled ? '关闭行为检测' : '开启行为检测'">
          <a-switch
            v-model="detectionEnabled"
            size="small"
            :checked-color="'#00b42a'"
            @change="onDetectionChange"
          >
            <template #checked>检测中</template>
            <template #unchecked>已关闭</template>
          </a-switch>
        </a-tooltip>
        <!-- 画质切换 -->
        <a-select
          v-model="quality"
          size="mini"
          style="width: 72px"
          @change="handleQualityChange"
        >
          <a-option value="原画">原画</a-option>
          <a-option value="超清">超清</a-option>
          <a-option value="高清">高清</a-option>
          <a-option value="流畅">流畅</a-option>
        </a-select>
      </a-space>
    </template>

    <!-- 视频播放区域 + Canvas叠加 -->
    <div class="video-wrapper" ref="videoWrapper">
      <!-- 视频元素（HLS / 本地视频） -->
      <video
        ref="videoEl"
        class="video-player"
        :src="streamSrc"
        autoplay
        muted
        playsinline
        @loadedmetadata="onVideoReady"
        @error="onVideoError"
      ></video>

      <!-- 播放器占位（无信号时） -->
      <div v-if="videoError || !streamSrc" class="video-placeholder">
        <div class="placeholder-content">
          <icon-video-camera class="placeholder-icon" />
          <p>暂无视频信号</p>
          <p class="placeholder-sub">等待教师开启直播...</p>
        </div>
      </div>

      <!-- YOLO识别框Canvas叠加层 -->
      <canvas
        ref="yoloCanvas"
        class="yolo-overlay"
        :class="{ active: detectionEnabled }"
      ></canvas>

      <!-- 视频控制栏底部 -->
      <div class="video-controls">
        <a-space :size="12">
          <a-button class="ctrl-btn" size="mini" @click="togglePlay">
            <template #icon>
              <icon-pause v-if="isPlaying" />
              <icon-play-arrow v-else />
            </template>
          </a-button>
          <span class="stream-time">{{ formatDuration(streamDuration) }}</span>
        </a-space>

        <a-space :size="16" class="stream-params">
          <span class="param-item">
            <icon-wifi class="param-icon" />
            {{ streamInfo.bitrate }} Mbps
          </span>
          <span class="param-item">
            <icon-layers class="param-icon" />
            {{ streamInfo.fps }} fps
          </span>
          <span class="param-item cdn-tag">
            CDN: {{ streamInfo.cdn }}
          </span>
        </a-space>
      </div>
    </div>

    <!-- 教师信息栏 -->
    <div class="studio-bar">
      <a-space :size="12">
        <a-avatar :size="28" :style="{ backgroundColor: '#165DFF' }">
          {{ teacherName.charAt(0) }}
        </a-avatar>
        <div class="teacher-meta">
          <span class="teacher-name">{{ teacherName }}</span>
          <span class="teacher-sub">正在授课</span>
        </div>
      </a-space>
      <a-typography-text class="watch-count">
        <icon-eye class="watch-icon" />
        {{ watchCount.toLocaleString() }} 人在线
      </a-typography-text>
    </div>

    <!-- YOLO检测状态提示 -->
    <transition name="detection-toast">
      <div v-if="detectionEnabled" class="detection-status">
        <span class="detection-dot" :class="{ scanning: scanActive }"></span>
        <span>AI行为检测运行中 · 识别到 {{ detectedCount }} 名学生</span>
      </div>
    </transition>
  </a-card>
</template>

<script lang="ts" setup>
  import {
    ref,
    onMounted,
    onUnmounted,
  } from 'vue';
  import { useUserStore } from '@/store';
  import { queryYoloDetections, queryStreamInfo, toggleClassroomDetection } from '@/api/dashboard';

  const userStore = useUserStore();

  // 视频相关
  const videoEl = ref<HTMLVideoElement | null>(null);
  const yoloCanvas = ref<HTMLCanvasElement | null>(null);
  const videoWrapper = ref<HTMLElement | null>(null);
  const isPlaying = ref(false);
  const videoError = ref(false);
  const streamDuration = ref(0);
  const quality = ref('高清');

  // 流信息
  const streamInfo = ref({
    bitrate: '6.0',
    fps: '30',
    cdn: 'KS',
  });

  // 直播地址（后端接口就绪后替换，目前使用空字符串触发占位图）
  // TODO: 接入真实HLS流地址 /api/v1/classroom/stream-info
  const streamSrc = ref('');

  // 教师信息
  const teacherName = userStore.name || '教师';
  const watchCount = ref(36000);

  // YOLO检测
  const detectionEnabled = ref(false);
  const detectedCount = ref(0);
  const scanActive = ref(false);
  let yoloTimer: ReturnType<typeof setInterval> | null = null;
  let durationTimer: ReturnType<typeof setInterval> | null = null;
  let ctx: CanvasRenderingContext2D | null = null;

  // Mock YOLO检测框数据（后端接口就绪后调用 /api/v1/classroom/yolo-detections）
  const mockDetections = [
    { x: 0.05, y: 0.1, w: 0.12, h: 0.25, label: '专注', conf: 0.94 },
    { x: 0.2, y: 0.08, w: 0.11, h: 0.24, label: '专注', conf: 0.91 },
    { x: 0.35, y: 0.12, w: 0.13, h: 0.26, label: '低头', conf: 0.82 },
    { x: 0.52, y: 0.1, w: 0.1, h: 0.23, label: '专注', conf: 0.96 },
    { x: 0.68, y: 0.09, w: 0.12, h: 0.25, label: '侧身', conf: 0.77 },
    { x: 0.82, y: 0.11, w: 0.11, h: 0.24, label: '专注', conf: 0.89 },
  ];

  const labelColors: Record<string, string> = {
    专注: '#00b42a',
    低头: '#ff7d00',
    侧身: '#0091ff',
    睡觉: '#f53f3f',
    玩手机: '#f53f3f',
  };

  function resizeCanvas() {
    if (!yoloCanvas.value || !videoWrapper.value) return;
    const rect = videoWrapper.value.getBoundingClientRect();
    yoloCanvas.value.width = rect.width;
    yoloCanvas.value.height = rect.height;
  }

  function drawYoloBoxes(detections: typeof mockDetections) {
    if (!ctx || !yoloCanvas.value) return;
    const cw = yoloCanvas.value.width;
    const ch = yoloCanvas.value.height;
    ctx.clearRect(0, 0, cw, ch);

    detections.forEach((det) => {
      const x = det.x * cw;
      const y = det.y * ch;
      const w = det.w * cw;
      const h = det.h * ch;
      const color = labelColors[det.label] || '#165DFF';

      // 识别框
      ctx!.strokeStyle = color;
      ctx!.lineWidth = 2;
      ctx!.shadowColor = color;
      ctx!.shadowBlur = 8;
      ctx!.strokeRect(x, y, w, h);
      ctx!.shadowBlur = 0;

      // 角标
      ctx!.fillStyle = color + 'cc';
      ctx!.fillRect(x, y - 20, w, 20);

      // 标签文字
      ctx!.fillStyle = '#ffffff';
      ctx!.font = 'bold 11px SF Pro Text, -apple-system, sans-serif';
      // letterSpacing is not supported on CanvasRenderingContext2D in older TS lib types; omit it.
      ctx!.fillText(
        `${det.label} ${Math.round(det.conf * 100)}%`,
        x + 4,
        y - 6
      );
    });

    detectedCount.value = detections.length;
  }

  function startYoloDetection() {
    if (!yoloCanvas.value) return;
    ctx = yoloCanvas.value.getContext('2d');
    resizeCanvas();
    scanActive.value = true;
    yoloTimer = setInterval(async () => {
      try {
        const { data } = await queryYoloDetections('default_class');
        if (data && data.length > 0) {
          // Normalize to [0...1] mapping assumed by frontend
          const normalized = data.map(d => ({ x: d.x, y: d.y, w: d.width, h: d.height, label: d.label, conf: d.confidence }));
          drawYoloBoxes(normalized);
        } else {
          throw new Error('Fallback');
        }
      } catch {
        // Fallback: 增加随机细微抖动模拟实时预测输出
        const jitter = mockDetections.map((d) => ({
          ...d,
          x: d.x + (Math.random() - 0.5) * 0.005,
          y: d.y + (Math.random() - 0.5) * 0.005,
        }));
        drawYoloBoxes(jitter);
      }
    }, 200);
  }

  function stopYoloDetection() {
    if (yoloTimer) clearInterval(yoloTimer);
    scanActive.value = false;
    if (ctx && yoloCanvas.value) {
      ctx.clearRect(0, 0, yoloCanvas.value.width, yoloCanvas.value.height);
    }
    detectedCount.value = 0;
  }

  function toggleDetection(val: boolean) {
    if (val) {
      startYoloDetection();
    } else {
      stopYoloDetection();
    }
    // TODO: POST /api/v1/classroom/toggle-detection
  }

  function onDetectionChange(val: string | number | boolean) {
    toggleDetection(Boolean(val));
  }

  function togglePlay() {
    if (!videoEl.value) return;
    if (isPlaying.value) {
      videoEl.value.pause();
      isPlaying.value = false;
    } else {
      videoEl.value.play();
      isPlaying.value = true;
    }
  }

  function onVideoReady() {
    isPlaying.value = true;
    videoError.value = false;
    resizeCanvas();
  }

  function onVideoError() {
    videoError.value = true;
    isPlaying.value = false;
  }

  function handleQualityChange(val: string) {
    // TODO: 切换直播线路/清晰度
    streamInfo.value = {
      bitrate: val === '原画' ? '8.0' : val === '超清' ? '6.0' : val === '高清' ? '4.0' : '1.5',
      fps: val === '流畅' ? '24' : '30',
      cdn: 'KS',
    };
  }

  function formatDuration(sec: number): string {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    const pad = (n: number) => String(n).padStart(2, '0');
    return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
  }

  const resizeObserver = new ResizeObserver(() => resizeCanvas());

  onMounted(() => {
    if (videoWrapper.value) {
      resizeObserver.observe(videoWrapper.value);
    }
    durationTimer = setInterval(() => {
      if (isPlaying.value) streamDuration.value++;
    }, 1000);
  });

  onUnmounted(() => {
    resizeObserver.disconnect();
    stopYoloDetection();
    if (durationTimer) clearInterval(durationTimer);
  });
</script>

<style scoped lang="less">
  .studio-card {
    background: var(--color-bg-2);
  }

  .live-badge {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
  }

  .live-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #fff;
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
  }

  // 视频区域
  .video-wrapper {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #0a0a0f;
    border-radius: 8px;
    overflow: hidden;
  }

  .video-player {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .video-placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(145deg, #0f172a 0%, #1e2a45 100%);
    color: rgba(255, 255, 255, 0.4);

    .placeholder-content {
      text-align: center;
    }

    .placeholder-icon {
      font-size: 48px;
      margin-bottom: 12px;
      opacity: 0.3;
      display: block;
    }

    p {
      margin: 4px 0;
      font-size: 15px;
      color: rgba(255, 255, 255, 0.5);
    }

    .placeholder-sub {
      font-size: 12px;
      opacity: 0.5;
    }
  }

  // Canvas叠加
  .yolo-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease;

    &.active {
      opacity: 1;
    }
  }

  // 控制栏
  .video-controls {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    background: linear-gradient(0deg, rgba(0, 0, 0, 0.7) 0%, transparent 100%);
    color: #fff;
  }

  .ctrl-btn {
    border: none;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;

    &:hover {
      background: rgba(255, 255, 255, 0.25);
    }
  }

  .stream-time {
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.5px;
    opacity: 0.9;
  }

  .stream-params {
    font-size: 12px;
    opacity: 0.8;
  }

  .param-item {
    display: flex;
    align-items: center;
    gap: 3px;
    font-variant-numeric: tabular-nums;
  }

  .param-icon {
    font-size: 12px;
  }

  .cdn-tag {
    background: rgba(255, 255, 255, 0.15);
    padding: 1px 6px;
    border-radius: 4px;
  }

  // 教师信息栏
  .studio-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 12px;
    padding: 8px 0;
    border-top: 1px solid var(--color-border-1);
  }

  .teacher-meta {
    display: flex;
    flex-direction: column;
  }

  .teacher-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-1);
    letter-spacing: -0.1px;
  }

  .teacher-sub {
    font-size: 11px;
    color: var(--color-text-3);
  }

  .watch-count {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: var(--color-text-2);
  }

  .watch-icon {
    font-size: 14px;
  }

  // 检测状态条
  .detection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(0, 180, 42, 0.08);
    border: 1px solid rgba(0, 180, 42, 0.2);
    border-radius: 8px;
    font-size: 12px;
    color: #00b42a;
  }

  .detection-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00b42a;

    &.scanning {
      animation: scan-pulse 1s ease-in-out infinite;
    }
  }

  @keyframes scan-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  // 过渡动画
  .detection-toast-enter-active,
  .detection-toast-leave-active {
    transition: all 0.25s ease;
  }

  .detection-toast-enter-from,
  .detection-toast-leave-to {
    opacity: 0;
    transform: translateY(-8px);
  }
</style>
