<template>
  <a-card
    class="general-card behavior-detection-card"
    :title="$t('monitor.behaviorDetection.title')"
  >
    <div class="detection-content">
      <!-- 教育学理论框架展示 -->
      <div class="theory-framework-panel">
        <div class="theory-title">🎓 基于教育学理论框架的课堂行为分析模型</div>
        <div class="theory-grid">
          <div class="theory-card">
            <div class="theory-icon">🧠</div>
            <div class="theory-name">Fredricks三维学习投入模型</div>
            <div class="theory-desc">行为投入 / 认知投入 / 情感投入</div>
          </div>
          <div class="theory-card">
            <div class="theory-icon">📊</div>
            <div class="theory-name">Bloom认知分类法修订版</div>
            <div class="theory-desc">记忆 → 理解 → 应用 → 分析 → 评价 → 创造</div>
          </div>
          <div class="theory-card">
            <div class="theory-icon">⏰</div>
            <div class="theory-name">持续性注意力动态模型</div>
            <div class="theory-desc">15-20分钟注意力周期性波动监测</div>
          </div>
          <div class="theory-card">
            <div class="theory-icon">🔥</div>
            <div class="theory-name">社会传染理论</div>
            <div class="theory-desc">课堂分心行为空间聚集性识别</div>
          </div>
        </div>
      </div>

      <!-- 上传分析 -->
      <a-divider orientation="center">上传分析</a-divider>
      <div class="upload-area">
        <div class="upload-buttons">
          <a-button
            long
            @click="fileInput?.click()"
          >
            <template #icon>
              <IconUpload />
            </template>
            上传图片
          </a-button>
          <a-button
            long
            @click="videoInput?.click()"
          >
            <template #icon>
              <IconUpload />
            </template>
            上传视频
          </a-button>
        </div>

        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display: none;"
          @change="handleFileUpload"
        />
        <input
          ref="videoInput"
          type="file"
          accept="video/*"
          style="display: none;"
          @change="handleVideoUpload"
        />

        <a-button
          v-if="lastUploadedFile"
          long
          type="primary"
          status="success"
          style="margin-top: 8px;"
          :loading="isUploading || isUploadingVideo"
          @click="startUploadAnalysis"
        >
          开始分析上传文件
        </a-button>
        <a-button
          v-if="detectionStatus === 'running'"
          long
          status="danger"
          style="margin-top: 8px;"
          @click="stopUploadAnalysis"
        >
          停止分析
        </a-button>
      </div>

      <!-- 上传预览区域 -->
      <div v-if="currentFrame" class="upload-preview-area">
        <div class="video-container">
          <img
            ref="previewImage"
            :src="currentFrame"
            alt="上传预览"
            class="preview-image"
            @load="onImageLoad"
          />
          <canvas
            v-if="currentResult?.persons?.length"
            ref="uploadDetectionCanvas"
            class="detection-canvas"
          />
          <div v-if="currentResult" class="detection-overlay">
            <div
              class="score-badge"
              :style="{
                backgroundColor: getScoreColor(currentResult.overall_score),
              }"
            >
              {{ currentResult.learning_status }}
            </div>
          </div>
        </div>
      </div>

      <!-- 上传分析结果 -->
      <div v-if="currentResult" class="upload-stats">
        <!-- 教育学模块参数总览 -->
        <div v-if="currentResult.classroom_metrics?.educational" class="edu-metrics-panel">
          <a-divider orientation="center">📊 课堂学习投入指标</a-divider>
          <div class="edu-metrics-grid">
            <div class="edu-metric-item">
              <div class="edu-metric-label">学习投入指数 LEI</div>
              <a-progress
                :percent="Math.round((currentResult.classroom_metrics.educational.learning_engagement_index || 0) * 100) / 100"
                :color="getEngagementColor(currentResult.classroom_metrics.educational.learning_engagement_index)"
                size="small"
              />
              <div class="edu-metric-num">{{ ((currentResult.classroom_metrics.educational.learning_engagement_index || 0) * 100).toFixed(0) }}</div>
            </div>
            <div class="edu-metric-item">
              <div class="edu-metric-label">行为投入 BEI</div>
              <a-progress
                :percent="Math.round((currentResult.classroom_metrics.educational.behavioral_engagement || 0) * 100) / 100"
                :color="getEngagementColor(currentResult.classroom_metrics.educational.behavioral_engagement)"
                size="small"
              />
              <div class="edu-metric-num">{{ ((currentResult.classroom_metrics.educational.behavioral_engagement || 0) * 100).toFixed(0) }}</div>
            </div>
            <div class="edu-metric-item">
              <div class="edu-metric-label">认知投入 CEI</div>
              <a-progress
                :percent="Math.round((currentResult.classroom_metrics.educational.cognitive_engagement || 0) * 100) / 100"
                :color="getEngagementColor(currentResult.classroom_metrics.educational.cognitive_engagement)"
                size="small"
              />
              <div class="edu-metric-num">{{ ((currentResult.classroom_metrics.educational.cognitive_engagement || 0) * 100).toFixed(0) }}</div>
            </div>
            <div class="edu-metric-item">
              <div class="edu-metric-label">情感投入 EEI</div>
              <a-progress
                :percent="Math.round((currentResult.classroom_metrics.educational.learning_engagement_index || 0) * 100) / 100"
                :color="getEngagementColor(currentResult.classroom_metrics.educational.learning_engagement_index)"
                size="small"
              />
              <div class="edu-metric-num">{{ ((currentResult.classroom_metrics.educational.learning_engagement_index || 0) * 100).toFixed(0) }}</div>
            </div>
          </div>
          <div class="edu-extra-row">
            <span class="edu-extra-item">
              🔥 社会传染指数: {{ (currentResult.classroom_metrics.educational.contagion_index || 0).toFixed(2) }}
            </span>
            <span class="edu-extra-item">
              ⏰ 注意力相位: {{ currentResult.classroom_metrics.educational.attention_cycle_phase || 'unknown' }}
            </span>
            <span class="edu-extra-item">
              📈 注意力趋势: {{ currentResult.classroom_metrics.educational.attention_trend || 'unknown' }}
            </span>
          </div>
          <div v-if="currentResult.classroom_metrics.educational.bloom_distribution && Object.keys(currentResult.classroom_metrics.educational.bloom_distribution).length > 0" class="bloom-distribution">
            <div class="bloom-title">🎯 Bloom认知分布</div>
            <div class="bloom-bars">
              <div v-for="(val, key) in currentResult.classroom_metrics.educational.bloom_distribution" :key="key" class="bloom-bar-item">
                <span class="bloom-label">{{ key }}</span>
                <a-progress :percent="val" size="small" :color="getBloomBarColor(key)" />
                <span class="bloom-pct">{{ (val * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </div>

        <a-divider orientation="center">分析结果</a-divider>

        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">综合评分</div>
            <div
              class="stat-value"
              :style="{ color: getScoreColor(currentResult.overall_score) }"
            >
              {{ currentResult.overall_score.toFixed(2) }}
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-label">检测人数</div>
            <div class="stat-value">{{ currentResult.persons?.length || 0 }}</div>
          </div>
        </div>

        <!-- 课堂教育学参数总览 -->
        <div v-if="currentResult.classroom_metrics" class="edu-overview">
          <div class="edu-row">
            <span class="edu-label">专注率</span>
            <span class="edu-value">{{ !isNaN(currentResult.classroom_metrics.focus_rate as number) ? ((currentResult.classroom_metrics.focus_rate as number) * 100).toFixed(0) : '--' }}%</span>
          </div>
          <div class="edu-row">
            <span class="edu-label">走神率</span>
            <span class="edu-value">{{ !isNaN(currentResult.classroom_metrics.distraction_rate as number) ? ((currentResult.classroom_metrics.distraction_rate as number) * 100).toFixed(0) : '--' }}%</span>
          </div>
        </div>

        <!-- 基于教育学理论的课堂建议 -->
        <div v-if="currentResult" class="edu-suggestions-panel">
          <a-divider orientation="center">💡 教育学理论驱动的课堂干预建议</a-divider>
          <div class="suggestion-list">
            <div
              v-for="(sg, idx) in generateClassroomSuggestions(currentResult)"
              :key="idx"
              class="suggestion-item"
              :class="'priority-' + sg.priority"
            >
              <div class="suggestion-header">
                <span class="suggestion-icon">{{ sg.icon }}</span>
                <span class="suggestion-theory">{{ sg.theory }}</span>
                <a-tag v-if="sg.priority === 'high'" color="red" size="small">紧急</a-tag>
                <a-tag v-else-if="sg.priority === 'medium'" color="orange" size="small">建议</a-tag>
                <a-tag v-else color="green" size="small">参考</a-tag>
              </div>
              <div class="suggestion-title">{{ sg.title }}</div>
              <div class="suggestion-content">{{ sg.content }}</div>
            </div>
            <div v-if="generateClassroomSuggestions(currentResult).length === 0" class="suggestion-empty">
              课堂状态良好，暂无特别建议
            </div>
          </div>
        </div>

        <!-- AI个性化学习方案 -->
        <div v-if="currentResult" class="ai-learning-plan-panel">
          <a-divider orientation="center">🤖 AI个性化学习方案</a-divider>
          <div class="ai-plan-desc">
            基于本次课堂行为检测的{{ currentResult.persons?.length || 0 }}人数据，调用大语言模型生成个性化教学建议
          </div>
          <div class="ai-plan-actions">
            <a-button
              type="primary"
              size="small"
              :loading="aiLoading.diagnosis"
              @click="handleRunDiagnosis"
            >
              <template #icon>🩺</template>
              一键诊断学情
            </a-button>
            <a-button
              status="success"
              size="small"
              :loading="aiLoading.plan"
              @click="handleGeneratePlan"
            >
              <template #icon>📋</template>
              生成复习计划
            </a-button>
            <a-button
              status="warning"
              size="small"
              :loading="aiLoading.mistakes"
              @click="handleGenerateMistakes"
            >
              <template #icon>📝</template>
              整理错题归因
            </a-button>
          </div>
          <div v-if="aiReport" class="ai-report-preview">
            <a-alert type="success">
              <template #title>{{ aiReport.title || '诊断完成' }}</template>
              {{ aiReport.summary || '已基于课堂行为数据生成个性化学习方案，请前往学习数据页面查看详情。' }}
            </a-alert>
            <a-button type="text" size="small" @click="goToLearningData">
              → 前往学习数据页面查看完整方案
            </a-button>
          </div>
        </div>

        <!-- 个人教育学参数卡片 -->
        <div class="edu-person-list">
          <div
            v-for="(person, index) in currentResult.persons"
            :key="index"
            class="edu-person-card"
          >
            <div class="edu-person-header">
              <span class="edu-person-id">学生{{ index + 1 }}</span>
              <a-tag
                :color="person.educational?.mind_wandering ? 'red' : 'green'"
                size="small"
              >
                {{ person.educational?.cognitive_state || person.behavior || '未知' }}
              </a-tag>
            </div>
            <div v-if="person.educational" class="edu-person-body">
              <div class="edu-metric-row">
                <span class="edu-metric-label">LEI</span>
                <a-progress
                  :percent="person.educational.lei"
                  :color="getLeiColor(person.educational.lei)"
                  size="small"
                  style="flex: 1;"
                  :show-text="false"
                />
                <span class="edu-metric-value">{{ (person.educational.lei * 100).toFixed(0) }}</span>
              </div>
              <div class="edu-metric-row">
                <span class="edu-metric-label">布鲁姆</span>
                <a-tag size="small" :color="getBloomColor(person.educational.bloom_level)">
                  {{ person.educational.bloom_level }}
                </a-tag>
              </div>
              <!-- 教育学姿态参数 -->
              <div class="edu-posture-params">
                <div class="posture-row">
                  <span class="posture-label">头部</span>
                  <span class="posture-value">{{ person.educational.head_pose || '-' }}</span>
                </div>
                <div class="posture-row">
                  <span class="posture-label">视线</span>
                  <span class="posture-value">{{ person.educational.gaze_direction || '-' }}</span>
                </div>
                <div class="posture-row">
                  <span class="posture-label">倾斜</span>
                  <span class="posture-value">{{ person.educational.body_lean ? person.educational.body_lean.toFixed(2) : '-' }}°</span>
                </div>
                <div class="posture-row">
                  <span class="posture-label">手部</span>
                  <span class="posture-value">{{ person.educational.hand_position || '-' }}</span>
                </div>
                <div class="posture-row">
                  <span class="posture-label">维度</span>
                  <span class="posture-value">{{ person.educational.engagement_dimension || '-' }}</span>
                </div>
              </div>
              <div class="edu-dimensions">
                <span class="edu-dim" title="身体投入">BEI {{ (person.educational.bei * 100).toFixed(0) }}</span>
                <span class="edu-dim" title="认知投入">CEI {{ (person.educational.cei * 100).toFixed(0) }}</span>
                <span class="edu-dim" title="情感投入">EEI {{ (person.educational.eei * 100).toFixed(0) }}</span>
              </div>
              <div v-if="person.educational.mind_wandering" class="edu-wander-alert">
                ⚠️ 检测到走神状态
              </div>
              <div class="edu-person-suggestion">
                💡 {{ generatePersonalSuggestion(person) }}
              </div>
            </div>
            <div v-else class="edu-person-body">
              <div class="edu-metric-row">
                <span class="edu-metric-label">行为</span>
                <span>{{ person.behavior }}</span>
                <span style="font-size: 12px; color: #666;">{{ Math.round(person.confidence * 100) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史记录快捷入口 -->
      <div v-if="recentRecords.length > 0" class="recent-records">
        <a-divider orientation="center">历史记录</a-divider>
        <a-list :bordered="false" size="small">
          <a-list-item
            v-for="record in recentRecords.slice(0, 3)"
            :key="record.id"
          >
            <div class="record-item">
              <span class="record-time">{{ formatTime(record.timestamp) }}</span>
              <a-tag :color="getOverallStatusColor(record.overall_status)">
                {{ record.overall_status }}
              </a-tag>
            </div>
          </a-list-item>
        </a-list>
        <a-button type="text" long @click="viewAllRecords">
          查看全部
        </a-button>
      </div>

      <!-- 空状态 -->
      <div v-if="!currentFrame" class="video-placeholder">
        <IconVideoCamera class="icon" />
        <span>上传图片或视频进行行为分析</span>
      </div>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  IconVideoCamera,
  IconUpload,
} from '@arco-design/web-vue/es/icon';
import {
  analyzeImage,
  analyzeVideo,
  getBehaviorDefinitions,
  getAnalysisRecords,
  type ImageAnalysisResult,
  type BehaviorDefinitionsResponse,
  type AnalysisRecord,
} from '@/api/behavior-analysis';
import {
  runLearningDiagnosis,
  generateReviewPlan,
  generateMistakeDigest,
} from '@/api/rag';

const props = defineProps<{
  courseId?: string;
}>();

const emit = defineEmits<{
  (e: 'update:result', result: ImageAnalysisResult | null): void;
  (e: 'analysis-complete', payload: { imageUrl: string; result: ImageAnalysisResult }): void;
}>();

// ==================== 上传分析 ====================
const fileInput = ref<HTMLInputElement | null>(null);
const videoInput = ref<HTMLInputElement | null>(null);
const previewImage = ref<HTMLImageElement | null>(null);
const uploadDetectionCanvas = ref<HTMLCanvasElement | null>(null);
const isUploading = ref(false);
const isUploadingVideo = ref(false);
const currentFrame = ref<string>('');
const currentResult = ref<ImageAnalysisResult | null>(null);
const hasAnalyzedImage = ref(false);
const hasAnalyzedVideo = ref(false);
const lastUploadedFile = ref<File | null>(null);
const lastUploadedType = ref<'image' | 'video' | null>(null);
const videoFrameUrl = ref<string>('');
const detectionStatus = ref<'idle' | 'running'>('idle');

const behaviorDefinitions = ref<BehaviorDefinitionsResponse | null>(null);
const recentRecords = ref<AnalysisRecord[]>([]);
let refreshInterval: ReturnType<typeof setInterval> | null = null;

// ==================== AI个性化学习方案 ====================
const aiLoading = ref({ diagnosis: false, plan: false, mistakes: false });
const aiReport = ref<{ title?: string; summary?: string } | null>(null);

const handleRunDiagnosis = async () => {
  aiLoading.value.diagnosis = true;
  try {
    const res = await runLearningDiagnosis(true);
    aiReport.value = {
      title: '学情诊断完成',
      summary: res.overall_summary || '已基于课堂行为数据生成学情诊断报告。',
    };
    Message.success('学情诊断生成成功，正在跳转...');
    setTimeout(goToLearningData, 800);
  } catch (error: any) {
    Message.error(error?.message || '学情诊断失败，请稍后重试');
  } finally {
    aiLoading.value.diagnosis = false;
  }
};

const handleGeneratePlan = async () => {
  aiLoading.value.plan = true;
  try {
    const res = await generateReviewPlan(true);
    aiReport.value = {
      title: '复习计划生成完成',
      summary: res.overview || '已基于课堂行为数据生成个性化复习计划。',
    };
    Message.success('复习计划生成成功，正在跳转...');
    setTimeout(goToLearningData, 800);
  } catch (error: any) {
    Message.error(error?.message || '复习计划生成失败，请稍后重试');
  } finally {
    aiLoading.value.plan = false;
  }
};

const handleGenerateMistakes = async () => {
  aiLoading.value.mistakes = true;
  try {
    const res = await generateMistakeDigest(true);
    aiReport.value = {
      title: '错题归因完成',
      summary: res.summary || '已基于课堂行为数据生成错题归因分析。',
    };
    Message.success('错题归因生成成功，正在跳转...');
    setTimeout(goToLearningData, 800);
  } catch (error: any) {
    Message.error(error?.message || '错题归因生成失败，请稍后重试');
  } finally {
    aiLoading.value.mistakes = false;
  }
};

const router = useRouter();
const goToLearningData = () => {
  router.push('/profile/learning-data');
};

// 获取行为定义
const loadBehaviorDefinitions = async () => {
  try {
    const res = await getBehaviorDefinitions();
    behaviorDefinitions.value = res.data;
  } catch (error) {
    console.error('加载行为定义失败:', error);
  }
};

// 获取历史记录
const loadRecentRecords = async () => {
  if (!props.courseId) return;
  try {
    const res = await getAnalysisRecords(props.courseId, 0, 10);
    recentRecords.value = res.data.data;
  } catch (error) {
    console.error('加载历史记录失败:', error);
  }
};

// 开始上传文件分析
const startUploadAnalysis = async () => {
  if (!props.courseId) {
    Message.warning('请先选择课程');
    return;
  }
  if (!lastUploadedFile.value) {
    Message.warning('请先上传图片或视频');
    return;
  }

  detectionStatus.value = 'running';

  if (lastUploadedType.value === 'image') {
    isUploading.value = true;
    Message.loading('正在分析图片...');
    try {
      const res = await analyzeImage(lastUploadedFile.value, props.courseId || undefined);
      if ((res.data as any)?.status === 'error') {
        throw new Error((res.data as any)?.error || '分析失败');
      }
      currentResult.value = res.data;
      hasAnalyzedImage.value = true;
      hasAnalyzedVideo.value = false;
      emit('update:result', res.data);
      emit('analysis-complete', { imageUrl: currentFrame.value, result: res.data });
      setTimeout(() => drawUploadDetectionBoxes(), 100);
      Message.success('分析完成！检测到 ' + (res.data.persons?.length || 0) + ' 人');
    } catch (error: any) {
      console.error('图片分析失败:', error);
      Message.error(error?.message || '分析失败');
    } finally {
      isUploading.value = false;
      detectionStatus.value = 'idle';
    }
  } else if (lastUploadedType.value === 'video') {
    isUploadingVideo.value = true;
    Message.loading('正在分析视频，请稍候...');
    try {
      const res = await analyzeVideo(lastUploadedFile.value, props.courseId || undefined, 30);
      if ((res.data as any)?.status === 'error') {
        throw new Error((res.data as any)?.error || '分析失败');
      }
      const summary = res.data.summary;
      const personsFromVideo = res.data.persons || [];
      const videoInfo = res.data.video_info || {};
      currentResult.value = {
        status: 'success',
        behaviors: [],
        persons: personsFromVideo,
        overall_score: summary?.average_score || 0,
        learning_status: summary?.overall_status || '无法评估',
        timestamp: new Date().toISOString(),
        image_width: (videoInfo as any).image_width || 0,
        image_height: (videoInfo as any).image_height || 0,
      };
      hasAnalyzedVideo.value = true;
      hasAnalyzedImage.value = false;
      emit('update:result', currentResult.value);
      emit('analysis-complete', { imageUrl: currentFrame.value, result: currentResult.value });
      setTimeout(() => drawUploadDetectionBoxes(), 200);
      Message.success(`视频分析完成！检测到 ${personsFromVideo.length} 人`);
      loadRecentRecords();
    } catch (error: any) {
      console.error('视频分析失败:', error);
      Message.error(error?.message || '视频分析失败');
      hasAnalyzedVideo.value = false;
    } finally {
      isUploadingVideo.value = false;
      detectionStatus.value = 'idle';
    }
  }
};

// 停止上传分析
const stopUploadAnalysis = () => {
  detectionStatus.value = 'idle';
  if (!hasAnalyzedImage.value && !hasAnalyzedVideo.value) {
    currentFrame.value = '';
    currentResult.value = null;
    emit('update:result', null);
  }
  Message.success('分析已停止');
};

// 处理文件上传（仅保存，不立即分析）
const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (!file) return;

  if (!file.type.startsWith('image/')) {
    Message.error('请选择图片文件');
    return;
  }

  lastUploadedFile.value = file;
  lastUploadedType.value = 'image';
  hasAnalyzedImage.value = false;
  hasAnalyzedVideo.value = false;
  detectionStatus.value = 'idle';
  currentResult.value = null;

  const reader = new FileReader();
  reader.onload = (e) => {
    currentFrame.value = e.target?.result as string;
  };
  reader.readAsDataURL(file);

  Message.info('图片已上传，点击"开始分析上传文件"进行分析');
  target.value = '';
};

// 从视频文件提取第一帧作为预览图
const extractVideoFirstFrame = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    video.preload = 'metadata';
    video.crossOrigin = 'anonymous';

    video.onloadeddata = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg');
      resolve(dataUrl);
    };

    video.onerror = () => {
      reject(new Error('无法加载视频'));
    };

    video.src = URL.createObjectURL(file);
    video.currentTime = 0.1;
  });
};

