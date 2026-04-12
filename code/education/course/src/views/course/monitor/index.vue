<template>
  <div class="monitor-hud-scope">
    <Breadcrumb :items="['menu.dashboard', 'menu.dashboard.monitor']" />

    <div class="chat-hero">
      <div class="chat-hero-head">
        <span class="chat-hero-title">{{ $t('monitor.title.chatStrip') }}</span>
        <span class="chat-hero-sub">{{ $t('monitor.subtitle.chatStrip') }}</span>
      </div>
      <ChatPanel />
    </div>

    <MonitorHudCharts />

    <div class="tools-bar">
      <span class="tools-label">{{ $t('monitor.tools.barLabel') }}</span>
      <a-space wrap :size="10">
        <a-button
          v-for="t in toolDefs"
          :key="t.key"
          :type="activeTool === t.key ? 'primary' : 'secondary'"
          @click="onToolClick(t.key)"
        >
          {{ $t(t.localeKey) }}
        </a-button>
      </a-space>
    </div>

    <div class="main-stage">
      <a-space :size="16" direction="vertical" fill>
        <Studio />
        <DataStatistic />
      </a-space>
    </div>

    <MonitorToolFloat v-model="floatOpen" :title="floatTitle">
      <div class="float-inner">
        <StudioStatus v-if="activeTool === 'status'" />
        <AttendanceGrid v-else-if="activeTool === 'attendance'" />
        <BehaviorDetectionPanel
          v-else-if="activeTool === 'behavior'"
          course-id="current-course-id"
        />
        <QuickOperation v-else-if="activeTool === 'quick'" />
        <StudioInformation v-else-if="activeTool === 'info'" />
      </div>
    </MonitorToolFloat>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import ChatPanel from './components/chat-panel.vue';
  import Studio from './components/studio.vue';
  import DataStatistic from './components/data-statistic.vue';
  import StudioStatus from './components/studio-status.vue';
  import AttendanceGrid from './components/attendance-grid.vue';
  import QuickOperation from './components/quick-operation.vue';
  import StudioInformation from './components/studio-information.vue';
  import BehaviorDetectionPanel from './components/behavior-detection-panel.vue';
  import MonitorToolFloat from './components/MonitorToolFloat.vue';
  import MonitorHudCharts from './components/MonitorHudCharts.vue';

  const { t } = useI18n();

  const toolDefs = [
    { key: 'status' as const, localeKey: 'monitor.tools.status' },
    { key: 'attendance' as const, localeKey: 'monitor.tools.attendance' },
    { key: 'behavior' as const, localeKey: 'monitor.tools.behavior' },
    { key: 'quick' as const, localeKey: 'monitor.tools.quick' },
    { key: 'info' as const, localeKey: 'monitor.tools.liveInfo' },
  ];

  type ToolKey = (typeof toolDefs)[number]['key'];

  const activeTool = ref<ToolKey | null>(null);
  const floatOpen = ref(false);

  const floatTitle = computed(() => {
    if (!activeTool.value) return '';
    const hit = toolDefs.find((x) => x.key === activeTool.value);
    return hit ? t(hit.localeKey) : '';
  });

  function onToolClick(key: ToolKey) {
    if (activeTool.value === key && floatOpen.value) {
      floatOpen.value = false;
      activeTool.value = null;
      return;
    }
    activeTool.value = key;
    floatOpen.value = true;
  }

  watch(floatOpen, (open) => {
    if (!open) activeTool.value = null;
  });
</script>

<script lang="ts">
  export default {
    name: 'Monitor',
  };
</script>

<style scoped lang="less">
  /* 敞亮紫蓝教学监控：与全局智屿主题一致，避免整页「暗色 HUD」压抑感 */
  .monitor-hud-scope {
    padding: 0 20px 28px;
    max-width: 1600px;
    margin: 0 auto;
    min-height: calc(100vh - 120px);
    background: linear-gradient(
      180deg,
      #f8fafc 0%,
      #f5f3ff 38%,
      #ecfeff 100%
    );
    color: #0f172a;

    :deep(.arco-breadcrumb-item) {
      color: #64748b;
    }
    :deep(.arco-breadcrumb-item:last-child) {
      color: #312e81;
    }

    :deep(.general-card) {
      background: rgba(255, 255, 255, 0.92) !important;
      border: 1px solid rgba(99, 102, 241, 0.16) !important;
      box-shadow: 0 8px 28px rgba(99, 102, 241, 0.08) !important;
    }

    :deep(.arco-card-header-title) {
      color: #1e293b !important;
    }

    :deep(.arco-typography) {
      color: #475569 !important;
    }

    :deep(.arco-table-th) {
      color: #64748b !important;
      background: rgba(238, 242, 255, 0.65) !important;
    }

    :deep(.arco-table-td) {
      color: #1e293b !important;
      background: transparent !important;
    }

    :deep(.arco-radio-button-content) {
      color: #475569;
    }
  }

  .chat-hero {
    margin-top: 8px;
    margin-bottom: 16px;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.22);
    background: linear-gradient(
      180deg,
      rgba(238, 242, 255, 0.96) 0%,
      #ffffff 52%
    );
    box-shadow: 0 8px 28px rgba(99, 102, 241, 0.12);
    overflow: hidden;
  }

  .chat-hero-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 10px 16px;
    padding: 12px 18px 0;
  }

  .chat-hero-title {
    font-size: 17px;
    font-weight: 700;
    color: #3730a3;
    letter-spacing: 0.02em;
  }

  .chat-hero-sub {
    font-size: 13px;
    color: #64748b;
  }

  .chat-hero :deep(.chat-panel) {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    border-radius: 0;
  }

  .chat-hero :deep(.chat-panel .arco-card-header) {
    display: none;
  }

  .chat-hero :deep(.chat-panel .arco-card-body) {
    padding-top: 4px !important;
  }

  .tools-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 16px;
    margin-bottom: 16px;
    padding: 12px 16px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(99, 102, 241, 0.14);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.06);
  }

  .tools-label {
    font-size: 13px;
    font-weight: 600;
    color: #4338ca;
    margin-right: 4px;
    letter-spacing: 0.02em;
  }

  .main-stage {
    min-height: 420px;
  }

  .float-inner {
    max-width: 100%;
  }

  .float-inner :deep(.general-card) {
    box-shadow: none;
  }
</style>
