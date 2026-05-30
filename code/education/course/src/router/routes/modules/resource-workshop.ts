import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const RESOURCE_WORKSHOP: AppRouteRecordRaw = {
  path: '/resource-workshop',
  name: 'resourceWorkshop',
  component: DEFAULT_LAYOUT,
  redirect: '/course/resource-generation',
  meta: {
    locale: '学习资源工坊兼容入口',
    requiresAuth: true,
    icon: 'icon-storage',
    order: 2.1,
    hideInMenu: true,
  },
  children: [
    {
      path: 'packages',
      name: 'ResourcePackageBuilder',
      redirect: '/course/resource-generation',
      meta: {
        locale: '资源包生成兼容入口',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'exercise-review',
      name: 'ResourceExerciseReview',
      redirect: '/assistant/chat',
      meta: {
        locale: '练习批改兼容入口',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'image-solver',
      name: 'ResourceImageSolver',
      redirect: '/assistant/chat',
      meta: {
        locale: '图像题解兼容入口',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
  ],
};

export default RESOURCE_WORKSHOP;
