<script setup>
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    BadgeCheck,
    Bell,
    BookOpen,
    Bot,
    Brain,
    GraduationCap,
    Layers3,
    Library,
    LineChart,
    LockKeyhole,
    Route,
    SearchCheck,
    ShieldCheck,
    Sparkles,
    Target,
    UsersRound,
    Zap,
  } from 'lucide-vue-next';
  import { useUserStore } from '@/store';
  import SearchDialog from './components/SearchDialog.vue';
  import SiteFooter from '@/components/zy/SiteFooter.vue';
  import { landingHeroPhotos } from '@/data/mediaCatalog';

  const showSearchDialog = ref(false);
  const userStore = useUserStore();
  const route = useRoute();
  const router = useRouter();
  const isTeacher = computed(() => userStore.role === 'teacher');
  const primaryAction = computed(() =>
    isTeacher.value ? '/dashboard/workplace' : '/tutor'
  );
  const primaryText = computed(() =>
    isTeacher.value ? '进入教学' : '开始 AI 伴学'
  );
  const secondaryAction = computed(() =>
    isTeacher.value ? '/course/resource-generation' : '/course/list'
  );
  const secondaryText = computed(() =>
    isTeacher.value ? '资源生成中心' : '我的课程'
  );

  const trustBadges = [
    { icon: ShieldCheck, label: '安全可靠' },
    { icon: LockKeyhole, label: '隐私保护' },
    { icon: GraduationCap, label: '教育专属优化' },
  ];

  const statsBar = [
    { icon: BookOpen, tone: 'blue', value: '1200+', label: '优质课程资源' },
    { icon: BadgeCheck, tone: 'green', value: '98%', label: '学生满意度' },
    { icon: UsersRound, tone: 'violet', value: '50+', label: '合作院校' },
    { icon: ShieldCheck, tone: 'orange', value: '10万+', label: '活跃学习者' },
  ];

  const features = [
    {
      icon: Brain,
      tone: 'violet',
      title: 'AI 智能问答',
      desc: '基于课程资料与引用证据回答问题，减少无效搜索和泛泛解释。',
      link: '/tutor',
      action: '立即体验',
    },
    {
      icon: Target,
      tone: 'green',
      title: '个性化学习路径',
      desc: '基于画像与掌握度的专属推荐，让每位同学走适合自己的路。',
      link: '/profile/learning-data',
      action: '了解更多',
    },
    {
      icon: SearchCheck,
      tone: 'blue',
      title: '学习画像分析',
      desc: '通过对话抽取目标、基础、风格与薄弱点，随学随新。',
      link: '/profile/learning-data',
      action: '查看示例',
    },
    {
      icon: Layers3,
      tone: 'amber',
      title: '多模态资源',
      desc: '讲解、文档、题库、导图与案例统一生成，跨格式知识触手可得。',
      link: '/course/resource-generation',
      action: '探索资源',
    },
    {
      icon: Zap,
      tone: 'cyan',
      title: '可控思考强度',
      desc: '普通提问保持轻量，复杂任务可启用更深入的推理与研究过程。',
      link: '/tutor',
      action: '了解模式',
    },
    {
      icon: Bell,
      tone: 'rose',
      title: '智能预警',
      desc: '学习风险提前识别，及时调整资源与计划，不让问题持续积累。',
      link: '/profile/messages',
      action: '了解预警',
    },
  ];

  const courseCategories = [
    {
      name: '计算机科学',
      icon: Library,
      tone: 'blue',
      count: 368,
      topics: '人工智能 · 编程 · 数据结构',
    },
    {
      name: '经济管理',
      icon: LineChart,
      tone: 'green',
      count: 256,
      topics: '经管学 · 管理学 · 金融学',
    },
    {
      name: '人文社科',
      icon: BookOpen,
      tone: 'amber',
      count: 198,
      topics: '文学 · 历史 · 心理学',
    },
    {
      name: '理工科',
      icon: Sparkles,
      tone: 'violet',
      count: 312,
      topics: '数学 · 物理 · 化学',
    },
    {
      name: '语言学习',
      icon: Bot,
      tone: 'cyan',
      count: 156,
      topics: '英语 · 日语 · 其他语言',
    },
    {
      name: '职业技能',
      icon: Route,
      tone: 'rose',
      count: 210,
      topics: '设计 · 营销 · 办公软件',
    },
  ];

  const handleOverlayClick = (event) => {
    if (event.target.classList.contains('search-dialog-overlay')) {
      closeSearchDialog();
    }
  };

  const openSearchDialog = () => {
    showSearchDialog.value = true;
  };

  const closeSearchDialog = () => {
    showSearchDialog.value = false;
    if (route.query.search === '1') {
      const nextQuery = { ...route.query };
      delete nextQuery.search;
      router.replace({ query: nextQuery });
    }
  };

  const handleClickOutside = (event) => {
    const searchDialog = document.querySelector('.search-dialog');
    if (
      searchDialog &&
      !searchDialog.contains(event.target) &&
      !event.target.closest('.search-container')
    ) {
      closeSearchDialog();
    }
  };

  const handleKeydown = (event) => {
    if (event.key === 'Escape') {
      closeSearchDialog();
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openSearchDialog();
    }
  };

  watch(
    () => route.query.search,
    (value) => {
      if (value === '1') openSearchDialog();
    },
    { immediate: true }
  );

  onMounted(() => {
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeydown);
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleKeydown);
  });
