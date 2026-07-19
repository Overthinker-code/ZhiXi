<script setup lang="ts">
  import { computed } from 'vue';
  import {
    BrainCircuit,
    CheckCircle2,
    Clock3,
    Network,
    Sparkles,
    Target,
  } from 'lucide-vue-next';
  import MermaidDiagramViewer from '@/components/chat/MermaidDiagramViewer.vue';
  import type { LearnerDigitalTwin } from '@/api/profile';

  const props = defineProps<{
    twin: LearnerDigitalTwin | null;
    loading?: boolean;
  }>();

  const updatedAt = computed(() => {
    if (!props.twin?.updated_time) return '等待首次画像更新';
    const date = new Date(props.twin.updated_time);
    if (Number.isNaN(date.getTime())) return '画像已更新';
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    }).format(date);
  });

  const understanding = computed(() => [
    { label: '学习阶段', value: props.twin?.learning_stage || '持续观察中', icon: Target },
    { label: '学习类型', value: props.twin?.learning_style || '持续观察型学习者', icon: BrainCircuit },
    { label: '主要优势', value: props.twin?.strengths?.join('、') || '等待有效学习证据', icon: Sparkles },
    { label: '待提升方向', value: props.twin?.weaknesses?.join('、') || '等待有效学习证据', icon: Network },
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
</script>

<template>
  <section class="digital-twin" aria-labelledby="digital-twin-title">
    <header class="digital-twin__header">
      <div class="digital-twin__identity">
        <span class="digital-twin__avatar"><BrainCircuit :size="27" /></span>
        <div>
          <div class="digital-twin__eyebrow"><i /> Profile Agent 持续运行中</div>
          <h2 id="digital-twin-title">AI 学习数字分身</h2>
          <p>基于你的学习行为、知识掌握和 AI 交互，系统正在持续理解你的学习特点。</p>
        </div>
      </div>
      <div class="digital-twin__score">
        <strong>{{ twin?.overall_score ?? 0 }}</strong><span>/100</span>
        <small>综合能力 · V{{ twin?.profile_version ?? 1 }}</small>
      </div>
    </header>

    <a-spin :loading="loading" style="width: 100%">
      <div class="understanding" aria-label="AI 当前对你的理解">
        <article v-for="item in understanding" :key="item.label">
          <component :is="item.icon" :size="18" />
          <div><small>{{ item.label }}</small><strong>{{ item.value }}</strong></div>
        </article>
      </div>

      <div class="digital-twin__body">
        <section class="twin-section update-section">
          <header><Clock3 :size="17" /><h3>AI 画像动态更新</h3></header>
          <small class="update-time">最近更新时间：{{ updatedAt }}</small>
          <ul v-if="twin?.last_updates?.length">
            <li v-for="item in twin.last_updates" :key="item">
              <CheckCircle2 :size="15" />{{ item }}
            </li>
          </ul>
          <p v-else>完成聊天、练习或资料学习后，Profile Agent 会在这里解释本次画像变化。</p>
          <em>画像已自动更新，并同步给规划、资源与评估 Agent</em>
        </section>

        <section class="twin-section dimension-section">
          <header><BrainCircuit :size="17" /><h3>八维 AI 认知模型</h3></header>
          <div class="dimension-list">
            <div v-for="item in twin?.dimensions || []" :key="item.key" class="dimension-row">
              <span>{{ item.label }}</span>
              <i><b :style="{ width: `${item.score}%` }" /></i>
              <strong>{{ item.score }}</strong>
            </div>
          </div>
        </section>
      </div>

      <div class="digital-twin__lower">
        <section class="twin-section summary-section">
          <header><Sparkles :size="17" /><h3>Profile Agent 分析总结</h3></header>
          <blockquote>{{ twin?.ai_summary || '正在积累学习证据，完成首次画像后会生成分析总结。' }}</blockquote>
          <div class="agent-links">
            <span v-for="(value, key) in twin?.agent_links || {}" :key="key" :title="value">
              {{ String(key).replace('_agent', ' Agent') }}
            </span>
          </div>
        </section>

        <section class="twin-section graph-section">
          <header><Network :size="17" /><h3>知识网络画像</h3></header>
          <MermaidDiagramViewer v-if="graphCode" :code="graphCode" />
          <p v-else>完成带知识点标签的练习后，将自动形成可演化的知识网络。</p>
          <div class="graph-legend"><span>● 已掌握</span><span>● 发展中</span><span>● 待加强</span></div>
        </section>
      </div>
    </a-spin>
  </section>
</template>

<style scoped lang="less">
  .digital-twin { overflow: hidden; border: 1px solid #dddafe; border-radius: 16px; background: linear-gradient(145deg,#fff 0%,#fbfaff 62%,#f3f5ff 100%); box-shadow: 0 14px 36px rgba(83,72,183,.09); }
  .digital-twin__header { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:22px 24px; border-bottom:1px solid #ebe9ff; background:linear-gradient(100deg,rgba(99,85,231,.08),rgba(52,120,246,.035)); }
  .digital-twin__identity { display:flex; align-items:center; gap:14px; min-width:0; }
  .digital-twin__avatar { display:inline-flex; align-items:center; justify-content:center; width:52px; height:52px; flex:0 0 52px; border-radius:16px; color:#fff; background:linear-gradient(135deg,#6255e7,#3478f6); box-shadow:0 8px 18px rgba(98,85,231,.25); }
  .digital-twin__eyebrow { display:flex; align-items:center; gap:6px; margin-bottom:3px; color:#6255e7; font-size:10px; font-weight:700; letter-spacing:.04em; }
  .digital-twin__eyebrow i { width:7px; height:7px; border-radius:50%; background:#22c55e; box-shadow:0 0 0 4px rgba(34,197,94,.12); }
  h2,h3,p { margin:0; } h2 { color:#172033; font-size:21px; } .digital-twin__identity p { margin-top:5px; color:#667085; font-size:12px; }
  .digital-twin__score { min-width:110px; text-align:right; } .digital-twin__score strong { color:#6255e7; font-size:28px; } .digital-twin__score span { color:#98a2b3; font-size:11px; } .digital-twin__score small { display:block; color:#667085; font-size:10px; }
  .understanding { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; padding:16px 18px 4px; }
  .understanding article { display:flex; align-items:flex-start; gap:10px; min-width:0; padding:13px; border:1px solid #e8eaf3; border-radius:11px; background:rgba(255,255,255,.88); }
  .understanding article>svg { flex:0 0 auto; margin-top:2px; color:#6255e7; } .understanding small,.understanding strong { display:block; } .understanding small { color:#8a94a6; font-size:10px; } .understanding strong { overflow:hidden; margin-top:4px; color:#253047; font-size:12px; line-height:1.5; text-overflow:ellipsis; }
  .digital-twin__body,.digital-twin__lower { display:grid; grid-template-columns:1fr 1.25fr; gap:12px; padding:12px 18px 0; }
  .digital-twin__lower { grid-template-columns:.9fr 1.35fr; padding-bottom:18px; }
  .twin-section { min-width:0; padding:15px; border:1px solid #e8eaf3; border-radius:12px; background:rgba(255,255,255,.91); }
  .twin-section>header { display:flex; align-items:center; gap:7px; margin-bottom:11px; color:#6255e7; } .twin-section h3 { color:#253047; font-size:13px; }
  .update-time { color:#8993a5; font-size:10px; } .update-section ul { display:flex; flex-direction:column; gap:7px; margin:10px 0; padding:0; list-style:none; } .update-section li { display:flex; align-items:center; gap:7px; color:#4d596c; font-size:11px; } .update-section li svg { color:#22a06b; } .update-section p { margin:14px 0; color:#7b8799; font-size:11px; } .update-section em { display:block; padding:7px 9px; border-radius:7px; color:#6255e7; background:#f4f2ff; font-size:10px; font-style:normal; }
  .dimension-list { display:grid; grid-template-columns:1fr 1fr; gap:9px 14px; } .dimension-row { display:grid; grid-template-columns:90px minmax(40px,1fr) 24px; align-items:center; gap:7px; color:#5c6678; font-size:10px; } .dimension-row>i { height:6px; overflow:hidden; border-radius:99px; background:#edf0f5; } .dimension-row b { display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,#6255e7,#4ea3ff); } .dimension-row>strong { color:#4f46b5; font-size:10px; text-align:right; }
  blockquote { margin:0; padding:12px; border-left:3px solid #6255e7; border-radius:0 8px 8px 0; color:#4d596c; background:#f8f7ff; font-size:11px; line-height:1.75; }
  .agent-links { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; } .agent-links span { padding:4px 7px; border:1px solid #dedaff; border-radius:99px; color:#6255e7; background:#faf9ff; font-size:9px; }
  .graph-section :deep(.mermaid-viewer) { max-height:215px; padding:8px; border:0; background:#fafbff; } .graph-section :deep(.mermaid-viewer__canvas) { min-width:420px; } .graph-section p { padding:22px; color:#7b8799; text-align:center; font-size:11px; }
  .graph-legend { display:flex; justify-content:flex-end; gap:12px; margin-top:7px; font-size:9px; } .graph-legend span:nth-child(1){color:#16a34a}.graph-legend span:nth-child(2){color:#d97706}.graph-legend span:nth-child(3){color:#dc2626}
  @media(max-width:900px){.understanding{grid-template-columns:1fr 1fr}.digital-twin__body,.digital-twin__lower{grid-template-columns:1fr}.dimension-list{grid-template-columns:1fr 1fr}}
  @media(max-width:560px){.digital-twin__header{align-items:flex-start;padding:18px}.digital-twin__score{display:none}.understanding{grid-template-columns:1fr}.dimension-list{grid-template-columns:1fr}.digital-twin__body,.digital-twin__lower{padding-right:12px;padding-left:12px}}
</style>
