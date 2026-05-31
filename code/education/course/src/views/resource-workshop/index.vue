<template>
  <div class="container">
    <Breadcrumb :items="['学习资源工坊', currentPageTitle]" />

    <section class="hero-band">
      <div class="hero-copy">
        <div class="eyebrow">学习资源工坊</div>
        <div class="hero-title-row">
          <h2>{{ currentPageTitle }}</h2>
          <span class="hero-scene">{{ currentModeCaption }}</span>
        </div>
        <p>{{ currentPageDescription }}</p>
        <div class="hero-highlights">
          <div
            v-for="item in heroHighlights"
            :key="item.label"
            class="hero-highlight"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
        <div v-if="isUnifiedWorkbench" class="mode-switch-wrap">
          <div class="section-note section-note--light">
            <strong>工作模式切换</strong>
            <span>同一页面内完成资源生成、练习批改与图像题解，结果区会随模式联动切换。</span>
          </div>
          <div class="mode-switch" role="tablist" aria-label="工坊模式">
            <button
              v-for="item in modeOptions"
              :key="item.value"
              type="button"
              class="mode-switch__item"
              :class="{ 'mode-switch__item--active': activeMode === item.value }"
              @click="activeMode = item.value"
            >
              <em>{{ item.badge }}</em>
              <strong>{{ item.label }}</strong>
              <span>{{ item.description }}</span>
            </button>
          </div>
        </div>
      </div>
      <div class="hero-actions">
        <div v-if="report" class="hero-status">
          <span class="hero-status__label">学习画像状态</span>
          <strong>{{ riskLabel(report.risk_level) }}</strong>
          <small>{{ report.current_goal || '会根据最新互动持续更新' }}</small>
          <div class="hero-status__meta">
            <div class="hero-status__meta-item">
              <span>薄弱点</span>
              <strong>{{ weakPoints.length || 0 }} 项</strong>
            </div>
            <div class="hero-status__meta-item">
              <span>掌握主题</span>
              <strong>{{ masteryBars.length || 0 }} 项</strong>
            </div>
          </div>
        </div>
        <div v-else class="hero-status hero-status--empty">
          <span class="hero-status__label">学习画像状态</span>
          <strong>待生成</strong>
          <small>首次进入可先刷新画像，系统会自动回填目标、薄弱点与学习背景。</small>
        </div>
        <a-button type="primary" :loading="loadingReport" @click="loadProfile(true)">
          刷新学习画像
        </a-button>
      </div>
    </section>

    <a-row :gutter="16">
      <a-col :xs="24" :xl="8">
        <a-card class="panel-card" title="学习画像与生成依据">
          <a-spin :loading="loadingReport" style="width: 100%">
            <template v-if="report">
              <div class="card-intro">
                当前资源编排会优先参考学习目标、知识短板与课堂投入度，作为正式生成的依据。
              </div>
              <div class="profile-summary">{{ report.summary }}</div>
              <div class="profile-grid">
                <div v-for="item in profileDimensions" :key="item.label" class="profile-dim">
                  <span class="dim-label">{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
              <div class="mastery-list">
                <div
                  v-for="item in masteryBars"
                  :key="item.topic"
                  class="mastery-row"
                >
                  <div class="mastery-head">
                    <span>{{ item.topic }}</span>
                    <span>{{ Math.round(item.value * 100) }}%</span>
                  </div>
                  <a-progress
                    :percent="Math.round(item.value * 100)"
                    size="small"
                    :show-text="false"
                  />
                </div>
              </div>
              <div class="tag-row">
                <a-tag v-for="item in weakPoints" :key="item" color="orange">
                  {{ item }}
                </a-tag>
              </div>
              <div class="signal-box">
                <div class="signal-box__title">画像更新依据</div>
                <ul class="plain-list plain-list--compact">
                  <li>对话画像：结合近期提问与追问方式动态抽取学习偏好。</li>
                  <li>掌握度：根据问答、练习批改与错因复盘持续更新。</li>
                  <li>课堂表现：有行为检测数据时同步修正学习风险与投入度。</li>
                </ul>
              </div>
            </template>
            <a-empty v-else description="尚未获取学习画像，请先刷新画像后再开始本轮资源生成。" />
          </a-spin>
        </a-card>

        <a-card v-if="isPackageMode" class="panel-card" title="资源生成设置">
          <div class="card-intro">
            设置本轮课程主题、目标与难度，系统将生成可直接用于教学的正式资源包。
          </div>
          <div v-if="incomingSeedSummary" class="seed-banner">
            <span class="seed-banner__label">本轮进入上下文</span>
            <strong>{{ incomingSeedSummary }}</strong>
          </div>
          <a-form :model="form" layout="vertical">
            <a-form-item field="subject" label="学科/课程">
              <a-input v-model="form.subject" placeholder="例如：数据库系统" />
            </a-form-item>
            <a-form-item field="topic" label="知识点">
              <a-input v-model="form.topic" placeholder="例如：关系模型、SQL 联结" />
            </a-form-item>
            <a-form-item field="goal" label="学习目标">
              <a-textarea
                v-model="form.goal"
                :auto-size="{ minRows: 3, maxRows: 4 }"
                placeholder="希望系统如何帮助学生完成本次学习"
              />
            </a-form-item>
            <a-row :gutter="12">
              <a-col :span="12">
                <a-form-item field="difficulty" label="目标难度">
                  <a-select v-model="form.difficulty">
                    <a-option value="auto">自动匹配</a-option>
                    <a-option value="foundation">基础巩固</a-option>
                    <a-option value="standard">标准提升</a-option>
                    <a-option value="challenge">挑战拓展</a-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item field="minutes" label="学习时长">
                  <a-input-number v-model="form.minutes" :min="10" :max="120" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-button
              type="primary"
              long
              :loading="loadingPackage"
              @click="handleGeneratePackage"
            >
              生成正式资源包
            </a-button>
          </a-form>
        </a-card>

        <a-card v-if="isExerciseMode" class="panel-card" title="批改范围与上下文">
          <div class="card-intro">
            补充课程与知识点后，批改结果会更准确地回写到学生画像与后续追练建议中。
          </div>
          <a-form :model="gradeForm" layout="vertical">
            <a-form-item label="学科/课程">
              <a-input v-model="gradeForm.subject" placeholder="例如：数据库系统" />
            </a-form-item>
            <a-form-item label="知识点">
              <a-input v-model="gradeForm.topic" placeholder="例如：关系模型" />
            </a-form-item>
          </a-form>
        </a-card>

        <a-card v-if="isImageMode" class="panel-card" title="题目背景补充">
          <div class="card-intro">
            可补充课程信息与文字题干，帮助图像识别结果更稳定，也便于生成更清晰的结构化讲解。
          </div>
          <a-form :model="imageForm" layout="vertical">
            <a-form-item label="学科/课程">
              <a-input v-model="imageForm.subject" placeholder="例如：数据库系统" />
            </a-form-item>
            <a-form-item label="补充题干">
              <a-textarea
                v-model="imageForm.question_text"
                :auto-size="{ minRows: 4, maxRows: 6 }"
                placeholder="可补充题干文字，提升识别稳定性"
              />
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <a-col :xs="24" :xl="16">
        <template v-if="isPackageMode">
          <a-card class="panel-card" title="资源编排流程">
            <div class="card-intro">
              从画像匹配到结果校对，生成流程会按教学可用性逐步组织内容。
            </div>
            <div class="agent-flow">
              <div
                v-for="(agent, index) in agentSteps"
                :key="agent.name"
                class="agent-node"
                :class="{ active: packageResult && index <= 4 }"
              >
                <div class="agent-icon">{{ agent.icon }}</div>
                <strong>{{ agent.name }}</strong>
                <span>{{ agent.desc }}</span>
              </div>
            </div>
          </a-card>

          <a-card class="panel-card" title="资源生成结果">
            <template v-if="packageResult">
              <div class="package-head">
                <div>
                  <h3>{{ packageResult.topic }} 学习资源包</h3>
                  <p>{{ packageResult.goal }}</p>
                </div>
                <a-tag color="arcoblue">{{ packageResult.resources.length }} 类资源</a-tag>
              </div>
              <div class="package-actions">
                <a-button size="small" type="outline" @click="copyPackageSummary">
                  复制摘要
                </a-button>
                <a-button size="small" type="outline" @click="downloadPackageSummary">
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
              <div class="result-stats">
                <div
                  v-for="item in packageStats"
                  :key="item.label"
                  class="result-stat"
                >
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
              <div class="result-section">
                <div class="result-section__head">
                  <h4>个性化匹配依据</h4>
                  <span>用于解释本轮资源为何这样编排</span>
                </div>
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
                  class="resource-card"
                >
                  <div class="resource-card__index">0{{ index + 1 }}</div>
                  <div class="resource-meta">
                    <a-tag>{{ resourceTypeLabel(item.type) }}</a-tag>
                    <span>{{ item.estimated_minutes }} 分钟</span>
                  </div>
                  <h4>{{ item.title }}</h4>
                  <p>{{ item.description }}</p>
                  <div class="preview-text">{{ item.content_preview }}</div>
                  <div class="resource-card__actions">
                    <a-button size="mini" type="outline" @click="copyResourceItem(item)">
                      复制
                    </a-button>
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
            <a-empty
              v-else
              description="尚未生成资源包。完成左侧设置后，这里会展示讲解、练习、案例与脚本等正式资源。"
            />
          </a-card>

          <a-card class="panel-card" title="个性化学习路径图">
            <div v-if="pathNodes.length" class="result-section">
              <div class="result-section__head">
                <h4>建议学习顺序</h4>
                <span>根据资源类型自动编排完成路径</span>
              </div>
            </div>
            <div v-if="pathNodes.length" class="path-flow">
              <div v-for="(node, index) in pathNodes" :key="node.title" class="path-node">
                <span class="path-index">{{ index + 1 }}</span>
                <strong>{{ node.title }}</strong>
                <small>{{ node.minutes }} 分钟</small>
              </div>
            </div>
            <a-empty v-else description="资源包生成后，将自动编排建议学习路径。" />
          </a-card>
        </template>

        <a-card v-if="isExerciseMode" class="panel-card" title="练习批改与掌握度更新">
          <div class="card-intro">
            输入题目与学生作答后，系统会完成评分、错因反馈，并同步更新相关知识点掌握度。
          </div>
          <a-form :model="gradeForm" layout="vertical">
            <a-form-item label="题目">
              <a-textarea
                v-model="gradeForm.question"
                :auto-size="{ minRows: 4, maxRows: 6 }"
              />
            </a-form-item>
            <a-form-item label="学生作答">
              <a-textarea
                v-model="gradeForm.student_answer"
                :auto-size="{ minRows: 5, maxRows: 8 }"
              />
            </a-form-item>
            <a-form-item label="参考答案（可选）">
              <a-textarea
                v-model="gradeForm.reference_answer"
                :auto-size="{ minRows: 3, maxRows: 5 }"
              />
            </a-form-item>
            <a-button
              type="primary"
              long
              :loading="loadingGrade"
              @click="handleGrade"
            >
              提交批改并同步画像
            </a-button>
          </a-form>
          <div v-if="gradeResult" class="grade-result">
            <div class="result-section">
              <div class="result-section__head">
                <h4>批改结果</h4>
                <span>结果已与学习画像联动</span>
              </div>
            </div>
            <div class="result-stats">
              <div
                v-for="item in gradeStats"
                :key="item.label"
                class="result-stat"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
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
                {{ Math.round(gradeResult.mastery_before * 100) }}%
                →
                {{ Math.round(gradeResult.mastery_after * 100) }}%
              </span>
            </div>
            <a-progress
              :percent="Math.round(gradeResult.mastery_after * 100)"
              :show-text="false"
            />
            <p>{{ gradeResult.feedback }}</p>
            <ul class="plain-list">
              <li v-for="item in gradeResult.follow_up" :key="item">{{ item }}</li>
            </ul>
          </div>
          <a-empty
            v-else
            class="result-empty"
            description="提交批改后，这里会展示得分、掌握度变化与后续追练建议。"
          />
        </a-card>

        <a-card v-if="isImageMode" class="panel-card" title="图像题目识别与图解">
          <div class="card-intro">
            上传题目图片后，系统会完成题意提取、解题步骤生成与结构化图解整理。
          </div>
          <div class="upload-line">
            <input type="file" accept="image/*" @change="handleImageFile" />
            <span v-if="imageName">{{ imageName }}</span>
            <span v-else class="upload-placeholder">支持课堂拍照、练习截图与试题图片</span>
          </div>
          <a-button
            type="primary"
            long
            :disabled="!imageForm.image_base64"
            :loading="loadingImage"
            @click="handleImageAnalyze"
          >
            开始图像识别与题解
          </a-button>
          <div v-if="imageResult" class="image-result">
            <div class="result-section">
              <div class="result-section__head">
                <h4>识别结果与题解输出</h4>
                <span>支持题干提取、图解节点与步骤化讲解</span>
              </div>
            </div>
            <div class="result-stats">
              <div
                v-for="item in imageStats"
                :key="item.label"
                class="result-stat"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
            <div class="result-meta">
              <a-tag>{{ imageResult.subject }}</a-tag>
              <a-tag color="arcoblue">{{ imageResult.problem_type }}</a-tag>
              <span>置信度 {{ Math.round(imageResult.confidence * 100) }}%</span>
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
              <li v-for="item in imageResult.solution_outline" :key="item">
                {{ item }}
              </li>
            </ul>
          </div>
          <a-empty
            v-else
            class="result-empty"
            description="上传并分析题目图片后，这里会展示识别文本、图解节点与完整题解。"
          />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import { fetchLearningReport, LearningReport } from '@/api/rag';
import {
  analyzeImageProblem,
  generateResourcePackage,
  gradeResourceExercise,
  ImageAnalyzeResponse,
  ResourceDifficulty,
  ResourceItem,
  ResourcePackageResponse,
} from '@/api/resource-workshop';
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
const gradeResult = ref<Awaited<ReturnType<typeof gradeResourceExercise>> | null>(null);
const imageResult = ref<ImageAnalyzeResponse | null>(null);
const imageName = ref('');
const activeMode = ref<WorkbenchMode>(resolveRouteMode(route.name));

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

const agentSteps = [
  { name: '画像匹配', desc: '抽取基础与短板', icon: 'P1' },
  { name: '讲解组织', desc: '整理概念讲解', icon: 'D1' },
  { name: '练习设计', desc: '生成分层练习', icon: 'Q1' },
  { name: '路径安排', desc: '排列学习顺序', icon: 'R1' },
  { name: '结果校对', desc: '整理可用资源', icon: 'A1' },
];

const mode = computed(() => String(route.name || 'ResourcePackageBuilder'));
const isUnifiedWorkbench = computed(() => mode.value === 'CourseResourceGeneration');
const isPackageMode = computed(() => activeMode.value === 'package');
const isExerciseMode = computed(() => activeMode.value === 'exercise');
const isImageMode = computed(() => activeMode.value === 'image');
const modeOptions: Array<{
  label: string;
  value: WorkbenchMode;
  description: string;
  badge: string;
}> = [
  { label: '资源包生成', value: 'package', description: '围绕画像生成讲义、导图、练习与案例', badge: '主线' },
  { label: '练习批改', value: 'exercise', description: '形成批改、掌握度、追练闭环', badge: '联动' },
  { label: '图像题解', value: 'image', description: '接入图片识别与结构化讲解', badge: '多模态' },
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

const weakPoints = computed(() => report.value?.weak_points?.slice(0, 6) || []);

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
    { label: '当前目标', value: report.value?.current_goal || '待从对话中更新' },
    { label: '学习偏好', value: report.value?.learning_style || '结构化讲解' },
    { label: '风险等级', value: riskLabel(report.value?.risk_level) },
    { label: '知识基础', value: basisLabel(masteryBars.value) },
    { label: '易错点', value: weakPoints.value[0] || '暂无明显薄弱点' },
    {
      label: '课堂投入',
      value: behavior?.on_task_rate
        ? `${Math.round(behavior.on_task_rate * 100)}%`
        : '等待课堂数据',
    },
  ];
});

