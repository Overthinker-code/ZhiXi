import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

/** 独立「AI助理」菜单，与「个人中心」分离 */
const ASSISTANT: AppRouteRecordRaw = {
  path: '/assistant',
  name: 'assistantHall',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '伴学大厅',
    requiresAuth: true,
    icon: 'icon-robot',
    order: 1.8,
  },
  children: [
    {
      path: '',
      name: 'AssistantHome',
      component: () => import('@/views/chat/HomePage.vue'),
      meta: {
        locale: '伴学大厅',
        requiresAuth: true,
        roles: ['*'],
      },
    },
  ],
};

export default ASSISTANT;
