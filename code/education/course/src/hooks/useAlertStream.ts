import { ref, onMounted, onUnmounted, type Ref } from 'vue';
import { Notification } from '@arco-design/web-vue';
import { getToken } from '@/utils/auth';
import axios from 'axios';

export interface Alert {
  id: string;
  student_id: string;
  alert_time: string;
  reason: string;
  severity: 'low' | 'medium' | 'high';
  student_name?: string;
}

/**
 * Composable for receiving real-time student behavior alerts via SSE.
 *
 * Connects to GET /alerts/stream and pushes incoming Alert objects
 * into a reactive list. High-severity alerts trigger an Arco Notification.
 *
 * Usage:
 * ```ts
 * const { alerts, isConnected } = useAlertStream('tc-uuid')
 * ```
 */
export function useAlertStream(tcId: string) {
  const alerts: Ref<Alert[]> = ref([]);
  const isConnected = ref(false);
  let eventSource: EventSource | null = null;

  function connect() {
    const base =
      axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || '';
    const token = getToken();
    const params = new URLSearchParams({ tc_id: tcId });
    if (token) {
      params.set('token', token);
    }
    const url = `${base.replace(/\/+$/, '')}/alerts/stream?${params.toString()}`;

    eventSource = new EventSource(url);
    isConnected.value = true;

    eventSource.onmessage = (e) => {
      try {
        const alert: Alert = JSON.parse(e.data);
        alerts.value.unshift(alert);

        // High-severity alerts trigger a visible notification
        if (alert.severity === 'high') {
          Notification.warning({
            title: '⚠️ 学情预警',
            content: `${alert.student_name || '学生'}: ${alert.reason}`,
            duration: 6000,
          });
        }
      } catch {
        // Ignore malformed events
      }
    };

    eventSource.onerror = () => {
      isConnected.value = false;
      eventSource?.close();
      // Attempt reconnection after 5 seconds
      setTimeout(() => {
        if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
          connect();
        }
      }, 5000);
    };
  }

  function disconnect() {
    eventSource?.close();
    eventSource = null;
    isConnected.value = false;
  }

  onMounted(connect);
  onUnmounted(disconnect);

  return { alerts, isConnected, disconnect };
}
