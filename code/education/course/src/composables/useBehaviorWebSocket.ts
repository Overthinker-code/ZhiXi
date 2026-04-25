import { ref, onBeforeUnmount } from 'vue';
import {
  BehaviorWebSocketClient,
  type WsAnalysisMessage,
  type WsPersonResult,
  type BehaviorStatus,
} from '@/api/behavior-analysis-ws';
import { getToken } from '@/utils/auth';

export interface BehaviorWsState {
  /** 连接状态 */
  connectionStatus: 'idle' | 'connecting' | 'open' | 'closed' | 'error';
  /** 是否正在检测（连接成功且定时发送帧中） */
  isDetecting: boolean;
  /** 最新一帧分析结果 */
  latestResult: WsAnalysisMessage | null;
  /** 检测到的所有人 */
  persons: WsPersonResult[];
  /** 当前帧专注人数 */
  focusedCount: number;
  /** 当前帧不专注人数 */
  unfocusedCount: number;
  /** 当前帧缺席人数 */
  absentCount: number;
  /** 错误信息 */
  errorMessage: string;
  /** 累计发送帧数 */
  sentFrameCount: number;
  /** 累计接收结果数 */
  receivedResultCount: number;
}

const STATUS_COLORS: Record<BehaviorStatus, string> = {
  focused: '#52c41a',
  unfocused: '#faad14',
  absent: '#f5222d',
};

export function useBehaviorWebSocket() {
  const client = new BehaviorWebSocketClient();

  const state = ref<BehaviorWsState>({
    connectionStatus: 'idle',
    isDetecting: false,
    latestResult: null,
    persons: [],
    focusedCount: 0,
    unfocusedCount: 0,
    absentCount: 0,
    errorMessage: '',
    sentFrameCount: 0,
    receivedResultCount: 0,
  });

  let sendTimer: ReturnType<typeof setInterval> | null = null;
  let frameId = 0;

  // 监听后端消息
  const unsubMsg = client.onMessage((msg) => {
    state.value.receivedResultCount += 1;

    if (msg.type === 'error') {
      state.value.errorMessage = msg.detail || msg.error || '检测出错';
      return;
    }

    state.value.latestResult = msg;
    state.value.persons = msg.persons || [];
    state.value.focusedCount = msg.summary?.focused_count || 0;
    state.value.unfocusedCount = msg.summary?.unfocused_count || 0;
    state.value.absentCount = msg.summary?.absent_count || 0;
    state.value.errorMessage = '';
  });

  // 监听连接状态
  const unsubStatus = client.onStatus((status) => {
    state.value.connectionStatus = status;
    if (status === 'closed' || status === 'error') {
      state.value.isDetecting = false;
    }
  });

  /**
   * 开始实时检测
   * @param courseId 课程ID
   * @param getFrame 获取当前视频帧 base64 的回调函数
   * @param intervalMs 发送间隔（默认 500ms）
   */
  const startDetection = (
    courseId: string,
    getFrame: () => string | null,
    intervalMs = 500
  ) => {
    if (state.value.isDetecting) return;

    state.value.errorMessage = '';
    const token = getToken() || '';
    if (token) client.setToken(token);
    client.connect(courseId);

    // 等待连接成功后开始发送帧
    const waitOpen = setInterval(() => {
      if (client.isOpen()) {
        clearInterval(waitOpen);
        state.value.isDetecting = true;
        state.value.sentFrameCount = 0;
        state.value.receivedResultCount = 0;

        sendTimer = setInterval(() => {
          const base64 = getFrame();
          if (base64) {
            frameId += 1;
            const ok = client.sendFrame(frameId, base64);
            if (ok) state.value.sentFrameCount += 1;
          }
        }, intervalMs);
      }
    }, 200);

    // 10 秒连接超时
    setTimeout(() => clearInterval(waitOpen), 10000);
  };

  /** 停止检测 */
  const stopDetection = () => {
    if (sendTimer) {
      clearInterval(sendTimer);
      sendTimer = null;
    }
    state.value.isDetecting = false;
    client.disconnect();
  };

  /** 获取状态对应颜色 */
  const getStatusColor = (status: BehaviorStatus) => STATUS_COLORS[status] || '#999';

  onBeforeUnmount(() => {
    stopDetection();
    unsubMsg();
    unsubStatus();
  });

  return {
    state,
    startDetection,
    stopDetection,
    getStatusColor,
  };
}
