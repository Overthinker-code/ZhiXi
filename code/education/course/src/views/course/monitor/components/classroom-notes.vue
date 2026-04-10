<template>
  <a-card class="general-card" :title="$t('monitor.title.classroomNotes') || '课堂笔记'">
    <template #extra>
      <a-select
        v-model="currentPromptKey"
        :options="promptTemplateOptions"
        style="width: 150px"
        @change="handlePromptChange"
      />
    </template>

    <div class="classroom-notes-wrapper">
      <!-- 笔记内容区域 - 支持划词 -->
      <div
        class="notes-content"
        @mouseup="handleTextSelection"
        @touchend="handleTextSelection"
      >
        <div class="notes-text">
          {{ notesContent }}
        </div>
      </div>

      <!-- 划词菜单 -->
      <div
        v-if="showContextMenu"
        :style="contextMenuStyle"
        class="context-menu"
      >
        <div class="menu-title">对所选文本执行操作：</div>
        <button
          v-for="template in promptTemplates"
          :key="template.key"
          class="menu-item"
          @click="handlePromptSelect(template.key)"
        >
          {{ template.label }}
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoadingResponse" class="loading-indicator">
        <a-spin />
      </div>

      <!-- AI 响应区域 -->
      <div v-if="aiResponse" class="ai-response">
        <div class="response-header">
          <span class="response-title">AI 解答</span>
          <button class="close-btn" @click="aiResponse = null">✕</button>
        </div>
        <div class="response-content markdown-body" v-html="renderedResponse"></div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
  import { ref, computed, reactive } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { renderMarkdown } from '@/utils/markdown';
  import { useChatStore } from '@/store/chat';
  import { askSelectionQuery } from '@/api/rag';
  import { useSettingStore } from '@/store/setting';
  import { messageHandler } from '@/utils/messageHandler';

  // ==================== 状态变量 ====================
  const chatStore = useChatStore();
  const settingStore = useSettingStore();

  // 硬编码的课堂笔记内容（数据库教学课程示例）
  const notesContent = `关系数据库基础概念

1. 关系模型概述
关系模型是由Edgar F. Codd于1970年提出的，它将数据组织成二维表格形式。在关系模型中，所有数据都被存储在表（relation）中，表由行（row/tuple）和列（column/attribute）组成。每个表代表一个实体集合，表中的每一行代表一个实体。

2. 关键概念
- 表（Table）：关系数据库中的基本结构，由行和列组成
- 属性（Attribute）：表中的列，代表实体的一个特征
- 元组（Tuple）：表中的一行，代表一个具体的实体实例
- 域（Domain）：属性的取值范围，定义了合法的数据值
- 关键字（Key）：用于唯一标识行的属性或属性组合

3. 数据完整性约束
- 实体完整性：确保每个表都有唯一的主键，主键值不能为NULL
- 参照完整性：维护表间的参照关系，外键必须是被参照表的有效主键值
- 用户定义的完整性：由用户定义的特定业务规则，如属性值范围约束

4. 规范化理论
数据库规范化是设计高效关系数据库的重要方法。通过消除冗余和异常，改进数据库结构。常见的规范化级别包括：
- 第一范式（1NF）：消除重复组
- 第二范式（2NF）：完全函数依赖
- 第三范式（3NF）：消除传递依赖
- BCNF：更强的三范式

5. SQL操作
SELECT：从一个或多个表中查询数据
INSERT：向表中插入新记录
UPDATE：修改表中的现有记录
DELETE：从表中删除记录
JOIN：连接多个表进行复杂查询

6. 事务处理
事务是数据库中一个逻辑工作单位，由一系列SQL语句组成。事务必须满足ACID特性：
- 原子性（Atomicity）：事务要么全部执行，要么不执行
- 一致性（Consistency）：事务执行后，数据库从一个一致状态变为另一个一致状态
- 隔离性（Isolation）：并发事务之间相互隔离
- 持久性（Durability）：提交的事务对数据库的修改是持久的

7. 索引机制
索引是提高查询性能的关键技术。常见的索引类型包括：
- B树索引：最常用的索引结构
- 哈希索引：适合等值查询
- 全文索引：用于文本搜索
- 位图索引：适合低基数属性

本课程重点学习的内容包括SQL编程、事务处理、性能优化和并发控制等核心技术。`;

  // 预设的Prompt模板选项
  const promptTemplates = ref([
    {
      key: 'explain',
      label: '📖 解释概念',
      prompt: (selected: string) =>
        `请用简白易懂的方式解释以下数据库概念：\n"${selected}"\n\n要求：先给定义，再举实例，最后说明实际应用。`,
    },
    {
      key: 'example',
      label: '💡 举个例子',
      prompt: (selected: string) =>
        `关于"${selected}"这个概念，请给出：\n1. 一个具体的现实生活中的例子\n2. 对应的数据库表结构示例\n3. 相关的SQL语句`,
    },
    {
      key: 'summarize',
      label: '📝 总结代码',
      prompt: (selected: string) =>
        `请总结以下代码段或内容的核心要点：\n"${selected}"\n\n要求：用3-5条关键点概括，每条简洁清晰`,
    },
    {
      key: 'deepdive',
      label: '🔍 深入讲解',
      prompt: (selected: string) =>
        `请对"${selected}"进行深入讲解，包括：\n1. 原理和机制\n2. 常见的做法或最佳实践\n3. 可能的陷阱和注意事项`,
    },
  ]);

  // UI状态
  const showContextMenu = ref(false);
  const contextMenuStyle = reactive({
    position: 'fixed',
    top: '0px',
    left: '0px',
  });
  const selectedText = ref('');
  const surroundingContext = ref('');
  const isLoadingResponse = ref(false);
  const aiResponse = ref('');
  const currentPromptKey = ref('explain');
  const currentThreadId = computed(
    () => chatStore.currentConversationId || 'default-notes-thread'
  );

  // ==================== 计算属性 ====================
  const promptTemplateOptions = computed(() =>
    promptTemplates.value.map((t) => ({
      label: t.label,
      value: t.key,
    }))
  );

  const renderedResponse = computed(() => {
    if (!aiResponse.value) return '';
    return renderMarkdown(aiResponse.value);
  });

  // ==================== 方法 ====================
  /**
   * 处理文本选中事件
   * 监听 mouseup 和 touchend，检测用户是否选中了文本
   */
  function handleTextSelection(event: Event) {
    const target = event.target as HTMLElement;
    if (!target.closest('.notes-text')) {
      return;
    }

    const selection = window.getSelection();
    if (!selection || selection.toString().length === 0) {
      showContextMenu.value = false;
      return;
    }

    selectedText.value = selection.toString().trim();
    if (selectedText.value.length === 0) {
      showContextMenu.value = false;
      return;
    }

    // 获取周围文本作为上下文（选中文本前后100个字符）
    const fullText = notesContent;
    const startIndex = fullText.indexOf(selectedText.value);
    const endIndex = startIndex + selectedText.value.length;

    const contextStart = Math.max(0, startIndex - 100);
    const contextEnd = Math.min(fullText.length, endIndex + 100);

    surroundingContext.value = fullText.substring(contextStart, contextEnd);

    // 计算菜单位置（在选中文本上方或下方）
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    contextMenuStyle.top = `${window.scrollY + rect.top - 10}px`;
    contextMenuStyle.left = `${window.scrollX + rect.left}px`;

    showContextMenu.value = true;
  }

  /**
   * 处理 Prompt 模板选择
   */
  function handlePromptSelect(templateKey: string) {
    currentPromptKey.value = templateKey;
    sendAIQuery(templateKey);
  }

  /**
   * 处理 Prompt 下拉菜单变化
   */
  function handlePromptChange(key: string) {
    if (selectedText.value) {
      sendAIQuery(key);
    }
  }

  /**
   * 发送 AI 查询
   */
  async function sendAIQuery(promptKey: string) {
    if (!selectedText.value) {
      Message.info('请先选中文本');
      return;
    }

    const template = promptTemplates.value.find((t) => t.key === promptKey);
    if (!template) {
      Message.error('未找到匹配的模板');
      return;
    }

    // 构建自定义系统提示词
    const systemPrompt = template.prompt(selectedText.value);

    isLoadingResponse.value = true;
    aiResponse.value = '';
    showContextMenu.value = false;

    try {
      const response = await askSelectionQuery(
        selectedText.value,
        surroundingContext.value,
        currentThreadId.value,
        {
          systemPrompt,
          ragK: settingStore.settings.ragK as 3 | 4 | 5,
          promptKey: 'custom',
          strictMode: settingStore.settings.strictMode,
          activeTools: settingStore.settings.activeTools || [],
          maxTokens: 2000,
          temperature: 0.7,
        }
      );

      // 解析响应
      if (response?.response) {
        aiResponse.value = response.response;

        // 同时保存到聊天记录中（可选）
        if (chatStore) {
          chatStore.addMessage(
            messageHandler.formatMessage('user', selectedText.value)
          );
          chatStore.addMessage(
            messageHandler.formatMessage('assistant', response.response)
          );
        }
      } else {
        Message.error('AI 响应为空');
      }
    } catch (error) {
      console.error('查询失败:', error);
      Message.error(`查询失败: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      isLoadingResponse.value = false;
    }
  }
</script>

<style scoped lang="less">
  .classroom-notes-wrapper {
    position: relative;
    min-height: 300px;
  }

  .notes-content {
    position: relative;
    padding: 20px;
    background-color: #f9fafc;
    border-radius: 8px;
    margin-bottom: 20px;
    border: 1px solid #e5e7eb;
    user-select: text; // 允许文本选中
    cursor: text;

    .notes-text {
      color: #333;
      line-height: 1.8;
      font-size: 14px;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
  }

  // 划词上下文菜单
  .context-menu {
    position: fixed;
    background: white;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    padding: 8px 4px;
    min-width: 160px;

    .menu-title {
      padding: 8px 12px;
      font-size: 12px;
      color: #666;
      font-weight: 500;
      border-bottom: 1px solid #f0f0f0;
      margin-bottom: 4px;
    }

    .menu-item {
      display: block;
      width: 100%;
      padding: 8px 12px;
      text-align: left;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 13px;
      color: #333;
      transition: all 0.3s ease;
      border-radius: 4px;

      &:hover {
        background-color: #f5f5f5;
        color: #1890ff;
      }

      &:active {
        background-color: #e6f7ff;
      }
    }
  }

  // 加载指示
  .loading-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    color: #666;
  }

  // AI 响应区域
  .ai-response {
    margin-top: 20px;
    padding: 16px;
    background-color: #f0f7ff;
    border-left: 4px solid #1890ff;
    border-radius: 6px;
    animation: slideIn 0.3s ease-out;

    .response-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-weight: 500;
      color: #1890ff;

      .response-title {
        font-size: 14px;
      }

      .close-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: #999;
        font-size: 16px;
        transition: color 0.2s;

        &:hover {
          color: #666;
        }
      }
    }

    .response-content {
      font-size: 13px;
      line-height: 1.8;
      color: #333;

      :deep(p) {
        margin: 0.5em 0;
      }

      :deep(code:not(pre code)) {
        padding: 0.16em 0.38em;
        border-radius: 0.3rem;
        font-size: 0.86em;
        background: #e6f7ff;
        color: #0050b3;
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
      }

      :deep(pre) {
        padding: 12px;
        background: #f5f5f5;
        border-radius: 4px;
        overflow-x: auto;
        margin: 0.5em 0;
      }

      :deep(blockquote) {
        margin: 0.5em 0;
        padding: 0.4rem 0.75rem;
        border-left: 3px solid #1890ff;
        background: white;
        color: #555;
        border-radius: 0 4px 4px 0;
      }

      :deep(ul),
      :deep(ol) {
        margin: 0.5em 0;
        padding-left: 1.5em;
      }

      :deep(li) {
        margin: 0.25em 0;
      }
    }
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  // Markdown 样式
  :deep(.markdown-body) {
    font-size: 13px;
    line-height: 1.8;

    p {
      margin: 0.5em 0;
    }

    strong {
      font-weight: 600;
    }

    em {
      font-style: italic;
    }
  }
</style>