// 处理视频上传（仅保存，不立即分析）
const handleVideoUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (!file) return;

  if (!file.type.startsWith('video/')) {
    Message.error('请选择视频文件');
    return;
  }

  if (file.size > 100 * 1024 * 1024) {
    Message.error('视频文件不能超过100MB');
    return;
  }

  lastUploadedFile.value = file;
  lastUploadedType.value = 'video';
  hasAnalyzedImage.value = false;
  hasAnalyzedVideo.value = false;
  detectionStatus.value = 'idle';
  currentResult.value = null;

  try {
    const firstFrameUrl = await extractVideoFirstFrame(file);
    videoFrameUrl.value = firstFrameUrl;
    currentFrame.value = firstFrameUrl;
    Message.info('视频已上传，点击"开始分析上传文件"进行分析');
  } catch (error: any) {
    Message.error('视频预览生成失败');
  }

  target.value = '';
};

// 图片加载完成后绘制检测框
const onImageLoad = () => {
  setTimeout(drawUploadDetectionBoxes, 50);
};

// 窗口大小变化时重绘检测框
const onResize = () => {
  if (currentFrame.value && currentResult.value?.persons) {
    drawUploadDetectionBoxes();
  }
};

// 绘制上传检测框
const drawUploadDetectionBoxes = () => {
  if (!uploadDetectionCanvas.value || !previewImage.value || !currentResult.value?.persons) {
    return;
  }

  const canvas = uploadDetectionCanvas.value;
  const img = previewImage.value;
  const ctx = canvas.getContext('2d');

  if (!ctx) return;

  if (!img.complete || img.naturalWidth === 0) {
    setTimeout(drawUploadDetectionBoxes, 100);
    return;
  }

  const rect = img.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;

  const imgWidth = currentResult.value.image_width || img.naturalWidth;
  const imgHeight = currentResult.value.image_height || img.naturalHeight;
  const scaleX = canvas.width / imgWidth;
  const scaleY = canvas.height / imgHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  currentResult.value.persons.forEach((person: any, index: number) => {
    const [x1, y1, x2, y2] = person.bbox;
    const sx1 = x1 * scaleX;
    const sy1 = y1 * scaleY;
    const sx2 = x2 * scaleX;
    const sy2 = y2 * scaleY;
    const width = sx2 - sx1;
    const height = sy2 - sy1;

    ctx.strokeStyle = person.color || '#6366f1';
    ctx.lineWidth = 3;
    ctx.strokeRect(sx1, sy1, width, height);

    // 优先显示教育学参数标签
    const edu = person.educational;
    const cognitiveLabel = edu?.cognitive_state || person.behavior || '未知';
    const leiLabel = edu ? `LEI:${(edu.lei * 100).toFixed(0)}` : `(${Math.round(person.confidence * 100)}%)`;
    const line1 = `${cognitiveLabel}`;
    const line2 = edu ? `${leiLabel} ${edu.bloom_level}` : leiLabel;

    ctx.font = 'bold 13px Arial';
    const textWidth1 = ctx.measureText(line1).width;
    const textWidth2 = ctx.measureText(line2).width;
    const maxTextWidth = Math.max(textWidth1, textWidth2);
    const lineHeight = 18;
    const padding = 6;
    const bgHeight = lineHeight * 2 + padding;

    ctx.fillStyle = person.color || '#6366f1';
    ctx.fillRect(sx1, sy1 - bgHeight - 2, maxTextWidth + padding * 2, bgHeight);

    ctx.fillStyle = '#fff';
    ctx.fillText(line1, sx1 + padding, sy1 - lineHeight - 2);
    ctx.fillText(line2, sx1 + padding, sy1 - 4);
  });
};