const pathNodes = computed(() =>
  (packageResult.value?.resources || []).map((item: ResourceItem) => ({
    title: resourceTypeLabel(item.type),
    minutes: item.estimated_minutes,
  }))
);
const packageStats = computed(() => {
  if (!packageResult.value) return [];
  const totalMinutes = packageResult.value.resources.reduce(
    (sum, item) => sum + (Number(item.estimated_minutes) || 0),
    0
  );
  return [
    { label: '资源数量', value: `${packageResult.value.resources.length} 项` },
    { label: '预计学习时长', value: `${totalMinutes} 分钟` },
    { label: '匹配依据', value: `${packageResult.value.personalization_basis.length} 条` },
  ];
});
const videoScriptResource = computed(() =>
  packageResult.value?.resources.find((item) => item.type === 'video_script') || null
);
const incomingSeedSummary = computed(() => {
  const topic = String(route.query.topic || '').trim();
  const goal = String(route.query.goal || '').trim();
  const source = String(route.query.source || '').trim();
  if (!topic && !goal && !source) return '';
  const segments = [];
  if (source) segments.push(`来自 ${source}`);
  if (topic) segments.push(`主题：${topic}`);
  if (goal) segments.push(`目标：${goal}`);
  return segments.join(' / ');
});
const gradeStats = computed(() => {
  if (!gradeResult.value) return [];
  return [
    { label: '得分', value: `${gradeResult.value.score} / 100` },
    {
      label: '掌握度变化',
      value: `${Math.round(gradeResult.value.mastery_before * 100)}% -> ${Math.round(
        gradeResult.value.mastery_after * 100
      )}%`,
    },
    { label: '后续建议', value: `${gradeResult.value.follow_up.length} 项` },
  ];
});

