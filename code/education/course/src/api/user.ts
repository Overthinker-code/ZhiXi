import axios from 'axios';
import type { RouteRecordNormalized } from 'vue-router';
import { UserState } from '@/store/modules/user/types';

/** 登录链路（含远端 2080、VPN、数据库冷启动）单独放宽，避免误超时 */
const AUTH_TIMEOUT_MS = 120000;

export interface LoginData {
  username: string;
  password: string;
}

export interface LoginRes {
  token: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface PasswordRecoveryData {
  email: string;
}

export interface ResetPasswordData {
  token: string;
  new_password: string;
}

function pickAccessToken(res: any): string {
  if (!res) return '';
  // 响应拦截器已把 FastAPI 包成 { code, data: { access_token } }
  if (res.code === 20000 && res.data?.access_token) {
    return res.data.access_token;
  }
  // 未走拦截器或兼容旧形态
  if (res.data?.access_token) return res.data.access_token;
  if (typeof res.access_token === 'string') return res.access_token;
  return '';
}

export function login(data: LoginData) {
  const body = new URLSearchParams();
  body.append('username', data.username);
  body.append('password', data.password);
  return axios
    .post<{ access_token: string }>('/login/access-token', body, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      timeout: AUTH_TIMEOUT_MS,
    })
    .then((res: any) => ({
      data: { token: pickAccessToken(res) },
    }));
}

export function registerUser(data: RegisterData) {
  return axios.post('/users/signup', data, { timeout: AUTH_TIMEOUT_MS });
}

export function recoverPassword(email: string) {
  return axios.post(
    `/password-recovery/${encodeURIComponent(email)}`,
    undefined,
    { timeout: AUTH_TIMEOUT_MS }
  );
}

export function logout() {
  return Promise.resolve({ data: {} as LoginRes });
}

export function getUserInfo() {
  return axios.get<UserState>('/users/me', { timeout: AUTH_TIMEOUT_MS });
}

export function getMenuList() {
  return Promise.resolve({ data: [] as RouteRecordNormalized[] });
}

export function register(data: RegisterData) {
  return axios.post('/users/signup', data, { timeout: AUTH_TIMEOUT_MS });
}

export function resetPassword(data: ResetPasswordData) {
  return axios.post('/reset-password/', data, { timeout: AUTH_TIMEOUT_MS });
}