// 获取分数颜色
const getScoreColor = (score: number): string => {
  const ranges = behaviorDefinitions.value?.score_ranges || [];
  for (const r of ranges) {
    if (score >= r.min && score <= r.max) {
      return r.color;
    }
  }
  if (score >= 0.7) return '#52c41a';
  if (score >= 0.3) return '#1890ff';
  if (score >= -0.3) return '#faad14';
  if (score >= -0.7) return '#fa541c';
  return '#f5222d';
};

// 获取行为颜色
const getBehaviorColor = (behaviorName: string): string => {
  const behavior = behaviorDefinitions.value?.behaviors.find(b => b.name === behaviorName);
  return behavior?.color || '#1890ff';
};

// LEI 颜色映射
const getLeiColor = (lei: number): string => {
  if (lei >= 0.75) return '#52c41a';
  if (lei >= 0.55) return '#1890ff';
  if (lei >= 0.40) return '#faad14';
  return '#f5222d';
};

// 布鲁姆层次颜色映射
const getBloomColor = (bloom: string): string => {
  const map: Record<string, string> = {
    remember: 'gray',
    understand: 'blue',
    apply: 'arcoblue',
    analyze: 'purple',
    evaluate: 'magenta',
    create: 'green',
  };
  return map[bloom] || 'gray';
};

