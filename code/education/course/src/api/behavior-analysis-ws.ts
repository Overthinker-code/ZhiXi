export type BehaviorStatus = 'focused' | 'unfocused' | 'absent';

export interface WsEducationalMetrics {
  lei: number;
  bloom_level: string;
  cognitive_state: string;
  bei: number;
  cei: number;
  eei: number;
  attention_deviation: number;
  mind_wandering: boolean;
}

export interface WsPersonResult {
  track_id: string;
  bbox: [number, number, number, number];
  status: BehaviorStatus;
  score: number;
  behavior?: string;
  confidence?: number;
  color?: string;
  reason?: string;
  method?: 'yolo' | 'fallback' | string;
  educational?: WsEducationalMetrics;
}

export interface WsSummaryResult {
  focused_count: number;
  unfocused_count: number;
  absent_count: number;
  overall_score?: number;
  attention_score?: number;
  focus_rate?: number;
  stability_index?: number;
  avg_lei?: number;
  bloom_distribution?: Record<string, number>;
  on_task_rate?: number;
  mind_wandering_rate?: number;
}

export interface WsAnalysisMessage {
  type: 'analysis' | 'error';
  frame_id: number;
  timestamp: number;
  persons: WsPersonResult[];
  summary: WsSummaryResult;
  detail?: string;
  error?: string;
}

export interface WsFrameMessage {
  type: 'frame';
  frame_id: number;
  timestamp: number;
  image_base64: string;
}

type MessageHandler = (msg: WsAnalysisMessage) => void;
type StatusHandler = (status: 'connecting' | 'open' | 'closed' | 'error') => void;

function resolveWsBaseUrl(): string {
  // 根据当前页面协议推断 WebSocket 地址
  const { protocol, host } = window.location;
  return protocol === 'https:' ? `wss://${host}` : `ws://${host}`;
}

const WS_BASE_URL = resolveWsBaseUrl();

export class BehaviorWebSocketClient {
  private ws: WebSocket | null = null;
  private messageHandlers: MessageHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private courseId = '';
  private token = '';

  /** 注册消息回调 */
  onMessage(handler: MessageHandler) {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  /** 注册状态回调 */
  onStatus(handler: StatusHandler) {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  private emitStatus(status: 'connecting' | 'open' | 'closed' | 'error') {
    this.statusHandlers.forEach((h) => h(status));
  }

  private emitMessage(msg: WsAnalysisMessage) {
    this.messageHandlers.forEach((h) => h(msg));
  }

  /** 设置 JWT Token */
  setToken(token: string) {
    this.token = token;
  }

  /** 建立连接 */
  connect(courseId?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.courseId = courseId || '';
    this.emitStatus('connecting');

    const params = new URLSearchParams();
    if (this.courseId) params.append('course_id', this.courseId);
    // token 由外部传入，保持客户端无 Vue store 依赖
    if (this.token) params.append('token', this.token);

    const query = params.toString();
    const url = `${WS_BASE_URL}/api/behavior/ws/realtime${query ? `?${query}` : ''}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.emitStatus('open');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsAnalysisMessage;
        this.emitMessage(msg);
      } catch {
        this.emitMessage({
          type: 'error',
          frame_id: 0,
          timestamp: Math.floor(Date.now() / 1000),
          persons: [],
          summary: { focused_count: 0, unfocused_count: 0, absent_count: 0 },
          detail: '解析后端消息失败',
        });
      }
    };

    this.ws.onclose = () => {
      this.emitStatus('closed');
      this.tryReconnect();
    };

    this.ws.onerror = () => {
      this.emitStatus('error');
    };
  }

  /** 发送单帧 */
  sendFrame(frameId: number, base64Image: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;

    const msg: WsFrameMessage = {
      type: 'frame',
      frame_id: frameId,
      timestamp: Math.floor(Date.now() / 1000),
      image_base64: base64Image,
    };
    this.ws.send(JSON.stringify(msg));
    return true;
  }

  /** 断开连接 */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts + 1; // 阻止自动重连
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.courseId);
    }, this.reconnectDelay);
  }

  /** 当前是否已连接 */
  isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
