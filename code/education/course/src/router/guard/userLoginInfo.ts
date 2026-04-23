import type { Router, LocationQueryRaw } from 'vue-router';
import NProgress from 'nprogress';

import { useUserStore } from '@/store';
import { restoreTokenFromStorage } from '@/utils/auth';
import isSessionInvalidError from '@/utils/authError';
import type { RoleType } from '@/store/modules/user/types';

function resolveAuthedHome(role?: string) {
  return { name: role === 'teacher' ? 'Workplace' : 'AssistantHome' };
}

export default function setupUserLoginInfoGuard(router: Router) {
  router.beforeEach(async (to, from, next) => {
    NProgress.start();
    restoreTokenFromStorage();
    const userStore = useUserStore();
    const token = userStore.getToken();
    if (token) {
      if (userStore.profileHydrated) {
        if (to.name === 'login') {
          next(resolveAuthedHome(userStore.role));
          return;
        }
        next();
      } else {
        try {
          await userStore.info();
          if (to.name === 'login') {
            next(resolveAuthedHome(userStore.role));
            return;
          }
          next();
        } catch (error) {
          if (isSessionInvalidError(error)) {
            await userStore.logout();
            next({
              name: 'login',
              query: {
                redirect: to.name,
                ...to.query,
              } as LocationQueryRaw,
            });
            return;
          }
          // 网络抖动、5xx 等：不清理 token，避免误踢回登录；兜底角色供权限路由使用
          userStore.setInfo({
            role: (userStore.role || 'student') as RoleType,
            profileHydrated: true,
          });
          next();
        }
      }
    } else {
      if (to.name === 'login') {
        next();
        return;
      }
      next({
        name: 'login',
        query: {
          redirect: to.name,
          ...to.query,
        } as LocationQueryRaw,
      });
    }
  });
}
