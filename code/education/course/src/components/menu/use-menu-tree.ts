import { computed } from 'vue';
import { RouteRecordRaw, RouteRecordNormalized } from 'vue-router';
import usePermission from '@/hooks/permission';
import { useAppStore, useUserStore } from '@/store';
import appClientMenus from '@/router/app-menus';
import { cloneDeep } from 'lodash';

const ROLE_MENU_RULES: Record<
  string,
  {
    topLevel: string[];
    children: Record<string, string[]>;
  }
> = {
  student: {
    topLevel: ['assistantHall', 'course', 'studentTutor', 'profile'],
    children: {
      course: ['CourseList', 'CourseOne', 'CourseContent', 'CourseDetail'],
      profile: ['ProfileLearningData', 'ProfileUserInfo', 'Basic'],
    },
  },
  teacher: {
    topLevel: ['dashboard', 'course', 'digitalHuman', 'profile'],
    children: {
      dashboard: ['Workplace'],
      course: ['Monitor', 'CourseList', 'CourseOne', 'CourseContent', 'CourseDetail'],
      profile: ['ProfileUserInfo', 'Basic', 'ProfileLearningData'],
    },
  },
};

export default function useMenuTree() {
  const permission = usePermission();
  const appStore = useAppStore();
  const userStore = useUserStore();
  const appRoute = computed(() => {
    if (appStore.menuFromServer) {
      return appStore.appAsyncMenus;
    }
    return appClientMenus;
  });
  const menuTree = computed(() => {
    const roleKey = userStore.role === 'teacher' ? 'teacher' : 'student';
    const rule = ROLE_MENU_RULES[roleKey];
    const copyRouter = cloneDeep(appRoute.value) as RouteRecordNormalized[];
    copyRouter.sort((a: RouteRecordNormalized, b: RouteRecordNormalized) => {
      return (a.meta.order || 0) - (b.meta.order || 0);
    });
    function travel(
      _routes: RouteRecordRaw[],
      layer: number,
      parentName = ''
    ) {
      if (!_routes) return null;

      const collector: any = _routes.map((element) => {
        const currentName = String(element.name || '');
        if (
          layer === 0 &&
          currentName &&
          !rule.topLevel.includes(currentName)
        ) {
          return null;
        }
        if (layer > 0 && parentName && rule.children[parentName]) {
          const allowChildren = rule.children[parentName];
          if (currentName && !allowChildren.includes(currentName)) {
            return null;
          }
        }
        if (element.meta?.hideInMenu === true) {
          return null;
        }
        // no access
        if (!permission.accessRouter(element)) {
          return null;
        }

        // leaf node
        if (element.meta?.hideChildrenInMenu || !element.children) {
          element.children = [];
          return element;
        }

        // route filter hideInMenu true
        element.children = element.children.filter(
          (x) => x.meta?.hideInMenu !== true
        );

        // Associated child node
        const subItem = travel(element.children, layer + 1, currentName);

        if (subItem.length) {
          element.children = subItem;
          return element;
        }
        // the else logic
        if (layer > 1) {
          element.children = subItem;
          return element;
        }

        if (element.meta?.hideInMenu === false) {
          return element;
        }

        return null;
      });
      return collector.filter(Boolean);
    }
    return travel(copyRouter, 0);
  });

  return {
    menuTree,
  };
}
