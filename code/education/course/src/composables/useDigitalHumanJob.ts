import { onBeforeUnmount, ref } from 'vue';
import {
  type DigitalHumanJobStatus,
  queryDigitalHumanJobStatus,
} from '@/api/digital-human';

export function useDigitalHumanJob() {
  const activeTaskId = ref('');
  const status = ref<DigitalHumanJobStatus>({
    status: 'pending',
    progress: 0,
    message: '等待任务开始',
    stage: 'idle',
  });
  const isPolling = ref(false);
  let timer: ReturnType<typeof window.setTimeout> | null = null;

  const stopPolling = () => {
    isPolling.value = false;
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
  };

  const pollOnce = async () => {
    if (!activeTaskId.value) return;
    const data = await queryDigitalHumanJobStatus(activeTaskId.value);
    status.value = data;
    if (data.status === 'success' || data.status === 'failed') {
      stopPolling();
      return;
    }
    timer = window.setTimeout(() => {
      void pollOnce();
    }, 2000);
  };

  const startPolling = async (taskId: string) => {
    stopPolling();
    activeTaskId.value = taskId;
    isPolling.value = true;
    status.value = {
      status: 'pending',
      progress: 0,
      message: '渲染排队中',
      stage: 'queued',
    };
    await pollOnce();
  };

  onBeforeUnmount(() => {
    stopPolling();
  });

  return {
    activeTaskId,
    status,
    isPolling,
    startPolling,
    stopPolling,
  };
}
