<template>
  <div class="auth-page">
    <a-card class="auth-card" title="注册账号">
      <p class="desc">创建知曦账号，用于登录教学平台。</p>
      <a-form :model="form" layout="vertical" @submit="onSubmit">
        <a-form-item field="fullName" label="姓名" required>
          <a-input v-model="form.fullName" placeholder="请输入姓名" />
        </a-form-item>
        <a-form-item field="email" label="邮箱" required>
          <a-input v-model="form.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item field="password" label="密码" required>
          <a-input-password v-model="form.password" placeholder="至少8位密码" />
        </a-form-item>
        <a-form-item field="confirmPassword" label="确认密码" required>
          <a-input-password
            v-model="form.confirmPassword"
            placeholder="请再次输入密码"
          />
        </a-form-item>
        <a-space direction="vertical" fill>
          <a-button type="primary" html-type="submit" :loading="loading" long>
            提交注册
          </a-button>
          <a-button long @click="goLogin">返回登录</a-button>
        </a-space>
      </a-form>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import { registerUser } from '@/api/user';

  const router = useRouter();
  const loading = ref(false);
  const form = reactive({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const onSubmit = async () => {
    if (!form.fullName || !form.email || !form.password) {
      Message.warning('请完整填写注册信息');
      return;
    }
    if (form.password !== form.confirmPassword) {
      Message.warning('两次输入的密码不一致');
      return;
    }
    loading.value = true;
    try {
      await registerUser({
        email: form.email,
        password: form.password,
        full_name: form.fullName,
      });
      Message.success('注册成功，请登录');
      goLogin();
    } catch (error) {
      Message.error((error as Error).message || '注册失败');
    } finally {
      loading.value = false;
    }
  };

  const goLogin = () => {
    router.push({ name: 'login' });
  };
</script>

<style scoped lang="less">
  .auth-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-fill-2);
  }

  .auth-card {
    width: 460px;
  }

  .desc {
    margin: 0 0 16px;
    color: var(--color-text-3);
  }
</style>
