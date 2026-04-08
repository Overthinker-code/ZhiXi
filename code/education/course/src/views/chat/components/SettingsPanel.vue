<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useSettingStore, modelOptions } from '@/store/setting';

  const settingStore = useSettingStore();
  const visible = ref(false);

  // MCP 工具列表（后端接口就绪后调用 GET /api/v1/mcp/tools）
  const mcpTools = [
    { key: 'realtime_search', label: '实时网络搜索', desc: '联网检索最新信息' },
    { key: 'local_knowledge', label: '知识图谱记忆', desc: '基于课程知识图谱查询' },
    { key: 'postgresql', label: '数据库交互', desc: '查询课程数据库' },
    { key: 'code_runner', label: '代码执行', desc: '运行并验证代码片段' },
  ];

  const reasoningLevels = [
    { label: '低', value: 3 },
    { label: '中', value: 4 },
    { label: '高', value: 5 },
  ];

  // 工作草稿——不直接写 store，等保存时再提交
  const draft = ref({
    model: 'deepseek-chat',
    stream: true,
    maxTokens: 4096,
    temperature: 0.7,
    topP: 0.7,
    topK: 50,
    ragK: 4,
    strictMode: false,
    promptKey: 'tutor',
    customSystemPrompt: '',
    activeTools: [] as string[],
  });

  const resetDraft = () => {
    const s = settingStore.settings as any;
    draft.value = {
      model: s.model || 'deepseek-chat',
      stream: s.stream !== false,
      maxTokens: s.maxTokens || 4096,
      temperature: s.temperature ?? 0.7,
      topP: s.topP ?? 0.7,
      topK: s.topK ?? 50,
      ragK: s.ragK || 4,
      strictMode: Boolean(s.strictMode),
      promptKey: s.promptKey || 'tutor',
      customSystemPrompt: s.customSystemPrompt || '',
      activeTools: s.activeTools || [],
    };
  };

  const activePromptDescription = computed(() => {
    const selected = settingStore.promptOptions.find(
      (item: any) => item.key === draft.value.promptKey
    );
    return selected?.description || '';
  });

  const selectedModelMaxTokens = computed(() => {
    return (
      modelOptions.find((m) => m.value === draft.value.model)?.maxTokens || 4096
    );
  });

  // Tool Calling 进度模拟（实际接入时通过 SSE 事件更新）
  const toolCallingProgress = ref<{
    active: boolean;
    tool: string;
    step: string;
    progress: number;
  } | null>(null);

  const openDrawer = () => {
    resetDraft();
    visible.value = true;
  };

  const handleCancel = () => {
    resetDraft();
    visible.value = false;
  };

  const handleSave = () => {
    const s = settingStore.settings as any;
    s.model = draft.value.model;
    s.stream = draft.value.stream;
    s.maxTokens = draft.value.maxTokens;
    s.temperature = draft.value.temperature;
    s.topP = draft.value.topP;
    s.topK = draft.value.topK;
    s.ragK = draft.value.ragK;
    s.strictMode = draft.value.strictMode;
    s.promptKey = draft.value.promptKey;
    s.customSystemPrompt = draft.value.customSystemPrompt;
    s.activeTools = draft.value.activeTools;
    visible.value = false;
  };

  defineExpose({ openDrawer, toolCallingProgress });
</script>

