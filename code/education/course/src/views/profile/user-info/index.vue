<template>
  <ZyPageShell title="用户设置" subtitle="管理个人资料、账号安全与实名认证">
    <ZyPageEnter>
      <section class="profile-header zy-stagger-child">
        <a-avatar :size="96" class="profile-avatar">
          <img
            alt=""
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=zhiyu"
          />
        </a-avatar>
        <div class="profile-meta-block">
          <h2>{{ displayName }}</h2>
          <div class="meta-row">
            <span>账号 ID：{{ userStore.accountId || '—' }}</span>
            <span v-if="userStore.email">邮箱：{{ userStore.email }}</span>
          </div>
          <div class="verify-row">
            <a-tag color="green" size="small">
              <template #icon><icon-check-circle /></template>
              实名认证 · 已认证
            </a-tag>
            <span v-if="userStore.registrationDate">注册于 {{ userStore.registrationDate }}</span>
            <span>最近更新：今天</span>
          </div>
        </div>
      </section>

      <div class="tab-bar zy-stagger-child">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="['tab-btn', { active: activeSection === tab.key }]"
          @click="activeSection = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <a-row :gutter="16" class="zy-stagger-child">
        <a-col :xs="24" :xl="16">
          <a-card v-show="activeSection === 'basic'" class="card-block form-card">
            <template #title>基础信息</template>
            <a-form :model="formData" layout="vertical" class="settings-form">
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="邮箱">
                    <a-input v-model="formData.email" placeholder="联系邮箱" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="昵称">
                    <a-input v-model="formData.nickname" placeholder="显示名称" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="国家/地区">
                    <a-input v-model="formData.country" placeholder="中国" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="省市区">
                    <a-input v-model="formData.region" placeholder="广东省 深圳市" />
                  </a-form-item>
                </a-col>
                <a-col :span="24">
                  <a-form-item label="详细地址">
                    <a-input v-model="formData.address" placeholder="街道门牌号" />
                  </a-form-item>
                </a-col>
                <a-col :span="24">
                  <a-form-item label="个人简介">
                    <a-textarea
                      v-model="formData.introduction"
                      :max-length="200"
                      show-word-limit
                      placeholder="一句话介绍自己"
                      :auto-size="{ minRows: 3, maxRows: 5 }"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-space>
                <a-button type="primary" @click="handleSaveBasic">保存</a-button>
                <a-button @click="resetBasic">重置</a-button>
              </a-space>
            </a-form>
          </a-card>

          <a-card v-show="activeSection === 'security'" class="card-block form-card">
            <template #title>安全设置</template>
            <div class="setting-row">
              <div>
                <strong>登录密码</strong>
                <p>定期更新密码可提升账号安全</p>
              </div>
              <a-button type="outline" @click="router.push('/login')">修改密码</a-button>
            </div>
            <div class="setting-row">
              <div>
                <strong>手机号</strong>
                <p>{{ userStore.phone || '未绑定' }}</p>
              </div>
              <a-button type="text">绑定</a-button>
            </div>
            <div class="setting-row">
              <div>
                <strong>两步验证</strong>
                <p>开启后登录需额外验证码</p>
              </div>
              <a-switch v-model="securityPrefs.twoFactor" />
            </div>
          </a-card>

          <a-card v-show="activeSection === 'verify'" class="card-block form-card">
            <template #title>实名认证</template>
            <div class="verify-card">
              <icon-check-circle class="verify-icon" />
              <div>
                <strong>已完成实名认证</strong>
                <p>你的账号已通过身份核验，可正常使用全部学习功能。</p>
              </div>
            </div>
            <div class="setting-row">
              <div>
                <strong>认证姓名</strong>
                <p>{{ displayName }}</p>
              </div>
            </div>
            <div class="setting-row">
              <div>
                <strong>认证时间</strong>
                <p>{{ userStore.registrationDate || '2024-09-01' }}</p>
              </div>
            </div>
          </a-card>
        </a-col>

        <a-col :xs="24" :xl="8">
          <a-card class="card-block widget-card">
            <template #title>资料完整度</template>
            <div class="completeness-wrap">
              <a-progress type="circle" :percent="profileCompleteness" :width="100" />
              <p>完善资料可获得更多个性化推荐</p>
            </div>
          </a-card>

          <a-card class="card-block widget-card">
            <template #title>账号安全提示</template>
            <ul class="tip-list">
              <li v-for="tip in securityTips" :key="tip">
                <icon-info-circle />
                <span>{{ tip }}</span>
              </li>
            </ul>
          </a-card>

          <a-card class="card-block widget-card">
            <template #title>最近活动</template>
            <ul class="activity-list">
              <li v-for="item in recentActivities" :key="item.text">
                <span class="activity-time">{{ item.time }}</span>
                <span>{{ item.text }}</span>
              </li>
            </ul>
          </a-card>
        </a-col>
      </a-row>
    </ZyPageEnter>
  </ZyPageShell>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store';

  const userStore = useUserStore();
  const router = useRouter();
  const displayName = computed(() => userStore.name || '同学');
  const activeSection = ref('basic');

  const tabs = [
    { key: 'basic', label: '基础信息' },
    { key: 'security', label: '安全设置' },
    { key: 'verify', label: '实名认证' },
  ];

  const formData = reactive({
    nickname: userStore.name || '',
    email: userStore.email || '',
    country: '中国',
    region: '',
    address: '',
    introduction: userStore.introduction || '',
  });

  const securityPrefs = reactive({
    twoFactor: false,
  });

  const profileCompleteness = computed(() => {
    let score = 40;
    if (formData.nickname) score += 15;
    if (formData.email) score += 15;
    if (formData.introduction) score += 15;
    if (formData.region) score += 8;
    if (formData.address) score += 7;
    return Math.min(100, score);
  });

  const securityTips = [
    '建议每 90 天更新一次登录密码',
    '不要在公共设备上保持登录状态',
    '绑定手机号可提升账号找回成功率',
  ];

  const recentActivities = [
    { time: '今天', text: '更新了个人简介' },
    { time: '昨天', text: '完成学情诊断更新' },
    { time: '3 天前', text: '登录智屿学习平台' },
  ];

  function handleSaveBasic() {
    userStore.setInfo({
      name: formData.nickname,
      email: formData.email,
      introduction: formData.introduction,
    });
    Message.success('已保存基本信息');
  }

  function resetBasic() {
    formData.nickname = userStore.name || '';
    formData.email = userStore.email || '';
    formData.introduction = userStore.introduction || '';
    formData.country = '中国';
    formData.region = '';
    formData.address = '';
  }
