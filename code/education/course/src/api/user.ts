import axios from 'axios';
import type { RouteRecordNormalized } from 'vue-router';
import { UserState } from '@/store/modules/user/types';

export interface LoginData {
  username: string;
  password: string;
}

export interface LoginRes {
  token: string;
}

export interface RegisterData {
  email: string;
  full_name: string;
  password: string;
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
    })
    .then((res: any) => ({
      ...res,
      data: { token: res?.data?.access_token || '' },
    }));
}

export function registerUser(data: RegisterData) {
  return axios.post('/users/signup', data);
}

export function recoverPassword(email: string) {
  return axios.post(`/password-recovery/${encodeURIComponent(email)}`);
}

export function logout() {
  return Promise.resolve({ data: {} as LoginRes });
}

export function getUserInfo() {
  return axios.get<UserState>('/users/me');
}

export function getMenuList() {
  return Promise.resolve({ data: [] as RouteRecordNormalized[] });
}
