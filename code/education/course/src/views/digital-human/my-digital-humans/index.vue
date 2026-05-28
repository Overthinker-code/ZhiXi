<template>
  <div class="container">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.my']" />
    <div class="content">
      <!-- 头部 -->
      <div class="header">
        <div class="back-btn" @click="goBack">
          <icon-left />
          <span>返回</span>
        </div>
        <h1 class="title">我的数字人</h1>
        <p class="subtitle">管理已创建的数字人和视频作品</p>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-cards">
        <div class="stat-card">
          <div class="stat-icon digital">
            <icon-user :size="28" />
          </div>
          <div class="stat-info">
            <p class="stat-value">{{ digitalHumanList.length }}</p>
            <p class="stat-label">数字人</p>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon video">
            <icon-video-camera :size="28" />
          </div>
          <div class="stat-info">
            <p class="stat-value">{{ videoList.length }}</p>
            <p class="stat-label">视频作品</p>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon duration">
            <icon-clock-circle :size="28" />
          </div>
          <div class="stat-info">
            <p class="stat-value">{{ totalDuration }}</p>
            <p class="stat-label">总时长(分钟)</p>
          </div>
        </div>
      </div>

      <!-- 标签页 -->
      <a-tabs v-model:active-key="activeTab" class="main-tabs" type="rounded">
        <!-- 数字人管理 -->
        <a-tab-pane key="digital-humans" title="数字人">
          <div class="section-header">
            <h3>我的数字人</h3>
            <a-button type="primary" @click="goToClone">
              <template #icon><icon-plus /></template>
              新建数字人
            </a-button>
          </div>

          <div class="digital-human-grid">
            <div
              v-for="item in digitalHumanList"
              :key="item.id"
              class="digital-human-card"
              :class="{ 'is-default': item.isDefault }"
            >
              <div class="card-image">
                <img :src="item.avatar" :alt="item.name" />
                <div v-if="item.isDefault" class="default-badge">默认</div>
                <div class="card-overlay">
                  <a-button type="primary" size="small" @click="useDigitalHuman(item)">
                    使用
                  </a-button>
                </div>
              </div>
              <div class="card-info">
                <h4 class="card-name">{{ item.name }}</h4>
                <p class="card-desc">{{ item.description }}</p>
                <div class="card-meta">
                  <span class="meta-item">
                    <icon-calendar /> {{ formatDate(item.createdAt) }}
                  </span>
                  <span class="meta-item">
                    <icon-video-camera /> {{ item.videoCount }}个视频
                  </span>
                </div>
              </div>
              <div class="card-actions">
                <a-button type="text" size="small" @click="editDigitalHuman(item)">
                  <template #icon><icon-edit /></template>
                </a-button>
                <a-button
                  v-if="!item.isDefault"
                  type="text"
                  size="small"
                  status="danger"
                  @click="deleteDigitalHuman(item)"
                >
                  <template #icon><icon-delete /></template>
                </a-button>
              </div>
            </div>

            <!-- 新建卡片 -->
            <div class="digital-human-card add-card" @click="goToClone">
              <div class="add-content">
                <icon-plus :size="40" />
                <span>新建数字人</span>
              </div>
            </div>
          </div>
        </a-tab-pane>

        <!-- 视频作品 -->
        <a-tab-pane key="videos" title="视频作品">
          <div class="section-header">
            <h3>视频作品</h3>
            <a-space>
              <a-select v-model="videoFilter" placeholder="全部类型" style="width: 120px">
                <a-option value="">全部类型</a-option>
                <a-option value="text">文本生成</a-option>
                <a-option value="ppt">PPT生成</a-option>
              </a-select>
              <a-button type="primary" @click="goToCreateVideo">
                <template #icon><icon-plus /></template>
                新建视频
              </a-button>
            </a-space>
          </div>

          <div class="video-grid">
            <div
              v-for="video in filteredVideos"
              :key="video.id"
              class="video-card"
            >
              <div class="video-thumbnail" @click="previewVideo(video)">
                <img :src="video.thumbnail" :alt="video.title" />
                <div class="video-duration">{{ video.duration }}</div>
                <div class="play-overlay">
                  <icon-play-circle :size="40" />
                </div>
              </div>
              <div class="video-info">
                <h4 class="video-title">{{ video.title }}</h4>
                <p class="video-desc">{{ video.description }}</p>
                <div class="video-meta">
                  <span class="meta-item">
                    <icon-user /> {{ video.digitalHumanName }}
                  </span>
                  <span class="meta-item">
                    <icon-calendar /> {{ formatDate(video.createdAt) }}
                  </span>
                </div>
              </div>
              <div class="video-actions">
                <a-button type="text" size="small" @click="previewVideo(video)">
                  <template #icon><icon-eye /></template>
                  预览
                </a-button>
                <a-button type="text" size="small" @click="downloadVideo(video)">
                  <template #icon><icon-download /></template>
                  下载
                </a-button>
                <a-dropdown position="bottom">
                  <a-button type="text" size="small">
                    <template #icon><icon-more /></template>
                  </a-button>
                  <template #content>
                    <a-doption @click="renameVideo(video)">重命名</a-doption>
                    <a-doption status="danger" @click="deleteVideo(video)">删除</a-doption>
                  </template>
                </a-dropdown>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="filteredVideos.length === 0" class="empty-state">
            <a-empty description="暂无视频作品">
              <a-button type="primary" @click="goToCreateVideo">立即创建</a-button>
            </a-empty>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>

    <!-- 视频预览弹窗 -->
    <a-modal
      v-model:visible="previewVisible"
      title="视频预览"
      width="800px"
      :footer="false"
    >
      <div class="video-player">
        <video v-if="currentVideo" controls :src="currentVideo.url" style="width: 100%"></video>
      </div>
      <div v-if="currentVideo" class="video-detail">
        <h4>{{ currentVideo.title }}</h4>
        <p>{{ currentVideo.description }}</p>
      </div>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Message } from '@arco-design/web-vue';