</script>

<template>
  <div class="home-page">
    <main class="main-content">
      <section class="hero-section">
        <div class="hero-orbit hero-orbit--one" aria-hidden="true" />
        <div class="hero-orbit hero-orbit--two" aria-hidden="true" />

        <div class="hero-left">
          <h1 class="hero-title">
            在知识的岛屿上<br />
            <span>开启智慧航行</span>
          </h1>

          <p class="hero-desc">
            智屿连接课程资料、学习画像与行为分析，<br />
            为每位学生提供有证据、有反馈、有下一步的学习路径。
          </p>

          <div class="hero-actions">
            <router-link :to="primaryAction" class="btn-primary">
              {{ primaryText }}
              <span aria-hidden="true">→</span>
            </router-link>
            <router-link :to="secondaryAction" class="btn-outline">
              {{ secondaryText }}
            </router-link>
          </div>

          <div class="trust-badges">
            <div v-for="badge in trustBadges" :key="badge.label" class="trust-badge">
              <component :is="badge.icon" :size="16" :stroke-width="1.9" />
              <span>{{ badge.label }}</span>
            </div>
          </div>
        </div>

        <div class="hero-right">
          <div class="visual-stage">
            <img
              :src="landingHeroPhotos.secondary"
              alt="图书馆学习场景"
              class="hero-photo hero-photo--library"
            />
            <img
              :src="landingHeroPhotos.accent"
              alt="AI 学习控制台"
              class="hero-photo hero-photo--console"
            />
            <img
              :src="landingHeroPhotos.primary"
              alt="小组学习讨论"
              class="hero-photo hero-photo--team"
            />

            <div class="floating-card floating-card--assistant">
              <span class="floating-card__icon">
                <Bot :size="18" />
              </span>
              <div>
                <strong>AI 伴学助手</strong>
                <small>智能问答 · 个性推荐</small>
              </div>
            </div>

            <div class="floating-card floating-card--analysis">
              <span class="floating-card__icon floating-card__icon--chart">
                <LineChart :size="18" />
              </span>
              <div class="analysis-body">
                <strong>学习行为分析</strong>
                <small>专注度 92%</small>
                <div class="mini-chart" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            </div>

            <div class="floating-card floating-card--rag">
              <span class="rag-avatar">
                <Bot :size="18" />
              </span>
              <div>
                <strong>课程证据检索</strong>
                <small>知识检索 · 精准回答</small>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="stats-section" aria-label="平台数据">
        <div class="stats-card">
          <div
            v-for="stat in statsBar"
            :key="stat.label"
            class="stats-card__item"
            :class="`stats-card__item--${stat.tone}`"
          >
            <span class="stats-card__icon">
              <component :is="stat.icon" :size="25" />
            </span>
            <div class="stats-card__text">
              <strong>{{ stat.value }}</strong>
              <span>{{ stat.label }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="features-section">
        <div class="section-header section-header--center">
          <h2 class="section-title">为什么选择智屿？</h2>
          <p class="section-subtitle">AI 驱动教育创新，助力每一位学习者成长</p>
        </div>

        <div class="features-grid">
          <router-link
            v-for="feat in features"
            :key="feat.title"
            :to="feat.link"
            class="feature-card"
            :class="`feature-card--${feat.tone}`"
          >
            <div class="feat-icon">
              <component :is="feat.icon" :size="28" :stroke-width="1.8" />
            </div>
            <h3 class="feat-title">{{ feat.title }}</h3>
            <p class="feat-desc">{{ feat.desc }}</p>
            <span class="feat-link">{{ feat.action }} →</span>
          </router-link>
        </div>
      </section>

      <section class="course-hub-section">
        <div class="section-header section-header--course">
          <div class="course-title-center">
            <h2 class="section-title">课程资源中心</h2>
            <p class="section-subtitle">覆盖多学科领域，满足不同学习需求</p>
          </div>
          <router-link to="/course/list" class="section-link">
            浏览全部课程
            <span aria-hidden="true">→</span>
          </router-link>
        </div>

        <div class="course-cat-grid">
          <router-link
            v-for="cat in courseCategories"
            :key="cat.name"
            to="/course/list"
            class="course-cat-card"
            :class="`course-cat-card--${cat.tone}`"
          >
            <span class="course-cat-icon">
              <component :is="cat.icon" :size="22" />
            </span>
            <div>
              <strong>{{ cat.name }}</strong>
              <small>{{ cat.topics }}</small>
              <em>{{ cat.count }} 门课程</em>
            </div>
          </router-link>
        </div>
      </section>

      <SiteFooter />
    </main>

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
  .home-page {
    min-height: 100vh;
    background:
      radial-gradient(circle at 72% 7%, rgba(129, 140, 248, 0.14), transparent 24%),
      linear-gradient(180deg, #f8faff 0%, #ffffff 45%, #fbfdff 100%);
    color: #15213b;
    font-family:
      'PingFang SC',
      'Hiragino Sans GB',
      'Microsoft YaHei',
      sans-serif;
  }

  .main-content {
    width: 100%;
    overflow: hidden;
  }

  .hero-section {
    position: relative;
    display: grid;
    grid-template-columns: 0.9fr 1.1fr;
    align-items: center;
    max-width: 1232px;
    min-height: 418px;
    margin: 0 auto;
    padding: 54px 24px 34px;
    gap: 42px;
  }

  .hero-orbit {
    position: absolute;
    pointer-events: none;
    border: 1px dashed rgba(99, 102, 241, 0.18);
    border-radius: 999px;
    transform: rotate(-12deg);
  }

  .hero-orbit--one {
    width: 540px;
    height: 260px;
    right: 28px;
    top: 66px;
  }

  .hero-orbit--two {
    width: 720px;
    height: 330px;
    right: -82px;
    top: 18px;
    opacity: 0.72;
  }

  .hero-left {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-left > *,
  .visual-stage {
    animation: home-reveal 0.42s ease both;
  }

  .hero-left .hero-desc {
    animation-delay: 0.05s;
  }

  .hero-left .hero-actions {
    animation-delay: 0.1s;
  }

  .hero-left .trust-badges {
    animation-delay: 0.15s;
  }

  .visual-stage {
    animation-delay: 0.08s;
  }

  .hero-title {
    margin: 0;
    color: #111a33;
    font-size: 45px;
    font-weight: 800;
    line-height: 1.22;

    span {
      color: #4f5dfb;
    }
  }

  .hero-desc {
    margin: 22px 0 0;
    max-width: 500px;
    color: #69758d;
    font-size: 16px;
    line-height: 1.78;
  }

  .hero-actions {
    display: flex;
    gap: 14px;
    margin-top: 31px;
    flex-wrap: wrap;
  }

  .btn-primary,
  .btn-outline {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 128px;
    height: 48px;
    padding: 0 25px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 700;
    text-decoration: none;
    transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      border-color 0.18s ease;
  }

  .btn-primary {
    gap: 8px;
    background: linear-gradient(135deg, #5662ff 0%, #4053f4 100%);
    color: #fff;
    box-shadow: 0 14px 28px rgba(72, 86, 241, 0.25);

    &:hover {
      color: #fff;
      transform: translateY(-2px);
      box-shadow: 0 18px 34px rgba(72, 86, 241, 0.34);
    }
  }

  .btn-outline {
    border: 1px solid #6977ff;
    background: rgba(255, 255, 255, 0.78);
    color: #4c5cf6;

    &:hover {
      color: #3c48e5;
      border-color: #4c5cf6;
      transform: translateY(-2px);
      box-shadow: 0 12px 24px rgba(76, 92, 246, 0.13);
    }
  }

  .trust-badges {
    display: flex;
    gap: 31px;
    margin-top: 26px;
    flex-wrap: wrap;
  }

  .trust-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #66728a;
    font-size: 13px;
    font-weight: 600;

    svg {
      color: #596273;
    }
  }

  .hero-right {
    position: relative;
    z-index: 2;
    min-height: 345px;
  }

  .visual-stage {
    position: relative;
    width: min(100%, 658px);
    height: 344px;
    margin-left: auto;
  }

  .hero-photo {
    position: absolute;
    object-fit: cover;
    border: 3px solid rgba(255, 255, 255, 0.92);
    box-shadow: 0 22px 46px rgba(25, 37, 73, 0.16);
    transition: transform 0.28s ease, box-shadow 0.28s ease;
  }

  .visual-stage:hover .hero-photo {
    box-shadow: 0 24px 50px rgba(25, 37, 73, 0.18);
  }

  .visual-stage:hover .hero-photo--library {
    transform: translate3d(0, -4px, 0);
  }

  .visual-stage:hover .hero-photo--console {
    transform: translate3d(-4px, 3px, 0);
  }

  .visual-stage:hover .hero-photo--team {
    transform: translate3d(4px, -2px, 0);
  }

  .hero-photo--library {
    top: 0;
    left: 133px;
    width: 294px;
    height: 168px;
    border-radius: 18px 18px 5px 5px;
  }

  .hero-photo--console {
    top: 118px;
    left: 0;
    width: 220px;
    height: 126px;
    border-radius: 14px;
    z-index: 2;
  }

  .hero-photo--team {
    right: 64px;
    bottom: 0;
    width: 316px;
    height: 181px;
    border-radius: 4px 18px 18px 18px;
    z-index: 3;
  }

  .floating-card {
    position: absolute;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 166px;
    padding: 13px 15px;
    border: 1px solid rgba(226, 232, 255, 0.9);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 16px 42px rgba(42, 55, 104, 0.12);
    backdrop-filter: blur(10px);
    transition: transform 0.24s ease, box-shadow 0.24s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 20px 48px rgba(42, 55, 104, 0.15);
    }

    strong {
      display: block;
      color: #1b2540;
      font-size: 13px;
      font-weight: 800;
      line-height: 1.2;
      white-space: nowrap;
    }

    small {
      display: block;
      margin-top: 5px;
      color: #718095;
      font-size: 11px;
      line-height: 1.2;
      white-space: nowrap;
    }
  }

  .floating-card__icon,
  .rag-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: #eef3ff;
    color: #4d63f7;
  }

  .floating-card__icon--chart {
    background: #eff6ff;
    color: #3182ff;
  }

  .rag-avatar {
    background: linear-gradient(145deg, #dbeafe, #edf2ff);
    color: #2f63f4;
  }

  .floating-card--assistant {
    left: 103px;
    top: 211px;
  }

  .floating-card--analysis {
    top: 22px;
    right: 0;
    width: 183px;
    align-items: flex-start;
  }

  .floating-card--rag {
    right: 4px;
    bottom: -2px;
  }

  .analysis-body {
    flex: 1;
  }

  .mini-chart {
    display: flex;
    align-items: flex-end;
    gap: 7px;
    height: 28px;
    margin-top: 8px;

    i {
      display: block;
      width: 3px;
      border-radius: 4px;
      background: #4c63ff;

      &:nth-child(1) { height: 17px; opacity: 0.7; }
      &:nth-child(2) { height: 12px; opacity: 0.48; }
      &:nth-child(3) { height: 10px; opacity: 0.42; }
      &:nth-child(4) { height: 22px; opacity: 0.88; }
      &:nth-child(5) { height: 15px; opacity: 0.62; }
      &:nth-child(6) { height: 26px; }
    }
  }

  @keyframes home-reveal {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .stats-section {
    max-width: 1232px;
    margin: 0 auto;
    padding: 0 24px;
  }

  .stats-card {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    min-height: 84px;
    border: 1px solid #e2e8f7;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 18px 46px rgba(42, 55, 104, 0.06);
  }

  .stats-card__item {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;
    min-width: 0;
    padding: 15px 18px;

    & + &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 24px;
      bottom: 24px;
      width: 1px;
      background: #e7ebf6;
    }
  }

  .stats-card__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 50px;
    height: 50px;
    border-radius: 50%;
  }

  .stats-card__item--blue .stats-card__icon {
    background: #e9efff;
    color: #3568ff;
  }

  .stats-card__item--green .stats-card__icon {
    background: #e8fbee;
    color: #19bf68;
  }

  .stats-card__item--violet .stats-card__icon {
    background: #efeaff;
    color: #7258ff;
  }

  .stats-card__item--orange .stats-card__icon {
    background: #fff2df;
    color: #ff9d24;
  }

  .stats-card__text {
    display: flex;
    flex-direction: column;
    gap: 3px;

    strong {
      color: #16213a;
      font-size: 26px;
      font-weight: 800;
      line-height: 1;
    }

    span {
      color: #66728a;
      font-size: 13px;
    }
  }

  .features-section {
    max-width: 1232px;
    margin: 0 auto;
    padding: 39px 24px 10px;
  }

  .section-header {
    margin-bottom: 21px;
  }

  .section-header--center {
    text-align: center;
  }

  .section-title {
    margin: 0;
    color: #111a33;
    font-size: 25px;
    font-weight: 800;
    line-height: 1.25;
  }

  .section-subtitle {
    margin: 9px 0 0;
    color: #7a879c;
    font-size: 14px;
  }

  .features-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 16px;
  }

  .feature-card {
    display: flex;
    min-height: 178px;
    flex-direction: column;
    padding: 20px 18px 18px;
    border: 1px solid #e9edf7;
    border-radius: 12px;
    background: #fff;
    color: inherit;
    text-decoration: none;
    box-shadow: 0 14px 34px rgba(45, 55, 93, 0.045);
    transition:
      transform 0.18s ease,
      border-color 0.18s ease,
      box-shadow 0.18s ease;

    &:hover {
      transform: translateY(-3px);
      border-color: rgba(99, 102, 241, 0.28);
      box-shadow: 0 20px 42px rgba(45, 55, 93, 0.09);
    }
  }

  .feat-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    margin-bottom: 14px;
    border-radius: 50%;
  }

  .feature-card--violet .feat-icon { background: #f0edff; color: #745cff; }
  .feature-card--green .feat-icon { background: #e9faef; color: #1fbf67; }
  .feature-card--blue .feat-icon { background: #eaf1ff; color: #3b6dff; }
  .feature-card--amber .feat-icon { background: #fff3df; color: #f59a23; }
  .feature-card--cyan .feat-icon { background: #e8fbff; color: #17a9d5; }
  .feature-card--rose .feat-icon { background: #ffedf3; color: #ef4d79; }

  .feat-title {
    margin: 0 0 13px;
    color: #1a2440;
    font-size: 15px;
    font-weight: 800;
  }

  .feat-desc {
    flex: 1;
    margin: 0;
    color: #6f7c92;
    font-size: 12px;
    line-height: 1.78;
  }

  .feat-link {
    margin-top: 13px;
    color: #5162f5;
    font-size: 12px;
    font-weight: 700;
  }

  .course-hub-section {
    max-width: 1232px;
    margin: 0 auto;
    padding: 3px 24px 29px;
  }

  .section-header--course {
    position: relative;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .course-title-center {
    text-align: center;
  }

  .section-link {
    position: absolute;
    right: 0;
    bottom: 4px;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #5362f6;
    font-size: 13px;
    font-weight: 700;
    text-decoration: none;

    &:hover {
      color: #3545e6;
    }
  }

  .course-cat-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
  }

  .course-cat-card {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 72px;
    padding: 13px 14px;
    border: 1px solid #e9edf7;
    border-radius: 9px;
    color: inherit;
    text-decoration: none;
    transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      border-color 0.18s ease;

    &:hover {
      transform: translateY(-2px);
      border-color: rgba(86, 98, 255, 0.26);
      box-shadow: 0 14px 28px rgba(42, 55, 104, 0.08);
    }

    strong,
    small,
    em {
      display: block;
    }

    strong {
      color: #202a44;
      font-size: 13px;
      font-weight: 800;
      line-height: 1.2;
    }

    small {
      margin-top: 5px;
      color: #69758b;
      font-size: 11px;
      line-height: 1.2;
      white-space: nowrap;
    }

    em {
      margin-top: 5px;
      color: #7a86a0;
      font-size: 11px;
      font-style: normal;
    }
  }

  .course-cat-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    border-radius: 10px;
  }

  .course-cat-card--blue { background: linear-gradient(135deg, #f0f4ff, #ffffff); }
  .course-cat-card--green { background: linear-gradient(135deg, #edfbf4, #ffffff); }
  .course-cat-card--amber { background: linear-gradient(135deg, #fff6e9, #ffffff); }
  .course-cat-card--violet { background: linear-gradient(135deg, #f4efff, #ffffff); }
  .course-cat-card--cyan { background: linear-gradient(135deg, #ecfbff, #ffffff); }
  .course-cat-card--rose { background: linear-gradient(135deg, #fff0f5, #ffffff); }

  .course-cat-card--blue .course-cat-icon { background: #e9efff; color: #3568ff; }
  .course-cat-card--green .course-cat-icon { background: #e6faee; color: #16b962; }
  .course-cat-card--amber .course-cat-icon { background: #fff0d7; color: #f59a23; }
  .course-cat-card--violet .course-cat-icon { background: #efe9ff; color: #735aff; }
  .course-cat-card--cyan .course-cat-icon { background: #e4faff; color: #0ea7cf; }
  .course-cat-card--rose .course-cat-icon { background: #ffebf2; color: #ee4a78; }

  .search-dialog-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    justify-content: center;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(4px);
  }

  .search-dialog-container {
    width: 640px;
    max-width: 92vw;
    margin-top: 15vh;
  }

  .fade-enter-active,
  .fade-leave-active {
    transition: opacity 0.2s ease;
  }

  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
  }

  @media (max-width: 1180px) {
    .hero-section {
      grid-template-columns: 1fr;
      min-height: auto;
      padding-top: 46px;
    }

    .visual-stage {
      margin: 0 auto;
    }

    .features-grid,
    .course-cat-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 820px) {
    .hero-title {
      font-size: 36px;
    }

    .stats-card {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .stats-card__item:nth-child(3)::before {
      display: none;
    }

    .section-header--course {
      align-items: center;
      flex-direction: column;
      gap: 10px;
    }

    .section-link {
      position: static;
    }

    .features-grid,
    .course-cat-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 560px) {
    .hero-section {
      padding: 34px 16px 24px;
    }

    .hero-title {
      font-size: 31px;
    }

    .hero-desc br {
      display: none;
    }

    .visual-stage {
      height: 300px;
      transform: scale(0.86);
      transform-origin: center top;
      margin-bottom: -40px;
    }

    .stats-section,
    .features-section,
    .course-hub-section {
      padding-left: 16px;
      padding-right: 16px;
    }

    .stats-card,
    .features-grid,
    .course-cat-grid {
      grid-template-columns: 1fr;
    }

    .stats-card__item::before {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .hero-left > *,
    .visual-stage {
      animation: none;
    }

    .hero-photo,
    .floating-card,
    .feature-card,
    .course-cat-card,
    .btn-primary,
    .btn-outline {
      transition: none;
    }

    .visual-stage:hover .hero-photo--library,
    .visual-stage:hover .hero-photo--console,
    .visual-stage:hover .hero-photo--team,
    .floating-card:hover {
      transform: none;
    }
  }
</style>
