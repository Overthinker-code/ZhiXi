<template>
  <ZyPageShell title="" max-width="1480px">
    <section v-if="!currentCourse" class="course-picker">
      <header class="picker-header">
        <div>
          <span class="picker-kicker">课堂内容</span>
          <h1>选择要继续学习的课程</h1>
          <p>六门课程均已配置独立章节、课堂笔记、思维导图和知识图谱。</p>
        </div>
        <div class="picker-summary">
          <strong>6</strong>
          <span>门在学课程</span>
        </div>
      </header>

      <div class="picker-grid">
        <article
          v-for="course in classroomCourses"
          :key="course.id"
          class="picker-card"
          tabindex="0"
          @click="openCourse(course.id)"
          @keydown.enter="openCourse(course.id)"
        >
          <div class="picker-card__cover">
            <img :src="course.cover" :alt="course.title" />
            <span>{{ course.department }}</span>
          </div>
          <div class="picker-card__body">
            <div class="picker-card__title">
              <h2>{{ course.title }}</h2>
              <small>{{ course.type }}</small>
            </div>
            <p>{{ course.description }}</p>
            <div class="picker-card__teacher">
              <img :src="teacherAvatarImg" alt="" />
              <span>{{ course.teacher }}</span>
              <i>{{ course.team }}</i>
            </div>
            <div class="picker-card__progress">
              <div>
                <span>学习进度</span>
                <strong>{{ course.progress }}%</strong>
              </div>
              <div class="progress-track">
                <i :style="{ width: `${course.progress}%`, background: course.accent }"></i>
              </div>
            </div>
            <button type="button" class="enter-course-btn">
              进入课堂 <icon-arrow-right />
            </button>
          </div>
        </article>
      </div>
    </section>

    <div v-else class="classroom-page">
      <div class="classroom-topbar">
        <button type="button" class="back-picker-btn" @click="backToPicker">
          <icon-left /> 全部课程
        </button>
        <div class="course-switcher">
          <span>当前课程</span>
          <a-select
            :model-value="currentCourse.id"
            :options="courseOptions"
            size="small"
            @change="openCourse(String($event))"
          />
        </div>
      </div>

      <section class="course-overview-card">
        <img class="overview-cover" :src="currentCourse.cover" :alt="currentCourse.title" />
        <div class="overview-info">
          <div class="overview-heading">
            <h1>{{ currentCourse.title }}</h1>
            <span>{{ currentCourse.department }}</span>
          </div>
          <p>{{ currentCourse.description }}</p>
          <div class="overview-teacher">
            <img :src="teacherAvatarImg" alt="" />
            <strong>{{ currentCourse.teacher }}</strong>
            <span>{{ currentCourse.team }}</span>
          </div>
          <div class="overview-progress">
            <span>学习进度</span>
            <div class="overview-progress__track">
              <i
                :style="{
                  width: `${currentCourse.progress}%`,
                  background: currentCourse.accent,
                }"
              ></i>
            </div>
            <strong>{{ currentCourse.progress }}%</strong>
            <small>已学 {{ currentCourse.learned }} / {{ currentCourse.total }} 节</small>
          </div>
        </div>
        <div class="overview-meta">
          <div v-for="item in courseMeta" :key="item.label">
            <span class="meta-icon"><component :is="item.icon" /></span>
            <p><small>{{ item.label }}</small><strong>{{ item.value }}</strong></p>
          </div>
        </div>
      </section>

      <div class="learning-layout">
        <main class="learning-main">
          <section class="video-card">
            <div class="video-toolbar">
              <div>
                <span>正在学习</span>
                <strong>{{ currentLesson.label }}</strong>
              </div>
              <div class="video-actions">
                <a-button size="small" @click="focusNotes">
                  <template #icon><icon-edit /></template>笔记
                </a-button>
                <a-button
                  size="small"
                  :class="{ favorite: isFavorite }"
                  @click="toggleFavorite"
                >
                  <template #icon>
                    <icon-heart-fill v-if="isFavorite" />
                    <icon-heart v-else />
                  </template>
                  {{ isFavorite ? '已收藏' : '收藏' }}
                </a-button>
                <a-button size="small" @click="downloadCurrentLesson">
                  <template #icon><icon-download /></template>下载
                </a-button>
              </div>
            </div>

            <div class="video-stage">
              <input
                ref="videoFileInput"
                type="file"
                accept="video/*"
                hidden
                @change="handleVideoUpload"
              />
              <video
                v-if="videoSrc"
                :src="videoSrc"
                controls
                autoplay
                class="video-element"
                :poster="currentCourse.cover"
              />
              <div v-else class="demo-frame">
                <img :src="currentCourse.cover" :alt="`${currentCourse.title}演示画面`" />
                <div class="demo-frame__shade"></div>
                <div class="demo-frame__content">
                  <button
                    type="button"
                    class="demo-play"
                    aria-label="载入本地课程视频"
                    @click="videoFileInput?.click()"
                  >
                    <icon-play-arrow-fill />
                  </button>
                  <strong>{{ currentLesson.title }}</strong>
                  <span>课程演示画面 · 暂无真实教学视频</span>
                </div>
                <button
                  type="button"
                  class="upload-video-btn"
                  @click="videoFileInput?.click()"
                >
                  <icon-upload /> 载入本地视频
                </button>
              </div>
            </div>
          </section>

          <section class="focus-card">
            <div class="panel-heading">
              <div><icon-bar-chart /><strong>内容时段与专注度</strong></div>
              <span>专注度越高，学习效果越好 <icon-info-circle /></span>
            </div>
            <div class="focus-chart-wrap"><VideoInfo /></div>
          </section>

          <section
            ref="notesPanel"
            class="artifact-panel notes-panel course-selection-root"
            @mouseup="handleTextSelection('.course-selection-root', $event)"
            @touchend="handleTextSelection('.course-selection-root', $event)"
          >
            <div class="panel-heading">
              <div><icon-file /><strong>课堂笔记</strong></div>
              <div class="panel-actions">
                <button type="button" @click="organizeNotes">
                  <icon-mind-mapping /> {{ notesOrganized ? '已智能整理' : 'AI 智能整理' }}
                </button>
                <button type="button" @click="openArtifact('notes')">
                  <icon-expand /> 放大阅读
                </button>
                <button type="button" @click="exportNotes">
                  <icon-download /> 导出
                </button>
              </div>
            </div>
            <div class="notes-grid">
              <article v-for="(note, index) in currentCourse.notes" :key="note.title">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <h3>{{ note.title }}</h3>
                <ul>
                  <li v-for="point in note.points" :key="point">{{ point }}</li>
                </ul>
              </article>
            </div>
          </section>

          <div class="knowledge-grid">
            <section class="artifact-panel knowledge-panel">
              <div class="panel-heading">
                <div><icon-bulb /><strong>思维导图</strong></div>
                <div class="panel-actions">
                  <button type="button" @click="openArtifact('mind')">
                    <icon-expand /> 放大
                  </button>
                  <button type="button" @click="exportCanvas('mind')">
                    <icon-download /> SVG
                  </button>
                </div>
              </div>
              <div class="concept-preview">
                <CourseConceptCanvas
                  ref="mindCanvas"
                  :title="currentCourse.title"
                  :short-title="currentCourse.shortTitle"
                  :concepts="currentCourse.concepts"
                  :accent="currentCourse.accent"
                  mode="mind"
                  @node-prompt="handleVisualNodePrompt($event)"
                />
              </div>
            </section>

            <section class="artifact-panel knowledge-panel">
              <div class="panel-heading">
                <div><icon-share-alt /><strong>课程知识图谱</strong></div>
                <div class="panel-actions">
                  <button type="button" @click="openArtifact('graph')">
                    <icon-expand /> 放大
                  </button>
                  <button type="button" @click="exportCanvas('graph')">
                    <icon-download /> SVG
                  </button>
                </div>
              </div>
              <div class="concept-preview">
                <CourseConceptCanvas
                  ref="graphCanvas"
                  :title="currentCourse.title"
                  :short-title="currentCourse.shortTitle"
                  :concepts="currentCourse.concepts"
                  :accent="currentCourse.accent"
                  mode="graph"
                  @node-prompt="handleVisualNodePrompt($event)"
                />
              </div>
            </section>
          </div>
        </main>

        <aside class="chapter-sidebar">
          <div class="chapter-header">
            <div>
              <strong>课程章节</strong>
              <span>{{ currentCourse.learned }} / {{ currentCourse.total }} 节</span>
            </div>
            <small>{{ currentCourse.progress }}%</small>
          </div>
          <div class="chapter-progress">
            <i
              :style="{
                width: `${currentCourse.progress}%`,
                background: currentCourse.accent,
              }"
            ></i>
          </div>
          <div class="chapter-list">
            <section
              v-for="chapter in currentCourse.chapters"
              :key="chapter.id"
              class="chapter-group"
            >
              <button type="button" class="chapter-title" @click="toggleChapter(chapter.id)">
                <icon-down v-if="openChapters.has(chapter.id)" />
                <icon-right v-else />
                <span>{{ chapter.title }}</span>
              </button>
              <div v-show="openChapters.has(chapter.id)" class="lesson-list">
                <button
                  v-for="lesson in chapter.lessons"
                  :key="lesson.id"
                  type="button"
                  :class="{
                    done: lesson.status === 'done',
                    active: currentLessonId === lesson.id,
                  }"
                  @click="selectLesson(lesson)"
                >
                  <span>{{ lesson.label }}</span>
                  <icon-check-circle-fill v-if="lesson.status === 'done'" />
                  <icon-play-circle-fill v-else-if="currentLessonId === lesson.id" />
                  <i v-else></i>
                </button>
              </div>
            </section>
          </div>
          <button type="button" class="download-all" @click="downloadAllLessons">
            <icon-download /> 下载全部课程资料
          </button>
        </aside>
      </div>
    </div>

    <a-modal
      v-model:visible="artifactVisible"
      :footer="false"
      :width="artifactType === 'notes' ? 1040 : 1180"
      modal-class="artifact-modal"
      unmount-on-close
    >
      <template #title>
        <div class="artifact-modal-title">
          <span>{{ artifactTitle }}</span>
          <small>{{ currentCourse?.title }}</small>
        </div>
      </template>
      <div
        v-if="artifactType === 'notes' && currentCourse"
        class="notes-modal course-selection-root"
        @mouseup="handleTextSelection('.course-selection-root', $event)"
        @touchend="handleTextSelection('.course-selection-root', $event)"
      >
        <article v-for="(note, index) in currentCourse.notes" :key="note.title">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div>
            <h3>{{ note.title }}</h3>
            <ul><li v-for="point in note.points" :key="point">{{ point }}</li></ul>
          </div>
        </article>
      </div>
      <div v-else-if="currentCourse" class="canvas-modal">
        <div class="canvas-toolbar">
          <button type="button" @click="changeZoom(-0.1)"><icon-zoom-out /></button>
          <span>{{ Math.round(artifactZoom * 100) }}%</span>
          <button type="button" @click="changeZoom(0.1)"><icon-zoom-in /></button>
          <button type="button" @click="artifactZoom = 1">重置</button>
          <button type="button" @click="exportModalCanvas">
            <icon-download /> 导出 SVG
          </button>
        </div>
        <div class="canvas-modal__body">
          <CourseConceptCanvas
            ref="modalCanvas"
            :title="currentCourse.title"
            :short-title="currentCourse.shortTitle"
            :concepts="currentCourse.concepts"
            :accent="currentCourse.accent"
            :mode="artifactType === 'graph' ? 'graph' : 'mind'"
            :zoom="artifactZoom"
            @node-prompt="handleVisualNodePrompt($event)"
          />
        </div>
      </div>
    </a-modal>

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
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  IconApps,
  IconArrowRight,
  IconBarChart,
  IconBulb,
  IconCheckCircleFill,
  IconClockCircle,
  IconDown,
  IconDownload,
  IconEdit,
  IconExpand,
  IconFile,
  IconHeart,
  IconHeartFill,
  IconInfoCircle,
  IconLayers,
  IconLeft,
  IconMindMapping,
  IconPlayArrowFill,
  IconPlayCircleFill,
  IconRight,
  IconShareAlt,
  IconUpload,
  IconZoomIn,
  IconZoomOut,
} from '@arco-design/web-vue/es/icon';
import ZyPageShell from '@/components/zy/ZyPageShell.vue';
import { useSelectionQueryMenu } from '@/composables/useSelectionQueryMenu';
import {
  classroomCourses,
  getClassroomCourse,
  type ClassroomLesson,
} from '@/data/classroomCourses';
import VideoInfo from './components/VideoInfo.vue';
import CourseConceptCanvas from './components/CourseConceptCanvas.vue';
import SelectionAiAnswerPanel from './components/SelectionAiAnswerPanel.vue';
import teacherAvatarImg from '@/assets/images/老师头像.png';

