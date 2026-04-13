<template>
  <div class="monitor-immersive">
    <Breadcrumb :items="['menu.dashboard', 'menu.dashboard.monitor']" />

    <div class="monitor-stage-shell">
      <div class="monitor-stage-main" :class="{ 'with-panel': activePanel !== null }">
        <div class="stage-canvas">
          <img
            class="stage-poster"
            src="http://p1-arco.byteimg.com/tos-cn-i-uwbnlip3yd/c788fc704d32cf3b1136c7d45afc2669.png~tplv-uwbnlip3yd-webp.webp"
            alt="课堂主舞台"
          />

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
                active: activePanel === item.panel,
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
          <div v-else-if="activePanel === 'ai'" class="ai-panel-wrap">
            <BehaviorDetectionPanel :course-id="currentCourse.id" />
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
  import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import ChatPanel from './components/chat-panel.vue';
  import AttendanceGrid from './components/attendance-grid.vue';
  import MonitorHudCharts from './components/MonitorHudCharts.vue';
  import BehaviorDetectionPanel from './components/behavior-detection-panel.vue';
  import AIImg from '@/assets/images/AI.jpg';
  import DatabaseImg from '@/assets/images/数据库图片.png';
  import DatastructureImg from '@/assets/images/数据结构.jpg';
  import EcoImg from '@/assets/images/宏观经济学.jpg';

  type PanelKey = 'chat' | 'signin' | 'ai' | 'setting' | null;

  const activePanel = ref<PanelKey>(null);
  const elapsedSeconds = ref(0);
  const courseDrawerOpen = ref(false);
  let timer: ReturnType<typeof setInterval> | null = null;

  const monitorCourses = [
    { id: 'db', name: '数据库原理', subtitle: 'SQL 与关系模型', cover: DatabaseImg },
    { id: 'ds', name: '数据结构', subtitle: '线性表与树图', cover: DatastructureImg },
    { id: 'ai', name: '人工智能导论', subtitle: 'AI 概念与应用', cover: AIImg },
    { id: 'eco', name: '宏观经济学', subtitle: '经济周期与政策', cover: EcoImg },
  ];

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

  const dockItems = [
    { key: 'video', icon: '🎥', label: '开启视频', panel: null as PanelKey },
    { key: 'mic', icon: '🎙️', label: '开启静音', panel: null as PanelKey },
    { key: 'chat', icon: '💬', label: '师生聊天', panel: 'chat' as PanelKey },
    { key: 'signin', icon: '🧾', label: '课堂签到', panel: 'signin' as PanelKey },
    { key: 'ai', icon: '🤖', label: 'AI 行为检测', panel: 'ai' as PanelKey },
    { key: 'setting', icon: '⚙️', label: '直播设置', panel: 'setting' as PanelKey },
  ];

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

  const onDockClick = (item: (typeof dockItems)[number]) => {
    if (!item.panel) {
      Message.info(`${item.label} 功能已接入中`);
      return;
    }
    activePanel.value = activePanel.value === item.panel ? null : item.panel;
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
  });

  onUnmounted(() => {
    if (timer) clearInterval(timer);
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
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: #0f172a;
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
  }

  .stage-poster {
    width: min(100%, 1280px);
    height: 100%;
    object-fit: cover;
    filter: saturate(0.98) contrast(1.04);
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
    z-index: 4;
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
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.25);
    z-index: 5;
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
    background: #ffffff;
    border-left: 1px solid rgba(15, 23, 42, 0.08);
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
    border-bottom: 1px solid #e2e8f0;
  }

  .side-title {
    margin: 0;
    font-size: 14px;
    color: #0f172a;
  }

  .close-btn {
    border: 0;
    background: transparent;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    cursor: pointer;
    color: #475569;
    &:hover {
      background: #f1f5f9;
    }
  }

  .side-body {
    flex: 1;
    min-height: 0;
    padding: 10px;
    background: #f8fafc;
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
    gap: 12px;
  }

  .settings-group {
    border-radius: 10px;
    background: #fff;
    border: 1px solid #e2e8f0;
    padding: 10px 12px;
    h4 {
      margin: 0 0 8px;
      color: #0f172a;
      font-size: 13px;
    }
  }

  .panel-empty {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #64748b;
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
    border: 1px solid #e2e8f0;
    background: #fff;
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
    color: #0f172a;
    font-weight: 600;
  }

  .course-sub {
    margin-top: 4px;
    font-size: 12px;
    color: #64748b;
  }
</style>
