import { createPinia } from 'pinia';
import useAppStore from './modules/app';
import useUserStore from './modules/user';
import useTabBarStore from './modules/tab-bar';
import useStudentProfileStore from './modules/student-profile';
import useAgentTaskStore from './modules/agent-task';

const pinia = createPinia();

export { useAppStore, useUserStore, useTabBarStore, useStudentProfileStore, useAgentTaskStore };
export default pinia;