type ArtifactType = 'notes' | 'mind' | 'graph';
type CanvasExpose = { exportSvg: (filename: string) => void };

const route = useRoute();
const router = useRouter();
const videoFileInput = ref<HTMLInputElement | null>(null);
const videoSrc = ref<string | null>(null);
const localVideoUrl = ref<string | null>(null);
const currentLessonId = ref('');
const isFavorite = ref(false);
const notesOrganized = ref(false);
const notesPanel = ref<HTMLElement | null>(null);
const openChapters = ref(new Set<string>());
const artifactVisible = ref(false);
const artifactType = ref<ArtifactType>('notes');
const artifactZoom = ref(1);
const mindCanvas = ref<CanvasExpose | null>(null);
const graphCanvas = ref<CanvasExpose | null>(null);
const modalCanvas = ref<CanvasExpose | null>(null);

const currentCourse = computed(() =>
  getClassroomCourse(
    typeof route.params.courseId === 'string'
      ? route.params.courseId
      : typeof route.query.courseId === 'string'
        ? route.query.courseId
        : null
  )
);
const courseOptions = classroomCourses.map((course) => ({
  label: course.title,
  value: course.id,
}));
const allLessons = computed(() =>
  currentCourse.value?.chapters.flatMap((chapter) => chapter.lessons) || []
);
const currentLesson = computed(
  () =>
    allLessons.value.find((lesson) => lesson.id === currentLessonId.value) ||
    allLessons.value[0] ||
    { id: '', label: '', title: '', status: 'pending' as const }
);
const courseMeta = computed(() => {
  if (!currentCourse.value) return [];
  return [
    { label: '课程学时', value: `${currentCourse.value.hours} 学时`, icon: IconClockCircle },
    { label: '课程难度', value: currentCourse.value.difficulty, icon: IconLayers },
    { label: '课程类型', value: currentCourse.value.type, icon: IconApps },
    { label: '更新时间', value: currentCourse.value.updatedAt, icon: IconClockCircle },
  ];
});
const artifactTitle = computed(() => {
  if (artifactType.value === 'mind') return '思维导图';
  if (artifactType.value === 'graph') return '课程知识图谱';
  return '课堂笔记';
});
const courseContext = computed(() => {
  if (!currentCourse.value) return '';
  const notes = currentCourse.value.notes
    .map((item) => `${item.title}：${item.points.join('、')}`)
    .join('\n');
  const concepts = currentCourse.value.concepts
    .map((item) => `${item.title}：${item.points.join('、')}`)
    .join('\n');
  return `${currentCourse.value.title}\n${currentCourse.value.description}\n\n课堂笔记\n${notes}\n\n知识结构\n${concepts}`;
});

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
} = useSelectionQueryMenu(() => courseContext.value);

