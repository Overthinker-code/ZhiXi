import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const PROFILE: AppRouteRecordRaw = {
  path: '/profile',
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
      redirect: '/profile/dashboard',
      meta: {
        requiresAuth: true,
        hideInMenu: true,
      },
    },
    {
      path: 'dashboard',
      name: 'ProfileDashboard',
      component: () => import('@/views/profile/dashboard/index.vue'),
      meta: {
        locale: '个人中心',
        requiresAuth: true,
        roles: ['student'],
      },
    },
    {
      path: 'achievements',
      name: 'ProfileAchievements',
      component: () => import('@/views/profile/achievements/index.vue'),
      meta: {
        locale: '成就与积分',
        requiresAuth: true,
        roles: ['student'],
      },
    },
    {
      path: 'messages',
      name: 'ProfileMessages',
      component: () => import('@/views/profile/messages/index.vue'),
      meta: {
        locale: '消息中心',
        requiresAuth: true,
        roles: ['*'],
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
        roles: ['student'],
      },
    },
    {
      path: 'class-insights',
      name: 'ProfileClassInsights',
      component: () => import('@/views/profile/class-insights/index.vue'),
      meta: {
        locale: '班级学情',
        requiresAuth: true,
        roles: ['teacher'],
      },
    },
    {
      path: 'basic',
      name: 'Basic',
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

export default PROFILE;
