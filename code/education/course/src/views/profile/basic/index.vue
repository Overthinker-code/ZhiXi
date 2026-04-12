<template>
  <div class="settings-page">
    <Breadcrumb :items="['menu.profile', 'menu.profile.basic']" />

    <a-card class="summary-card" :bordered="false">
      <div class="summary-inner">
        <div class="avatar-wrap">
          <a-avatar :size="96" class="avatar">
            <img v-if="avatarUrl" :src="avatarUrl" alt="" />
            <span v-else>{{ nameInitial }}</span>
          </a-avatar>
          <button type="button" class="cam-btn" aria-label="更换头像">
            <IconCamera />
          </button>
        </div>
        <div class="summary-grid">
          <div class="col">
            <div class="row">
              <span class="lbl">用户名</span>
              <span class="val">{{ displayName }}</span>
            </div>
            <div class="row">
              <span class="lbl">账号ID</span>
              <span class="val">{{ accountId }}</span>
            </div>
            <div class="row">
              <span class="lbl">注册时间</span>
              <span class="val">{{ registrationTime }}</span>
            </div>
          </div>
          <div class="col">
            <div class="row">
              <span class="lbl">实名认证</span>
              <span class="val cert">{{ certText }}</span>
            </div>
            <div class="row">
              <span class="lbl">手机号码</span>
              <span class="val">{{ maskedPhone }}</span>
            </div>
          </div>
        </div>
      </div>
    </a-card>

    <a-card class="detail-card" :bordered="false">
      <a-tabs v-model:active-key="activeTab" type="line" class="settings-tabs">
        <a-tab-pane key="basic" title="基础信息">
          <a-form
            :model="form"
            layout="horizontal"
            :label-col-props="{ span: 6 }"
            :wrapper-col-props="{ span: 16 }"
            class="settings-form"
          >
            <a-form-item
              label="邮箱"
              field="email"
              :rules="[{ required: true, message: '请输入邮箱' }]"
            >
              <a-input
                v-model="form.email"
                placeholder="请输入邮箱地址，如xxx@bytedance.com"
              />
            </a-form-item>
            <a-form-item
              label="昵称"
              field="nickname"
              :rules="[{ required: true, message: '请输入昵称' }]"
            >
              <a-input v-model="form.nickname" placeholder="请输入您的昵称" />
            </a-form-item>
            <a-form-item
              label="国家/地区"
              field="country"
              :rules="[{ required: true, message: '请选择' }]"
            >
              <a-select
                v-model="form.country"
                placeholder="请选择"
                allow-clear
              >
                <a-option value="cn">中国</a-option>
                <a-option value="us">美国</a-option>
                <a-option value="jp">日本</a-option>
              </a-select>
            </a-form-item>
            <a-form-item
              label="所在区域"
              field="region"
              :rules="[{ required: true, message: '请选择' }]"
            >
              <a-select
                v-model="form.region"
                placeholder="请选择"
                allow-clear
              >
                <a-option value="hb">华北</a-option>
                <a-option value="hd">华东</a-option>
                <a-option value="hn">华南</a-option>
                <a-option value="hz">华中</a-option>
              </a-select>
            </a-form-item>
            <a-form-item label="具体地址" field="address">
              <a-input v-model="form.address" placeholder="请输入您的地址" />
            </a-form-item>
            <a-form-item label="个人简介" field="bio">
              <a-textarea
                v-model="form.bio"
                :max-length="200"
                show-word-limit
                :auto-size="{ minRows: 4, maxRows: 8 }"
                placeholder="请输入您的个人简介，最多不超过200字。"
              />
            </a-form-item>
            <a-form-item :wrapper-col-props="{ offset: 6, span: 16 }">
              <a-space>
                <a-button type="primary" @click="onSave">保存</a-button>
                <a-button @click="onReset">重置</a-button>
              </a-space>
            </a-form-item>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="security" title="安全设置">
          <div class="tab-placeholder">
            <p>登录密码、二次验证等安全项可在此管理。</p>
            <a-button type="outline" disabled>修改密码（即将开放）</a-button>
          </div>
        </a-tab-pane>
        <a-tab-pane key="verify" title="实名认证">
          <div class="tab-placeholder">
            <p>完成实名认证可享受更多课程与实验权限。</p>
            <a-tag v-if="userStore.certification === 1" color="green"
              >当前状态：已认证</a-tag
            >
            <a-tag v-else color="orangered">当前状态：未认证</a-tag>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { IconCamera } from '@arco-design/web-vue/es/icon';
  import { Message } from '@arco-design/web-vue';
  import { computed, onMounted, reactive, ref } from 'vue';
  import { useUserStore } from '@/store';

  const userStore = useUserStore();
  const activeTab = ref('basic');

  const displayName = computed(() => userStore.name || '卡布奇');
  const nameInitial = computed(() =>
    (displayName.value || '用').slice(0, 1).toUpperCase()
  );
  const avatarUrl = computed(() => userStore.avatar || '');
  const accountId = computed(
    () => userStore.accountId || userStore.phone || '15012312300'
  );
  const registrationTime = computed(
    () => userStore.registrationDate || '2013-05-10 12:10:00'
  );
  const certText = computed(() =>
    userStore.certification === 1 ? '已认证' : '未认证'
  );

  function maskPhone(phone: string) {
    if (!phone || phone.length < 8) return phone || '150****0000';
    const p = phone.replace(/\s/g, '');
    if (p.length <= 7) return p;
    return `${p.slice(0, 3)}****${p.slice(-4)}`;
  }

  const maskedPhone = computed(() => maskPhone(userStore.phone || '15012312300'));

  const defaultForm = () => ({
    email: userStore.email || 'student@zhiyu.edu.cn',
    nickname: userStore.name || '卡布奇',
    country: 'cn',
    region: 'hd',
    address: userStore.location || '',
    bio: userStore.introduction || '',
  });

  const form = reactive(defaultForm());
  const snapshot = ref(defaultForm());

  function syncFromStore() {
    Object.assign(form, defaultForm());
    snapshot.value = { ...form };
  }

  onMounted(async () => {
    if (!userStore.profileHydrated && userStore.getToken()) {
      try {
        await userStore.info();
      } catch {
        // 静默，使用占位展示
      }
    }
    syncFromStore();
  });

  function onSave() {
    userStore.setInfo({
      email: form.email,
      name: form.nickname,
      introduction: form.bio,
      location: form.address,
    });
    snapshot.value = { ...form };
    Message.success('已保存（本地）');
  }

  function onReset() {
    Object.assign(form, snapshot.value);
    Message.info('已重置为上次保存内容');
  }
