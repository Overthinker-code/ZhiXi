<template>
  <div class="container">
    <Breadcrumb :items="['menu.profile', 'menu.profile.learningData']" />
    <a-row :gutter="16">
      <a-col :xs="24" :lg="10">
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
      <a-col :xs="24" :lg="14">
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
  import { computed, ref } from 'vue';
  import { useUserStore } from '@/store';

  const userStore = useUserStore();
  const displayName = computed(() => userStore.name || '同学');

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
    { name: '操作系统', pct: 22.88, color: '#722ED1' },
    { name: '算法设计与分析', pct: 21.19, color: '#FA8C16' },
  ];

  const donutStyle = computed(() => {
    let start = 0;
    const segs = pieParts.map((p) => {
      const deg = (p.pct / 100) * 360;
      const s = start;
      start += deg;
      return `${p.color} ${s}deg ${start}deg`;
    });
    return {
      background: `conic-gradient(${segs.join(', ')})`,
    };
  });
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 24px;
  }

  .card-block {
    margin-bottom: 16px;
    border-radius: 12px;
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

  .section-title {
    font-weight: 600;
    margin-bottom: 8px;
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

  .stat-box {
    text-align: center;
    padding: 12px 8px;
    border-radius: 10px;
    background: linear-gradient(180deg, #f5f3ff, #fff);
    border: 1px solid rgba(99, 102, 241, 0.12);
    margin-bottom: 8px;
  }

  .stat-num {
    font-size: 22px;
    font-weight: 700;
    color: #6366f1;
  }

  .stat-label {
    font-size: 12px;
    color: var(--color-text-3);
    margin-top: 4px;
  }

  .w-date {
    color: var(--color-text-3);
    margin-right: 8px;
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
    list-style: none;
    padding: 0;
    margin: 0;
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
</style>
