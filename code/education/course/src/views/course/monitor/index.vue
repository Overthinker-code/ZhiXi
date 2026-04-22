<template>
  <div class="monitor-immersive">
    <Breadcrumb :items="['menu.dashboard', 'menu.dashboard.monitor']" />

    <div class="monitor-stage-shell">
      <div class="monitor-stage-main" :class="{ 'with-panel': activePanel !== null }">
        <div class="stage-canvas">
          <!-- 教室摄像头/本地摄像头实时画面 -->
          <video
            v-if="videoEnabled"
            ref="mainVideo"
            class="stage-video"
            autoplay
            playsinline
            muted
            crossorigin="anonymous"
            @loadeddata="onMainVideoLoaded"
          ></video>

          <!-- 默认海报图 -->
          <img
            v-else
            class="stage-poster"
            src="http://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/c788fc704d32cf3b1136c7d45afc2669.png~tplv-uwbnlip3yd-webp.webp"
            alt="课堂主舞台"
          />

          <!-- 主舞台检测框 Canvas -->
          <canvas
            v-if="wsState.isDetecting && wsState.persons.length > 0"
            ref="mainCanvas"
            class="stage-detection-canvas"
          ></canvas>

          <!-- WebSocket 错误提示 -->
          <div v-if="wsState.errorMessage" class="stage-error-toast">
            <span class="error-icon">⚠️</span>
            <span class="error-text">{{ wsState.errorMessage }}</span>
          </div>

          <!-- 主舞台评分浮层 -->
          <div v-if="wsState.isDetecting" class="stage-score-overlay">
            <div class="stage-score-badge" style="background-color: #52c41a">
              实时检测中
            </div>
            <div class="stage-score-detail">
              专注: {{ wsState.focusedCount }} ·
              不专注: {{ wsState.unfocusedCount }} ·
              缺席: {{ wsState.absentCount }}
            </div>
          </div>

          <div class="stage-status-bar">
            <div class="status-main">
              <span class="class-name">{{ currentCourse.name }} · 实时课堂</span>
              <span class="time-chip">{{ timerText }}</span>
            </div>
            <a-dropdown trigger="hover" position="br">
              <button type="button" class="network-signal" aria-label="网络状态">
                <span class="signal-dot" />
                <span class="signal-label">稳定</span>
              </button>
              <template #content>
                <div class="net-dropdown">
                  <div>网络质量: 优秀</div>
                  <div>视频码率: 2.8 Mbps</div>
                  <div>视频帧率: 30 FPS</div>
                  <div>端到端延迟: 84 ms</div>
                </div>
              </template>
            </a-dropdown>
          </div>

          <div class="hud-metrics">
            <div class="hud-metric" v-for="item in hudMetrics" :key="item.label">
              <span class="hud-label">{{ item.label }}</span>
              <span class="hud-value">{{ item.value }}</span>
            </div>
          </div>

          <button type="button" class="course-drawer-trigger" @click="courseDrawerOpen = true">
            📚 课程选择
          </button>

          <div class="stage-dock">
            <button
              v-for="item in dockItems"
              :key="item.key"
              type="button"
              class="dock-item"
              :class="{
                active: activePanel === item.panel || item.active,
                'dock-item--brand': item.key === 'ai',
              }"
              @click="onDockClick(item)"
            >
              <span class="dock-icon">{{ item.icon }}</span>
              <span class="dock-text">{{ item.label }}</span>
            </button>
          </div>
        </div>
      </div>

      <aside class="monitor-side-panel" :class="{ open: activePanel !== null }">
        <div class="side-header">
          <h3 class="side-title">{{ panelTitle }}</h3>
          <button type="button" class="close-btn" @click="activePanel = null">✕</button>
        </div>
        <div class="side-body">
          <ChatPanel v-if="activePanel === 'chat'" />
          <AttendanceGrid v-else-if="activePanel === 'signin'" />
          <div
            v-if="activePanel === 'ai' || wsState.isDetecting"
            v-show="activePanel === 'ai'"
            class="ai-panel-wrap"
          >
            <BehaviorDetectionPanel
              :course-id="currentCourse.id"
            />
            <MonitorHudCharts />
          </div>
          <div v-else-if="activePanel === 'setting'" class="settings-panel">
            <div class="settings-group" v-for="group in meetingSettings" :key="group.title">
              <h4>{{ group.title }}</h4>
              <a-checkbox-group direction="vertical" v-model="group.checked">
                <a-checkbox v-for="opt in group.options" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </a-checkbox>
              </a-checkbox-group>
            </div>
          </div>
          <div v-else class="panel-empty">请选择下方功能进入对应面板</div>
        </div>
      </aside>
    </div>

    <!-- 视频源选择弹窗 -->
    <a-modal
      v-model:visible="videoSourceModalVisible"
      :footer="false"
      :title="videoSourceStep === 'source' ? '选择视频源' : '选择教室课堂'"
      :mask-closable="true"
      :unmount-on-close="true"
      @cancel="videoSourceModalVisible = false"
    >
      <div v-if="videoSourceStep === 'source'" class="source-select">
        <a-button
          size="large"
          type="primary"
          style="width: 100%; margin-bottom: 12px;"
          @click="onSelectLocalCamera"
        >
          🎥 本地摄像头
        </a-button>
        <a-button
          size="large"
          type="outline"
          style="width: 100%;"
          @click="videoSourceStep = 'classroom'"
        >
          🏫 远程摄像头
        </a-button>
      </div>

      <div v-else class="classroom-select">
        <div class="course-list-modal">
          <button
            v-for="c in monitorCourses"
            :key="c.id"
            type="button"
            class="course-item"
            @click="onSelectClassroomCamera(c)"
          >
            <img :src="c.cover" :alt="c.name" class="course-cover" />
            <div class="course-meta">
              <div class="course-name">{{ c.name }}</div>
              <div class="course-sub">{{ c.subtitle }}</div>
            </div>
          </button>
        </div>
        <a-button type="text" long style="margin-top: 10px;" @click="videoSourceStep = 'source'">
          ← 返回上一步
        </a-button>
      </div>
    </a-modal>

    <a-drawer
      :visible="courseDrawerOpen"
      :width="330"
      placement="left"
      unmount-on-close
      :footer="false"
      @cancel="courseDrawerOpen = false"
    >
      <template #title>课程实时课堂选择</template>
      <div class="course-list">
        <button
          v-for="c in monitorCourses"
          :key="c.id"
          type="button"
          class="course-item"
          :class="{ active: currentCourse.id === c.id }"
          @click="selectCourse(c)"
        >
          <img :src="c.cover" :alt="c.name" class="course-cover" />
          <div class="course-meta">
            <div class="course-name">{{ c.name }}</div>
            <div class="course-sub">{{ c.subtitle }}</div>
          </div>
        </button>
      </div>
    </a-drawer>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, onUnmounted, reactive, ref, watch, nextTick } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import ChatPanel from './components/chat-panel.vue';
  import AttendanceGrid from './components/attendance-grid.vue';
  import MonitorHudCharts from './components/MonitorHudCharts.vue';
  import BehaviorDetectionPanel from './components/behavior-detection-panel.vue';
  import AIImg from '@/assets/images/AI.jpg';
  import DatabaseImg from '@/assets/images/数据库图片.png';
  import DatastructureImg from '@/assets/images/数据结构.jpg';
  import EcoImg from '@/assets/images/宏观经济学.jpg';
  import { getClassroomCameras, getBehaviorDefinitions } from '@/api/behavior-analysis';
  import { useBehaviorWebSocket } from '@/composables/useBehaviorWebSocket';
  import type { BehaviorStatus } from '@/api/behavior-analysis-ws';

  type PanelKey = 'chat' | 'signin' | 'ai' | 'setting' | null;

  const activePanel = ref<PanelKey>(null);
  const elapsedSeconds = ref(0);
  const courseDrawerOpen = ref(false);
  let timer: ReturnType<typeof setInterval> | null = null;

  const mainVideo = ref<HTMLVideoElement | null>(null);
  const mainCanvas = ref<HTMLCanvasElement | null>(null);
  const captureCanvas = document.createElement('canvas');

  // WebSocket 实时检测（由主舞台直接管理，侧边栏只负责上传分析）
  const ws = useBehaviorWebSocket();
  const { state: wsState, getStatusColor } = ws;

  // 视频源弹窗
  const videoSourceModalVisible = ref(false);
  const videoSourceStep = ref<'source' | 'classroom'>('source');

  // 摄像头
  const videoEnabled = ref(false);
  const mediaStream = ref<MediaStream | null>(null);



  // ===========================================================================
  // 【课堂列表配置区】仅配置前端展示用的课堂信息，远程摄像头 URL 不再在前端硬编码
  // 摄像头地址统一从后端 /api/behavior/cameras 读取，如需修改请编辑：
  // code/backend/app/api/routes/behavior_analysis.py -> get_classroom_cameras()
  // ===========================================================================
  const monitorCourses = [
    {
      id: 'db',
      name: '数据库原理',
      subtitle: 'SQL 与关系模型',
      cover: DatabaseImg,
    },
    {
      id: 'ds',
      name: '数据结构',
      subtitle: '线性表与树图',
      cover: DatastructureImg,
    },
    {
      id: 'ai',
      name: '人工智能导论',
      subtitle: 'AI 概念与应用',
      cover: AIImg,
    },
    {
      id: 'eco',
      name: '宏观经济学',
      subtitle: '经济周期与政策',
      cover: EcoImg,
    },
  ];

  const cameraUrlMap = ref<Record<string, string>>({});
  const behaviorDefinitions = ref<any>(null);

  const currentCourse = ref(monitorCourses[0]);

  const meetingSettings = reactive([
    {
      title: '常规设置',
      options: [
        { value: 'autoCamera', label: '入课开启摄像头' },
        { value: 'autoMic', label: '入课开启麦克风' },
        { value: 'speakerMark', label: '显示当前说话者' },
        { value: 'showDuration', label: '显示参会时长' },
      ],
      checked: ['autoMic', 'speakerMark', 'showDuration'],
    },
    {
      title: '通知与体验',
      options: [
        { value: 'desktopNotice', label: '接收桌面通知' },
        { value: 'shrinkFloat', label: '遮挡时自动进入缩略浮窗' },
        { value: 'lockKeep', label: '锁屏时不退出课堂' },
      ],
      checked: ['desktopNotice', 'shrinkFloat'],
    },
  ]);

  const dockItems = computed(() => [
    {
      key: 'video',
      icon: '🎥',
      label: videoEnabled.value ? '关闭视频' : '开启视频',
      panel: null as PanelKey,
      active: videoEnabled.value,
    },
    { key: 'mic', icon: '🎙️', label: '开启静音', panel: null as PanelKey },
    { key: 'chat', icon: '💬', label: '师生聊天', panel: 'chat' as PanelKey },
    { key: 'signin', icon: '🧾', label: '课堂签到', panel: 'signin' as PanelKey },
    { key: 'ai', icon: '🤖', label: 'AI 行为检测', panel: 'ai' as PanelKey },
    { key: 'setting', icon: '⚙️', label: '直播设置', panel: 'setting' as PanelKey },
  ]);

  const timerText = computed(() => {
    const m = Math.floor(elapsedSeconds.value / 60)
      .toString()
      .padStart(2, '0');
    const s = (elapsedSeconds.value % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  });

  const panelTitle = computed(() => {
    if (activePanel.value === 'chat') return '师生聊天';
    if (activePanel.value === 'signin') return '课堂签到';
    if (activePanel.value === 'ai') return 'AI 行为检测';
    if (activePanel.value === 'setting') return '直播设置';
    return '功能面板';
  });

  const hudMetrics = computed(() => [
    { label: '在线学生', value: `${wsState.value.persons.length || 0} 人` },
    {
      label: '专注指数',
      value: `${wsState.value.persons.length > 0
        ? Math.round((wsState.value.focusedCount / wsState.value.persons.length) * 100)
        : 0}%`,
    },
    { label: '智屿预警', value: wsState.value.isDetecting ? '实时开启' : '待机中' },
  ]);

  const onDockClick = async (item: typeof dockItems.value[number]) => {
    if (item.key === 'video') {
      if (videoEnabled.value) {
        stopCamera();
        Message.success('视频已关闭');
      } else {
        // 弹出视频源选择
        videoSourceStep.value = 'source';
        videoSourceModalVisible.value = true;
      }
      return;
    }
    if (!item.panel) {
      Message.info(`${item.label} 功能已接入中`);
      return;
    }
    activePanel.value = activePanel.value === item.panel ? null : item.panel;
  };

  // 选择本地摄像头
  const onSelectLocalCamera = async () => {
    videoSourceModalVisible.value = false;
    await startCamera('local');
  };

  // 选择远程摄像头（教室）
  const onSelectClassroomCamera = async (course: typeof monitorCourses[number]) => {
    const url = cameraUrlMap.value[course.id];
    if (!url) {
      Message.error('未获取到该教室的摄像头地址，请检查网络或后端配置');
      return;
    }
    currentCourse.value = course;
    videoSourceModalVisible.value = false;
    await startCamera('classroom', url);
  };

  // 开启摄像头（本地 or 教室流）
  const startCamera = async (source: 'local' | 'classroom', url?: string) => {
    if (source === 'classroom' && url) {
      videoEnabled.value = true;
      await nextTick();
      if (mainVideo.value) {
        mainVideo.value.srcObject = null;
        mainVideo.value.src = url;
        try {
          await mainVideo.value.play();
          Message.success(`已连接到《${currentCourse.value.name}》教室摄像头，自动开始行为分析`);
          ws.startDetection(currentCourse.value.id, getMainStageFrame, 500);
        } catch (e: any) {
          Message.error('教室摄像头连接失败，请检查地址是否可播放');
          videoEnabled.value = false;
        }
      }
      return;
    }

    // 本地摄像头模式
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      mediaStream.value = stream;
      videoEnabled.value = true;
      await nextTick();
      if (mainVideo.value) {
        mainVideo.value.src = '';
        mainVideo.value.srcObject = stream;
        try { await mainVideo.value.play(); } catch (e) { /* ignore */ }
      }
      Message.success('本地摄像头已开启，自动开始行为分析');
      ws.startDetection(currentCourse.value.id, getMainStageFrame, 500);
    } catch (error: any) {
      if (error.name === 'NotAllowedError') {
        Message.error('摄像头权限被拒绝');
      } else if (error.name === 'NotFoundError') {
        Message.error('未找到摄像头设备');
      } else {
        Message.error('开启视频失败: ' + (error.message || '未知错误'));
      }
    }
  };

  // 关闭摄像头
  const stopCamera = () => {
    videoEnabled.value = false;
    // 显式停止 WebSocket 检测，确保关闭视频时大屏检测同步停止
    ws.stopDetection();
    if (mediaStream.value) {
      mediaStream.value.getTracks().forEach((track) => track.stop());
      mediaStream.value = null;
    }
    if (mainVideo.value) {
      mainVideo.value.pause();
      mainVideo.value.srcObject = null;
      mainVideo.value.src = '';
    }
  };

  // 从主舞台视频捕获当前帧并转为 base64（供 WebSocket 发送）
  const getMainStageFrame = (): string | null => {
    const video = mainVideo.value;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) return null;

    captureCanvas.width = video.videoWidth;
    captureCanvas.height = video.videoHeight;
    const ctx = captureCanvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
    return captureCanvas.toDataURL('image/jpeg', 0.8);
  };

  // 状态标签
  const statusLabel = (status: BehaviorStatus) => {
    const map: Record<BehaviorStatus, string> = {
      focused: '专注',
      unfocused: '不专注',
      absent: '缺席',
    };
    return map[status] || status;
  };

  // 在主舞台 Canvas 上绘制检测框（适配 WebSocket 新格式）
  const drawMainStageBoxes = () => {
    if (!mainCanvas.value || !mainVideo.value || wsState.value.persons.length === 0) return;

    const canvas = mainCanvas.value;
    const video = mainVideo.value;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = video.getBoundingClientRect();
    const parentRect = video.parentElement!.getBoundingClientRect();
    const videoScale = Math.min(parentRect.width / video.videoWidth, parentRect.height / video.videoHeight);
    const displayWidth = video.videoWidth * videoScale;
    const displayHeight = video.videoHeight * videoScale;
    const offsetX = (parentRect.width - displayWidth) / 2;
    const offsetY = (parentRect.height - displayHeight) / 2;

    canvas.width = parentRect.width;
    canvas.height = parentRect.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const imgWidth = video.videoWidth;
    const imgHeight = video.videoHeight;
    const scaleX = displayWidth / imgWidth;
    const scaleY = displayHeight / imgHeight;

    wsState.value.persons.forEach((person) => {
      const [x1, y1, x2, y2] = person.bbox;
      const sx1 = offsetX + x1 * scaleX;
      const sy1 = offsetY + y1 * scaleY;
      const sx2 = offsetX + x2 * scaleX;
      const sy2 = offsetY + y2 * scaleY;
      const width = sx2 - sx1;
      const height = sy2 - sy1;

      const color = getStatusColor(person.status);

      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(sx1, sy1, width, height);

      const label = `${person.track_id} ${statusLabel(person.status)} ${person.score.toFixed(2)}`;
      ctx.font = 'bold 14px Arial';
      const textWidth = ctx.measureText(label).width;
      const textHeight = 20;

      ctx.fillStyle = color;
      ctx.fillRect(sx1, sy1 - textHeight - 4, textWidth + 10, textHeight + 4);

      ctx.fillStyle = '#fff';
      ctx.fillText(label, sx1 + 5, sy1 - 4);
    });
  };

  // 监听 persons 变化自动重绘
  watch(
    () => wsState.value.persons,
    () => {
      if (wsState.value.isDetecting) {
        nextTick(() => drawMainStageBoxes());
      }
    },
    { deep: true }
  );

  // 窗口变化时重绘
  const onResize = () => {
    if (wsState.value.isDetecting) {
      drawMainStageBoxes();
    }
  };

  const selectCourse = (course: (typeof monitorCourses)[number]) => {
    currentCourse.value = course;
    courseDrawerOpen.value = false;
    Message.success(`已切换到《${course.name}》实时课堂`);
  };

  onMounted(() => {
    timer = setInterval(() => {
      elapsedSeconds.value += 1;
    }, 1000);
    window.addEventListener('resize', onResize);

    // 远程摄像头地址统一从后端读取，修改请编辑后端 behavior_analysis.py 的 /cameras 接口
    getClassroomCameras()
      .then((res) => {
        const cameras = res.data?.cameras || [];
        const map: Record<string, string> = {};
        cameras.forEach((item: any) => {
          if (item.id && item.cameraUrl) map[item.id] = item.cameraUrl;
        });
        cameraUrlMap.value = map;
      })
      .catch(() => {
        Message.warning('获取教室摄像头配置失败，请检查后端服务');
      });

    getBehaviorDefinitions()
      .then((res) => {
        behaviorDefinitions.value = res.data;
      })
      .catch(() => {
        // 静默失败，getScoreColor 会使用默认兜底颜色
      });
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
    window.removeEventListener('resize', onResize);
    stopCamera();
  });