// 学习投入指标颜色映射
const getEngagementColor = (value: number): string => {
  if (value >= 0.75) return '#52c41a';
  if (value >= 0.55) return '#1890ff';
  if (value >= 0.40) return '#faad14';
  return '#f5222d';
};

// Bloom分布条颜色映射
const getBloomBarColor = (bloom: string): string => {
  const map: Record<string, string> = {
    remembering: '#bfbfbf',
    understanding: '#1890ff',
    applying: '#52c41a',
    analyzing: '#722ed1',
    evaluating: '#eb2f96',
    creating: '#13c2c2',
  };
  return map[bloom.toLowerCase()] || '#1890ff';
};

// 获取状态颜色
const getOverallStatusColor = (status: string): string => {
  if (status.includes('优秀')) return 'arcoblue';
  if (status.includes('良好')) return 'blue';
  if (status.includes('一般')) return 'orange';
  if (status.includes('较差')) return 'red';
  return 'gray';
};

// 格式化时间
const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// ==================== 基于教育学理论的建议生成 ====================

interface ClassroomSuggestion {
  theory: string;
  icon: string;
  title: string;
  content: string;
  priority: 'high' | 'medium' | 'low';
}

const generateClassroomSuggestions = (result: any): ClassroomSuggestion[] => {
  if (!result?.classroom_metrics?.educational) {
    // 即使无教育学数据，也基于基本指标生成建议
    const baseSuggestions: ClassroomSuggestion[] = [];
    const focusRate = result?.classroom_metrics?.focus_rate || 0;
    if (focusRate < 0.6) {
      baseSuggestions.push({
        theory: '课堂注意力管理',
        icon: '⏰',
        title: '整体专注率偏低，需结构性干预',
        content: '当前课堂专注率不足60%，建议采用"20-20-20法则"：每20分钟切换一次教学模态(讲授→讨论→练习→视频)，每次切换不超过20秒过渡时间，保持20%的内容具有挑战性。',
        priority: 'high',
      });
    }
    baseSuggestions.push({
      theory: 'Fredricks三维投入模型',
      icon: '🧠',
      title: '持续优化三维学习投入',
      content: '无论课堂状态如何，建议每节课设计至少1个"认知冲突任务"(迫使学生从被动听转为主动想)、1个"情感连接时刻"(与学生生活经验关联)、1个"身体参与环节"(站立讨论/白板书写)。',
      priority: 'medium',
    });
    return baseSuggestions;
  }

  const edu = result.classroom_metrics.educational;
  const suggestions: ClassroomSuggestion[] = [];

  // 1. Fredricks 三维学习投入模型建议
  const bei = edu.behavioral_engagement || 0;
  const cei = edu.cognitive_engagement || 0;
  const eei = edu.emotional_engagement || 0;
  const lei = edu.learning_engagement_index || 0;

  if (cei < 0.5 && bei > 0.6) {
    suggestions.push({
      theory: 'Fredricks三维投入模型',
      icon: '🧠',
      title: '认知投入不足，行为投入虚高',
      content: '学生身体在场但思维游离。建议引入"思考-配对-分享"(Think-Pair-Share)策略，每15分钟设置一个认知冲突点，强迫大脑从被动接收转为主动加工。同时采用"一分钟论文"(One-Minute Paper)即时检验理解深度。',
      priority: 'high',
    });
  } else if (eei < 0.4) {
    suggestions.push({
      theory: 'Fredricks三维投入模型',
      icon: '❤️',
      title: '情感投入偏低，课堂氛围冷淡',
      content: '情感投入是深度学习的前提。建议运用"情感锚点"技术：在讲解抽象概念时嵌入与学生生活经验相关的案例，或采用"惊喜-悬念"开场法提升情绪唤醒度。也可使用"情绪温度计"让学生匿名反馈当前感受。',
      priority: 'high',
    });
  } else if (bei < 0.5) {
    suggestions.push({
      theory: 'Fredricks三维投入模型',
      icon: '✍️',
      title: '行为投入低，学生参与度不足',
      content: '建议采用"随机提问+即时板书"组合策略，配合走动式教学(Proximity Teaching)增加教师的物理存在感，减少后排学生的"匿名感"。同时引入"举手投票+手势回应"让每个学生都有动作参与。',
      priority: 'medium',
    });
  }

  // 无论BEI/CEI/EEI如何，都给出均衡性建议
  const maxDim = Math.max(bei, cei, eei);
  const minDim = Math.min(bei, cei, eei);
  if (maxDim - minDim > 0.3) {
    suggestions.push({
      theory: 'Fredricks三维投入模型',
      icon: '⚖️',
      title: '三维投入不均衡，存在短板效应',
      content: `行为${(bei*100).toFixed(0)}%/认知${(cei*100).toFixed(0)}%/情感${(eei*100).toFixed(0)}%差距超过30个百分点。学习投入如同三脚凳，任何一条腿过短都会导致整体不稳。建议针对最低维度设计专项干预。`,
      priority: 'medium',
    });
  }

  // 2. Bloom 认知分类法建议
  const bloom = edu.bloom_distribution || {};
  const lowerOrder = (bloom.remembering || 0) + (bloom.understanding || 0);
  const higherOrder = (bloom.analyzing || 0) + (bloom.evaluating || 0) + (bloom.creating || 0);
  if (lowerOrder > 0.7) {
    suggestions.push({
      theory: 'Bloom认知分类法',
      icon: '📊',
      title: '高阶思维训练严重不足',
      content: `当前${(lowerOrder * 100).toFixed(0)}%的认知活动停留在记忆/理解层面。建议将讲授内容重构为"问题链"：从"是什么"(记忆) → "为什么"(分析) → "怎么办"(创造)，每节课至少设计2个需要综合应用的高阶任务。使用苏格拉底提问法逐步提升思维层级。`,
      priority: 'high',
    });
  } else if (higherOrder > 0.5) {
    suggestions.push({
      theory: 'Bloom认知分类法',
      icon: '🚀',
      title: '高阶思维活跃，注意支架搭建',
      content: '学生已进入分析/评价/创造层级，但需要足够的"认知支架"(Scaffolding)。建议在抛出开放性问题前，先提供思维导图或分析框架，避免认知超载导致的挫败感。采用"同伴互评+迭代修正"巩固高阶成果。',
      priority: 'medium',
    });
  } else {
    suggestions.push({
      theory: 'Bloom认知分类法',
      icon: '🎯',
      title: '认知分布中等，建议多样化任务设计',
      content: '当前认知分布较为均衡但缺乏突出优势。建议设计"分层任务卡"：基础层(记忆理解)人人必做，进阶层(应用分析)选做，挑战层(评价创造)加分。让不同水平学生都能找到认知舒适区与拉伸区。',
      priority: 'medium',
    });
  }

  // 3. 持续性注意力动态模型建议
  const trend = edu.attention_trend || 'stable';
  const phase = edu.attention_cycle_phase || 'unknown';
  if (trend === 'declining') {
    suggestions.push({
      theory: '注意力动态模型',
      icon: '⏰',
      title: '注意力呈下降趋势，需立即干预',
      content: '根据持续性注意力理论，15-20分钟是注意力自然衰减周期。建议立即切换教学模态(如从讲授→小组讨论→视频案例)，利用"变化性恢复"(Variability Restoration)重置注意力曲线。插入"惊喜元素"(反常识数据/戏剧性演示)制造注意力峰值。',
      priority: 'high',
    });
  } else if (phase === 'trough') {
    suggestions.push({
      theory: '注意力动态模型',
      icon: '📉',
      title: '处于注意力波谷期',
      content: '当前处于注意力周期的波谷阶段。最有效的干预不是增加音量，而是引入"惊奇元素"(如反常识数据、戏剧化演示)或2分钟的"身体-大脑同步"活动(如站立伸展)。也可使用"快速写作"(Quick Write)让学生静默思考2分钟。',
      priority: 'medium',
    });
  } else if (trend === 'rising') {
    suggestions.push({
      theory: '注意力动态模型',
      icon: '📈',
      title: '注意力回升期，抓住黄金窗口',
      content: '注意力正处于上升通道，这是传递核心知识点的最佳时机。建议将本节课最重要的概念/技能安排在此阶段讲解，配合"精细复述"(Elaborative Rehearsal)加深记忆痕迹。避免在此时处理行政事务。',
      priority: 'low',
    });
  } else {
    suggestions.push({
      theory: '注意力动态模型',
      icon: '🔄',
      title: '注意力平稳期，预防性维持',
      content: '当前注意力处于平稳状态，建议采取预防性策略维持：每10分钟插入一个"微互动"(投票/提问/手势回应)，每20分钟进行一次"模态切换"(听→看→做→说)。提前规划好注意力"蓄水池"。',
      priority: 'low',
    });
  }

  // 4. 社会传染理论建议
  const contagion = edu.contagion_index || 0;
  if (contagion > 0.6) {
    suggestions.push({
      theory: '社会传染理论',
      icon: '🔥',
      title: '分心行为存在社会传染风险',
      content: `社会传染指数${(contagion * 100).toFixed(0)}%，表明分心行为正在空间上聚集扩散。建议立即采用"物理隔离法"：让走神学生更换座位(打破传染网络)，或使用"同伴教学"让高投入学生带动周围。同时增加教师的"物理存在感"，走到分心区域附近讲课。`,
      priority: 'high',
    });
  } else if (contagion < 0.2) {
    suggestions.push({
      theory: '社会传染理论',
      icon: '🛡️',
      title: '课堂注意力免疫良好，正向强化',
      content: '低传染指数说明课堂已形成积极的"注意力免疫屏障"。建议强化这一优势：公开表扬专注学生的具体行为(而非笼统夸奖)，利用"正向传染"效应巩固课堂氛围。可让高投入学生担任"学习伙伴"，扩大正向影响半径。',
      priority: 'low',
    });
  } else {
    suggestions.push({
      theory: '社会传染理论',
      icon: '👥',
      title: '中等传染水平，建立防火墙',
      content: `社会传染指数${(contagion * 100).toFixed(0)}%处于中等水平。建议采用"正向节点植入"策略：在易分心区域(后排/角落)安排高投入学生作为"注意力锚点"，通过同伴效应形成局部正向场域。同时监控传染热点区域。`,
      priority: 'medium',
    });
  }

  // 5. 综合LEI建议（始终添加）
  if (lei < 0.5) {
    suggestions.push({
      theory: '综合学习投入指数',
      icon: '📉',
      title: '整体学习投入指数偏低',
      content: `LEI仅${(lei*100).toFixed(0)}%，表明课堂整体学习效能不足。建议采用"目标-反馈-调整"循环：每节课开始时明确学习目标(What/Why/How)，中间进行形成性评价(即时测验/手势反馈)，结束时让学生自评目标达成度。`,
      priority: 'high',
    });
  } else if (lei > 0.8) {
    suggestions.push({
      theory: '综合学习投入指数',
      icon: '🏆',
      title: '高学习投入，注意认知负荷',
      content: `LEI高达${(lei*100).toFixed(0)}%，学生处于高度投入状态。注意监控认知负荷，避免"过度投入导致的疲劳"。建议在高强度学习后插入5分钟的"认知卸载"活动(如轻松讨论/幽默视频)，保护学生的持续学习能力。`,
      priority: 'low',
    });
  }

  return suggestions;
};

