import { defineStore } from 'pinia';
import {
  analyzeChatProfile,
  fetchDynamicStudentProfile,
  updateProfileSignals,
  type DynamicStudentProfile,
} from '@/api/profile';

const useStudentProfileStore = defineStore('student-profile', {
  state: () => ({
    profile: {} as DynamicStudentProfile,
    lastAnalysis: {} as Record<string, any>,
    loading: false,
  }),
  actions: {
    async loadProfile() {
      this.loading = true;
      try {
        this.profile = await fetchDynamicStudentProfile();
        return this.profile;
      } finally {
        this.loading = false;
      }
    },
    async analyzeChat(payload: {
      session_id: string;
      user_message: string;
      assistant_message?: string;
    }) {
      const result = await analyzeChatProfile(payload);
      this.profile = result.profile;
      this.lastAnalysis = result.analysis;
      return result;
    },
    async updateSignals(payload: Record<string, any>) {
      const result = await updateProfileSignals(payload);
      this.profile = result.profile;
      this.lastAnalysis = result.analysis;
      return result;
    },
  },
});

export default useStudentProfileStore;
