<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useSettingStore } from '@/store/setting';

  const settingStore = useSettingStore();
  const visible = ref(false);

  const reasoningLevels = [
    { label: '低', value: 3 },
    { label: '中', value: 4 },
    { label: '高', value: 5 },
  ];

  const draft = ref({
    ragK: 4,
    strictMode: false,
    promptKey: 'tutor',
    customSystemPrompt: '',
    stream: true,
    maxTokens: 4096,
    temperature: 0.7,
    topP: 0.7,
    topK: 50,
    activeTools: [] as string[],
  });

  const resetDraft = () => {
    draft.value = {
      ragK: settingStore.settings.ragK,
      strictMode: Boolean(settingStore.settings.strictMode),
      promptKey: settingStore.settings.promptKey,
      customSystemPrompt: settingStore.settings.customSystemPrompt || '',
      stream: Boolean(settingStore.settings.stream),
      maxTokens: Number(settingStore.settings.maxTokens || 4096),
      temperature: Number(settingStore.settings.temperature || 0.7),
      topP: Number(settingStore.settings.topP || 0.7),
      topK: Number(settingStore.settings.topK || 50),
      activeTools: [...(settingStore.settings.activeTools || [])],
    };
  };

  const activePromptDescription = computed(() => {
    const selected = settingStore.promptOptions.find(
      (item) => item.key === draft.value.promptKey
    );
    return selected?.description || '';
  });

  const openDrawer = () => {
    resetDraft();
    visible.value = true;
  };

  const handleCancel = () => {
    resetDraft();
    visible.value = false;
  };

  const handleSave = () => {
    settingStore.settings.ragK = draft.value.ragK;
    settingStore.settings.strictMode = draft.value.strictMode;
    settingStore.settings.promptKey = draft.value.promptKey;
    settingStore.settings.customSystemPrompt = draft.value.customSystemPrompt;
    settingStore.settings.stream = draft.value.stream;
    settingStore.settings.maxTokens = draft.value.maxTokens;
    settingStore.settings.temperature = draft.value.temperature;
    settingStore.settings.topP = draft.value.topP;
    settingStore.settings.topK = draft.value.topK;
    settingStore.settings.activeTools = [...draft.value.activeTools];
    visible.value = false;
  };

  defineExpose({
    openDrawer,
  });
</script>

<template>
  <el-drawer
    v-model="visible"
    title="对话设置"
    direction="rtl"
    size="360px"
    @closed="resetDraft"
  >
    <div class="setting-container">
      <div class="setting-item">
        <div class="setting-label">当前模型</div>
        <div class="readonly-value">{{
          settingStore.settings.modelDisplay
        }}</div>
        <p class="setting-tip">当前仅显示模型，暂不支持切换。</p>
      </div>

      <div class="setting-item">
        <div class="setting-label">推理强度等级</div>
        <el-radio-group v-model="draft.ragK" class="level-group">
          <el-radio-button
            v-for="level in reasoningLevels"
            :key="level.value"
            :label="level.value"
          >
            {{ level.label }}
          </el-radio-button>
        </el-radio-group>
        <p class="setting-tip">强度越高召回片段越多，回答会更慢。</p>
      </div>

      <div class="setting-item">
        <div class="setting-label-row">
          <div class="setting-label">强约束模式</div>
          <el-switch v-model="draft.strictMode" />
        </div>
        <p class="setting-tip">
          开启后必须基于检索片段并附 citation，无法满足时会拒答。
        </p>
      </div>

      <div class="setting-item">
        <div class="setting-label-row">
          <div class="setting-label">流式响应</div>
          <el-switch v-model="draft.stream" />
        </div>
        <p class="setting-tip">
          建议开启：可实时显示多智能体流水线（主管拆解→知识检索→专员/工具→汇总）与正文流式输出。
        </p>
      </div>

      <div class="setting-item">
        <div class="setting-label">MCP工具开关（演示版）</div>
        <el-checkbox-group v-model="draft.activeTools" class="tool-grid">
          <el-checkbox
            v-for="tool in settingStore.toolOptions"
            :key="tool.key"
            :label="tool.key"
          >
            {{ tool.label }}
          </el-checkbox>
        </el-checkbox-group>
      </div>

      <div class="setting-item">
        <div class="setting-label">Max Tokens</div>
        <el-slider v-model="draft.maxTokens" :min="256" :max="8192" :step="128" />
      </div>

      <div class="setting-item">
        <div class="setting-label">Temperature</div>
        <el-slider
          v-model="draft.temperature"
          :min="0"
          :max="1"
          :step="0.1"
          show-input
        />
      </div>

      <div class="setting-item">
        <div class="setting-label">Top-P</div>
        <el-slider v-model="draft.topP" :min="0" :max="1" :step="0.1" show-input />
      </div>

      <div class="setting-item">
        <div class="setting-label">Top-K</div>
        <el-slider v-model="draft.topK" :min="1" :max="100" :step="1" show-input />
      </div>

      <div class="setting-item">
        <div class="setting-label">回答风格 Prompt</div>
        <el-select
          v-model="draft.promptKey"
          class="full-width"
          placeholder="选择回答风格"
        >
          <el-option
            v-for="option in settingStore.promptOptions"
            :key="option.key"
            :label="option.label"
            :value="option.key"
          />
        </el-select>
        <p v-if="activePromptDescription" class="setting-tip">
          {{ activePromptDescription }}
        </p>
      </div>

      <div class="setting-item">
        <div class="setting-label">补充要求（可选）</div>
        <el-input
          v-model="draft.customSystemPrompt"
          type="textarea"
          :rows="4"
          placeholder="例如：优先给结论，再分点解释。"
        />
      </div>

      <div class="actions">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<style lang="scss" scoped>
  .setting-container {
    padding: 20px;
    color: #27272a;
  }

  .setting-item {
    margin-bottom: 24px;
  }

  .setting-label {
    margin-bottom: 8px;
    font-weight: 600;
    color: #111827;
  }

  .setting-label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .readonly-value {
    padding: 10px 12px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #f8fafc;
    color: #0f172a;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .setting-tip {
    margin: 8px 0 0;
    font-size: 12px;
    line-height: 1.5;
    color: #6b7280;
  }

  .level-group {
    width: 100%;
  }

  .full-width {
    width: 100%;
  }

  .actions {
    margin-top: 8px;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .tool-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .level-group :deep(.el-radio-button__inner) {
    color: #165dff;
    border-color: #165dff;
  }

  .level-group
    :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    background: #165dff;
    border-color: #165dff;
    color: #fff;
    box-shadow: -1px 0 0 0 #165dff;
  }

  .actions :deep(.el-button--primary) {
    --el-button-bg-color: #165dff;
    --el-button-border-color: #165dff;
    --el-button-hover-bg-color: #3a7bff;
    --el-button-hover-border-color: #3a7bff;
  }
</style>
