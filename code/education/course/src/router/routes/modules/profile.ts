import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const PROFILE: AppRouteRecordRaw = {
  path: '/profile',
  name: 'profile',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '个人中心',
    requiresAuth: true,
    icon: 'icon-user',
    order: 3,
  },
  children: [
    {
      path: '',
      redirect: '/profile/user-info',
      meta: {
        hideInMenu: true,
      },
    },
    {
      path: 'user-info',
      name: 'ProfileUserInfo',
      component: () => import('@/views/profile/user-info/index.vue'),
      meta: {
        locale: '个人中心',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'learning-data',
      name: 'ProfileLearningData',
      component: () => import('@/views/profile/learning-data/index.vue'),
      meta: {
        locale: '学情档案',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'basic',
      name: 'Basic',
      component: () => import('@/views/profile/basic/index.vue'),
      meta: {
        locale: 'menu.profile.basic',
        requiresAuth: true,
        roles: ['*'],
      },
    },
  ],
};

export default PROFILE;
