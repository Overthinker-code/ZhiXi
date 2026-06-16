<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconArrowRight,
    IconBarChart,
    IconBulb,
    IconCheckCircle,
    IconClockCircle,
    IconRobot,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { buildCourseTasks } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  const route = useRoute();
  const router = useRouter();
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const allLessons = computed(
    () => course.value?.chapters.flatMap((chapter) => chapter.lessons) || []
  );
  const doneLessons = computed(
    () => allLessons.value.filter((lesson) => lesson.status === 'done').length
  );
  const chapterMastery = computed(() =>
    (course.value?.chapters || []).map((chapter, index) => {
      const done = chapter.lessons.filter((lesson) => lesson.status === 'done').length;
      const base = Math.round((done / Math.max(chapter.lessons.length, 1)) * 100);
      return {
        title: chapter.title,
        value: Math.max(18, Math.min(96, base || course.value!.progress - index * 7)),
      };
    })
  );
  const weakPoints = computed(() => {
    const concepts = course.value?.concepts || [];
    return concepts
      .slice(-2)
      .flatMap((item) => item.points.slice(0, 2))
      .slice(0, 4);
  });
  const nextTasks = computed(() =>
    course.value
      ? buildCourseTasks(course.value).filter((task) => task.status !== 'done').slice(0, 3)
      : []
  );

  function askForPlan() {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        prompt: `请根据《${course.value.title}》当前 ${course.value.progress}% 的进度和薄弱点 ${weakPoints.value.join('、')}，生成下一周复习计划。`,
        source: 'analytics',
      })
    );
  }
</script>

<template>
  <section v-if="course" class="course-analytics">
    <header class="analytics-heading">
      <div>
        <span>COURSE INSIGHTS</span>
        <h1>课程学情</h1>
        <p>只分析当前课程的进度、掌握度和下一步行动，避免跨课程数据混淆。</p>
      </div>
      <button type="button" @click="askForPlan"><icon-robot /> 生成个性化计划</button>
    </header>

    <div class="insight-summary">
      <article>
        <span class="summary-icon"><icon-bar-chart /></span>
        <div><small>课程进度</small><strong>{{ course.progress }}%</strong></div>
        <em>稳步推进</em>
      </article>
      <article>
        <span class="summary-icon"><icon-check-circle /></span>
        <div><small>已完成课节</small><strong>{{ doneLessons }}/{{ allLessons.length }}</strong></div>
        <em>本周 +2</em>
      </article>
      <article>
        <span class="summary-icon"><icon-clock-circle /></span>
        <div><small>近 7 日投入</small><strong>4.8h</strong></div>
        <em>高于上周</em>
      </article>
    </div>

    <div class="analytics-grid">
      <section class="panel mastery-panel">
        <div class="panel-title">
          <div><icon-bar-chart /><strong>章节掌握度</strong></div>
          <span>基于课节、练习与对话综合估算</span>
        </div>
        <div class="mastery-list">
          <article v-for="item in chapterMastery" :key="item.title">
            <div><strong>{{ item.title }}</strong><span>{{ item.value }}%</span></div>
            <div class="mastery-track"><i :style="{ width: `${item.value}%` }"></i></div>
          </article>
        </div>
      </section>

      <section class="panel weak-panel">
        <div class="panel-title">
          <div><icon-bulb /><strong>优先巩固</strong></div>
          <span>建议从低负担任务开始</span>
        </div>
        <div class="weak-list">
          <article v-for="(item, index) in weakPoints" :key="item">
            <span>{{ index + 1 }}</span>
            <div>
              <strong>{{ item }}</strong>
              <small>{{ index < 2 ? '需要结合例题再练习' : '建议回看课堂笔记' }}</small>
            </div>
            <button type="button" @click="askForPlan"><icon-arrow-right /></button>
          </article>
        </div>
      </section>

      <section class="panel rhythm-panel">
        <div class="panel-title">
          <div><icon-clock-circle /><strong>本周学习节奏</strong></div>
          <span>保持连续学习比单次时长更重要</span>
        </div>
        <div class="rhythm-chart" aria-label="近七日学习时长">
          <div v-for="(value, index) in [42, 68, 36, 82, 58, 74, 50]" :key="index">
            <i :style="{ height: `${value}%` }"></i>
            <span>{{ ['一', '二', '三', '四', '五', '六', '日'][index] }}</span>
          </div>
        </div>
      </section>

      <section class="panel next-panel">
        <div class="panel-title">
          <div><icon-check-circle /><strong>下一步行动</strong></div>
          <span>预计 45 分钟完成</span>
        </div>
        <div class="next-list">
          <article v-for="task in nextTasks" :key="task.id">
            <span>{{ task.type }}</span>
            <div><strong>{{ task.title }}</strong><small>{{ task.dueLabel }}</small></div>
          </article>
        </div>
        <button type="button" @click="router.push(courseWorkspaceLocation(course.id, 'tasks'))">
          查看全部课程任务 <icon-arrow-right />
        </button>
      </section>
    </div>
  </section>
