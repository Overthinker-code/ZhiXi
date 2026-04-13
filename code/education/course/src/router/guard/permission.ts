import type { Router, RouteRecordNormalized } from 'vue-router';
import NProgress from 'nprogress'; // progress bar

import usePermission from '@/hooks/permission';
import { useUserStore, useAppStore } from '@/store';
import { appRoutes } from '../routes';
import { WHITE_LIST, NOT_FOUND } from '../constants';

function routeNameExistsInLocalConfig(
  routeName: string | symbol | null | undefined,
  routes: RouteRecordNormalized[]
) {
  if (!routeName) return false;
  const queue = [...routes];
  while (queue.length) {
    const route = queue.shift();
    if (!route) continue;
    if (route.name === routeName) return true;
    if (route.children?.length) {
      queue.push(...(route.children as unknown as RouteRecordNormalized[]));
    }
  }
  return false;
}

export default function setupPermissionGuard(router: Router) {
  router.beforeEach(async (to, from, next) => {
    const appStore = useAppStore();
    const userStore = useUserStore();
    const Permission = usePermission();
    const permissionsAllow = Permission.accessRouter(to);
    if (appStore.menuFromServer) {
      // 数字人工具页包含多个 hideInMenu 子路由，服务端菜单常不返回这些节点。
      // 这里先强制放行该业务域，避免页面入口点击后无响应。
      if (to.path.startsWith('/digital-human')) {
        next();
        NProgress.done();
        return;
      }
      // 针对来自服务端的菜单配置进行处理
      // Handle routing configuration from the server

      // 根据需要自行完善来源于服务端的菜单配置的permission逻辑
      // Refine the permission logic from the server's menu configuration as needed
      if (
        !appStore.appAsyncMenus.length &&
        !WHITE_LIST.find((el) => el.name === to.name)
      ) {
        await appStore.fetchServerMenuConfig();
      }
      const serverMenuConfig = [...appStore.appAsyncMenus, ...WHITE_LIST];

      let exist = false;
      while (serverMenuConfig.length && !exist) {
        const element = serverMenuConfig.shift();
        if (element?.name === to.name) exist = true;

        if (element?.children) {
          serverMenuConfig.push(
            ...(element.children as unknown as RouteRecordNormalized[])
          );
        }
      }
      // 在菜单来源于服务端时，hideInMenu 子路由可能不在服务端菜单树中，
      // 这里补充本地路由白名单校验，避免页面按钮跳转被误拦截。
      const existInLocal = routeNameExistsInLocalConfig(
        to.name,
        appRoutes as unknown as RouteRecordNormalized[]
      );
      if ((exist || existInLocal) && permissionsAllow) {
        next();
      } else next(NOT_FOUND);
    } else {
      // eslint-disable-next-line no-lonely-if
      if (permissionsAllow) next();
      else {
        const destination =
          Permission.findFirstPermissionRoute(appRoutes, userStore.role) ||
          NOT_FOUND;
        next(destination);
      }
    }
    NProgress.done();
  });
}
