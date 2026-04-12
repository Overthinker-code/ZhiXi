<template>
  <div class="knowledge-panels">
    <a-card class="panel-card" title="课堂笔记">
      <div v-if="!notesStarted" class="reveal-stage">
        <p class="reveal-hint">点击按钮整理本节笔记，内容将逐字呈现</p>
        <a-button
          type="primary"
          size="large"
          class="action-btn"
          @click="startNotesTypewriter"
        >
          整理课堂笔记
        </a-button>
      </div>
      <div
        v-else
        class="selectable-wrap"
        @mouseup="() => handleTextSelection('.notes-select-target')"
        @touchend="() => handleTextSelection('.notes-select-target')"
      >
        <div class="notes-select-target course-knowledge-selectable notes-body">
          {{ notesLive }}<span v-if="notesTyping" class="caret">▍</span>
        </div>
      </div>
    </a-card>

    <a-card class="panel-card" title="思维导图">
      <div v-if="!mindActive && !mindDone" class="reveal-stage">
        <a-button
          type="primary"
          size="large"
          class="action-btn mind-btn"
          @click="mindActive = true"
        >
          自动生成思维导图
        </a-button>
      </div>
      <div
        v-else
        class="course-knowledge-selectable graph-select-wrap"
        @mouseup="() => handleTextSelection('.course-knowledge-selectable')"
        @touchend="() => handleTextSelection('.course-knowledge-selectable')"
      >
        <CourseMindMapVisual :active="mindActive" @complete="onMindComplete" />
      </div>
    </a-card>

    <a-card class="panel-card" title="课程知识图谱">
      <div v-if="!graphActive && !graphDone" class="reveal-stage">
        <a-button
          type="primary"
          size="large"
          class="action-btn"
          @click="graphActive = true"
        >
          生成课程知识图谱
        </a-button>
      </div>
      <div
        v-else
        class="course-knowledge-selectable graph-select-wrap"
        @mouseup="() => handleTextSelection('.course-knowledge-selectable')"
        @touchend="() => handleTextSelection('.course-knowledge-selectable')"
      >
        <CourseKnowledgeGraphVisual
          :active="graphActive"
          @complete="onGraphComplete"
        />
      </div>
    </a-card>

    <Transition name="sel-menu">
      <div
        v-if="showContextMenu"
        :style="contextMenuStyle"
        class="ctx-menu notes-context-menu"
      >
        <div class="menu-title">对所选文本执行操作：</div>
        <button
          v-for="t in promptTemplates"
          :key="t.key"
          class="menu-item"
          @click="sendAIQuery(t.key)"
        >
          {{ t.label }}
        </button>
      </div>
    </Transition>

    <svg
      v-if="bridgeLine.active"
      class="selection-bridge"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <line
        :x1="bridgeLine.x1"
        :y1="bridgeLine.y1"
        :x2="bridgeLine.x2"
        :y2="bridgeLine.y2"
        stroke="#a78bfa"
        stroke-width="2.5"
        stroke-linecap="round"
        class="selection-bridge-line"
      />
    </svg>

    <SelectionAiAnswerPanel
      v-if="showAnswerPanel && answerPanelBounds"
      :visible="showAnswerPanel"
      :session="answerPanelSession"
      :initial-bounds="answerPanelBounds"
      :html="renderedResponse"
      :loading="isLoadingResponse"
      :typing="isTypingAnswer"
      @close="clearAi"
    />
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import { onBeforeRouteLeave } from 'vue-router';
  import { RELATION_DB_CLASSROOM_NOTES } from '@/constants/relationDbClassroomNotes';
  import {
    MIND_MAP_CONTEXT_TEXT,
    KNOWLEDGE_GRAPH_CONTEXT_TEXT,
  } from '@/constants/courseVisualContext';
  import { useSelectionQueryMenu } from '@/composables/useSelectionQueryMenu';
  import { useTypewriterText } from '@/composables/useTypewriterText';
  import CourseMindMapVisual from './CourseMindMapVisual.vue';
  import CourseKnowledgeGraphVisual from './CourseKnowledgeGraphVisual.vue';
  import SelectionAiAnswerPanel from './SelectionAiAnswerPanel.vue';

  const notesStarted = ref(false);
  const notesTyping = ref(false);
  const notesComplete = ref(false);
  const mindActive = ref(false);
  const mindDone = ref(false);
  const graphActive = ref(false);
  const graphDone = ref(false);

  const {
    text: notesLive,
    start: startNotesTw,
    reset: resetNotesTw,
    stop: stopNotesTw,
  } = useTypewriterText(380);

  const {
    promptTemplates,
    showContextMenu,
    contextMenuStyle,
    isLoadingResponse,
    aiResponse,
    showAnswerPanel,
    answerPanelBounds,
    answerPanelSession,
    isTypingAnswer,
    renderedResponse,
    bridgeLine,
    handleTextSelection,
    sendAIQuery,
    clearAnswerPanel,
  } = useSelectionQueryMenu(() => {
    let s = '';
    if (notesComplete.value) s += RELATION_DB_CLASSROOM_NOTES;
    else if (notesStarted.value) s += notesLive.value;
    if (mindDone.value) s += ` ${MIND_MAP_CONTEXT_TEXT}`;
    if (graphDone.value) s += ` ${KNOWLEDGE_GRAPH_CONTEXT_TEXT}`;
    return s;
  });

  function startNotesTypewriter() {
    notesStarted.value = true;
    notesTyping.value = true;
    notesComplete.value = false;
    startNotesTw(RELATION_DB_CLASSROOM_NOTES, () => {
      notesTyping.value = false;
      notesComplete.value = true;
    });
  }

  function onMindComplete() {
    mindDone.value = true;
  }

  function onGraphComplete() {
    graphDone.value = true;
  }

  function resetAll() {
    stopNotesTw();
    resetNotesTw();
    notesStarted.value = false;
    notesTyping.value = false;
    notesComplete.value = false;
    mindActive.value = false;
    mindDone.value = false;
    graphActive.value = false;
    graphDone.value = false;
    clearAnswerPanel();
    showContextMenu.value = false;
  }

  onBeforeRouteLeave(() => {
    resetAll();
    return true;
  });

  function clearAi() {
    clearAnswerPanel();
  }