watch(
  currentCourse,
  (course) => {
    if (localVideoUrl.value) URL.revokeObjectURL(localVideoUrl.value);
    localVideoUrl.value = null;
    videoSrc.value = null;
    isFavorite.value = false;
    notesOrganized.value = false;
    currentLessonId.value = course?.chapters[0]?.lessons[0]?.id || '';
    openChapters.value = new Set(course?.chapters.map((chapter) => chapter.id) || []);
    clearAnswerPanel();
  },
  { immediate: true }
);

function openCourse(courseId: string) {
  router.push({ name: 'StudentCourseContent', params: { courseId } });
}

function backToPicker() {
  router.push({ name: 'CourseList' });
}

function toggleChapter(id: string) {
  const next = new Set(openChapters.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  openChapters.value = next;
}

function selectLesson(lesson: ClassroomLesson) {
  currentLessonId.value = lesson.id;
  Message.success(`已切换到 ${lesson.label}`);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function focusNotes() {
  notesPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function toggleFavorite() {
  isFavorite.value = !isFavorite.value;
  Message.success(isFavorite.value ? '已收藏当前课节' : '已取消收藏');
}

function organizeNotes() {
  notesOrganized.value = true;
  Message.success('课堂笔记已按知识结构重新整理');
}

function downloadText(filename: string, content: string, mime = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function notesMarkdown() {
  if (!currentCourse.value) return '';
  return [
    `# ${currentCourse.value.title}课堂笔记`,
    `## ${currentLesson.value.label}`,
    ...currentCourse.value.notes.flatMap((note) => [
      `### ${note.title}`,
      ...note.points.map((point) => `- ${point}`),
    ]),
  ].join('\n\n');
}

function exportNotes() {
  if (!currentCourse.value) return;
  downloadText(`${currentCourse.value.title}-课堂笔记.md`, notesMarkdown(), 'text/markdown;charset=utf-8');
  Message.success('课堂笔记已导出');
}

function downloadCurrentLesson() {
  if (!currentCourse.value) return;
  downloadText(
    `${currentLesson.value.id}-${currentLesson.value.title}.md`,
    notesMarkdown(),
    'text/markdown;charset=utf-8'
  );
  Message.success('当前课节资料已下载');
}

function downloadAllLessons() {
  if (!currentCourse.value) return;
  const catalog = currentCourse.value.chapters
    .map(
      (chapter) =>
        `## ${chapter.title}\n${chapter.lessons
          .map((lesson) => `- ${lesson.label}`)
          .join('\n')}`
    )
    .join('\n\n');
  downloadText(
    `${currentCourse.value.title}-课程资料.md`,
    `# ${currentCourse.value.title}\n\n${currentCourse.value.description}\n\n${catalog}\n\n${notesMarkdown()}`,
    'text/markdown;charset=utf-8'
  );
  Message.success('课程目录与笔记已下载');
}

function handleVideoUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (localVideoUrl.value) URL.revokeObjectURL(localVideoUrl.value);
  localVideoUrl.value = URL.createObjectURL(file);
  videoSrc.value = localVideoUrl.value;
  Message.success(`已载入本地视频：${file.name}`);
}

function openArtifact(type: ArtifactType) {
  artifactType.value = type;
  artifactZoom.value = 1;
  artifactVisible.value = true;
}

function changeZoom(delta: number) {
  artifactZoom.value = Math.min(1.6, Math.max(0.7, Number((artifactZoom.value + delta).toFixed(1))));
}

function exportCanvas(type: 'mind' | 'graph') {
  if (!currentCourse.value) return;
  const target = type === 'mind' ? mindCanvas.value : graphCanvas.value;
  target?.exportSvg(`${currentCourse.value.title}-${type === 'mind' ? '思维导图' : '知识图谱'}.svg`);
  Message.success('学习图谱已导出为 SVG');
}

function exportModalCanvas() {
  if (!currentCourse.value) return;
  modalCanvas.value?.exportSvg(
    `${currentCourse.value.title}-${artifactType.value === 'graph' ? '知识图谱' : '思维导图'}.svg`
  );
  Message.success('学习图谱已导出为 SVG');
}

function handleVisualNodePrompt(payload: { text: string; rect: DOMRect }) {
  openMenuForText(payload.text, payload.rect, courseContext.value);
}

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
.course-picker,
.classroom-page {
  color: #17213a;
}

.course-picker {
  padding-bottom: 30px;
}

.picker-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 8px 4px 22px;
  border-bottom: 1px solid #e7eaf2;

  h1 {
    margin: 8px 0 8px;
    font-size: 30px;
    letter-spacing: -.7px;
  }

  p {
    margin: 0;
    color: #7d879a;
    font-size: 14px;
  }
}

.picker-kicker {
  color: #5367f8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .12em;
}

.picker-summary {
  display: flex;
  align-items: baseline;
  gap: 8px;
  color: #8a94a7;

  strong {
    color: #5367f8;
    font-size: 32px;
  }
}

.picker-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.picker-card {
  overflow: hidden;
  border: 1px solid #e4e8f1;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 5px 18px rgba(31, 45, 84, .05);
  cursor: pointer;
  outline: none;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;

  &:hover,
  &:focus-visible {
    border-color: #c8d0ff;
    box-shadow: 0 14px 30px rgba(54, 67, 140, .12);
    transform: translateY(-4px);
  }
}

.picker-card__cover {
  position: relative;
  height: 168px;
  overflow: hidden;
  background: #10182a;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: .88;
    transition: transform 260ms ease;
  }

  &::after {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent 36%, rgba(8, 17, 38, .62));
    content: '';
  }

  span {
    position: absolute;
    z-index: 1;
    right: 13px;
    bottom: 12px;
    padding: 5px 9px;
    border: 1px solid rgba(255, 255, 255, .26);
    border-radius: 7px;
    color: #fff;
    background: rgba(12, 24, 50, .52);
    backdrop-filter: blur(8px);
    font-size: 10px;
  }
}