const generatePersonalSuggestion = (person: any): string => {
  if (!person.educational) {
    if (person.behavior === '睡觉') return '深度睡眠状态，建议课后沟通了解原因（熬夜/内容过难/身体不适）。';
    if (person.behavior === '查看手机') return '注意力被外部刺激捕获，建议将手机收纳至统一位置或使用"手机监狱"。';
    if (person.behavior === '与他人交谈') return '社交需求压倒了学习任务，建议安排其担任小组汇报人以转化社交动机。';
    return '保持当前学习状态。';
  }
  const edu = person.educational;
  const lei = (edu.lei || 0) * 100;
  const bloom = edu.bloom_level || '';
  const mindWander = edu.mind_wandering;

  if (mindWander) {
    return '走神警报！建议采用"锚定技术"：在桌面放置 tactile 物品(如压力球)，当注意力飘移时通过触觉反馈自我提醒。';
  }
  if (lei < 40) {
    return '学习投入极低。建议教师进行1对1微交流(30秒)，了解是内容难度还是动机问题，避免公开点名造成羞耻感。';
  }
  if (bloom === 'remembering' || bloom === 'understanding') {
    return '处于低阶认知层级。建议为其提供"挑战升级路径"：在完成基础任务后，尝试用比喻/类比向同伴解释概念。';
  }
  if (bloom === 'creating' || bloom === 'evaluating') {
    return '高阶思维活跃！建议担任"认知示范者"，向同伴展示思考过程，教是最好的学。';
  }
  if (lei > 75) {
    return '深度投入状态。注意保护其"心流"(Flow)体验，避免不必要的打断。';
  }
  return '学习状态平稳，建议适度增加认知挑战以维持注意力曲线。';
};