</script>

<style scoped lang="less">
  .profile-header {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 28px 32px;
    margin-bottom: 16px;
    border-radius: 20px;
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #ecfeff 100%);
    border: 1px solid rgba(99, 102, 241, 0.12);
    box-shadow: var(--zy-shadow-card);
  }

  .profile-avatar {
    flex-shrink: 0;
    border: 4px solid #fff;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2);
  }

  .profile-meta-block {
    flex: 1;
    min-width: 0;

    h2 {
      margin: 0 0 8px;
      font-size: 24px;
      font-weight: 800;
      color: var(--zy-color-text-primary);
    }
  }

  .meta-row,
  .verify-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    font-size: var(--zy-text-sm);
    color: var(--zy-color-text-secondary);
  }

  .verify-row {
    margin-top: 8px;
  }

  .tab-bar {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
    padding: 4px;
    border-radius: var(--zy-radius-pill);
    background: #fff;
    border: 1px solid rgba(99, 102, 241, 0.1);
    width: fit-content;
  }

  .tab-btn {
    padding: 8px 20px;
    border: none;
    border-radius: var(--zy-radius-pill);
    background: transparent;
    color: var(--zy-color-text-secondary);
    font-size: var(--zy-text-sm);
    font-weight: 600;
    cursor: pointer;
    transition: all var(--zy-duration-fast) ease;

    &.active {
      background: var(--zy-gradient-brand);
      color: #fff;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }
  }

  .card-block {
    margin-bottom: 16px;
    border-radius: var(--zy-radius-card);
  }

  .form-card {
    min-height: 420px;
  }

  .settings-form {
    max-width: 100%;
  }

  .setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 0;
    border-bottom: 1px solid #f1f5f9;

    &:last-child {
      border-bottom: none;
    }

    strong {
      display: block;
      color: var(--zy-color-text-primary);
      font-size: 14px;
    }

    p {
      margin: 4px 0 0;
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-sm);
    }
  }

  .verify-card {
    display: flex;
    gap: 14px;
    padding: 16px;
    margin-bottom: 8px;
    border-radius: 12px;
    background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
    border: 1px solid rgba(22, 163, 74, 0.2);

    .verify-icon {
      font-size: 32px;
      color: #16a34a;
      flex-shrink: 0;
    }

    strong {
      display: block;
      margin-bottom: 4px;
      color: #166534;
    }

    p {
      margin: 0;
      font-size: 13px;
      color: #15803d;
    }
  }

  .completeness-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    text-align: center;

    p {
      margin: 0;
      font-size: 12px;
      color: var(--zy-color-text-secondary);
    }
  }

  .tip-list,
  .activity-list {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .tip-list li {
    display: flex;
    gap: 10px;
    padding: 10px 0;
    font-size: 13px;
    color: var(--zy-color-text-secondary);
    border-bottom: 1px solid #f1f5f9;

    svg {
      color: var(--zy-color-brand);
      flex-shrink: 0;
      margin-top: 2px;
    }

    &:last-child {
      border-bottom: none;
    }
  }

  .activity-list li {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 0;
    font-size: 13px;
    color: var(--zy-color-text-primary);
    border-bottom: 1px solid #f1f5f9;

    &:last-child {
      border-bottom: none;
    }
  }

  .activity-time {
    font-size: 11px;
    color: var(--zy-color-text-secondary);
  }

  @media (max-width: 900px) {
    .profile-header {
      flex-wrap: wrap;
    }

    .tab-bar {
      width: 100%;
      overflow-x: auto;
    }
  }
</style>