.picker-card:hover .picker-card__cover img {
  transform: scale(1.035);
}

.picker-card__body {
  padding: 17px 18px 18px;

  > p {
    min-height: 42px;
    margin: 10px 0 14px;
    color: #778298;
    font-size: 12px;
    line-height: 1.7;
  }
}

.picker-card__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;

  h2 {
    margin: 0;
    font-size: 18px;
  }

  small {
    padding: 4px 8px;
    border-radius: 6px;
    color: #596bfa;
    background: #f0f2ff;
    white-space: nowrap;
  }
}

.picker-card__teacher {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #465268;
  font-size: 12px;

  img {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    object-fit: cover;
  }

  i {
    color: #9aa3b3;
    font-size: 10px;
    font-style: normal;
  }
}

.picker-card__progress {
  margin-top: 15px;

  > div:first-child {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    color: #8892a4;
    font-size: 10px;

    strong {
      color: #526078;
    }
  }
}

.progress-track,
.chapter-progress {
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf0f6;

  i {
    display: block;
    height: 100%;
    border-radius: inherit;
  }
}

.enter-course-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 34px;
  margin-top: 16px;
  border: 0;
  border-radius: 8px;
  color: #5367f8;
  background: #f1f3ff;
  font-weight: 650;
  cursor: pointer;
}

