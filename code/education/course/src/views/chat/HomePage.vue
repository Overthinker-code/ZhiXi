<script setup>
  import { ref, onMounted, onUnmounted } from 'vue';
  import { Search } from '@element-plus/icons-vue';
  import SearchDialog from './components/SearchDialog.vue';
  import WaveDivider from '@/components/WaveDivider.vue';

  const searchText = ref('');
  const showSearchDialog = ref(false);
  const isHeaderScrolled = ref(false);

  // Header 滚动变色
  const handleHeaderScroll = () => {
    isHeaderScrolled.value = window.scrollY > 20;
  };

  // 功能亮点卡片数据（designup.md §2.2）
  const features = [
    { icon: '🧠', title: 'AI 智能问答', desc: '基于 RAG 的精准知识检索，告别无效搜索，直达答案核心' },
    { icon: '🎯', title: '个性化学习路径', desc: '基于行为分析的专属推荐，让每位同学走最适合的路' },
    { icon: '👁️', title: '行为智能分析', desc: 'YOLO 实时识别，专注度可视化，帮助教师精准关注学生' },
    { icon: '📚', title: '多模态资源', desc: '视频、文档、PPT 统一检索，跨格式知识触手可得' },
    { icon: '⚡', title: '4 种 AI 模式', desc: '导师 / 考试 / 简洁 / 苏格拉底，场景切换一键完成' },
    { icon: '🔔', title: '智能预警', desc: '学习风险提前识别，教师及时介入，不让任何学生掉队' },
  ];

  // 处理搜索框点击
  const handleSearchClick = () => {
    showSearchDialog.value = true;
  };

  // 添加点击遮罩层关闭对话框的处理
  const handleOverlayClick = (event) => {
    if (event.target.classList.contains('search-dialog-overlay')) {
      showSearchDialog.value = false;
    }
  };

  // 处理点击外部关闭对话框
  const handleClickOutside = (event) => {
    const searchDialog = document.querySelector('.search-dialog');
    if (
      searchDialog &&
      !searchDialog.contains(event.target) &&
      !event.target.closest('.search-container')
    ) {
      showSearchDialog.value = false;
    }
  };

  // 处理快捷键
  const handleKeydown = (event) => {
    if (event.key === 'Escape') {
      showSearchDialog.value = false;
    }
    if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
      event.preventDefault();
      showSearchDialog.value = true;
    }
  };

  onMounted(() => {
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeydown);
    window.addEventListener('scroll', handleHeaderScroll, { passive: true });
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleKeydown);
    window.removeEventListener('scroll', handleHeaderScroll);
  });
</script>