</script>

<script lang="ts">
  export default {
    name: 'Monitor',
  };
</script>

<style scoped lang="less">
  .monitor-immersive {
    padding: 0 16px 16px;
    min-height: calc(100vh - 96px);
    background: #020617;

    :deep(.arco-breadcrumb-item) {
      color: #94a3b8;
    }
    :deep(.arco-breadcrumb-item:last-child) {
      color: #e2e8f0;
    }
  }

  .monitor-stage-shell {
    margin-top: 10px;
    display: flex;
    gap: 0;
    height: calc(100vh - 150px);
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid rgba(56, 189, 248, 0.24);
    background: #0f172a;
    box-shadow:
      0 20px 45px rgba(2, 6, 23, 0.65),
      inset 0 0 0 1px rgba(99, 102, 241, 0.08);
  }

  .monitor-stage-main {
    flex: 1;
    min-width: 0;
    transition: width 0.3s ease;
    &.with-panel {
      width: calc(100% - 350px);
    }
  }

  .stage-canvas {
    position: relative;
    width: 100%;
    height: 100%;
    background: #0f172a;
    display: flex;
    justify-content: center;
    align-items: center;
    overflow: hidden;
    &::before {
      content: '';
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 14% 8%, rgba(56, 189, 248, 0.18), transparent 34%),
        radial-gradient(circle at 88% 16%, rgba(99, 102, 241, 0.2), transparent 32%);
      z-index: 1;
    }
  }

  .stage-poster {
    width: min(100%, 1280px);
    height: 100%;
    object-fit: cover;
    filter: saturate(0.98) contrast(1.04);
  }

  .stage-video {
    width: min(100%, 1280px);
    height: 100%;
    object-fit: contain;
    background: #000;
  }

  .stage-detection-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 3;
  }

  .stage-error-toast {
    position: absolute;
    top: 72px;
    left: 16px;
    z-index: 7;
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(245, 34, 45, 0.85);
    color: #fff;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 13px;
    backdrop-filter: blur(4px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);

    .error-icon {
      font-size: 14px;
    }

    .error-text {
      max-width: 260px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .stage-score-overlay {
    position: absolute;
    top: 72px;
    left: 16px;
    z-index: 5;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .stage-score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
    color: #fff;
    backdrop-filter: blur(4px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  }

  .stage-score-detail {
    font-size: 12px;
    color: #e2e8f0;
    background: rgba(15, 23, 42, 0.6);
    padding: 4px 10px;
    border-radius: 999px;
    backdrop-filter: blur(4px);
    width: fit-content;
  }

  .stage-status-bar {
    position: absolute;
    top: 16px;
    left: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.26);
    border-radius: 999px;
    padding: 8px 12px;
    backdrop-filter: blur(8px);
    z-index: 6;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.45);
  }

  .hud-metrics {
    position: absolute;
    top: 64px;
    right: 18px;
    z-index: 6;
    display: flex;
    gap: 10px;
  }

  .hud-metric {
    min-width: 112px;
    padding: 8px 10px;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    background: rgba(2, 6, 23, 0.56);
    backdrop-filter: blur(10px);
    display: flex;
    flex-direction: column;
    gap: 3px;
    box-shadow: 0 8px 24px rgba(2, 6, 23, 0.45);
  }

  .hud-label {
    font-size: 11px;
    color: #94a3b8;
    letter-spacing: 0.04em;
  }

  .hud-value {
    font-size: 14px;
    color: #e2e8f0;
    font-weight: 700;
  }

  .status-main {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e2e8f0;
  }

  .class-name {
    font-size: 13px;
    font-weight: 600;
  }

  .time-chip {
    font-size: 12px;
    color: #a5b4fc;
  }

  .network-signal {
    height: 24px;
    border: 0;
    border-radius: 999px;
    background: rgba(2, 6, 23, 0.5);
    color: #86efac;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0 8px;
    cursor: pointer;
  }

  .signal-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
  }

  .signal-label {
    font-size: 11px;
    color: #bbf7d0;
  }

  .net-dropdown {
    padding: 8px 10px;
    line-height: 1.7;
    font-size: 12px;
    color: #334155;
  }

  .course-drawer-trigger {
    position: absolute;
    left: 16px;
    bottom: 22px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    background: rgba(15, 23, 42, 0.68);
    color: #e2e8f0;
    backdrop-filter: blur(10px);
    border-radius: 10px;
    height: 34px;
    padding: 0 10px;
    cursor: pointer;
    z-index: 5;
  }

  .stage-dock {
    position: absolute;
    left: 50%;
    bottom: 14px;
    transform: translateX(-50%);
    height: 70px;
    border-radius: 16px;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    backdrop-filter: blur(15px);
    background: rgba(2, 6, 23, 0.62);
    border: 1px solid rgba(56, 189, 248, 0.32);
    z-index: 5;
    box-shadow:
      0 20px 40px rgba(2, 6, 23, 0.58),
      inset 0 0 28px rgba(56, 189, 248, 0.08);
  }

  .dock-item {
    width: 84px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: #cbd5e1;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 6px 4px;
    transition: all 0.2s ease;

    &:hover,
    &.active {
      background: rgba(148, 163, 184, 0.18);
      color: #fff;
    }
  }

  .dock-icon {
    font-size: 18px;
    line-height: 1;
  }

  .dock-text {
    font-size: 12px;
    line-height: 1.2;
  }

  .dock-item--brand {
    position: relative;
    color: #fff;
    background: linear-gradient(
      135deg,
      var(--zy-color-brand, #6366f1),
      var(--zy-color-ocean, #22d3ee)
    );
    box-shadow: 0 10px 22px rgba(99, 102, 241, 0.32);
  }

  .monitor-side-panel {
    width: 0;
    flex-shrink: 0;
    background: linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
    border-left: 1px solid rgba(56, 189, 248, 0.26);
    overflow: hidden;
    transition: width 0.3s ease;
    display: flex;
    flex-direction: column;
    &.open {
      width: 350px;
    }
  }

  .side-header {
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 14px;
    border-bottom: 1px solid rgba(56, 189, 248, 0.2);
  }

  .side-title {
    margin: 0;
    font-size: 14px;
    color: #e2e8f0;
  }

  .close-btn {
    border: 0;
    background: transparent;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    cursor: pointer;
    color: #94a3b8;
    &:hover {
      background: rgba(99, 102, 241, 0.18);
      color: #fff;
    }
  }

  .side-body {
    flex: 1;
    min-height: 0;
    padding: 10px;
    background: transparent;
    overflow: auto;
    :deep(.general-card) {
      margin: 0;
    }
  }

  .ai-panel-wrap {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .settings-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 4px 2px;
  }

  .settings-group {
    border-radius: 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    transition: all 0.3s ease;

    &:hover {
      border-color: #cbd5e1;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }

    h4 {
      margin: 0 0 12px;
      color: #1e293b;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    :deep(.arco-checkbox) {
      color: #334155;
      font-size: 13px;
      margin-bottom: 8px;
      transition: color 0.2s ease;

      &:hover {
        color: #0f172a;
      }

      .arco-checkbox-icon {
        border-color: #94a3b8;
      }

      .arco-checkbox-text {
        color: #334155;
      }

      &.arco-checkbox-checked {
        color: #0f172a;

        .arco-checkbox-icon {
          background-color: #3b82f6;
          border-color: #3b82f6;
        }

        .arco-checkbox-text {
          color: #0f172a;
        }
      }
    }
  }

  .panel-empty {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 13px;
  }

  .course-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .course-item {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid rgba(56, 189, 248, 0.2);
    background: rgba(15, 23, 42, 0.45);
    border-radius: 10px;
    padding: 8px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
    &.active,
    &:hover {
      border-color: rgba(99, 102, 241, 0.45);
      box-shadow: 0 8px 18px rgba(99, 102, 241, 0.12);
    }
  }

  .course-cover {
    width: 70px;
    height: 48px;
    border-radius: 8px;
    object-fit: cover;
    flex-shrink: 0;
  }

  .course-meta {
    min-width: 0;
  }

  .course-name {
    font-size: 13px;
    color: #e2e8f0;
    font-weight: 600;
  }

  .course-sub {
    margin-top: 4px;
    font-size: 12px;
    color: #94a3b8;
  }

  @media (max-width: 1280px) {
    .hud-metrics {
      display: none;
    }
  }

  .source-select {
    padding: 8px 0;
  }

  .classroom-select {
    padding: 4px 0;
  }

  .course-list-modal {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 320px;
    overflow-y: auto;
  }
</style>
