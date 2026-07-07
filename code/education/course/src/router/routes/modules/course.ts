import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

function legacyCourseRedirect(
  section: 'home' | 'content' | 'resources',
  idSource: 'params' | 'query'
) {
  return (to: any) => {
    const source = idSource === 'params' ? to.params.id : to.query.courseId;
    const courseId = Array.isArray(source) ? source[0] : source;
    if (!courseId) return { name: 'CourseList' };
    const query = { ...to.query };
    delete query.courseId;
    delete query.id;
    return {
      path: `/course/${courseId}/${section}`,
      query,
    };
  };
}

const COURSE: AppRouteRecordRaw = {
  path: '/course',
  name: 'course',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: '课程中心',
    requiresAuth: true,
    order: 2,
  },
  children: [
    {
      path: 'monitor',
      name: 'Monitor',
      component: () => import('@/views/course/monitor/index.vue'),
      meta: {
        locale: '实时学情监控',
        requiresAuth: true,
        roles: ['teacher'],
      },
    },
    {
      path: 'list',
      name: 'CourseList',
      component: () => import('@/views/course/courselist/index.vue'),
      meta: {
        locale: '课程总览',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'detail/:id',
      name: 'CourseDetail',
      redirect: legacyCourseRedirect('home', 'params'),
      meta: {
        locale: '课程详情',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'course-one/:id?',
      name: 'CourseOne',
      redirect: legacyCourseRedirect('home', 'params'),
      meta: {
        locale: '课程信息',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'course-list',
      name: 'CourseListAlias',
      redirect: '/course/list',
      meta: {
        locale: '课程总览',
        requiresAuth: true,
        roles: ['*'],
        hideInMenu: true,
      },
    },
    {
      path: 'course-content',
      name: 'CourseContent',
      redirect: legacyCourseRedirect('content', 'query'),
      meta: {
        locale: '课堂内容',
        requiresAuth: true,
        roles: ['*'],
      },
    },
    {
      path: 'resource-generation',
      name: 'CourseResourceGeneration',
      component: () => import('@/views/course/resource-generation/index.vue'),
      meta: {
        locale: '资源生成中心',
        requiresAuth: true,
        roles: ['student', 'teacher'],
        topNavGroup: 'course',
      },
    },
    {
      path: 'student-resources',
      name: 'StudentCourseResourcesLegacy',
      redirect: legacyCourseRedirect('resources', 'query'),
      meta: {
        hideInMenu: true,
        requiresAuth: true,
        roles: ['student'],
      },
    },
    {
      path: ':courseId',
      name: 'StudentCourseWorkspace',
      component: () =>
        import('@/views/course/workspace/CourseWorkspaceLayout.vue'),
      redirect: (to: any) => ({
        name: 'StudentCourseHome',
        params: { courseId: to.params.courseId },
        query: to.query,
      }),
      meta: {
        locale: '课程空间',
        requiresAuth: true,
        roles: ['student'],
        hideInMenu: true,
        topNavGroup: 'course',
      },
      children: [
        {
          path: 'home',
          name: 'StudentCourseHome',
          component: () => import('@/views/course/courseone/index.vue'),
          meta: {
            locale: '课程首页',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'home',
            topNavGroup: 'course',
          },
        },
        {
          path: 'content',
          name: 'StudentCourseContent',
          component: () => import('@/views/course/coursevideo/index.vue'),
          meta: {
            locale: '课堂内容',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'content',
            topNavGroup: 'course',
          },
        },
        {
          path: 'tasks',
          name: 'StudentCourseTasks',
          component: () =>
            import('@/views/course/workspace/CourseTasksPage.vue'),
          meta: {
            locale: '任务中心',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'tasks',
            topNavGroup: 'course',
          },
        },
        {
          path: 'resources/generate',
          name: 'StudentCourseResourceGenerator',
          component: () =>
            import('@/views/course/resource-generation/index.vue'),
          meta: {
            locale: '资源生成',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'resources',
            topNavGroup: 'course',
          },
        },
        {
          path: 'resources',
          name: 'StudentCourseResources',
          component: () =>
            import('@/views/course/workspace/CourseResourcesPage.vue'),
          meta: {
            locale: '课程资料',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'resources',
            topNavGroup: 'course',
          },
        },
        {
          path: 'knowledge',
          name: 'StudentCourseKnowledge',
          component: () =>
            import('@/views/course/workspace/CourseKnowledgePage.vue'),
          meta: {
            locale: '课程图谱',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'knowledge',
            topNavGroup: 'course',
          },
        },
        {
          path: 'analytics',
          name: 'StudentCourseAnalytics',
          component: () =>
            import('@/views/course/workspace/CourseAnalyticsPage.vue'),
          meta: {
            locale: '课程学情',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'analytics',
            topNavGroup: 'course',
          },
        },
        {
          path: 'agent',
          name: 'StudentCourseAgent',
          component: () =>
            import('@/views/course/workspace/CourseAgentWorkbench.vue'),
          meta: {
            locale: 'AI 课程助手',
            requiresAuth: true,
            roles: ['student'],
            courseSection: 'agent',
            topNavGroup: 'course',
          },
        },
      ],
    },
  ],
};

export default COURSE;
