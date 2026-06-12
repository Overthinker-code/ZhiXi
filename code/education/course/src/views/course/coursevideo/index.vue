<template>
  <ZyPageShell title="" max-width="1428px">
    <div class="course-learn">
      <div class="course-learn__main">
        <section class="course-header-card">
          <div class="course-cover">
            <img :src="posterImg" alt="数据库系统原理课程封面" />
            <span class="course-cover__glow" />
          </div>
          <div class="course-header-card__info">
            <div class="course-heading">
              <h1 class="course-title">{{ courseTitle }}</h1>
              <span class="course-badge">高校计算机专业</span>
            </div>
            <div class="course-teacher">
              <img :src="teacherAvatarImg" alt="" class="teacher-avatar" />
              <strong>林老师</strong>
              <span>数据库课程组</span>
            </div>
            <div class="course-progress-row">
              <span class="course-progress-row__label">学习进度</span>
              <a-progress
                :percent="0.62"
                :color="'#5367f8'"
                :track-color="'#e8ebff'"
                size="small"
                :show-text="false"
                class="progress-bar"
              />
              <span class="progress-label">62%</span>
            </div>
            <p class="course-progress-copy">已学 18 / 29 节</p>
          </div>
          <div class="course-header-card__meta">
            <div v-for="item in courseMeta" :key="item.label" class="meta-item">
              <span
                class="meta-item__icon"
                :class="`meta-item__icon--${item.tone}`"
              >
                <component :is="item.icon" />
              </span>
              <span class="meta-item__copy">
                <small>{{ item.label }}</small>
                <strong>{{ item.value }}</strong>
              </span>
            </div>
          </div>
        </section>

        <section class="video-card">
          <div class="video-card__toolbar">
            <h2 class="video-lesson-title">
              <span>正在学习</span>
              <strong>{{ currentLesson.label }}</strong>
            </h2>
            <div class="video-actions">
              <a-button size="small" class="action-btn" @click="focusNotes">
                <template #icon><icon-edit /></template>
                笔记
              </a-button>
              <a-button
                size="small"
                class="action-btn"
                :class="{ 'action-btn--active': isFavorite }"
                @click="toggleFavorite"
              >
                <template #icon>
                  <icon-heart-fill v-if="isFavorite" />
                  <icon-heart v-else />
                </template>
                {{ isFavorite ? '已收藏' : '收藏' }}
              </a-button>
              <a-button
                size="small"
                class="action-btn"
                @click="downloadCurrentLesson"
              >
                <template #icon><icon-download /></template>
                下载
              </a-button>
            </div>
          </div>
          <div class="video-card__player">
            <input
              ref="videoFileInput"
              type="file"
              accept="video/*"
              class="video-file-input"
              @change="handleVideoUpload"
            />
            <video
              v-if="videoSrc"
              :src="videoSrc"
              controls
              class="video-element"
              :poster="posterImg"
            />
            <video v-else controls class="video-element" :poster="posterImg">
              <source src="" type="video/mp4" />
              您的浏览器不支持视频标签。
            </video>
            <button
              type="button"
              class="video-upload-trigger"
              aria-label="上传本地课程视频"
              @click="videoFileInput?.click()"
            >
              <icon-upload />
              <span>本地视频</span>
            </button>
          </div>
        </section>

        <section class="section-card timeline-card">
          <div class="section-card__head">
            <div class="section-card__title">
              <span>内容时段划分</span>
            </div>
            <span class="section-card__hint">
              专注度越高，学习效果越好
              <icon-info-circle />
            </span>
          </div>
          <div class="timeline-wrap">
            <VideoInfo />
          </div>
        </section>

        <section
          ref="notesPanel"
          class="artifact-panel notes-panel course-selection-root"
          @mouseup="handleTextSelection('.course-selection-root', $event)"
          @touchend="handleTextSelection('.course-selection-root', $event)"
        >
          <div class="artifact-panel__head">
            <div class="section-card__title">
              <icon-file />
              <span>课堂笔记</span>
            </div>
            <a-button
              size="small"
              type="text"
              class="panel-text-action"
              @click="organizeNotes"
            >
              {{ notesOrganized ? '已智能整理' : 'AI 智能整理' }}
            </a-button>
          </div>
          <div class="notes-grid">
            <div
              v-for="note in noteSummaries"
              :key="note.title"
              class="note-col"
            >
              <div class="note-col__num">{{ note.num }}</div>
              <h4 class="note-col__title">{{ note.title }}</h4>
              <ul class="note-col__list">
                <li v-for="point in note.points" :key="point">{{ point }}</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- 思维导图 + 知识图谱 -->
        <div class="knowledge-row">
          <section class="artifact-panel knowledge-card">
            <div class="artifact-panel__head">
              <div class="section-card__title">
                <icon-bulb />
                <span>思维导图</span>
              </div>
              <span class="panel-text-action">展开全部 <icon-right /></span>
            </div>
            <div
              class="knowledge-card__body knowledge-card__body--mind course-selection-root"
              @mouseup="handleTextSelection('.course-selection-root', $event)"
              @touchend="handleTextSelection('.course-selection-root', $event)"
            >
              <CourseMindMapVisual
                :active="true"
                @node-prompt="
                  handleVisualNodePrompt($event, MIND_MAP_CONTEXT_TEXT)
                "
              />
            </div>
          </section>
          <section class="artifact-panel knowledge-card">
            <div class="artifact-panel__head">
              <div class="section-card__title">
                <icon-share-alt />
                <span>课程知识图谱</span>
              </div>
              <span class="panel-text-action">查看详情 <icon-right /></span>
            </div>
            <div
              class="knowledge-card__body knowledge-card__body--graph course-selection-root"
              @mouseup="handleTextSelection('.course-selection-root', $event)"
              @touchend="handleTextSelection('.course-selection-root', $event)"
            >
              <CourseKnowledgeGraphVisual
                :active="true"
                @node-prompt="
                  handleVisualNodePrompt($event, KNOWLEDGE_GRAPH_CONTEXT_TEXT)
                "
              />
            </div>
          </section>
        </div>
      </div>

      <aside class="course-learn__sidebar">
        <section class="chapter-card">
          <div class="chapter-card__head">
            <strong>课程章节</strong>
            <span><b>18</b> / 29 节</span>
          </div>

          <div class="chapter-accordion">
            <div
              v-for="chapter in chapters"
              :key="chapter.id"
              class="chapter-group"
              :class="{ 'chapter-group--open': openChapters.has(chapter.id) }"
            >
              <button
                type="button"
                class="chapter-group__header"
                @click="toggleChapter(chapter.id)"
              >
                <icon-down v-if="openChapters.has(chapter.id)" />
                <icon-right v-else />
                <span>{{ chapter.title }}</span>
                <icon-up
                  v-if="openChapters.has(chapter.id)"
                  class="chapter-group__fold"
                />
                <icon-down v-else class="chapter-group__fold" />
              </button>
              <div
                v-show="openChapters.has(chapter.id)"
                class="chapter-group__body"
              >
                <button
                  v-for="lesson in chapter.lessons"
                  :key="lesson.id"
                  type="button"
                  class="lesson-item"
                  :class="{
                    'lesson-item--done': lesson.status === 'done',
                    'lesson-item--playing': currentLessonId === lesson.id,
                  }"
                  @click="selectLesson(lesson)"
                >
                  <span class="lesson-item__label">{{ lesson.label }}</span>
                  <icon-check-circle-fill
                    v-if="lesson.status === 'done'"
                    class="lesson-icon lesson-icon--done"
                  />
                  <icon-play-circle-fill
                    v-else-if="currentLessonId === lesson.id"
                    class="lesson-icon lesson-icon--playing"
                  />
                  <span v-else class="lesson-icon lesson-icon--pending" />
                </button>
              </div>
            </div>
          </div>

          <a-button long class="download-all-btn" @click="downloadAllLessons">
            <template #icon><icon-download /></template>
            下载全部课件
          </a-button>
        </section>
      </aside>
    </div>

    <Transition name="sel-menu">
      <div
        v-if="showContextMenu"
        :style="contextMenuStyle"
        class="selection-context-menu"
        @mousedown.stop
        @pointerdown.stop
      >
        <div class="selection-context-menu__title">划词唤醒</div>
        <button
          v-for="template in promptTemplates"
          :key="template.key"
          type="button"
          class="selection-context-menu__item"
          @click="sendAIQuery(template.key)"
        >
          {{ template.label }}
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
        stroke="#2563eb"
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
      @close="clearAnswerPanel"
    />
  </ZyPageShell>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
  import { onBeforeRouteLeave, useRoute } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import {
    IconApps,
    IconBulb,
    IconCheckCircle,
    IconCheckCircleFill,
    IconClockCircle,
    IconDown,
    IconDownload,
    IconEdit,
    IconFile,
    IconHeart,
    IconHeartFill,
    IconInfoCircle,
    IconLayers,
    IconPlayCircleFill,
    IconRight,
    IconShareAlt,
    IconUp,
    IconUpload,
  } from '@arco-design/web-vue/es/icon';
  import ZyPageShell from '@/components/zy/ZyPageShell.vue';
  import { useSelectionQueryMenu } from '@/composables/useSelectionQueryMenu';
  import { fetchCourseById } from '@/api/course';
  import { RELATION_DB_CLASSROOM_NOTES } from '@/constants/relationDbClassroomNotes';
  import {
    MIND_MAP_CONTEXT_TEXT,
    KNOWLEDGE_GRAPH_CONTEXT_TEXT,
  } from '@/constants/courseVisualContext';
  import VideoInfo from './components/VideoInfo.vue';
  import CourseMindMapVisual from './components/CourseMindMapVisual.vue';
  import CourseKnowledgeGraphVisual from './components/CourseKnowledgeGraphVisual.vue';
  import SelectionAiAnswerPanel from './components/SelectionAiAnswerPanel.vue';
  import posterImg from '@/assets/images/数据库图片.png';
  import teacherAvatarImg from '@/assets/images/老师头像.png';

  type LessonStatus = 'done' | 'pending';
  type Lesson = {
    id: string;
    label: string;
    title: string;
    status: LessonStatus;
  };

  const route = useRoute();
  const videoFileInput = ref<HTMLInputElement | null>(null);
  const videoSrc = ref<string | null>(null);
  const localVideoUrl = ref<string | null>(null);
  const courseTitle = ref('数据库系统原理');
  const currentLessonId = ref('1.1');
  const isFavorite = ref(false);
  const notesOrganized = ref(false);
  const notesPanel = ref<HTMLElement | null>(null);
  const openChapters = ref(new Set(['ch1', 'ch2', 'ch3', 'ch4', 'ch5']));

  const courseMeta = [
    {
      label: '课程学时',
      value: '48 学时',
      icon: IconClockCircle,
      tone: 'blue',
    },
    { label: '课程难度', value: '中等', icon: IconLayers, tone: 'violet' },
    { label: '课程类型', value: '专业必修', icon: IconApps, tone: 'cyan' },
    {
      label: '更新时间',
      value: '2026-05-20',
      icon: IconClockCircle,
      tone: 'amber',
    },
  ];

  const noteSummaries = [
    {
      num: '01',
      title: '关系模型概述',
      points: [
        '二维表格组织数据',
        '行=元组，列=属性',
        'Edgar F. Codd 1970 提出',
      ],
    },
    {
      num: '02',
      title: '关键概念',
      points: ['表、属性、元组', '域与关键字', '主键与外键约束'],
    },
    {
      num: '03',
      title: '完整性约束',
      points: ['实体完整性', '参照完整性', '用户定义完整性'],
    },
    {
      num: '04',
      title: 'SQL 与事务',
      points: ['SELECT/INSERT/UPDATE', 'JOIN 多表查询', 'ACID 事务特性'],
    },
  ];

  const chapters = [
    {
      id: 'ch1',
      title: '第1章 关系数据模型与关系代数',
      lessons: [
        {
          id: '1.1',
          label: '1.1 数据模型与关系模型',
          title: '数据模型与关系模型',
          status: 'done',
        },
        {
          id: '1.2',
          label: '1.2 关系代数与关系演算',
          title: '关系代数与关系演算',
          status: 'done',
        },
        { id: '1.3', label: '1.3 SQL 基础', title: 'SQL 基础', status: 'done' },
        {
          id: '1.4',
          label: '1.4 视图与数据库架构',
          title: '视图与数据库架构',
          status: 'pending',
        },
      ],
    },
    {
      id: 'ch2',
      title: '第2章 关系数据库的完整性',
      lessons: [
        {
          id: '2.1',
          label: '2.1 实体完整性',
          title: '实体完整性',
          status: 'pending',
        },
        {
          id: '2.2',
          label: '2.2 参照完整性',
          title: '参照完整性',
          status: 'pending',
        },
        {
          id: '2.3',
          label: '2.3 用户定义完整性',
          title: '用户定义完整性',
          status: 'pending',
        },
      ],
    },
    {
      id: 'ch3',
      title: '第3章 事务与并发控制',
      lessons: [
        {
          id: '3.1',
          label: '3.1 事务与原子性',
          title: '事务与原子性',
          status: 'pending',
        },
        {
          id: '3.2',
          label: '3.2 并发控制与可串行化',
          title: '并发控制与可串行化',
          status: 'pending',
        },
        {
          id: '3.3',
          label: '3.3 死锁与并发调度',
          title: '死锁与并发调度',
          status: 'pending',
        },
      ],
    },
    {
      id: 'ch4',
      title: '第4章 数据库规范化与范式',
      lessons: [
        {
          id: '4.1',
          label: '4.1 函数依赖',
          title: '函数依赖',
          status: 'pending',
        },
        {
          id: '4.2',
          label: '4.2 范式与规范化',
          title: '范式与规范化',
          status: 'pending',
        },
        {
          id: '4.3',
          label: '4.3 模式分解与 BCNF',
          title: '模式分解与 BCNF',
          status: 'pending',
        },
      ],
    },
    {
      id: 'ch5',
      title: '第5章 数据库恢复技术',
      lessons: [
        {
          id: '5.1',
          label: '5.1 故障类型与恢复概述',
          title: '故障类型与恢复概述',
          status: 'pending',
        },
        {
          id: '5.2',
          label: '5.2 日志与检查点',
          title: '日志与检查点',
          status: 'pending',
        },
        {
          id: '5.3',
          label: '5.3 恢复策略',
          title: '恢复策略',
          status: 'pending',
        },
      ],
    },
  ] satisfies Array<{ id: string; title: string; lessons: Lesson[] }>;

  const allLessons = computed(() =>
    chapters.flatMap((chapter) => chapter.lessons)
  );
  const currentLesson = computed(
    () =>
      allLessons.value.find((lesson) => lesson.id === currentLessonId.value) ||
      allLessons.value[0]
  );

  const {
    promptTemplates,
    showContextMenu,
    contextMenuStyle,
    isLoadingResponse,
    showAnswerPanel,
    answerPanelBounds,
    answerPanelSession,
    isTypingAnswer,
    renderedResponse,
    bridgeLine,
    handleTextSelection,
    openMenuForText,
    sendAIQuery,
    clearAnswerPanel,
  } = useSelectionQueryMenu(
    () =>
      `${RELATION_DB_CLASSROOM_NOTES}\n\n${MIND_MAP_CONTEXT_TEXT}\n\n${KNOWLEDGE_GRAPH_CONTEXT_TEXT}`
  );

  function toggleChapter(id: string) {
    const next = new Set(openChapters.value);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    openChapters.value = next;
  }

  function selectLesson(lesson: Lesson) {
    currentLessonId.value = lesson.id;
    Message.success(`已切换到 ${lesson.label}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function focusNotes() {
    notesPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function toggleFavorite() {
    isFavorite.value = !isFavorite.value;
    Message.success(isFavorite.value ? '已收藏当前课程' : '已取消收藏');
  }

  function organizeNotes() {
    notesOrganized.value = true;
    Message.success('课堂笔记已按知识结构完成智能整理');
  }

  function downloadText(filename: string, content: string) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadCurrentLesson() {
    downloadText(
      `${currentLesson.value.id}-${currentLesson.value.title}.txt`,
      `${courseTitle.value}\n${currentLesson.value.label}\n\n${RELATION_DB_CLASSROOM_NOTES}`
    );
    Message.success('当前课节笔记已下载');
  }

  function downloadAllLessons() {
    const catalog = chapters
      .map(
        (chapter) =>
          `${chapter.title}\n${chapter.lessons
            .map((lesson) => `- ${lesson.label}`)
            .join('\n')}`
      )
      .join('\n\n');
    downloadText(
      `${courseTitle.value}-课程资料.txt`,
      `${courseTitle.value}\n\n${catalog}`
    );
    Message.success('课程目录资料已下载');
  }

  function handleVisualNodePrompt(
    payload: { text: string; rect: DOMRect },
    context: string
  ) {
    openMenuForText(payload.text, payload.rect, context);
  }

  function handleVideoUpload(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      if (localVideoUrl.value) URL.revokeObjectURL(localVideoUrl.value);
      localVideoUrl.value = URL.createObjectURL(file);
      videoSrc.value = localVideoUrl.value;
      Message.success(`已载入本地视频：${file.name}`);
    }
  }

  onMounted(async () => {
    const courseId = String(route.query.courseId || '');
    if (!courseId) return;
    try {
      const course = await fetchCourseById(courseId);
      if (course?.name) courseTitle.value = course.name;
    } catch {
      Message.warning('课程详情暂不可用，已展示数据库课程示例内容');
    }
  });

  onBeforeUnmount(() => {
    if (localVideoUrl.value) URL.revokeObjectURL(localVideoUrl.value);
  });

  onBeforeRouteLeave(() => {
    clearAnswerPanel();
    showContextMenu.value = false;
    return true;
  });
</script>

<style scoped lang="less">
  .course-learn {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 14px;
    align-items: start;
    --classroom-border: #e8ecf5;
    --classroom-text: #17213a;
    --classroom-muted: #74819b;
    --classroom-brand: #5668f6;
    --classroom-surface: #fff;
    margin-top: -16px;
  }

  @media (max-width: 1100px) {
    .course-learn {
      grid-template-columns: 1fr;
    }

    .course-learn__sidebar {
      order: 2;
    }
  }

  .course-learn__main {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }

  .course-header-card {
    display: grid;
    grid-template-columns: 228px minmax(300px, 1fr) 286px;
    gap: 30px;
    align-items: center;
    box-sizing: border-box;
    height: 170px;
    padding: 16px 18px;
    border: 1px solid var(--classroom-border);
    border-radius: 12px;
    background: var(--classroom-surface);
    box-shadow: 0 2px 12px rgba(35, 50, 90, 0.06);
  }

  @media (max-width: 900px) {
    .course-header-card {
      grid-template-columns: 1fr;
    }

    .course-header-card__meta {
      grid-template-columns: repeat(2, 1fr) !important;
    }
  }

  .course-cover {
    position: relative;
    width: 228px;
    height: 140px;
    overflow: hidden;
    border-radius: 9px;
    background: #0b2b75;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      filter: saturate(1.08) contrast(1.06);
    }

    &__glow {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: radial-gradient(
        circle at 48% 45%,
        rgba(79, 210, 255, 0.18),
        transparent 42%
      );
    }
  }

  .course-header-card__info {
    min-width: 0;
  }

  .course-heading {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .course-title {
    margin: 0;
    color: #10172a;
    font-size: 26px;
    font-weight: 750;
    letter-spacing: -0.04em;
    line-height: 1.35;
  }

  .course-badge {
    padding: 5px 10px;
    border-radius: 999px;
    background: #f0efff;
    color: #5e60d8;
    font-size: 11px;
    font-weight: 600;
  }

  .course-teacher {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    color: #25324c;
    font-size: 13px;

    span {
      margin-left: 4px;
      padding: 4px 9px;
      border-radius: 999px;
      color: #727e9a;
      background: #f7f8fc;
      font-size: 11px;
    }
  }

  .teacher-avatar {
    width: 30px;
    height: 30px;
    object-fit: cover;
    border-radius: 50%;
    border: 2px solid #eef0ff;
  }

  .course-progress-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 15px;
  }

  .course-progress-row__label {
    color: #526079;
    font-size: 12px;
    white-space: nowrap;
  }

  .progress-bar {
    flex: 1;
    max-width: 250px;
  }

  .progress-label {
    color: #435278;
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
  }

  .course-progress-copy {
    margin: 3px 0 0 78px;
    color: #8791a9;
    font-size: 11px;
  }

  .course-header-card__meta {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px 16px;
    min-width: 286px;
    padding-left: 24px;
    border-left: 1px solid #edf0f6;
  }

  .meta-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;

    &__icon {
      display: grid;
      width: 30px;
      height: 30px;
      flex: 0 0 30px;
      place-items: center;
      border-radius: 8px;
      color: #5367f8;
      background: #f1f4ff;

      &--violet {
        color: #7869e8;
        background: #f3f0ff;
      }

      &--cyan {
        color: #2786c7;
        background: #edf8ff;
      }

      &--amber {
        color: #d58a2d;
        background: #fff7e9;
      }
    }

    &__copy {
      display: flex;
      flex-direction: column;
      gap: 4px;

      small {
        color: #8a95aa;
        font-size: 10px;
      }

      strong {
        color: #1d2943;
        font-size: 14px;
        font-weight: 650;
      }
    }
  }

  .video-card,
  .section-card,
  .chapter-card {
    border: 1px solid var(--classroom-border);
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 2px 12px rgba(35, 50, 90, 0.06);
    overflow: hidden;
  }

  .video-card__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 50px;
    gap: 12px;
    padding: 8px 16px;
    flex-wrap: wrap;
  }

  .video-lesson-title {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 0;
    color: #28344c;
    font-size: 13px;

    span {
      font-weight: 700;
    }

    strong {
      font-weight: 600;
    }
  }

  .video-actions {
    display: flex;
    gap: 6px;
  }

  .action-btn {
    height: 32px;
    border: 0 !important;
    border-radius: 7px;
    color: #55627b !important;
    background: #f7f8fc !important;

    &--active {
      color: #5367f8 !important;
      background: #eff1ff !important;
    }
  }

  .video-card__player {
    position: relative;
    margin: 0 16px 8px;
    overflow: hidden;
    border-radius: 5px;
    background: #071226;
  }

  .video-file-input {
    display: none;
  }

  .video-element {
    display: block;
    width: 100%;
    height: 192px;
    object-fit: cover;
    background: #0f172a;
  }

  .video-upload-trigger {
    position: absolute;
    top: 12px;
    right: 12px;
    display: flex;
    align-items: center;
    gap: 5px;
    height: 30px;
    padding: 0 10px;
    border: 1px solid rgba(255, 255, 255, 0.28);
    border-radius: 7px;
    color: rgba(255, 255, 255, 0.9);
    background: rgba(10, 23, 51, 0.58);
    backdrop-filter: blur(10px);
    font: inherit;
    font-size: 11px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.18s ease;
  }

  .video-card__player:hover .video-upload-trigger,
  .video-upload-trigger:focus-visible {
    opacity: 1;
  }

  .section-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 42px;
    padding: 0 18px;
  }

  .section-card__title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #26334d;
    font-size: 13px;
    font-weight: 700;
  }

  .section-card__hint {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: #8a95aa;
    font-size: 10px;
  }

  .timeline-wrap {
    height: 105px;
    padding: 0 10px 4px;

    :deep(.focus-chart) {
      height: 105px;
    }
  }

  .artifact-panel {
    overflow: hidden;
    border-radius: 12px;
    background: #fff;
    border: 1px solid var(--classroom-border);
    box-shadow: 0 2px 12px rgba(35, 50, 90, 0.05);
  }

  .artifact-panel__head {
    height: 38px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #edf0fb;
  }

  .panel-text-action {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    color: #6072f5 !important;
    font-size: 10px;
    font-weight: 600;
  }

  .course-selection-root {
    user-select: text;
    cursor: text;

    ::selection {
      background: rgba(77, 124, 254, 0.24);
      color: #172033;
    }
  }

  .notes-panel {
    background: #fff;
  }

  .notes-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    padding: 14px 16px 16px;
  }

  @media (max-width: 1000px) {
    .notes-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 560px) {
    .notes-grid {
      grid-template-columns: 1fr;
    }
  }

  .note-col {
    position: relative;
    min-width: 0;
    padding: 0 0 0 14px;

    &:not(:first-child) {
      border-left: 1px solid #edf0f6;
    }

    &__num {
      display: none;
    }

    &__title {
      margin: 0 0 5px;
      color: #2c3953;
      font-size: 11px;
      font-weight: 700;
    }

    &__list {
      margin: 0;
      padding-left: 12px;
      color: #68758d;
      font-size: 9px;
      line-height: 1.65;

      li {
        margin-bottom: 1px;
        padding-left: 1px;

        &::marker {
          color: #6576e8;
          font-size: 0.7em;
        }
      }
    }
  }

  .knowledge-row {
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    gap: 10px;
  }

  @media (max-width: 900px) {
    .knowledge-row {
      grid-template-columns: 1fr;
    }
  }

  .knowledge-card__body {
    height: 210px;
    margin: 0;
    overflow: hidden;
    background: #fff;
  }

  .knowledge-card__body--mind {
    border: 0;
  }

  .knowledge-card__body--graph {
    border: 0;
    background: #fff;
  }

  .selection-context-menu {
    position: fixed;
    z-index: 10003;
    width: 172px;
    padding: 8px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(209, 216, 238, 0.96);
    box-shadow: 0 18px 42px rgba(22, 31, 60, 0.18);
    backdrop-filter: blur(16px);
  }

  .selection-context-menu__title {
    padding: 6px 8px 8px;
    font-size: 12px;
    font-weight: 700;
    color: #172033;
    border-bottom: 1px solid #edf0fb;
    margin-bottom: 4px;
  }

  .selection-context-menu__item {
    width: 100%;
    border: 0;
    background: transparent;
    padding: 9px 8px;
    border-radius: 8px;
    text-align: left;
    font: inherit;
    font-size: 13px;
    color: #43506a;
    cursor: pointer;
    transition: all 0.16s ease;

    &:hover {
      background: #f0f4ff;
      color: #2f63e6;
    }
  }

  .sel-menu-enter-active,
  .sel-menu-leave-active {
    transition: opacity 0.18s ease, transform 0.18s ease;
  }

  .sel-menu-enter-from,
  .sel-menu-leave-to {
    opacity: 0;
    transform: translateY(4px) scale(0.98);
  }

  .selection-bridge {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 10002;
  }

  .selection-bridge-line {
    stroke-dasharray: 8 7;
    filter: drop-shadow(0 0 6px rgba(47, 123, 255, 0.55));
    animation: selection-bridge-flow 0.62s ease forwards;
  }

  @keyframes selection-bridge-flow {
    from {
      opacity: 0.2;
      stroke-dashoffset: 36;
    }
    to {
      opacity: 1;
      stroke-dashoffset: 0;
    }
  }

  .chapter-card {
    position: sticky;
    top: 76px;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 88px);
    min-height: 760px;
    background: #fff;
  }

  .chapter-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 54px;
    padding: 0 18px;
    border-bottom: 1px solid #edf0f6;
    color: #1c2941;
    font-size: 15px;

    span {
      color: #8b95a9;
      font-size: 11px;

      b {
        color: #5668f6;
      }
    }
  }

  .chapter-accordion {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    scrollbar-width: thin;
  }

  .chapter-group {
    border-bottom: 1px solid #edf0f6;

    &__header {
      display: flex;
      align-items: center;
      gap: 7px;
      width: 100%;
      min-height: 43px;
      padding: 8px 16px;
      border: none;
      background: #fff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      color: #4f63d8;
      text-align: left;
      font-family: inherit;
      transition: background 0.15s ease;

      &:hover {
        background: #f8f9ff;
      }
    }

    &__fold {
      margin-left: auto;
      color: #73809c;
    }

    &__body {
      padding: 0 10px 5px;
    }
  }

  .lesson-item {
    display: flex;
    align-items: center;
    gap: 7px;
    width: 100%;
    min-height: 39px;
    padding: 7px 10px 7px 18px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: 6px;
    font-size: 11px;
    color: #60708d;
    text-align: left;
    font-family: inherit;
    transition: all 0.15s ease;

    &:hover {
      background: #f7f8ff;
    }

    &--done {
      color: #445571;
    }

    &--playing {
      background: #f0f1ff;
      color: #5265ed;
      font-weight: 600;
    }

    &__label {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .lesson-icon {
    flex-shrink: 0;
    width: 13px;
    height: 13px;
    font-size: 13px;

    &--done {
      color: #6578f7;
    }

    &--playing {
      color: #6578f7;
    }

    &--pending {
      box-sizing: border-box;
      border: 1px solid #d9deea;
      border-radius: 50%;
    }
  }

  .download-all-btn {
    flex: 0 0 42px;
    height: 42px;
    border: 0 !important;
    border-top: 1px solid #edf0f6 !important;
    border-radius: 0;
    color: #5668f6 !important;
    background: #fff !important;
  }

  @media (max-width: 1280px) {
    .course-learn {
      grid-template-columns: minmax(0, 1fr) 300px;
    }

    .course-header-card {
      grid-template-columns: 180px minmax(260px, 1fr) 240px;
      gap: 20px;
    }

    .course-cover {
      width: 180px;
    }

    .course-header-card__meta {
      min-width: 240px;
      padding-left: 18px;
    }
  }

  @media (max-width: 900px) {
    .course-cover {
      width: 100%;
      height: 180px;
    }

    .course-header-card__meta {
      min-width: 0;
      padding: 16px 0 0;
      border-top: 1px solid #edf0f6;
      border-left: 0;
    }

    .chapter-card {
      position: static;
      height: auto;
      min-height: 0;
    }

    .chapter-accordion {
      max-height: 520px;
    }

    .video-element {
      height: auto;
      aspect-ratio: 16 / 9;
    }
  }
</style>
