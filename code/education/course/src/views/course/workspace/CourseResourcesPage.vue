<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    IconDownload,
    IconFile,
    IconRobot,
    IconSearch,
    IconStorage,
  } from '@arco-design/web-vue/es/icon';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import {
    buildCourseResources,
    type CourseResourceItem,
  } from '@/data/courseWorkspace';
  import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';

  const route = useRoute();
  const router = useRouter();
  const query = ref('');
  const activeType = ref<'全部' | CourseResourceItem['type']>('全部');
  const course = computed(() => getClassroomCourse(String(route.params.courseId || '')));
  const resources = computed(() =>
    course.value ? buildCourseResources(course.value) : []
  );
  const resourceTypes = computed(() => [
    '全部' as const,
    ...Array.from(new Set(resources.value.map((item) => item.type))),
  ]);
  const visibleResources = computed(() => {
    const keyword = query.value.trim().toLowerCase();
    return resources.value.filter((item) => {
      const typeMatches = activeType.value === '全部' || item.type === activeType.value;
      const searchMatches =
        !keyword ||
        item.title.toLowerCase().includes(keyword) ||
        item.chapter.toLowerCase().includes(keyword);
      return typeMatches && searchMatches;
    });
  });

  function askAboutResource(item: CourseResourceItem) {
    if (!course.value) return;
    router.push(
      courseWorkspaceLocation(course.value.id, 'agent', {
        prompt: `当前课程是《${course.value.title}》。我想围绕资料《${item.title}》提问，请先告诉我可以从哪些角度阅读这份资料。`,
        resourceId: item.id,
        source: 'resource',
      })
    );
  }

  function openGenerator() {
    if (!course.value) return;
    router.push({
      name: 'StudentCourseResourceGenerator',
      params: { courseId: course.value.id },
      query: {
        subject: course.value.title,
        topic: course.value.chapters[0]?.title || course.value.title,
        source: 'course-workspace',
      },
    });
  }

  function downloadDemo(item: CourseResourceItem) {
    const content = `# ${item.title}\n\n课程：${course.value?.title || ''}\n章节：${item.chapter}\n类型：${item.type}\n\n这是课程资源演示文件。`;
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${item.title}.md`;
    link.click();
    URL.revokeObjectURL(url);
    Message.success('演示资源已下载');
  }
</script>

<template>
  <section v-if="course" class="course-resources">
    <header class="resource-heading">
      <div>
        <span>COURSE LIBRARY</span>
        <h1>课程资料</h1>
        <p>按章节组织课件、讲义、案例和练习，所有资料都保留课程上下文。</p>
      </div>
      <button type="button" @click="openGenerator">
        <icon-robot /> AI 生成课程资源
      </button>
    </header>

    <div class="resource-overview">
      <article>
        <span class="overview-icon"><icon-storage /></span>
        <div><small>资料总数</small><strong>{{ resources.length }}</strong></div>
      </article>
      <article>
        <span class="overview-icon"><icon-file /></span>
        <div><small>覆盖章节</small><strong>{{ course.chapters.length }}</strong></div>
      </article>
      <article>
        <span class="overview-icon"><icon-download /></span>
        <div><small>本周新增</small><strong>6</strong></div>
      </article>
    </div>

    <div class="resource-toolbar">
      <label>
        <icon-search />
        <input v-model="query" type="search" placeholder="搜索资料或章节" />
      </label>
      <div>
        <button
          v-for="type in resourceTypes"
          :key="type"
          type="button"
          :class="{ active: activeType === type }"
          @click="activeType = type"
        >
          {{ type }}
        </button>
      </div>
    </div>

    <div class="resource-grid">
      <article v-for="item in visibleResources" :key="item.id" class="resource-card">
        <div class="resource-card__top">
          <span class="resource-type">{{ item.type }}</span>
          <small>{{ item.updatedAt }}</small>
        </div>
        <span class="resource-file-icon"><icon-file /></span>
        <h2>{{ item.title }}</h2>
        <p>{{ item.chapter }}</p>
        <div class="resource-meta">
          <span>{{ item.size }}</span>
          <span>{{ item.downloads }} 次使用</span>
        </div>
        <div class="resource-actions">
          <button type="button" @click="downloadDemo(item)">
            <icon-download /> 下载
          </button>
          <button type="button" @click="askAboutResource(item)">
            <icon-robot /> 围绕资料提问
          </button>
        </div>
      </article>
    </div>

    <a-empty v-if="!visibleResources.length" description="没有匹配的课程资料" />
  </section>
</template>

<style scoped lang="less">
  .course-resources {
    color: #17213a;
  }

  .resource-heading {
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

  .resource-overview {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;

    article {
      display: flex;
      align-items: center;
      gap: 12px;
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
  }

  .overview-icon {
    display: grid;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    color: #596bfa;
    background: #edf0ff;
    place-items: center;
  }

  .resource-toolbar {
    margin: 16px 0 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;

    label {
      width: min(320px, 100%);
      height: 36px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 11px;
      border: 1px solid #e1e6ef;
      border-radius: 9px;
      color: #929cad;
      background: #fff;
    }

    input {
      width: 100%;
      border: 0;
      outline: 0;
      color: #354158;
      background: transparent;
      font-size: 11px;
    }

    > div {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }

    > div button {
      height: 30px;
      padding: 0 10px;
      border: 1px solid #e3e7ef;
      border-radius: 8px;
      color: #778196;
      background: #fff;
      font-size: 10px;
      cursor: pointer;

      &.active {
        border-color: #d9dfff;
        color: #5367f8;
        background: #eef1ff;
      }
    }
  }

  .resource-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .resource-card {
    min-width: 0;
    padding: 15px;
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 3px 12px rgba(34, 48, 88, 0.04);
    transition: transform 160ms ease, box-shadow 160ms ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 24px rgba(46, 59, 116, 0.08);
    }

    h2 {
      margin: 11px 0 6px;
      overflow: hidden;
      color: #2b374e;
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    p {
      height: 30px;
      margin: 0;
      color: #8993a5;
      font-size: 10px;
      line-height: 1.5;
    }
  }

  .resource-card__top,
  .resource-meta,
  .resource-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .resource-card__top small,
  .resource-meta {
    color: #98a1b1;
    font-size: 9px;
  }

  .resource-type {
    padding: 3px 7px;
    border-radius: 6px;
    color: #596bfa;
    background: #eef1ff;
    font-size: 9px;
  }

  .resource-file-icon {
    display: grid;
    width: 38px;
    height: 38px;
    margin-top: 14px;
    border-radius: 10px;
    color: #5367f8;
    background: #f0f2ff;
    place-items: center;
  }

  .resource-meta {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #edf0f5;
  }

  .resource-actions {
    gap: 6px;
    margin-top: 12px;

    button {
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      flex: 1;
      border: 1px solid #e0e5ee;
      border-radius: 8px;
      color: #687389;
      background: #fafbfc;
      font-size: 9px;
      cursor: pointer;
    }

    button:last-child {
      border-color: #dce2ff;
      color: #5367f8;
      background: #f5f7ff;
    }
  }

  @media (max-width: 1080px) {
    .resource-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .resource-heading,
    .resource-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .resource-overview,
    .resource-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
