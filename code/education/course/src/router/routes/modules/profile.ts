import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const PROFILE: AppRouteRecordRaw = {
  path: '/profile',
  name: 'profile',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: 'menu.profile',
    requiresAuth: true,
    icon: 'icon-file',
    order: 3,
  },
  children: [
    {
      path: '',
      redirect: { name: 'Chat' },
    },
    {
      path: 'chat',
      name: 'Chat',
      component: () => import('@/views/chat/ChatView.vue'),
      meta: {
        locale: 'menu.profile.chat',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'user-info',
      name: 'ProfileUserInfo',
      component: () => import('@/views/profile/user-info/index.vue'),
      meta: {
        locale: 'menu.profile.userInfo',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'learning-data',
      name: 'ProfileLearningData',
      component: () => import('@/views/profile/learning-data/index.vue'),
      meta: {
        locale: 'menu.profile.learningData',
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
