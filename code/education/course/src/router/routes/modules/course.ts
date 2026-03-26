import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const COURSE: AppRouteRecordRaw = {
  path: '/course',
  name: 'course',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: 'menu.course',
    requiresAuth: true,
    icon: 'icon-link',
    order: 2,
  },
  children: [
    {
      path: 'monitor',
      name: 'Monitor',
      component: () => import('@/views/course/monitor/index.vue'),
      meta: {
        locale: 'menu.dashboard.monitor',
        requiresAuth: true,
        roles: ['admin'],
      },
    },
    {
      path: 'course-one', // The midline path complies with SEO specifications
      name: 'CourseOne',
      component: () => import('@/views/course/courseone/index.vue'),
      meta: {
        locale: '课程信息',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'course-list', // The midline path complies with SEO specifications
      name: 'CourseList',
      component: () => import('@/views/course/courselist/index.vue'),
      meta: {
        locale: '课程总览',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'course-content', // The midline path complies with SEO specifications
      name: 'CourseContent',
      component: () => import('@/views/course/coursevideo/index.vue'),
      meta: {
        locale: '课堂内容',
        requiresAuth: true,
        roles: ['*'],
      },
    },
  ],
};

export default COURSE;
