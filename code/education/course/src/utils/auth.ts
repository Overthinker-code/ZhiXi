import { useUserStore } from '@/store';

const TOKEN_KEY = 'token';

const isLogin = () => {
  const userStore = useUserStore();
  return !!userStore.getToken();
};

const getToken = () => {
  const userStore = useUserStore();
  return userStore.getToken() || null;
};

const setToken = (token: string) => {
  const userStore = useUserStore();
  userStore.setToken(token);
};

const clearToken = () => {
  const userStore = useUserStore();
  userStore.clearToken();
};

const persistTokenForRefresh = () => {
  const userStore = useUserStore();
  const token = userStore.getToken();
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  }
};

/** 刷新/多标签页：从 LS 回补内存，不再 removeItem（旧逻辑会清空 LS 导致误判未登录） */
const restoreTokenFromStorage = () => {
  const userStore = useUserStore();
  const storedToken = localStorage.getItem(TOKEN_KEY);
  if (storedToken && !userStore.token) {
    userStore.setToken(storedToken);
  }
};

export {
  isLogin,
  getToken,
  setToken,
  clearToken,
  persistTokenForRefresh,
  restoreTokenFromStorage,
};
