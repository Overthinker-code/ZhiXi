<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.textToVideo']" />
    <div class="content studio-shell">
      <div class="header studio-header">
        <a-button type="text" class="back-btn" @click="goBack">返回数字人创作舱</a-button>
        <h1 class="title">文本生成视频 Studio</h1>
        <p class="subtitle">输入课程脚本，一键生成智屿数字人口播视频</p>
      </div>

      <div class="studio-layout">
        <section class="left-panel panel-card">
          <h3>脚本输入</h3>
          <a-textarea
            v-model="scriptContent"
            :auto-size="{ minRows: 12, maxRows: 16 }"
            placeholder="请输入文本内容，例如：大家好，欢迎来到今天的课程，我们将重点讲解..."
          />
          <div class="actions">
            <a-button type="primary" :loading="isGenerating" @click="generateVideo">
              生成视频
            </a-button>
          </div>
        </section>

        <section class="middle-panel panel-card">
          <h3>生成参数</h3>
          <div class="config-list">
            <div class="config-item">
              <span>讲解语速</span>
              <a-slider :default-value="45" :min="20" :max="80" />
            </div>
            <div class="config-item">
              <span>情感强度</span>
              <a-slider :default-value="60" :min="10" :max="100" />
            </div>
            <div class="config-item">
              <span>输出画幅</span>
              <a-radio-group :default-value="'16:9'" type="button">
                <a-radio value="16:9">16:9</a-radio>
                <a-radio value="9:16">9:16</a-radio>
              </a-radio-group>
            </div>
            <div class="config-item">
              <span>配音音色</span>
              <a-select v-model="selectedVoice" :options="voiceOptions" />
            </div>
          </div>
          <div class="tips">
            <a-alert type="info" show-icon>
              建议单条脚本控制在 350~800 字，画面节奏和口播流畅度更稳定。
            </a-alert>
          </div>
        </section>

        <section class="right-panel panel-card dark-card">
          <div class="preview-canvas">
            <video
              v-if="videoUrl && jobStatus.status === 'success'"
              class="studio-cover"
              :src="videoUrl"
              controls
            />
            <img v-else :src="studioCoverImage" class="studio-cover" alt="数字人封面" />
            <div v-if="isGenerating" class="scan-line"></div>
            <div class="play-mask">{{ videoUrl && jobStatus.status === 'success' ? '▶' : 'AI' }}</div>
            <div class="status-badge">{{ statusBadge }}</div>
          </div>

          <div class="job-panel">
            <div class="job-line">
              <span>当前任务</span>
              <strong>{{ jobMessage }}</strong>
            </div>
            <div class="job-line">
              <span>任务 ID</span>
              <strong class="task-id">{{ activeTaskId || '未创建' }}</strong>
            </div>
            <a-progress
              :percent="jobProgress"
              :show-text="true"
              :animation="true"
              :status="jobStatus.status === 'failed' ? 'danger' : 'normal'"
            />
          </div>

          <p class="preview-tip">
            当前显示：{{ videoUrl ? '已生成的视频成片，可直接预览播放' : '数字人预览画面，任务完成后会自动切换成片' }}
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import studioCover from '@/assets/digital-human/studio-cover.png';
import { createTextToVideoJob } from '@/api/digital-human';
import { useDigitalHumanJob } from '@/composables/useDigitalHumanJob';

const router = useRouter();
const scriptContent = ref('');
const isGenerating = ref(false);
const studioCoverImage = ref(studioCover);
const videoUrl = ref('');
const selectedVoice = ref('zh-CN-YunxiNeural');
const selectedDigitalHumanId = ref('teacher-default');
const { activeTaskId, status: jobStatus, startPolling } = useDigitalHumanJob();

const voiceOptions = [
  { label: '知性男声 Yunxi', value: 'zh-CN-YunxiNeural' },
  { label: '温和女声 Xiaoxiao', value: 'zh-CN-XiaoxiaoNeural' },
  { label: '沉稳女声 Yunjian', value: 'zh-CN-YunjianNeural' },
];