.classroom-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -8px 0 10px;
}

.back-picker-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 10px;
  border: 1px solid #e2e6ef;
  border-radius: 8px;
  color: #667188;
  background: #fff;
  cursor: pointer;
}

.course-switcher {
  display: flex;
  align-items: center;
  gap: 8px;

  > span {
    color: #8a94a6;
    font-size: 11px;
  }

  :deep(.arco-select-view) {
    width: 190px;
    border-radius: 8px;
  }
}

.course-overview-card {
  display: grid;
  grid-template-columns: 210px minmax(360px, 1fr) 330px;
  align-items: center;
  gap: 24px;
  min-height: 146px;
  padding: 14px 18px;
  border: 1px solid #e4e8f1;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 3px 14px rgba(34, 48, 88, .05);
}

.overview-cover {
  width: 210px;
  height: 118px;
  border-radius: 9px;
  object-fit: cover;
}

.overview-heading {
  display: flex;
  align-items: center;
  gap: 10px;

  h1 {
    margin: 0;
    font-size: 24px;
    letter-spacing: -.5px;
  }

  span {
    padding: 4px 9px;
    border-radius: 999px;
    color: #596bfa;
    background: #f0f2ff;
    font-size: 10px;
  }
}

.overview-info > p {
  margin: 7px 0 9px;
  color: #7c879b;
  font-size: 11px;
}