</script>

<style scoped lang="less">
  .knowledge-panels {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 16px;
    width: 100%;
  }

  .panel-card {
    border-radius: 12px;
    border: 1px solid rgba(99, 102, 241, 0.2);
  }

  .reveal-stage {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 140px;
    background: linear-gradient(180deg, #f5fbff 0%, #fafafa 100%);
    border-radius: 8px;
    gap: 12px;
  }

  .reveal-hint {
    margin: 0;
    font-size: 14px;
    color: #5a6b78;
  }

  .action-btn {
    min-width: 200px;
    height: 44px;
    border-radius: 22px;
    background: linear-gradient(135deg, #1677ff, #69b1ff);
    box-shadow: 0 8px 20px rgba(22, 119, 255, 0.35);
  }

  .mind-btn {
    background: linear-gradient(135deg, #0958d9, #69b1ff);
  }

  .selectable-wrap {
    user-select: text;
    cursor: text;
    padding: 12px;
    background: #fafafa;
    border-radius: 8px;
  }

  .graph-select-wrap {
    user-select: text;
    cursor: text;
    padding: 0;
    border-radius: 8px;
    overflow: hidden;
  }

  .notes-body {
    white-space: pre-wrap;
    line-height: 1.75;
    font-size: 14px;
    color: #333;
    min-height: 120px;
  }

  .caret {
    display: inline-block;
    margin-left: 1px;
    color: #1677ff;
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    50% {
      opacity: 0;
    }
  }

  .notes-select-target::selection,
  .graph-select-wrap ::selection {
    background: rgba(99, 102, 241, 0.35);
    color: inherit;
  }

  @keyframes sel-halo-flow {
    0% {
      background-position: 0% 50%;
    }
    100% {
      background-position: 100% 50%;
    }
  }

  .graph-select-wrap {
    position: relative;
  }

  .graph-select-wrap::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 8px;
    pointer-events: none;
    opacity: 0;
    z-index: 1;
    background: linear-gradient(
      120deg,
      rgba(99, 102, 241, 0.12),
      rgba(14, 165, 233, 0.18),
      rgba(139, 92, 246, 0.12)
    );
    background-size: 220% 220%;
    animation: sel-halo-flow 3.5s linear infinite;
  }

  .graph-select-wrap:hover::before {
    opacity: 0.35;
  }

  .ctx-menu {
    position: fixed;
    z-index: 1000;
    min-width: 200px;
    padding: 8px 0;
    border-radius: 14px;
    border: 1px solid rgba(139, 92, 246, 0.45);
    background: rgba(15, 23, 42, 0.42);
    backdrop-filter: blur(20px) saturate(1.4);
    -webkit-backdrop-filter: blur(20px) saturate(1.4);
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.08) inset,
      0 18px 48px rgba(2, 6, 23, 0.45);

    .menu-title {
      padding: 8px 14px 6px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #94a3b8;
      border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    }

    .menu-item {
      display: block;
      width: 100%;
      text-align: left;
      padding: 10px 16px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 13px;
      color: #e2e8f0;
      transition:
        background 0.2s,
        color 0.2s;

      &:hover {
        background: rgba(99, 102, 241, 0.2);
        color: #f8fafc;
      }
    }
  }

  .sel-menu-enter-active,
  .sel-menu-leave-active {
    transition:
      opacity 0.22s ease,
      transform 0.42s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }

  .sel-menu-enter-from,
  .sel-menu-leave-to {
    opacity: 0;
    transform: scale(0.82) translateY(6px);
  }

  .sel-menu-enter-to,
  .sel-menu-leave-from {
    transform: scale(1) translateY(0);
  }

  .selection-bridge {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 999;
  }

  .selection-bridge-line {
    filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.75));
    stroke-dasharray: 8 6;
    animation: sel-bridge-dash 0.65s linear forwards;
  }

  @keyframes sel-bridge-dash {
    from {
      stroke-dashoffset: 40;
      opacity: 0.2;
    }
    to {
      stroke-dashoffset: 0;
      opacity: 1;
    }
  }

</style>
