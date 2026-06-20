<template>
  <ZyPageShell title="" max-width="1480px">
    <section v-if="!currentCourse" class="course-picker">
      <header class="picker-header">
        <div>
          <span class="picker-kicker">课堂内容</span>
          <h1>选择要继续学习的课程</h1>
          <p>六门课程均已配置独立章节、课堂笔记和可交互高清思维导图。</p>
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
                  width: `${displayProgress}%`,
                  background: currentCourse.accent,
                }"
              ></i>
            </div>
            <strong>{{ displayProgress }}%</strong>
            <small>已学 {{ displayLearned }} / {{ currentCourse.total }} 节</small>
          </div>
        </div>
        <div class="overview-meta">
          <div v-for="item in courseMeta" :key="item.label">
            <span class="meta-icon"><component :is="item.icon" /></span>
            <p><small>{{ item.label }}</small><strong>{{ item.value }}</strong></p>
          </div>
        </div>
      </section>

      <section class="learning-state-strip">
        <article v-for="item in learningStateCards" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <p>{{ item.desc }}</p>
        </article>
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
                <a-button size="small" type="primary" @click="completeCurrentLesson">
                  <template #icon><icon-check-circle-fill /></template>
                  {{ currentLessonCompleted ? '已完成' : '完成本节' }}
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
              <div v-else class="media-frame">
                <img :src="currentCourse.cover" :alt="`${currentCourse.title}课程资源预览`" />
                <div class="media-frame__shade"></div>
                <div class="media-frame__content">
                  <button
                    type="button"
                    class="media-play"
                    aria-label="载入本地课程视频"
                    @click="videoFileInput?.click()"
                  >
                    <icon-play-arrow-fill />
                  </button>
                  <strong>{{ currentLesson.title }}</strong>
                  <span>课程资源预览 · 可载入本地教学视频</span>
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
                <button type="button" @click="generateFromNotes">
                  <icon-robot /> 生成资料
                </button>
                <button type="button" :disabled="notesGenerating" @click="generateNotesPdfArtifact">
                  <icon-download /> PDF
                </button>
                <button type="button" @click="exportNotesDoc">
                  <icon-file /> Word
                </button>
                <button type="button" @click="exportNotes">
                  <icon-download /> Markdown
                </button>
              </div>
            </div>
            <div class="notes-brief">
              <article v-for="item in notesExplanation" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.desc }}</p>
              </article>
            </div>
            <div v-if="notesOrganized" class="notes-organized-banner">
              <div>
                <span>整理模式</span>
                <strong>按“定义 - 证据 - 误区 - 检查题 - 行动”重排课堂笔记</strong>
              </div>
              <button type="button" @click="selectedMindNodeText = currentCourse.notes[0]?.title || currentCourse.shortTitle">
                聚焦第一组主题
              </button>
            </div>
            <div class="notes-grid">
              <article
                v-for="(note, index) in organizedNoteCards"
                :key="note.title"
                :class="{ 'note-card--organized': notesOrganized }"
              >
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <div>
                  <h3>{{ note.title }}</h3>
                  <p>{{ note.detail }}</p>
                  <div v-if="notesOrganized" class="note-evidence-board">
                    <section>
                      <small>定义边界</small>
                      <strong>{{ note.definition }}</strong>
                    </section>
                    <section>
                      <small>课堂证据</small>
                      <strong>{{ note.evidence }}</strong>
                    </section>
                    <section>
                      <small>易错提醒</small>
                      <strong>{{ note.pitfall }}</strong>
                    </section>
                    <section>
                      <small>检查题</small>
                      <strong>{{ note.check }}</strong>
                    </section>
                  </div>
                  <div class="note-chip-row">
                    <button
                      v-for="point in note.points"
                      :key="point"
                      type="button"
                      class="note-chip"
                      :class="{ active: selectedMindNodeText === point }"
                      @click="selectMindText(point)"
                    >
                      {{ point }}
                    </button>
                  </div>
                  <div class="note-columns">
                    <section>
                      <strong>学习产出</strong>
                      <ul>
                        <li v-for="item in note.outcomes" :key="item">{{ item }}</li>
                      </ul>
                    </section>
                    <section>
                      <strong>常见误区</strong>
                      <ul>
                        <li v-for="item in note.misconceptions" :key="item">{{ item }}</li>
                      </ul>
                    </section>
                  </div>
                  <div class="note-action-strip">
                    <span v-for="item in note.activities" :key="item">{{ item }}</span>
                  </div>
                </div>
              </article>
            </div>
          </section>

          <section class="artifact-panel knowledge-panel mindmap-panel">
            <div class="panel-heading">
              <div><icon-bulb /><strong>课堂内容思维导图</strong></div>
              <div class="panel-actions">
                <button type="button" @click="openArtifact('mind')">
                  <icon-expand /> 高清放大
                </button>
                <button type="button" @click="exportCanvas('mind')">
                  <icon-download /> SVG
                </button>
                <button type="button" @click="askMindMapTutor">
                  <icon-robot /> AI 解读
                </button>
              </div>
            </div>
            <div class="mindmap-intro">
              <div>
                <strong>{{ currentCourse.shortTitle }}知识框架</strong>
                <p>点击任意节点可定位证据、资源、检查题和相邻知识；课堂笔记中的知识点也会反向联动导图。</p>
              </div>
              <div class="mindmap-stats">
                <span v-for="item in mindMapStats" :key="item.label">
                  <b>{{ item.value }}</b>{{ item.label }}
                </span>
              </div>
            </div>
            <div class="mindmap-workbench">
              <div class="concept-preview concept-preview--large">
                <CourseConceptCanvas
                  ref="mindCanvas"
                  :title="currentCourse.title"
                  :short-title="currentCourse.shortTitle"
                  :concepts="currentCourse.concepts"
                  :accent="currentCourse.accent"
                  mode="mind"
                  :active-node="activeMindCanvasNode"
                  @node-prompt="handleVisualNodePrompt($event)"
                />
              </div>
              <aside v-if="mindNodeProfile" class="mind-node-card">
                <span>{{ mindNodeProfile.kind }}</span>
                <h3>{{ mindNodeProfile.title }}</h3>
                <p>{{ mindNodeProfile.detail }}</p>
                <div class="mind-node-summary">
                  <div>
                    <strong>{{ mindNodeProfile.mastery }}%</strong>
                    <small>掌握度</small>
                  </div>
                  <div>
                    <strong>{{ mindNodeProfile.resources.length }}</strong>
                    <small>证据资源</small>
                  </div>
                  <div>
                    <strong>{{ mindNodeProfile.checks.length }}</strong>
                    <small>检查题</small>
                  </div>
                </div>
                <div class="mind-node-section">
                  <strong>学习产出</strong>
                  <em v-for="item in mindNodeProfile.outcomes.slice(0, 3)" :key="item">{{ item }}</em>
                </div>
                <div class="mind-node-section resource-list">
                  <strong>证据资源</strong>
                  <button
                    v-for="item in mindNodeProfile.resources.slice(0, 3)"
                    :key="item"
                    type="button"
                    @click="openMindCheckPrompt(item, $event)"
                  >
                    {{ item }}
                  </button>
                </div>
                <div class="mind-node-section">
                  <strong>常见误区</strong>
                  <em v-for="item in mindNodeProfile.misconceptions.slice(0, 2)" :key="item">{{ item }}</em>
                </div>
                <div v-if="mindNodeNeighbors.length" class="mind-node-section relation-list">
                  <strong>相邻知识</strong>
                  <button
                    v-for="item in mindNodeNeighbors"
                    :key="`${item.relation}-${item.title}`"
                    type="button"
                    @click="selectMindText(item.title)"
                  >
                    <span>{{ item.relation }}</span>{{ item.title }}
                  </button>
                </div>
                <div class="mind-node-section compact">
                  <strong>检查题</strong>
                  <button
                    v-for="item in mindNodeProfile.checks.slice(0, 3)"
                    :key="item"
                    type="button"
                    @click="openMindCheckPrompt(item, $event)"
                  >
                    {{ item }}
                  </button>
                </div>
                <div class="mind-node-actions">
                  <button type="button" @click="askMindMapTutor">
                    <icon-robot /> AI 解读
                  </button>
                  <button type="button" @click="generateFromNotes">
                    <icon-file /> 生成资料
                  </button>
                  <button type="button" @click="downloadMindNodePack">
                    <icon-download /> 节点学习单
                  </button>
                </div>
              </aside>
            </div>
          </section>
        </main>

        <aside class="chapter-sidebar">
          <div class="chapter-header">
            <div>
              <strong>课程章节</strong>
              <span>{{ displayLearned }} / {{ currentCourse.total }} 节</span>
            </div>
            <small>{{ displayProgress }}%</small>
          </div>
          <div class="chapter-progress">
            <i
              :style="{
                width: `${displayProgress}%`,
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
                    done: completedLessonIds.has(lesson.id),
                    active: currentLessonId === lesson.id,
                  }"
                  @click="selectLesson(lesson)"
                >
                  <span>{{ lesson.label }}</span>
                  <icon-check-circle-fill v-if="completedLessonIds.has(lesson.id)" />
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
      :width="artifactType === 'notes' ? 1040 : 1280"
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
            <p>{{ note.detail }}</p>
            <h4>学习产出</h4>
            <ul><li v-for="item in note.outcomes" :key="item">{{ item }}</li></ul>
            <h4>检查问题</h4>
            <ul><li v-for="item in note.checks" :key="item">{{ item }}</li></ul>
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
        <div class="canvas-modal__body canvas-modal__body--mind">
          <CourseConceptCanvas
            ref="modalCanvas"
            :title="currentCourse.title"
            :short-title="currentCourse.shortTitle"
            :concepts="currentCourse.concepts"
            :accent="currentCourse.accent"
            mode="mind"
            :zoom="artifactZoom"
            :active-node="activeMindCanvasNode"
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
      :citations="responseCitations"
      :citation-hints="responseCitationHints"
      :confidence="responseConfidence"
      :grounding-mode="responseGroundingMode"
      :metrics="responseMetrics"
      @close="clearAnswerPanel"
    />
  </ZyPageShell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import type { LocationQueryRaw } from 'vue-router';
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
  IconRobot,
  IconUpload,
  IconZoomIn,
  IconZoomOut,
} from '@arco-design/web-vue/es/icon';
import axios from 'axios';
import ZyPageShell from '@/components/zy/ZyPageShell.vue';
import { courseWorkspaceLocation } from '@/composables/useCourseRouteContext';
import { useSelectionQueryMenu } from '@/composables/useSelectionQueryMenu';
import {
  generateResourcePackage as generateDownloadableResourcePackage,
  type GeneratedResourceArtifact,
} from '@/api/resource-generation';
import { getToken } from '@/utils/auth';
import {
  classroomCourses,
  getClassroomCourse,
  type ClassroomConcept,
  type ClassroomLesson,
} from '@/data/classroomCourses';
import VideoInfo from './components/VideoInfo.vue';
import CourseConceptCanvas from './components/CourseConceptCanvas.vue';
import SelectionAiAnswerPanel from './components/SelectionAiAnswerPanel.vue';
import teacherAvatarImg from '@/assets/images/老师头像.png';

