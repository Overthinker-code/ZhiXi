<template>
  <div class="resource-workshop-page">
    <Breadcrumb :items="['menu.resourceWorkshop', 'menu.resourceGeneration']" />

    <section class="workshop-hero">
      <div class="hero-visual" aria-hidden="true">
        <div class="folder-box">
          <div class="folder-lid" />
          <div class="folder-body">
            <span class="folder-sheet folder-sheet--one" />
            <span class="folder-sheet folder-sheet--two">AI</span>
          </div>
        </div>
      </div>

      <div class="hero-main">
        <div class="hero-title-line">
          <h1>AI 学习资源工坊</h1>
          <span>{{ currentModeCaption }}</span>
        </div>
        <p>{{ currentPageDescription }}</p>

        <div class="hero-metrics">
          <article
            v-for="item in heroHighlights"
            :key="item.label"
            class="hero-metric"
          >
            <span class="metric-icon" />
            <div>
              <strong>{{ item.label }}</strong>
              <p>{{ item.value }}</p>
            </div>
          </article>
        </div>
      </div>

      <aside class="profile-state">
        <div class="state-label">
          <span>当前学习画像状态</span>
          <i />
        </div>
        <strong>{{ report ? riskLabel(report.risk_level) : '待生成' }}</strong>
        <p>{{ report?.current_goal || '尚未进入可生成画像状态' }}</p>
        <a-button
          type="primary"
          :loading="loadingReport"
          @click="loadProfile(true)"
        >
          刷新学习画像
        </a-button>
      </aside>
    </section>

    <section
      v-if="isUnifiedWorkbench"
      class="mode-dock"
      role="tablist"
      aria-label="工作模式"
    >
      <div class="mode-dock__label">工作模式</div>
      <button
        v-for="item in modeOptions"
        :key="item.value"
        type="button"
        class="mode-card"
        :class="{ 'mode-card--active': activeMode === item.value }"
        role="tab"
        :aria-selected="activeMode === item.value"
        @click="activeMode = item.value"
      >
        <span class="mode-card__icon">{{ item.badge }}</span>
        <span class="mode-card__copy">
          <strong>{{ item.label }}</strong>
          <em>{{ item.description }}</em>
        </span>
        <span v-if="activeMode === item.value" class="mode-card__check">✓</span>
      </button>
    </section>

    <section class="workbench-grid">
      <aside class="settings-column">
        <div class="work-card settings-card">
          <div class="card-heading">
            <span class="step-badge">1</span>
            <h2>{{
              isPackageMode
                ? '资源设置'
                : isExerciseMode
                ? '批改设置'
                : '图像题解设置'
            }}</h2>
          </div>

          <div v-if="incomingSeedSummary" class="seed-banner">
            <span>本轮进入上下文</span>
            <strong>{{ incomingSeedSummary }}</strong>
          </div>

          <div v-if="activeCourse" class="course-seed-card">
            <div class="course-seed-card__head">
              <span>课程上下文</span>
              <strong>{{ activeCourse.title }}</strong>
            </div>
            <p>{{ activeCourse.description }}</p>
            <div class="seed-links">
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
          </div>

          <a-form
            v-if="isPackageMode"
            :model="form"
            layout="vertical"
            class="compact-form"
          >
            <a-form-item field="subject" label="学科/课程">
              <a-input v-model="form.subject" placeholder="数学 / 高二上学期" />
            </a-form-item>
            <a-form-item field="topic" label="知识点">
              <a-input v-model="form.topic" placeholder="函数的单调性" />
            </a-form-item>
            <a-form-item field="goal" label="学习目标">
              <a-textarea
                v-model="form.goal"
                :auto-size="{ minRows: 4, maxRows: 5 }"
                placeholder="理解并掌握函数单调性的判定方法，能解决相关综合题"
              />
            </a-form-item>
            <div class="form-two">
              <a-form-item field="difficulty" label="目标难度">
                <a-select v-model="form.difficulty">
                  <a-option value="auto">自动匹配</a-option>
                  <a-option value="foundation">基础巩固</a-option>
                  <a-option value="standard">标准提升</a-option>
                  <a-option value="challenge">挑战拓展</a-option>
                </a-select>
              </a-form-item>
              <a-form-item field="minutes" label="学习时长">
                <a-input-number v-model="form.minutes" :min="10" :max="120" />
              </a-form-item>
            </div>
            <a-button
              class="primary-action"
              type="primary"
              long
              :loading="loadingPackage"
              @click="handleGeneratePackage"
            >
              ✦ 生成正式资源包
            </a-button>
          </a-form>

          <a-form
            v-if="isExerciseMode"
            :model="gradeForm"
            layout="vertical"
            class="compact-form"
          >
            <a-form-item label="学科/课程">
              <a-input
                v-model="gradeForm.subject"
                placeholder="例如：数据库系统"
              />
            </a-form-item>
            <a-form-item label="知识点">
              <a-input v-model="gradeForm.topic" placeholder="例如：关系模型" />
            </a-form-item>
            <a-form-item label="题目">
              <a-textarea
                v-model="gradeForm.question"
                :auto-size="{ minRows: 4, maxRows: 6 }"
              />
            </a-form-item>
            <a-form-item label="学生作答">
              <a-textarea
                v-model="gradeForm.student_answer"
                :auto-size="{ minRows: 5, maxRows: 7 }"
              />
            </a-form-item>
            <a-form-item label="参考答案（可选）">
              <a-textarea
                v-model="gradeForm.reference_answer"
                :auto-size="{ minRows: 3, maxRows: 5 }"
              />
            </a-form-item>
            <a-button
              class="primary-action"
              type="primary"
              long
              :loading="loadingGrade"
              @click="handleGrade"
            >
              提交批改并同步画像
            </a-button>
          </a-form>

          <a-form
            v-if="isImageMode"
            :model="imageForm"
            layout="vertical"
            class="compact-form"
          >
            <a-form-item label="学科/课程">
              <a-input
                v-model="imageForm.subject"
                placeholder="例如：数据库系统"
              />
            </a-form-item>
            <a-form-item label="补充题干">
              <a-textarea
                v-model="imageForm.question_text"
                :auto-size="{ minRows: 5, maxRows: 7 }"
                placeholder="可补充题干文字，提升识别稳定性"
              />
            </a-form-item>
            <label class="upload-tile">
              <input type="file" accept="image/*" @change="handleImageFile" />
              <strong>{{ imageName || '上传题目图片' }}</strong>
              <span>支持课堂拍照、练习截图与试题图片</span>
            </label>
            <a-button
              class="primary-action"
              type="primary"
              long
              :disabled="!imageForm.image_base64"
              :loading="loadingImage"
              @click="handleImageAnalyze"
            >
              开始图像识别与题解
            </a-button>
          </a-form>
        </div>
      </aside>

      <main class="result-column">
        <div v-if="isPackageMode" class="work-card flow-card">
          <div class="card-heading">
            <span class="step-badge">2</span>
            <h2>生成流程</h2>
          </div>
          <AgentStagePanel :nodes="agentStageNodes" />
        </div>

        <div v-if="isPackageMode" class="work-card result-preview-card">
          <div class="card-heading card-heading--split">
            <div>
              <span class="step-badge">3</span>
              <h2>生成结果预览</h2>
            </div>
            <span class="muted-pill">生成后将包含以下内容</span>
          </div>

          <template v-if="packageResult">
            <div class="package-summary">
              <div>
                <h3>{{ packageResult.topic }} 学习资源包</h3>
                <p>{{ packageResult.goal }}</p>
              </div>
              <a-tag color="arcoblue"
                >{{ packageResult.resources.length }} 类资源</a-tag
              >
            </div>
            <div class="package-actions">
              <a-button size="small" type="outline" @click="copyPackageSummary"
                >复制摘要</a-button
              >
              <a-button
                size="small"
                type="outline"
                @click="downloadPackageSummary"
              >
                下载资源包
              </a-button>
              <a-button
                v-if="videoScriptResource"
                size="small"
                type="primary"
                @click="() => goToDigitalHumanStudio()"
              >
                生成数字人讲解
              </a-button>
            </div>
            <div v-if="downloadablePackage" class="artifact-download-panel">
              <div class="artifact-download-panel__head">
                <div>
                  <strong>真实生成文件</strong>
                  <span>后端已生成 Markdown、PDF、导图和脚本，并完成生成审查</span>
                </div>
                <div class="artifact-stats">
                  <article v-for="item in artifactStats" :key="item.label">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </article>
                </div>
              </div>
              <div
                v-if="downloadablePackage.quality_notes?.length || downloadablePackage.agent_trace?.length"
                class="artifact-audit-panel"
              >
                <section v-if="downloadablePackage.quality_notes?.length">
                  <strong>质量审查</strong>
                  <ul>
                    <li
                      v-for="item in downloadablePackage.quality_notes"
                      :key="item"
                    >
                      {{ item }}
                    </li>
                  </ul>
                </section>
                <section v-if="downloadablePackage.agent_trace?.length">
                  <strong>生成链路</strong>
                  <ol>
                    <li
                      v-for="item in downloadablePackage.agent_trace"
                      :key="item"
                    >
                      {{ item }}
                    </li>
                  </ol>
                </section>
              </div>
              <div class="artifact-grid">
                <article
                  v-for="artifact in downloadablePackage.artifacts"
                  :key="artifact.file_name"
                  class="artifact-card"
                >
                  <div>
                    <span>{{ artifactKindLabel(artifact.kind) }}</span>
                    <strong>{{ artifact.title }}</strong>
                    <small>{{ artifact.file_name }} · {{ formatFileSize(artifact.file_size) }}</small>
                  </div>
                  <p>{{ artifact.preview }}</p>
                  <button type="button" @click="downloadArtifact(artifact)">
                    下载文件
                  </button>
                </article>
              </div>
            </div>
            <div class="result-stats">
              <article v-for="item in packageStats" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>
            <div class="basis-row">
              <a-tag
                v-for="item in packageResult.personalization_basis"
                :key="item"
                color="purple"
              >
                {{ item }}
              </a-tag>
            </div>
            <div class="resource-grid">
              <article
                v-for="(item, index) in packageResult.resources"
                :key="item.title"
                class="resource-card zy-flip-in"
                :style="{ animationDelay: `${index * 0.08}s` }"
              >
                <div class="resource-card__top">
                  <span class="resource-kind">{{
                    resourceTypeLabel(item.type)
                  }}</span>
                  <small>{{ item.estimated_minutes }} 分钟</small>
                </div>
                <h4>{{ item.title }}</h4>
                <p>{{ item.description }}</p>
                <div class="preview-text">{{ item.content_preview }}</div>
                <div class="resource-card__actions">
                  <a-button
                    size="mini"
                    type="outline"
                    @click="copyResourceItem(item)"
                    >复制</a-button
                  >
                  <a-button
                    v-if="item.type === 'video_script'"
                    size="mini"
                    type="primary"
                    @click="goToDigitalHumanStudio(item)"
                  >
                    去数字人
                  </a-button>
                </div>
              </article>
            </div>
          </template>

          <div v-else class="empty-preview">
            <div class="empty-folder" />
            <strong>尚未生成资源包</strong>
            <p
              >设置左侧参数并点击「生成正式资源包」，即可在此预览生成的资源内容。</p
            >
            <div class="preview-resource-row">
              <article
                v-for="item in resourcePreviewCards"
                :key="item.label"
                :class="`preview-resource preview-resource--${item.tone}`"
              >
                <span>{{ item.icon }}</span>
                <strong>{{ item.label }}</strong>
                <small>{{ item.desc }}</small>
              </article>
            </div>
          </div>
        </div>

        <div v-if="isExerciseMode" class="work-card result-preview-card">
          <div class="card-heading">
            <span class="step-badge">2</span>
            <h2>练习批改与掌握度更新</h2>
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
              <span>掌握度更新</span>
              <span>
                {{ Math.round(gradeResult.mastery_before * 100) }}% →
                {{ Math.round(gradeResult.mastery_after * 100) }}%
              </span>
            </div>
            <a-progress
              :percent="Math.round(gradeResult.mastery_after * 100)"
              :show-text="false"
            />
            <p>{{ gradeResult.feedback }}</p>
            <ul class="plain-list">
              <li v-for="item in gradeResult.follow_up" :key="item">{{
                item
              }}</li>
            </ul>
          </div>
          <div v-else class="empty-preview empty-preview--compact">
            <div class="empty-folder" />
            <strong>等待提交练习</strong>
            <p>提交后将展示得分、掌握度变化、错因反馈与后续追练建议。</p>
          </div>
        </div>

        <div v-if="isImageMode" class="work-card result-preview-card">
          <div class="card-heading">
            <span class="step-badge">2</span>
            <h2>图像题目识别与图解</h2>
          </div>
          <div v-if="imageResult" class="image-result">
            <div class="result-stats">
              <article v-for="item in imageStats" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </article>
            </div>
            <div class="result-meta">
              <a-tag>{{ imageResult.subject }}</a-tag>
              <a-tag color="arcoblue">{{ imageResult.problem_type }}</a-tag>
              <span
                >置信度 {{ Math.round(imageResult.confidence * 100) }}%</span
              >
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
          <div v-else class="empty-preview empty-preview--compact">
            <div class="empty-folder" />
            <strong>等待上传题目图片</strong>
            <p>分析后会展示识别文本、图解节点、步骤化讲解和完整题解。</p>
          </div>
        </div>
      </main>

      <aside class="insight-column">
        <div class="work-card insight-card">
          <div class="card-heading card-heading--split">
            <div>
              <span class="step-badge">4</span>
              <h2>学习画像与推荐</h2>
            </div>
            <button type="button" class="text-link" @click="loadProfile(true)"
              >更多 ›</button
            >
          </div>
          <a-spin :loading="loadingReport" style="width: 100%">
            <template v-if="report">
              <div class="weak-title">当前薄弱点</div>
              <div class="tag-row">
                <a-tag v-for="item in weakPoints" :key="item" color="orange">{{
                  item
                }}</a-tag>
              </div>
              <div class="weak-title">当前学习目标</div>
              <div class="goal-line">{{
                report.current_goal || '保持当前课程进度'
              }}</div>
              <div class="weak-title">推荐生成方向</div>
              <ul class="recommend-list">
                <li>围绕薄弱项生成讲解资源包</li>
                <li>综合题解题思路训练包</li>
                <li>错题强化与变式练习包</li>
              </ul>
            </template>
            <div v-else class="mini-empty"
              >刷新画像后显示薄弱点和推荐方向。</div
            >
          </a-spin>
        </div>

        <div class="work-card path-card">
          <div class="card-heading">
            <span class="step-badge">5</span>
            <h2>个性化学习路径（预览）</h2>
          </div>
          <div v-if="pathNodes.length" class="path-flow">
            <article
              v-for="(node, index) in pathNodes"
              :key="node.title"
              class="path-node"
            >
              <span>{{ index + 1 }}</span>
              <strong>{{ node.title }}</strong>
              <small>{{ node.minutes }} 课时</small>
            </article>
          </div>
          <div v-else class="path-flow path-flow--ghost">
            <article
              v-for="(node, index) in defaultPathNodes"
              :key="node.title"
              class="path-node"
            >
              <span>{{ index + 1 }}</span>
              <strong>{{ node.title }}</strong>
              <small>{{ node.minutes }}</small>
            </article>
          </div>
          <p class="path-note">生成资源包后将为你匹配完整学习路径</p>
        </div>
      </aside>
    </section>

  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import axios from 'axios';
  import { getClassroomCourse } from '@/data/classroomCourses';
  import { fetchLearningReport, LearningReport } from '@/api/rag';
  import {
    analyzeImageProblem,
    generateResourcePackage as generateWorkshopResourcePackage,
    gradeResourceExercise,
    ImageAnalyzeResponse,
    ResourceDifficulty,
    ResourceItem,
    ResourcePackageResponse,
  } from '@/api/resource-workshop';
  import {
    generateResourcePackage as generateDownloadableResourcePackage,
    type GeneratedResourceArtifact,
    type ResourceGenerationResponse,
    type ResourceKind,
  } from '@/api/resource-generation';
  import { getToken } from '@/utils/auth';
  import { renderMarkdown } from '@/utils/markdown';

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
  const packageResult = ref<ResourcePackageResponse | null>(null);
  const downloadablePackage = ref<ResourceGenerationResponse | null>(null);
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
  }>({
    subject: '',
    topic: '',
    goal: '',
    difficulty: 'auto',
    minutes: 45,
  });

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

  const agentStageNodes = computed(() => {
    if (packageResult.value?.agent_steps?.length) {
      return packageResult.value.agent_steps.map((step, index) => ({
        key: step.agent || `step-${index}`,
        label: step.label,
        sub: step.message,
        message: step.message,
        status: (step.status || 'done') as
          | 'idle'
          | 'running'
          | 'done'
          | 'error',
      }));
    }
    if (loadingPackage.value) {
      return [
        {
          key: 'profile',
          label: '学习画像分析师',
          status: 'running' as const,
          sub: '读取画像…',
        },
        { key: 'retrieval', label: '课程证据检索员', status: 'idle' as const },
        { key: 'content', label: '内容生成专员', status: 'idle' as const },
        { key: 'safety', label: '事实审查员', status: 'idle' as const },
        { key: 'assembler', label: '资源组装专员', status: 'idle' as const },
      ];
    }
    return [
      {
        key: 'profile',
        label: '学习画像分析师',
        status: 'idle' as const,
        sub: '点击生成启动',
      },
      { key: 'retrieval', label: '课程证据检索员', status: 'idle' as const },
      { key: 'content', label: '内容生成专员', status: 'idle' as const },
      { key: 'safety', label: '事实审查员', status: 'idle' as const },
      { key: 'assembler', label: '资源组装专员', status: 'idle' as const },
    ];
  });

  const mode = computed(() => String(route.name || 'ResourcePackageBuilder'));
  const isUnifiedWorkbench = computed(
    () => mode.value === 'CourseResourceGeneration'
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
    return isUnifiedWorkbench.value ? 'AI画像驱动资源工坊' : '资源包生成';
  });
  const currentPageDescription = computed(() => {
    if (isExerciseMode.value) {
      return '围绕指定课程与知识点批改学生作答，给出反馈并同步更新学习画像。';
    }
    if (isImageMode.value) {
      return '上传题目图片并补充题干信息，识别题意后生成解题提示、步骤与图解。';
    }
    return '基于学生画像、当前目标和薄弱点，生成讲解文档、思维导图、练习题、阅读材料、实操案例与数字人脚本，并串联学习路径。';
  });
  const currentModeCaption = computed(() => {
    if (isExerciseMode.value) return '掌握度闭环';
    if (isImageMode.value) return '多模态题解';
    return '正式资源生成';
  });
  const heroHighlights = computed(() => {
    if (isExerciseMode.value) {
      return [
        { label: '结果输出', value: '评分、反馈、追练建议' },
        { label: '联动更新', value: '掌握度即时回写' },
        { label: '适用场景', value: '课堂练习与课后作业' },
      ];
    }
    if (isImageMode.value) {
      return [
        { label: '输入方式', value: '题目图片与补充题干' },
        { label: '结果输出', value: '识别文本、图解、步骤讲解' },
        { label: '适用场景', value: '板书拍照与试题截图' },
      ];
    }
    return [
      { label: '资源范围', value: '讲解、练习、案例、脚本' },
      { label: '编排依据', value: '画像、目标、薄弱点联动' },
      { label: '结果组织', value: '资源包与学习路径同步生成' },
    ];
  });

  const weakPoints = computed(
    () => report.value?.weak_points?.slice(0, 6) || []
  );

  const masteryBars = computed(() =>
    Object.entries(report.value?.mastery_map || {})
      .slice(0, 6)
      .map(([topic, value]) => ({
        topic,
        value: Math.max(0, Math.min(1, Number(value) || 0)),
      }))
  );

  const profileDimensions = computed(() => {
    const behavior = report.value?.classroom_behavior_summary;
    return [
      { label: '当前目标', value: report.value?.current_goal || '—' },
      { label: '学习偏好', value: report.value?.learning_style || '—' },
      { label: '风险等级', value: riskLabel(report.value?.risk_level) },
      { label: '知识基础', value: basisLabel(masteryBars.value) },
      { label: '易错点', value: weakPoints.value[0] || '—' },
      {
        label: '课堂投入',
        value: behavior?.on_task_rate
          ? `${Math.round(behavior.on_task_rate * 100)}%`
          : '—',
      },
    ];
  });

  const pathNodes = computed(() =>
    (packageResult.value?.resources || []).map((item: ResourceItem) => ({
      title: resourceTypeLabel(item.type),
      minutes: item.estimated_minutes,
    }))
  );
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
  const defaultPathNodes = [
    { title: '基础巩固', minutes: '2 课时' },
    { title: '能力提升', minutes: '3 课时' },
    { title: '综合应用', minutes: '2 课时' },
    { title: '阶段复习', minutes: '1 课时' },
  ];
  const packageStats = computed(() => {
    if (!packageResult.value) return [];
    const totalMinutes = packageResult.value.resources.reduce(
      (sum, item) => sum + (Number(item.estimated_minutes) || 0),
      0
    );
    return [
      {
        label: '资源数量',
        value: `${packageResult.value.resources.length} 项`,
      },
      { label: '预计学习时长', value: `${totalMinutes} 分钟` },
      {
        label: '匹配依据',
        value: `${packageResult.value.personalization_basis.length} 条`,
      },
    ];
  });
  const videoScriptResource = computed(
    () =>
      packageResult.value?.resources.find(
        (item) => item.type === 'video_script'
      ) || null
  );
  const artifactStats = computed(() => {
    if (!downloadablePackage.value) return [];
    const totalSize = downloadablePackage.value.artifacts.reduce(
      (sum, item) => sum + item.file_size,
      0
    );
    return [
      { label: '真实文件', value: `${downloadablePackage.value.artifacts.length} 个` },
      { label: '下载体积', value: formatFileSize(totalSize) },
      { label: '生成方式', value: downloadablePackage.value.local_model_profile?.mode || '课程资源生成' },
    ];
  });
  const artifactKindLabel = (kind: ResourceKind) => {
    const map: Record<ResourceKind, string> = {
      lecture_markdown: '讲义 Markdown',
      lecture_pdf: '讲义 PDF',
      practice_markdown: '练习 Markdown',
      practice_pdf: '练习 PDF',
      mind_map: '思维导图',
      reading_list: '阅读清单',
      case_project: '案例项目',
      video_script: '数字人脚本',
    };
    return map[kind] || kind;
  };
  const incomingSeedSummary = computed(() => {
    const topic = String(route.query.topic || '').trim();
    const goal = String(route.query.goal || '').trim();
    const source = String(route.query.source || '').trim();
    if (!topic && !goal && !source) return '';
    const segments = [];
    if (source) segments.push(`来自 ${sourceLabel(source)}`);
    if (topic) segments.push(`主题：${topic}`);
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
        goal: `把${firstNote?.points.join('、') || '课堂笔记'}整理成复习讲义和练习`,
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
      {
        label: '识别置信度',
        value: `${Math.round(imageResult.value.confidence * 100)}%`,
      },
      { label: '图解节点', value: `${diagramNodes.value.length} 项` },
      {
        label: '解题步骤',
        value: `${imageResult.value.solution_outline.length} 步`,
      },
    ];
  });

  function hydrateFormsFromReport(snapshot: LearningReport | null) {
    if (!snapshot) return;
    const primaryWeakPoint = snapshot.weak_points?.[0] || '';
    const primaryGoal = snapshot.current_goal || '';
    const primarySubject =
      form.subject || gradeForm.subject || imageForm.subject || '';

    if (!form.topic && primaryWeakPoint) form.topic = primaryWeakPoint;
    if (!form.goal && primaryGoal) form.goal = primaryGoal;
    if (!gradeForm.topic && primaryWeakPoint)
      gradeForm.topic = primaryWeakPoint;
    if (!imageForm.subject && primarySubject)
      imageForm.subject = primarySubject;

    if (!gradeForm.subject && form.subject) gradeForm.subject = form.subject;
    if (!imageForm.subject && form.subject) imageForm.subject = form.subject;
  }

  function hydrateFormsFromRoute() {
    const seedMode = String(route.query.mode || '').trim();
    const seedSubject = String(route.query.subject || '').trim();
    const seedTopic = String(route.query.topic || '').trim();
    const seedGoal = String(route.query.goal || '').trim();
    const signature = JSON.stringify({
      seedMode,
      seedSubject,
      seedTopic,
      seedGoal,
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
    }
    if (seedGoal) {
      form.goal = seedGoal;
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

  function basisLabel(items: Array<{ value: number }>) {
    if (!items.length) return '画像构建中';
    const avg = items.reduce((sum, item) => sum + item.value, 0) / items.length;
    if (avg >= 0.75) return '较扎实';
    if (avg >= 0.55) return '中等，需要迁移训练';
    return '基础薄弱，优先补概念';
  }

  function riskLabel(level?: string) {
    const map: Record<string, string> = {
      low: '低风险',
      medium: '中风险',
      high: '高风险',
    };
    return map[level || ''] || level || '待评估';
  }

  function sourceLabel(source: string) {
    const map: Record<string, string> = {
      'classroom-notes': '课堂笔记',
      'knowledge-map': '课程图谱',
      'course-agent': '课程 Agent',
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
      video_script: '数字人脚本',
      reflection: '口头复述',
    };
    return map[type] || type;
  }

  function formatFileSize(size: number) {
    if (!Number.isFinite(size) || size <= 0) return '0 KB';
    if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  }

  function artifactDownloadUrl(artifact: GeneratedResourceArtifact) {
    const token = getToken();
    const baseURL =
      axios.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || window.location.origin;
    const baseOrigin = /^https?:\/\//.test(baseURL)
      ? new URL(baseURL).origin
      : window.location.origin;
    const url = new URL(artifact.download_url, baseOrigin);
    if (token) url.searchParams.set('token', token);
    return url.toString();
  }

  function downloadArtifact(artifact: GeneratedResourceArtifact) {
    window.open(artifactDownloadUrl(artifact), '_blank', 'noopener,noreferrer');
  }

  function productionResourceTypes(): ResourceKind[] {
    return [
      'lecture_markdown',
      'lecture_pdf',
      'practice_markdown',
      'practice_pdf',
      'mind_map',
      'reading_list',
      'case_project',
      'video_script',
    ];
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
      ...packageResult.value.resources.flatMap((item, index) => [
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

  async function copyResourceItem(item: ResourceItem) {
    try {
      await copyTextPayload(
        `${item.title}\n${item.description}\n\n${item.content_preview}`,
        '资源内容已复制'
      );
    } catch {
      Message.error('复制失败，请检查浏览器剪贴板权限');
    }
  }

  function downloadPackageSummary() {
    if (!packageResult.value) return;
    const blob = new Blob([buildPackageExportText()], {
      type: 'text/plain;charset=utf-8',
    });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${packageResult.value.topic || '学习资源包'}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    Message.success('资源包文本已下载');
  }

  function goToDigitalHumanStudio(resource?: ResourceItem) {
    const payload = resource || videoScriptResource.value;
    if (!payload) {
      Message.warning('当前资源包里还没有数字人脚本');
      return;
    }
    router.push({
      path: '/digital-human/text-to-video',
      query: {
        source: 'resource-workshop',
        title: payload.title,
        script: payload.content_preview,
      },
    });
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

  async function handleGeneratePackage() {
    if (!form.subject.trim()) {
      Message.warning('请先填写课程名称');
      return;
    }
    loadingPackage.value = true;
    downloadablePackage.value = null;
    try {
      const difficulty =
        form.difficulty === 'auto' ? 'standard' : form.difficulty;
      const [previewResult, artifactResult] = await Promise.allSettled([
        generateWorkshopResourcePackage({
          ...form,
          resource_count: 6,
        }),
        generateDownloadableResourcePackage({
          course_id: activeCourse.value?.id,
          subject: form.subject,
          topic: form.topic || weakPoints.value[0] || '课程重点',
          learning_goal: form.goal || '生成可下载的个性化课程资源包',
          difficulty,
          target_minutes: form.minutes,
          resource_types: productionResourceTypes(),
          use_web_search: false,
        }),
      ]);

      if (previewResult.status === 'fulfilled') {
        packageResult.value = previewResult.value;
      }
      if (artifactResult.status === 'fulfilled') {
        downloadablePackage.value = artifactResult.value;
      }
      if (previewResult.status === 'rejected' && artifactResult.status === 'rejected') {
        throw previewResult.reason || artifactResult.reason;
      }

      const subject =
        packageResult.value?.subject || downloadablePackage.value?.subject || form.subject;
      const topic =
        packageResult.value?.topic || downloadablePackage.value?.topic || form.topic;
      gradeForm.subject = subject;
      gradeForm.topic = topic;
      imageForm.subject = subject;
      if (!imageForm.question_text.trim()) {
        imageForm.question_text = `请结合 ${topic} 的核心概念，对题目进行结构化讲解。`;
      }
      Message.success(
        downloadablePackage.value
          ? '资源包与可下载文件已生成'
          : '资源包预览已生成'
      );
    } catch (error) {
      Message.error('资源包生成失败，请检查后端服务');
    } finally {
      loadingPackage.value = false;
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
      Message.success('批改完成，画像已更新');
    } catch (error) {
      Message.error('批改失败，请检查后端服务');
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
      Message.error('图片分析失败，请检查多模态配置');
    } finally {
      loadingImage.value = false;
    }
  }

  onMounted(() => {
    hydrateFormsFromRoute();
    loadProfile(false);
  });

  watch(
    () => route.name,
    (name) => {
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

<style scoped>
  .resource-workshop-page {
    --workshop-brand: #5368f5;
    --workshop-ink: #182448;
    --workshop-muted: #7180a2;
    --workshop-line: #e4e9f5;
    --workshop-surface: rgba(255, 255, 255, 0.96);
    position: relative;
    min-height: calc(100vh - 64px);
    padding: 0 18px 40px;
    overflow: hidden;
    color: var(--workshop-ink);
    background: radial-gradient(
        circle at 78% 8%,
        rgba(112, 145, 255, 0.09),
        transparent 26%
      ),
      linear-gradient(180deg, #f8faff 0%, #f5f7fc 100%);
  }

  .resource-workshop-page::before {
    position: absolute;
    inset: 54px 0 auto;
    height: 360px;
    pointer-events: none;
    content: '';
    background-image: radial-gradient(
      rgba(92, 111, 207, 0.09) 0.7px,
      transparent 0.7px
    );
    background-size: 18px 18px;
    mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.55), transparent);
  }

  .workshop-hero,
  .mode-dock,
  .workbench-grid {
    position: relative;
    z-index: 1;
    width: min(100%, 1560px);
    margin-right: auto;
    margin-left: auto;
  }

  .workshop-hero {
    display: grid;
    grid-template-columns: 180px minmax(0, 1fr) 300px;
    gap: 24px;
    align-items: center;
    min-height: 226px;
    margin-top: 10px;
    padding: 22px 24px;
    overflow: hidden;
    background: radial-gradient(
        circle at 7% 78%,
        rgba(116, 156, 255, 0.25),
        transparent 25%
      ),
      linear-gradient(108deg, #e7ecff 0%, #f2f4ff 47%, #e9f5ff 100%);
    border: 1px solid #dce4fb;
    border-radius: 14px;
    box-shadow: 0 14px 34px rgba(57, 72, 142, 0.08);
  }

  .workshop-hero::after {
    position: absolute;
    top: -80px;
    right: 14%;
    width: 310px;
    height: 310px;
    pointer-events: none;
    content: '';
    border: 1px solid rgba(255, 255, 255, 0.7);
    border-radius: 50%;
    box-shadow: 0 0 0 42px rgba(255, 255, 255, 0.14),
      0 0 0 90px rgba(255, 255, 255, 0.08);
  }

  .hero-visual {
    position: relative;
    display: grid;
    height: 180px;
    place-items: center;
    perspective: 760px;
  }

  .hero-visual::after {
    position: absolute;
    bottom: 4px;
    width: 150px;
    height: 28px;
    content: '';
    background: rgba(73, 89, 190, 0.24);
    border-radius: 50%;
    filter: blur(14px);
  }

  .folder-box {
    position: relative;
    z-index: 1;
    width: 126px;
    height: 102px;
    transform: rotateY(-12deg) rotateX(6deg);
    animation: folder-float 5s ease-in-out infinite;
  }

  .folder-lid {
    position: absolute;
    top: -18px;
    left: 6px;
    width: 72px;
    height: 38px;
    background: linear-gradient(145deg, #8f9cff, #586af5);
    border-radius: 16px 16px 5px 5px;
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.35);
  }

  .folder-body {
    position: absolute;
    inset: 0;
    overflow: visible;
    background: linear-gradient(145deg, #7689ff 0%, #4f5fe4 58%, #3948c2 100%);
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 16px 22px 20px 18px;
    box-shadow: inset 8px 8px 14px rgba(255, 255, 255, 0.16),
      0 20px 34px rgba(58, 69, 180, 0.35);
    transform: skewY(-2deg);
  }

  .folder-sheet {
    position: absolute;
    bottom: 36px;
    width: 66px;
    height: 90px;
    border: 1px solid rgba(255, 255, 255, 0.72);
    border-radius: 10px;
    box-shadow: 0 12px 24px rgba(65, 74, 167, 0.24);
  }

  .folder-sheet--one {
    left: 22px;
    background: linear-gradient(#d4dcff 0 0) 15px 22px / 34px 4px no-repeat,
      linear-gradient(#d4dcff 0 0) 15px 34px / 27px 4px no-repeat,
      linear-gradient(155deg, #fff, #dce5ff);
    transform: rotate(-8deg);
  }

  .folder-sheet--two {
    right: 7px;
    bottom: 46px;
    display: grid;
    width: 58px;
    height: 68px;
    place-items: center;
    color: #fff;
    font-size: 24px;
    font-weight: 900;
    background: linear-gradient(145deg, #ad6bff, #6754f7);
    transform: rotate(8deg);
  }

  .hero-main {
    min-width: 0;
  }

  .hero-title-line {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .hero-title-line h1 {
    margin: 0;
    color: #172248;
    font-size: clamp(27px, 2vw, 34px);
    font-weight: 800;
    letter-spacing: -0.03em;
  }

  .hero-title-line > span {
    padding: 5px 12px;
    color: #5364e8;
    font-size: 12px;
    font-weight: 700;
    background: rgba(239, 241, 255, 0.84);
    border: 1px solid #bdc8ff;
    border-radius: 999px;
  }

  .hero-main > p {
    max-width: 720px;
    margin: 10px 0 18px;
    color: #617092;
    font-size: 14px;
    line-height: 1.75;
  }

  .hero-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .hero-metric {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 10px;
    min-height: 78px;
    padding: 13px 14px;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(218, 225, 246, 0.95);
    border-radius: 10px;
    box-shadow: inset 0 1px rgba(255, 255, 255, 0.9);
  }

  .metric-icon {
    position: relative;
    display: inline-grid;
    width: 30px;
    height: 30px;
    place-items: center;
    background: linear-gradient(145deg, #eef1ff, #d9e1ff);
    border-radius: 9px;
  }

  .metric-icon::before,
  .metric-icon::after {
    position: absolute;
    content: '';
    border: 2px solid #6475ed;
    border-radius: 2px;
  }

  .metric-icon::before {
    width: 13px;
    height: 16px;
  }

  .metric-icon::after {
    width: 7px;
    height: 2px;
    border-width: 2px 0 0;
  }

  .hero-metric strong {
    display: block;
    color: #3d4a74;
    font-size: 13px;
  }

  .hero-metric p {
    margin: 5px 0 0;
    color: #1d294e;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.45;
  }

  .profile-state {
    min-width: 0;
    padding: 20px;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(218, 225, 246, 0.96);
    border-radius: 12px;
    box-shadow: inset 0 1px rgba(255, 255, 255, 0.95);
  }

  .state-label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #667392;
    font-size: 12px;
    font-weight: 600;
  }

  .state-label i {
    position: relative;
    width: 14px;
    height: 14px;
    background: #42c7a2;
    border-radius: 50%;
  }

  .state-label i::after {
    position: absolute;
    top: 3px;
    left: 4px;
    width: 5px;
    height: 3px;
    content: '';
    border-bottom: 2px solid #fff;
    border-left: 2px solid #fff;
    transform: rotate(-45deg);
  }

  .profile-state > strong {
    display: block;
    margin-top: 15px;
    color: #172248;
    font-size: 22px;
  }

  .profile-state > p {
    min-height: 38px;
    margin: 8px 0 14px;
    overflow: hidden;
    color: #7a86a3;
    font-size: 12px;
    line-height: 1.55;
    text-overflow: ellipsis;
  }

  .profile-state :deep(.arco-btn) {
    float: right;
    min-width: 120px;
    border-radius: 7px;
    box-shadow: 0 8px 18px rgba(83, 104, 245, 0.22);
  }

  .mode-dock {
    display: grid;
    grid-template-columns: 94px repeat(3, minmax(0, 1fr));
    gap: 16px;
    align-items: center;
    margin-top: 12px;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--workshop-line);
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(35, 48, 98, 0.04);
  }

  .mode-dock__label {
    color: #3e4b70;
    font-size: 14px;
    font-weight: 800;
  }

  .mode-card {
    position: relative;
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr) 24px;
    gap: 12px;
    align-items: center;
    min-width: 0;
    min-height: 64px;
    padding: 8px 12px;
    text-align: left;
    background: #fff;
    border: 1px solid #e2e7f2;
    border-radius: 9px;
    cursor: pointer;
    transition: transform 180ms ease, border-color 180ms ease,
      box-shadow 180ms ease;
  }

  .mode-card:hover {
    border-color: #b9c4ff;
    transform: translateY(-1px);
  }

  .mode-card--active {
    background: linear-gradient(135deg, #fff 0%, #f5f7ff 100%);
    border-color: #6274f6;
    box-shadow: 0 8px 20px rgba(83, 104, 245, 0.14);
  }

  .mode-card__icon {
    display: grid;
    width: 40px;
    height: 40px;
    place-items: center;
    color: #5368f5;
    font-size: 13px;
    font-weight: 900;
    background: linear-gradient(145deg, #f0f2ff, #dde4ff);
    border-radius: 12px;
  }

  .mode-card__copy {
    min-width: 0;
  }

  .mode-card__copy strong,
  .mode-card__copy em {
    display: block;
  }

  .mode-card__copy strong {
    color: #263253;
    font-size: 14px;
  }

  .mode-card__copy em {
    margin-top: 3px;
    overflow: hidden;
    color: #8690a8;
    font-size: 11px;
    font-style: normal;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mode-card__check {
    display: grid;
    width: 20px;
    height: 20px;
    place-items: center;
    color: #fff;
    font-size: 11px;
    font-weight: 800;
    background: #5368f5;
    border-radius: 50%;
  }

  .workbench-grid {
    display: grid;
    grid-template-columns: minmax(260px, 0.78fr) minmax(520px, 1.75fr) minmax(
        280px,
        0.92fr
      );
    gap: 14px;
    align-items: start;
    margin-top: 12px;
  }

  .settings-column,
  .result-column,
  .insight-column {
    display: grid;
    min-width: 0;
    gap: 14px;
  }

  .work-card {
    min-width: 0;
    padding: 16px;
    background: var(--workshop-surface);
    border: 1px solid var(--workshop-line);
    border-radius: 12px;
    box-shadow: 0 8px 26px rgba(34, 48, 98, 0.045);
  }

  .settings-card {
    min-height: 492px;
  }

  .flow-card {
    min-height: 178px;
  }

  .result-preview-card {
    min-height: 300px;
  }

  .card-heading,
  .card-heading > div {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 9px;
  }

  .card-heading {
    margin-bottom: 17px;
  }

  .card-heading--split {
    justify-content: space-between;
  }

  .card-heading h2 {
    margin: 0;
    overflow: hidden;
    color: #263253;
    font-size: 14px;
    font-weight: 800;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-badge {
    display: grid;
    width: 26px;
    height: 26px;
    flex: 0 0 26px;
    place-items: center;
    color: #fff;
    font-size: 12px;
    font-weight: 800;
    background: linear-gradient(145deg, #667af8, #4658dc);
    border-radius: 50%;
    box-shadow: 0 5px 12px rgba(83, 104, 245, 0.3);
  }

  .muted-pill {
    padding: 5px 10px;
    color: #9aa3b8;
    font-size: 10px;
    background: #f5f6fa;
    border-radius: 999px;
  }

  .text-link {
    padding: 0;
    color: #919bb2;
    font-size: 11px;
    background: none;
    border: none;
    cursor: pointer;
  }

  .seed-banner {
    display: grid;
    gap: 4px;
    margin-bottom: 13px;
    padding: 10px 12px;
    background: #f5f7ff;
    border: 1px solid #e0e5fb;
    border-radius: 8px;
  }

  .seed-banner span {
    color: #909bb5;
    font-size: 10px;
  }

  .seed-banner strong {
    color: #4f5f8d;
    font-size: 11px;
    line-height: 1.45;
  }

  .course-seed-card {
    display: grid;
    gap: 10px;
    margin-bottom: 14px;
    padding: 12px;
    background:
      radial-gradient(circle at right top, rgba(83, 104, 245, 0.12), transparent 36%),
      #fff;
    border: 1px solid #e0e6f6;
    border-radius: 10px;
  }

  .course-seed-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .course-seed-card__head span {
    color: #5368f5;
    font-size: 10px;
    font-weight: 800;
  }

  .course-seed-card__head strong {
    min-width: 0;
    overflow: hidden;
    color: #293655;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .course-seed-card p {
    margin: 0;
    color: #7d879d;
    font-size: 11px;
    line-height: 1.65;
  }

  .seed-links {
    display: grid;
    gap: 6px;
  }

  .seed-links button {
    display: grid;
    gap: 3px;
    padding: 9px 10px;
    color: #66728c;
    text-align: left;
    background: #f8faff;
    border: 1px solid #e6ebf6;
    border-radius: 8px;
    cursor: pointer;
  }

  .seed-links button:hover {
    color: #5368f5;
    border-color: #d7defc;
  }

  .seed-links strong,
  .seed-links small {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .seed-links strong {
    color: #34405c;
    font-size: 11px;
  }

  .seed-links small {
    color: #8d98ad;
    font-size: 9px;
  }

  .compact-form :deep(.arco-form-item) {
    margin-bottom: 14px;
  }

  .compact-form :deep(.arco-form-item-label-col > label) {
    color: #53607e;
    font-size: 12px;
    font-weight: 700;
  }

  .compact-form :deep(.arco-input-wrapper),
  .compact-form :deep(.arco-select-view-single),
  .compact-form :deep(.arco-input-number),
  .compact-form :deep(.arco-textarea-wrapper) {
    min-height: 38px;
    background: #fbfcff;
    border-color: #e2e7f1;
    border-radius: 7px;
  }

  .compact-form :deep(.arco-input-number) {
    width: 100%;
  }

  .form-two {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .primary-action {
    height: 44px;
    margin-top: 2px;
    font-size: 15px;
    font-weight: 700;
    background: linear-gradient(100deg, #526ef6, #8b4ef0);
    border: none;
    border-radius: 7px;
    box-shadow: 0 10px 20px rgba(101, 82, 236, 0.2);
  }

  .upload-tile {
    display: grid;
    gap: 5px;
    margin-bottom: 14px;
    padding: 24px 14px;
    text-align: center;
    background: #fafbff;
    border: 1px dashed #b9c5ed;
    border-radius: 10px;
    cursor: pointer;
  }

  .upload-tile input {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    opacity: 0;
  }

  .upload-tile strong {
    color: #5368e9;
    font-size: 13px;
  }

  .upload-tile span {
    color: #929db4;
    font-size: 11px;
  }

  .flow-card :deep(.agent-stage) {
    padding: 6px 0 0;
  }

  .flow-card :deep(.agent-stage__node-icon) {
    width: 38px;
    height: 38px;
    background: linear-gradient(145deg, #f3f5ff, #e2e8ff);
    border: 1px solid #d7defa;
    box-shadow: 0 5px 14px rgba(65, 84, 190, 0.1);
  }

  .flow-card :deep(.agent-stage__node-label) {
    color: #405077;
    font-size: 11px;
  }

  .flow-card :deep(.agent-stage__node-sub) {
    max-width: 110px;
    color: #96a0b5;
  }

  .flow-card :deep(.agent-stage__line) {
    stroke: #cdd5eb;
    stroke-dasharray: 4 4;
  }

  .flow-card :deep(.agent-stage__message) {
    padding: 6px 10px;
    font-family: inherit;
    background: #f7f8fc;
  }

  .package-summary,
  .resource-card__top,
  .result-meta,
  .score-line,
  .mastery-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .package-summary h3 {
    margin: 0;
    color: #263253;
    font-size: 16px;
  }

  .package-summary p {
    margin: 5px 0 0;
    color: #7d88a3;
    font-size: 12px;
  }

  .package-actions,
  .basis-row,
  .tag-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 12px;
  }

  .artifact-download-panel {
    margin-top: 14px;
    padding: 13px;
    border: 1px solid #dfe7f3;
    border-radius: 10px;
    background: #f8fbff;
  }

  .artifact-download-panel__head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 360px;
    gap: 14px;
    align-items: start;
  }

  .artifact-download-panel__head > div:first-child strong,
  .artifact-download-panel__head > div:first-child span {
    display: block;
  }

  .artifact-download-panel__head > div:first-child strong {
    color: #263253;
    font-size: 14px;
  }

  .artifact-download-panel__head > div:first-child span {
    margin-top: 4px;
    color: #75829a;
    font-size: 11px;
  }

  .artifact-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
  }

  .artifact-stats article {
    padding: 8px;
    border: 1px solid #e3e9f4;
    border-radius: 8px;
    background: #fff;
  }

  .artifact-stats span,
  .artifact-stats strong {
    display: block;
  }

  .artifact-stats span {
    color: #8b96ad;
    font-size: 9px;
  }

  .artifact-stats strong {
    margin-top: 3px;
    color: #34426a;
    font-size: 11px;
  }

  .artifact-audit-panel {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
    gap: 10px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #e5ebf5;
  }

  .artifact-audit-panel section {
    min-width: 0;
    padding: 10px 11px;
    border: 1px solid #e4eaf6;
    border-radius: 8px;
    background: #fff;
  }

  .artifact-audit-panel strong {
    display: block;
    margin-bottom: 7px;
    color: #2c385a;
    font-size: 12px;
  }

  .artifact-audit-panel ul,
  .artifact-audit-panel ol {
    display: grid;
    gap: 5px;
    margin: 0;
    padding-left: 16px;
    color: #68758f;
    font-size: 11px;
    line-height: 1.55;
  }

  .artifact-audit-panel li::marker {
    color: #5368f5;
    font-weight: 800;
  }

  .artifact-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 12px;
  }

  .artifact-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    padding: 12px;
    border: 1px solid #e2e9f4;
    border-radius: 9px;
    background: #fff;
  }

  .artifact-card span,
  .artifact-card strong,
  .artifact-card small {
    display: block;
  }

  .artifact-card span {
    color: #5368e9;
    font-size: 10px;
    font-weight: 700;
  }

  .artifact-card strong {
    margin-top: 4px;
    color: #263253;
    font-size: 13px;
  }

  .artifact-card small {
    margin-top: 4px;
    color: #8b96ad;
    font-size: 10px;
    word-break: break-all;
  }

  .artifact-card p {
    grid-column: 1 / -1;
    margin: 2px 0 0;
    color: #728096;
    font-size: 11px;
    line-height: 1.65;
  }

  .artifact-card button {
    height: 30px;
    padding: 0 10px;
    border: 0;
    border-radius: 7px;
    color: #fff;
    background: #5367f8;
    font-size: 11px;
    cursor: pointer;
    white-space: nowrap;
  }

  .result-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
    margin: 14px 0;
  }

  .result-stats article {
    padding: 11px 12px;
    background: #f7f9ff;
    border: 1px solid #e6eaf5;
    border-radius: 8px;
  }

  .result-stats span,
  .result-stats strong {
    display: block;
  }

  .result-stats span {
    color: #8b96ad;
    font-size: 10px;
  }

  .result-stats strong {
    margin-top: 5px;
    color: #34426a;
    font-size: 13px;
  }

  .resource-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 13px;
  }

  .resource-card {
    min-width: 0;
    padding: 13px;
    background: #fff;
    border: 1px solid #e4e9f3;
    border-radius: 9px;
  }

  .resource-card__top small {
    color: #9aa4b8;
    font-size: 10px;
  }

  .resource-kind {
    padding: 3px 8px;
    color: #5368e9;
    font-size: 10px;
    font-weight: 700;
    background: #eef1ff;
    border-radius: 999px;
  }

  .resource-card h4 {
    margin: 10px 0 6px;
    color: #2e3a5d;
    font-size: 13px;
  }

  .resource-card > p {
    margin: 0;
    color: #818ca5;
    font-size: 11px;
    line-height: 1.55;
  }

  .preview-text {
    max-height: 96px;
    margin-top: 9px;
    padding: 9px 10px;
    overflow: auto;
    color: #52607f;
    font-size: 11px;
    line-height: 1.55;
    background: #f8f9fd;
    border-radius: 7px;
  }

  .resource-card__actions {
    display: flex;
    gap: 7px;
    margin-top: 9px;
  }

  .empty-preview {
    display: grid;
    min-height: 240px;
    place-items: center;
    align-content: center;
    padding: 12px 0 2px;
    text-align: center;
  }

  .empty-preview--compact {
    min-height: 340px;
  }

  .empty-folder {
    position: relative;
    width: 62px;
    height: 46px;
    margin-bottom: 10px;
    background: linear-gradient(145deg, #dce3fb, #b9c7ed);
    border-radius: 7px 11px 9px 9px;
    box-shadow: 0 12px 22px rgba(84, 102, 166, 0.14);
  }

  .empty-folder::before {
    position: absolute;
    top: -9px;
    left: 6px;
    width: 28px;
    height: 14px;
    content: '';
    background: #ced8f6;
    border-radius: 6px 6px 0 0;
  }

  .empty-folder::after {
    position: absolute;
    top: -25px;
    left: 20px;
    width: 31px;
    height: 39px;
    content: '';
    background: linear-gradient(#b3c0e6 0 0) 7px 10px / 17px 2px no-repeat,
      linear-gradient(#b3c0e6 0 0) 7px 17px / 13px 2px no-repeat, #f5f7ff;
    border: 1px solid #d5def5;
    border-radius: 4px;
    transform: rotate(6deg);
  }

  .empty-preview > strong {
    color: #5c6886;
    font-size: 13px;
  }

  .empty-preview > p {
    margin: 8px 0 16px;
    color: #9aa4b7;
    font-size: 11px;
  }

  .preview-resource-row {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 9px;
    width: 100%;
  }

  .preview-resource {
    display: grid;
    min-width: 0;
    min-height: 105px;
    padding: 11px 9px;
    place-items: start;
    text-align: left;
    border: 1px solid currentColor;
    border-radius: 8px;
  }

  .preview-resource > span {
    display: grid;
    width: 30px;
    height: 30px;
    place-items: center;
    color: currentColor;
    font-size: 11px;
    font-weight: 900;
    background: rgba(255, 255, 255, 0.75);
    border-radius: 7px;
  }

  .preview-resource strong {
    margin-top: 7px;
    color: #3c4867;
    font-size: 11px;
  }

  .preview-resource small {
    margin-top: 3px;
    color: #929bae;
    font-size: 9px;
    line-height: 1.4;
  }

  .preview-resource--blue {
    color: #6385ec;
    background: #f1f5ff;
  }

  .preview-resource--green {
    color: #35ad79;
    background: #f0fbf6;
  }

  .preview-resource--violet {
    color: #8b68ed;
    background: #f7f2ff;
  }

  .preview-resource--orange {
    color: #e79143;
    background: #fff7ef;
  }

  .preview-resource--cyan {
    color: #35aeb0;
    background: #eefafb;
  }

  .weak-title {
    margin: 16px 0 8px;
    color: #64708e;
    font-size: 11px;
    font-weight: 800;
  }

  .weak-title:first-child {
    margin-top: 0;
  }

  .goal-line {
    padding: 10px 11px;
    color: #526084;
    font-size: 11px;
    line-height: 1.5;
    background: #f8f9fd;
    border-radius: 7px;
  }

  .recommend-list,
  .plain-list {
    margin: 0;
    padding-left: 18px;
    color: #68748e;
    font-size: 11px;
    line-height: 1.9;
  }

  .recommend-list li::marker {
    color: #6377ed;
  }

  .mini-empty {
    padding: 34px 12px;
    color: #9aa4b7;
    font-size: 11px;
    text-align: center;
  }

  .path-flow {
    position: relative;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 7px;
  }

  .path-flow::before {
    position: absolute;
    top: 19px;
    right: 11%;
    left: 11%;
    height: 1px;
    content: '';
    background: repeating-linear-gradient(
      90deg,
      #c9d1eb 0 4px,
      transparent 4px 8px
    );
  }

  .path-node {
    position: relative;
    z-index: 1;
    min-width: 0;
    text-align: center;
  }

  .path-node > span {
    display: grid;
    width: 38px;
    height: 38px;
    margin: 0 auto 8px;
    place-items: center;
    color: #5368ef;
    font-size: 11px;
    font-weight: 800;
    background: linear-gradient(145deg, #f2f4ff, #e0e7ff);
    border: 1px solid #d8e0fa;
    border-radius: 50%;
  }

  .path-node strong,
  .path-node small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .path-node strong {
    color: #52607e;
    font-size: 10px;
  }

  .path-node small {
    margin-top: 4px;
    color: #a0a8b9;
    font-size: 9px;
  }

  .path-flow--ghost {
    opacity: 0.9;
  }

  .path-note {
    margin: 14px 0 0;
    color: #9ba4b6;
    font-size: 10px;
    text-align: center;
  }

  .score-line {
    justify-content: flex-start;
    margin: 14px 0;
  }

  .score-line strong {
    color: #5368ef;
    font-size: 34px;
  }

  .mastery-head {
    margin: 15px 0 7px;
    color: #6c7894;
    font-size: 11px;
  }

  .grade-result > p {
    color: #5f6d89;
    font-size: 12px;
    line-height: 1.7;
  }

  .image-result {
    min-width: 0;
  }

  .extracted-text,
  .answer-box {
    margin-top: 12px;
    padding: 12px;
    color: #53607c;
    font-size: 12px;
    line-height: 1.7;
    background: #f8f9fd;
    border: 1px solid #e6eaf3;
    border-radius: 8px;
  }

  .diagram-flow {
    display: flex;
    gap: 7px;
    flex-wrap: wrap;
    margin-top: 12px;
  }

  .diagram-flow span {
    padding: 5px 9px;
    color: #5268e9;
    font-size: 10px;
    background: #eef1ff;
    border-radius: 999px;
  }

  @keyframes folder-float {
    0%,
    100% {
      transform: rotateY(-12deg) rotateX(6deg) translateY(0);
    }

    50% {
      transform: rotateY(-8deg) rotateX(3deg) translateY(-7px);
    }
  }

  @media (max-width: 1280px) {
    .workshop-hero {
      grid-template-columns: 140px minmax(0, 1fr) 250px;
    }

    .workbench-grid {
      grid-template-columns: minmax(250px, 0.8fr) minmax(480px, 1.55fr);
    }

    .insight-column {
      grid-column: 1 / -1;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 980px) {
    .resource-workshop-page {
      padding-right: 12px;
      padding-left: 12px;
    }

    .workshop-hero {
      grid-template-columns: 110px minmax(0, 1fr);
    }

    .profile-state {
      grid-column: 1 / -1;
    }

    .hero-metrics {
      grid-template-columns: 1fr;
    }

    .mode-dock {
      grid-template-columns: 1fr;
    }

    .mode-dock__label {
      padding-left: 4px;
    }

    .workbench-grid {
      grid-template-columns: 1fr;
    }

    .insight-column {
      grid-column: auto;
    }
  }

  @media (max-width: 680px) {
    .workshop-hero {
      grid-template-columns: 1fr;
      padding: 18px;
    }

    .artifact-audit-panel {
      grid-template-columns: 1fr;
    }

    .hero-visual {
      display: none;
    }

    .hero-metrics,
    .insight-column,
    .form-two,
    .artifact-grid,
    .artifact-download-panel__head,
    .artifact-stats,
    .resource-grid,
    .result-stats {
      grid-template-columns: 1fr;
    }

    .mode-card {
      grid-template-columns: 40px minmax(0, 1fr) 22px;
    }

    .preview-resource-row {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .preview-resource:last-child {
      grid-column: 1 / -1;
    }

}
</style>