.overview-teacher {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #3f4a61;
  font-size: 11px;

  img {
    width: 25px;
    height: 25px;
    border-radius: 50%;
    object-fit: cover;
  }

  span {
    color: #9099aa;
  }
}

.overview-progress {
  display: grid;
  grid-template-columns: auto minmax(120px, 240px) auto auto;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #7c879b;
  font-size: 10px;

  strong {
    color: #48556e;
  }

  small {
    color: #9ba4b5;
  }
}

.overview-progress__track {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: #e9edf5;

  i {
    display: block;
    height: 100%;
    border-radius: inherit;
  }
}

.overview-meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 17px;
  padding-left: 23px;
  border-left: 1px solid #e9edf4;

  > div {
    display: flex;
    align-items: center;
    gap: 9px;
  }

  p,
  small,
  strong {
    display: block;
    margin: 0;
  }

  small {
    margin-bottom: 3px;
    color: #9aa3b4;
    font-size: 9px;
  }

  strong {
    color: #344057;
    font-size: 12px;
  }
}

.meta-icon {
  display: grid;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  color: #596bfa;
  background: #f0f2ff;
  place-items: center;
}

.learning-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 14px;
  margin-top: 12px;
  align-items: start;
}

.learning-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 12px;
}

.video-card,
.focus-card,
.artifact-panel,
.chapter-sidebar {
  overflow: hidden;
  border: 1px solid #e4e8f1;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 3px 14px rgba(34, 48, 88, .045);
}

.video-toolbar,
.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 50px;
  gap: 12px;
  padding: 8px 15px;
  border-bottom: 1px solid #edf0f5;
}

.video-toolbar > div:first-child {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #68748a;
  font-size: 12px;

  span {
    color: #27334a;
    font-weight: 700;
  }
}

.video-actions {
  display: flex;
  gap: 6px;

  :deep(.arco-btn) {
    border: 0;
    border-radius: 7px;
    color: #59657b;
    background: #f6f7fb;
  }

  :deep(.favorite) {
    color: #596bfa;
    background: #eef1ff;
  }
}

.video-stage {
  margin: 0;
  background: #08111f;
  aspect-ratio: 16 / 8.65;
}

.video-element,
.demo-frame {
  display: block;
  width: 100%;
  height: 100%;
}