// 查看所有记录
const viewAllRecords = () => {
  Message.info('查看所有历史记录功能待实现');
};

// 组件挂载
onMounted(() => {
  loadBehaviorDefinitions();
  loadRecentRecords();

  refreshInterval = setInterval(() => {
    if (detectionStatus.value !== 'running') {
      loadRecentRecords();
    }
  }, 30000);

  window.addEventListener('resize', onResize);
});

// 组件卸载
onBeforeUnmount(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  window.removeEventListener('resize', onResize);
});
</script>

<style scoped lang="less">
.behavior-detection-card {
  .detection-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .upload-area {
    .upload-buttons {
      display: flex;
      gap: 8px;
    }
  }

  .upload-preview-area {
    .video-container {
      position: relative;
      width: 100%;
      min-height: 500px;
      max-height: none;
      background: #000;
      border-radius: 8px;
      overflow: hidden;
    }

    .preview-image {
      display: block;
      width: 100%;
      height: auto;
      object-fit: contain;
    }

    .detection-canvas {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }

    .detection-overlay {
      position: absolute;
      top: 8px;
      left: 8px;
    }

    .score-badge {
      padding: 4px 12px;
      border-radius: 4px;
      color: #fff;
      font-size: 14px;
      font-weight: 600;
    }
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 12px;

    .stat-item {
      text-align: center;
      padding: 8px;
      background: #f5f5f5;
      border-radius: 8px;

      .stat-label {
        font-size: 12px;
        color: #666;
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: 20px;
        font-weight: 600;
      }
    }
  }

  .upload-stats {
    .edu-overview {
      display: flex;
      gap: 12px;
      margin-bottom: 12px;
      padding: 8px;
      background: #f0f7ff;
      border-radius: 8px;

      .edu-row {
        display: flex;
        align-items: center;
        gap: 6px;

        .edu-label {
          font-size: 12px;
          color: #666;
        }

        .edu-value {
          font-size: 14px;
          font-weight: 600;
          color: #333;
        }
      }
    }

    .edu-person-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 520px;
      overflow-y: auto;

      .edu-person-card {
        padding: 10px;
        background: #fafafa;
        border-radius: 8px;
        border: 1px solid #f0f0f0;

        .edu-person-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;

          .edu-person-id {
            font-size: 13px;
            font-weight: 600;
            color: #333;
          }
        }

        .edu-person-body {
          display: flex;
          flex-direction: column;
          gap: 6px;

          .edu-metric-row {
            display: flex;
            align-items: center;
            gap: 8px;

            .edu-metric-label {
              font-size: 12px;
              color: #666;
              min-width: 48px;
            }

            .edu-metric-value {
              font-size: 12px;
              font-weight: 600;
              color: #333;
              min-width: 32px;
              text-align: right;
            }
          }

          .edu-dimensions {
            display: flex;
            gap: 8px;
            margin-top: 4px;

            .edu-dim {
              font-size: 11px;
              color: #888;
              background: #f0f0f0;
              padding: 2px 6px;
              border-radius: 4px;
            }
          }
        }
      }
    }

    .behavior-list {
      .behavior-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .behavior-name {
          width: 80px;
          font-size: 12px;
          color: #333;
        }

        .behavior-confidence {
          flex: 1;
        }
      }
    }
  }

  .recent-records {
    .record-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;

      .record-time {
        font-size: 12px;
        color: #666;
      }
    }
  }

  .video-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 150px;
    background: #f5f5f5;
    border-radius: 8px;
    color: #999;

    .icon {
      font-size: 40px;
      margin-bottom: 8px;
    }
  }

  // 教育学理论框架展示
  .theory-framework-panel {
    background: linear-gradient(135deg, #f0f5ff 0%, #e6f7ff 100%);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    border: 1px solid #d6e4ff;

    .theory-title {
      font-size: 15px;
      font-weight: 600;
      color: #1d39c4;
      text-align: center;
      margin-bottom: 12px;
    }

    .theory-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }

    .theory-card {
      background: #fff;
      border-radius: 8px;
      padding: 10px;
      text-align: center;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      .theory-icon {
        font-size: 22px;
        margin-bottom: 4px;
      }

      .theory-name {
        font-size: 12px;
        font-weight: 600;
        color: #333;
        margin-bottom: 2px;
      }

      .theory-desc {
        font-size: 10px;
        color: #666;
      }
    }
  }

  // 教育学模块参数
  .edu-metrics-panel {
    background: #fff;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);

    .edu-metrics-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }

    .edu-metric-item {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 8px;

      .edu-metric-label {
        font-size: 11px;
        color: #666;
        margin-bottom: 4px;
      }

      .edu-metric-num {
        font-size: 16px;
        font-weight: 700;
        color: #333;
        text-align: right;
        margin-top: 2px;
      }
    }

    .edu-extra-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #f0f0f0;

      .edu-extra-item {
        font-size: 11px;
        color: #555;
        background: #f0f5ff;
        padding: 3px 8px;
        border-radius: 4px;
      }
    }

    .bloom-distribution {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #f0f0f0;

      .bloom-title {
        font-size: 12px;
        font-weight: 600;
        color: #333;
        margin-bottom: 6px;
      }

      .bloom-bars {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .bloom-bar-item {
        display: flex;
        align-items: center;
        gap: 6px;

        .bloom-label {
          font-size: 11px;
          color: #666;
          width: 70px;
          text-align: right;
        }

        .bloom-pct {
          font-size: 11px;
          color: #333;
          width: 36px;
          text-align: right;
        }
      }
    }
  }

  // 课堂建议面板
  .edu-suggestions-panel {
    background: #fff;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);

    .suggestion-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .suggestion-item {
      border-radius: 8px;
      padding: 10px;
      border-left: 4px solid #52c41a;
      background: #f6ffed;

      &.priority-high {
        border-left-color: #f5222d;
        background: #fff2f0;
      }

      &.priority-medium {
        border-left-color: #faad14;
        background: #fffbe6;
      }

      .suggestion-header {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 4px;

        .suggestion-icon {
          font-size: 16px;
        }

        .suggestion-theory {
          font-size: 11px;
          color: #888;
          flex: 1;
        }
      }

      .suggestion-title {
        font-size: 13px;
        font-weight: 600;
        color: #333;
        margin-bottom: 4px;
      }

      .suggestion-content {
        font-size: 12px;
        color: #555;
        line-height: 1.6;
      }
    }

    .suggestion-empty {
      text-align: center;
      color: #999;
      font-size: 13px;
      padding: 16px;
    }
  }

  // 个人建议
  .edu-person-suggestion {
    margin-top: 6px;
    padding: 6px 8px;
    background: #e6f7ff;
    border-radius: 6px;
    font-size: 11px;
    color: #0958d9;
    line-height: 1.5;
  }

  // 姿态参数
  .edu-posture-params {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
    margin: 6px 0;
    padding: 6px;
    background: #f5f5f5;
    border-radius: 6px;

    .posture-row {
      display: flex;
      align-items: center;
      gap: 4px;

      .posture-label {
        font-size: 10px;
        color: #888;
        min-width: 32px;
      }

      .posture-value {
        font-size: 11px;
        color: #333;
        font-weight: 500;
      }
    }
  }

  // 走神警告
  .edu-wander-alert {
    margin-top: 4px;
    padding: 4px 8px;
    background: #fff2f0;
    border: 1px solid #ffccc7;
    border-radius: 4px;
    font-size: 11px;
    color: #cf1322;
    font-weight: 500;
  }

  // AI个性化学习方案
  .ai-learning-plan-panel {
    background: linear-gradient(135deg, #f6ffed 0%, #e6fffb 100%);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    border: 1px solid #b7eb8f;

    .ai-plan-desc {
      font-size: 12px;
      color: #555;
      margin-bottom: 10px;
      text-align: center;
    }

    .ai-plan-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
    }

    .ai-report-preview {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #d9f7be;
    }
  }
}
</style>
