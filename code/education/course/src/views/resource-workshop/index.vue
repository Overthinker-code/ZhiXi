<template>
  <div
    class="resource-workshop-page"
    :class="{ 'resource-workshop-page--course': isCourseScoped }"
  >
    <Breadcrumb :items="['menu.resourceWorkshop', 'menu.resourceGeneration']" />

    <header class="workshop-heading">
      <div class="workshop-heading__copy">
        <span class="workshop-kicker">学习资源工坊</span>
        <h1>{{ currentPageTitle }}</h1>
        <p>{{ currentPageDescription }}</p>
      </div>

      <div
        v-if="isUnifiedWorkbench"
        class="workbench-switch"
        role="tablist"
        aria-label="资源工坊功能"
      >
        <button
          v-for="item in modeOptions"
          :key="item.value"
          type="button"
          class="workbench-switch__item"
          :class="{
            'workbench-switch__item--active': activeMode === item.value,
          }"
          role="tab"
          :aria-selected="activeMode === item.value"
          @click="activeMode = item.value"
        >
          <span aria-hidden="true">{{ item.badge }}</span>
          {{ item.label }}
        </button>
      </div>
    </header>

    <section class="workbench-grid">
      <aside class="task-composer" aria-label="任务设置">
        <div class="composer-heading">
          <span class="composer-heading__icon" aria-hidden="true">
            <IconRobot />
          </span>
          <div>
            <h2>{{
              isPackageMode
                ? '生成学习资源'
                : isExerciseMode
                ? '提交练习批改'
                : '上传题目图片'
            }}</h2>
            <p>{{
              isPackageMode
                ? '填写核心需求，其余内容由系统自动组织。'
                : isExerciseMode
                ? '根据课程要求分析答案并给出后续建议。'
                : '识别题目后生成步骤化讲解与图解。'
            }}</p>
          </div>
        </div>

        <div v-if="incomingSeedSummary" class="context-note">
          <IconBulb aria-hidden="true" />
          <div>
            <span>已带入学习上下文</span>
            <strong>{{ incomingSeedSummary }}</strong>
          </div>
        </div>

        <div v-else-if="report?.current_goal" class="context-note">
          <IconBulb aria-hidden="true" />
          <div>
            <span>本次将参考你的学习目标</span>
            <strong>{{ report.current_goal }}</strong>
          </div>
          <button
            type="button"
            :aria-label="loadingReport ? '正在刷新学习建议' : '刷新学习建议'"
            :disabled="loadingReport"
            @click="loadProfile(true)"
          >
            <IconRefresh aria-hidden="true" />
          </button>
        </div>

        <details
          v-if="activeCourse && courseSeedActions.length"
          class="course-suggestions"
        >
          <summary>
            <span>课程建议</span>
            <strong>{{ activeCourse.shortTitle }}</strong>
            <IconDown aria-hidden="true" />
          </summary>
          <div class="course-suggestions__list">
            <button
              v-for="action in courseSeedActions"
              :key="action.topic"
              type="button"
              @click="applyCourseSeed(action.topic, action.goal)"
            >
              <strong>{{ action.topic }}</strong>
              <small>{{ action.goal }}</small>
            </button>
          </div>
        </details>

        <a-form
          v-if="isPackageMode"
          :model="form"
          layout="vertical"
          class="composer-form"
        >
          <a-form-item field="subject" label="课程">
            <a-input v-model="form.subject" placeholder="例如：数据库系统" />
          </a-form-item>
          <a-form-item field="topic" label="主题 / 知识点">
            <a-input v-model="form.topic" placeholder="例如：事务与并发控制" />
          </a-form-item>
          <a-form-item field="goal" label="学习目标">
            <a-textarea
              v-model="form.goal"
              :auto-size="{ minRows: 3, maxRows: 4 }"
              placeholder="希望理解什么、解决什么问题，或完成什么任务"
            />
          </a-form-item>
          <div class="form-two">
            <a-form-item field="difficulty" label="难度">
              <select
                v-model="form.difficulty"
                class="difficulty-select"
                aria-label="目标难度"
              >
                <option value="auto">自动匹配</option>
                <option value="foundation">基础巩固</option>
                <option value="standard">标准提升</option>
                <option value="challenge">挑战拓展</option>
              </select>
            </a-form-item>
            <a-form-item field="minutes" label="预计时长（分钟）">
              <a-input-number
                v-model="form.minutes"
                :min="10"
                :max="120"
                :hide-button="true"
                aria-label="预计学习时长（分钟）"
                :input-attrs="{ 'aria-label': '预计学习时长（分钟）' }"
              />
            </a-form-item>
          </div>
          <fieldset class="format-selector">
            <legend>讲义与练习格式</legend>
            <label
              v-for="option in documentFormatOptions"
              :key="option.value"
              :class="{
                'format-selector__option--active':
                  form.documentFormat === option.value,
              }"
            >
              <input
                v-model="form.documentFormat"
                type="radio"
                name="resource-document-format"
                :value="option.value"
                :aria-label="`${option.label}，${option.description}`"
              />
              <span class="format-selector__icon" aria-hidden="true">
                <IconFilePdf v-if="option.value === 'pdf'" />
                <IconDriveFile v-else />
              </span>
              <span>
                <strong>{{ option.label }}</strong>
                <small>{{ option.description }}</small>
              </span>
            </label>
          </fieldset>
          <a-button
            class="primary-action"
            type="primary"
            long
            :loading="loadingPackage"
            @click="handleGeneratePackage"
          >
            <IconRobot aria-hidden="true" />
            {{ loadingPackage ? '正在生成' : '生成学习资源' }}
          </a-button>
          <a-button
            v-if="loadingPackage"
            class="secondary-action"
            long
            :disabled="cancellationRequested"
            @click="handleCancelPackage"
          >
            {{ cancellationRequested ? '正在安全停止…' : '停止本次生成' }}
          </a-button>
          <a-button
            v-else-if="conflictingRunId || resumableRunId"
            class="secondary-action"
            long
            @click="handleResumePackage"
          >
            {{ conflictingRunId ? '查看正在生成的任务' : '继续上次生成' }}
          </a-button>
        </a-form>

        <a-form
          v-if="isExerciseMode"
          :model="gradeForm"
          layout="vertical"
          class="composer-form"
        >
          <a-form-item label="课程">
            <a-input
              v-model="gradeForm.subject"
              placeholder="例如：数据库系统"
            />
          </a-form-item>
          <a-form-item label="知识点">
            <a-input
              v-model="gradeForm.topic"
              placeholder="例如：事务隔离级别"
            />
          </a-form-item>
          <a-form-item label="题目">
            <a-textarea
              v-model="gradeForm.question"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </a-form-item>
          <a-form-item label="你的作答">
            <a-textarea
              v-model="gradeForm.student_answer"
              :auto-size="{ minRows: 4, maxRows: 6 }"
            />
          </a-form-item>
          <a-form-item label="参考答案（可选）">
            <a-textarea
              v-model="gradeForm.reference_answer"
              :auto-size="{ minRows: 2, maxRows: 4 }"
            />
          </a-form-item>
          <a-button
            class="primary-action"
            type="primary"
            long
            :loading="loadingGrade"
            @click="handleGrade"
          >
            提交批改
          </a-button>
        </a-form>

        <a-form
          v-if="isImageMode"
          :model="imageForm"
          layout="vertical"
          class="composer-form"
        >
          <a-form-item label="课程">
            <a-input
              v-model="imageForm.subject"
              placeholder="例如：数据库系统"
            />
          </a-form-item>
          <a-form-item label="补充题干（可选）">
            <a-textarea
              v-model="imageForm.question_text"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              placeholder="补充图片中不清晰的条件或你的疑问"
            />
          </a-form-item>
          <label class="upload-tile">
            <input type="file" accept="image/*" @change="handleImageFile" />
            <IconFileImage aria-hidden="true" />
            <strong>{{ imageName || '选择题目图片' }}</strong>
            <span>支持课堂拍照、练习截图和试题图片</span>
          </label>
          <a-button
            class="primary-action"
            type="primary"
            long
            :disabled="!imageForm.image_base64"
            :loading="loadingImage"
            @click="handleImageAnalyze"
          >
            开始识别与讲解
          </a-button>
        </a-form>
      </aside>

      <main class="execution-canvas" role="tabpanel">
        <template v-if="isPackageMode">
          <section
            class="progress-panel"
            aria-labelledby="generation-progress-title"
          >
            <div class="panel-heading">
              <div>
                <span>当前任务</span>
                <h2 id="generation-progress-title">生成进度</h2>
              </div>
              <span
                class="status-chip"
                :class="`status-chip--${generationStatusTone}`"
              >
                {{ generationStatusLabel }}
              </span>
            </div>
            <AgentStagePanel :nodes="agentStageNodes" />
          </section>

          <section
            class="package-panel"
            aria-labelledby="current-package-title"
          >
            <div class="package-panel__heading">
              <div>
                <span>本次资源包</span>
                <h2 id="current-package-title">
                  {{
                    packageResult
                      ? `${packageResult.topic} 学习资源包`
                      : '等待生成学习资源'
                  }}
                </h2>
                <p v-if="packageResult">{{ artifactCompletionMessage }}</p>
                <p v-else>生成结果会按文件整理，正文内容仅在需要时预览。</p>
              </div>
              <div v-if="packageResult" class="package-heading-actions">
                <button type="button" @click="copyPackageSummary"
                  >复制摘要</button
                >
                <button
                  v-if="downloadableArtifacts.length"
                  type="button"
                  class="primary"
                  @click="downloadAllArtifacts"
                >
                  <IconDownload aria-hidden="true" />
                  下载全部
                </button>
              </div>
            </div>

            <template v-if="packageResult && downloadablePackage">
              <div class="artifact-grid">
                <article
                  v-for="artifact in visibleDownloadableArtifacts"
                  :key="artifact.file_name"
                  class="artifact-card"
                >
                  <span
                    class="artifact-card__icon"
                    :class="`artifact-card__icon--${artifactFileTone(
                      artifact.file_name
                    )}`"
                    aria-hidden="true"
                  >
                    <IconFilePdf
                      v-if="artifactFileTone(artifact.file_name) === 'pdf'"
                    />
                    <IconDriveFile
                      v-else-if="
                        artifactFileTone(artifact.file_name) === 'docx'
                      "
                    />
                    <IconFile v-else />
                  </span>
                  <div class="artifact-card__copy">
                    <span>{{ artifactKindLabel(artifact.kind) }}</span>
                    <strong>{{ artifact.title }}</strong>
                    <small
                      >{{ artifactFileFormat(artifact.file_name) }} ·
                      {{ formatFileSize(artifact.file_size) }}</small
                    >
                  </div>
                  <div class="artifact-card__actions">
                    <button
                      type="button"
                      :aria-label="`预览 ${artifact.title}`"
                      @click="openArtifactPreview(artifact, $event)"
                    >
                      <IconEye aria-hidden="true" />
                      <span>预览</span>
                    </button>
                    <button
                      type="button"
                      :aria-label="`下载 ${artifact.title}`"
                      @click="downloadArtifact(artifact)"
                    >
                      <IconDownload aria-hidden="true" />
                      <span>下载</span>
                    </button>
                  </div>
                </article>
              </div>

              <button
                v-if="downloadableArtifacts.length > artifactPreviewLimit"
                type="button"
                class="show-all-artifacts"
                :aria-expanded="showAllArtifacts"
                @click="showAllArtifacts = !showAllArtifacts"
              >
                {{
                  showAllArtifacts
                    ? '收起文件'
                    : `查看全部 ${downloadableArtifacts.length} 个文件`
                }}
                <IconDown aria-hidden="true" />
              </button>

              <details
                v-if="
                  downloadableQualityNotes.length ||
                  downloadableAgentTrace.length ||
                  packageResult.personalization_basis.length
                "
                class="evidence-disclosure"
              >
                <summary>
                  <span>
                    <IconCheckCircleFill aria-hidden="true" />
                    质量说明与生成依据
                  </span>
                  <small>按需查看内容检查、执行记录和个性化参考</small>
                  <IconDown aria-hidden="true" />
                </summary>
                <div class="evidence-disclosure__content">
                  <section v-if="downloadableQualityNotes.length">
                    <h3>内容检查</h3>
                    <ul>
                      <li
                        v-for="item in downloadableQualityNotes"
                        :key="item"
                        >{{ item }}</li
                      >
                    </ul>
                  </section>
                  <section v-if="downloadableAgentTrace.length">
                    <h3>生成记录</h3>
                    <ol>
                      <li v-for="item in downloadableAgentTrace" :key="item">{{
                        item
                      }}</li>
                    </ol>
                  </section>
                  <section v-if="packageResult.personalization_basis.length">
                    <h3>个性化参考</h3>
                    <ul>
                      <li
                        v-for="item in packageResult.personalization_basis"
                        :key="item"
                        >{{ item }}</li
                      >
                    </ul>
                  </section>
                </div>
              </details>

              <footer class="next-step-strip">
                <div>
                  <span>继续学习</span>
                  <strong>把资源用于练习、复核或课程图谱</strong>
                </div>
                <div class="next-step-strip__actions">
                  <button type="button" @click="openKnowledgeGraph">
                    关联知识点 <IconRight aria-hidden="true" />
                  </button>
                  <button type="button" @click="() => openAiReview()">
                    AI 复核 <IconRight aria-hidden="true" />
                  </button>
                  <button
                    v-if="checklistArtifact"
                    type="button"
                    @click="downloadArtifact(checklistArtifact)"
                  >
                    检查清单 <IconDownload aria-hidden="true" />
                  </button>
                </div>
              </footer>
            </template>

            <div v-else class="package-empty">
              <span class="package-empty__icon" aria-hidden="true">
                <IconDriveFile />
              </span>
              <h3>从一个明确的学习目标开始</h3>
              <p
                >系统会生成讲义、练习、思维导图、阅读材料和实操案例，并整理为可下载文件。</p
              >
              <div class="expected-files" aria-label="预计生成内容">
                <span v-for="item in resourcePreviewCards" :key="item.label">
                  <IconCheck aria-hidden="true" /> {{ item.label }}
                </span>
              </div>
            </div>
          </section>
        </template>

        <section v-if="isExerciseMode" class="package-panel mode-result-panel">
          <div class="package-panel__heading">
            <div>
              <span>批改结果</span>
              <h2>练习反馈与后续建议</h2>
              <p>结果只展示给学习者，掌握情况会用于后续推荐。</p>
            </div>
          </div>
          <div v-if="gradeResult" class="grade-result">
            <div class="result-stats">
              <article v-for="item in gradeStats" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>
            <div class="score-line">
              <strong>{{ gradeResult.score }}</strong>
              <span>分</span>
              <a-tag :color="gradeResult.is_correct ? 'green' : 'orange'">
                {{ gradeResult.is_correct ? '已掌握' : '继续巩固' }}
              </a-tag>
            </div>
            <div class="mastery-head">
              <span>掌握情况</span>
              <span>{{ Math.round(gradeResult.mastery_after * 100) }}%</span>
            </div>
            <a-progress
              aria-hidden="true"
              :percent="Math.round(gradeResult.mastery_after * 100)"
              :show-text="false"
            />
            <span
              class="zy-sr-only"
              role="progressbar"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="Math.round(gradeResult.mastery_after * 100)"
              :aria-label="`当前掌握度 ${Math.round(
                gradeResult.mastery_after * 100
              )}%`"
              >当前掌握度
              {{ Math.round(gradeResult.mastery_after * 100) }}%</span
            >
            <p>{{ gradeResult.feedback }}</p>
            <ul class="plain-list">
              <li v-for="item in gradeResult.follow_up" :key="item">{{
                item
              }}</li>
            </ul>
          </div>
          <div v-else class="package-empty package-empty--compact">
            <span class="package-empty__icon" aria-hidden="true"
              ><IconCheckSquare
            /></span>
            <h3>等待提交练习</h3>
            <p>提交后会展示得分、反馈和后续追练建议。</p>
          </div>
        </section>

        <section v-if="isImageMode" class="package-panel mode-result-panel">
          <div class="package-panel__heading">
            <div>
              <span>题目解析</span>
              <h2>识别文本与步骤化讲解</h2>
              <p>识别结果不清晰时，可返回左侧补充题干条件。</p>
            </div>
          </div>
          <div v-if="imageResult" class="image-result">
            <div class="result-meta">
              <a-tag>{{ imageResult.subject }}</a-tag>
              <a-tag color="arcoblue">{{ imageResult.problem_type }}</a-tag>
              <span>识别清晰度 {{ imageClarityLabel }}</span>
            </div>
            <div class="extracted-text">{{ imageResult.extracted_text }}</div>
            <div
              class="markdown-body answer-box"
              v-html="renderMarkdown(imageResult.answer_markdown)"
            />
            <div v-if="diagramNodes.length" class="diagram-flow">
              <span v-for="node in diagramNodes" :key="node">{{ node }}</span>
            </div>
            <ul class="plain-list">
              <li v-for="item in imageResult.solution_outline" :key="item">{{
                item
              }}</li>
            </ul>
          </div>
          <div v-else class="package-empty package-empty--compact">
            <span class="package-empty__icon" aria-hidden="true"
              ><IconFileImage
            /></span>
            <h3>等待上传题目图片</h3>
            <p>分析后会展示识别文本、图解节点和完整题解。</p>
          </div>
        </section>
      </main>
    </section>

    <teleport to="body">
      <section
        v-if="previewedArtifact"
        class="artifact-preview-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="artifact-preview-title"
        @keydown="handleArtifactPreviewKeydown"
      >
        <div
          class="artifact-preview-modal__backdrop"
          aria-hidden="true"
          @click="closeArtifactPreview"
        />
        <article
          ref="artifactPreviewPanel"
          class="artifact-preview-modal__panel"
          tabindex="-1"
        >
          <header>
            <span>{{ artifactKindLabel(previewedArtifact.kind) }}</span>
            <strong id="artifact-preview-title">{{
              previewedArtifact.title
            }}</strong>
            <small
              >内容摘要预览 · {{ artifactFileFormat(previewedArtifact.file_name) }} 文件 ·
              {{ formatFileSize(previewedArtifact.file_size) }}</small
            >
          </header>
          <div
            class="artifact-preview-modal__body"
            role="region"
            tabindex="0"
            :aria-label="`${previewedArtifact.title}内容摘要预览`"
            v-html="
              renderMarkdown(previewedArtifact.preview || '暂无可用内容摘要。')
            "
          />
          <footer>
            <button type="button" @click="closeArtifactPreview">关闭</button>
            <button type="button" @click="downloadArtifact(previewedArtifact)"
              >下载文件</button
            >
            <button
              type="button"
              class="primary"
              @click="openAiReview(previewedArtifact)"
            >
              让 AI 复核这个文件
            </button>
          </footer>
        </article>
      </section>
    </teleport>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import {
    IconBulb,
    IconCheck,
    IconCheckCircleFill,
    IconCheckSquare,
    IconDown,
    IconDownload,
    IconDriveFile,
    IconEye,
    IconFile,
    IconFileImage,
    IconFilePdf,
    IconRefresh,
    IconRight,
    IconRobot,
  } from '@arco-design/web-vue/es/icon';
  import axios from 'axios';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { fetchLearningReport, LearningReport } from '@/api/rag';
  import {
    analyzeImageProblem,
    gradeResourceExercise,
    ImageAnalyzeResponse,
  } from '@/api/resource-workshop';
  import {
    cancelResourceRun,
    fetchRecentGeneratedPackages,
    generateResourcePackageCompatible as generateDownloadableResourcePackage,
    resumeResourceRun,
    restoreGeneratedPackage,
    type GeneratedResourceArtifact,
    type ResourceGenerationResponse,
    type ResourceKind,
    type ResourceRunEvidence,
  } from '@/api/resource-generation';
  import { getToken } from '@/utils/auth';
  import { renderMarkdown } from '@/utils/markdown';
  import {
    buildResourcePackageViewModel,
    buildFriendlyGenerationTrace,
    buildProductionResourceTypes,
    type ResourceDifficulty,
    type ResourceDocumentFormat,
    type ResourceItem,
    type ResourcePackageViewModel,
  } from './resourcePackageViewModel';

  const route = useRoute();
  const router = useRouter();
  type WorkbenchMode = 'package' | 'exercise' | 'image';

  function resolveRouteMode(routeName: unknown): WorkbenchMode {
    const name = String(routeName || '');
    if (name === 'ResourceExerciseReview') return 'exercise';
    if (name === 'ResourceImageSolver') return 'image';
    return 'package';
  }

  const loadingReport = ref(false);
  const loadingPackage = ref(false);
  const loadingGrade = ref(false);
  const loadingImage = ref(false);

  const report = ref<LearningReport | null>(null);
  const packageResult = ref<ResourcePackageViewModel | null>(null);
  const downloadablePackage = ref<ResourceGenerationResponse | null>(null);
  const activeRunEvidence = ref<ResourceRunEvidence | null>(null);
  const generationController = ref<AbortController | null>(null);
  const resumableRunId = ref('');
  const conflictingRunId = ref('');
  const cancellationRequested = ref(false);
  const showAllArtifacts = ref(false);
  const previewedArtifact = ref<GeneratedResourceArtifact | null>(null);
  const artifactPreviewPanel = ref<HTMLElement | null>(null);
  const artifactPreviewTrigger = ref<HTMLElement | null>(null);
  const gradeResult = ref<Awaited<
    ReturnType<typeof gradeResourceExercise>
  > | null>(null);
  const imageResult = ref<ImageAnalyzeResponse | null>(null);
  const imageName = ref('');
  const activeMode = ref<WorkbenchMode>(resolveRouteMode(route.name));
  const activeCourse = computed(() =>
    getClassroomCourse(
      String(route.params.courseId || route.query.courseId || '').trim()
    )
  );

  const form = reactive<{
    subject: string;
    topic: string;
    goal: string;
    difficulty: ResourceDifficulty;
    minutes: number;
    documentFormat: ResourceDocumentFormat;
  }>({
    subject: '',
    topic: '',
    goal: '',
    difficulty: 'auto',
    minutes: 45,
    documentFormat: 'both',
  });
  const documentFormatOptions: Array<{
    value: ResourceDocumentFormat;
    label: string;
    description: string;
  }> = [
    { value: 'docx', label: 'Word', description: '便于继续编辑' },
    { value: 'pdf', label: 'PDF', description: '适合阅读与打印' },
    { value: 'both', label: 'Word + PDF', description: '同时生成两种格式' },
  ];

  const gradeForm = reactive({
    subject: '',
    topic: '',
    question: '',
    student_answer: '',
    reference_answer: '',
  });

  const imageForm = reactive({
    subject: '',
    question_text: '',
    image_base64: '',
  });
  const lastSeedSignature = ref('');

  function friendlyStageMessage(stage: ResourceRunEvidence['stages'][number]) {
    const running: Record<typeof stage.key, string> = {
      generation: '正在生成讲义、练习和配套学习资料',
      review: '正在检查结构、内容和输出格式',
      persistence: '正在保存生成文件',
      graph_link: '正在整理资源与课程知识点的关系',
      path_update: '正在整理后续学习建议',
      profile_update: '正在记录本次学习活动',
    };
    const completed: Record<typeof stage.key, string> = {
      generation: '学习内容已生成',
      review: '结构、内容和输出格式已检查',
      persistence: '生成文件已保存',
      graph_link: '课程知识点关系已整理',
      path_update: '后续学习建议已整理',
      profile_update: '本次学习活动已记录',
    };
    if (stage.status === 'running') return running[stage.key];
    if (stage.status === 'failed') return '本步骤暂未完成，可稍后重试';
    if (stage.status === 'unsupported') return '当前任务无需执行此步骤';
    if (
      stage.key === 'graph_link' &&
      /course_id|未.*课程|全局资源包/i.test(stage.message || '')
    ) {
      return '未选择课程，暂不关联课程图谱';
    }
    if (stage.status === 'completed') return completed[stage.key];
    return '等待处理';
  }

  const agentStageNodes = computed(() => {
    const evidence = activeRunEvidence.value || downloadablePackage.value?.run;
    if (evidence?.stages?.length) {
      const labels = {
        generation: '生成学习内容',
        review: '检查内容质量',
        persistence: '保存资源文件',
        graph_link: '关联课程图谱',
        path_update: '更新学习路径',
        profile_update: '记录学习活动',
      } as const;
      return evidence.stages.map((stage) => ({
        key: stage.key,
        label: labels[stage.key],
        sub: friendlyStageMessage(stage),
        message: friendlyStageMessage(stage),
        status:
          stage.status === 'completed' || stage.status === 'unsupported'
            ? ('done' as const)
            : stage.status === 'running'
            ? ('running' as const)
            : stage.status === 'failed'
            ? ('error' as const)
            : ('idle' as const),
      }));
    }
    return [
      {
        key: 'profile',
        label: '分析学习需求',
        status: 'idle' as const,
        sub: '点击生成启动',
      },
      { key: 'retrieval', label: '查找课程资料', status: 'idle' as const },
      { key: 'content', label: '生成学习内容', status: 'idle' as const },
      { key: 'safety', label: '检查内容质量', status: 'idle' as const },
      { key: 'assembler', label: '整理下载文件', status: 'idle' as const },
    ];
  });

  const mode = computed(() => String(route.name || 'ResourcePackageBuilder'));
  const isUnifiedWorkbench = computed(
    () => mode.value === 'CourseResourceGeneration'
  );
  const isCourseScoped = computed(
    () => mode.value === 'StudentCourseResourceGenerator'
  );
  const isPackageMode = computed(() => activeMode.value === 'package');
  const isExerciseMode = computed(() => activeMode.value === 'exercise');
  const isImageMode = computed(() => activeMode.value === 'image');
  const modeOptions: Array<{
    label: string;
    value: WorkbenchMode;
    description: string;
    badge: string;
  }> = [
    {
      label: '资源包生成',
      value: 'package',
      description: '生成讲解、练习、案例等完整资源包',
      badge: '包',
    },
    {
      label: '练习批改',
      value: 'exercise',
      description: '拍照或上传，智能批改与解析',
      badge: '评',
    },
    {
      label: '图像题解',
      value: 'image',
      description: '输入图片识别与结构化讲解',
      badge: '图',
    },
  ];
  const currentPageTitle = computed(() => {
    if (isExerciseMode.value) return '练习批改';
    if (isImageMode.value) return '图像题解';
    return isUnifiedWorkbench.value ? '学习资源工坊' : '课程资源生成';
  });
  const currentPageDescription = computed(() => {
    if (isExerciseMode.value) {
      return '围绕指定课程与知识点批改作答，给出反馈并更新后续学习建议。';
    }
    if (isImageMode.value) {
      return '上传题目图片并补充题干信息，识别题意后生成解题提示、步骤与图解。';
    }
    return '围绕当前课程和学习目标，生成可编辑、可阅读、可继续练习的学习资料。';
  });
  const weakPoints = computed(
    () => report.value?.weak_points?.slice(0, 6) || []
  );

  const packageResources = computed(() => {
    const result = packageResult.value;
    if (!result || !Array.isArray(result.resources)) return [];
    return result.resources;
  });
  const resourcePreviewCards = [
    { label: '讲解讲义', desc: '知识梳理与例题解析', icon: '文', tone: 'blue' },
    { label: '练习题', desc: '分层练习与巩固训练', icon: '题', tone: 'green' },
    {
      label: '阅读材料',
      desc: '拓展阅读与背景知识',
      icon: '读',
      tone: 'violet',
    },
    {
      label: '实操案例',
      desc: '实际应用与案例分析',
      icon: '案',
      tone: 'orange',
    },
    { label: '复习提纲', desc: '知识框架与复习重点', icon: '纲', tone: 'cyan' },
  ];
  const downloadableArtifacts = computed(() => {
    const pkg = downloadablePackage.value;
    if (!pkg || !Array.isArray(pkg.artifacts)) return [];
    return pkg.artifacts;
  });
  const artifactPreviewLimit = 6;
  const visibleDownloadableArtifacts = computed(() =>
    showAllArtifacts.value
      ? downloadableArtifacts.value
      : downloadableArtifacts.value.slice(0, artifactPreviewLimit)
  );
  const downloadableQualityNotes = computed(() => {
    const pkg = downloadablePackage.value;
    if (!pkg || !Array.isArray(pkg.quality_notes)) return [];
    if (!pkg.quality_notes.length) return [];
    const missingCourseSource = pkg.quality_notes.some((item) =>
      /未找到|通用知识|未关联课程/.test(item)
    );
    return [
      '已检查文件结构、内容完整性和下载格式。',
      missingCourseSource
        ? '本次未关联课程原文，内容按通用知识生成；使用前建议结合课件复核。'
        : '内容已结合当前课程资料整理。',
      '涉及外部资料时，请在学习或提交前再次确认来源。',
    ];
  });
  const downloadableAgentTrace = computed(() => {
    const pkg = downloadablePackage.value;
    if (!pkg || !Array.isArray(pkg.agent_trace)) return [];
    return buildFriendlyGenerationTrace(pkg.agent_trace);
  });
  const checklistArtifact = computed(
    () =>
      downloadableArtifacts.value.find(
        (item) => item.kind === 'quality_checklist'
      ) || null
  );
  const primaryReviewArtifact = computed(
    () =>
      checklistArtifact.value ||
      downloadableArtifacts.value.find(
        (item) => item.kind === 'lecture_markdown'
      ) ||
      downloadableArtifacts.value.find(
        (item) => item.kind === 'practice_markdown'
      ) ||
      downloadableArtifacts.value[0] ||
      null
  );
  const artifactReviewList = computed(() =>
    downloadableArtifacts.value
      .slice(0, 6)
      .map(
        (artifact, index) =>
          `${index + 1}. ${artifactKindLabel(artifact.kind)}：${
            artifact.title
          }（${artifact.file_name}，${formatFileSize(artifact.file_size)}）`
      )
      .join('\n')
  );
  const artifactPreviewSummary = computed(() =>
    downloadableArtifacts.value
      .slice(0, 4)
      .map((artifact) => `${artifact.title}：${artifact.preview || '暂无预览'}`)
      .join('\n')
  );
  const artifactCompletionMessage = computed(() => {
    const count = downloadableArtifacts.value.length;
    const status = downloadablePackage.value?.run?.status;
    if (status === 'completed') return `已生成并核验 ${count} 个可下载文件`;
    if (status === 'partial_success') {
      return `已生成 ${count} 个文件，部分后续处理尚未完成`;
    }
    return `已恢复 ${count} 个可下载文件`;
  });
  const generationStatusLabel = computed(() => {
    if (loadingPackage.value)
      return cancellationRequested.value ? '正在停止' : '生成中';
    const status =
      activeRunEvidence.value?.status || downloadablePackage.value?.run?.status;
    if (status === 'completed') return '已完成';
    if (status === 'partial_success') return '核心文件已完成';
    if (status === 'failed') return '需要重试';
    if (status === 'cancelled') return '已停止';
    return packageResult.value ? '已恢复' : '等待开始';
  });
  const generationStatusTone = computed(() => {
    if (loadingPackage.value) return 'running';
    const status =
      activeRunEvidence.value?.status || downloadablePackage.value?.run?.status;
    if (status === 'completed') return 'success';
    if (status === 'partial_success') return 'warning';
    if (status === 'failed') return 'danger';
    return 'neutral';
  });
  const artifactKindLabel = (kind: ResourceKind) => {
    const map: Record<ResourceKind, string> = {
      lecture_markdown: '讲义 Markdown',
      lecture_docx: '讲义 Word',
      lecture_pdf: '讲义 PDF',
      practice_markdown: '练习 Markdown',
      practice_docx: '练习 Word',
      practice_pdf: '练习 PDF',
      mind_map: '思维导图',
      reading_list: '阅读清单',
      case_project: '案例项目',
      video_script: '数字人脚本',
      quality_checklist: '内容检查清单',
    };
    return map[kind] || kind;
  };
  function artifactFileFormat(fileName: string) {
    const extension = fileName.split('.').pop()?.toLowerCase() || '';
    const labels: Record<string, string> = {
      docx: 'Word',
      pdf: 'PDF',
      md: 'Markdown',
      json: 'JSON',
      txt: '文本',
    };
    return labels[extension] || extension.toUpperCase() || '学习资料';
  }
  function artifactFileTone(fileName: string) {
    const extension = fileName.split('.').pop()?.toLowerCase() || '';
    if (extension === 'pdf') return 'pdf';
    if (extension === 'docx') return 'docx';
    return 'other';
  }

  function queryText(value: unknown) {
    if (Array.isArray(value)) return String(value[0] || '').trim();
    return typeof value === 'string' ? value.trim() : '';
  }

  const incomingRouteContext = computed(() => ({
    source: queryText(route.query.source),
    nodeId: queryText(route.query.nodeId),
    nodeLabel: queryText(route.query.nodeLabel),
    mapType: queryText(route.query.mapType),
    resourceId: queryText(route.query.resourceId),
    resourceTitle: queryText(route.query.resourceTitle),
    resourceChapter: queryText(route.query.resourceChapter),
    resourceType: queryText(route.query.resourceType),
    packageId: queryText(route.query.packageId),
    upstreamSource: queryText(route.query.upstreamSource),
  }));

  function compactQuery(payload: Record<string, string | number | undefined>) {
    return Object.fromEntries(
      Object.entries(payload).filter(
        ([, value]) => value !== undefined && String(value).trim()
      )
    ) as Record<string, string | number>;
  }

  function contextRouteQuery(
    extra: Record<string, string | number | undefined> = {}
  ) {
    return compactQuery({
      ...incomingRouteContext.value,
      ...extra,
    });
  }

  const incomingSeedSummary = computed(() => {
    const topic = queryText(route.query.topic);
    const goal = queryText(route.query.goal);
    const source = queryText(route.query.source);
    const { nodeLabel, resourceTitle, resourceChapter } =
      incomingRouteContext.value;
    if (!topic && !goal && !source && !nodeLabel && !resourceTitle) return '';
    const segments = [];
    if (source) segments.push(`来自 ${sourceLabel(source)}`);
    if (topic) segments.push(`主题：${topic}`);
    if (nodeLabel) segments.push(`图谱节点：${nodeLabel}`);
    if (resourceTitle) {
      segments.push(
        `资料：${resourceTitle}${
          resourceChapter ? `（${resourceChapter}）` : ''
        }`
      );
    }
    if (goal) segments.push(`目标：${goal}`);
    return segments.join(' / ');
  });
  const courseSeedActions = computed(() => {
    if (!activeCourse.value) return [];
    const firstNote = activeCourse.value.notes[0];
    const firstConcept = activeCourse.value.concepts[0];
    return [
      {
        topic: String(route.query.topic || firstConcept?.title || '课程重点'),
        goal: String(
          route.query.goal ||
            `基于《${activeCourse.value.title}》生成课堂笔记、知识卡和自测题`
        ),
      },
      {
        topic: firstNote?.title || '课堂笔记整理',
        goal: `把${
          firstNote?.points.join('、') || '课堂笔记'
        }整理成复习讲义和练习`,
      },
      {
        topic: '课程知识图谱',
        goal: '按知识、问题、能力和目标四类图谱生成一套学习资源包',
      },
    ];
  });
  const gradeStats = computed(() => {
    if (!gradeResult.value) return [];
    return [
      { label: '得分', value: `${gradeResult.value.score} / 100` },
      {
        label: '掌握度变化',
        value: `${Math.round(
          gradeResult.value.mastery_before * 100
        )}% -> ${Math.round(gradeResult.value.mastery_after * 100)}%`,
      },
      { label: '后续建议', value: `${gradeResult.value.follow_up.length} 项` },
    ];
  });

  const diagramNodes = computed(() => {
    const content = imageResult.value?.diagram?.content || '';
    const labels = Array.from(content.matchAll(/\[([^\]]+)\]/g)).map(
      (item) => item[1]
    );
    return labels.length
      ? labels.slice(0, 6)
      : imageResult.value?.solution_outline?.slice(0, 4) || [];
  });
  const imageStats = computed(() => {
    if (!imageResult.value) return [];
    return [
      { label: '识别清晰度', value: imageClarityLabel.value },
      { label: '图解节点', value: `${diagramNodes.value.length} 项` },
      {
        label: '解题步骤',
        value: `${imageResult.value.solution_outline.length} 步`,
      },
    ];
  });
  const imageClarityLabel = computed(() => {
    const confidence = imageResult.value?.confidence || 0;
    if (confidence >= 0.85) return '高';
    if (confidence >= 0.6) return '中';
    return '需核对';
  });

  function hydrateFormsFromReport(snapshot: LearningReport | null) {
    if (!snapshot) return;
    const primaryWeakPoint = snapshot.weak_points?.[0] || '';
    const primaryGoal = snapshot.current_goal || '';
    const primarySubject =
      form.subject || gradeForm.subject || imageForm.subject || '';

    if (!activeCourse.value && !form.topic && primaryWeakPoint) {
      form.topic = primaryWeakPoint;
    }
    if (!form.goal && primaryGoal) form.goal = primaryGoal;
    if (!gradeForm.topic && primaryWeakPoint)
      gradeForm.topic = primaryWeakPoint;
    if (!imageForm.subject && primarySubject)
      imageForm.subject = primarySubject;

    if (!gradeForm.subject && form.subject) gradeForm.subject = form.subject;
    if (!imageForm.subject && form.subject) imageForm.subject = form.subject;
  }

  function defaultCourseTopic() {
    return (
      activeCourse.value?.concepts[0]?.title ||
      activeCourse.value?.notes[0]?.title ||
      activeCourse.value?.chapters[0]?.lessons[0]?.title ||
      '课程重点'
    );
  }

  function hydrateFormsFromRoute() {
    const routeContext = incomingRouteContext.value;
    const seedMode = queryText(route.query.mode);
    const seedSubject = queryText(route.query.subject);
    const seedTopic =
      queryText(route.query.topic) ||
      routeContext.nodeLabel ||
      routeContext.resourceTitle;
    const seedGoal = queryText(route.query.goal);
    const signature = JSON.stringify({
      seedMode,
      seedSubject,
      seedTopic,
      seedGoal,
      nodeId: routeContext.nodeId,
      nodeLabel: routeContext.nodeLabel,
      mapType: routeContext.mapType,
      resourceId: routeContext.resourceId,
      resourceTitle: routeContext.resourceTitle,
      resourceChapter: routeContext.resourceChapter,
      resourceType: routeContext.resourceType,
      source: routeContext.source,
      upstreamSource: routeContext.upstreamSource,
      routeName: String(route.name || ''),
    });
    if (signature === lastSeedSignature.value) return;
    lastSeedSignature.value = signature;

    if (
      seedMode === 'exercise' ||
      seedMode === 'image' ||
      seedMode === 'package'
    ) {
      activeMode.value = seedMode as WorkbenchMode;
    }
    if (seedSubject) {
      form.subject = seedSubject;
      gradeForm.subject = seedSubject;
      imageForm.subject = seedSubject;
    } else if (activeCourse.value && !form.subject) {
      form.subject = activeCourse.value.title;
      gradeForm.subject = activeCourse.value.title;
      imageForm.subject = activeCourse.value.title;
    }
    if (seedTopic) {
      form.topic = seedTopic;
      gradeForm.topic = seedTopic;
      if (!imageForm.question_text.trim()) {
        imageForm.question_text = `请围绕“${seedTopic}”生成结构化题解与图示说明。`;
      }
    } else if (activeCourse.value && !form.topic) {
      const courseTopic = defaultCourseTopic();
      form.topic = courseTopic;
      gradeForm.topic = courseTopic;
    }
    if (seedGoal) {
      form.goal = seedGoal;
    } else if (routeContext.resourceTitle) {
      form.goal = [
        `围绕资料《${routeContext.resourceTitle}》生成讲义、练习、思维导图和质量核查清单。`,
        routeContext.resourceChapter
          ? `章节：${routeContext.resourceChapter}。`
          : '',
        routeContext.nodeLabel
          ? `同步校准图谱节点：${routeContext.nodeLabel}。`
          : '',
      ]
        .filter(Boolean)
        .join('');
    } else if (routeContext.nodeLabel) {
      form.goal = `围绕课程图谱节点“${routeContext.nodeLabel}”生成可复习、可练习、可回图谱核验的学习资料。`;
    } else if (activeCourse.value && !form.goal) {
      form.goal = `结合${activeCourse.value.shortTitle}的课堂笔记、课程图谱和薄弱点生成可执行学习资源。`;
    }
  }

  function applyCourseSeed(topic: string, goal: string) {
    if (activeCourse.value) {
      form.subject = activeCourse.value.title;
      gradeForm.subject = activeCourse.value.title;
      imageForm.subject = activeCourse.value.title;
    }
    form.topic = topic;
    gradeForm.topic = topic;
    form.goal = goal;
    activeMode.value = 'package';
    Message.success('已载入课程上下文');
  }

  function sourceLabel(source: string) {
    const map: Record<string, string> = {
      'classroom-notes': '课堂笔记',
      'knowledge-map': '课程图谱',
      'knowledge-path': '图谱学习路径',
      'course-agent': '课程助手',
      'course-agent-graph': '课程图谱',
      'course-workspace': '课程资源中心',
      'resource-generation': '资源生成中心',
      'course-agent-package-audit': '课程内容检查',
      'resource': '课程资料',
    };
    return map[source] || source;
  }

  function resourceTypeLabel(type: ResourceItem['type']) {
    const map: Record<ResourceItem['type'], string> = {
      lecture_doc: '讲解文档',
      mind_map: '思维导图',
      practice_set: '练习题',
      reading: '拓展阅读',
      case_project: '实操案例',
      video_script: '讲解脚本',
      reflection: '口头复述',
    };
    return map[type] || type;
  }

  function formatFileSize(size: number) {
    if (!Number.isFinite(size) || size <= 0) return '0 KB';
    if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  }

  async function downloadArtifact(artifact: GeneratedResourceArtifact) {
    const token = getToken();
    try {
      const response = await axios.get(artifact.download_url, {
        responseType: 'blob',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const blobUrl = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = artifact.file_name;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
      return true;
    } catch {
      Message.warning('资源文件暂时无法下载，请稍后重试。');
      return false;
    }
  }

  async function downloadAllArtifacts() {
    if (!downloadableArtifacts.value.length) return;
    let downloaded = 0;
    for (const artifact of downloadableArtifacts.value) {
      if (await downloadArtifact(artifact)) downloaded += 1;
    }
    if (downloaded === downloadableArtifacts.value.length) {
      Message.success(`已开始下载 ${downloaded} 个文件`);
    } else if (downloaded > 0) {
      Message.warning(`已下载 ${downloaded} 个文件，其余文件请稍后重试`);
    }
  }

  function openArtifactPreview(
    artifact: GeneratedResourceArtifact,
    event?: MouseEvent
  ) {
    if (event?.currentTarget instanceof HTMLElement) {
      artifactPreviewTrigger.value = event.currentTarget;
    }
    previewedArtifact.value = artifact;
  }

  function closeArtifactPreview() {
    previewedArtifact.value = null;
  }

  function artifactPreviewFocusableElements() {
    const panel = artifactPreviewPanel.value;
    if (!panel) return [];
    return Array.from(
      panel.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hasAttribute('hidden'));
  }

  function handleArtifactPreviewKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeArtifactPreview();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = artifactPreviewFocusableElements();
    if (!focusable.length) {
      event.preventDefault();
      artifactPreviewPanel.value?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const activeElement = document.activeElement;
    if (
      event.shiftKey &&
      (activeElement === first || activeElement === artifactPreviewPanel.value)
    ) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  watch(previewedArtifact, async (artifact, previousArtifact) => {
    if (artifact) {
      await nextTick();
      artifactPreviewPanel.value?.focus();
      return;
    }
    if (previousArtifact) {
      await nextTick();
      artifactPreviewTrigger.value?.focus();
      artifactPreviewTrigger.value = null;
    }
  });

  function openKnowledgeGraph() {
    if (activeCourse.value) {
      router.push({
        name: 'StudentCourseKnowledge',
        params: { courseId: activeCourse.value.id },
        query: contextRouteQuery({
          topic: downloadablePackage.value?.topic || form.topic,
          source: 'resource-generation',
          packageId:
            downloadablePackage.value?.package_id ||
            incomingRouteContext.value.packageId,
          nodeLabel:
            incomingRouteContext.value.nodeLabel ||
            incomingRouteContext.value.resourceTitle ||
            downloadablePackage.value?.topic ||
            form.topic,
          mapType:
            incomingRouteContext.value.mapType ||
            (incomingRouteContext.value.resourceId ? 'problem' : 'knowledge'),
        }),
      });
      return;
    }
    Message.info('请先选择一门课程，再查看资源与知识点的关联');
  }

  function openAiReview(targetArtifact?: GeneratedResourceArtifact) {
    const topic =
      downloadablePackage.value?.topic ||
      packageResult.value?.topic ||
      form.topic;
    const packageId = downloadablePackage.value?.package_id;
    const courseId = activeCourse.value?.id || '';
    const artifact = targetArtifact || primaryReviewArtifact.value;
    const artifactFileId =
      artifact && packageId ? `${packageId}/${artifact.file_name}` : '';
    closeArtifactPreview();
    router.push({
      path: '/tutor',
      query: contextRouteQuery({
        subject: form.subject,
        topic,
        source: 'resource-generation',
        packageId,
        packageTopic: topic,
        packageSource:
          downloadablePackage.value?.source ||
          incomingRouteContext.value.source ||
          'resource-generation',
        resourceTitle: artifact?.title || topic,
        resourceType: artifact?.kind,
        currentFileId: artifactFileId,
        fileId: artifactFileId,
        fileName: artifact?.file_name,
        artifactKind: artifact?.kind,
        artifactList: artifactReviewList.value,
        artifactPreview: artifactPreviewSummary.value,
        ...(courseId ? { courseId } : {}),
        intent: 'exercise-review',
        prompt: [
          `请对「${
            topic || form.subject || '当前课程'
          }」学习资源包做 AI 复核。`,
          packageId ? `资源包编号：${packageId}` : '',
          artifact
            ? `当前优先复核文件：${artifact.title}（${
                artifact.file_name
              }，${artifactKindLabel(artifact.kind)}）`
            : '',
          artifactReviewList.value
            ? `生成文件清单：\n${artifactReviewList.value}`
            : '',
          artifactPreviewSummary.value
            ? `文件预览摘要：\n${artifactPreviewSummary.value}`
            : '',
          form.subject ? `课程/学科：${form.subject}` : '',
          '请先说明当前复核依据是文件预览、路由文件线索还是完整原文；如果没有原文片段，不要声称已经完整读取文件。再检查讲义、练习、导图、阅读材料是否围绕课程目标和薄弱点，指出证据不足、重复或需要回炉生成的部分，并给出下一步个性化学习建议。',
        ]
          .filter(Boolean)
          .join('\n'),
      }),
    });
  }

  function buildPackageExportText() {
    if (!packageResult.value) return '';
    const lines = [
      `${packageResult.value.topic} 学习资源包`,
      `课程：${packageResult.value.subject}`,
      `目标：${packageResult.value.goal}`,
      '',
      '个性化匹配依据：',
      ...packageResult.value.personalization_basis.map(
        (item, index) => `${index + 1}. ${item}`
      ),
      '',
      '资源清单：',
      ...packageResources.value.flatMap((item, index) => [
        `${index + 1}. ${resourceTypeLabel(item.type)}｜${item.title}`,
        `   用时：${item.estimated_minutes} 分钟`,
        `   描述：${item.description}`,
        `   预览：${item.content_preview}`,
      ]),
    ];
    return lines.join('\n');
  }

  async function copyTextPayload(text: string, successText: string) {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    Message.success(successText);
  }

  async function copyPackageSummary() {
    if (!packageResult.value) return;
    try {
      await copyTextPayload(buildPackageExportText(), '资源包摘要已复制');
    } catch {
      Message.error('复制失败，请检查浏览器剪贴板权限');
    }
  }

  async function loadProfile(refresh = false) {
    loadingReport.value = true;
    try {
      report.value = await fetchLearningReport(refresh);
      hydrateFormsFromReport(report.value);
      hydrateFormsFromRoute();
    } catch (error) {
      Message.warning('画像数据暂不可用，可先按当前设置继续生成资源');
    } finally {
      loadingReport.value = false;
    }
  }

  async function restoreLatestPackage() {
    try {
      const recentPackages = await fetchRecentGeneratedPackages(
        activeCourse.value?.id
      );
      const restored = recentPackages[0]
        ? restoreGeneratedPackage(recentPackages[0])
        : null;
      if (!restored || packageResult.value || loadingPackage.value) return;
      const difficulty =
        form.difficulty === 'auto' ? 'standard' : form.difficulty;
      downloadablePackage.value = restored;
      activeRunEvidence.value = restored.run || null;
      if (
        restored.run?.status === 'cancelled' ||
        restored.run?.status === 'failed'
      ) {
        resumableRunId.value = restored.run.run_id || '';
      }
      packageResult.value = buildResourcePackageViewModel(restored, {
        goal: form.goal || `继续学习 ${restored.topic}`,
        difficulty,
        targetMinutes: form.minutes,
        personalizationBasis: [
          '已从课程资源库恢复',
          `生成主题：${restored.topic}`,
        ],
      });
    } catch {
      // The empty state remains usable when no archived package can be restored.
    }
  }

  async function handleGeneratePackage() {
    if (!form.subject.trim()) {
      Message.warning('请先填写课程名称');
      return;
    }
    if (loadingPackage.value) return;
    loadingPackage.value = true;
    cancellationRequested.value = false;
    resumableRunId.value = '';
    conflictingRunId.value = '';
    showAllArtifacts.value = false;
    activeRunEvidence.value = null;
    generationController.value = new AbortController();
    packageResult.value = null;
    downloadablePackage.value = null;
    try {
      const difficulty =
        form.difficulty === 'auto' ? 'standard' : form.difficulty;
      const goal = form.goal || '生成可下载的个性化课程资源包';
      const artifactResult = await generateDownloadableResourcePackage(
        {
          course_id: activeCourse.value?.id,
          resource_id: incomingRouteContext.value.resourceId || undefined,
          node_id: incomingRouteContext.value.nodeId || undefined,
          node_label: incomingRouteContext.value.nodeLabel || undefined,
          map_type: incomingRouteContext.value.mapType || undefined,
          source:
            incomingRouteContext.value.source ||
            incomingRouteContext.value.upstreamSource ||
            undefined,
          subject: form.subject,
          topic:
            form.topic ||
            (activeCourse.value ? defaultCourseTopic() : weakPoints.value[0]) ||
            '课程重点',
          learning_goal: goal,
          difficulty,
          target_minutes: form.minutes,
          resource_types: buildProductionResourceTypes(form.documentFormat),
          use_web_search: false,
        },
        {
          signal: generationController.value.signal,
          onEvidence: (evidence) => {
            activeRunEvidence.value = evidence;
            if (
              evidence.status === 'cancelled' ||
              evidence.status === 'failed'
            ) {
              resumableRunId.value = evidence.run_id || '';
            }
          },
        }
      );

      downloadablePackage.value = artifactResult;
      activeRunEvidence.value = artifactResult.run || activeRunEvidence.value;
      packageResult.value = buildResourcePackageViewModel(artifactResult, {
        goal,
        difficulty,
        targetMinutes: form.minutes,
        personalizationBasis: [
          report.value?.current_goal || '',
          report.value?.learning_style
            ? `学习偏好：${report.value.learning_style}`
            : '',
          !activeCourse.value && weakPoints.value.length
            ? `薄弱点：${weakPoints.value.slice(0, 3).join('、')}`
            : '',
          activeCourse.value
            ? `课程上下文：${activeCourse.value.shortTitle}`
            : '',
          `目标难度：${difficulty}`,
        ],
      });
      const subject = packageResult.value.subject || form.subject;
      const topic = packageResult.value.topic || form.topic;
      gradeForm.subject = subject;
      gradeForm.topic = topic;
      imageForm.subject = subject;
      if (!imageForm.question_text.trim()) {
        imageForm.question_text = `请结合 ${topic} 的核心概念，对题目进行结构化讲解。`;
      }
      if (artifactResult.run?.status === 'partial_success') {
        Message.warning('核心文件已生成，部分后续处理尚未完成，可稍后继续');
      } else {
        Message.success(
          artifactResult.persistence_status === 'resources_persisted'
            ? '学习资源已生成，并保存到课程资料'
            : '学习资源已生成，并保存到我的资源'
        );
      }
    } catch (error: any) {
      if (
        cancellationRequested.value &&
        activeRunEvidence.value?.status === 'cancelled'
      ) {
        resumableRunId.value = activeRunEvidence.value.run_id || '';
        Message.info('本次生成已停止，可继续上次生成');
      } else if (
        cancellationRequested.value ||
        error?.name === 'AbortError' ||
        error?.code === 'ERR_CANCELED'
      ) {
        Message.warning('停止请求已提交，系统仍在等待当前生成步骤安全退出');
      } else {
        const detail = error?.response?.data?.detail || {};
        const detailCode = String(detail?.code || '');
        const runId = String(
          detail?.run_id || activeRunEvidence.value?.run_id || ''
        ).trim();
        if (detailCode === 'RESOURCE_RUN_ALREADY_ACTIVE') {
          conflictingRunId.value = runId;
          Message.warning(
            '已有其他资源任务正在生成，请先查看或停止该任务后再试'
          );
        } else if (detailCode === 'IDEMPOTENCY_CONFLICT') {
          Message.warning('本次请求与正在执行的任务不一致，请重新发起');
        } else {
          Message.error('资源暂未生成，请稍后重试或继续上次生成');
        }
      }
    } finally {
      loadingPackage.value = false;
      generationController.value = null;
    }
  }

  async function handleCancelPackage() {
    const runId = activeRunEvidence.value?.run_id;
    if (!runId || cancellationRequested.value) return;
    cancellationRequested.value = true;
    try {
      const evidence = await cancelResourceRun(runId);
      if (evidence) activeRunEvidence.value = evidence;
      if (evidence?.status === 'cancelled') {
        resumableRunId.value = runId;
      } else {
        Message.info('正在安全停止当前生成步骤');
      }
    } catch {
      cancellationRequested.value = false;
      Message.error('停止请求未送达，请稍后重试');
    }
  }

  async function handleResumePackage() {
    const runId = conflictingRunId.value || resumableRunId.value;
    if (!runId || loadingPackage.value) return;
    loadingPackage.value = true;
    cancellationRequested.value = false;
    generationController.value = new AbortController();
    try {
      const artifactResult = await resumeResourceRun(runId, {
        signal: generationController.value.signal,
        onEvidence: (evidence) => {
          activeRunEvidence.value = evidence;
        },
      });
      downloadablePackage.value = artifactResult;
      activeRunEvidence.value = artifactResult.run || activeRunEvidence.value;
      const originalRequest = artifactResult.run?.requested;
      const difficulty =
        originalRequest?.difficulty ||
        (form.difficulty === 'auto' ? 'standard' : form.difficulty);
      packageResult.value = buildResourcePackageViewModel(artifactResult, {
        goal:
          originalRequest?.learning_goal || `${artifactResult.topic} 学习资源`,
        difficulty,
        targetMinutes: originalRequest?.target_minutes || form.minutes,
        personalizationBasis: ['已恢复上次资源生成任务'],
      });
      resumableRunId.value = '';
      conflictingRunId.value = '';
      if (artifactResult.run?.status === 'partial_success') {
        Message.warning('核心文件已恢复，部分后续处理仍待完成');
      } else {
        Message.success('上次资源生成任务已完成');
      }
    } catch (error: any) {
      if (error?.name !== 'AbortError' && error?.code !== 'ERR_CANCELED') {
        Message.error('上次任务暂未恢复，请稍后重试');
      }
    } finally {
      loadingPackage.value = false;
      generationController.value = null;
    }
  }

  async function handleGrade() {
    if (!gradeForm.student_answer.trim()) {
      Message.warning('请先填写学生作答');
      return;
    }
    loadingGrade.value = true;
    try {
      gradeResult.value = await gradeResourceExercise({
        ...gradeForm,
        max_score: 100,
      });
      await loadProfile(false);
      Message.success('批改完成，后续学习建议已更新');
    } catch (error) {
      Message.error('批改暂未完成，请稍后重试');
    } finally {
      loadingGrade.value = false;
    }
  }

  function handleImageFile(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    imageName.value = file.name;
    const reader = new FileReader();
    reader.onload = () => {
      imageForm.image_base64 = String(reader.result || '');
    };
    reader.readAsDataURL(file);
  }

  async function handleImageAnalyze() {
    loadingImage.value = true;
    try {
      imageResult.value = await analyzeImageProblem(imageForm);
      Message.success('题目分析完成');
    } catch (error) {
      Message.error('图片分析暂未完成，请重新上传或稍后重试');
    } finally {
      loadingImage.value = false;
    }
  }

  onMounted(async () => {
    hydrateFormsFromRoute();
    await Promise.allSettled([loadProfile(false), restoreLatestPackage()]);
  });

  watch(
    () => route.name,
    async (name) => {
      activeMode.value = resolveRouteMode(name);
      hydrateFormsFromRoute();
    }
  );

  watch(
    () => route.query,
    () => {
      hydrateFormsFromRoute();
    },
    { deep: true }
  );
</script>

<style scoped lang="less" src="./resource-workshop-v2.less"></style>