type ArtifactType = 'notes' | 'mind';
type CanvasExpose = { exportSvg: (filename: string) => void };
type OrganizedNoteCard = ClassroomConcept & {
  definition: string;
  evidence: string;
  pitfall: string;
  check: string;
  activities: string[];
};
type LocalLearningState = {
  lessonId: string;
  isFavorite: boolean;
  notesOrganized: boolean;
  selectedMindNodeText: string;
  completedLessonIds: string[];
  actionCount: number;
  generatedCount: number;
  downloadCount: number;
  lastActiveAt: string;
};

const emptyLearningState: LocalLearningState = {
  lessonId: '',
  isFavorite: false,
  notesOrganized: false,
  selectedMindNodeText: '',
  completedLessonIds: [],
  actionCount: 0,
  generatedCount: 0,
  downloadCount: 0,
  lastActiveAt: '',
};

const route = useRoute();
const router = useRouter();
const videoFileInput = ref<HTMLInputElement | null>(null);
const videoSrc = ref<string | null>(null);
const localVideoUrl = ref<string | null>(null);
const currentLessonId = ref('');
const isFavorite = ref(false);
const notesOrganized = ref(false);
const notesGenerating = ref(false);
const notesPanel = ref<HTMLElement | null>(null);
const openChapters = ref(new Set<string>());
const artifactVisible = ref(false);
const artifactType = ref<ArtifactType>('notes');
const artifactZoom = ref(1);
const mindCanvas = ref<CanvasExpose | null>(null);
const modalCanvas = ref<CanvasExpose | null>(null);
const selectedMindNodeText = ref('');
const localLearningState = ref<LocalLearningState>({ ...emptyLearningState });

