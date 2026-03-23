import { defineStore } from 'pinia';
import {
  login as userLogin,
  logout as userLogout,
  getUserInfo,
  LoginData,
} from '@/api/user';
import { removeRouteListener } from '@/utils/route-listener';
import { UserState } from './types';
import useAppStore from '../app';

const TOKEN_KEY = 'token';

function formatDate(input?: string) {
  if (!input) return '-';
  const date = new Date(input);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toISOString().slice(0, 10);
}

const useUserStore = defineStore('user', {
  state: (): UserState => ({
    name: undefined,
    avatar: undefined,
    job: undefined,
    organization: undefined,
    location: undefined,
    email: undefined,
    introduction: undefined,
    personalWebsite: undefined,
    jobName: undefined,
    organizationName: undefined,
    locationName: undefined,
    phone: undefined,
    registrationDate: undefined,
    accountId: undefined,
    certification: undefined,
    role: '',
    token: undefined,
  }),

  getters: {
    userInfo(state: UserState): UserState {
      return { ...state };
    },
  },

  actions: {
    switchRoles() {
      return new Promise((resolve) => {
        this.role = this.role === 'user' ? 'admin' : 'user';
        resolve(this.role);
      });
    },
    setInfo(partial: Partial<UserState>) {
      this.$patch(partial);
    },

    resetInfo() {
      this.$reset();
    },

    getToken(): string | undefined {
      if (this.token) {
        return this.token;
      }
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (storedToken) {
        this.token = storedToken;
        localStorage.removeItem(TOKEN_KEY);
      }
      return this.token;
    },

    setToken(token: string) {
      this.token = token;
    },

    clearToken() {
      this.token = undefined;
      localStorage.removeItem(TOKEN_KEY);
    },

    async info() {
      const res = await getUserInfo();
      const data = res.data as UserState & {
        id?: string;
        full_name?: string;
        created_at?: string;
        is_superuser?: boolean;
      };
      const name =
        data.name || data.full_name || data.email?.split('@')[0] || 'User';
      const avatar =
        data.avatar ||
        `https://ui-avatars.com/api/?name=${encodeURIComponent(
          name
        )}&background=1677ff&color=fff`;
      this.setInfo({
        ...data,
        name,
        avatar,
        accountId: data.accountId || data.id || '-',
        registrationDate: data.registrationDate || formatDate(data.created_at),
        certification: data.certification ?? 1,
        phone: data.phone || '-',
        role: data?.is_superuser ? 'admin' : 'user',
      });
    },

    async login(loginForm: LoginData) {
      try {
        const res = await userLogin(loginForm);
        this.setToken(res.data.token);
      } catch (err) {
        this.clearToken();
        throw err;
      }
    },
    logoutCallBack() {
      const appStore = useAppStore();
      this.resetInfo();
      this.clearToken();
      removeRouteListener();
      appStore.clearServerMenu();
    },
    async logout() {
      try {
        await userLogout();
      } finally {
        this.logoutCallBack();
      }
    },
  },
});

export default useUserStore;