.video-element {
  object-fit: contain;
  background: #080f1d;
}

.demo-frame {
  position: relative;
  overflow: hidden;

  > img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: saturate(.88) contrast(1.04);
  }
}

.demo-frame__shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(5, 12, 27, .12), rgba(5, 12, 27, .58)),
    radial-gradient(circle at center, transparent 12%, rgba(5, 12, 27, .2));
}

.demo-frame__content {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  align-items: center;
  width: 72%;
  color: #fff;
  flex-direction: column;
  transform: translate(-50%, -44%);
  text-align: center;

  strong {
    margin-top: 17px;
    font-size: clamp(18px, 2.1vw, 31px);
    text-shadow: 0 4px 18px rgba(0, 0, 0, .45);
  }

  span {
    margin-top: 7px;
    color: rgba(255, 255, 255, .75);
    font-size: 11px;
  }
}

.demo-play {
  display: grid;
  width: 70px;
  height: 70px;
  border: 1px solid rgba(255, 255, 255, .46);
  border-radius: 50%;
  color: #fff;
  background: rgba(44, 89, 135, .72);
  backdrop-filter: blur(10px);
  place-items: center;
  font-size: 30px;
  cursor: pointer;
  transition: transform 180ms ease, background 180ms ease;

  &:hover {
    background: rgba(83, 103, 248, .86);
    transform: scale(1.06);
  }
}

.upload-video-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid rgba(255, 255, 255, .3);
  border-radius: 7px;
  color: #fff;
  background: rgba(7, 18, 38, .58);
  backdrop-filter: blur(8px);
  font-size: 10px;
  cursor: pointer;
}

.panel-heading {
  min-height: 46px;

  > div:first-child {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #2c3850;
    font-size: 13px;
  }

  > span {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #929cad;
    font-size: 10px;
  }
}

.focus-chart-wrap {
  height: 126px;
  padding: 0 12px 5px;

  :deep(.focus-chart) {
    height: 126px;
  }
}

.panel-actions {
  display: flex;
  gap: 4px;

  button {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 8px;
    border: 0;
    border-radius: 6px;
    color: #6675dc;
    background: #f4f5ff;
    font-size: 10px;
    cursor: pointer;
  }
}

.course-selection-root {
  user-select: text;

  ::selection {
    color: #17213a;
    background: rgba(83, 103, 248, .22);
  }
}

.notes-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 14px;

  article {
    min-height: 145px;
    padding: 14px;
    border: 1px solid #e7eaf2;
    border-radius: 10px;
    background: linear-gradient(145deg, #fff, #fafbff);
  }

  article > span {
    color: #8090f6;
    font-size: 10px;
    font-weight: 700;
  }

  h3 {
    margin: 7px 0 9px;
    color: #344057;
    font-size: 12px;
  }

  ul {
    margin: 0;
    padding-left: 16px;
    color: #707c91;
    font-size: 10px;
    line-height: 1.8;
  }

  li::marker {
    color: #6678f4;
  }
}

.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.concept-preview {
  height: 310px;
}

.chapter-sidebar {
  position: sticky;
  top: 76px;
  display: flex;
  max-height: calc(100vh - 88px);
  min-height: 650px;
  flex-direction: column;
}

.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px 10px;

  > div {
    strong,
    span {
      display: block;
    }

    strong {
      color: #263149;
      font-size: 14px;
    }

    span {
      margin-top: 4px;
      color: #929bad;
      font-size: 10px;
    }
  }

  small {
    color: #596bfa;
    font-weight: 700;
  }
}

.chapter-progress {
  margin: 0 16px 12px;
}

.chapter-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-top: 1px solid #edf0f5;
  scrollbar-width: thin;
}

.chapter-group {
  border-bottom: 1px solid #edf0f5;
}

.chapter-title {
  display: grid;
  align-items: center;
  width: 100%;
  min-height: 45px;
  padding: 8px 13px;
  grid-template-columns: 16px 1fr;
  gap: 7px;
  border: 0;
  color: #4c5c78;
  background: #fff;
  text-align: left;
  cursor: pointer;

  span {
    font-size: 11px;
    font-weight: 650;
  }
}

