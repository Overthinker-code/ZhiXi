<script setup lang="ts">
  import { ref } from 'vue';
  import { useRouter } from 'vue-router';
  import logoImg from '@/assets/logo.svg?url';

  const router = useRouter();
  const subscribeEmail = ref('');
  const subscribeSent = ref(false);

  const productLinks = [
    { label: 'AI 伴学', route: 'TutorChat' },
    { label: '课程中心', route: 'CourseList' },
    { label: '学情档案', route: 'ProfileLearningData' },
    { label: '资源生成中心', route: 'CourseResourceGeneration' },
    { label: '题库练习', route: 'LearningPractice' },
  ];

  const supportLinks = [
    { label: '帮助中心', route: 'MarketingSolutions' },
    { label: '常见问题', route: 'MarketingPricing' },
    { label: '联系客服', route: 'MarketingAbout' },
    { label: '开发者文档', route: 'MarketingAbout' },
  ];

  const aboutLinks = [
    { label: '关于智屿', route: 'MarketingAbout' },
    { label: '解决方案', route: 'MarketingSolutions' },
    { label: '价格方案', route: 'MarketingPricing' },
    { label: '加入我们', route: 'MarketingAbout' },
  ];

  const legalLinks = [
    { label: '服务条款', route: 'MarketingAbout' },
    { label: '隐私政策', route: 'MarketingAbout' },
    { label: '免责声明', route: 'MarketingAbout' },
  ];

  const navigate = (name: string) => {
    router.push({ name });
  };

  const handleSubscribe = () => {
    if (!subscribeEmail.value.trim()) return;
    subscribeSent.value = true;
    subscribeEmail.value = '';
    setTimeout(() => {
      subscribeSent.value = false;
    }, 3000);
  };
</script>

