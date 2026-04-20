<template>
  <div class="login-form-wrapper">
    <div class="login-form-title">{{ $t('login.form.title') }}</div>
    <div class="login-form-sub-title">{{ $t('login.form.subTitle') }}</div>
    <div class="login-form-error-msg">{{ errorMessage }}</div>

    <a-tabs v-model:active-key="activeTab" class="login-tabs">
      <a-tab-pane key="login" :title="$t('login.form.login')">
        <a-form :model="loginForm" class="login-form" layout="vertical" @submit="handleLogin">
          <a-form-item
            field="username"
            :rules="[{ required: true, message: $t('login.form.userName.errMsg') }]"
            :validate-trigger="['change', 'blur']"
            hide-label
          >
            <a-input v-model="loginForm.username" :placeholder="$t('login.form.userName.placeholder')">
              <template #prefix>
                <icon-user />
              </template>
            </a-input>
          </a-form-item>
          <a-form-item
            field="password"
            :rules="[{ required: true, message: $t('login.form.password.errMsg') }]"
            :validate-trigger="['change', 'blur']"
            hide-label
          >
            <a-input-password
              v-model="loginForm.password"
              :placeholder="$t('login.form.password.placeholder')"
              allow-clear
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </a-form-item>
          <a-space :size="16" direction="vertical">
            <div class="login-form-password-actions">
              <a-checkbox
                :model-value="loginConfig.rememberPassword"
                @change="setRememberPassword as any"
              >
                {{ $t('login.form.rememberPassword') }}
              </a-checkbox>
              <a-link @click="activeTab = 'recovery'">{{ $t('login.form.forgetPassword') }}</a-link>
            </div>
            <a-button type="primary" html-type="submit" long :loading="loading">
              {{ $t('login.form.login') }}
            </a-button>
          </a-space>
        </a-form>
      </a-tab-pane>

      <a-tab-pane key="register" :title="$t('login.form.register')">
        <a-form :model="registerForm" class="login-form" layout="vertical" @submit="handleRegister">
          <a-form-item
            field="email"
            :rules="[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]"
            :validate-trigger="['change', 'blur']"
            hide-label
          >
            <a-input v-model="registerForm.email" placeholder="邮箱地址">
              <template #prefix>
                <icon-email />
              </template>
            </a-input>
          </a-form-item>
          <a-form-item field="full_name" hide-label>
            <a-input v-model="registerForm.full_name" placeholder="姓名（可选）">
              <template #prefix>
                <icon-user />
              </template>
            </a-input>
          </a-form-item>
          <a-form-item
            field="password"
            :rules="[
              { required: true, message: '请输入密码' },
              { minLength: 6, message: '密码至少6位' },
            ]"
            :validate-trigger="['change', 'blur']"
            hide-label
          >
            <a-input-password v-model="registerForm.password" placeholder="密码（至少6位）" allow-clear>
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </a-form-item>
          <a-form-item
            field="confirmPassword"
            :rules="[
              { required: true, message: '请确认密码' },
              { validator: validateConfirmPassword },
            ]"
            :validate-trigger="['change', 'blur']"
            hide-label
          >
            <a-input-password v-model="registerForm.confirmPassword" placeholder="确认密码" allow-clear>
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </a-form-item>
          <a-space :size="16" direction="vertical">
            <a-button type="primary" html-type="submit" long :loading="loading">
              {{ $t('login.form.register') }}
            </a-button>
          </a-space>
        </a-form>
      </a-tab-pane>

      <a-tab-pane key="recovery" :title="$t('login.form.forgetPassword')">
        <a-form :model="recoveryForm" class="login-form" layout="vertical" @submit="handleRecovery">
          <a-form-item
            field="email"
            :rules="[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]"
            :validate-trigger="['change', 'blur']"
            hide-label
          >
            <a-input v-model="recoveryForm.email" placeholder="输入注册邮箱">
              <template #prefix>
                <icon-email />
              </template>
            </a-input>
          </a-form-item>
          <a-space :size="16" direction="vertical">
            <a-button type="primary" html-type="submit" long :loading="loading">
              发送重置邮件
            </a-button>
            <a-button type="text" long @click="activeTab = 'login'">返回登录</a-button>
          </a-space>
        </a-form>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script lang="ts" setup>
  import { ref, reactive } from 'vue';
  import { useRouter } from 'vue-router';
  import { Message } from '@arco-design/web-vue';
  import type { ValidatedError } from '@arco-design/web-vue';
  import { useI18n } from 'vue-i18n';
  import { useStorage } from '@vueuse/core';
  import { useUserStore } from '@/store';
  import useLoading from '@/hooks/loading';
  import type { LoginData, RegisterData } from '@/api/user';
  import { register, recoverPassword } from '@/api/user';

  const router = useRouter();
  const { t } = useI18n();
  const errorMessage = ref('');
  const { loading, setLoading } = useLoading();
  const userStore = useUserStore();
  const activeTab = ref('login');

  const loginConfig = useStorage('login-config', {
    rememberPassword: true,
    username: 'admin@example.com',
    password: 'admin123456',
  });
  if (
    loginConfig.value.username === 'admin@example.com' &&
    loginConfig.value.password === 'admin123'
  ) {
    loginConfig.value.password = 'admin123456';
  }

  const loginForm = reactive({
    username: loginConfig.value.username,
    password: loginConfig.value.password,
  });

  const registerForm = reactive({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });

  const recoveryForm = reactive({
    email: '',
  });

  const validateConfirmPassword = (value: string, callback: (error?: string) => void) => {
    if (value !== registerForm.password) {
      callback('两次输入的密码不一致');
    } else {
      callback();
    }
  };

  const handleLogin = async ({
    errors,
    values,
  }: {
    errors: Record<string, ValidatedError> | undefined;
    values: Record<string, any>;
  }) => {
    if (loading.value) return;
    if (!errors) {
      setLoading(true);
      try {
        await userStore.login(values as LoginData);
        try {
          await userStore.info();
        } catch (infoErr) {
          errorMessage.value = (infoErr as Error).message;
          return;
        }
        const { redirect, ...othersQuery } = router.currentRoute.value.query;
        const roleDefaultRoute =
          userStore.role === 'teacher' ? 'Workplace' : 'AssistantHome';
        router.push({
          name: (redirect as string) || roleDefaultRoute,
          query: { ...othersQuery },
        });
        Message.success(t('login.form.login.success'));
        const { rememberPassword } = loginConfig.value;
        const { username, password } = values;
        loginConfig.value.username = rememberPassword ? username : '';
        loginConfig.value.password = rememberPassword ? password : '';
      } catch (err) {
        errorMessage.value = (err as Error).message;
      } finally {
        setLoading(false);
      }
    }
  };

  const handleRegister = async ({
    errors,
    values,
  }: {
    errors: Record<string, ValidatedError> | undefined;
    values: Record<string, any>;
  }) => {
    if (loading.value) return;
    if (!errors) {
      setLoading(true);
      try {
        const data: RegisterData = {
          email: values.email,
          username: values.email.split('@')[0] || values.email,
          password: values.password,
          full_name: values.full_name || undefined,
        };
        await register(data);
        Message.success('注册成功，请登录');
        activeTab.value = 'login';
        loginForm.username = values.email;
        loginForm.password = '';
      } catch (err) {
        errorMessage.value = (err as Error).message;
      } finally {
        setLoading(false);
      }
    }
  };

  const handleRecovery = async ({
    errors,
    values,
  }: {
    errors: Record<string, ValidatedError> | undefined;
    values: Record<string, any>;
  }) => {
    if (loading.value) return;
    if (!errors) {
      setLoading(true);
      try {
        await recoverPassword(values.email);
        Message.success('密码重置邮件已发送，请查收邮箱');
        activeTab.value = 'login';
      } catch (err) {
        errorMessage.value = (err as Error).message;
      } finally {
        setLoading(false);
      }
    }
  };

  const setRememberPassword = (value: boolean) => {
    loginConfig.value.rememberPassword = value;
  };
</script>

<style lang="less" scoped>
  .login-form {
    &-wrapper {
      width: 320px;
    }

    &-title {
      color: var(--color-text-1);
      font-weight: 500;
      font-size: 24px;
      line-height: 32px;
    }

    &-sub-title {
      color: var(--color-text-3);
      font-size: 16px;
      line-height: 24px;
    }

    &-error-msg {
      height: 32px;
      color: rgb(var(--red-6));
      line-height: 32px;
    }

    &-password-actions {
      display: flex;
      justify-content: space-between;
    }
  }

  .login-tabs {
    margin-top: 20px;
  }
</style>
