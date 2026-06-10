import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const STUDENT_TUTOR: AppRouteRecordRaw = {
  path: '/student-tutor',
  name: 'studentTutor',
  component: DEFAULT_LAYOUT,
  redirect: '/tutor',
  meta: {
    locale: '智屿伴学中心',
    requiresAuth: true,
    icon: 'icon-robot',
    order: 2.2,
    hideInMenu: true,
  },
  children: [
    {
      path: '',
      name: 'StudentTutor',
      redirect: '/tutor',
      meta: {
        locale: '智屿伴学中心',
        requiresAuth: true,
        roles: ['student'],
        hideInMenu: true,
      },
    },
  ],
};

export default STUDENT_TUTOR;