import {
  fetchDigitalHumanAssets,
  fetchDigitalHumanWorks,
  type DigitalHumanWork,
} from '@/api/digital-human';
import teacherDefaultImage from '@/assets/digital-human/teacher-default.png';
import studioCoverImage from '@/assets/digital-human/studio-cover.png';
import {
  IconLeft,
  IconUser,
  IconVideoCamera,
  IconClockCircle,
  IconPlus,
  IconEdit,
  IconDelete,
  IconCalendar,
  IconPlayCircle,
  IconEye,
  IconDownload,
  IconMore,
} from '@arco-design/web-vue/es/icon';

const router = useRouter();
const activeTab = ref('digital-humans');
const videoFilter = ref('');
const previewVisible = ref(false);
const currentVideo = ref<any>(null);

interface DigitalHumanCard {
  id: string;
  name: string;
  description: string;
  avatar: string;
  createdAt: string;
  videoCount: number;
  isDefault: boolean;
}

interface VideoCard {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  duration: string;
  type: 'text' | 'ppt';
  digitalHumanName: string;
  createdAt: string;
  url: string;
  scriptUrl?: string | null;
}

const digitalHumanList = ref<DigitalHumanCard[]>([]);
const videoList = ref<VideoCard[]>([]);

const formatFileDuration = (work: DigitalHumanWork) => {
  if (work.duration) return work.duration;
  const minutes = Math.max(1, Math.round((work.file_size || 0) / 1024 / 1024));
  return `${String(minutes).padStart(2, '0')}:00`;
};

const loadDigitalHumanLibrary = async () => {
  try {
    const [assetRes, workRes] = await Promise.allSettled([
      fetchDigitalHumanAssets(),
      fetchDigitalHumanWorks(),
    ]);
    const works =
      workRes.status === 'fulfilled' ? workRes.value.works || [] : [];
    const assets =
      assetRes.status === 'fulfilled' ? assetRes.value.assets || [] : [];

    digitalHumanList.value = (assets.length ? assets : [{ id: 'teacher-default', label: '默认教师数字人', default_voice: 'zh-CN-YunxiNeural' }]).map((asset, index) => ({
      id: asset.id,
      name: asset.label || '默认教师数字人',
      description: `适合课程讲解与资源生成，默认音色 ${asset.default_voice || 'Yunxi'}`,
      avatar: teacherDefaultImage,
      createdAt: '2026-05-01',
      videoCount: works.filter((item) => item.digital_human_id === asset.id).length,
      isDefault: index === 0,
    }));

    videoList.value = works.map((work) => ({
      id: work.id,
      title: work.title,
      description: work.description || '数字人讲解视频',
      thumbnail: studioCoverImage,
      duration: formatFileDuration(work),
      type: work.type,
      digitalHumanName: work.digital_human_name || '默认教师数字人',
      createdAt: work.created_at,
      url: work.video_url,
      scriptUrl: work.script_url,
    }));
  } catch (error) {
    Message.warning('数字人作品列表暂时不可用，请确认后端服务已启动');
  }
};

onMounted(() => {
  void loadDigitalHumanLibrary();
});

// 计算属性
const totalDuration = computed(() => {
  return videoList.value.reduce((total, video) => {
    const [min] = video.duration.split(':').map(Number);
    return total + min;
  }, 0);
});

const filteredVideos = computed(() => {
  if (!videoFilter.value) return videoList.value;
  return videoList.value.filter((v) => v.type === videoFilter.value);
});

// 方法
const goBack = () => {
  router.push('/digital-human');
};

const goToClone = () => {
  router.push('/digital-human/clone');
};

const goToCreateVideo = () => {
  router.push('/digital-human/text-to-video');
};

const useDigitalHuman = (item: any) => {
  router.push('/digital-human/text-to-video');
};

const editDigitalHuman = (item: any) => {
  Message.info(`${item.name} 为当前素材库资产，可在数字人创作舱中直接使用`);
};

const deleteDigitalHuman = (item: any) => {
  Message.info(`${item.name} 是系统教学资产，暂不支持在前端直接删除`);
};

const previewVideo = (video: any) => {
  currentVideo.value = video;
  previewVisible.value = true;
};

