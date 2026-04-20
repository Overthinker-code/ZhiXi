import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const STUDENT_TUTOR: AppRouteRecordRaw = {
  path: '/student-tutor',
  name: 'studentTutor',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '智屿伴学中心',
    requiresAuth: true,
    icon: 'icon-robot',
    order: 2.2,
  },
  children: [
    {
      path: '',
      name: 'StudentTutor',
      component: () => import('@/views/chat/ChatView.vue'),
      meta: {
        locale: '智屿伴学中心',
        requiresAuth: true,
        roles: ['student'],
      },
    },
  ],
};

export default STUDENT_TUTOR;
