import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const staticMeta = (title: string, desc: string) => ({
  locale: title,
  requiresAuth: false,
  hideInMenu: true,
  pageTitle: title,
  pageDesc: desc,
});

const MARKETING: AppRouteRecordRaw[] = [
  {
    path: '/solutions',
    component: DEFAULT_LAYOUT,
    meta: staticMeta(
      '解决方案',
      '智屿面向高校提供 AI 伴学、个性化资源生成、学情分析与课堂行为检测的一体化方案。'
    ),
    children: [
      {
        path: '',
        name: 'MarketingSolutions',
        component: () => import('@/views/marketing/static-page.vue'),
        meta: staticMeta(
          '解决方案',
          '智屿面向高校提供 AI 伴学、个性化资源生成、学情分析与课堂行为检测的一体化方案。'
        ),
      },
    ],
  },
  {
    path: '/pricing',
    component: DEFAULT_LAYOUT,
    meta: staticMeta('价格方案', '按院校规模与模块授权灵活定价，支持试点部署与赛题演示环境。'),
    children: [
      {
        path: '',
        name: 'MarketingPricing',
        component: () => import('@/views/marketing/static-page.vue'),
        meta: staticMeta('价格方案', '按院校规模与模块授权灵活定价，支持试点部署与赛题演示环境。'),
      },
    ],
  },
  {
    path: '/about',
    component: DEFAULT_LAYOUT,
    meta: staticMeta(
      '关于智屿',
      '智屿智能教育平台，致力于用多智能体与大模型技术实现因材施教。'
    ),
    children: [
      {
        path: '',
        name: 'MarketingAbout',
        component: () => import('@/views/marketing/static-page.vue'),
        meta: staticMeta(
          '关于智屿',
          '智屿智能教育平台，致力于用多智能体与大模型技术实现因材施教。'
        ),
      },
    ],
  },
];

export default MARKETING;
