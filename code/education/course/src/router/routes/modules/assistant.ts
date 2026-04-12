import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

/** 独立「AI助理」菜单，与「个人中心」分离 */
const ASSISTANT: AppRouteRecordRaw = {
  path: '/assistant',
  name: 'assistant',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: 'menu.assistant',
    requiresAuth: true,
    icon: 'icon-robot',
    order: 2.75,
  },
  children: [
    {
      path: '',
      name: 'AssistantChat',
      component: () => import('@/views/chat/ChatView.vue'),
      meta: {
        locale: 'menu.assistant.chat',
        requiresAuth: true,
        roles: ['*'],
      },
    },
  ],
};

export default ASSISTANT;
