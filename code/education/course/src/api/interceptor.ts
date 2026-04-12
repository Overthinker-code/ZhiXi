import axios from 'axios';
import type { AxiosRequestConfig, AxiosResponse } from 'axios';
import { Message, Modal } from '@arco-design/web-vue';
import { useUserStore } from '@/store';
import { getToken } from '@/utils/auth';
import isSessionInvalidError from '@/utils/authError';

export interface HttpResponse<T = unknown> {
  status: number;
  msg: string;
  code: number;
  data: T;
}

/** FastAPI：detail 可能是字符串或校验错误对象数组 */
function formatFastApiDetail(detailRaw: unknown): string {
  if (typeof detailRaw === 'string') {
    return detailRaw;
  }
  if (!Array.isArray(detailRaw)) {
    return '';
  }
  return detailRaw
    .map((d: unknown) => {
      if (typeof d === 'object' && d !== null && 'msg' in d) {
        return String((d as { msg: string }).msg);
      }
      return JSON.stringify(d);
    })
    .join('; ');
}

if (import.meta.env.VITE_API_BASE_URL) {
  axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL;
}
const parsedTimeout = Number(import.meta.env.VITE_AXIOS_TIMEOUT_MS);
/** 通用默认 60s；勿过短，否则远程/冷启动后端易误报超时 */
axios.defaults.timeout =
  Number.isFinite(parsedTimeout) && parsedTimeout > 0 ? parsedTimeout : 60000;

axios.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // let each request carry token
    // this example using the JWT token
    // Authorization is a custom headers key
    // please modify it according to the actual situation
    const token = getToken();
    if (token) {
      if (!config.headers) {
        config.headers = {};
      }
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // do something
    return Promise.reject(error);
  }
);
// add response interceptors
axios.interceptors.response.use(
  (response: AxiosResponse<HttpResponse | unknown>) => {
    const raw = response.data as any;
    const isArcoStyle =
      raw &&
      typeof raw === 'object' &&
      Object.prototype.hasOwnProperty.call(raw, 'code') &&
      Object.prototype.hasOwnProperty.call(raw, 'data');

    // Normalize backend responses to the shape used by existing frontend code.
    // FastAPI returns plain JSON; Arco Pro expects { code, data, msg }.
    const res: HttpResponse = isArcoStyle
      ? (raw as HttpResponse)
      : {
          status: response.status,
          msg: 'success',
          code: 20000,
          data: raw,
        };

    if (res.code !== 20000) {
      Message.error({
        content: res.msg || 'Error',
        duration: 5 * 1000,
      });
      // 50008: Illegal token; 50012: Other clients logged in; 50014: Token expired;
      if (
        [50008, 50012, 50014].includes(res.code) &&
        response.config.url !== '/api/user/info'
      ) {
        Modal.error({
          title: 'Confirm logout',
          content:
            'You have been logged out, you can cancel to stay on this page, or log in again',
          okText: 'Re-Login',
          async onOk() {
            const userStore = useUserStore();

            await userStore.logout();
            window.location.reload();
          },
        });
      }
      return Promise.reject(new Error(res.msg || 'Error'));
    }
    return res;
  },
  (error) => {
    const url: string = error?.config?.url || '';
    const isTimeout = error?.code === 'ECONNABORTED';
    const isChat = url.includes('/chat/');
    const isFeedback = url.includes('/chat/feedback');
    const isNetworkError = !error?.response;
    const isLogin = url.includes('/login/');
    const isDashboard = url.includes('/dashboard/');
    const isEducationRead =
      url.includes('/education/courses') || url.includes('/education/tc');
    /** 课程中心接口失败由页面兜底，勿整站登出（避免隧道/权限抖动误踢） */
    const isEducationApi = url.includes('/education/');
    /** 登录/注册等：错误由页面内文案展示，避免与全局 Message 叠在一起 */
    const isAuthFormRequest =
      url.includes('/login/') ||
      url.includes('/users/signup') ||
      url.includes('/password-recovery') ||
      url.includes('/reset-password');

    if (!isLogin && !isEducationApi && isSessionInvalidError(error)) {
      const userStore = useUserStore();
      userStore.logoutCallBack();
      window.location.href = '/login';
      return Promise.reject(new Error('登录已过期，请重新登录'));
    }

    const resData = error?.response?.data;
    let detailStr = '';
    if (typeof resData === 'object' && resData !== null) {
      detailStr = formatFastApiDetail(
        (resData as Record<string, unknown>).detail
      );
    } else if (typeof resData === 'string') {
      detailStr = resData;
    }
    const rawMessage = detailStr || error?.message || 'Request Error';
    const friendlyChatMessage =
      '无法连接后端 API。请确认：① SSH 隧道已建立且未断开；② 本机可 curl 通隧道端口；③ VITE_DEV_API_PROXY_TARGET 与隧道本地端口一致；④ 修改 .env.development 后已重启 npm run dev。';
    const friendlyNetworkHint =
      '无法连接后端 API，请确认后端已启动，且 .env 中 VITE_API_BASE_URL 指向可访问地址（如 http://127.0.0.1:8000/api/v1）';
    let message = rawMessage;
    if (isChat && isNetworkError) {
      message = friendlyChatMessage;
    } else if (isNetworkError && (isAuthFormRequest || isLogin)) {
      message = friendlyNetworkHint;
    }

    /** 后端未实现或路径不一致的读接口：404 不在全局弹 Toast，由各页兜底/占位 */
    const status = error?.response?.status;
    /** 含 /api/v1/chat/… 等（axios baseURL 带版本前缀），勿仅用 /api/chat/ 判断 */
    const shouldSilence404 =
      status === 404 &&
      (() => {
        const u = url || '';
        if (u.includes('/dashboard/')) return true;
        if (u.includes('/education/')) return true;
        if (u.includes('/chat/')) return true;
        if (u.includes('/message/')) return true;
        if (u.includes('/profile/basic')) return true;
        if (u.includes('/operation/log')) return true;
        if (u.includes('/behavior/')) return true;
        if (u.includes('/user/my-project')) return true;
        if (u.includes('/user/my-team')) return true;
        if (u.includes('/user/latest-activity')) return true;
        if (u.includes('/user/visits')) return true;
        if (u.includes('/user/project-and-team')) return true;
        if (u.includes('/user/save-info')) return true;
        if (u.includes('/user/certification')) return true;
        if (u.includes('/user/upload')) return true;
        if (u.includes('/rag')) return true;
        if (u.includes('/file/upload')) return true;
        return false;
      })();

    const shouldSilenceGlobalToast =
      shouldSilence404 ||
      (isChat && isTimeout) ||
      isFeedback ||
      (isChat && isNetworkError) ||
      (isDashboard && isNetworkError) ||
      (isEducationRead && isNetworkError) ||
      isAuthFormRequest ||
      (url.includes('/users/me') && isNetworkError);
    /** /chat/threads 由业务层（如 useChat）统一提示，避免与 axios reject 后的 Message 重复 */
    const isChatThreads = url.includes('/chat/threads');
    if (!shouldSilenceGlobalToast && !isChatThreads) {
      Message.error({
        content: message,
        duration: 5 * 1000,
      });
    }
    return Promise.reject(new Error(message));
  }
);
