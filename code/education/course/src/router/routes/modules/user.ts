import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const USER: AppRouteRecordRaw = {
  path: '/user',
  name: 'user',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: 'menu.user',
    icon: 'icon-user',
    requiresAuth: true,
    order: 3,
    /** 与「个人中心」菜单合并展示后易重复，仅保留路由供直达，侧边栏隐藏整组 */
    hideInMenu: true,
  },
  children: [
    {
      path: 'info',
      name: 'Info',
      redirect: '/profile/user-info',
      meta: {
        locale: 'menu.user.info',
        requiresAuth: true,
        roles: ['*'],
        // Hide from navigation menu, keep route available.
        hideInMenu: true,
      },
    },
    {
      path: 'study',
      redirect: '/profile/learning-data',
      meta: {
        requiresAuth: true,
        hideInMenu: true,
      },
    },
    {
      path: 'setting',
      name: 'Setting',
      redirect: '/profile/user-info',
      meta: {
        locale: '个人资料',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
  ],
};

export default USER;
