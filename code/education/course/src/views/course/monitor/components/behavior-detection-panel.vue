<template>
  <a-card
    class="general-card behavior-detection-card"
    :title="$t('monitor.behaviorDetection.title')"
  >
    <template #extra>
      <a-tag :color="detectionStatus === 'running' ? 'green' : 'gray'">
        {{ detectionStatus === 'running' ? '检测中' : '未启动' }}
      </a-tag>
    </template>

    <div class="detection-content">
      <!-- 实时视频预览区域 -->
      <div class="video-preview-area">
        <div v-if="detectionStatus === 'running'" class="video-container">
          <img
            v-if="currentFrame"
            :src="currentFrame"
            alt="实时检测画面"
            class="preview-image"
          />
          <div v-else class="placeholder">
            <IconVideoCamera class="icon" />
            <span>等待视频流...</span>
          </div>

          <!-- 检测结果叠加层 -->
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

        <div v-else class="video-placeholder">
          <IconVideoCamera class="icon" />
          <span>点击"开启课堂行为检测"开始分析</span>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="control-buttons">
        <a-button
          long
          type="primary"
          :loading="isStarting"
          :disabled="detectionStatus === 'running'"
          @click="startDetection"
        >
          <template #icon>
            <IconPlayCircle />
          </template>
          {{ $t('monitor.behaviorDetection.start') }}
        </a-button>

        <a-button
          long
          status="danger"
          :disabled="detectionStatus !== 'running'"
          @click="stopDetection"
        >
          <template #icon>
            <IconPauseCircle />
          </template>
          {{ $t('monitor.behaviorDetection.stop') }}
        </a-button>
      </div>

      <!-- 实时统计 -->
      <div
        v-if="detectionStatus === 'running' && currentResult"
        class="realtime-stats"
      >
        <a-divider orientation="center">{{
          $t('monitor.behaviorDetection.realtimeStats')
        }}</a-divider>

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
            <div class="stat-value">{{ currentResult.behaviors.length }}</div>
          </div>
        </div>

        <!-- 行为列表 -->
        <div class="behavior-list">
          <div
            v-for="(behavior, index) in currentResult.behaviors"
            :key="index"
            class="behavior-item"
          >
            <div class="behavior-name">{{ behavior.behavior }}</div>
            <div class="behavior-confidence">
              <a-progress
                :percent="Math.round(behavior.confidence * 100)"
                :color="getBehaviorColor(behavior.behavior)"
                size="small"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 历史记录快捷入口 -->
      <div v-if="recentRecords.length > 0" class="recent-records">
        <a-divider orientation="center">{{
          $t('monitor.behaviorDetection.recentRecords')
        }}</a-divider>
        <a-list :bordered="false" size="small">
          <a-list-item
            v-for="record in recentRecords.slice(0, 3)"
            :key="record.id"
          >
            <div class="record-item">
              <span class="record-time">{{
                formatTime(record.timestamp)
              }}</span>
              <a-tag :color="getStatusColor(record.overall_status)">
                {{ record.overall_status }}
              </a-tag>
            </div>
          </a-list-item>
        </a-list>
        <a-button type="text" long @click="viewAllRecords">
          {{ $t('monitor.behaviorDetection.viewAll') }}
        </a-button>
      </div>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  import { ref, onMounted, onUnmounted } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import {
    IconVideoCamera,
    IconPlayCircle,
    IconPauseCircle,
  } from '@arco-design/web-vue/es/icon';
  import {
    startRealtimeAnalysis,
    getAnalysisRecords,
    getBehaviorDefinitions,
    type AnalysisRecord,
    type BehaviorDefinitionsResponse,
    type ImageAnalysisResult,
  } from '@/api/behavior-analysis';

  const props = defineProps<{
    courseId?: string;
  }>();

  // 状态
  const detectionStatus = ref<'idle' | 'running' | 'paused'>('idle');
  const isStarting = ref(false);
  const currentFrame = ref<string>('');
  const currentResult = ref<ImageAnalysisResult | null>(null);
  const recentRecords = ref<AnalysisRecord[]>([]);
  const behaviorDefinitions = ref<BehaviorDefinitionsResponse | null>(null);
  const sessionId = ref<string>('');

  // 定时器
  let detectionInterval: ReturnType<typeof setInterval> | null = null;
  let refreshInterval: ReturnType<typeof setInterval> | null = null;

  // 获取行为定义
  const loadBehaviorDefinitions = async () => {
    try {
      const res = await getBehaviorDefinitions();
      behaviorDefinitions.value = res.data;
    } catch (error) {
      Message.warning('加载行为定义失败');
    }
  };

  // 获取历史记录
  const loadRecentRecords = async () => {
    if (!props.courseId) return;
    try {
      const res = await getAnalysisRecords(props.courseId, 0, 10);
      recentRecords.value = res.data.data;
    } catch (error) {
      Message.warning('加载历史记录失败');
    }
  };

  // 模拟实时检测数据（实际项目中替换为真实的视频流处理）
  function startSimulation() {
    detectionInterval = setInterval(() => {
      // 模拟检测结果
      const mockBehaviors = [
        {
          behavior: '专注学习',
          confidence: 0.85 + Math.random() * 0.1,
          description: '学习状态良好',
          score_contribution: 0.85,
        },
        {
          behavior: '查看手机',
          confidence: 0.1 + Math.random() * 0.05,
          description: '注意力分散',
          score_contribution: -0.05,
        },
      ];

      const mockResult: ImageAnalysisResult = {
        status: 'success',
        behaviors: mockBehaviors.filter((b) => b.confidence > 0.3),
        overall_score: 0.6 + Math.random() * 0.3,
        learning_status: '学习状态良好',
        timestamp: new Date().toISOString(),
      };

      currentResult.value = mockResult;
    }, 3000);
  }

  // 开始检测
  const startDetection = async () => {
    if (!props.courseId) {
      Message.warning('请先选择课程');
      return;
    }

    isStarting.value = true;
    try {
      const res = await startRealtimeAnalysis(props.courseId);
      sessionId.value = res.data.session_id;
      detectionStatus.value = 'running';
      Message.success('课堂行为检测已启动');

      // 模拟实时检测（实际项目中这里应该连接WebSocket或轮询视频流）
      startSimulation();
    } catch {
      Message.error('启动检测失败');
    } finally {
      isStarting.value = false;
    }
  };

  // 停止检测
  const stopDetection = () => {
    detectionStatus.value = 'idle';
    if (detectionInterval) {
      clearInterval(detectionInterval);
      detectionInterval = null;
    }
    currentFrame.value = '';
    currentResult.value = null;
    Message.success('检测已停止');
    loadRecentRecords();
  };

  // 获取分数颜色
  const getScoreColor = (score: number): string => {
    if (score >= 0.7) return '#52c41a';
    if (score >= 0.3) return '#1890ff';
    if (score >= -0.3) return '#faad14';
    if (score >= -0.7) return '#fa541c';
    return '#f5222d';
  };

  // 获取行为颜色
  const getBehaviorColor = (behaviorName: string): string => {
    const behavior = behaviorDefinitions.value?.behaviors.find(
      (b) => b.name === behaviorName
    );
    return behavior?.color || '#1890ff';
  };

  // 获取状态颜色
  const getStatusColor = (status: string): string => {
    if (status.includes('优秀')) return 'green';
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

  // 查看所有记录
  const viewAllRecords = () => {
    // 可以跳转到分析历史页面
    Message.info('查看所有历史记录功能待实现');
  };

  // 组件挂载
  onMounted(() => {
    loadBehaviorDefinitions();
    loadRecentRecords();

    // 定期刷新历史记录
    refreshInterval = setInterval(() => {
      if (detectionStatus.value !== 'running') {
        loadRecentRecords();
      }
    }, 30000);
  });

  // 组件卸载
  onUnmounted(() => {
    if (detectionInterval) {
      clearInterval(detectionInterval);
    }
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });
</script>

<style scoped lang="less">
  .behavior-detection-card {
    .detection-content {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .video-preview-area {
      .video-container {
        position: relative;
        width: 100%;
        height: 150px;
        background: #000;
        border-radius: 8px;
        overflow: hidden;

        .preview-image {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: #fff;

          .icon {
            font-size: 32px;
            margin-bottom: 8px;
          }
        }

        .detection-overlay {
          position: absolute;
          top: 8px;
          right: 8px;

          .score-badge {
            padding: 4px 8px;
            border-radius: 4px;
            color: #fff;
            font-size: 12px;
            font-weight: 500;
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
    }

    .control-buttons {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .realtime-stats {
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
  }
</style>
