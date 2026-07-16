import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

/** 学生端独立 AI 伴学对话（顶级菜单，默认入口） */
const TUTOR: AppRouteRecordRaw = {
  path: '/tutor',
  name: 'aiTutor',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: 'AI 伴学',
    requiresAuth: true,
    icon: 'icon-message',
    order: 1,
    roles: ['student'],
  },
  children: [
    {
      path: '',
      name: 'TutorChat',
      component: () => import('@/views/chat/ChatView.vue'),
      meta: {
        locale: 'AI 伴学',
        requiresAuth: true,
        roles: ['student'],
      },
    },
  ],
};

export default TUTOR;