<template>
  <a-drawer
    v-model:visible="visible"
    title="助手设置"
    placement="right"
    :width="380"
    @cancel="handleCancel"
  >
    <div class="setting-container">

      <!-- ① 模型选择 -->
      <div class="setting-section">
        <div class="section-title">
          <icon-robot class="section-icon" />模型
        </div>
        <a-select
          v-model="draft.model"
          class="full-width"
          placeholder="选择模型"
        >
          <a-option
            v-for="m in modelOptions"
            :key="m.value"
            :value="m.value"
          >
            <span class="model-label">{{ m.label }}</span>
            <span class="model-tokens">{{ m.maxTokens / 1024 }}K</span>
          </a-option>
        </a-select>
        <p class="setting-tip">当前模型: {{ settingStore.settings.modelDisplay }}</p>
      </div>

      <!-- ② 流式响应 Toggle -->
      <div class="setting-section">
        <div class="setting-label-row section-title">
          <span>
            <icon-thunderbolt class="section-icon" />流式输出
          </span>
          <a-switch v-model="draft.stream" size="small" />
        </div>
        <p class="setting-tip">关闭后等待完整回复再展示，适合截图导出场景。</p>
      </div>

      <!-- ③ 生成参数滑块 -->
      <div class="setting-section">
        <div class="section-title">
          <icon-settings class="section-icon" />生成参数
        </div>

        <div class="param-row">
          <div class="param-label">
            <span>Temperature</span>
            <span class="param-value">{{ draft.temperature }}</span>
          </div>
          <a-slider
            v-model="draft.temperature"
            :min="0"
            :max="2"
            :step="0.05"
            :show-tooltip="false"
          />
          <div class="param-hints">
            <span>保守</span><span>创意</span>
          </div>
        </div>

        <div class="param-row">
          <div class="param-label">
            <span>Max Tokens</span>
            <span class="param-value">{{ draft.maxTokens }}</span>
          </div>
          <a-slider
            v-model="draft.maxTokens"
            :min="256"
            :max="selectedModelMaxTokens"
            :step="256"
            :show-tooltip="false"
          />
        </div>

        <div class="param-row">
          <div class="param-label">
            <span>Top-P</span>
            <span class="param-value">{{ draft.topP }}</span>
          </div>
          <a-slider
            v-model="draft.topP"
            :min="0"
            :max="1"
            :step="0.05"
            :show-tooltip="false"
          />
        </div>

        <div class="param-row">
          <div class="param-label">
            <span>Top-K</span>
            <span class="param-value">{{ draft.topK }}</span>
          </div>
          <a-slider
            v-model="draft.topK"
            :min="0"
            :max="100"
            :step="1"
            :show-tooltip="false"
          />
        </div>
      </div>

      <!-- ④ 推理强度（RAG K） -->
      <div class="setting-section">
        <div class="section-title">
          <icon-search class="section-icon" />知识库检索强度
        </div>
        <a-radio-group v-model="draft.ragK" type="button" class="level-group">
          <a-radio v-for="level in reasoningLevels" :key="level.value" :value="level.value">
            {{ level.label }}
          </a-radio>
        </a-radio-group>
        <p class="setting-tip">强度越高召回片段越多，响应会稍慢。</p>
      </div>

      <!-- ⑤ MCP 工具多选 -->
      <div class="setting-section">
        <div class="section-title">
          <icon-tool class="section-icon" />MCP 工具
          <a-tag size="small" color="arcoblue" style="margin-left: 6px">Beta</a-tag>
        </div>
        <div class="mcp-tools-list">
          <div
            v-for="tool in mcpTools"
            :key="tool.key"
            class="mcp-tool-item"
            :class="{ active: draft.activeTools.includes(tool.key) }"
            @click="
              draft.activeTools.includes(tool.key)
                ? (draft.activeTools = draft.activeTools.filter((t) => t !== tool.key))
                : draft.activeTools.push(tool.key)
            "
          >
            <a-checkbox
              :model-value="draft.activeTools.includes(tool.key)"
              @change="() => {}"
              class="tool-checkbox"
            />
            <div class="tool-meta">
              <span class="tool-label">{{ tool.label }}</span>
              <span class="tool-desc">{{ tool.desc }}</span>
            </div>
          </div>
        </div>
        <p class="setting-tip">选中的工具将在对话时自动调用。</p>
      </div>

      <!-- ⑥ Tool Calling 进度展示 -->
      <transition name="tool-progress">
        <div v-if="toolCallingProgress?.active" class="tool-calling-progress">
          <div class="tcp-header">
            <span class="tcp-dot"></span>
            <span>工具调用: {{ toolCallingProgress.tool }}</span>
          </div>
          <p class="tcp-step">{{ toolCallingProgress.step }}</p>
          <a-progress
            :percent="toolCallingProgress.progress"
            :show-text="false"
            size="small"
            status="normal"
          />
        </div>
      </transition>

      <!-- ⑦ 强约束模式 -->
      <div class="setting-section">
        <div class="setting-label-row section-title">
          <span>
            <icon-lock class="section-icon" />强约束模式
          </span>
          <a-switch v-model="draft.strictMode" size="small" />
        </div>
        <p class="setting-tip">
          开启后回答必须基于检索片段并附 citation，无法满足时会拒答。
        </p>
      </div>

      <!-- ⑧ 回答风格 -->
      <div class="setting-section">
        <div class="section-title">
          <icon-message class="section-icon" />回答风格 Prompt
        </div>
        <a-select
          v-model="draft.promptKey"
          class="full-width"
          placeholder="选择回答风格"
        >
          <a-option
            v-for="option in settingStore.promptOptions"
            :key="option.key"
            :value="option.key"
          >
            {{ option.label }}
          </a-option>
        </a-select>
        <p v-if="activePromptDescription" class="setting-tip">
          {{ activePromptDescription }}
        </p>
      </div>

      <!-- ⑨ 补充要求 -->
      <div class="setting-section">
        <div class="section-title">
          <icon-edit class="section-icon" />补充要求（可选）
        </div>
        <a-textarea
          v-model="draft.customSystemPrompt"
          :auto-size="{ minRows: 3, maxRows: 5 }"
          placeholder="例如：优先给结论，再分点解释。"
        />
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="drawer-footer">
        <a-button @click="handleCancel">取消</a-button>
        <a-button type="primary" @click="handleSave">保存设置</a-button>
      </div>
    </template>
  </a-drawer>