<template>
  <footer class="site-footer">
    <div class="site-footer__main">
      <div class="site-footer__grid">
        <!-- 列1：品牌 -->
        <div class="site-footer__col site-footer__col--brand">
          <div class="site-footer__logo">
            <img :src="logoImg" alt="智屿" class="site-footer__logo-img" />
            <strong>智屿</strong>
          </div>
          <p class="site-footer__slogan">
            智能教育平台 · 让因材施教可落地
          </p>
        </div>

        <!-- 列2：产品服务 -->
        <div class="site-footer__col">
          <h4 class="site-footer__heading">产品服务</h4>
          <ul class="site-footer__list">
            <li v-for="link in productLinks" :key="link.label">
              <button type="button" @click="navigate(link.route)">
                {{ link.label }}
              </button>
            </li>
          </ul>
        </div>

        <!-- 列3：支持与帮助 -->
        <div class="site-footer__col">
          <h4 class="site-footer__heading">支持与帮助</h4>
          <ul class="site-footer__list">
            <li v-for="link in supportLinks" :key="link.label">
              <button type="button" @click="navigate(link.route)">
                {{ link.label }}
              </button>
            </li>
          </ul>
        </div>

        <!-- 列4：关于我们 -->
        <div class="site-footer__col">
          <h4 class="site-footer__heading">关于我们</h4>
          <ul class="site-footer__list">
            <li v-for="link in aboutLinks" :key="link.label">
              <button type="button" @click="navigate(link.route)">
                {{ link.label }}
              </button>
            </li>
          </ul>
        </div>

        <!-- 列5：订阅 -->
        <div class="site-footer__col site-footer__col--subscribe">
          <h4 class="site-footer__heading">订阅学习资讯</h4>
          <p class="site-footer__subscribe-desc">
            获取最新课程动态、AI 教育趋势与活动通知
          </p>
          <form class="site-footer__subscribe" @submit.prevent="handleSubscribe">
            <input
              v-model="subscribeEmail"
              type="email"
              placeholder="请输入邮箱地址"
              aria-label="订阅邮箱"
            />
            <button type="submit">发送</button>
          </form>
          <p v-if="subscribeSent" class="site-footer__subscribe-tip">
            订阅成功，感谢关注！
          </p>
        </div>
      </div>
    </div>

    <div class="site-footer__bottom">
      <div class="site-footer__bottom-inner">
        <span>© {{ new Date().getFullYear() }} 智屿智能教育 保留所有权利</span>
        <div class="site-footer__legal">
          <button
            v-for="link in legalLinks"
            :key="link.label"
            type="button"
            @click="navigate(link.route)"
          >
            {{ link.label }}
          </button>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped lang="less">
  .site-footer__main {
    max-width: 1232px;
    margin: 0 auto;
    padding: 28px 24px 18px;
  }

  .site-footer__grid {
    display: grid;
    grid-template-columns: 1.35fr 0.84fr 0.84fr 0.84fr 1.55fr;
    gap: 42px;
  }

  .site-footer__col {
    min-width: 0;
  }

  .site-footer__logo {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;

    strong {
      font-size: 20px;
      font-weight: 700;
      color: #1a2440;
      letter-spacing: 0.02em;
    }
  }

  .site-footer__logo-img {
    width: 36px;
    height: 36px;
  }

  .site-footer__slogan {
    margin: 0 0 20px;
    font-size: 13px;
    line-height: 1.65;
    color: #68758d;
    max-width: 220px;
  }

  .site-footer__heading {
    margin: 0 0 18px;
    font-size: 14px;
    font-weight: 800;
    color: #1c2742;
    letter-spacing: 0.02em;
  }

  .site-footer__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;

    button {
      border: none;
      background: transparent;
      padding: 0;
      color: #68758d;
      font-size: 13px;
      cursor: pointer;
      text-align: left;
      transition: color 0.2s;

      &:hover {
        color: #4f5dfb;
      }
    }
  }

  .site-footer__subscribe-desc {
    margin: 0 0 14px;
    font-size: 12px;
    line-height: 1.6;
    color: #7b879c;
  }

  .site-footer__subscribe {
    display: flex;
    gap: 8px;

    input {
      flex: 1;
      min-width: 0;
      height: 40px;
      padding: 0 14px;
      border-radius: 8px;
      border: 1px solid #dce4f2;
      background: #fff;
      color: #1c2742;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;

      &::placeholder {
        color: #a2adc0;
      }

      &:focus {
        border-color: rgba(81, 98, 245, 0.6);
      }
    }

    button {
      flex-shrink: 0;
      height: 40px;
      padding: 0 17px;
      border: none;
      border-radius: 8px;
      background: linear-gradient(135deg, #5662ff, #4151f2);
      color: #fff;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.9;
      }
    }
  }

  .site-footer__subscribe-tip {
    margin: 10px 0 0;
    font-size: 12px;
    color: #18a35d;
  }

  .site-footer__bottom {
    border-top: 1px solid #e1e7f3;
    background: rgba(255, 255, 255, 0.72);
  }

  .site-footer__bottom-inner {
    max-width: 1232px;
    margin: 0 auto;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px 24px;
    font-size: 12px;
    color: #7b879c;
  }

  .site-footer__legal {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-left: auto;

    button {
      border: none;
      background: transparent;
      padding: 0;
      color: #7b879c;
      font-size: 12px;
      cursor: pointer;
      transition: color 0.2s;

      &:hover {
        color: #4f5dfb;
      }
    }
  }

  @media (max-width: 1024px) {
    .site-footer__grid {
      grid-template-columns: repeat(3, 1fr);
    }

    .site-footer__col--brand {
      grid-column: 1 / -1;
    }

    .site-footer__col--subscribe {
      grid-column: 1 / -1;
      max-width: 420px;
    }
  }

  @media (max-width: 640px) {
    .site-footer__main {
      padding: 40px 24px 32px;
    }

    .site-footer__grid {
      grid-template-columns: 1fr 1fr;
      gap: 28px;
    }

    .site-footer__col--brand,
    .site-footer__col--subscribe {
      grid-column: 1 / -1;
    }

    .site-footer__bottom-inner {
      padding: 16px 24px;
      flex-direction: column;
      align-items: flex-start;
    }

    .site-footer__legal {
      margin-left: 0;
    }
  }
</style>
