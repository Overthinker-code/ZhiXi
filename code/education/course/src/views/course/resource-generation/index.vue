<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import {
    fetchRecentGeneratedPackages,
    generateResourcePackage,
    type RecentGeneratedPackage,
    type ResourceGenerationResponse,
    type ResourceKind,
  } from '@/api/resource-generation';
  import { getToken } from '@/utils/auth';

  const loading = ref(false);
  const result = ref<ResourceGenerationResponse | null>(null);
  const recentPackages = ref<RecentGeneratedPackage[]>([]);

  const form = reactive({
    subject: '数据库系统',
    topic: '关系模型',
    learning_goal: '巩固核心概念，生成讲义、练习和实操案例',
    difficulty: 'standard' as 'foundation' | 'standard' | 'challenge',
    target_minutes: 45,
    use_web_search: false,
    resource_types: [
      'lecture_markdown',
      'lecture_pdf',
      'practice_markdown',
      'practice_pdf',
      'mind_map',
      'reading_list',
      'case_project',
      'video_script',
    ] as ResourceKind[],
  });

  const resourceOptions = [
    { label: '讲义 Markdown', value: 'lecture_markdown' },
    { label: '讲义 PDF', value: 'lecture_pdf' },
    { label: '分层练习 Markdown', value: 'practice_markdown' },
    { label: '分层练习 PDF', value: 'practice_pdf' },
    { label: '思维导图', value: 'mind_map' },
    { label: '拓展阅读', value: 'reading_list' },
    { label: '实操案例', value: 'case_project' },
    { label: '数字人脚本', value: 'video_script' },
  ];

  const difficultyOptions = [
    { label: '基础巩固', value: 'foundation' },
    { label: '标准提升', value: 'standard' },
    { label: '挑战拓展', value: 'challenge' },
  ];

  const templateCards = [
    {
      title: '45 分钟新授课',
      subject: '数据库系统',
      topic: '关系模型',
      learning_goal: '帮助学生掌握关系模型、键约束和关系完整性，并配套课堂练习',
      difficulty: 'standard' as const,
      target_minutes: 45,
    },
    {
      title: '课后巩固练习',
      subject: '数据结构',
      topic: '二叉树遍历',
      learning_goal: '生成分层练习、错因提示和一份可发放的课后训练材料',
      difficulty: 'foundation' as const,
      target_minutes: 30,
    },
    {
      title: '项目式案例包',
      subject: '软件工程',
      topic: '需求分析',
      learning_goal: '生成案例背景、任务单、评价量规和数字人导入脚本',
      difficulty: 'challenge' as const,
      target_minutes: 90,
    },
  ];

  const workflowSteps = [
    '填写课程、知识点和教学目标',
    '选择讲义、练习、案例、导图等产物',
    '本地模型生成并记录协作过程',
    '教师下载资源包后微调用于课堂',
  ];

  const agentPipeline = [
    {
      name: '课程分析 Agent',
      role: '识别课程目标、知识边界与学生短板',
      output: '资源设计方案',
    },
    {
      name: '讲义 Agent',
      role: '生成结构化 Markdown/PDF 讲义',
      output: '讲义文档',
    },
    {
      name: '练习 Agent',
      role: '生成分层题库、参考答案和错因提示',
      output: '练习材料',
    },
    {
      name: '实践 Agent',
      role: '设计代码实操案例和项目任务',
      output: '实操案例',
    },
    {
      name: '媒体 Agent',
      role: '生成数字人口播脚本和短视频素材说明',
      output: '脚本/视频',
    },
  ];

  const exampleArtifacts = [
    '知识点讲义 PDF',
    '分层练习 Markdown',
    '课堂思维导图',
    '数字人口播脚本',
  ];

  const generationScenarios = computed(() => {
    if (recentPackages.value.length) {
      return recentPackages.value.map((item) => ({
        topic: item.topic,
        time: item.subject,
        status: `已生成 ${item.artifacts.length} 个真实产物`,
      }));
    }
    return [
      { topic: 'SQL 联结查询', time: '数据库系统', status: '适合生成讲义+练习' },
      { topic: '操作系统进程调度', time: '计算机基础', status: '适合生成思维导图' },
      { topic: 'Python 文件读写', time: '程序设计', status: '适合生成实操案例' },
    ];
  });

  const modelProfile = computed(() => result.value?.local_model_profile || {});
  const activeAgentCount = computed(() =>
    result.value ? agentPipeline.length : loading.value ? 2 : 0
  );
  const artifactSummary = computed(() => {
    if (!result.value) return [];
    return result.value.artifacts.map((item) => ({
      ...item,
      label: resourceOptions.find((option) => option.value === item.kind)?.label || item.kind,
    }));
  });
  const modelLabel = computed(() => {
    const profile = modelProfile.value || {};
    return (
      profile.multimodal_model ||
      profile.chat_model ||
      '本地模型'
    );
  });

  const applyTemplate = (template: (typeof templateCards)[number]) => {
    form.subject = template.subject;
    form.topic = template.topic;
    form.learning_goal = template.learning_goal;
    form.difficulty = template.difficulty;
    form.target_minutes = template.target_minutes;
  };

  const formatBytes = (size: number) => {
    if (!size) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1);
    const value = size / 1024 ** index;
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[index]}`;
  };

  const handleGenerate = async () => {
    if (!form.subject.trim() || !form.topic.trim()) {
      Message.warning('请填写课程和知识点');
      return;
    }
    loading.value = true;
    try {
      result.value = await generateResourcePackage({
        ...form,
        subject: form.subject.trim(),
        topic: form.topic.trim(),
        learning_goal: form.learning_goal.trim(),
      });
      await loadRecentPackages();
      Message.success('资源包已生成');
    } catch (error: any) {
      Message.error(error?.message || '资源生成失败');
    } finally {
      loading.value = false;
    }
  };

  const loadRecentPackages = async () => {
    try {
      recentPackages.value = await fetchRecentGeneratedPackages();
    } catch {
      recentPackages.value = [];
    }
  };

  const openArtifact = (downloadUrl: string) => {
    const token = getToken();
    if (!token) {
      Message.warning('当前登录状态已失效，请重新登录后下载');
      return;
    }
    window.open(`${downloadUrl}?token=${encodeURIComponent(token)}`, '_blank');
  };

  onMounted(() => {
    void loadRecentPackages();
  });
</script>

<template>
  <div class="resource-generation-page">
    <Breadcrumb :items="['课程资源管理', '资源生成中心']" />

    <section class="page-head">
      <div>
        <span class="eyebrow">多智能体资源生产线</span>
        <h1>资源生成中心</h1>
        <p>围绕课程知识点生成可下载讲义、练习、思维导图、案例和数字人脚本。</p>
      </div>
      <a-button type="primary" :loading="loading" @click="handleGenerate">
        生成资源包
      </a-button>
    </section>

    <section class="workspace">
      <div class="config-panel">
        <div class="template-section">
          <div class="section-title">快速模板</div>
          <button
            v-for="template in templateCards"
            :key="template.title"
            class="template-card"
            type="button"
            @click="applyTemplate(template)"
          >
            <strong>{{ template.title }}</strong>
            <span>{{ template.subject }} · {{ template.topic }}</span>
          </button>
        </div>
        <a-form :model="form" layout="vertical">
          <a-form-item label="课程">
            <a-input v-model="form.subject" placeholder="例如：数据库系统" />
          </a-form-item>
          <a-form-item label="知识点">
            <a-input v-model="form.topic" placeholder="例如：关系模型、SQL 联结" />
          </a-form-item>
          <a-form-item label="学习目标">
            <a-textarea
              v-model="form.learning_goal"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              placeholder="说明本次资源面向的学习目标"
            />
          </a-form-item>
          <div class="form-grid">
            <a-form-item label="目标难度">
              <a-select v-model="form.difficulty" :options="difficultyOptions" />
            </a-form-item>
            <a-form-item label="建议时长">
              <a-input-number v-model="form.target_minutes" :min="10" :max="180" />
            </a-form-item>
          </div>
          <a-form-item label="资源类型">
            <a-checkbox-group v-model="form.resource_types" direction="vertical">
              <a-checkbox
                v-for="item in resourceOptions"
                :key="item.value"
                :value="item.value"
              >
                {{ item.label }}
              </a-checkbox>
            </a-checkbox-group>
          </a-form-item>
          <a-form-item label="联网搜索补充">
            <a-switch v-model="form.use_web_search" />
            <span class="switch-note">开启后仅作为来源标注的补充材料</span>
          </a-form-item>
        </a-form>
      </div>

      <div class="result-panel">
        <div v-if="!result" class="starter-panel">
          <div class="pipeline-board">
            <div class="section-title">Agent 协作编排</div>
            <div class="agent-pipeline">
              <article
                v-for="(agent, index) in agentPipeline"
                :key="agent.name"
                :class="{
                  active: index < activeAgentCount,
                  pending: index >= activeAgentCount,
                }"
              >
                <span class="step-index">{{ index + 1 }}</span>
                <div>
                  <strong>{{ agent.name }}</strong>
                  <p>{{ agent.role }}</p>
                  <small>{{ agent.output }}</small>
                </div>
              </article>
            </div>
          </div>

          <div class="starter-section">
            <div class="section-title">生成流程</div>
            <ol class="workflow-list">
              <li v-for="item in workflowSteps" :key="item">{{ item }}</li>
            </ol>
          </div>

          <div class="starter-grid">
            <div class="starter-section">
              <div class="section-title">可生成资源</div>
              <div class="example-list">
                <a-tag
                  v-for="item in exampleArtifacts"
                  :key="item"
                  color="arcoblue"
                >
                  {{ item }}
                </a-tag>
              </div>
            </div>

            <div class="starter-section">
              <div class="section-title">推荐生成场景</div>
              <div class="recent-list">
                <article
                  v-for="item in generationScenarios"
                  :key="item.topic"
                  class="recent-item"
                >
                  <div>
                    <strong>{{ item.topic }}</strong>
                    <span>{{ item.time }}</span>
                  </div>
                  <a-tag color="green">{{ item.status }}</a-tag>
                </article>
              </div>
            </div>
          </div>
        </div>
        <template v-else>
          <div class="result-head">
            <div>
              <h2>{{ result.topic }} 资源包</h2>
              <p>{{ result.package_id }}</p>
            </div>
            <a-tag color="green">已生成</a-tag>
          </div>

          <div class="profile-row">
            <a-tag>{{ modelProfile.chat_provider || 'local' }}</a-tag>
            <a-tag color="arcoblue">{{ modelLabel }}</a-tag>
            <a-tag>{{ modelProfile.embedding_provider || 'embedding' }}</a-tag>
          </div>

          <div class="agent-result-board">
            <article
              v-for="(agent, index) in agentPipeline"
              :key="agent.name"
              class="agent-result-card"
            >
              <div class="step-index">{{ index + 1 }}</div>
              <div>
                <strong>{{ agent.name }}</strong>
                <span>{{ agent.output }} 已完成</span>
              </div>
            </article>
          </div>

          <div class="artifact-list">
            <article
              v-for="artifact in artifactSummary"
              :key="artifact.file_name"
              class="artifact-card"
            >
              <div>
                <a-tag color="arcoblue">{{ artifact.label }}</a-tag>
                <h3>{{ artifact.title }}</h3>
                <p>{{ artifact.file_name }} · {{ formatBytes(artifact.file_size) }}</p>
                <div class="artifact-preview">{{ artifact.preview }}</div>
              </div>
              <a-button
                type="outline"
                @click="openArtifact(artifact.download_url)"
              >
                下载
              </a-button>
            </article>
          </div>

          <div class="trace-block">
            <h3>协作过程</h3>
            <ol>
              <li v-for="item in result.agent_trace" :key="item">{{ item }}</li>
            </ol>
          </div>

          <div class="trace-block">
            <h3>质量说明</h3>
            <ul>
              <li v-for="item in result.quality_notes" :key="item">{{ item }}</li>
            </ul>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
  .resource-generation-page {
    padding: 20px;
    min-height: 100%;
    background:
      radial-gradient(circle at top left, rgba(56, 189, 248, 0.14), transparent 30%),
      linear-gradient(135deg, #f7fbfd 0%, #f3faf7 48%, #f8fbff 100%);
  }

  .page-head {
    margin-top: 14px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;

    h1 {
      margin: 3px 0 0;
      font-size: 24px;
      color: #172033;
    }

    p {
      margin: 8px 0 0;
      color: #5d6b82;
    }
  }

  .eyebrow {
    color: #16806b;
    font-size: 12px;
    font-weight: 800;
  }

  .workspace {
    margin-top: 18px;
    display: grid;
    grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
    gap: 16px;
  }

  .config-panel,
  .result-panel {
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(48, 112, 104, 0.14);
    border-radius: 8px;
    padding: 18px;
    box-shadow: 0 12px 28px rgba(15, 59, 72, 0.07);
  }

  .template-section {
    margin-bottom: 18px;
    display: grid;
    gap: 10px;
  }

  .section-title {
    font-size: 14px;
    font-weight: 700;
    color: #24324a;
  }

  .template-card {
    width: 100%;
    padding: 12px;
    border: 1px solid #e3eaf3;
    border-radius: 8px;
    background: #fbfdff;
    text-align: left;
    cursor: pointer;
    display: grid;
    gap: 5px;

    strong {
      color: #172033;
      font-size: 14px;
    }

    span {
      color: #6b778c;
      font-size: 12px;
    }

    &:hover {
      border-color: #a9d9ce;
      background: #f6fcfa;
    }
  }

  .pipeline-board {
    padding: 16px;
    border: 1px solid #dceee9;
    border-radius: 8px;
    background: #fbfffd;
  }

  .agent-pipeline {
    margin-top: 12px;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;

    article {
      min-height: 148px;
      padding: 12px;
      border: 1px solid #e2ece9;
      border-radius: 8px;
      background: #fff;
      color: #607383;

      &.active {
        border-color: #a9d9ce;
        background: #f3fcf8;

        .step-index {
          background: #16806b;
        }
      }
    }

    strong {
      display: block;
      margin: 10px 0 6px;
      color: #173447;
      line-height: 1.35;
    }

    p {
      margin: 0;
      min-height: 48px;
      color: #607383;
      font-size: 12px;
      line-height: 1.5;
    }

    small {
      display: inline-flex;
      margin-top: 10px;
      color: #16806b;
      font-size: 12px;
      font-weight: 700;
    }
  }

  .step-index {
    display: inline-flex;
    width: 26px;
    height: 26px;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-weight: 800;
    background: #93a7b4;
    border-radius: 999px;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .switch-note {
    margin-left: 10px;
    color: #6b778c;
    font-size: 13px;
  }

  .result-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;

    h2 {
      margin: 0;
      font-size: 20px;
      color: #172033;
    }

    p {
      margin: 6px 0 0;
      color: #748198;
      font-size: 13px;
    }
  }

  .starter-panel {
    display: grid;
    gap: 16px;
  }

  .starter-section {
    padding: 16px;
    border: 1px solid #e8edf5;
    border-radius: 8px;
    background: #fbfdff;
  }

  .starter-grid {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    gap: 16px;
  }

  .workflow-list {
    margin: 12px 0 0;
    padding-left: 20px;
    color: #526176;
    line-height: 1.9;
  }

  .example-list {
    margin-top: 12px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .recent-list {
    margin-top: 12px;
    display: grid;
    gap: 10px;
  }

  .recent-item {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 12px;
    border: 1px solid #edf1f7;
    border-radius: 8px;
    background: #fff;

    div {
      display: grid;
      gap: 4px;
    }

    strong {
      color: #24324a;
      font-size: 14px;
    }

    span {
      color: #7a8799;
      font-size: 12px;
    }
  }

  .profile-row {
    margin-top: 14px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .artifact-list {
    margin-top: 18px;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .agent-result-board {
    margin-top: 18px;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }

  .agent-result-card {
    min-height: 82px;
    padding: 12px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    border: 1px solid #dceee9;
    border-radius: 8px;
    background: #f7fcfa;

    .step-index {
      background: #16806b;
    }

    strong,
    span {
      display: block;
    }

    strong {
      color: #173447;
      font-size: 13px;
    }

    span {
      margin-top: 4px;
      color: #607383;
      font-size: 12px;
    }
  }

  .artifact-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    justify-content: space-between;
    gap: 12px;
    padding: 14px;
    border: 1px solid #e8edf5;
    border-radius: 8px;
    background: #fbfdff;

    h3 {
      margin: 10px 0 4px;
      font-size: 15px;
      color: #24324a;
    }

    p {
      margin: 5px 0 0;
      color: #738198;
      font-size: 12px;
    }
  }

  .artifact-preview {
    margin-top: 10px;
    padding: 10px;
    max-height: 92px;
    overflow: hidden;
    border-radius: 8px;
    background: #f7fbfa;
    color: #42596a;
    font-size: 12px;
    line-height: 1.6;
  }

  .trace-block {
    margin-top: 18px;

    h3 {
      margin: 0 0 8px;
      font-size: 15px;
      color: #24324a;
    }

    ol,
    ul {
      margin: 0;
      padding-left: 20px;
      color: #526176;
      line-height: 1.8;
    }
  }

  @media (max-width: 900px) {
    .workspace {
      grid-template-columns: 1fr;
    }

    .page-head {
      flex-direction: column;
    }

    .starter-grid {
      grid-template-columns: 1fr;
    }

    .agent-pipeline,
    .agent-result-board,
    .artifact-list {
      grid-template-columns: 1fr;
    }
  }
</style>