<template>
  <div class="home-page">

    <!-- ===== Header（保留搜索交互逻辑）===== -->
    <header class="header" :class="{ 'header--scrolled': isHeaderScrolled }">
      <div class="header-left">
        <!-- 智屿品牌 Logo -->
        <div class="brand-logo">
          <svg width="32" height="32" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="18" cy="29" rx="12" ry="5" fill="#C8956C"/>
            <rect x="16.5" y="18" width="3" height="11" rx="1.5" fill="#A0714A"/>
            <circle cx="18" cy="14" r="8" fill="#6366f1"/>
            <circle cx="18" cy="7" r="1.8" fill="white" opacity="0.9"/>
            <circle cx="24.2" cy="17.5" r="1.8" fill="white" opacity="0.9"/>
            <circle cx="11.8" cy="17.5" r="1.8" fill="white" opacity="0.9"/>
          </svg>
          <div class="brand-text">
            <span class="brand-name">智屿</span>
            <span class="brand-sub">智能教育平台</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <div class="search-container" @click="handleSearchClick">
          <div class="search-input-box">
            <el-icon class="search-icon"><Search /></el-icon>
            <input type="text" placeholder="搜索课程、知识点..." readonly v-model="searchText" />
            <div class="shortcut-key">⌘ K</div>
          </div>
        </div>
      </div>
    </header>

    <!-- ===== Hero 区（designup.md §2.1）===== -->
    <main class="main-content">
      <section class="hero-section">
        <!-- 左列：文字内容 -->
        <div class="hero-left zy-fade-up">
          <!-- 1. 胶囊标签 -->
          <div class="hero-tag">
            🤖 AI 驱动 · 智慧教学
          </div>

          <!-- 2. 主标题 H1 -->
          <h1 class="hero-title">
            在知识的岛屿上<br>
            <span class="hero-title-gradient">开启智慧航行</span>
          </h1>

          <!-- 3. 副标题 -->
          <p class="hero-desc">
            智屿融合 AI 大模型、RAG 知识检索与行为分析，<br>
            为每位学生提供专属学习路径。
          </p>

          <!-- 4. 按钮组 -->
          <div class="hero-actions">
            <router-link to="/course/list" class="btn-primary">
              开始学习 →
            </router-link>
            <router-link to="/chat" class="btn-outline">
              智能问答
            </router-link>
          </div>

          <!-- 5. 数据展示行 -->
          <div class="hero-stats">
            <div class="stat-item">
              <span class="stat-num">1200+</span>
              <span class="stat-label">课程资源</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">98%</span>
              <span class="stat-label">学生满意度</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-num">50+</span>
              <span class="stat-label">合作院校</span>
            </div>
          </div>
        </div>

        <!-- 右列：插画 + 浮动卡片 -->
        <div class="hero-right">
          <!-- 主体插画：抽象岛屿知识图谱 -->
          <div class="hero-illustration">
            <svg viewBox="0 0 400 320" fill="none" xmlns="http://www.w3.org/2000/svg" class="zy-float">
              <!-- 海洋背景圆 -->
              <circle cx="200" cy="200" r="130" fill="url(#ocean-grad)" opacity="0.12"/>
              <!-- 岛屿 -->
              <ellipse cx="200" cy="240" rx="100" ry="40" fill="#C8956C" opacity="0.7"/>
              <ellipse cx="200" cy="235" rx="90" ry="30" fill="#D4A574"/>
              <!-- 树干 -->
              <rect x="193" y="170" width="14" height="70" rx="7" fill="#A0714A"/>
              <!-- 树冠大圆 -->
              <circle cx="200" cy="140" r="68" fill="url(#brand-grad)"/>
              <!-- 神经网络节点 -->
              <circle cx="200" cy="88" r="10" fill="white" opacity="0.95"/>
              <circle cx="252" cy="162" r="9" fill="white" opacity="0.90"/>
              <circle cx="148" cy="162" r="9" fill="white" opacity="0.90"/>
              <circle cx="230" cy="108" r="7" fill="white" opacity="0.80"/>
              <circle cx="170" cy="108" r="7" fill="white" opacity="0.80"/>
              <!-- 连接线 -->
              <line x1="200" y1="98" x2="200" y2="115" stroke="white" stroke-width="2" opacity="0.6"/>
              <line x1="244" y1="155" x2="228" y2="145" stroke="white" stroke-width="2" opacity="0.6"/>
              <line x1="156" y1="155" x2="172" y2="145" stroke="white" stroke-width="2" opacity="0.6"/>
              <line x1="208" y1="96" x2="225" y2="112" stroke="white" stroke-width="1.5" opacity="0.5"/>
              <line x1="192" y1="96" x2="175" y2="112" stroke="white" stroke-width="1.5" opacity="0.5"/>
              <!-- 装饰波浪 -->
              <path d="M100,265 Q150,250 200,265 Q250,280 300,265" stroke="#3B82F6" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.35"/>
              <path d="M80,285 Q160,268 240,285 Q300,298 320,278" stroke="#6366f1" stroke-width="2" stroke-linecap="round" fill="none" opacity="0.25"/>
              <!-- 渐变定义 -->
              <defs>
                <linearGradient id="brand-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#818cf8"/>
                  <stop offset="100%" stop-color="#3b82f6"/>
                </linearGradient>
                <linearGradient id="ocean-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#3B82F6"/>
                  <stop offset="100%" stop-color="#6366f1"/>
                </linearGradient>
              </defs>
            </svg>

            <!-- 浮动卡片 1（左上） -->
            <div class="float-card float-card--tl zy-float" style="animation-delay: 0.4s">
              <span class="float-card-icon">🎯</span>
              <span class="float-card-text">AI 个性化推荐</span>
            </div>

            <!-- 浮动卡片 2（右中） -->
            <div class="float-card float-card--rm zy-float" style="animation-delay: 1s">
              <span class="float-card-icon">📊</span>
              <span class="float-card-text">行为实时分析</span>
            </div>

            <!-- 浮动卡片 3（左下） -->
            <div class="float-card float-card--bl zy-float" style="animation-delay: 1.8s">
              <span class="float-card-icon">💬</span>
              <span class="float-card-text">智能问答助手</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 波浪分隔线 ===== -->
      <WaveDivider fill="rgba(99, 102, 241,0.06)" />

      <!-- ===== 功能亮点区（designup.md §2.2）===== -->
      <section class="features-section">
        <div class="section-header">
          <h2 class="section-title">为什么选择智屿？</h2>
          <div class="section-line"></div>
        </div>

        <div class="features-grid">
          <div v-for="feat in features" :key="feat.icon" class="feature-card">
            <div class="feat-icon">{{ feat.icon }}</div>
            <h3 class="feat-title">{{ feat.title }}</h3>
            <p class="feat-desc">{{ feat.desc }}</p>
            <div class="feat-hover-bar"></div>
          </div>
        </div>
      </section>
    </main>

    <!-- ===== 搜索对话框（逻辑保持不变）===== -->
    <Transition name="fade">
      <div
        v-if="showSearchDialog"
        class="search-dialog-overlay"
        @click="handleOverlayClick"
      >
        <div class="search-dialog-container" @click.stop>
          <SearchDialog />
        </div>
      </div>
    </Transition>
  </div>
