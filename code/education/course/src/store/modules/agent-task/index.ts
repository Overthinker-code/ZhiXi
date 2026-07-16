import { defineStore } from 'pinia';
import { fetchAgentTasks, type AgentTask } from '@/api/agent-workspace';

const useAgentTaskStore = defineStore('agent-task', {
  state: () => ({
    tasks: [] as AgentTask[],
    runId: '',
    loading: false,
  }),
  actions: {
    replaceTasks(tasks: AgentTask[]) {
      this.tasks = Array.isArray(tasks) ? tasks : [];
      this.runId = this.tasks[0]?.run_id || '';
    },
    clear() {
      this.tasks = [];
      this.runId = '';
    },
    async loadLatest(sessionId: string) {
      if (!sessionId) {
        this.clear();
        return [];
      }
      this.loading = true;
      try {
        const tasks = await fetchAgentTasks(sessionId);
        this.replaceTasks(tasks);
        return tasks;
      } finally {
        this.loading = false;
      }
    },
  },
});

export default useAgentTaskStore;