</template>

<style scoped lang="less">
  .course-analytics {
    color: #17213a;
  }

  .analytics-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    padding: 2px 2px 18px;

    > div > span {
      color: #5367f8;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.14em;
    }

    h1 {
      margin: 6px 0 5px;
      font-size: 26px;
    }

    p {
      margin: 0;
      color: #7d879a;
      font-size: 12px;
    }

    > button {
      display: flex;
      align-items: center;
      gap: 6px;
      height: 36px;
      padding: 0 14px;
      border: 0;
      border-radius: 9px;
      color: #fff;
      background: #5367f8;
      cursor: pointer;
    }
  }

  .insight-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;

    article {
      display: grid;
      grid-template-columns: 38px 1fr auto;
      align-items: center;
      gap: 11px;
      padding: 15px 16px;
      border: 1px solid #e4e8f1;
      border-radius: 12px;
      background: #fff;
    }

    small,
    strong {
      display: block;
    }

    small {
      color: #8e98a9;
      font-size: 10px;
    }

    strong {
      margin-top: 4px;
      color: #29364d;
      font-size: 20px;
    }

    em {
      color: #168a65;
      font-size: 9px;
      font-style: normal;
    }
  }

  .summary-icon {
    display: grid;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    color: #596bfa;
    background: #edf0ff;
    place-items: center;
  }

  .analytics-grid {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 12px;
  }

  .panel {
    min-width: 0;
    padding: 16px;
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
  }

  .panel-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-bottom: 13px;
    border-bottom: 1px solid #edf0f5;

    > div {
      display: flex;
      align-items: center;
      gap: 7px;
      color: #5367f8;
    }

    strong {
      color: #2d394f;
      font-size: 13px;
    }

    > span {
      color: #98a1b1;
      font-size: 9px;
    }
  }

  .mastery-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding-top: 15px;

    article > div:first-child {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 6px;
      font-size: 10px;
    }

    strong {
      color: #566177;
      font-weight: 600;
    }

    span {
      color: #5367f8;
    }
  }

  .mastery-track {
    height: 6px;
    overflow: hidden;
    border-radius: 99px;
    background: #edf0f5;

    i {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: #5b6cf7;
    }
  }

  .weak-list,
  .next-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-top: 13px;
  }

  .weak-list article {
    display: grid;
    grid-template-columns: 26px 1fr 26px;
    align-items: center;
    gap: 8px;
    padding: 9px;
    border-radius: 9px;
    background: #f8f9fc;

    > span {
      display: grid;
      width: 24px;
      height: 24px;
      border-radius: 7px;
      color: #5367f8;
      background: #e9edff;
      font-size: 9px;
      place-items: center;
    }

    strong,
    small {
      display: block;
    }

    strong {
      color: #445068;
      font-size: 10px;
    }

    small {
      margin-top: 2px;
      color: #929bad;
      font-size: 8px;
    }

    button {
      display: grid;
      width: 24px;
      height: 24px;
      border: 0;
      border-radius: 7px;
      color: #6877e9;
      background: #fff;
      cursor: pointer;
      place-items: center;
    }
  }

  .rhythm-chart {
    height: 170px;
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    gap: 12px;
    padding: 22px 12px 0;
    border-bottom: 1px solid #edf0f5;

    > div {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      flex-direction: column;
      flex: 1;
    }

    i {
      width: min(24px, 60%);
      min-height: 16px;
      border-radius: 6px 6px 2px 2px;
      background: #7a88f8;
    }

    span {
      margin: 7px 0 8px;
      color: #919aac;
      font-size: 9px;
    }
  }

  .next-list article {
    display: grid;
    grid-template-columns: 40px 1fr;
    align-items: center;
    gap: 9px;
    padding: 8px 0;
    border-bottom: 1px solid #eff1f5;

    > span {
      padding: 4px 6px;
      border-radius: 6px;
      color: #5a6cec;
      background: #eef1ff;
      font-size: 8px;
      text-align: center;
    }

    strong,
    small {
      display: block;
    }

    strong {
      color: #48546a;
      font-size: 10px;
    }

    small {
      margin-top: 3px;
      color: #969faf;
      font-size: 8px;
    }
  }

  .next-panel > button {
    margin-top: 13px;
    display: flex;
    align-items: center;
    gap: 4px;
    border: 0;
    color: #5367f8;
    background: transparent;
    font-size: 9px;
    cursor: pointer;
  }

  @media (max-width: 900px) {
    .analytics-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .analytics-heading {
      align-items: flex-start;
      flex-direction: column;
    }

    .insight-summary {
      grid-template-columns: 1fr;
    }
  }
</style>