const downloadVideo = (video: any) => {
  if (!video.url) {
    Message.warning('该视频文件暂不可下载');
    return;
  }
  window.open(video.url, '_blank');
};

const renameVideo = (video: any) => {
  Message.info(`"${video.title}" 来自生成任务记录，暂不在前端改名`);
};

const deleteVideo = (video: any) => {
  Message.info(`"${video.title}" 已归档在后端产物目录，暂不在前端删除`);
};

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN');
};
</script>

<script lang="ts">
export default {
  name: 'MyDigitalHumans',
};
</script>

<style scoped lang="less">
.container {
  padding: 0 20px 40px 20px;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  text-align: center;
  padding: 20px 0 30px;
  position: relative;

  .back-btn {
    position: absolute;
    left: 0;
    top: 20px;
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--color-text-3);
    cursor: pointer;
    transition: color 0.3s;

    &:hover {
      color: rgb(var(--primary-5));
    }
  }

  .title {
    font-size: 28px;
    font-weight: 600;
    color: var(--color-text-1);
    margin-bottom: 8px;
  }

  .subtitle {
    font-size: 14px;
    color: var(--color-text-3);
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);

  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    &.digital {
      background: linear-gradient(135deg, #667eea, #764ba2);
    }

    &.video {
      background: linear-gradient(135deg, #f093fb, #f5576c);
    }

    &.duration {
      background: linear-gradient(135deg, #4facfe, #00f2fe);
    }
  }

  .stat-info {
    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: var(--color-text-1);
      line-height: 1.2;
    }

    .stat-label {
      font-size: 14px;
      color: var(--color-text-3);
      margin-top: 4px;
    }
  }
}

.main-tabs {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text-1);
    margin: 0;
  }
}

.digital-human-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

.digital-human-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.5);
  transition: all 0.3s;
  position: relative;

  &:hover {
    transform: translateY(-6px);
    box-shadow:
      0 18px 42px rgba(15, 23, 42, 0.14),
      0 0 55px color-mix(in srgb, var(--zy-color-brand, #6366f1) 26%, transparent);
  }

  &.is-default {
    border-color: rgb(var(--primary-5));
  }

  &.add-card {
    border-style: dashed;
    cursor: pointer;
    min-height: 280px;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      border-color: rgb(var(--primary-5));
      background: rgb(var(--primary-1));
    }

    .add-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      color: var(--color-text-3);

      span {
        font-size: 14px;
      }
    }
  }

  .card-image {
    position: relative;
    width: 100%;
    aspect-ratio: 1;
    overflow: hidden;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .default-badge {
      position: absolute;
      top: 12px;
      left: 12px;
      background: rgb(var(--primary-5));
      color: #fff;
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 4px;
    }

    .card-overlay {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.3s;
    }

    &:hover .card-overlay {
      opacity: 1;
    }
  }

  .card-info {
    padding: 16px;

    .card-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-text-1);
      margin-bottom: 8px;
    }

    .card-desc {
      font-size: 13px;
      color: var(--color-text-3);
      margin-bottom: 12px;
      line-height: 1.5;
    }

    .card-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;

      .meta-item {
        font-size: 12px;
        color: var(--color-text-4);
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }

  .card-actions {
    position: absolute;
    top: 12px;
    right: 12px;
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.3s;

    .arco-btn {
      background: rgba(255, 255, 255, 0.9);
    }
  }

  &:hover .card-actions {
    opacity: 1;
  }
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.video-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.5);
  transition: all 0.3s;

  &:hover {
    transform: translateY(-6px);
    box-shadow:
      0 18px 42px rgba(15, 23, 42, 0.14),
      0 0 55px color-mix(in srgb, var(--zy-color-brand, #6366f1) 26%, transparent);

    .play-overlay {
      opacity: 1;
    }

    .video-thumbnail img {
      transform: scale(1.05);
    }
  }

  .video-thumbnail {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    overflow: hidden;
    cursor: pointer;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.35s ease;
    }

    .video-duration {
      position: absolute;
      bottom: 8px;
      right: 8px;
      background: rgba(0, 0, 0, 0.7);
      color: #fff;
      font-size: 12px;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .play-overlay {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      opacity: 0;
      transition: opacity 0.3s;
    }
  }

  .video-info {
    padding: 16px;

    .video-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--color-text-1);
      margin-bottom: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .video-desc {
      font-size: 13px;
      color: var(--color-text-3);
      margin-bottom: 12px;
      line-height: 1.5;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .video-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;

      .meta-item {
        font-size: 12px;
        color: var(--color-text-4);
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }

  .video-actions {
    padding: 0 16px 16px;
    display: flex;
    gap: 8px;
  }
}

.empty-state {
  padding: 60px 0;
  display: flex;
  justify-content: center;
}

.video-player {
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-detail {
  margin-top: 16px;

  h4 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: var(--color-text-3);
  }
}

@media (max-width: @screen-md) {
  .stats-cards {
    grid-template-columns: 1fr;
  }

  .digital-human-grid,
  .video-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: @screen-sm) {
  .digital-human-grid,
  .video-grid {
    grid-template-columns: 1fr;
  }
}
</style>