.lesson-list {
  padding: 3px 9px 8px;

  button {
    display: grid;
    align-items: center;
    width: 100%;
    min-height: 39px;
    padding: 7px 10px 7px 25px;
    grid-template-columns: 1fr 16px;
    gap: 6px;
    border: 0;
    border-radius: 7px;
    color: #778399;
    background: transparent;
    font-size: 10px;
    text-align: left;
    cursor: pointer;

    &:hover {
      color: #5062d8;
      background: #f6f7ff;
    }

    &.active {
      color: #5062d8;
      background: #eef1ff;
      font-weight: 650;
    }

    &.done svg {
      color: #6678f4;
    }

    i {
      width: 13px;
      height: 13px;
      border: 1px solid #d6dce7;
      border-radius: 50%;
    }
  }
}

.download-all {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 45px;
  border: 0;
  border-top: 1px solid #edf0f5;
  color: #596bfa;
  background: #fff;
  font-size: 11px;
  cursor: pointer;
}

.artifact-modal-title {
  display: flex;
  align-items: baseline;
  gap: 10px;

  small {
    color: #929bad;
    font-size: 11px;
    font-weight: 400;
  }
}

.notes-modal {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  max-height: 70vh;
  overflow-y: auto;
  padding: 4px;

  article {
    display: grid;
    grid-template-columns: 42px 1fr;
    gap: 12px;
    min-height: 180px;
    padding: 18px;
    border: 1px solid #e4e8f1;
    border-radius: 12px;
    background: #fbfcff;

    > span {
      display: grid;
      width: 38px;
      height: 38px;
      border-radius: 10px;
      color: #596bfa;
      background: #eef1ff;
      place-items: center;
      font-weight: 700;
    }
  }

  h3 {
    margin: 5px 0 12px;
    font-size: 16px;
  }

  ul {
    margin: 0;
    padding-left: 19px;
    color: #647188;
    line-height: 2;
  }
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-bottom: 9px;

  button {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 30px;
    padding: 0 10px;
    border: 1px solid #e0e5ee;
    border-radius: 7px;
    color: #5e6a80;
    background: #fff;
    cursor: pointer;
  }

  span {
    min-width: 46px;
    color: #596bfa;
    text-align: center;
    font-size: 11px;
  }
}

.canvas-modal__body {
  height: 68vh;
  overflow: hidden;
  border: 1px solid #e4e8f1;
  border-radius: 12px;
}

.selection-context-menu {
  position: fixed;
  z-index: 10003;
  width: 172px;
  padding: 8px;
  border: 1px solid rgba(209, 216, 238, .96);
  border-radius: 12px;
  background: rgba(255, 255, 255, .97);
  box-shadow: 0 18px 42px rgba(22, 31, 60, .18);
  backdrop-filter: blur(16px);
}

.selection-context-menu__title {
  margin-bottom: 4px;
  padding: 6px 8px 8px;
  border-bottom: 1px solid #edf0fb;
  color: #172033;
  font-size: 12px;
  font-weight: 700;
}

.selection-context-menu__item {
  width: 100%;
  padding: 9px 8px;
  border: 0;
  border-radius: 8px;
  color: #43506a;
  background: transparent;
  font-size: 13px;
  text-align: left;
  cursor: pointer;

  &:hover {
    color: #2f63e6;
    background: #f0f4ff;
  }
}

.sel-menu-enter-active,
.sel-menu-leave-active {
  transition: opacity .18s ease, transform .18s ease;
}

.sel-menu-enter-from,
.sel-menu-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(.98);
}

.selection-bridge {
  position: fixed;
  z-index: 10002;
  inset: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
}

.selection-bridge-line {
  stroke-dasharray: 8 7;
  filter: drop-shadow(0 0 6px rgba(47, 123, 255, .55));
}

@media (max-width: 1180px) {
  .picker-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .course-overview-card {
    grid-template-columns: 180px 1fr;
  }

  .overview-cover {
    width: 180px;
  }

  .overview-meta {
    grid-column: 1 / -1;
    padding: 12px 0 0;
    border-top: 1px solid #edf0f5;
    border-left: 0;
  }

  .learning-layout {
    grid-template-columns: 1fr;
  }

  .chapter-sidebar {
    position: static;
    min-height: 0;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .picker-header,
  .classroom-topbar {
    align-items: flex-start;
    gap: 14px;
    flex-direction: column;
  }

  .picker-grid,
  .knowledge-grid,
  .notes-modal {
    grid-template-columns: 1fr;
  }

  .course-overview-card {
    grid-template-columns: 1fr;
  }

  .overview-cover {
    width: 100%;
    height: 190px;
  }

  .notes-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .overview-progress {
    grid-template-columns: auto 1fr auto;

    small {
      grid-column: 2 / -1;
    }
  }
}
</style>