const diagramNodes = computed(() => {
  const content = imageResult.value?.diagram?.content || '';
  const labels = Array.from(content.matchAll(/\[([^\]]+)\]/g)).map((item) => item[1]);
  return labels.length ? labels.slice(0, 6) : imageResult.value?.solution_outline?.slice(0, 4) || [];
});
const imageStats = computed(() => {
  if (!imageResult.value) return [];
  return [
    { label: '识别置信度', value: `${Math.round(imageResult.value.confidence * 100)}%` },
    { label: '图解节点', value: `${diagramNodes.value.length} 项` },
    { label: '解题步骤', value: `${imageResult.value.solution_outline.length} 步` },
  ];
});

function hydrateFormsFromReport(snapshot: LearningReport | null) {
  if (!snapshot) return;
  const primaryWeakPoint = snapshot.weak_points?.[0] || '';
  const primaryGoal = snapshot.current_goal || '';
  const primarySubject = form.subject || gradeForm.subject || imageForm.subject || '';

  if (!form.topic && primaryWeakPoint) form.topic = primaryWeakPoint;
  if (!form.goal && primaryGoal) form.goal = primaryGoal;
  if (!gradeForm.topic && primaryWeakPoint) gradeForm.topic = primaryWeakPoint;
  if (!imageForm.subject && primarySubject) imageForm.subject = primarySubject;

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

  if (seedMode === 'exercise' || seedMode === 'image' || seedMode === 'package') {
    activeMode.value = seedMode as WorkbenchMode;
  }
  if (seedSubject) {
    form.subject = seedSubject;
    gradeForm.subject = seedSubject;
    imageForm.subject = seedSubject;
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
  }
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

function buildPackageExportText() {
  if (!packageResult.value) return '';
  const lines = [
    `${packageResult.value.topic} 学习资源包`,
    `课程：${packageResult.value.subject}`,
    `目标：${packageResult.value.goal}`,
    '',
    '个性化匹配依据：',
    ...packageResult.value.personalization_basis.map((item, index) => `${index + 1}. ${item}`),
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
  const blob = new Blob([buildPackageExportText()], { type: 'text/plain;charset=utf-8' });
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
  try {
    packageResult.value = await generateResourcePackage({
      ...form,
      resource_count: 6,
    });
    gradeForm.subject = packageResult.value.subject;
    gradeForm.topic = packageResult.value.topic;
    imageForm.subject = packageResult.value.subject;
    if (!imageForm.question_text.trim()) {
      imageForm.question_text = `请结合 ${packageResult.value.topic} 的核心概念，对题目进行结构化讲解。`;
    }
    Message.success('资源包已生成');
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
.container {
  padding: 0 20px 24px;
}

.hero-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 28px;
  color: #102033;
  background:
    radial-gradient(circle at right top, rgba(55, 122, 246, 0.15), transparent 28%),
    linear-gradient(135deg, #eef7ff 0%, #f7fbff 44%, #f4fff9 100%);
  border: 1px solid #d7e9fb;
  border-radius: 8px;
}

.hero-band h2 {
  margin: 4px 0 8px;
  font-size: 28px;
}

.hero-band p {
  max-width: 760px;
  margin: 0;
  color: #50657b;
  line-height: 1.7;
}

.hero-copy {
  display: grid;
  gap: 12px;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.eyebrow {
  color: #1476d4;
  font-weight: 700;
}

.hero-scene {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  color: #0f5ca8;
  font-size: 12px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(141, 182, 228, 0.9);
  border-radius: 999px;
}

.hero-actions {
  min-width: 210px;
  display: grid;
  gap: 12px;
  justify-items: end;
}

.hero-status {
  width: 100%;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(142, 181, 228, 0.8);
  border-radius: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.hero-status__label {
  display: block;
  margin-bottom: 4px;
  color: #5f7388;
  font-size: 12px;
}

.hero-status strong {
  display: block;
  color: #163a63;
  font-size: 18px;
}

.hero-status small {
  display: block;
  margin-top: 4px;
  color: #62758b;
  line-height: 1.6;
}

.hero-status--empty {
  background: rgba(255, 255, 255, 0.7);
}

.hero-status__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.hero-status__meta-item {
  padding: 10px 12px;
  background: rgba(241, 247, 255, 0.9);
  border-radius: 8px;
}

.hero-status__meta-item span {
  display: block;
  color: #6c7f93;
  font-size: 12px;
}

.hero-status__meta-item strong {
  margin-top: 4px;
  font-size: 15px;
}

.hero-highlights {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.hero-highlight {
  min-height: 74px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(211, 227, 243, 0.95);
  border-radius: 8px;
}

.hero-highlight span {
  display: block;
  color: #6a7c8e;
  font-size: 12px;
}

.hero-highlight strong {
  display: block;
  margin-top: 8px;
  color: #173a62;
  line-height: 1.6;
}

.mode-switch-wrap {
  display: grid;
  gap: 10px;
}

.mode-switch {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.mode-switch__item {
  padding: 14px 14px 12px;
  text-align: left;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid #d5e3f0;
  border-radius: 8px;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.mode-switch__item:hover {
  border-color: #9fc4ef;
  transform: translateY(-1px);
}

.mode-switch__item--active {
  background: #ffffff;
  border-color: #4f92e8;
  box-shadow: 0 10px 24px rgba(36, 96, 173, 0.12);
}

.mode-switch__item strong,
.mode-switch__item span {
  display: block;
}

.mode-switch__item em {
  display: inline-flex;
  align-items: center;
  margin-bottom: 10px;
  padding: 2px 8px;
  color: #1b5f9c;
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
  background: #e9f4ff;
  border-radius: 999px;
}

.mode-switch__item strong {
  color: #163a63;
  line-height: 1.4;
}

.mode-switch__item span {
  margin-top: 6px;
  color: #5f7388;
  font-size: 12px;
  line-height: 1.5;
}

.panel-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.card-intro {
  margin-bottom: 14px;
  color: #62758b;
  line-height: 1.7;
}

.section-note {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  background: #f6faff;
  border: 1px solid #deebf8;
  border-radius: 8px;
}

.section-note strong {
  color: #193a5c;
  line-height: 1.4;
}

.section-note span {
  color: #62758b;
  font-size: 13px;
  line-height: 1.6;
}

.section-note--light {
  background: rgba(255, 255, 255, 0.6);
}

.profile-summary,
.package-head p,
.resource-card p,
.extracted-text,
.grade-result p {
  color: #526477;
  line-height: 1.7;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0;
}

.profile-dim {
  min-height: 70px;
  padding: 12px;
  background: #f7fafc;
  border: 1px solid #e4edf6;
  border-radius: 8px;
}

.dim-label {
  display: block;
  margin-bottom: 8px;
  color: #7a8a9a;
}

.mastery-row + .mastery-row {
  margin-top: 10px;
}

.mastery-head,
.resource-meta,
.package-head,
.result-meta,
.score-line,
.upload-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.tag-row,
.basis-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.signal-box {
  margin-top: 16px;
  padding: 14px 16px;
  background: #f8fbff;
  border: 1px solid #dfe9f4;
  border-radius: 8px;
}

.signal-box__title {
  margin-bottom: 8px;
  color: #173447;
  font-weight: 700;
}

.seed-banner {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
  padding: 12px 14px;
  background: #f8fbff;
  border: 1px solid #dce9f5;
  border-radius: 8px;
}

.seed-banner__label {
  color: #708295;
  font-size: 12px;
}

.seed-banner strong {
  color: #173a62;
  line-height: 1.7;
}

.agent-flow {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.agent-node {
  min-height: 128px;
  padding: 16px;
  overflow-wrap: anywhere;
  color: #607083;
  background: #f8fafc;
  border: 1px solid #e1e8f0;
  border-radius: 8px;
}

.agent-node.active {
  color: #0f3c67;
  background: #eef8ff;
  border-color: #8ac7f2;
}

.agent-icon {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
  color: #ffffff;
  font-weight: 700;
  background: #2f80ed;
  border-radius: 999px;
}

.agent-node span {
  display: block;
  margin-top: 8px;
}

.agent-node strong {
  display: block;
  line-height: 1.4;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.package-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0;
}

.result-stat {
  min-height: 84px;
  padding: 14px;
  background: #f8fbff;
  border: 1px solid #dce9f5;
  border-radius: 8px;
}

.result-stat span {
  display: block;
  color: #708295;
  font-size: 12px;
}

.result-stat strong {
  display: block;
  margin-top: 10px;
  color: #163a63;
  line-height: 1.6;
}

.result-section {
  margin-top: 16px;
}

.result-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.result-section__head h4 {
  margin: 0;
  color: #173a62;
  font-size: 15px;
}

.result-section__head span {
  color: #708295;
  font-size: 12px;
  line-height: 1.5;
}

.resource-card {
  position: relative;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e2ebf5;
  border-radius: 8px;
}

.resource-card__index {
  position: absolute;
  top: 14px;
  right: 16px;
  color: #9aaaba;
  font-size: 12px;
  font-weight: 700;
}

.resource-card h4 {
  margin: 12px 0 8px;
  font-size: 16px;
}

.resource-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.preview-text {
  min-height: 52px;
  padding: 10px 12px;
  color: #274562;
  background: #f5f9ff;
  border-radius: 6px;
  line-height: 1.6;
}

.path-flow {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 12px;
}

.path-node {
  position: relative;
  min-height: 94px;
  padding: 14px;
  background: #f8fbff;
  border: 1px solid #dbeafb;
  border-radius: 8px;
}

.path-index {
  display: inline-flex;
  width: 24px;
  height: 24px;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
  color: #ffffff;
  background: #2f80ed;
  border-radius: 999px;
}

.path-node small {
  display: block;
  margin-top: 8px;
  color: #7c8d9e;
}

.score-line {
  justify-content: flex-start;
  margin-top: 16px;
}

.score-line strong {
  font-size: 30px;
  color: #1d6fd6;
}

.result-empty {
  margin-top: 18px;
}

.plain-list {
  padding-left: 18px;
  color: #526477;
  line-height: 1.8;
}

.plain-list--compact {
  margin: 0;
}

.upload-line {
  justify-content: flex-start;
  margin-bottom: 12px;
}

.upload-placeholder {
  color: #7a8b9c;
}

.image-result {
  margin-top: 16px;
}

.extracted-text,
.answer-box {
  margin-top: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e3ebf3;
  border-radius: 8px;
}

.diagram-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.diagram-flow span {
  padding: 8px 10px;
  color: #155f9c;
  background: #edf7ff;
  border: 1px solid #bde0fb;
  border-radius: 999px;
}

@media (max-width: 900px) {
  .hero-band,
  .package-head,
  .result-section__head {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-actions {
    width: 100%;
    justify-items: stretch;
  }

  .hero-highlights,
  .mode-switch,
  .agent-flow,
  .resource-grid,
  .result-stats {
    grid-template-columns: 1fr;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
