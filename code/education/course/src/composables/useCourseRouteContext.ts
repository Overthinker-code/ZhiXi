import { computed } from 'vue';
import {
  type LocationQueryRaw,
  type RouteLocationRaw,
  useRoute,
} from 'vue-router';

export type CourseWorkspaceSection =
  | 'home'
  | 'content'
  | 'tasks'
  | 'resources'
  | 'analytics'
  | 'agent';

const sectionRouteNames: Record<CourseWorkspaceSection, string> = {
  home: 'StudentCourseHome',
  content: 'StudentCourseContent',
  tasks: 'StudentCourseTasks',
  resources: 'StudentCourseResources',
  analytics: 'StudentCourseAnalytics',
  agent: 'StudentCourseAgent',
};

function firstString(value: unknown) {
  if (Array.isArray(value)) return String(value[0] || '');
  return typeof value === 'string' ? value : '';
}

export function resolveCourseId(
  params: Record<string, unknown>,
  query: Record<string, unknown>
) {
  return (
    firstString(params.courseId) ||
    firstString(params.id) ||
    firstString(query.courseId) ||
    firstString(query.id)
  );
}

export function courseWorkspaceLocation(
  courseId: string,
  section: CourseWorkspaceSection = 'home',
  query?: LocationQueryRaw
): RouteLocationRaw {
  return {
    name: sectionRouteNames[section],
    params: { courseId },
    ...(query ? { query } : {}),
  };
}

export function useCourseRouteContext() {
  const route = useRoute();
  const courseId = computed(() =>
    resolveCourseId(
      route.params as Record<string, unknown>,
      route.query as Record<string, unknown>
    )
  );

  return {
    courseId,
    location: (
      section: CourseWorkspaceSection,
      query?: LocationQueryRaw
    ) => courseWorkspaceLocation(courseId.value, section, query),
  };
}
