import axios from 'axios';
import type { AxiosRequestConfig, AxiosResponse } from 'axios';
import { Message, Modal } from '@arco-design/web-vue';
import { useUserStore } from '@/store';
import { getToken } from '@/utils/auth';

export interface HttpResponse<T = unknown> {
  status: number;
  msg: string;
  code: number;
  data: T;
}

if (import.meta.env.VITE_API_BASE_URL) {
  axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL;
}
axios.defaults.timeout = 30000;

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

    const message =
      error?.response?.data?.detail || error?.message || 'Request Error';

    // Silence chat timeout errors (LLM inference can be slow) and
    // feedback endpoint 404s (backend may not implement it yet)
    if (!(isChat && isTimeout) && !isFeedback) {
      Message.error({
        content: message,
        duration: 5 * 1000,
      });
    }
    return Promise.reject(new Error(message));
  }
);
