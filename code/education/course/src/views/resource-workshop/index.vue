<template>
  <div class="container">
    <Breadcrumb :items="['学习资源工坊', currentPageTitle]" />

    <section class="hero-band">
      <div>
        <div class="eyebrow">学习资源工坊</div>
        <h2>{{ currentPageTitle }}</h2>
        <p>{{ currentPageDescription }}</p>
      </div>
      <a-button type="primary" :loading="loadingReport" @click="loadProfile(true)">
        刷新画像
      </a-button>
    </section>

    <a-row :gutter="16">
      <a-col :xs="24" :xl="8">
        <a-card class="panel-card" title="学习画像">
          <a-spin :loading="loadingReport" style="width: 100%">
            <template v-if="report">
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
            </template>
            <a-empty v-else description="暂无画像数据，点击刷新画像生成" />
          </a-spin>
        </a-card>

        <a-card v-if="isPackageMode" class="panel-card" title="生成设置">
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
              生成个性化资源包
            </a-button>
          </a-form>
        </a-card>

        <a-card v-if="isExerciseMode" class="panel-card" title="批改范围">
          <a-form :model="gradeForm" layout="vertical">
            <a-form-item label="学科/课程">
              <a-input v-model="gradeForm.subject" placeholder="例如：数据库系统" />
            </a-form-item>
            <a-form-item label="知识点">
              <a-input v-model="gradeForm.topic" placeholder="例如：关系模型" />
            </a-form-item>
          </a-form>
        </a-card>

        <a-card v-if="isImageMode" class="panel-card" title="题目背景">
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
                  v-for="item in packageResult.resources"
                  :key="item.title"
                  class="resource-card"
                >
                  <div class="resource-meta">
                    <a-tag>{{ resourceTypeLabel(item.type) }}</a-tag>
                    <span>{{ item.estimated_minutes }} 分钟</span>
                  </div>
                  <h4>{{ item.title }}</h4>
                  <p>{{ item.description }}</p>
                  <div class="preview-text">{{ item.content_preview }}</div>
                </article>
              </div>
            </template>
            <a-empty v-else description="生成后将在这里展示资源包内容" />
          </a-card>

          <a-card class="panel-card" title="个性化学习路径图">
            <div v-if="pathNodes.length" class="path-flow">
              <div v-for="(node, index) in pathNodes" :key="node.title" class="path-node">
                <span class="path-index">{{ index + 1 }}</span>
                <strong>{{ node.title }}</strong>
                <small>{{ node.minutes }} 分钟</small>
              </div>
            </div>
            <a-empty v-else description="暂无路径，先生成资源包" />
          </a-card>
        </template>

        <a-card v-if="isExerciseMode" class="panel-card" title="练习批改与掌握度更新">
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
              批改并更新画像
            </a-button>
          </a-form>
          <div v-if="gradeResult" class="grade-result">
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
        </a-card>

        <a-card v-if="isImageMode" class="panel-card" title="图像题目识别与图解">
          <div class="upload-line">
            <input type="file" accept="image/*" @change="handleImageFile" />
            <span v-if="imageName">{{ imageName }}</span>
          </div>
          <a-button
            type="primary"
            long
            :disabled="!imageForm.image_base64"
            :loading="loadingImage"
            @click="handleImageAnalyze"
          >
            分析题目并生成图解
          </a-button>
          <div v-if="imageResult" class="image-result">
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
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
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

const loadingReport = ref(false);
const loadingPackage = ref(false);
const loadingGrade = ref(false);
const loadingImage = ref(false);

const report = ref<LearningReport | null>(null);
const packageResult = ref<ResourcePackageResponse | null>(null);
const gradeResult = ref<Awaited<ReturnType<typeof gradeResourceExercise>> | null>(null);
const imageResult = ref<ImageAnalyzeResponse | null>(null);
const imageName = ref('');

const form = reactive<{
  subject: string;
  topic: string;
  goal: string;
  difficulty: ResourceDifficulty;
  minutes: number;
}>({
  subject: '数据库系统',
  topic: '关系模型',
  goal: '先补齐核心概念，再生成练习和可复盘路径',
  difficulty: 'auto',
  minutes: 45,
});

const gradeForm = reactive({
  subject: '数据库系统',
  topic: '关系模型',
  question: '请说明关系模型中的实体完整性与参照完整性分别约束什么。',
  student_answer: '',
  reference_answer: '',
});

const imageForm = reactive({
  subject: '数据库系统',
  question_text: '',
  image_base64: '',
});

const agentSteps = [
  { name: '画像匹配', desc: '抽取基础与短板', icon: 'P1' },
  { name: '讲解组织', desc: '整理概念讲解', icon: 'D1' },
  { name: '练习设计', desc: '生成分层练习', icon: 'Q1' },
  { name: '路径安排', desc: '排列学习顺序', icon: 'R1' },
  { name: '结果校对', desc: '整理可用资源', icon: 'A1' },
];

const mode = computed(() => String(route.name || 'ResourcePackageBuilder'));
const isPackageMode = computed(() => mode.value === 'ResourcePackageBuilder');
const isExerciseMode = computed(() => mode.value === 'ResourceExerciseReview');
const isImageMode = computed(() => mode.value === 'ResourceImageSolver');
const currentPageTitle = computed(() => {
  if (isExerciseMode.value) return '练习批改';
  if (isImageMode.value) return '图像题解';
  return '资源包生成';
});
const currentPageDescription = computed(() => {
  if (isExerciseMode.value) {
    return '围绕指定课程与知识点批改学生作答，给出反馈并同步更新学习画像。';
  }
  if (isImageMode.value) {
    return '上传题目图片并补充题干信息，识别题意后生成解题提示、步骤与图解。';
  }
  return '基于学生画像、当前目标和薄弱点，生成讲解文档、思维导图、练习题、阅读材料、实操案例与数字人脚本。';
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

const diagramNodes = computed(() => {
  const content = imageResult.value?.diagram?.content || '';
  const labels = Array.from(content.matchAll(/\[([^\]]+)\]/g)).map((item) => item[1]);
  return labels.length ? labels.slice(0, 6) : imageResult.value?.solution_outline?.slice(0, 4) || [];
});

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

async function loadProfile(refresh = false) {
  loadingReport.value = true;
  try {
    report.value = await fetchLearningReport(refresh);
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
  loadProfile(false);
});
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
  padding: 24px 28px;
  color: #102033;
  background: linear-gradient(135deg, #eef7ff 0%, #f7fbff 44%, #f4fff9 100%);
  border: 1px solid #d7e9fb;
  border-radius: 8px;
}

.hero-band h2 {
  margin: 4px 0 8px;
  font-size: 26px;
}

.hero-band p {
  max-width: 820px;
  margin: 0;
  color: #50657b;
  line-height: 1.7;
}

.eyebrow {
  color: #1476d4;
  font-weight: 700;
}

.panel-card {
  margin-bottom: 16px;
  border-radius: 8px;
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

.resource-card {
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e2ebf5;
  border-radius: 8px;
}

.resource-card h4 {
  margin: 12px 0 8px;
  font-size: 16px;
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

.plain-list {
  padding-left: 18px;
  color: #526477;
  line-height: 1.8;
}

.upload-line {
  justify-content: flex-start;
  margin-bottom: 12px;
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
  .package-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .agent-flow,
  .resource-grid {
    grid-template-columns: 1fr;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
