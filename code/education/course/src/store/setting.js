import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useSettingStore = defineStore(
  'llm-setting',
  () => {
    const settings = ref({
      model: 'deepseek-chat',
      apiKey: import.meta.env.VITE_API_BASE_URL,
      stream: true,
      maxTokens: 16384,
      temperature: 0.7,
      topP: 0.7,
      topK: 50,
      activeTools: ['knowledge_base', 'web_search'],
      modelDisplay: 'deepseek-r1:7b',
      ragK: 4,
      strictMode: false,
      promptKey: 'tutor',
      customSystemPrompt: '',
    });
    const promptOptions = ref([
      {
        key: 'tutor',
        label: '学习辅导',
        description: '分步骤讲解，强调理解与迁移。',
      },
      {
        key: 'exam',
        label: '考试作答',
        description: '按得分点组织答案。',
      },
      {
        key: 'concise',
        label: '简洁速答',
        description: '更短更直接，适合快速确认。',
      },
      {
        key: 'socratic',
        label: '苏格拉底引导',
        description: '先提关键问题，再给提示与答案。',
      },
    ]);
    const toolOptions = ref([
      {
        key: 'knowledge_base',
        label: '知识库检索',
        description: '检索课程资料与引用片段',
      },
      {
        key: 'web_search',
        label: '联网搜索',
        description: '用于补充最新公开信息',
      },
      {
        key: 'behavior_analysis',
        label: '行为分析',
        description: '用于课堂行为图像分析',
      },
    ]);

    return {
      settings,
      promptOptions,
      toolOptions,
    };
  },
  {
    persist: {
      pick: ['settings'],
    },
  }
);

export const modelOptions = [
  {
    label: 'DeepSeek-R1',
    value: 'deepseek-ai/DeepSeek-R1',
    maxTokens: 16384,
  },
  {
    label: 'DeepSeek-V3',
    value: 'deepseek-ai/DeepSeek-V3',
    maxTokens: 4096,
  },
  {
    label: 'DeepSeek-V2.5',
    value: 'deepseek-ai/DeepSeek-V2.5',
    maxTokens: 4096,
  },
  {
    label: 'Qwen2.5-72B-Instruct-128K',
    value: 'Qwen/Qwen2.5-72B-Instruct-128K',
    maxTokens: 4096,
  },
  {
    label: 'QwQ-32B-Preview',
    value: 'Qwen/QwQ-32B-Preview',
    maxTokens: 8192,
  },
  {
    label: 'glm-4-9b-chat',
    value: 'THUDM/glm-4-9b-chat',
    maxTokens: 4096,
  },
  {
    label: 'glm-4-9b-chat(Pro)',
    value: 'Pro/THUDM/glm-4-9b-chat',
    maxTokens: 4096,
  },
];
