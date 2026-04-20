<template>
  <div class="studio-page">
    <Breadcrumb :items="['menu.digitalHuman', 'menu.digitalHuman.tools']" />
    <div class="studio-shell">
      <header class="studio-header">
        <div>
          <h1>数字人创作舱</h1>
          <p>围绕课程内容生成、数字人演绎与作品沉淀，打造一体化教学创作流程</p>
        </div>
        <a-space>
          <a-tag color="arcoblue">智屿 Studio</a-tag>
          <a-tag color="purple">多模态生成链路</a-tag>
        </a-space>
      </header>

      <div class="studio-layout">
        <section class="studio-nav">
          <router-link
            v-for="tool in tools"
            :key="tool.name"
            :to="tool.to"
            class="tool-card"
          >
            <div class="tool-head">
              <span class="tool-icon">{{ tool.icon }}</span>
              <icon-right class="tool-arrow" />
            </div>
            <h3>{{ tool.name }}</h3>
            <p>{{ tool.desc }}</p>
          </router-link>
        </section>

        <section class="studio-workbench">
          <h3>创作流程导引</h3>
          <div class="workflow-list">
            <div class="workflow-item" v-for="(step, idx) in workflow" :key="step.title">
              <span class="step-index">{{ idx + 1 }}</span>
              <div>
                <p class="step-title">{{ step.title }}</p>
                <p class="step-desc">{{ step.desc }}</p>
              </div>
            </div>
          </div>
        </section>

        <section class="studio-preview">
          <div class="preview-screen">
            <img :src="studioCover" alt="数字人实时预览" />
            <div class="preview-glow" />
            <div class="preview-badge">LIVE PREVIEW</div>
          </div>
          <p class="preview-caption">
            生成完成后在此区域展示数字人实机画面，可用于课堂讲解与课程宣传。
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { IconRight } from '@arco-design/web-vue/es/icon';
  import studioCover from '@/assets/digital-human/studio-cover.png';

  const tools = [
    {
      name: '文本生成视频',
      icon: '📝',
      desc: '输入脚本内容，快速生成数字人口播视频',
      to: '/digital-human/text-to-video',
    },
    {
      name: 'PPT 生成视频',
      icon: '📊',
      desc: '上传教学 PPT，自动生成分段讲解视频',
      to: { name: 'PptToVideo' },
    },
    {
      name: '数字人克隆',
      icon: '🧬',
      desc: '基于照片和声音样本，创建个性化数字人',
      to: { name: 'DigitalHumanClone' },
    },
    {
      name: '我的数字人',
      icon: '🎬',
      desc: '统一管理数字人素材、成片与模板',
      to: { name: 'MyDigitalHumans' },
    },
  ];

  const workflow = [
    { title: '课程脚本准备', desc: '输入课程目标与讲解内容，智屿自动优化表达结构' },
    { title: '数字人形象选择', desc: '选择教师形象、音色和镜头风格，统一课堂品牌形象' },
    { title: '视频渲染输出', desc: '生成讲解成片并支持后续章节扩写与批量导出' },
  ];
</script>

<script lang="ts">
  export default {
    name: 'DigitalHumanTools',
  };
</script>

<style scoped lang="less">
  .studio-page {
    padding: 0 20px 24px;
    min-height: 100%;
    background:
      radial-gradient(circle at 12% -10%, rgba(99, 102, 241, 0.2), transparent 42%),
      radial-gradient(circle at 92% 8%, rgba(14, 165, 233, 0.18), transparent 40%),
      linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
  }

  .studio-shell {
    max-width: 1320px;
    margin: 0 auto;
    padding: 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(10px);
  }

  .studio-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 16px;
    h1 {
      margin: 0;
      font-size: 30px;
      font-weight: 700;
      color: #0f172a;
    }
    p {
      margin: 8px 0 0;
      color: #64748b;
    }
  }

  .studio-layout {
    display: grid;
    grid-template-columns: 28% 32% 40%;
    gap: 14px;
  }

  .studio-nav,
  .studio-workbench,
  .studio-preview {
    min-height: 560px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(255, 255, 255, 0.75);
    box-shadow: 0 14px 36px rgba(15, 23, 42, 0.1);
  }

  .studio-nav {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    padding: 12px;
  }

  .tool-card {
    padding: 16px;
    min-height: 122px;
    background: rgba(255, 255, 255, 0.75);
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    transition: transform 0.26s ease, box-shadow 0.26s ease;
    text-align: left;
    text-decoration: none;
    color: inherit;
    &:hover {
      transform: translateY(-4px);
      border-color: rgba(99, 102, 241, 0.4);
      box-shadow:
        0 18px 36px rgba(15, 23, 42, 0.14),
        0 0 55px rgba(99, 102, 241, 0.2);
      .tool-arrow {
        transform: translateX(4px);
      }
    }
    h3 {
      margin: 10px 0 6px;
      font-size: 18px;
      color: #0f172a;
    }
    p {
      margin: 0;
      font-size: 13px;
      line-height: 1.5;
      color: #64748b;
    }
  }

  .tool-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .tool-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
  }

  .tool-arrow {
    color: #64748b;
    transition: transform 0.2s ease;
  }

  .studio-workbench {
    padding: 16px;
    h3 {
      margin: 0 0 12px;
      font-size: 20px;
      color: #0f172a;
    }
  }

  .workflow-list {
    display: grid;
    gap: 10px;
  }

  .workflow-item {
    display: flex;
    gap: 10px;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(255, 255, 255, 0.76);
    padding: 12px;
  }

  .step-index {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: linear-gradient(135deg, #4f46e5, #0ea5e9);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    flex-shrink: 0;
  }

  .step-title {
    margin: 0;
    color: #0f172a;
    font-weight: 600;
  }

  .step-desc {
    margin: 5px 0 0;
    color: #64748b;
    font-size: 13px;
    line-height: 1.55;
  }

  .studio-preview {
    padding: 16px;
    background: #0b1220;
    border-color: rgba(56, 189, 248, 0.32);
  }

  .preview-screen {
    position: relative;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(56, 189, 248, 0.4);
    aspect-ratio: 16 / 9;
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .preview-glow {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(circle at 50% 120%, rgba(56, 189, 248, 0.3), transparent 52%);
  }

  .preview-badge {
    position: absolute;
    right: 12px;
    top: 10px;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #fff;
    background: rgba(2, 6, 23, 0.55);
    border: 1px solid rgba(56, 189, 248, 0.48);
  }

  .preview-caption {
    margin: 12px 0 0;
    color: #cbd5e1;
    line-height: 1.6;
    font-size: 13px;
  }

  @media (max-width: @screen-md) {
    .studio-layout {
      grid-template-columns: 1fr;
    }
    .studio-nav,
    .studio-workbench,
    .studio-preview {
      min-height: auto;
    }
  }
</style>