const jobProgress = computed(() => Number(jobStatus.value.progress || 0));
const jobMessage = computed(() => jobStatus.value.message || '等待任务开始');
const statusBadge = computed(() => {
  if (jobStatus.value.status === 'success') return '预览就绪';
  if (jobStatus.value.status === 'failed') return '渲染失败';
  if (jobStatus.value.status === 'processing') {
    return `${jobStatus.value.message} (${jobProgress.value}%)`;
  }
  if (activeTaskId.value) {
    return `渲染排队中 (${jobProgress.value}%)`;
  }
  return '等待任务';
});

const goBack = () => {
  router.push('/digital-human');
};

const generateVideo = async () => {
  const text = scriptContent.value.trim();
  if (!text) {
    Message.warning('请先输入脚本内容');
    return;
  }
  isGenerating.value = true;
  videoUrl.value = '';
  try {
    const job = await createTextToVideoJob({
      text,
      title: text.slice(0, 24),
      voice_id: selectedVoice.value,
      digital_human_id: selectedDigitalHumanId.value,
    });
    await startPolling(job.task_id);
    if (jobStatus.value.status === 'success' && jobStatus.value.video_url) {
      videoUrl.value = jobStatus.value.video_url;
      Message.success('数字人视频渲染完成');
    } else if (jobStatus.value.status === 'failed') {
      Message.error(jobStatus.value.message || '数字人渲染失败');
    }
  } catch (error: any) {
    Message.error(error?.message || '创建数字人任务失败');
  } finally {
    isGenerating.value = false;
  }
};
</script>

<script lang="ts">
export default {
  name: 'TextToVideo',
};
</script>

<style scoped lang="less">
.container {
  padding: 0 20px 24px;
  min-height: 100%;
  background:
    radial-gradient(circle at 8% -10%, rgba(99, 102, 241, 0.16), transparent 42%),
    radial-gradient(circle at 95% 8%, rgba(14, 165, 233, 0.16), transparent 38%),
    linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
}
.content {
  max-width: 1340px;
  margin: 0 auto;
}
.studio-shell {
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  padding: 18px;
}
.header {
  text-align: center;
  margin-bottom: 16px;
}
.back-btn {
  float: left;
  margin-bottom: 8px;
}
.title {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  color: #0f172a;
}
.subtitle {
  margin: 8px 0 0;
  color: #64748b;
}
.studio-layout {
  display: grid;
  grid-template-columns: 35% 30% 35%;
  gap: 14px;
}
.panel-card {
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.1);
  padding: 16px;
}
.panel-card h3 {
  margin: 0 0 12px;
  font-size: 18px;
  color: #0f172a;
}
.left-panel {
  min-height: 520px;
}
.actions {
  margin-top: 14px;
}
.middle-panel {
  min-height: 520px;
}
.config-list {
  display: grid;
  gap: 14px;
}
.config-item {
  display: grid;
  gap: 8px;
}
.config-item span {
  font-size: 13px;
  color: #334155;
  font-weight: 600;
}
.tips {
  margin-top: 14px;
}
.right-panel {
  min-height: 520px;
}
.dark-card {
  background-color: #0f172a;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 24px 24px;
  border-color: rgba(56, 189, 248, 0.36);
}
.preview-canvas {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(56, 189, 248, 0.4);
}
.studio-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #38bdf8, transparent);
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.9);
  animation: scan 1.1s linear infinite;
}
.play-mask {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 74px;
  height: 74px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
}
.status-badge {
  position: absolute;
  right: 10px;
  top: 10px;
  border-radius: 999px;
  border: 1px solid rgba(56, 189, 248, 0.55);
  background: rgba(2, 6, 23, 0.6);
  color: #e2e8f0;
  font-size: 11px;
  padding: 4px 10px;
  font-weight: 700;
}
.job-panel {
  margin-top: 14px;
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(56, 189, 248, 0.22);
}
.job-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  color: #cbd5e1;
  font-size: 13px;
}
.job-line strong {
  color: #f8fafc;
}
.task-id {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-tip {
  margin: 12px 0 0;
  color: #cbd5e1;
}
@keyframes scan {
  0% { top: 0; }
  100% { top: calc(100% - 2px); }
}
@media (max-width: @screen-lg) {
  .studio-layout {
    grid-template-columns: 1fr;
  }
}
</style>