</template>


<style lang="scss" scoped>
  /**
   * 智屿 首页 - 品牌化视觉升级
   * 规格：designup.md §2
   * Hero 区左文右图，两列，功能亮点 6 卡片
   */

  .home-page {
    min-height: 100vh;
    background: var(--zy-gradient-hero, linear-gradient(135deg, #f5f3ff 0%, #FFFFFF 100%));
    font-family: var(--zy-font-display, "PingFang SC", "Hiragino Sans GB", sans-serif);
  }

  /* ===== Header ===== */
  .header {
    position: sticky;
    top: 0;
    z-index: 100;
    height: 64px;
    padding: 0 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background-color: rgba(255, 255, 255, 0.92);
    border-bottom: 1px solid rgba(99, 102, 241, 0.12);
    transition: box-shadow 0.3s ease, backdrop-filter 0.3s ease;
  }

  .header--scrolled {
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 2px 16px rgba(99, 102, 241, 0.10);
  }

  /* Logo */
  .brand-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    text-decoration: none;
    flex-shrink: 0;
  }

  .brand-text {
    display: flex;
    flex-direction: column;
    line-height: 1;
  }

  .brand-name {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.02em;
  }

  .brand-sub {
    font-size: 11px;
    color: #64748b;
    margin-top: 2px;
  }

  /* Header 右侧搜索 */
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    flex: 1;
    justify-content: flex-end;
  }

  .search-container {
    flex: 1;
    max-width: 280px;
    cursor: pointer;
  }

  .search-input-box {
    display: flex;
    align-items: center;
    height: 36px;
    padding: 0 12px;
    border-radius: 9999px;
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.20);
    transition: all 0.2s ease;

    &:hover {
      border-color: rgba(99, 102, 241, 0.40);
      background: rgba(99, 102, 241, 0.10);
    }

    .search-icon {
      flex-shrink: 0;
      font-size: 14px;
      color: #64748b;
      margin-right: 8px;
    }

    input {
      flex: 1;
      width: 0;
      min-width: 0;
      border: none;
      outline: none;
      background: none;
      font-size: 13px;
      color: #0f172a;
      cursor: pointer;

      &::placeholder {
        color: #64748b;
      }
    }

    .shortcut-key {
      flex-shrink: 0;
      font-size: 11px;
      color: #64748b;
      background: rgba(99, 102, 241, 0.10);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(99, 102, 241, 0.25);
    }
  }

  /* ===== 主内容 ===== */
  .main-content {
    width: 100%;
  }

  /* ===== Hero 区 ===== */
  .hero-section {
    display: grid;
    grid-template-columns: 55% 45%;
    align-items: center;
    min-height: calc(100vh - 64px);
    max-width: 1280px;
    margin: 0 auto;
    padding: 60px 40px;
    gap: 40px;
  }

  /* ---- 左列 ---- */
  .hero-left {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  /* 胶囊标签 */
  .hero-tag {
    display: inline-flex;
    align-items: center;
    padding: 5px 14px;
    border: 1px solid #6366f1;
    color: #6366f1;
    background: #eef2ff;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 500;
    width: fit-content;
    letter-spacing: 0.03em;
    animation: zy-fade-up 0.5s ease 0.1s both;
  }

  /* 主标题 */
  .hero-title {
    font-size: 48px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
    margin: 0;
    animation: zy-fade-up 0.5s ease 0.25s both;
  }

  .hero-title-gradient {
    background: linear-gradient(135deg, #6366f1, #3B82F6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* 副标题 */
  .hero-desc {
    font-size: 16px;
    color: #64748b;
    line-height: 1.7;
    max-width: 480px;
    margin: 0;
    animation: zy-fade-up 0.5s ease 0.4s both;
  }

  /* 按钮组 */
  .hero-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    animation: zy-fade-up 0.5s ease 0.55s both;
  }

  .btn-primary {
    display: inline-flex;
    align-items: center;
    padding: 14px 32px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: #fff;
    border-radius: 9999px;
    font-size: 16px;
    font-weight: 600;
    text-decoration: none;
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.35);
    transition: all 0.25s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 32px rgba(99, 102, 241, 0.45);
    }
  }

  .btn-outline {
    display: inline-flex;
    align-items: center;
    padding: 14px 32px;
    border: 2px solid #6366f1;
    color: #6366f1;
    border-radius: 9999px;
    font-size: 16px;
    font-weight: 600;
    text-decoration: none;
    background: transparent;
    transition: all 0.25s ease;

    &:hover {
      background: rgba(99, 102, 241, 0.08);
      transform: translateY(-2px);
    }
  }

  /* 数据展示行 */
  .hero-stats {
    display: flex;
    align-items: center;
    gap: 20px;
    animation: zy-fade-up 0.5s ease 0.7s both;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .stat-num {
    font-size: 22px;
    font-weight: 700;
    color: #6366f1;
  }

  .stat-label {
    font-size: 12px;
    color: #64748b;
  }

  .stat-divider {
    width: 1px;
    height: 36px;
    background: rgba(99, 102, 241, 0.25);
  }

  /* ---- 右列：插画区 ---- */
  .hero-right {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .hero-illustration {
    position: relative;
    width: 100%;
    max-width: 440px;

    svg {
      width: 100%;
      height: auto;
    }
  }

  /* 浮动卡片 */
  .float-card {
    position: absolute;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    background: white;
    border-radius: 12px;
    border-left: 3px solid #6366f1;
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.15);
    white-space: nowrap;
  }

  .float-card-icon { font-size: 18px; }
  .float-card-text { font-size: 13px; font-weight: 600; color: #0f172a; }

  /* 卡片位置 */
  .float-card--tl { top: 10%; left: -8%; }
  .float-card--rm { top: 42%; right: -10%; }
  .float-card--bl { bottom: 12%; left: -5%; }

  /* ===== 功能亮点区 ===== */
  .features-section {
    max-width: 1280px;
    margin: 0 auto;
    padding: 80px 40px 100px;
  }

  .section-header {
    text-align: center;
    margin-bottom: 56px;
  }

  .section-title {
    font-size: 32px;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 12px;
  }

  .section-line {
    width: 48px;
    height: 4px;
    background: linear-gradient(90deg, #6366f1, #3B82F6);
    border-radius: 9999px;
    margin: 0 auto;
  }

  /* 功能卡片 6 列 Grid */
  .features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }

  @media (max-width: 900px) {
    .features-grid { grid-template-columns: repeat(2, 1fr); }
  }

  @media (max-width: 560px) {
    .features-grid { grid-template-columns: 1fr; }
  }

  .feature-card {
    position: relative;
    padding: 28px 24px;
    background: #FFFFFF;
    border-radius: 16px;
    border: 1px solid rgba(99, 102, 241, 0.08);
    box-shadow: 0 4px 24px rgba(99, 102, 241, 0.06);
    overflow: hidden;
    cursor: default;
    transition: transform 0.25s ease, box-shadow 0.25s ease;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15);

      .feat-hover-bar {
        opacity: 1;
      }
    }
  }

  /* 底部绿色 hover 边条 */
  .feat-hover-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #6366f1, #3B82F6);
    border-radius: 0 0 16px 16px;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .feat-icon {
    font-size: 36px;
    margin-bottom: 16px;
    line-height: 1;
  }

  .feat-title {
    font-size: 17px;
    font-weight: 600;
    color: #0f172a;
    margin: 0 0 10px;
  }

  .feat-desc {
    font-size: 14px;
    color: #64748b;
    line-height: 1.6;
    margin: 0;
  }

  /* ===== 搜索对话框 ===== */
  .search-dialog-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: flex;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }

  .search-dialog-container {
    margin-top: 15vh;
    width: 640px;
    max-width: 92vw;
  }

  /* ===== 过渡动画 ===== */
  .fade-enter-active, .fade-leave-active {
    transition: opacity 0.2s ease;
  }

  .fade-enter-from, .fade-leave-to {
    opacity: 0;
  }

  /* ===== 响应式 ===== */
  @media (max-width: 900px) {
    .hero-section {
      grid-template-columns: 1fr;
      min-height: auto;
      padding: 48px 24px;
    }

    .hero-right { display: none; }

    .hero-title { font-size: 36px; }

    .header { padding: 0 24px; }
  }
</style>
