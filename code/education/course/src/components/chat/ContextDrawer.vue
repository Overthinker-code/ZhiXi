<script setup lang="ts">
  import { computed } from 'vue';
  import type { AIContextCourse, CourseContextPayload } from '@/api/ai-chat';
  import ArtifactCards from './ArtifactCards.vue';
  import CitationList from './CitationList.vue';
  import ToolTrace from './ToolTrace.vue';

  const props = defineProps<{
    visible: boolean;
    courses: AIContextCourse[];
    courseContext: CourseContextPayload;
    citations: Array<Record<string, any>>;
    toolEvents: Array<Record<string, any>>;
    profileItems: Array<{ label: string; value: string }>;
    artifacts: Array<Record<string, any>>;
    resourcePackage?: Record<string, any> | null;
  }>();

  const emit = defineEmits<{
    (e: 'close'): void;
    (e: 'updateCourse', courseId: string): void;
    (e: 'updateChapter', chapterId: string): void;
    (e: 'toggleRag'): void;
  }>();

  const selectedCourse = computed(() =>
    props.courses.find((item) => item.courseId === props.courseContext.courseId)
  );
</script>

<template>
  <div v-if="visible" class="drawer-mask" @click="emit('close')" />
  <aside
    id="tutor-context-drawer"
    :class="['context-drawer', { visible }]"
    role="dialog"
    aria-modal="true"
    aria-labelledby="tutor-context-title"
    :aria-hidden="!visible"
    :inert="!visible"
    data-testid="tutor-context-drawer"
  >
    <header>
      <strong id="tutor-context-title">上下文</strong>
      <button type="button" @click="emit('close')">关闭</button>
    </header>

    <section class="drawer-section">
      <h3>当前课程上下文</h3>
      <label>
        课程
        <select
          :value="courseContext.courseId || ''"
          @change="emit('updateCourse', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">未选择</option>
          <option v-for="course in courses" :key="course.courseId" :value="course.courseId">
            {{ course.title }}
          </option>
        </select>
      </label>
      <label>
        章节
        <select
          :value="courseContext.chapterId || ''"
          @change="emit('updateChapter', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">未选择</option>
          <option
            v-for="chapter in selectedCourse?.chapters || []"
            :key="chapter.chapterId"
            :value="chapter.chapterId"
          >
            {{ chapter.title }}
          </option>
        </select>
      </label>
      <button type="button" :class="{ active: courseContext.useCourseRag }" @click="emit('toggleRag')">
        使用课程资料：{{ courseContext.useCourseRag ? '开启' : '关闭' }}
      </button>
    </section>

    <section class="drawer-section">
      <h3>参考来源</h3>
      <CitationList :citations="citations" />
      <p v-if="!citations.length" class="muted">完成一次课程问答后，这里会显示参考来源。</p>
    </section>

    <section class="drawer-section">
      <h3>学习画像摘要</h3>
      <div class="profile-mini">
        <article v-for="item in profileItems" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>
    </section>

    <section class="drawer-section">
      <h3>智能体协作状态</h3>
      <ToolTrace :events="toolEvents" />
    </section>

    <section class="drawer-section">
      <h3>生成资源包</h3>
      <ArtifactCards
        :artifacts="artifacts"
        :package-id="resourcePackage?.package_id"
      />
      <p v-if="!artifacts.length" class="muted">资料生成完成后会出现在这里。</p>
    </section>
  </aside>
</template>

<style scoped lang="scss">
  .drawer-mask {
    position: fixed;
    inset: 64px 0 0;
    z-index: 30;
    background: rgba(15, 23, 42, 0.08);
  }

  .context-drawer {
    position: fixed;
    top: 64px;
    right: 0;
    bottom: 0;
    z-index: 31;
    width: 360px;
    padding: 18px;
    overflow-y: auto;
    border-left: 1px solid rgba(15, 23, 42, 0.08);
    background: #fff;
    box-shadow: -12px 0 32px rgba(15, 23, 42, 0.06);
    visibility: hidden;
    pointer-events: none;
    transform: translateX(100%);
    transition: transform 0.2s ease, visibility 0s linear 0.2s;

    &.visible {
      visibility: visible;
      pointer-events: auto;
      transform: translateX(0);
      transition-delay: 0s;
    }

    > header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;

      strong {
        color: #101828;
        font-size: 18px;
      }

      button {
        border: 0;
        color: #4f46e5;
        background: transparent;
        cursor: pointer;
      }
    }
  }

  .drawer-section {
    padding: 14px 0;
    border-top: 1px solid rgba(15, 23, 42, 0.08);

    h3 {
      margin: 0 0 12px;
      color: #101828;
      font-size: 14px;
    }

    label {
      display: grid;
      gap: 6px;
      margin-bottom: 10px;
      color: #667085;
      font-size: 12px;
    }

    select {
      height: 38px;
      padding: 0 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 12px;
      outline: none;
      background: #fff;
      color: #344054;
    }

    > button {
      height: 34px;
      padding: 0 12px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 999px;
      color: #475467;
      background: #f7f9ff;
      cursor: pointer;

      &.active {
        color: #fff;
        background: #4f46e5;
        border-color: #4f46e5;
      }
    }
  }

  .profile-mini {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;

    article {
      padding: 10px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      border-radius: 14px;
      background: #f7f9ff;
    }

    span {
      display: block;
      color: #667085;
      font-size: 12px;
    }

    strong {
      display: block;
      margin-top: 4px;
      color: #101828;
      font-size: 13px;
    }
  }

  .muted {
    margin: 0;
    color: #98a2b3;
    font-size: 13px;
    line-height: 1.6;
  }

  @media (prefers-reduced-motion: reduce) {
    .context-drawer {
      transition: none;
    }
  }
</style>
