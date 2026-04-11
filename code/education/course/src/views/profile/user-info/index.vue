<template>
  <div class="container">
    <Breadcrumb :items="['menu.profile', 'menu.profile.userInfo']" />
    <div class="hero">
      <div class="hero-bg" />
      <div class="hero-inner">
        <a-avatar :size="88" class="avatar">
          <img
            alt=""
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=zhiyu"
          />
        </a-avatar>
        <h2 class="name">{{ displayName }}</h2>
        <div class="tags">
          <a-tag>计算机学院</a-tag>
          <a-tag color="arcoblue">计算机科学与技术</a-tag>
          <a-tag color="green">武汉</a-tag>
        </div>
      </div>
    </div>

    <a-row :gutter="16" class="main-row">
      <a-col :xs="24" :lg="16">
        <a-card title="我的课程" class="card-block">
          <a-row :gutter="[12, 12]">
            <a-col
              v-for="c in courses"
              :key="c.title"
              :xs="24"
              :sm="12"
              :md="8"
            >
              <div class="course-card">
                <div class="course-title">{{ c.title }}</div>
                <div class="course-sub">{{ c.sub }}</div>
                <div class="course-meta">
                  <IconUser /> {{ c.count }} 人
                </div>
              </div>
            </a-col>
          </a-row>
        </a-card>
        <a-card title="最新动态" class="card-block">
          <a-timeline>
            <a-timeline-item
              v-for="(d, i) in dynamics"
              :key="i"
              :label="d.time"
            >
              {{ d.text }}
            </a-timeline-item>
          </a-timeline>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card title="我的小组" class="card-block">
          <a-list :bordered="false">
            <a-list-item v-for="g in groups" :key="g.name">
              <a-list-item-meta :title="g.name" :description="g.desc" />
              <template #actions>
                <span class="muted">{{ g.members }} 人</span>
              </template>
            </a-list-item>
          </a-list>
        </a-card>
        <a-card title="站内通知" class="card-block notify">
          <p class="muted">实验报告批改、作业截止提醒将在此展示。</p>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { IconUser } from '@arco-design/web-vue/es/icon';
  import { useUserStore } from '@/store';

  const userStore = useUserStore();
  const displayName = computed(() => userStore.name || '同学');

  const courses = [
    { title: '高等数学', sub: 'Advanced Mathematics', count: 539 },
    { title: '智能引擎应用', sub: 'The Volcano Engine', count: 975 },
    { title: '算法设计与分析', sub: 'Algorithm Design', count: 330 },
    { title: '数据结构', sub: 'Data Structure', count: 477 },
    { title: '计算机网络', sub: 'Computer Network', count: 349 },
    { title: '智能机器人', sub: 'Intelligent Robot', count: 218 },
  ];

  const groups = [
    { name: '智能应用小组', desc: '课程项目协作', members: 12 },
    { name: '产品设计队', desc: 'UX 与原型', members: 8 },
    { name: '算法兴趣组', desc: '周赛与题解', members: 25 },
    { name: '数据库助教组', desc: '答疑与实验', members: 6 },
  ];

  const dynamics = [
    { time: '今天 10:20', text: '发布了新实验：0-1 背包问题进阶练习。' },
    { time: '昨天', text: '图遍历算法专题讨论区有新回复。' },
    { time: '本周', text: '操作系统课程签到已全部完成。' },
  ];
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 24px;
  }

  .hero {
    position: relative;
    margin-bottom: 20px;
    border-radius: 16px;
    overflow: hidden;
    min-height: 180px;
    background: linear-gradient(135deg, #e8f4ff 0%, #f0fdf6 100%);
  }

  .hero-bg {
    position: absolute;
    inset: 0;
    opacity: 0.35;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 200'%3E%3Cpath fill='%232DB583' d='M0 120L60 105C120 90 240 60 360 55C480 50 600 70 720 80C840 90 960 90 1080 75C1200 60 1320 30 1380 15L1440 0V200H0Z'/%3E%3C/svg%3E")
      no-repeat bottom;
    background-size: cover;
  }

  .hero-inner {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 28px 16px 24px;
  }

  .avatar {
    border: 3px solid #fff;
    box-shadow: 0 8px 24px rgba(45, 181, 131, 0.2);
  }

  .name {
    margin: 12px 0 8px;
    font-size: 22px;
    color: #1d3b2f;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  .card-block {
    margin-bottom: 16px;
    border-radius: 12px;
  }

  .course-card {
    padding: 12px;
    border-radius: 10px;
    border: 1px solid rgba(45, 181, 131, 0.15);
    background: #fafdfb;
    height: 100%;
  }

  .course-title {
    font-weight: 600;
    font-size: 15px;
    color: #1d3b2f;
  }

  .course-sub {
    font-size: 12px;
    color: #6b7a72;
    margin: 4px 0 8px;
  }

  .course-meta {
    font-size: 13px;
    color: #2db583;
  }

  .muted {
    color: var(--color-text-3);
    font-size: 13px;
  }

  .notify {
    min-height: 120px;
  }
</style>
