<script setup>
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
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
  let revealObserver = null;
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
    { icon: ShieldCheck, label: '证据可追溯' },
    { icon: LockKeyhole, label: '画像可更新' },
    { icon: GraduationCap, label: '路径可回写' },
  ];

  const statsBar = [
    { icon: SearchCheck, tone: 'blue', value: '证据可追溯', label: '课程问答' },
    { icon: Brain, tone: 'green', value: '画像可更新', label: '学习建议' },
    { icon: Layers3, tone: 'violet', value: '资源可入库', label: '多类生成' },
    { icon: Route, tone: 'orange', value: '路径可调整', label: '学习安排' },
  ];

  const features = [
    {
      icon: Brain,
      tone: 'violet',
      title: '课程证据问答',
      desc: '自动检索课程证据，回答有出处。',
      link: '/tutor',
      action: '进入 AI 伴学',
    },
    {
      icon: Target,
      tone: 'green',
      title: '个性化学习路径',
      desc: '按掌握度生成今天的学习任务。',
      link: '/profile/learning-data',
      action: '查看学习路径',
    },
    {
      icon: SearchCheck,
      tone: 'blue',
      title: '学情画像更新',
      desc: '从问答和练习更新薄弱点画像。',
      link: '/profile/learning-data',
      action: '打开学情档案',
    },
    {
      icon: Layers3,
      tone: 'amber',
      title: '多智能体资源生成',
      desc: '讲义、练习、导图和案例可入库。',
      link: '/course/resource-generation',
      action: '进入资源工坊',
    },
    {
      icon: Zap,
      tone: 'cyan',
      title: '可控研究深度',
      desc: '复杂任务启用深度检索与报告。',
      link: '/tutor',
      action: '选择思考强度',
    },
    {
      icon: Bell,
      tone: 'rose',
      title: '智能预警',
      desc: '提前发现风险，回写路径和提醒。',
      link: '/profile/messages',
      action: '查看提醒',
    },
  ];

  const courseCategories = [
    {
      name: '计算机科学',
      icon: Library,
      tone: 'blue',
      topics: '人工智能 · 编程 · 数据结构',
    },
    {
      name: '经济管理',
      icon: LineChart,
      tone: 'green',
      topics: '经管学 · 管理学 · 金融学',
    },
    {
      name: '人文社科',
      icon: BookOpen,
      tone: 'amber',
      topics: '文学 · 历史 · 心理学',
    },
    {
      name: '理工科',
      icon: Sparkles,
      tone: 'violet',
      topics: '数学 · 物理 · 化学',
    },
    {
      name: '语言学习',
      icon: Bot,
      tone: 'cyan',
      topics: '英语 · 日语 · 其他语言',
    },
    {
      name: '职业技能',
      icon: Route,
      tone: 'rose',
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
    const targets = Array.from(document.querySelectorAll('.reveal-on-scroll'));
    if (!targets.length) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      targets.forEach((item) => item.classList.add('is-visible'));
      return;
    }
    revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          revealObserver?.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -12% 0px', threshold: 0.12 }
    );
    targets.forEach((item) => revealObserver?.observe(item));
  });

  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleKeydown);
    revealObserver?.disconnect();
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
            你的 AI 学习伙伴<br />
            <span>让学习更有依据</span>
          </h1>

          <p class="hero-desc">
            自动理解课程资料、作业和学习记录，<br />
            把提问、练习、资料与复习建议整理成清晰的下一步。
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
                <strong>证据问答</strong>
                <small>课程引用 · 精准解释</small>
              </div>
            </div>

            <div class="floating-card floating-card--analysis">
              <span class="floating-card__icon floating-card__icon--chart">
                <LineChart :size="18" />
              </span>
              <div class="analysis-body">
                <strong>路径推荐</strong>
                <small>薄弱点优先</small>
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
                <strong>资料入库</strong>
                <small>资源同步 · 图谱关联</small>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="stats-section reveal-on-scroll" aria-label="平台数据">
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

      <section class="features-section reveal-on-scroll">
        <div class="section-header section-header--center">
          <h2 class="section-title">为什么选择智屿？</h2>
          <p class="section-subtitle">把课程证据、AI 辅导和个性化复习组织成稳定的学习工作流</p>
        </div>

        <div class="feature-loop">
          <div class="feature-loop__intro">
            <span class="feature-loop__eyebrow">学习工作流</span>
            <h3>从一次提问开始，形成可复用的学习记录</h3>
            <p>围绕课程、作业和资料持续整理证据，让学生知道下一步该学什么、为什么这样学。</p>
          </div>
          <router-link
            v-for="(feat, index) in features"
            :key="feat.title"
            :to="feat.link"
            class="feature-step"
            :class="`feature-step--${feat.tone}`"
          >
            <span class="feature-step__index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="feat-icon">
              <component :is="feat.icon" :size="21" :stroke-width="1.9" />
            </span>
            <span class="feature-step__body">
              <strong>{{ feat.title }}</strong>
              <small>{{ feat.desc }}</small>
            </span>
            <span class="feat-link">{{ feat.action }} →</span>
          </router-link>
        </div>
      </section>

      <section class="course-hub-section reveal-on-scroll">
        <div class="section-header section-header--course">
          <div class="course-title-center">
            <h2 class="section-title">课程资源中心</h2>
            <p class="section-subtitle">按学科组织课程入口，先找到课程，再进入资料、问答和学习路径</p>
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

  .reveal-on-scroll {
    opacity: 0;
    transform: translateY(12px);
    transition:
      opacity 0.42s ease,
      transform 0.42s ease;
  }

  .reveal-on-scroll.is-visible {
    opacity: 1;
    transform: translateY(0);
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
    font-size: 43px;
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

  .visual-stage::after {
    content: '';
    position: absolute;
    top: 36px;
    right: 42px;
    z-index: 6;
    width: 176px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.78), transparent);
    opacity: 0.28;
    transform-origin: center;
    animation: stage-scan 4.8s ease-in-out infinite;
  }

  .hero-photo {
    position: absolute;
    object-fit: cover;
    border: 3px solid rgba(255, 255, 255, 0.92);
    box-shadow: 0 22px 46px rgba(25, 37, 73, 0.16);
    translate: 0 0;
    transition: transform 0.28s ease, box-shadow 0.28s ease;
  }

  .hero-photo--library,
  .floating-card--analysis {
    animation: hero-drift-up 5.6s ease-in-out infinite alternate;
  }

  .hero-photo--console,
  .floating-card--assistant {
    animation: hero-drift-side 6.2s ease-in-out infinite alternate;
  }

  .hero-photo--team,
  .floating-card--rag {
    animation: hero-drift-soft 5.9s ease-in-out infinite alternate;
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
    border-radius: 20px;
  }

  .hero-photo--console {
    top: 118px;
    left: 0;
    width: 220px;
    height: 126px;
    border-radius: 18px;
    z-index: 2;
  }

  .hero-photo--team {
    right: 64px;
    bottom: 0;
    width: 316px;
    height: 181px;
    border-radius: 20px;
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
    top: 38px;
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
      transform-origin: bottom;
      animation: chart-breathe 1.9s ease-in-out infinite;

      &:nth-child(1) { height: 17px; opacity: 0.7; }
      &:nth-child(2) { height: 12px; opacity: 0.48; animation-delay: 0.1s; }
      &:nth-child(3) { height: 10px; opacity: 0.42; animation-delay: 0.2s; }
      &:nth-child(4) { height: 22px; opacity: 0.88; animation-delay: 0.3s; }
      &:nth-child(5) { height: 15px; opacity: 0.62; animation-delay: 0.4s; }
      &:nth-child(6) { height: 26px; animation-delay: 0.5s; }
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

  @keyframes hero-drift-up {
    from { translate: 0 0; }
    to { translate: 0 -5px; }
  }

  @keyframes hero-drift-side {
    from { translate: 0 0; }
    to { translate: 4px 3px; }
  }

  @keyframes hero-drift-soft {
    from { translate: 0 0; }
    to { translate: -3px -4px; }
  }

  @keyframes chart-breathe {
    0%,
    100% {
      transform: scaleY(0.72);
    }
    50% {
      transform: scaleY(1);
    }
  }

  @keyframes loop-line {
    0%,
    100% {
      opacity: 0.48;
      transform: scaleX(0.82);
    }
    50% {
      opacity: 1;
      transform: scaleX(1);
    }
  }

  @keyframes loop-marker {
    0%,
    100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(164px);
    }
  }

  @keyframes stage-scan {
    0%,
    100% {
      opacity: 0;
      transform: translate3d(-92px, 34px, 0) rotate(-12deg) scaleX(0.5);
    }
    42%,
    58% {
      opacity: 0.38;
      transform: translate3d(70px, 158px, 0) rotate(-12deg) scaleX(0.9);
    }
  }

  @keyframes loop-sweep {
    0% {
      transform: translateX(-34%);
      opacity: 0;
    }
    18%,
    70% {
      opacity: 0.55;
    }
    100% {
      transform: translateX(34%);
      opacity: 0;
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
    padding: 32px 24px 12px;
  }

  .section-header {
    margin-bottom: 24px;
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
    line-height: 1.7;
  }

  .feature-loop {
    position: relative;
    overflow: hidden;
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0;
    padding: 18px 20px 22px;
    border: 1px solid rgba(80, 95, 150, 0.13);
    border-radius: 26px;
    background:
      radial-gradient(circle at 11% 16%, rgba(99, 102, 241, 0.1), transparent 28%),
      linear-gradient(135deg, #ffffff 0%, #fcfdff 52%, #f8faff 100%);
    box-shadow: 0 18px 46px rgba(31, 41, 85, 0.055);
    animation: home-reveal 0.32s ease both;
  }

  .feature-loop::before {
    content: '';
    position: absolute;
    top: 154px;
    right: 42px;
    left: 42px;
    height: 1px;
    background: linear-gradient(90deg, rgba(99, 102, 241, 0.06), rgba(99, 102, 241, 0.36), rgba(99, 102, 241, 0.06));
    transform-origin: left;
    animation: loop-line 3.8s ease-in-out infinite;
  }

  .feature-loop::after {
    content: '';
    position: absolute;
    top: 140px;
    left: 0;
    width: 44%;
    height: 30px;
    background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.13), transparent);
    filter: blur(10px);
    animation: loop-sweep 5.4s ease-in-out infinite;
  }

  .feature-loop__intro {
    position: relative;
    z-index: 1;
    display: flex;
    grid-column: 1 / -1;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
    min-height: 0;
    padding: 4px 6px 26px;
    color: #111a33;
  }

  .feature-loop__intro::before {
    display: none;
  }

  .feature-loop__intro::after {
    display: none;
  }

  .feature-loop__eyebrow {
    width: fit-content;
    margin-bottom: 12px;
    padding: 5px 11px;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 999px;
    color: #5865f2;
    background: rgba(99, 102, 241, 0.06);
    font-size: 12px;
    font-weight: 700;
  }

  .feature-loop__intro h3 {
    margin: 0;
    max-width: 420px;
    font-size: 25px;
    font-weight: 820;
    line-height: 1.28;
  }

  .feature-loop__intro p {
    margin: 0;
    max-width: 520px;
    color: #6b778d;
    font-size: 14px;
    line-height: 1.7;
    text-align: right;
  }

  .feature-step:nth-child(3),
  .course-cat-card:nth-child(2) { animation-delay: 0.03s; }
  .feature-step:nth-child(4),
  .course-cat-card:nth-child(3) { animation-delay: 0.06s; }
  .feature-step:nth-child(5),
  .course-cat-card:nth-child(4) { animation-delay: 0.09s; }
  .feature-step:nth-child(6),
  .course-cat-card:nth-child(5) { animation-delay: 0.12s; }
  .feature-step:nth-child(7),
  .course-cat-card:nth-child(6) { animation-delay: 0.15s; }

  .feature-step {
    position: relative;
    z-index: 1;
    display: flex;
    min-height: 154px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 30px 15px 8px;
    border-radius: 18px;
    color: inherit;
    text-decoration: none;
    transition:
      transform 0.18s ease,
      background-color 0.18s ease,
      box-shadow 0.18s ease;
    animation: home-reveal 0.32s ease both;

    &::before {
      content: '';
      position: absolute;
      top: 52px;
      left: 32px;
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: #fff;
      box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.1);
      transition: box-shadow 0.18s ease, background-color 0.18s ease;
    }

    &:hover {
      transform: translateY(-2px);
      background: rgba(255, 255, 255, 0.76);
      box-shadow: 0 14px 30px rgba(31, 41, 85, 0.06);
    }

    &:hover::before {
      background: #6366f1;
      box-shadow: 0 0 0 7px rgba(99, 102, 241, 0.13);
    }
  }

  .feature-step__index {
    order: -2;
    margin-left: 38px;
    margin-bottom: 6px;
    color: #a2acc1;
    font-size: 12px;
    font-weight: 800;
  }

  .feat-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    order: -1;
    border-radius: 50%;
    transition:
      transform 0.18s ease,
      box-shadow 0.18s ease;
  }

  .feature-step:hover .feat-icon {
    transform: translateY(-1px) rotate(-4deg);
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.12);
  }

  .feature-step--violet .feat-icon { background: #f0edff; color: #745cff; }
  .feature-step--green .feat-icon { background: #e9faef; color: #1fbf67; }
  .feature-step--blue .feat-icon { background: #eaf1ff; color: #3b6dff; }
  .feature-step--amber .feat-icon { background: #fff3df; color: #f59a23; }
  .feature-step--cyan .feat-icon { background: #e8fbff; color: #17a9d5; }
  .feature-step--rose .feat-icon { background: #ffedf3; color: #ef4d79; }

  .feature-step__body {
    display: grid;
    min-width: 0;
    gap: 7px;
  }

  .feature-step__body strong {
    color: #1a2440;
    font-size: 15px;
    font-weight: 800;
  }

  .feature-step__body small {
    overflow: hidden;
    color: #6f7c92;
    font-size: 13px;
    line-height: 1.55;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .feat-link {
    margin-top: auto;
    color: #5162f5;
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
    transition:
      color 0.18s ease,
      transform 0.18s ease;
  }

  .feature-step:hover .feat-link {
    color: #3f4ee8;
    transform: translateX(2px);
  }

  .course-hub-section {
    max-width: 1232px;
    margin: 0 auto;
    padding: 18px 24px 34px;
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
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .course-cat-card {
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    min-height: 78px;
    padding: 14px 16px;
    border: 1px solid #e9edf7;
    border-radius: 18px;
    color: inherit;
    text-decoration: none;
    transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      border-color 0.18s ease;
    animation: home-reveal 0.28s ease both;

    &:hover {
      transform: translateY(-2px);
      border-color: rgba(86, 98, 255, 0.26);
      box-shadow: 0 14px 28px rgba(42, 55, 104, 0.08);
    }

    &::before {
      display: none;
    }

    > div {
      min-width: 0;
      flex: 1;
    }

    strong,
    small,
    em {
      display: block;
    }

    strong {
      overflow: hidden;
      color: #202a44;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.2;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      margin-top: 5px;
      color: #69758b;
      font-size: 12px;
      line-height: 1.3;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    em {
      margin-top: 5px;
      color: #7a86a0;
      font-size: 12px;
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

    .feature-loop,
    .course-cat-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .feature-loop__intro {
      grid-column: 1 / -1;
      grid-row: auto;
      min-height: 0;
      align-items: flex-start;
      flex-direction: column;

      p {
        text-align: left;
      }
    }

    .feature-step {
      min-height: 150px;
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

    .feature-loop,
    .course-cat-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .feature-loop__intro,
    .feature-step {
      grid-column: 1 / -1;
    }

    .feature-step {
      min-height: 138px;
    }

    .feature-step .feat-link {
      justify-self: start;
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
    .feature-loop,
    .course-cat-grid {
      grid-template-columns: 1fr;
    }

    .feature-loop {
      border-radius: 22px;
    }

    .feature-loop__intro,
    .feature-step {
      grid-column: 1;
    }

    .stats-card__item::before {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .reveal-on-scroll {
      opacity: 1;
      transform: none;
      transition: none;
    }

    .hero-left > *,
    .visual-stage,
    .visual-stage::after,
    .hero-photo,
    .floating-card,
    .mini-chart i,
    .feature-loop,
    .feature-loop::before,
    .feature-loop::after,
    .feature-loop__intro::after,
    .feature-step,
    .course-cat-card {
      animation: none;
    }

    .hero-photo,
    .floating-card,
    .feature-step,
    .course-cat-card,
    .btn-primary,
    .btn-outline {
      transition: none;
    }

    .visual-stage:hover .hero-photo--library,
    .visual-stage:hover .hero-photo--console,
    .visual-stage:hover .hero-photo--team,
    .floating-card:hover,
    .feature-step:hover {
      transform: none;
    }
  }
</style>
