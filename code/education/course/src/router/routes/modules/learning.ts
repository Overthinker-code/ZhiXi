import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const LEARNING: AppRouteRecordRaw = {
  path: '/learning',
  name: 'learning',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '学习中心',
    requiresAuth: true,
    icon: 'icon-book',
    order: 2.2,
    hideInMenu: true,
    roles: ['student'],
  },
  children: [
    {
      path: 'resources',
      name: 'LearningResources',
      component: () => import('@/views/learning/resources/index.vue'),
      meta: {
        locale: '学习资源',
        requiresAuth: true,
        roles: ['student'],
      },
    },
    {
      path: 'practice',
      name: 'LearningPractice',
      component: () => import('@/views/learning/practice/index.vue'),
      meta: {
        locale: '题库练习',
        requiresAuth: true,
        roles: ['student'],
      },
    },
    {
      path: 'groups',
      name: 'LearningGroups',
      component: () => import('@/views/learning/groups/index.vue'),
      meta: {
        locale: '小组协作',
        requiresAuth: true,
        roles: ['student'],
      },
    },
  ],
};

export default LEARNING;
