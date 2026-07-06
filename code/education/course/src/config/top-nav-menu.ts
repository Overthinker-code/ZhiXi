export interface MegaMenuItem {
  title: string;
  desc: string;
  routeName: string;
  icon: string;
  roles?: Array<'student' | 'teacher' | '*'>;
}

export interface TopNavGroup {
  key: string;
  label: string;
  routeName?: string;
  roles?: Array<'student' | 'teacher' | '*'>;
  items?: MegaMenuItem[];
}

const STUDENT_GROUPS: TopNavGroup[] = [
  {
    key: 'home',
    label: '首页',
    routeName: 'AssistantHome',
    roles: ['student'],
  },
  {
    key: 'ai',
    label: 'AI 伴学',
    routeName: 'TutorChat',
    roles: ['student'],
  },
  {
    key: 'course',
    label: '课程中心',
    routeName: 'CourseList',
    roles: ['student', 'teacher', '*'],
  },
  {
    key: 'solutions',
    label: '解决方案',
    routeName: 'MarketingSolutions',
    roles: ['student', 'teacher', '*'],
  },
  {
    key: 'pricing',
    label: '价格',
    routeName: 'MarketingPricing',
    roles: ['student', 'teacher', '*'],
  },
  {
    key: 'about',
    label: '关于我们',
    routeName: 'MarketingAbout',
    roles: ['student', 'teacher', '*'],
  },
  {
    key: 'profile',
    label: '个人中心',
    roles: ['teacher'],
    items: [
      {
        title: '个人中心',
        desc: '课程、待办与最新动态',
        routeName: 'ProfileDashboard',
        icon: 'icon-home',
        roles: ['student'],
      },
      {
        title: '教学指挥舱',
        desc: '教师工作台与班级预警',
        routeName: 'Workplace',
        icon: 'icon-dashboard',
        roles: ['teacher'],
      },
      {
        title: '班级学情',
        desc: '班级洞察与趋势分析',
        routeName: 'ProfileClassInsights',
        icon: 'icon-bar-chart',
        roles: ['teacher'],
      },
      {
        title: '成就与积分',
        desc: '学习成就与积分排行',
        routeName: 'ProfileAchievements',
        icon: 'icon-trophy',
        roles: ['student'],
      },
      {
        title: '消息中心',
        desc: '系统通知与课程提醒',
        routeName: 'ProfileMessages',
        icon: 'icon-notification',
      },
      {
        title: '用户设置',
        desc: '资料、安全与实名认证',
        routeName: 'ProfileUserInfo',
        icon: 'icon-settings',
      },
    ],
  },
];

export function getTopNavGroups(role: string): TopNavGroup[] {
  const normalized = role === 'teacher' ? 'teacher' : 'student';
  return STUDENT_GROUPS.filter((group) => {
    if (!group.roles?.length) return true;
    return (
      group.roles.includes('*') ||
      group.roles.includes(normalized as 'student' | 'teacher')
    );
  }).map((group) => ({
    ...group,
    items: group.items?.filter((item) => {
      if (!item.roles?.length) return true;
      return (
        item.roles.includes('*') ||
        item.roles.includes(normalized as 'student' | 'teacher')
      );
    }),
  }));
}