</template>

<style lang="less" scoped>
  .setting-container {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 0;
  }

  .setting-section {
    padding: 14px 20px;
    border-bottom: 1px solid var(--color-border-1);

    &:last-child {
      border-bottom: none;
    }
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 12px;
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-1);
    letter-spacing: -0.1px;
  }

  .section-icon {
    font-size: 14px;
    color: #165dff;
    flex-shrink: 0;
  }

  .setting-label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 0;
  }

  .full-width {
    width: 100%;
  }

  .setting-tip {
    margin: 8px 0 0;
    font-size: 12px;
    line-height: 1.5;
    color: var(--color-text-3);
    letter-spacing: -0.05px;
  }

  // 模型选项内部布局
  .model-label {
    flex: 1;
    font-size: 13px;
  }

  .model-tokens {
    font-size: 11px;
    color: var(--color-text-3);
    font-variant-numeric: tabular-nums;
    margin-left: 8px;
  }

  // 参数滑块
  .param-row {
    margin-bottom: 14px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .param-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    font-size: 12px;
    color: var(--color-text-2);
  }

  .param-value {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    color: #165dff;
    min-width: 36px;
    text-align: right;
  }

  .param-hints {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--color-text-4);
    margin-top: 2px;
  }

  // RAG 强度
  .level-group {
    width: 100%;

    :deep(.arco-radio-button) {
      flex: 1;
      text-align: center;
    }
  }

  // MCP 工具列表
  .mcp-tools-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .mcp-tool-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border: 1px solid var(--color-border-2);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s ease;
    user-select: none;

    &:hover {
      background: var(--color-fill-1);
      border-color: var(--color-border-1);
    }

    &.active {
      background: rgba(22, 93, 255, 0.06);
      border-color: rgba(22, 93, 255, 0.3);
    }
  }

  .tool-checkbox {
    pointer-events: none;
    flex-shrink: 0;
  }

  .tool-meta {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .tool-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text-1);
    letter-spacing: -0.1px;
  }

  .tool-desc {
    font-size: 11px;
    color: var(--color-text-3);
  }

  // Tool Calling 进度
  .tool-calling-progress {
    margin: 0 20px 8px;
    padding: 10px 12px;
    background: rgba(22, 93, 255, 0.06);
    border: 1px solid rgba(22, 93, 255, 0.2);
    border-radius: 8px;
  }

  .tcp-header {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 12px;
    font-weight: 600;
    color: #165dff;
    margin-bottom: 4px;
  }

  .tcp-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #165dff;
    animation: blink 1s ease-in-out infinite;
  }

  .tcp-step {
    font-size: 11px;
    color: var(--color-text-3);
    margin: 0 0 8px;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .tool-progress-enter-active,
  .tool-progress-leave-active {
    transition: all 0.25s ease;
  }

  .tool-progress-enter-from,
  .tool-progress-leave-to {
    opacity: 0;
    transform: translateY(-8px);
  }

  // Footer
  .drawer-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 12px 20px;
  }
</style>
