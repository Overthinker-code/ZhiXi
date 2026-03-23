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

const restoreTokenFromStorage = () => {
  const storedToken = localStorage.getItem(TOKEN_KEY);
  if (storedToken) {
    const userStore = useUserStore();
    userStore.setToken(storedToken);
    localStorage.removeItem(TOKEN_KEY);
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
