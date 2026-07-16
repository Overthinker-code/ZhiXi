import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

/** 伴学大厅：功能导航与欢迎页（不含主对话） */
const ASSISTANT: AppRouteRecordRaw = {
  path: '/assistant',
  name: 'assistantHall',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '伴学大厅',
    requiresAuth: true,
    icon: 'icon-apps',
    order: 1.5,
    roles: ['student', 'teacher'],
  },
  children: [
    {
      path: '',
      name: 'AssistantHome',
      component: () => import('@/views/chat/HomePage.vue'),
      meta: {
        locale: '伴学大厅',
        requiresAuth: true,
        roles: ['student', 'teacher'],
      },
    },
    {
      path: 'chat',
      name: 'AssistantChat',
      redirect: '/tutor',
      meta: {
        locale: 'AI 对话',
        requiresAuth: true,
        hideInMenu: true,
        roles: ['student'],
      },
    },
  ],
};

export default ASSISTANT;
