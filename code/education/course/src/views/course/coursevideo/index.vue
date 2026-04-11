<template>
  <div class="course-video-root">
    <a-layout class="cv-outer">
      <a-layout-content class="cv-main">
        <div
          class="main"
          style="
            display: flex;
            flex-direction: column;
            width: 90%;
            padding: 20px;
            overflow-y: hidden;
          "
        >
          <div
            class="top"
            style="
              width: 100%;
              height: 500px;
              text-align: center;
              background-color: #fff;
            "
          >
            <div
              class="video1"
              style="
                display: flex;
                align-items: center;
                justify-content: center;
                width: 70%;
                margin-top: 20px;
              "
            >
              <input
                ref="videoFileInput"
                type="file"
                style="display: none"
                @change="handleVideoUpload"
              />
            </div>
            <video
              controls
              style="width: 90%; height: 90%; object-fit: cover"
              poster="@/assets/images/AI.jpg"
            >
              <source src="@/assets/images/AI.jpg" type="video/mp4" />
              您的浏览器不支持视频标签。
            </video>
          </div>
          <div
            class="second"
            style="width: 100%; height: 35%; margin: 20px 0; background: #fff"
          >
            <p
              style="
                margin: 0;
                margin-top: 15px;
                margin-left: 10px;
                font-weight: 600;
                font-size: 20px;
              "
              >内容时段划分</p
            >
            <div
              style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 300px;
                margin-left: 5%;
              "
            >
              <VideoInfo />
            </div>
          </div>
          <CourseKnowledgePanels />
        </div>
        <div class="menu-demo">
          <a-menu
            :style="{ width: '250px', height: '100%' }"
            :default-open-keys="['0']"
            :default-selected-keys="['0_1']"
            show-collapse-button
          >
            <a-menu-item key="0_0_0" data-obj="1" disabled
              >人工智能</a-menu-item
            >
            <a-sub-menu key="0">
              <template #icon><icon-apps></icon-apps></template>
              <template #title>Chapter 1</template>
              <a-menu-item key="0_0">人工智能发展史</a-menu-item>
              <a-menu-item key="0_1">人工智能主要应用领域</a-menu-item>
              <a-menu-item key="0_2">人工智能常见术语</a-menu-item>
            </a-sub-menu>
            <a-sub-menu key="1">
              <template #icon><icon-bug></icon-bug></template>
              <template #title>Chapter 2</template>
              <a-menu-item key="1_0">监督学习与无监督学习</a-menu-item>
              <a-menu-item key="1_1">常见机器学习算法</a-menu-item>
              <a-menu-item key="1_2">模型评估与优化</a-menu-item>
            </a-sub-menu>
            <a-sub-menu key="2">
              <template #icon><icon-bulb></icon-bulb></template>
              <template #title>Chapter 3</template>
              <a-menu-item-group title="神经网络基础">
                <a-menu-item key="2_0">感知机与前馈神经网络</a-menu-item>
                <a-menu-item key="2_1">反向传播算法</a-menu-item>
              </a-menu-item-group>
              <a-menu-item-group title="深度学习应用">
                <a-menu-item key="2_2">卷积神经网络</a-menu-item>
                <a-menu-item key="2_3">循环神经网络</a-menu-item>
              </a-menu-item-group>
            </a-sub-menu>
          </a-menu>
        </div>
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script>
  import { IconApps, IconBug, IconBulb } from '@arco-design/web-vue/es/icon';
  import VideoInfo from './components/VideoInfo.vue';
  import CourseKnowledgePanels from './components/CourseKnowledgePanels.vue';

  export default {
    name: 'CourseVideoPage',
    components: {
      VideoInfo,
      CourseKnowledgePanels,
      IconApps,
      IconBug,
      IconBulb,
    },
    data() {
      return {
        videoSrc: null, // 用于存储视频的URL
        showUploadModal: false, // 控制弹窗显示
        videoName: '', // 视频名称
        videoDescription: '', // 视频简介
        isChartRendered: false,
        isVideoInfoVisible: false,
        chartValues: [1, 2, 3, 4, 5], // 动态数据
      };
    },
    methods: {
      renderChart() {
        this.isChartRendered = true;
      },
      toggleVideoInfo() {
        this.isVideoInfoVisible = true;
      },
      handleVideoUpload(event) {
        const file = event.target.files[0];
        if (file) {
          const fileNameWithoutExtension = file.name
            .split('.')
            .slice(0, -1)
            .join('.'); // 去掉文件后缀
          this.videoName = fileNameWithoutExtension; // 设置视频标题为去掉后缀的文件名
          const reader = new FileReader();
          reader.onload = (e) => {
            this.videoSrc = e.target.result;
          };
          reader.readAsDataURL(file);
        }
      },
      submitVideoInfo() {
        // 这里可以添加提交视频信息的逻辑
        // console.log('视频名称:', this.videoName);
        // console.log('视频简介:', this.videoDescription);
        // 假设提交成功后，关闭弹窗
        this.showUploadModal = false;
      },
    },
  };
</script>

<style scoped>
  /* ===== 智屿课程视频页 — 品牌化 ===== */
  .cv-outer {
    width: 100%;
    background: transparent;
  }

  .cv-main {
    display: flex;
    gap: 0;
    justify-content: space-around;
    width: 100%;
  }

  .menu-demo {
    box-sizing: border-box;
    height: 825px;
    margin-top: 20px;
    margin-right: 20px;
    background-color: #F0FDF6;
    border-radius: 12px;
    border: 1px solid rgba(45, 181, 131, 0.15);
  }

  .modal {
    position: fixed;
    top: 0%;
    left: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    background-color: rgb(0 0 0 / 50%);
  }

  .modal-content {
    width: 100%;
    max-width: 400px;
    padding: 30px;
    background-color: #fff;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(45, 181, 131, 0.15);
  }

  .close {
    float: right;
    color: #5A7A68;
    font-weight: bold;
    font-size: 28px;
    cursor: pointer;
  }

  .close:hover,
  .close:focus {
    color: #2DB583;
    text-decoration: none;
    cursor: pointer;
  }

  input[type='text'],
  textarea {
    width: 100%;
    margin: 10px 0;
    padding: 10px;
    overflow: hidden;
    border: 1px solid rgba(45, 181, 131, 0.30);
    border-radius: 8px;
  }

  textarea {
    resize: vertical;
  }

  /* 提交按钮品牌绿 */
  .submit-button {
    margin-top: 10px;
    padding: 10px 20px;
    color: white;
    background-color: #2DB583;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.25s ease;
  }

  .submit-button:hover {
    background-color: #1A9E6E;
  }

  .upload-container {
    text-align: center;
  }
</style>
