<template>
  <div class="container">
    <Breadcrumb :items="['menu.profile', 'menu.profile.userInfo']" />
    <div class="hero">
      <div class="hero-bg" />
      <div class="hero-inner">
        <a-avatar :size="88" class="avatar">
          <img
            alt=""
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=zhiyu"
          />
        </a-avatar>
        <h2 class="name">{{ displayName }}</h2>
        <div class="tags">
          <a-tag>{{ userStore.role === 'teacher' ? '教师' : '学生' }}</a-tag>
        </div>
      </div>
    </div>

    <a-row :gutter="16" class="main-row">
      <a-col :xs="24" :lg="16">
        <a-card title="我的课程" class="card-block">
          <LoadingState v-if="loadingCourses" skeleton :skeleton-rows="3" />
          <template v-else-if="courses.length">
            <a-row :gutter="[12, 12]">
              <a-col
                v-for="c in courses"
                :key="c.id"
                :xs="24"
                :sm="12"
                :md="8"
              >
                <div class="course-card" @click="goCourse(c.id)">
                  <div class="course-title">{{ c.name }}</div>
                  <div class="course-sub">{{ c.course_type || c.identifier }}</div>
                </div>
              </a-col>
            </a-row>
          </template>
          <EmptyState
            v-else
            compact
            text="暂无课程"
            action-text="浏览课程"
            @action="router.push('/course/list')"
          />
        </a-card>
        <a-card title="最新动态" class="card-block">
          <EmptyState compact text="暂无动态" description="学习活动将在此展示" />
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="8">
        <a-card title="我的小组" class="card-block">
          <EmptyState compact text="暂无小组" description="加入课程小组后将在此展示" />
        </a-card>
        <a-card title="站内通知" class="card-block notify">
          <EmptyState compact text="暂无通知" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store';
  import { fetchCourses, type Course } from '@/api/course';

  const userStore = useUserStore();
  const router = useRouter();
  const displayName = computed(() => userStore.name || '同学');
  const courses = ref<Course[]>([]);
  const loadingCourses = ref(false);

  function goCourse(id: string) {
    router.push(`/course/course-content?courseId=${id}`);
  }

  onMounted(async () => {
    loadingCourses.value = true;
    try {
      const res = await fetchCourses({ limit: 12 });
      courses.value = res.data || [];
    } catch {
      courses.value = [];
    } finally {
      loadingCourses.value = false;
    }
  });
</script>

<style scoped lang="less">
  .container {
    padding: 0 20px 24px;
  }

  .hero {
    position: relative;
    margin-bottom: 20px;
    border-radius: 16px;
    overflow: hidden;
    min-height: 180px;
    background: linear-gradient(135deg, #e8f4ff 0%, #f5f3ff 100%);
  }

  .hero-bg {
    position: absolute;
    inset: 0;
    opacity: 0.35;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 200'%3E%3Cpath fill='%236366f1' d='M0 120L60 105C120 90 240 60 360 55C480 50 600 70 720 80C840 90 960 90 1080 75C1200 60 1320 30 1380 15L1440 0V200H0Z'/%3E%3C/svg%3E")
      no-repeat bottom;
    background-size: cover;
  }

  .hero-inner {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 28px 16px 24px;
  }

  .avatar {
    border: 3px solid #fff;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2);
  }

  .name {
    margin: 12px 0 8px;
    font-size: 22px;
    color: #1e293b;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  .card-block {
    margin-bottom: 16px;
    border-radius: 12px;
  }

  .course-card {
    padding: 12px;
    border-radius: 10px;
    border: 1px solid rgba(99, 102, 241, 0.15);
    background: #fafdfb;
    height: 100%;
    cursor: pointer;
    transition: box-shadow var(--zy-duration-fast, 150ms) ease;

    &:hover {
      box-shadow: var(--zy-shadow-card-hover);
    }
  }

  .course-title {
    font-weight: 600;
    font-size: 15px;
    color: #1e293b;
  }

  .course-sub {
    font-size: 12px;
    color: #6b7a72;
    margin-top: 4px;
  }

  .notify {
    min-height: 120px;
  }
</style>
