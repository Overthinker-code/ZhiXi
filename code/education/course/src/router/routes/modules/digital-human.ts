import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const DIGITAL_HUMAN: AppRouteRecordRaw = {
  path: '/digital-human',
  name: 'digitalHuman',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '数字人创作舱',
    requiresAuth: true,
    icon: 'icon-robot',
    order: 2,
  },
  children: [
    {
      path: '',
      name: 'DigitalHumanTools',
      component: () => import('@/views/digital-human/index.vue'),
      meta: {
        locale: 'menu.digitalHuman.tools',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'ppt-to-video',
      name: 'PptToVideo',
      component: () => import('@/views/digital-human/ppt-to-video/index.vue'),
      meta: {
        locale: 'menu.digitalHuman.pptToVideo',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'text-to-video',
      name: 'TextToVideo',
      component: () => import('@/views/digital-human/text-to-video/index.vue'),
      meta: {
        locale: 'menu.digitalHuman.textToVideo',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'clone',
      name: 'DigitalHumanClone',
      component: () => import('@/views/digital-human/clone/index.vue'),
      meta: {
        locale: 'menu.digitalHuman.clone',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'my',
      name: 'MyDigitalHumans',
      component: () => import('@/views/digital-human/my-digital-humans/index.vue'),
      meta: {
        locale: 'menu.digitalHuman.my',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
  ],
};

export default DIGITAL_HUMAN;
