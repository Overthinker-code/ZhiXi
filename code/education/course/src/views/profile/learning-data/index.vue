<template>
  <div class="container">
    <Breadcrumb :items="['menu.profile', 'menu.profile.learningData']" />
    <a-row :gutter="16">
      <a-col :xs="24" :lg="8">
        <a-card title="学生画像" class="card-block">
          <div class="profile-row">
            <a-avatar :size="72">
              <img
                alt=""
                src="https://api.dicebear.com/7.x/avataaars/svg?seed=study"
              />
            </a-avatar>
            <div class="profile-meta">
              <div><strong>姓名</strong> {{ displayName }}</div>
              <div><strong>学号</strong> 12345689</div>
              <div><strong>专业</strong> 计算机科学与技术</div>
            </div>
          </div>
          <a-divider />
          <div class="section-title">本学期已选课程</div>
          <ul class="course-ul">
            <li v-for="c in enrolled" :key="c">《{{ c }}》</li>
          </ul>
        </a-card>

        <a-card title="日历提醒" class="card-block">
          <a-calendar v-model="calValue" mode="month" class="mini-cal" />
          <a-divider style="margin: 12px 0" />
          <div class="event-list">
            <div v-for="(row, i) in eventRows" :key="i" class="event-row">
              <span class="event-date">{{ row.date }}</span>
              <span class="event-desc">{{ row.desc }}</span>
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="16">
        <a-card class="card-block action-block" title="AI 学情助手">
          <div class="action-copy">
            <h3>个性化学情诊断与学习建议</h3>
            <p>
              结合近期学习表现、课堂互动与练习情况，为你生成阶段诊断、错题复盘与复习安排，帮助你更清晰地把握当前进度与提升方向。
            </p>
          </div>
          <div class="action-row">
            <a-button
              type="primary"
              :loading="loadingDiagnosis"
              @click="handleRunDiagnosis"
            >
              一键诊断学情
            </a-button>
            <a-button
              status="success"
              :loading="loadingMistakes"
              @click="handleGenerateMistakes"
            >
              一键整理错题
            </a-button>
            <a-button
              status="warning"
              :loading="loadingPlan"
              @click="handleGeneratePlan"
            >
              一键生成复习计划
            </a-button>
          </div>
        </a-card>

        <!-- 课堂行为数据（来自CV检测） -->
        <a-card title="课堂行为数据" class="card-block">
          <a-spin :loading="loadingDiagnosis" style="width: 100%">
            <template v-if="behaviorStats && behaviorStats.length">
              <a-row :gutter="12">
                <a-col v-for="s in behaviorStats" :key="s.label" :span="8">
                  <div class="stat-box">
                    <div class="stat-num">{{ s.value }}</div>
                    <div class="stat-label">{{ s.label }}</div>
                  </div>
                </a-col>
              </a-row>

              <!-- Bloom认知分布 -->
              <div v-if="behaviorBloomBars.length" class="bloom-section">
                <a-divider orientation="left">🎯 Bloom认知分布</a-divider>
                <div class="bloom-bar-list">
                  <div v-for="b in behaviorBloomBars" :key="b.label" class="bloom-bar-row">
                    <span class="bloom-bar-label">{{ b.label }}</span>
                    <a-progress :percent="Math.round(b.value * 100)" size="small" style="flex: 1;" />
                    <span class="bloom-bar-pct">{{ (b.value * 100).toFixed(0) }}%</span>
                  </div>
                </div>
              </div>

              <!-- 教育学理论分析 -->
              <div v-if="eduTheoryAnalysis.length" class="theory-section">
                <a-divider orientation="left">🎓 教育学理论驱动分析</a-divider>
                <div class="theory-list">
                  <div v-for="(t, idx) in eduTheoryAnalysis" :key="idx" class="theory-item">
                    <div class="theory-header">
                      <span class="theory-icon">{{ t.icon }}</span>
                      <span class="theory-name">{{ t.theory }}</span>
                    </div>
                    <div class="theory-insight">{{ t.insight }}</div>
                  </div>
                </div>
              </div>

              <div v-if="behaviorNote" class="behavior-note">
                <a-tag color="arcoblue">教师备注</a-tag>
                <span class="note-text">{{ behaviorNote }}</span>
              </div>
            </template>
            <a-empty v-else description="暂无课堂行为数据，请先上传课堂图片或视频进行分析" />
          </a-spin>
        </a-card>

        <a-card title="学情概况" class="card-block">
          <a-row :gutter="12">
            <a-col v-for="s in stats" :key="s.label" :span="8">
              <div class="stat-box">
                <div class="stat-num">{{ s.value }}</div>
                <div class="stat-label">{{ s.label }}</div>
              </div>
            </a-col>
          </a-row>
        </a-card>

        <a-card title="AI 诊断结果" class="card-block">
          <a-spin :loading="loadingDiagnosis" style="width: 100%">
            <template v-if="diagnosis">
              <div class="report-summary">{{ diagnosis.summary }}</div>
              <div class="meta-line">
                <span class="meta-pill">{{ riskLabel(diagnosis.risk_level) }}</span>
                <span v-if="diagnosis.current_goal" class="meta-pill meta-pill--soft">
                  当前目标：{{ diagnosis.current_goal }}
                </span>
                <span
                  v-if="diagnosis.learning_style"
                  class="meta-pill meta-pill--soft"
                >
                  学习偏好：{{ diagnosis.learning_style }}
                </span>
              </div>
              <div v-if="diagnosis.weak_points.length" class="tag-row">
                <span
                  v-for="item in diagnosis.weak_points"
                  :key="item"
                  class="info-tag"
                >
                  {{ item }}
                </span>
              </div>
              <div class="dual-grid">
                <div class="insight-box">
                  <div class="box-title">优势表现</div>
                  <ul class="plain-list">
                    <li v-for="item in diagnosis.strengths" :key="item">{{ item }}</li>
                  </ul>
                </div>
                <div class="insight-box">
                  <div class="box-title">建议动作</div>
                  <ul class="plain-list">
                    <li v-for="item in diagnosis.recommended_actions" :key="item">
                      {{ item }}
                    </li>
                  </ul>
                </div>
              </div>
            </template>
            <a-empty v-else description="点击上方按钮生成最新学情诊断" />
          </a-spin>
        </a-card>

        <a-card title="错题整理与复盘建议" class="card-block">
          <a-spin :loading="loadingMistakes" style="width: 100%">
            <template v-if="mistakeDigest">
              <div class="report-summary">{{ mistakeDigest.summary }}</div>
              <div class="mistake-list">
                <div
                  v-for="item in mistakeDigest.mistakes"
                  :key="item.title"
                  class="mistake-card"
                >
                  <div class="mistake-title">{{ item.title }}</div>
                  <div class="mistake-line">
                    <strong>表现：</strong>{{ item.symptom }}
                  </div>
                  <div class="mistake-line">
                    <strong>依据：</strong>{{ item.evidence }}
                  </div>
                  <div class="mistake-line">
                    <strong>修正：</strong>{{ item.fix_strategy }}
                  </div>
                </div>
              </div>
              <div v-if="mistakeDigest.flashcards.length" class="flashcard-box">
                <div class="box-title">速记卡片</div>
                <ul class="plain-list">
                  <li v-for="item in mistakeDigest.flashcards" :key="item">{{ item }}</li>
                </ul>
              </div>
            </template>
            <a-empty v-else description="点击“一键整理错题”生成复盘清单" />
          </a-spin>
        </a-card>

        <a-card title="三天复习计划" class="card-block">
          <a-spin :loading="loadingPlan" style="width: 100%">
            <template v-if="reviewPlan">
              <div class="report-summary">{{ reviewPlan.summary }}</div>
              <div v-if="reviewPlan.focus_topics.length" class="tag-row">
                <span
                  v-for="item in reviewPlan.focus_topics"
                  :key="item"
                  class="info-tag info-tag--warm"
                >
                  {{ item }}
                </span>
              </div>
              <div class="plan-grid">
                <div v-for="item in reviewPlan.daily_plan" :key="item.day_label" class="plan-card">
                  <div class="plan-day">{{ item.day_label }}</div>
                  <div class="plan-focus">{{ item.focus }}</div>
                  <ul class="plain-list">
                    <li v-for="task in item.tasks" :key="task">{{ task }}</li>
                  </ul>
                </div>
              </div>
              <div v-if="reviewPlan.checkpoints.length" class="flashcard-box">
                <div class="box-title">复习检查点</div>
                <ul class="plain-list">
                  <li v-for="item in reviewPlan.checkpoints" :key="item">{{ item }}</li>
                </ul>
              </div>
            </template>
            <a-empty v-else description="点击“一键生成复习计划”安排接下来三天的学习闭环" />
          </a-spin>
        </a-card>

        <a-card title="学情预警" class="card-block">
          <a-list :bordered="false" size="small">
            <a-list-item v-for="(w, i) in warnings" :key="i">
              <span class="w-date">{{ w.date }}</span>
              <span class="w-text">{{ w.text }}</span>
            </a-list-item>
          </a-list>
        </a-card>

        <a-card title="学习时长占比" class="card-block">
          <div class="donut-wrap">
            <div class="donut" :style="donutStyle" />
            <ul class="legend">
              <li v-for="p in pieParts" :key="p.name">
                <span class="dot" :style="{ background: p.color }" />
                {{ p.name }}：{{ p.pct }}%
              </li>
            </ul>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useUserStore } from '@/store';
  import {
    fetchLearningReport,
    generateMistakeDigest,
    generateReviewPlan,
    runLearningDiagnosis,
    type LearningReport,
    type MistakeDigest,
    type ReviewPlan,
  } from '@/api/rag';

  const userStore = useUserStore();
  const displayName = computed(() => userStore.name || '同学');

  const diagnosis = ref<LearningReport | null>(null);
  const reviewPlan = ref<ReviewPlan | null>(null);
  const mistakeDigest = ref<MistakeDigest | null>(null);
  const loadingDiagnosis = ref(false);
  const loadingPlan = ref(false);
  const loadingMistakes = ref(false);

  const enrolled = [
    '计算机组成原理',
    '操作系统',
    '计算机网络',
    '数据库原理',
    '算法设计与分析',
  ];

  const calValue = ref(new Date(2025, 4, 10));

  const eventRows = [
    { date: '5月8日', desc: 'task4 截止 · 计算机网络课程' },
    { date: '5月10日', desc: '实验1 截止 · 计算机组成原理' },
    { date: '5月15日', desc: '计算机网络课程' },
  ];

  const stats = [
    { label: '云端时长', value: 11 },
    { label: '讨论次数', value: 2 },
    { label: '互动次数', value: 4 },
    { label: '缺勤次数', value: 0 },
    { label: '考勤次数', value: 15 },
    { label: '平均成绩', value: 91 },
  ];

  const warnings = [
    { date: '2025.4.27', text: '操作系统 — 上课无故缺席' },
    { date: '2025.4.23', text: '计算机网络 — 实验作业未提交' },
    { date: '2025.3.15', text: '算法设计与分析 — 未发布讨论' },
    { date: '2025.2.25', text: '计算机组成原理 — 测试成绩不佳' },
  ];

  const pieParts = [
    { name: '计算机组成原理', pct: 29.66, color: '#6366f1' },
    { name: '计算机网络', pct: 26.27, color: '#1677FF' },
    { name: '操作系统', pct: 22.88, color: '#2563eb' },
    { name: '算法设计与分析', pct: 21.19, color: '#0ea5e9' },
  ];

  const donutStyle = computed(() => {
    let start = 0;
    const segs = pieParts.map((p) => {
      const deg = (p.pct / 100) * 360;
      const current = `${p.color} ${start}deg ${start + deg}deg`;
      start += deg;
      return current;
    });
    return {
      background: `conic-gradient(${segs.join(', ')})`,
    };
  });

  const riskLabel = (value: string) => {
    if (value === 'high') return '高风险';
    if (value === 'low') return '低风险';
    return '中风险';
  };

  // 课堂行为数据（来自CV检测 → 学情诊断接口）
  const behaviorStats = computed(() => {
    const cbs = diagnosis.value?.classroom_behavior_summary;
    if (!cbs) return [];
    const statsList: { label: string; value: string }[] = [];
    if (typeof cbs.recent_avg_lei === 'number') {
      statsList.push({ label: '学习投入指数 LEI', value: (cbs.recent_avg_lei * 100).toFixed(0) });
    }
    if (typeof cbs.behavioral_engagement === 'number') {
      statsList.push({ label: '行为投入 BEI', value: (cbs.behavioral_engagement * 100).toFixed(0) });
    }
    if (typeof cbs.cognitive_engagement === 'number') {
      statsList.push({ label: '认知投入 CEI', value: (cbs.cognitive_engagement * 100).toFixed(0) });
    }
    if (typeof cbs.emotional_engagement === 'number') {
      statsList.push({ label: '情感投入 EEI', value: (cbs.emotional_engagement * 100).toFixed(0) });
    }
    if (typeof cbs.avg_cognitive_depth === 'number') {
      statsList.push({ label: '认知深度', value: (cbs.avg_cognitive_depth * 100).toFixed(0) });
    }
    if (typeof cbs.mind_wandering_rate === 'number') {
      statsList.push({ label: '走神率', value: `${(cbs.mind_wandering_rate * 100).toFixed(0)}%` });
    }
    if (typeof cbs.contagion_index === 'number') {
      statsList.push({ label: '社会传染指数', value: cbs.contagion_index.toFixed(2) });
    }
    if (typeof cbs.on_task_rate === 'number') {
      statsList.push({ label: '目标行为率', value: `${(cbs.on_task_rate * 100).toFixed(0)}%` });
    }
    if (cbs.attention_cycle_phase) {
      statsList.push({ label: '注意力相位', value: cbs.attention_cycle_phase });
    }
    if (cbs.class_attention_trend) {
      statsList.push({ label: '注意力趋势', value: cbs.class_attention_trend });
    }
    if (typeof cbs.student_count === 'number' && cbs.student_count > 0) {
      statsList.push({ label: '检测人数', value: `${cbs.student_count}人` });
    }
    return statsList;
  });

  const behaviorBloomBars = computed(() => {
    const cbs = diagnosis.value?.classroom_behavior_summary;
    if (!cbs?.bloom_distribution) return [];
    return Object.entries(cbs.bloom_distribution).map(([key, val]) => ({
      label: key,
      value: typeof val === 'number' ? val : 0,
    }));
  });

  const behaviorNote = computed(() => {
    return diagnosis.value?.classroom_behavior_summary?.teacher_note || '';
  });

  const eduTheoryAnalysis = computed(() => {
    const cbs = diagnosis.value?.classroom_behavior_summary;
    if (!cbs) return [];
    const items: { theory: string; icon: string; insight: string }[] = [];
    // Fredricks三维投入模型分析
    const bei = (cbs.behavioral_engagement || 0) * 100;
    const cei = (cbs.cognitive_engagement || 0) * 100;
    const eei = (cbs.emotional_engagement || 0) * 100;
    if (bei > 0 || cei > 0 || eei > 0) {
      const minDim = Math.min(bei, cei, eei);
      const minName = minDim === bei ? '行为投入(BEI)' : minDim === cei ? '认知投入(CEI)' : '情感投入(EEI)';
      items.push({
        theory: 'Fredricks三维投入模型',
        icon: '🧠',
        insight: `BEI ${bei.toFixed(0)}% / CEI ${cei.toFixed(0)}% / EEI ${eei.toFixed(0)}%。${minName}相对偏低，建议针对性提升该维度。`,
      });
    }
    // Bloom认知分类分析
    const bd = cbs.bloom_distribution || {};
    const bloomKeys = Object.keys(bd);
    if (bloomKeys.length) {
      const dominant = bloomKeys.reduce((a, b) => (bd[a] || 0) > (bd[b] || 0) ? a : b);
      items.push({
        theory: 'Bloom认知分类法',
        icon: '📊',
        insight: `主导认知层次为「${dominant}」。建议设计分层任务，推动学生向更高阶思维进阶。`,
      });
    }
    // 注意力动态模型
    if (cbs.class_attention_trend) {
      items.push({
        theory: '注意力动态模型',
        icon: '⏰',
        insight: `注意力趋势：${cbs.class_attention_trend}。${cbs.attention_cycle_phase ? '当前相位：' + cbs.attention_cycle_phase + '。' : ''}建议每15-20分钟切换教学模态以重置注意力曲线。`,
      });
    }
    // 社会传染理论
    const ci = cbs.contagion_index || 0;
    if (ci > 0) {
      items.push({
        theory: '社会传染理论',
        icon: '🔥',
        insight: `社会传染指数 ${(ci * 100).toFixed(0)}%。${ci > 0.5 ? '分心行为存在聚集扩散风险，建议物理隔离或同伴教学干预。' : '课堂注意力免疫良好，可强化正向传染效应。'}`,
      });
    }
    return items;
  });

  async function loadInitialDiagnosis() {
    try {
      diagnosis.value = await fetchLearningReport(false);
    } catch {
      // keep page available even if backend has not synced yet
    }
  }

  async function handleRunDiagnosis() {
    loadingDiagnosis.value = true;
    try {
      diagnosis.value = await runLearningDiagnosis(true);
      Message.success('已生成最新学情诊断');
    } catch (error: any) {
      Message.error(error?.message || '生成学情诊断失败');
    } finally {
      loadingDiagnosis.value = false;
    }
  }

  async function handleGeneratePlan() {
    loadingPlan.value = true;
    try {
      reviewPlan.value = await generateReviewPlan(true);
      Message.success('复习计划已生成');
    } catch (error: any) {
      Message.error(error?.message || '生成复习计划失败');
    } finally {
      loadingPlan.value = false;
    }
  }

  async function handleGenerateMistakes() {
    loadingMistakes.value = true;
    try {
      mistakeDigest.value = await generateMistakeDigest(true);
      Message.success('错题整理已完成');
    } catch (error: any) {
      Message.error(error?.message || '整理错题失败');
    } finally {
      loadingMistakes.value = false;
    }
  }

  onMounted(() => {
    void loadInitialDiagnosis();
  });
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 24px;
  }

  .card-block {
    margin-bottom: 16px;
    border-radius: 14px;
  }

  .profile-row {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .profile-meta {
    line-height: 1.9;
    font-size: 14px;
  }

  .section-title,
  .box-title {
    margin-bottom: 8px;
    font-weight: 600;
  }

  .course-ul {
    margin: 0;
    padding-left: 1.2em;
    color: var(--color-text-2);
    line-height: 1.8;
  }

  .mini-cal {
    :deep(.arco-calendar-header) {
      padding: 0 0 8px;
    }
  }

  .event-list {
    font-size: 13px;
  }

  .event-row {
    display: flex;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid var(--color-border-2);
  }

  .event-date {
    color: #1677ff;
    font-weight: 500;
    white-space: nowrap;
  }

  .action-block {
    background:
      radial-gradient(circle at top left, rgba(99, 102, 241, 0.12), transparent 38%),
      linear-gradient(180deg, #f8fbff, #fff);
  }

  .action-copy h3 {
    margin: 0 0 6px;
    color: #0f172a;
    font-size: 18px;
  }

  .action-copy p {
    margin: 0;
    color: #64748b;
    line-height: 1.7;
  }

  .action-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 16px;
  }

  .stat-box {
    margin-bottom: 8px;
    padding: 12px 8px;
    border: 1px solid rgba(37, 99, 235, 0.12);
    border-radius: 12px;
    background: linear-gradient(180deg, #eff6ff, #fff);
    text-align: center;
  }

  .stat-num {
    color: #2563eb;
    font-weight: 700;
    font-size: 22px;
  }

  .stat-label {
    margin-top: 4px;
    color: var(--color-text-3);
    font-size: 12px;
  }

  .behavior-note {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding: 8px 12px;
    background: #f0f7ff;
    border-radius: 8px;

    .note-text {
      font-size: 13px;
      color: #333;
    }
  }

  .report-summary {
    color: #1e293b;
    line-height: 1.8;
  }

  .meta-line,
  .tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }

  .meta-pill,
  .info-tag {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.1);
    color: #1d4ed8;
    font-size: 12px;
    font-weight: 600;
  }

  .meta-pill--soft {
    background: rgba(15, 23, 42, 0.06);
    color: #475569;
  }

  .info-tag--warm {
    background: rgba(245, 158, 11, 0.12);
    color: #b45309;
  }

  .dual-grid,
  .plan-grid {
    display: grid;
    gap: 12px;
    margin-top: 14px;
  }

  .dual-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .plan-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .insight-box,
  .flashcard-box,
  .mistake-card,
  .plan-card {
    padding: 14px;
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 12px;
    background: #fff;
  }

  .plain-list {
    margin: 0;
    padding-left: 18px;
    color: #475569;
    line-height: 1.8;
  }

  .mistake-list {
    display: grid;
    gap: 12px;
    margin-top: 14px;
  }

  .mistake-title,
  .plan-day {
    color: #0f172a;
    font-weight: 700;
    font-size: 15px;
  }

  .mistake-line {
    margin-top: 8px;
    color: #475569;
    line-height: 1.7;
  }

  .plan-focus {
    margin: 6px 0 10px;
    color: #2563eb;
    font-weight: 600;
  }

  .w-date {
    margin-right: 8px;
    color: var(--color-text-3);
    white-space: nowrap;
  }

  .w-text {
    font-size: 13px;
  }

  .donut-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    align-items: center;
  }

  .donut {
    width: 160px;
    height: 160px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: inset 0 0 0 28px #fff;
  }

  .legend {
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 13px;
    line-height: 2;
  }

  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
  }

  // Bloom认知分布
  .bloom-section {
    margin-top: 12px;

    .bloom-bar-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .bloom-bar-row {
      display: flex;
      align-items: center;
      gap: 8px;

      .bloom-bar-label {
        font-size: 12px;
        color: #666;
        width: 70px;
        text-align: right;
      }

      .bloom-bar-pct {
        font-size: 12px;
        color: #333;
        width: 40px;
        text-align: right;
      }
    }
  }

  // 教育学理论分析
  .theory-section {
    margin-top: 12px;

    .theory-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .theory-item {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 8px 10px;
      border-left: 3px solid #1890ff;

      .theory-header {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 4px;

        .theory-icon {
          font-size: 14px;
        }

        .theory-name {
          font-size: 12px;
          font-weight: 600;
          color: #333;
        }
      }

      .theory-insight {
        font-size: 12px;
        color: #555;
        line-height: 1.6;
      }
    }
  }

  @media (max-width: 991px) {
    .dual-grid,
    .plan-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
