import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useSettingStore = defineStore(
  'llm-setting',
  () => {
    const developerPanelEnabled = ref(true);
    const settings = ref({
      model: 'Qwen/Qwen3-14B-Instruct',
      apiKey: import.meta.env.VITE_API_BASE_URL,
      stream: true,
      maxTokens: 32768,
      temperature: 0.7,
      topP: 0.7,
      topK: 50,
      activeTools: ['knowledge_base', 'code_sandbox'],
      modelDisplay: 'qwen3:14b',
      ragK: 4,
      strictMode: false,
      promptKey: 'tutor',
      customSystemPrompt: '',
      debugMode: false,
      forceCache: false,
      forceAgent: '',
      simulateDigitalHumanSuccess: false,
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
        description: '受控补充最新公开信息，回答中会说明来源与合理性',
      },
      {
        key: 'code_sandbox',
        label: '代码沙盒',
        description: '运行轻量 Python 代码用于验证思路',
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
      developerPanelEnabled,
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
    label: 'Qwen3-14B-Instruct',
    value: 'Qwen/Qwen3-14B-Instruct',
    maxTokens: 16384,
  },
  {
    label: 'Qwen3-32B-Instruct',
    value: 'Qwen/Qwen3-32B-Instruct',
    maxTokens: 32768,
  },
  {
    label: 'Qwen3-VL-8B-Instruct',
    value: 'Qwen/Qwen3-VL-8B-Instruct',
    maxTokens: 8192,
  },
  {
    label: 'Qwen3-VL-4B-Instruct',
    value: 'Qwen/Qwen3-VL-4B-Instruct',
    maxTokens: 8192,
  },
  {
    label: 'Qwen3-8B-Instruct',
    value: 'Qwen/Qwen3-8B-Instruct',
    maxTokens: 8192,
  },
];