function routeQueryText(value: unknown) {
  if (Array.isArray(value)) return String(value[0] || '').trim();
  return typeof value === 'string' ? value.trim() : '';
}

function incomingMindNodeText() {
  return (
    routeQueryText(route.query.nodeLabel) ||
    routeQueryText(route.query.node) ||
    routeQueryText(route.query.topic)
  );
}

function resolveIncomingMindNodeText(course = currentCourse.value) {
  const directText = incomingMindNodeText();
  if (!course) return directText;
  const nodeId = routeQueryText(route.query.nodeId);
  const chapterMatch = /^chapter-(\d+)$/u.exec(nodeId);
  if (chapterMatch) {
    const chapterIndex = Number(chapterMatch[1]);
    return course.concepts[chapterIndex]?.title || course.notes[chapterIndex]?.title || directText;
  }
  if (!directText) return '';
  const exactMatch = [...course.concepts, ...course.notes].some(
    (item) => item.title === directText || item.points.includes(directText)
  );
  if (exactMatch) return directText;
  const fuzzyConcept = course.concepts.find(
    (item) => directText.includes(item.title) || item.title.includes(directText)
  );
  return fuzzyConcept?.title || directText;
}

type ClassroomQueryValue = string | number | null | undefined;

function incomingNodeContext(extra: Record<string, ClassroomQueryValue> = {}): LocationQueryRaw {
  return Object.fromEntries(
    Object.entries({
      nodeId: routeQueryText(route.query.nodeId),
      nodeLabel: selectedMindNodeText.value || incomingMindNodeText(),
      mapType: routeQueryText(route.query.mapType),
      topic: selectedMindNodeText.value || incomingMindNodeText() || currentLesson.value.title,
      lessonId: currentLesson.value.id,
      ...extra,
    }).filter(([, value]) => value !== undefined && value !== null && value !== '')
  ) as LocationQueryRaw;
}

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
const completedLessonIds = computed(() => {
  const ids = new Set(
    allLessons.value.filter((lesson) => lesson.status === 'done').map((lesson) => lesson.id)
  );
  localLearningState.value.completedLessonIds.forEach((id) => ids.add(id));
  return ids;
});
const currentLessonCompleted = computed(() => completedLessonIds.value.has(currentLesson.value.id));
const displayLearned = computed(() => completedLessonIds.value.size);
const displayProgress = computed(() => {
  const total = currentCourse.value?.total || allLessons.value.length || 1;
  return Math.max(
    currentCourse.value?.progress || 0,
    Math.round((displayLearned.value / Math.max(total, 1)) * 100)
  );
});
const learningStateCards = computed(() => {
  const lastActive = localLearningState.value.lastActiveAt
    ? new Date(localLearningState.value.lastActiveAt).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '本次进入';
  return [
    {
      label: '最近课节',
      value: currentLesson.value.label || '未选择',
      desc: currentLesson.value.title || '打开课程后自动恢复上次学习位置',
    },
    {
      label: '本地进度',
      value: `${displayProgress.value}%`,
      desc: `${displayLearned.value}/${currentCourse.value?.total || allLessons.value.length} 节完成，刷新后保留`,
    },
    {
      label: '学习动作',
      value: `${localLearningState.value.actionCount}`,
      desc: `最近活跃：${lastActive}`,
    },
    {
      label: '产物沉淀',
      value: `${localLearningState.value.generatedCount + localLearningState.value.downloadCount}`,
      desc: `${localLearningState.value.generatedCount} 次生成 · ${localLearningState.value.downloadCount} 次下载`,
    },
  ];
});
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
  return '课堂笔记';
});
const notesExplanation = computed(() => {
  if (!currentCourse.value) return [];
  const firstNote = currentCourse.value.notes[0];
  const firstConcept = currentCourse.value.concepts[0];
  return [
    {
      label: '学习目标',
      value: currentLesson.value.title || currentCourse.value.shortTitle,
      desc: `用本节内容解释${firstNote?.title || '核心概念'}，并能说出适用条件与常见误区。`,
    },
    {
      label: '复习路径',
      value: firstConcept?.title || '核心框架',
      desc: '先复述概念，再用导图定位前后置关系，最后生成练习检查掌握度。',
    },
    {
      label: '可生成资料',
      value: 'PDF / Word / SVG',
      desc: notesOrganized.value
        ? '导出内容会保留整理后的定义、证据、误区、检查题和行动项。'
        : '笔记可一键导出，PDF 讲义由后端资源生成链路实时产出。',
    },
  ];
});
const organizedNoteCards = computed<OrganizedNoteCard[]>(() => {
  const course = currentCourse.value;
  if (!course) return [];
  return course.notes.map((note, index) => {
    const concept = course.concepts[index] || course.concepts[0] || note;
    const primary = note.points[0] || note.title;
    const secondary = note.points[1] || concept.points[0] || note.title;
    const activity = note.activities?.[0] || `围绕 ${note.title} 完成概念复述和错因订正。`;
    return {
      ...note,
      definition: `${note.title} 需要先说清“是什么、解决什么问题、适用到哪一步”。${primary} 是本组笔记的入口证据。`,
      evidence: `${secondary} 与 ${concept.title} 形成课堂证据链，建议回到当前课节标出定义、条件和例题位置。`,
      pitfall:
        note.misconceptions?.[0] ||
        `只记 ${primary} 的结论但没有说明适用条件，会导致后续推理断裂。`,
      check:
        note.checks?.[0] ||
        `我能否用一个课程案例解释 ${note.title}，并指出 ${primary} 的证据？`,
      activities: [
        activity,
        `把 ${note.points.slice(0, 3).join('、')} 写成三列对照表。`,
        `完成检查题后进入思维导图节点，补齐相邻知识关系。`,
      ],
    };
  });
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
const mindNodeProfile = computed(() => {
  const course = currentCourse.value;
  if (!course) return null;
  const fallbackConcept = course.concepts[0] || course.notes[0];
  const selectedText = selectedMindNodeText.value || course.shortTitle;
  const matchedConcept =
    course.concepts.find((item) => item.title === selectedText) ||
    course.concepts.find((item) => item.points.includes(selectedText)) ||
    course.notes.find((item) => item.title === selectedText) ||
    course.notes.find((item) => item.points.includes(selectedText)) ||
    fallbackConcept;
  if (!matchedConcept) {
    return {
      kind: '课程总览',
      title: course.shortTitle,
      detail: course.description,
      outcomes: [`能复述${course.shortTitle}的课程主线。`],
      misconceptions: ['只看节点名称，不回到课堂证据。'],
      checks: ['我能否说出当前课程最关键的三个知识点？'],
      resources: [`${course.shortTitle} 总览讲义`],
      activities: ['先选中一个主题节点，再进入右侧检查题完成自测。'],
      mastery: course.progress,
    };
  }
  const isPoint = matchedConcept.points.includes(selectedText);
  return normalizeMindNodeProfile(matchedConcept, isPoint ? selectedText : matchedConcept.title, isPoint);
});
const mindMapStats = computed(() => {
  const course = currentCourse.value;
  if (!course) return [];
  const pointCount = course.concepts.reduce((sum, concept) => sum + concept.points.length, 0);
  const checkCount = course.concepts.reduce(
    (sum, concept) => sum + (concept.checks?.length || 0),
    0
  );
  return [
    { label: '主题', value: course.concepts.length },
    { label: '知识点', value: pointCount },
    { label: '检查题', value: checkCount },
  ];
});
const mindNodeNeighbors = computed(() => {
  const course = currentCourse.value;
  const selectedText = selectedMindNodeText.value;
  if (!course || !selectedText) return [];
  const conceptIndex = course.concepts.findIndex(
    (item) => item.title === selectedText || item.points.includes(selectedText)
  );
  if (conceptIndex < 0) {
    return course.concepts.slice(0, 3).map((item, index) => ({
      relation: index === 0 ? '课程主线' : '并列主题',
      title: item.title,
    }));
  }
  const concept = course.concepts[conceptIndex];
  const neighbors = [
    conceptIndex > 0 ? { relation: '前置主题', title: course.concepts[conceptIndex - 1].title } : null,
    concept.title !== selectedText ? { relation: '所属主题', title: concept.title } : null,
    ...concept.points
      .filter((point) => point !== selectedText)
      .slice(0, 3)
      .map((point) => ({ relation: '同组知识', title: point })),
    course.concepts[conceptIndex + 1]
      ? { relation: '后续主题', title: course.concepts[conceptIndex + 1].title }
      : null,
  ].filter(Boolean) as Array<{ relation: string; title: string }>;
  return neighbors.slice(0, 5);
});
const activeMindCanvasNode = computed(() => {
  const course = currentCourse.value;
  const selectedText = selectedMindNodeText.value;
  if (!course || !selectedText) return '';
  const canvasHasNode = course.concepts.some(
    (concept) => concept.title === selectedText || concept.points.includes(selectedText)
  );
  if (canvasHasNode) return selectedText;
  const noteIndex = course.notes.findIndex(
    (note) => note.title === selectedText || note.points.includes(selectedText)
  );
  return course.concepts[noteIndex]?.title || course.concepts[0]?.title || selectedText;
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
  responseCitations,
  responseCitationHints,
  responseConfidence,
  responseGroundingMode,
  responseMetrics,
  bridgeLine,
  handleTextSelection,
  openMenuForText,
  sendAIQuery,
  clearAnswerPanel,
} = useSelectionQueryMenu(() => courseContext.value);

function stateStorageKey(courseId: string) {
  return `zhixi:classroom-learning:${courseId}`;
}

function readLearningState(courseId: string): LocalLearningState {
  try {
    const raw = window.localStorage.getItem(stateStorageKey(courseId));
    if (!raw) return { ...emptyLearningState };
    const parsed = JSON.parse(raw) as Partial<LocalLearningState>;
    return {
      ...emptyLearningState,
      ...parsed,
      completedLessonIds: Array.isArray(parsed.completedLessonIds)
        ? parsed.completedLessonIds.filter(Boolean)
        : [],
    };
  } catch {
    return { ...emptyLearningState };
  }
}

function persistLearningState(patch: Partial<LocalLearningState> = {}) {
  const course = currentCourse.value;
  if (!course) return;
  const next: LocalLearningState = {
    ...localLearningState.value,
    lessonId: currentLessonId.value,
    isFavorite: isFavorite.value,
    notesOrganized: notesOrganized.value,
    selectedMindNodeText: selectedMindNodeText.value,
    lastActiveAt: new Date().toISOString(),
    ...patch,
  };
  next.completedLessonIds = Array.from(new Set(next.completedLessonIds)).filter(Boolean);
  localLearningState.value = next;
  try {
    window.localStorage.setItem(stateStorageKey(course.id), JSON.stringify(next));
    window.dispatchEvent(
      new CustomEvent('zhixi-classroom-learning-updated', {
        detail: { courseId: course.id, state: next },
      })
    );
  } catch {
    // localStorage may be unavailable in restricted browser modes; the in-memory state still updates.
  }
}

function recordLearningAction(
  kind: 'navigate' | 'favorite' | 'organize' | 'download' | 'generate' | 'complete' | 'node',
  patch: Partial<LocalLearningState> = {}
) {
  persistLearningState({
    actionCount: localLearningState.value.actionCount + 1,
    downloadCount:
      kind === 'download'
        ? localLearningState.value.downloadCount + 1
        : localLearningState.value.downloadCount,
    generatedCount:
      kind === 'generate'
        ? localLearningState.value.generatedCount + 1
        : localLearningState.value.generatedCount,
    ...patch,
  });
}

watch(
  currentCourse,
  (course) => {
    if (localVideoUrl.value) URL.revokeObjectURL(localVideoUrl.value);
    localVideoUrl.value = null;
    videoSrc.value = null;
    notesGenerating.value = false;
    const saved = course ? readLearningState(course.id) : { ...emptyLearningState };
    const lessonIds = new Set(
      course?.chapters.flatMap((chapter) => chapter.lessons.map((lesson) => lesson.id)) || []
    );
    localLearningState.value = saved;
    isFavorite.value = saved.isFavorite;
    notesOrganized.value = saved.notesOrganized;
    currentLessonId.value =
      saved.lessonId && lessonIds.has(saved.lessonId)
        ? saved.lessonId
        : course?.chapters[0]?.lessons[0]?.id || '';
    selectedMindNodeText.value = resolveIncomingMindNodeText(course) || saved.selectedMindNodeText || course?.shortTitle || '';
    openChapters.value = new Set(course?.chapters.map((chapter) => chapter.id) || []);
    clearAnswerPanel();
    if (route.query.open === 'mind' && course) {
      requestAnimationFrame(() => openArtifact('mind'));
    }
  },
  { immediate: true }
);

watch(
  () => [route.query.nodeId, route.query.nodeLabel, route.query.node, route.query.topic, route.query.open],
  () => {
    if (!currentCourse.value) return;
    const incomingText = resolveIncomingMindNodeText();
    if (incomingText) {
      selectedMindNodeText.value = incomingText;
      recordLearningAction('node', { selectedMindNodeText: incomingText });
    }
    if (route.query.open === 'mind') {
      requestAnimationFrame(() => openArtifact('mind'));
    }
  }
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
  recordLearningAction('navigate', { lessonId: lesson.id });
  Message.success(`已切换到 ${lesson.label}`);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function focusNotes() {
  notesPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function toggleFavorite() {
  isFavorite.value = !isFavorite.value;
  recordLearningAction('favorite', { isFavorite: isFavorite.value });
  Message.success(isFavorite.value ? '已收藏当前课节' : '已取消收藏');
}

function organizeNotes() {
  notesOrganized.value = true;
  recordLearningAction('organize', { notesOrganized: true });
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
  const noteLines = notesOrganized.value
    ? organizedNoteCards.value.flatMap((note) => [
        `### ${note.title}`,
        `- 定义边界：${note.definition}`,
        `- 课堂证据：${note.evidence}`,
        `- 易错提醒：${note.pitfall}`,
        `- 检查题：${note.check}`,
        '- 行动项：',
        ...note.activities.map((item) => `  - ${item}`),
      ])
    : currentCourse.value.notes.flatMap((note) => [
        `### ${note.title}`,
        ...note.points.map((point) => `- ${point}`),
      ]);
  return [
    `# ${currentCourse.value.title}课堂笔记`,
    `## ${currentLesson.value.label}`,
    '## 本节讲解',
    ...notesExplanation.value.map(
      (item) => `- **${item.label}：${item.value}**。${item.desc}`
    ),
    notesOrganized.value ? '## AI 智能整理版' : '## 原始课堂笔记',
    ...noteLines,
  ].join('\n\n');
}

function exportNotes() {
  if (!currentCourse.value) return;
  downloadText(`${currentCourse.value.title}-课堂笔记.md`, notesMarkdown(), 'text/markdown;charset=utf-8');
  recordLearningAction('download');
  Message.success('课堂笔记已导出');
}

function notesWordHtml() {
  if (!currentCourse.value) return '';
  const escapeHtml = (value: string) =>
    value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  const sections = (notesOrganized.value ? organizedNoteCards.value : currentCourse.value.notes)
    .map((note) => {
      if (notesOrganized.value) {
        const organized = note as OrganizedNoteCard;
        return `
        <h2>${escapeHtml(organized.title)}</h2>
        <table>
          <tr><th>定义边界</th><td>${escapeHtml(organized.definition)}</td></tr>
          <tr><th>课堂证据</th><td>${escapeHtml(organized.evidence)}</td></tr>
          <tr><th>易错提醒</th><td>${escapeHtml(organized.pitfall)}</td></tr>
          <tr><th>检查题</th><td>${escapeHtml(organized.check)}</td></tr>
        </table>
        <p><strong>行动项</strong></p>
        <ul>${organized.activities.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
      }
      return `
        <h2>${escapeHtml(note.title)}</h2>
        <p>${escapeHtml(note.points.join('、'))}共同构成该主题的课堂理解框架。</p>
        <ul>${note.points
          .map(
            (point) =>
              `<li><strong>${escapeHtml(point)}</strong>：建议结合课节案例复述定义、条件和应用边界。</li>`
          )
          .join('')}</ul>`;
    })
    .join('');
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(currentCourse.value.title)}课堂笔记</title>
  <style>
    body { font-family: "Microsoft YaHei", Arial, sans-serif; color: #17213a; line-height: 1.75; }
    h1 { font-size: 24px; }
    h2 { margin-top: 22px; font-size: 18px; color: #334155; }
    .meta { color: #64748b; }
    .brief { padding: 12px 16px; border: 1px solid #dbe4f0; background: #f8fafc; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0 12px; }
    th, td { border: 1px solid #dbe4f0; padding: 8px 10px; vertical-align: top; }
    th { width: 88px; background: #f3f6fb; color: #475569; text-align: left; }
  </style>
</head>
<body>
  <h1>${escapeHtml(currentCourse.value.title)}课堂笔记</h1>
  <p class="meta">${escapeHtml(currentLesson.value.label)} · ${escapeHtml(currentLesson.value.title)}</p>
  <div class="brief">${notesExplanation.value
    .map(
      (item) =>
        `<p><strong>${escapeHtml(item.label)}：${escapeHtml(item.value)}</strong><br />${escapeHtml(item.desc)}</p>`
    )
    .join('')}</div>
  ${sections}
</body>
</html>`;
}

function exportNotesDoc() {
  if (!currentCourse.value) return;
  downloadText(
    `${currentCourse.value.title}-课堂笔记.doc`,
    notesWordHtml(),
    'application/msword;charset=utf-8'
  );
  recordLearningAction('download');
  Message.success('Word 版课堂笔记已下载');
}

async function downloadGeneratedArtifact(artifact: GeneratedResourceArtifact) {
  const token = getToken();
  const response = await axios.get(artifact.download_url, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  const blobUrl = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = artifact.file_name;
  link.click();
  URL.revokeObjectURL(blobUrl);
}

async function generateNotesPdfArtifact() {
  if (!currentCourse.value || notesGenerating.value) return;
  notesGenerating.value = true;
  try {
    const response = await generateDownloadableResourcePackage({
      course_id: currentCourse.value.id,
      subject: currentCourse.value.title,
      topic: currentLesson.value.title || currentCourse.value.notes[0]?.title || '课堂笔记',
      learning_goal: `基于${currentCourse.value.title}课堂笔记生成可下载讲义 PDF，并保留关键概念、案例和自测题。`,
      difficulty: 'standard',
      target_minutes: 45,
      resource_types: ['lecture_markdown', 'lecture_pdf', 'practice_pdf', 'mind_map'],
    });
    const pdf = response.artifacts.find(
      (item: GeneratedResourceArtifact) => item.kind === 'lecture_pdf'
    );
    if (!pdf) {
      Message.warning('资源已生成，但未返回 PDF 文件');
      return;
    }
    await downloadGeneratedArtifact(pdf);
    recordLearningAction('generate');
    Message.success('PDF 讲义已生成，正在下载');
  } catch (error) {
    Message.error('PDF 生成失败，请检查后端资源生成服务');
  } finally {
    notesGenerating.value = false;
  }
}

function downloadCurrentLesson() {
  if (!currentCourse.value) return;
  downloadText(
    `${currentLesson.value.id}-${currentLesson.value.title}.md`,
    notesMarkdown(),
    'text/markdown;charset=utf-8'
  );
  recordLearningAction('download');
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
  recordLearningAction('download');
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

function generateFromNotes() {
  if (!currentCourse.value) return;
  recordLearningAction('generate');
  router.push({
    name: 'StudentCourseResourceGenerator',
    params: { courseId: currentCourse.value.id },
    query: incomingNodeContext({
      subject: currentCourse.value.title,
      goal: `基于${currentCourse.value.title}的课堂笔记和「${selectedMindNodeText.value || currentLesson.value.title}」节点生成讲义、知识卡和自测题。`,
      source: 'classroom-notes',
    }),
  });
}

function askMindMapTutor() {
  if (!currentCourse.value) return;
  recordLearningAction('generate');
  router.push(
    courseWorkspaceLocation(currentCourse.value.id, 'agent', incomingNodeContext({
      task: 'graph',
      source: 'classroom-mind-map',
      forceAgent: 'tutor_agent',
      prompt: [
        `当前课程：${currentCourse.value.title}`,
        `当前课节：${currentLesson.value.label} ${currentLesson.value.title}`,
        `当前课堂节点：${selectedMindNodeText.value || currentLesson.value.title}`,
        `思维导图节点：${currentCourse.value.concepts
          .map((item) => `${item.title}（${item.points.join('、')}）`)
          .join('；')}`,
        '请按“核心概念-前后置关系-易错提醒-练习建议”的结构解读这张课堂思维导图。',
      ].join('\n'),
    }))
  );
}

function normalizeMindNodeProfile(concept: ClassroomConcept, title: string, isPoint: boolean) {
  const primary = concept.points[0] || title;
  const pointIndex = Math.max(concept.points.findIndex((point) => point === title), 0);
  return {
    kind: isPoint ? '知识点节点' : '主题节点',
    title,
    detail:
      isPoint && concept.detail
        ? `${title} 属于「${concept.title}」。${concept.detail}`
        : concept.detail || `${title} 需要同时掌握定义、边界、证据和应用任务。`,
    outcomes: concept.outcomes || [`能解释 ${title} 的定义、条件和应用边界。`],
    misconceptions: concept.misconceptions || [`把 ${primary} 当成孤立概念，忽略与相邻知识的关系。`],
    checks: concept.checks || [`我能否用课堂案例解释 ${title}？`],
    resources: concept.resources || [`${title} 课堂讲义`, `${primary} 例题卡片`],
    activities: concept.activities || [`围绕 ${title} 完成概念复述、证据定位和错因订正。`],
    mastery: Math.max(48, Math.min(96, 68 + concept.points.length * 4 + pointIndex * 3)),
  };
}

function selectMindText(text: string) {
  selectedMindNodeText.value = text;
  recordLearningAction('node', { selectedMindNodeText: text });
}

function openMindCheckPrompt(text: string, event: MouseEvent) {
  const element = event.currentTarget as HTMLElement | null;
  if (!element) return;
  openMenuForText(text, element.getBoundingClientRect(), courseContext.value);
}

function mindNodePackMarkdown() {
  const course = currentCourse.value;
  const profile = mindNodeProfile.value;
  if (!course || !profile) return '';
  return [
    `# ${course.title} - ${profile.title}节点学习单`,
    '',
    `- 当前课节：${currentLesson.value.label} ${currentLesson.value.title}`,
    `- 节点类型：${profile.kind}`,
    `- 掌握度：${profile.mastery}%`,
    '',
    '## 节点解释',
    profile.detail,
    '',
    '## 学习产出',
    ...profile.outcomes.map((item) => `- ${item}`),
    '',
    '## 证据资源',
    ...profile.resources.map((item) => `- ${item}`),
    '',
    '## 相邻知识',
    ...(mindNodeNeighbors.value.length
      ? mindNodeNeighbors.value.map((item) => `- ${item.relation}：${item.title}`)
      : ['- 暂无相邻节点，建议从课程总览进入下一主题。']),
    '',
    '## 常见误区',
    ...profile.misconceptions.map((item) => `- ${item}`),
    '',
    '## 检查题',
    ...profile.checks.map((item, index) => `${index + 1}. ${item}`),
    '',
    '## 课堂行动',
    ...profile.activities.map((item) => `- ${item}`),
    '',
    '## 完成标准',
    '- 能用自己的话复述节点定义、适用条件和边界。',
    '- 能指出至少 2 条课堂证据或资源出处。',
    '- 能完成检查题并写出错因订正。',
  ].join('\n');
}

function safeFilePart(value: string) {
  return value.replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, '').slice(0, 48) || '节点';
}

function downloadMindNodePack() {
  const course = currentCourse.value;
  const profile = mindNodeProfile.value;
  if (!course || !profile) return;
  downloadText(
    `${safeFilePart(course.title)}-${safeFilePart(profile.title)}-节点学习单.md`,
    mindNodePackMarkdown(),
    'text/markdown;charset=utf-8'
  );
  recordLearningAction('download');
  Message.success('节点学习单已生成');
}

function completeCurrentLesson() {
  if (!currentLesson.value.id) return;
  const wasCompleted = currentLessonCompleted.value;
  const nextCompleted = Array.from(
    new Set([...localLearningState.value.completedLessonIds, currentLesson.value.id])
  );
  recordLearningAction('complete', {
    completedLessonIds: nextCompleted,
    lessonId: currentLesson.value.id,
  });
  Message.success(wasCompleted ? '本节学习状态已保存' : '已标记完成本节');
}

function changeZoom(delta: number) {
  artifactZoom.value = Math.min(
    1.6,
    Math.max(0.7, Number((artifactZoom.value + delta).toFixed(1)))
  );
}

function exportCanvas(type: 'mind') {
  if (!currentCourse.value) return;
  if (type === 'mind') {
    mindCanvas.value?.exportSvg(`${currentCourse.value.title}-思维导图.svg`);
  }
  recordLearningAction('download');
  Message.success('思维导图已导出为 SVG');
}

function exportModalCanvas() {
  if (!currentCourse.value) return;
  modalCanvas.value?.exportSvg(`${currentCourse.value.title}-思维导图.svg`);
  recordLearningAction('download');
  Message.success('思维导图已导出为 SVG');
}

function handleVisualNodePrompt(payload: { text: string; rect: DOMRect }) {
  selectedMindNodeText.value = payload.text;
  recordLearningAction('node', { selectedMindNodeText: payload.text });
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

.learning-state-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;

  article {
    min-width: 0;
    padding: 13px 14px;
    border: 1px solid #e4eaf4;
    border-radius: 12px;
    background:
      linear-gradient(135deg, rgba(248, 251, 255, .96), rgba(255, 255, 255, .98)),
      #fff;
    box-shadow: 0 3px 14px rgba(34, 48, 88, .04);
  }

  span,
  strong,
  p {
    display: block;
    min-width: 0;
  }

  span {
    color: #8a95a8;
    font-size: 10px;
    font-weight: 800;
  }

  strong {
    margin-top: 5px;
    overflow: hidden;
    color: #253047;
    font-size: 15px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  p {
    margin: 5px 0 0;
    color: #748095;
    font-size: 10px;
    line-height: 1.55;
  }
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
.media-frame {
  display: block;
  width: 100%;
  height: 100%;
}

.video-element {
  object-fit: contain;
  background: #080f1d;
}

.media-frame {
  position: relative;
  overflow: hidden;

  > img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: saturate(.88) contrast(1.04);
  }
}

.media-frame__shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(5, 12, 27, .12), rgba(5, 12, 27, .58)),
    radial-gradient(circle at center, transparent 12%, rgba(5, 12, 27, .2));
}

.media-frame__content {
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

.media-play {
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
  flex-wrap: wrap;
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

    &:disabled {
      cursor: wait;
      opacity: .62;
    }
  }
}

.course-selection-root {
  user-select: text;

  ::selection {
    color: #17213a;
    background: rgba(83, 103, 248, .22);
  }
}

.notes-brief {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 14px;
  padding-bottom: 0;

  article {
    min-height: 108px;
    padding: 13px;
    border: 1px solid #dde5f1;
    border-radius: 10px;
    background: #f8fbff;
  }

  span,
  p {
    margin: 0;
    color: #7a8799;
    font-size: 10px;
  }

  strong {
    display: block;
    margin: 5px 0 6px;
    color: #2b3850;
    font-size: 13px;
  }

  p {
    line-height: 1.7;
  }
}

.notes-organized-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 14px 14px 0;
  padding: 12px 14px;
  border: 1px solid #cad6ff;
  border-radius: 10px;
  background:
    linear-gradient(135deg, rgba(240, 244, 255, .98), rgba(248, 251, 255, .98)),
    #f7f9ff;

  span,
  strong {
    display: block;
  }

  span {
    color: #6675dc;
    font-size: 10px;
    font-weight: 800;
  }

  strong {
    margin-top: 3px;
    color: #24304a;
    font-size: 13px;
  }

  button {
    flex: 0 0 auto;
    padding: 7px 10px;
    border: 0;
    border-radius: 7px;
    color: #fff;
    background: #5367f8;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }
}

.notes-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 14px;

  article {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 10px;
    min-height: 174px;
    padding: 15px;
    border: 1px solid #e1e7f1;
    border-radius: 10px;
    background: linear-gradient(145deg, #fff, #fafcff);
  }

  .note-card--organized {
    border-color: #cfd8ff;
    background:
      linear-gradient(145deg, rgba(255, 255, 255, .98), rgba(247, 250, 255, .98)),
      #fff;
    box-shadow: 0 8px 22px rgba(57, 78, 156, .08);
  }

  article > span {
    display: grid;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    color: #5367f8;
    background: #eef2ff;
    font-size: 10px;
    font-weight: 700;
    place-items: center;
  }

  h3 {
    margin: 0 0 7px;
    color: #344057;
    font-size: 14px;
  }

  p {
    margin: 0 0 9px;
    color: #748095;
    font-size: 11px;
    line-height: 1.65;
  }

  .note-evidence-board {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin: 10px 0;

    section {
      min-width: 0;
      padding: 9px 10px;
      border: 1px solid #dfe6f6;
      border-radius: 8px;
      background: #fff;
    }

    small {
      color: #6979d7;
      font-size: 9px;
      font-weight: 800;
    }

    strong {
      margin-top: 5px;
      color: #3e4a62;
      font-size: 10px;
      line-height: 1.65;
    }
  }

  .note-card--organized .note-action-strip span {
    border-left-color: #1f9d78;
    background: #f1fbf7;
  }

  ul {
    margin: 0;
    padding-left: 16px;
    color: #707c91;
    font-size: 11px;
    line-height: 1.85;
  }

  strong,
  small {
    display: block;
  }

  small {
    margin-top: 1px;
    color: #8d98aa;
    font-size: 10px;
    line-height: 1.45;
  }

  li::marker {
    color: #6678f4;
  }

  .note-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;

    .note-chip {
      padding: 4px 8px;
      border: 1px solid transparent;
      border-radius: 999px;
      color: #5367f8;
      background: #eef2ff;
      font-size: 10px;
      font-style: normal;
      font-weight: 650;
      cursor: pointer;

      &:hover,
      &.active {
        border-color: #bfc8ff;
        color: #fff;
        background: #5367f8;
      }
    }
  }

  .note-columns {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 8px;

    section {
      padding: 9px 10px;
      border: 1px solid #e8eef7;
      border-radius: 9px;
      background: #fff;
    }

    strong {
      margin: 0 0 5px;
      color: #334155;
      font-size: 11px;
    }

    ul {
      padding-left: 14px;
      font-size: 10px;
      line-height: 1.7;
    }
  }

  .note-action-strip {
    display: grid;
    gap: 6px;
    margin-top: 10px;

    span {
      padding: 7px 9px;
      border-left: 3px solid #5367f8;
      border-radius: 8px;
      color: #5c6980;
      background: #f7f9ff;
      font-size: 10px;
      line-height: 1.55;
    }
  }
}

.mindmap-panel {
  overflow: hidden;
}

.concept-preview {
  height: 310px;
}

.mindmap-intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 0 14px 12px;
  padding: 13px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fbff;

  strong {
    color: #28364e;
    font-size: 14px;
    white-space: nowrap;
  }

  p {
    margin: 0;
    color: #6f7d91;
    font-size: 11px;
    line-height: 1.7;
  }
}

.mindmap-stats {
  display: flex;
  flex-shrink: 0;
  gap: 8px;

  span {
    display: grid;
    min-width: 58px;
    padding: 7px 9px;
    border: 1px solid #e0e7f2;
    border-radius: 9px;
    color: #7b8798;
    background: #fff;
    font-size: 10px;
    line-height: 1.25;
    text-align: center;
  }

  b {
    color: #5367f8;
    font-size: 15px;
  }
}

.concept-preview--large {
  height: 500px;
  margin: 0;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fbfcff;
}

.mindmap-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
  margin: 0 14px 14px;
}

.mind-node-card {
  min-width: 0;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background:
    linear-gradient(180deg, #fff, #f8fbff),
    radial-gradient(circle at 100% 0%, rgba(83, 103, 248, .12), transparent 34%);

  > span {
    display: inline-flex;
    margin-bottom: 8px;
    padding: 5px 9px;
    border-radius: 999px;
    color: #5367f8;
    background: #eef2ff;
    font-size: 10px;
    font-weight: 800;
  }

  h3 {
    margin: 0;
    color: #263149;
    font-size: 18px;
    line-height: 1.28;
  }

  > p {
    margin: 8px 0 12px;
    color: #6f7d91;
    font-size: 11px;
    line-height: 1.72;
  }
}

.mind-node-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
  margin: 0 0 10px;

  div {
    padding: 9px 8px;
    border: 1px solid #e5ebf5;
    border-radius: 10px;
    background: #fff;
  }

  strong,
  small {
    display: block;
  }

  strong {
    color: #5367f8;
    font-size: 16px;
  }

  small {
    margin-top: 2px;
    color: #8a95a8;
    font-size: 10px;
  }
}

.mind-node-section {
  display: grid;
  gap: 7px;
  padding: 11px 0;
  border-top: 1px solid #edf1f7;

  strong {
    color: #334155;
    font-size: 12px;
  }

  em,
  button {
    position: relative;
    padding: 7px 9px 7px 20px;
    border: 1px solid #e8eef7;
    border-radius: 9px;
    color: #5f6b80;
    background: #fff;
    font-size: 10px;
    font-style: normal;
    line-height: 1.5;
    text-align: left;
  }

  em::before,
  button::before {
    position: absolute;
    top: 13px;
    left: 9px;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #5367f8;
    content: '';
  }

  button {
    cursor: pointer;

    &:hover {
      border-color: #c8d0ff;
      color: #4458d7;
      background: #f7f9ff;
    }
  }
}

.mind-node-section.compact {
  button {
    width: 100%;
  }
}

.mind-node-section.resource-list,
.mind-node-section.relation-list {
  button {
    width: 100%;
    cursor: pointer;

    span {
      display: inline-flex;
      margin-right: 6px;
      padding: 2px 5px;
      border-radius: 999px;
      color: #5367f8;
      background: #eef2ff;
      font-size: 9px;
      font-weight: 800;
    }
  }
}

.mind-node-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #edf1f7;

  button {
    min-height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    border: 1px solid #dfe6f1;
    border-radius: 9px;
    color: #536079;
    background: #fff;
    font-size: 11px;
    font-weight: 750;
    cursor: pointer;

    &:first-child {
      border-color: transparent;
      color: #fff;
      background: #5367f8;
    }

    &:last-child {
      border-color: #cbd5ff;
      color: #4e5ed8;
      background: #f4f6ff;
    }
  }
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

.canvas-modal__body--mind {
  height: 72vh;
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

  .learning-state-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .learning-layout {
    grid-template-columns: 1fr;
  }

  .mindmap-workbench {
    grid-template-columns: 1fr;
  }

  .mind-node-card {
    order: -1;
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
  .notes-brief,
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
    grid-template-columns: 1fr;
  }

  .notes-organized-banner {
    align-items: stretch;
    flex-direction: column;

    button {
      width: 100%;
    }
  }

  .notes-grid .note-evidence-board {
    grid-template-columns: 1fr;
  }

  .learning-state-strip {
    grid-template-columns: 1fr;
  }

  .mindmap-intro {
    align-items: flex-start;
    flex-direction: column;
  }

  .overview-progress {
    grid-template-columns: auto 1fr auto;

    small {
      grid-column: 2 / -1;
    }
  }
}
</style>
