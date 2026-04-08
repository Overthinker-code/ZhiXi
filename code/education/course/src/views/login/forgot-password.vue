<template>
  <div class="auth-page">
    <a-card class="auth-card" title="找回密码">
      <p class="desc">输入注册邮箱，系统将发送重置密码邮件。</p>
      <a-form :model="form" layout="vertical" @submit="onSubmit">
        <a-form-item field="email" label="邮箱" required>
          <a-input v-model="form.email" placeholder="请输入注册邮箱" />
        </a-form-item>
        <a-space direction="vertical" fill>
          <a-button type="primary" html-type="submit" :loading="loading" long>
            发送重置邮件
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
  import { recoverPassword } from '@/api/user';

  const router = useRouter();
  const loading = ref(false);
  const form = reactive({ email: '' });

  const onSubmit = async () => {
    if (!form.email) {
      Message.warning('请先输入邮箱');
      return;
    }
    loading.value = true;
    try {
      await recoverPassword(form.email);
      Message.success('重置邮件已发送，请检查邮箱');
      goLogin();
    } catch (error) {
      Message.error((error as Error).message || '发送失败');
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
    width: 420px;
  }

  .desc {
    margin: 0 0 16px;
    color: var(--color-text-3);
  }
</style>