</script>

<script lang="ts">
  export default {
    name: 'Basic',
  };
</script>

<style scoped lang="less">
  .settings-page {
    padding: 0 20px 32px;
    max-width: 1100px;
    margin: 0 auto;
  }

  .summary-card {
    margin-top: 8px;
    margin-bottom: 20px;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }

  .summary-inner {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 32px;
    padding: 8px 8px 4px;
  }

  .avatar-wrap {
    position: relative;
    flex-shrink: 0;
  }

  .avatar {
    border: 3px solid #fff;
    box-shadow: 0 4px 16px rgba(22, 119, 255, 0.15);
  }

  .cam-btn {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 2px solid #fff;
    background: #1677ff;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 0;
    font-size: 16px;
    box-shadow: 0 2px 8px rgba(22, 119, 255, 0.35);
  }

  .summary-grid {
    flex: 1;
    min-width: 280px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 24px 48px;
  }

  .col {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .row {
    display: flex;
    align-items: baseline;
    gap: 16px;
    font-size: 14px;
  }

  .lbl {
    color: var(--color-text-3);
    min-width: 72px;
    text-align: right;
  }

  .val {
    color: var(--color-text-1);
    font-weight: 500;
  }

  .cert {
    color: rgb(var(--green-6));
  }

  .detail-card {
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }

  .settings-tabs {
    :deep(.arco-tabs-nav-tab) {
      font-size: 15px;
    }

    :deep(.arco-tabs-tab-active) {
      color: #1677ff;
      font-weight: 600;
    }
  }

  .settings-form {
    max-width: 720px;
    padding-top: 16px;
  }

  .tab-placeholder {
    padding: 32px 8px;
    color: var(--color-text-2);
    line-height: 1.8;

    p {
      margin: 0 0 16px;
    }
  }
</style>
