import { computed, onBeforeUnmount, ref } from 'vue';
import {
  type DigitalHumanJobStatus,
  queryDigitalHumanJobStatus,
} from '@/api/digital-human';

type StageState = 'pending' | 'active' | 'completed' | 'error';

interface StageDefinition {
  key: string;
  label: string;
  stages: string[];
}

interface StageItem {
  key: string;
  label: string;
  state: StageState;
}

const stageDefinitions: StageDefinition[] = [
  { key: 'queued', label: '任务排队', stages: ['idle', 'queued'] },
  { key: 'prepare', label: '脚本准备', stages: ['prepare'] },
  { key: 'tts', label: '语音合成', stages: ['tts'] },
  {
    key: 'render',
    label: '数字人渲染',
    stages: [
      'musetalk_prepare',
      'musetalk',
      'musetalk_extract_frames',
      'musetalk_audio_features',
      'musetalk_landmarks',
      'musetalk_latents',
      'musetalk_inference',
      'musetalk_compositing',
      'wav2lip',
    ],
  },
  {
    key: 'deliver',
    label: '成片输出',
    stages: ['musetalk_encode_video', 'musetalk_mux_audio', 'done', 'failed'],
  },
];

function normalizeProgressValue(
  value: unknown,
  status: DigitalHumanJobStatus['status']
): number {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) {
    return status === 'success' ? 100 : 0;
  }

  let normalized = numeric;
  if (normalized > 0 && normalized <= 1) {
    normalized *= 100;
  } else if (
    normalized > 100 &&
    normalized <= 10000 &&
    normalized % 100 === 0
  ) {
    normalized /= 100;
  }

  normalized = Math.round(normalized);
  normalized = Math.max(0, Math.min(normalized, 100));

  if (status === 'success') return 100;
  return normalized;
}

function normalizeJobStatus(
  data: DigitalHumanJobStatus
): DigitalHumanJobStatus {
  const stage = data.stage || (data.status === 'pending' ? 'queued' : 'idle');
  let { message } = data;
  if (!message) {
    if (data.status === 'success') {
      message = '渲染完成';
    } else if (data.status === 'failed') {
      message = '渲染失败';
    } else {
      message = '渲染处理中';
    }
  }

  return {
    ...data,
    stage,
    message,
    progress: normalizeProgressValue(data.progress, data.status),
  };
}

function resolveStageIndex(
  stage: string,
  status: DigitalHumanJobStatus['status']
) {
  if (status === 'success') return stageDefinitions.length - 1;
  const index = stageDefinitions.findIndex((item) =>
    item.stages.includes(stage)
  );
  if (index >= 0) return index;
  if (status === 'failed') return stageDefinitions.length - 1;
  return 0;
}

export default function useDigitalHumanJob() {
  const activeTaskId = ref('');
  const status = ref<DigitalHumanJobStatus>(
    normalizeJobStatus({
      status: 'pending',
      progress: 0,
      message: '等待任务开始',
      stage: 'idle',
    })
  );
  const displayProgress = ref(0);
  const isPolling = ref(false);
  let timer: ReturnType<typeof window.setTimeout> | null = null;
  let progressFrame: number | null = null;
  let settle: ((value: DigitalHumanJobStatus) => void) | null = null;

  const stopProgressAnimation = () => {
    if (progressFrame !== null) {
      window.cancelAnimationFrame(progressFrame);
      progressFrame = null;
    }
  };

  const animateProgress = (target: number, immediate = false) => {
    stopProgressAnimation();
    const safeTarget = Math.max(0, Math.min(Math.round(target), 100));
    if (immediate || Math.abs(safeTarget - displayProgress.value) < 1) {
      displayProgress.value = safeTarget;
      return;
    }

    const startValue = displayProgress.value;
    const delta = safeTarget - startValue;
    const duration = Math.min(800, Math.max(260, Math.abs(delta) * 22));
    const startAt = performance.now();

    const step = (now: number) => {
      const progress = Math.min((now - startAt) / duration, 1);
      displayProgress.value = Math.round(startValue + delta * progress);
      if (progress < 1) {
        progressFrame = window.requestAnimationFrame(step);
      } else {
        progressFrame = null;
      }
    };

    progressFrame = window.requestAnimationFrame(step);
  };

  const syncStatus = (nextStatus: DigitalHumanJobStatus, immediate = false) => {
    const normalized = normalizeJobStatus(nextStatus);
    status.value = normalized;
    animateProgress(
      normalized.progress,
      immediate || normalized.status !== 'processing'
    );
    return normalized;
  };

  const stopPolling = () => {
    isPolling.value = false;
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
  };

  const pollOnce = async () => {
    if (!activeTaskId.value) return;
    const data = syncStatus(
      await queryDigitalHumanJobStatus(activeTaskId.value)
    );
    if (data.status === 'success' || data.status === 'failed') {
      stopPolling();
      if (settle) {
        settle(data);
        settle = null;
      }
      return;
    }
    timer = window.setTimeout(() => {
      pollOnce();
    }, 1000);
  };

  const startPolling = async (taskId: string) => {
    stopPolling();
    activeTaskId.value = taskId;
    isPolling.value = true;
    syncStatus(
      {
        status: 'pending',
        progress: 0,
        message: '渲染排队中',
        stage: 'queued',
      },
      true
    );
    return new Promise<DigitalHumanJobStatus>((resolve) => {
      settle = resolve;
      pollOnce();
    });
  };

  const currentStageIndex = computed(() =>
    resolveStageIndex(status.value.stage, status.value.status)
  );
  const currentStageLabel = computed(
    () => stageDefinitions[currentStageIndex.value]?.label || '任务处理中'
  );
  const stageItems = computed<StageItem[]>(() =>
    stageDefinitions.map((item, index) => {
      let state: StageState = 'pending';
      if (
        status.value.status === 'failed' &&
        index === currentStageIndex.value
      ) {
        state = 'error';
      } else if (index < currentStageIndex.value) {
        state = 'completed';
      } else if (
        index === currentStageIndex.value &&
        (activeTaskId.value || status.value.status === 'success')
      ) {
        state = status.value.status === 'success' ? 'completed' : 'active';
      } else if (status.value.status === 'success') {
        state = 'completed';
      }

      return {
        key: item.key,
        label: item.label,
        state,
      };
    })
  );

  onBeforeUnmount(() => {
    stopPolling();
    stopProgressAnimation();
  });

  return {
    activeTaskId,
    status,
    isPolling,
    displayProgress,
    currentStageLabel,
    stageItems,
    startPolling,
    stopPolling,
  };
}
