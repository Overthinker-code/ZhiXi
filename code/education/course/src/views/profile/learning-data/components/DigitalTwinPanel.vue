<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import {
    BrainCircuit,
    CheckCircle2,
    ChevronDown,
    Circle,
    Clock3,
    Expand,
    Maximize2,
    Minimize2,
    Network,
    Sparkles,
    Target,
    X,
  } from 'lucide-vue-next';
  import MermaidDiagramViewer from '@/components/chat/MermaidDiagramViewer.vue';
  import type { LearnerDigitalTwin } from '@/api/profile';

  const props = defineProps<{
    twin: LearnerDigitalTwin | null;
    loading?: boolean;
  }>();

  const showAllWeaknesses = ref(false);
  const showAllDimensions = ref(false);
  const graphPreviewOpen = ref(false);
  const graphScale = ref(1);
  const graphPan = ref({ x: 0, y: 0 });
  const previewTrigger = ref<HTMLButtonElement | null>(null);
  const graphPreviewRef = ref<HTMLElement | null>(null);
  const graphDragStart = ref<{ x: number; y: number; panX: number; panY: number } | null>(null);

  const styleLabels: Record<string, string> = {
    practice_pdf: '偏好练习与讲义的结构化学习者',
    practice: '偏好通过练习巩固的学习者',
    reading: '偏好通过阅读理解的学习者',
    visual: '偏好图示与结构梳理的学习者',
    video: '偏好视频讲解的学习者',
    mixed: '善于组合多种学习方式的学习者',
  };

  function humanizeLearningEnum(value: string) {
    const standalone = /^(?:practice_(?:pdf|docx)|lecture_(?:pdf|docx)|video|visual|practice|reading|mixed)(?:驱动型学习者)?$/i.test(value.trim());
    return value
      .replace(/practice_(?:pdf|docx)(?:驱动型学习者)?/gi, standalone ? '偏好练习与讲义的结构化学习者' : '练习与讲义')
      .replace(/lecture_(?:pdf|docx)(?:驱动型学习者)?/gi, standalone ? '偏好通过讲义梳理的学习者' : '讲义梳理')
      .replace(/video(?:驱动型学习者)?/gi, standalone ? '偏好视频讲解的学习者' : '视频讲解')
      .replace(/visual(?:驱动型学习者)?/gi, standalone ? '偏好图示与结构梳理的学习者' : '图示与结构梳理')
      .replace(/practice(?:驱动型学习者)?/gi, standalone ? '偏好通过练习巩固的学习者' : '练习巩固')
      .replace(/reading(?:驱动型学习者)?/gi, standalone ? '偏好通过阅读理解的学习者' : '阅读理解')
      .replace(/mixed(?:驱动型学习者)?/gi, standalone ? '善于组合多种学习方式的学习者' : '多种学习方式');
  }

  function cleanStudentText(value: unknown, fallback = '') {
    const text = humanizeLearningEnum(String(value || ''))
      .replace(/Profile\s*Agent|planner\s*agent|resource\s*agent|evaluator\s*agent/gi, '')
      .replace(/(?:规划|资源|评估|画像)\s*(?:Agent|智能体)|持续运行中/gi, '')
      .replace(/\bV\d+\b|画像版本|证据数|可信度/gi, '')
      .replace(/\s{2,}/g, ' ')
      .replace(/^[，、；：\s]+|[，、；：\s]+$/g, '');
    return text || fallback;
  }

  function learningStyleLabel(value: unknown) {
    const raw = String(value || '').trim();
    if (!raw) return '仍在了解你的学习偏好';
    const key = raw.toLowerCase().replace(/[\s-]+/g, '_');
    if (styleLabels[key]) return styleLabels[key];
    const looksLikeInternalStyle =
      /^[a-z][a-z0-9_-]*(?:驱动型学习者)?$/i.test(raw) ||
      /(?:practice|lecture|video|visual|reading|mixed)(?:[_-][a-z0-9]+)*(?:驱动型学习者)?/i.test(raw);
    if (looksLikeInternalStyle) {
      const friendly = humanizeLearningEnum(raw);
      return friendly === raw ? '仍在了解你的学习偏好' : friendly;
    }
    return cleanStudentText(raw, '仍在了解你的学习偏好');
  }

  function shortText(value: unknown, fallback: string, maxLength = 34) {
    const text = cleanStudentText(value, fallback).split(/[。！？!？\n]/)[0].trim();
    return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
  }

  const updatedAt = computed(() => {
    if (!props.twin?.updated_time) return '等待首次画像更新';
    const date = new Date(props.twin.updated_time);
    if (Number.isNaN(date.getTime())) return '画像已更新';
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    }).format(date);
  });

  const strengths = computed(() =>
    (props.twin?.strengths || []).map((item) => cleanStudentText(item)).filter(Boolean).slice(0, 2)
  );
  const weaknesses = computed(() =>
    (props.twin?.weaknesses || []).map((item) => cleanStudentText(item)).filter(Boolean)
  );
  const visibleWeaknesses = computed(() =>
    showAllWeaknesses.value ? weaknesses.value : weaknesses.value.slice(0, 3)
  );
  const visibleDimensions = computed(() => {
    const dimensions = props.twin?.dimensions || [];
    return showAllDimensions.value ? dimensions : dimensions.slice(0, 4);
  });
  const summaryItems = computed(() => [
    {
      label: '优势',
      value: strengths.value.length ? strengths.value.join('、') : '仍在积累稳定表现',
    },
    {
      label: '重点',
      value: weaknesses.value.length ? weaknesses.value.slice(0, 2).join('、') : '继续完成当前学习任务',
    },
    {
      label: '下一步',
      value: shortText(props.twin?.ai_summary, '完成一次练习后查看新的学习建议'),
    },
  ]);
  const recentUpdates = computed(() =>
    (props.twin?.last_updates || [])
      .map((item) => shortText(item, '学习记录已整理', 42))
      .filter(Boolean)
      .slice(0, 2)
  );
  const understanding = computed(() => [
    { label: '学习阶段', value: cleanStudentText(props.twin?.learning_stage, '仍在了解中'), icon: Target },
    { label: '学习类型', value: learningStyleLabel(props.twin?.learning_style), icon: BrainCircuit },
    { label: '主要优势', value: strengths.value.join('、') || '等待学习记录', icon: Sparkles },
    { label: '待提升方向', value: visibleWeaknesses.value.join('、') || '等待学习记录', icon: Network },
  ]);

  const graphCode = computed(() => {
    const graph = props.twin?.knowledge_graph;
    if (!graph?.nodes?.length) return '';
    const idMap = new Map(graph.nodes.map((node, index) => [node.id, `n${index}`]));
    const safe = (value: string) => String(value || '').replace(/["\n\r]/g, ' ').slice(0, 28);
    const lines = ['flowchart LR'];
    graph.nodes.forEach((node, index) => {
      const percent = Math.round(Math.max(0, Math.min(1, Number(node.mastery) || 0)) * 100);
      lines.push(`n${index}["${safe(node.name)} · ${percent}%"]`);
      lines.push(`class n${index} ${percent > 80 ? 'strong' : percent >= 40 ? 'developing' : 'weak'}`);
    });
    graph.edges.forEach((edge) => {
      const source = idMap.get(edge.source);
      const target = idMap.get(edge.target);
      if (source && target) lines.push(`${source} --> ${target}`);
    });
    lines.push('classDef strong fill:#ecfdf3,stroke:#16a34a,color:#166534');
    lines.push('classDef developing fill:#fffbeb,stroke:#f59e0b,color:#92400e');
    lines.push('classDef weak fill:#fef2f2,stroke:#ef4444,color:#991b1b');
    return lines.join('\n');
  });

  function resetGraphView() {
    graphScale.value = 1;
    graphPan.value = { x: 0, y: 0 };
  }

  function fitGraphView() {
    resetGraphView();
  }

  function getDialogFocusableElements() {
    return Array.from(
      graphPreviewRef.value?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      ) || []
    ).filter((element) => !element.hasAttribute('hidden'));
  }

  function focusPreviewStart() {
    getDialogFocusableElements()[0]?.focus();
  }

  function openGraphPreview(event: MouseEvent) {
    previewTrigger.value = event.currentTarget as HTMLButtonElement;
    resetGraphView();
    graphPreviewOpen.value = true;
    void nextTick(focusPreviewStart);
  }

  function closeGraphPreview() {
    graphPreviewOpen.value = false;
    graphDragStart.value = null;
    void nextTick(() => previewTrigger.value?.focus());
  }

  function zoomGraph(delta: number) {
    graphScale.value = Math.min(2.25, Math.max(0.65, Number((graphScale.value + delta).toFixed(2))));
  }

  function onGraphWheel(event: WheelEvent) {
    event.preventDefault();
    zoomGraph(event.deltaY < 0 ? 0.12 : -0.12);
  }

  function startGraphDrag(event: PointerEvent) {
    if (event.button !== 0) return;
    graphDragStart.value = {
      x: event.clientX,
      y: event.clientY,
      panX: graphPan.value.x,
      panY: graphPan.value.y,
    };
    (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  }

  function moveGraphDrag(event: PointerEvent) {
    const start = graphDragStart.value;
    if (!start) return;
    graphPan.value = {
      x: start.panX + event.clientX - start.x,
      y: start.panY + event.clientY - start.y,
    };
  }

  function stopGraphDrag() {
    graphDragStart.value = null;
  }

  function onPreviewKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeGraphPreview();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = getDialogFocusableElements();
    if (!focusable.length) {
      event.preventDefault();
      graphPreviewRef.value?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || active === graphPreviewRef.value)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  watch(graphPreviewOpen, (opened) => {
    if (!opened) resetGraphView();
  });

  onBeforeUnmount(() => {
    graphDragStart.value = null;
  });
</script>

<template>
  <section class="digital-twin" aria-labelledby="digital-twin-title">
    <header class="digital-twin__header">
      <div class="digital-twin__identity">
        <span class="digital-twin__avatar"><BrainCircuit :size="27" /></span>
        <div>
          <div class="digital-twin__eyebrow">学习画像</div>
          <h2 id="digital-twin-title">AI 学习数字分身</h2>
          <p>结合你的学习记录，整理当前优势、重点与下一步。</p>
        </div>
      </div>
      <div class="digital-twin__score">
        <strong>{{ twin?.overall_score ?? '—' }}</strong><span v-if="twin">/100</span>
        <small>综合能力</small>
      </div>
    </header>

    <a-spin :loading="loading" style="width: 100%">
      <div class="understanding" aria-label="当前学习画像">
        <article v-for="item in understanding" :key="item.label">
          <component :is="item.icon" :size="18" />
          <div><small>{{ item.label }}</small><strong>{{ item.value }}</strong></div>
        </article>
      </div>

      <div v-if="weaknesses.length > 3" class="detail-toggle detail-toggle--understanding">
        <button type="button" :aria-expanded="showAllWeaknesses" @click="showAllWeaknesses = !showAllWeaknesses">
          {{ showAllWeaknesses ? '收起待提升方向' : `查看全部 ${weaknesses.length} 项` }}
          <ChevronDown :size="14" :class="{ 'is-open': showAllWeaknesses }" />
        </button>
      </div>

      <div class="digital-twin__body">
        <section class="twin-section update-section">
          <header><Clock3 :size="17" /><h3>近期变化</h3></header>
          <small class="update-time">最近更新：{{ updatedAt }}</small>
          <ul v-if="recentUpdates.length">
            <li v-for="item in recentUpdates" :key="item">
              <CheckCircle2 :size="15" />{{ item }}
            </li>
          </ul>
          <p v-else>完成聊天、练习或资料学习后，这里会显示与你相关的变化。</p>
        </section>

        <section class="twin-section dimension-section">
          <header><BrainCircuit :size="17" /><h3>能力观察维度</h3></header>
          <div v-if="visibleDimensions.length" class="dimension-list">
            <div v-for="item in visibleDimensions" :key="item.key" class="dimension-row">
              <span>{{ item.label }}</span>
              <i><b :style="{ width: `${Math.max(0, Math.min(100, item.score))}%` }" /></i>
              <strong>{{ item.score }}</strong>
            </div>
          </div>
          <p v-else>完成学习活动后，这里会逐步形成能力观察维度。</p>
          <div v-if="(twin?.dimensions?.length || 0) > 4" class="detail-toggle">
            <button type="button" :aria-expanded="showAllDimensions" @click="showAllDimensions = !showAllDimensions">
              {{ showAllDimensions ? '收起完整维度' : `查看完整 ${twin?.dimensions?.length} 项维度` }}
              <ChevronDown :size="14" :class="{ 'is-open': showAllDimensions }" />
            </button>
          </div>
        </section>
      </div>

      <div class="digital-twin__lower">
        <section class="twin-section summary-section">
          <header><Sparkles :size="17" /><h3>学习提示</h3></header>
          <ul class="summary-list">
            <li v-for="item in summaryItems" :key="item.label">
              <strong>{{ item.label }}</strong><span>{{ item.value }}</span>
            </li>
          </ul>
        </section>

        <section class="twin-section graph-section">
          <header>
            <div><Network :size="17" /><h3>知识网络</h3></div>
            <button
              v-if="graphCode"
              type="button"
              class="graph-expand"
              aria-label="展开查看完整知识网络"
              @click="openGraphPreview"
            ><Expand :size="15" />展开查看</button>
          </header>
          <div v-if="graphCode" class="graph-fit" aria-label="知识网络预览，已适配卡片宽度">
            <MermaidDiagramViewer :code="graphCode" />
          </div>
          <p v-else>完成带知识点标签的练习后，这里会形成可查看的知识网络。</p>
          <div v-if="graphCode" class="graph-legend" aria-label="掌握程度图例">
            <span><Circle :size="8" fill="currentColor" />已掌握</span>
            <span><Circle :size="8" fill="currentColor" />发展中</span>
            <span><Circle :size="8" fill="currentColor" />待加强</span>
          </div>
        </section>
      </div>
    </a-spin>

    <Teleport to="body">
      <div
        v-if="graphPreviewOpen"
        class="graph-preview-backdrop"
        role="presentation"
        @click.self="closeGraphPreview"
      >
        <section
          ref="graphPreviewRef"
          class="graph-preview-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="knowledge-network-preview-title"
          tabindex="-1"
          @keydown="onPreviewKeydown"
        >
          <header>
            <div><Network :size="18" /><h2 id="knowledge-network-preview-title">完整知识网络</h2></div>
            <button type="button" aria-label="关闭完整知识网络预览" @click="closeGraphPreview"><X :size="18" /></button>
          </header>
          <div class="graph-preview-toolbar" aria-label="知识网络视图工具">
            <button type="button" aria-label="缩小知识网络" @click="zoomGraph(-0.15)"><Minimize2 :size="16" /></button>
            <span aria-live="polite">{{ Math.round(graphScale * 100) }}%</span>
            <button type="button" aria-label="放大知识网络" @click="zoomGraph(0.15)"><Maximize2 :size="16" /></button>
            <button type="button" @click="fitGraphView"><Expand :size="15" />适配视图</button>
          </div>
          <div
            class="graph-preview-viewport"
            :class="{ 'is-dragging': graphDragStart }"
            aria-label="可缩放和拖动的完整知识网络"
            @wheel="onGraphWheel"
            @pointerdown="startGraphDrag"
            @pointermove="moveGraphDrag"
            @pointerup="stopGraphDrag"
            @pointercancel="stopGraphDrag"
          >
            <div class="graph-preview-canvas" :style="{ transform: `translate(${graphPan.x}px, ${graphPan.y}px) scale(${graphScale})` }">
              <MermaidDiagramViewer :code="graphCode" />
            </div>
          </div>
          <p class="graph-preview-hint">滚轮缩放，拖动查看；按 Esc 或点击背景关闭。</p>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<style scoped lang="less">
  .digital-twin { overflow: hidden; border: 1px solid #dddafe; border-radius: 16px; background: linear-gradient(145deg,#fff 0%,#fbfaff 62%,#f3f5ff 100%); box-shadow: 0 14px 36px rgba(83,72,183,.09); }
  .digital-twin__header { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:22px 24px; border-bottom:1px solid #ebe9ff; background:linear-gradient(100deg,rgba(99,85,231,.08),rgba(52,120,246,.035)); }
  .digital-twin__identity { display:flex; align-items:center; gap:14px; min-width:0; }
  .digital-twin__avatar { display:inline-flex; align-items:center; justify-content:center; width:52px; height:52px; flex:0 0 52px; border-radius:16px; color:#fff; background:linear-gradient(135deg,#6255e7,#3478f6); box-shadow:0 8px 18px rgba(98,85,231,.25); }
  .digital-twin__eyebrow { margin-bottom:3px; color:#6255e7; font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
  h2,h3,p { margin:0; } h2 { color:#172033; font-size:21px; } .digital-twin__identity p { margin-top:5px; color:#667085; font-size:12px; }
  .digital-twin__score { min-width:110px; text-align:right; } .digital-twin__score strong { color:#6255e7; font-size:28px; } .digital-twin__score span { color:#98a2b3; font-size:11px; } .digital-twin__score small { display:block; color:#667085; font-size:10px; }
  .understanding { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; padding:16px 18px 4px; }
  .understanding article { display:flex; align-items:flex-start; gap:10px; min-width:0; padding:13px; border:1px solid #e8eaf3; border-radius:11px; background:rgba(255,255,255,.88); }
  .understanding article>svg { flex:0 0 auto; margin-top:2px; color:#6255e7; } .understanding small,.understanding strong { display:block; } .understanding small { color:#8a94a6; font-size:10px; } .understanding strong { overflow:hidden; margin-top:4px; color:#253047; font-size:12px; line-height:1.5; text-overflow:ellipsis; }
  .digital-twin__body,.digital-twin__lower { display:grid; grid-template-columns:1fr 1.25fr; gap:12px; padding:12px 18px 0; }
  .digital-twin__lower { grid-template-columns:.9fr 1.35fr; padding-bottom:18px; }
  .twin-section { min-width:0; padding:15px; border:1px solid #e8eaf3; border-radius:12px; background:rgba(255,255,255,.91); }
  .twin-section>header { display:flex; align-items:center; justify-content:space-between; gap:7px; margin-bottom:11px; color:#6255e7; } .twin-section>header>div { display:flex; align-items:center; gap:7px; } .twin-section h3 { color:#253047; font-size:13px; }
  .update-time { color:#8993a5; font-size:10px; } .update-section ul { display:flex; flex-direction:column; gap:7px; margin:10px 0 0; padding:0; list-style:none; } .update-section li { display:flex; align-items:flex-start; gap:7px; color:#4d596c; font-size:11px; line-height:1.55; } .update-section li svg { flex:0 0 auto; margin-top:1px; color:#22a06b; } .update-section p,.dimension-section p,.graph-section p { padding:12px 0 2px; color:#7b8799; font-size:11px; line-height:1.6; }
  .dimension-list { display:grid; grid-template-columns:1fr 1fr; gap:9px 14px; } .dimension-row { display:grid; grid-template-columns:90px minmax(40px,1fr) 24px; align-items:center; gap:7px; color:#5c6678; font-size:10px; } .dimension-row>i { height:6px; overflow:hidden; border-radius:99px; background:#edf0f5; } .dimension-row b { display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,#6255e7,#4ea3ff); } .dimension-row>strong { color:#4f46b5; font-size:10px; text-align:right; }
  .detail-toggle { display:flex; justify-content:flex-end; margin-top:10px; } .detail-toggle--understanding { margin:0; padding:0 18px; } .detail-toggle button,.graph-expand,.graph-preview-toolbar button,.graph-preview-dialog>header button { display:inline-flex; align-items:center; justify-content:center; gap:4px; border:0; border-radius:8px; color:#4f46b5; background:#f4f2ff; font-size:10px; font-weight:700; cursor:pointer; } .detail-toggle button { padding:6px 8px; } .detail-toggle svg { transition:transform .18s ease; } .detail-toggle svg.is-open { transform:rotate(180deg); }
  .summary-list { display:flex; flex-direction:column; gap:8px; margin:0; padding:0; list-style:none; } .summary-list li { display:grid; grid-template-columns:42px minmax(0,1fr); gap:8px; align-items:start; padding:8px 9px; border-radius:8px; background:#f8f7ff; color:#4d596c; font-size:11px; line-height:1.5; } .summary-list strong { color:#6255e7; font-size:10px; }
  .graph-expand { padding:6px 8px; } .graph-fit { overflow:hidden; min-height:174px; border-radius:10px; background:#fafbff; } .graph-section :deep(.mermaid-viewer) { display:flex; align-items:center; justify-content:center; min-height:174px; padding:8px; overflow:hidden; border:0; border-radius:0; background:transparent; } .graph-section :deep(.mermaid-viewer__canvas) { min-width:0; width:100%; text-align:center; } .graph-section :deep(.mermaid-viewer__canvas svg) { display:block; width:100% !important; max-width:100%; height:auto !important; max-height:190px; margin:0 auto; } .graph-legend { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:10px; margin-top:7px; font-size:9px; } .graph-legend span { display:inline-flex; align-items:center; gap:3px; } .graph-legend span:nth-child(1){color:#16a34a}.graph-legend span:nth-child(2){color:#d97706}.graph-legend span:nth-child(3){color:#dc2626}
  :global(.graph-preview-backdrop) { position:fixed; z-index:11000; inset:0; display:grid; place-items:center; padding:16px; background:rgba(15,23,42,.52); backdrop-filter:blur(3px); } :global(.graph-preview-dialog) { width:min(1120px,94vw); height:min(760px,calc(100vh - 32px)); display:flex; flex-direction:column; overflow:hidden; border:1px solid rgba(203,213,225,.9); border-radius:20px; background:#fff; box-shadow:0 28px 80px rgba(15,23,42,.32); outline:none; } :global(.graph-preview-dialog>header) { display:flex; align-items:center; justify-content:space-between; padding:16px 18px; border-bottom:1px solid #e8eaf3; } :global(.graph-preview-dialog>header>div) { display:flex; align-items:center; gap:8px; color:#6255e7; } :global(.graph-preview-dialog h2) { font-size:16px; } :global(.graph-preview-dialog>header button) { width:32px; height:32px; color:#475467; background:#f8fafc; } :global(.graph-preview-toolbar) { display:flex; align-items:center; gap:7px; padding:10px 16px; border-bottom:1px solid #eef1f6; } :global(.graph-preview-toolbar button) { min-height:30px; padding:0 9px; } :global(.graph-preview-toolbar span) { min-width:40px; color:#667085; font-size:11px; text-align:center; } :global(.graph-preview-viewport) { min-height:0; flex:1; overflow:hidden; padding:16px 20px; cursor:grab; background:radial-gradient(circle at 1px 1px,#dbe3f4 1px,transparent 0) 0 0/16px 16px,#f8faff; touch-action:none; } :global(.graph-preview-viewport.is-dragging) { cursor:grabbing; } :global(.graph-preview-canvas) { width:100%; height:100%; min-height:0; display:flex; align-items:center; justify-content:center; transform-origin:center center; transition:transform .15s ease; } :global(.graph-preview-viewport.is-dragging .graph-preview-canvas) { transition:none; } :global(.graph-preview-canvas .mermaid-viewer) { width:100%; height:100%; box-sizing:border-box; display:flex; align-items:center; justify-content:center; overflow:visible; padding:0 !important; border:0; background:transparent; } :global(.graph-preview-canvas .mermaid-viewer__canvas) { width:100%; height:100%; min-width:0; text-align:center; } :global(.graph-preview-canvas .mermaid-viewer__canvas svg) { display:block; width:100% !important; height:100% !important; max-width:100%; max-height:100%; margin:0 auto; } :global(.graph-preview-hint) { margin:0; padding:10px 16px 14px; color:#7b8799; font-size:11px; text-align:center; }
  button:focus-visible { outline:3px solid rgba(52,120,246,.4); outline-offset:2px; }
  @media(max-width:900px){.understanding{grid-template-columns:1fr 1fr}.digital-twin__body,.digital-twin__lower{grid-template-columns:1fr}.dimension-list{grid-template-columns:1fr 1fr}}
  @media(max-width:560px){.digital-twin__header{align-items:flex-start;padding:18px}.digital-twin__score{display:none}.understanding{grid-template-columns:1fr}.dimension-list{grid-template-columns:1fr}.digital-twin__body,.digital-twin__lower{padding-right:12px;padding-left:12px}:global(.graph-preview-backdrop){padding:10px}:global(.graph-preview-dialog){width:100%;height:calc(100vh - 20px)}:global(.graph-preview-canvas){min-height:0}}
  @media(prefers-reduced-motion:reduce){.detail-toggle svg,:global(.graph-preview-canvas){transition:none !important;}}
</style>
