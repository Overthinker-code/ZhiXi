<template>
  <a-card class="general-card" title="课堂签到人员列表">
    <div class="grid">
      <div v-for="item in rows" :key="item.id" class="student" :class="statusClass(item.status)">
        <div class="avatar">{{ item.name.slice(0, 1) }}</div>
        <div class="meta">
          <div class="name">{{ item.name }}</div>
          <div class="status">{{ item.status }}</div>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { demoAttendanceStudents } from '@/mock/demoData';

  const rows = computed(() => demoAttendanceStudents);

  const statusClass = (status: string) => {
    if (status === '已签到') return 'ok';
    if (status === '迟到') return 'late';
    if (status === '请假') return 'leave';
    return 'absent';
  };
</script>

<style scoped lang="less">
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .student {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px;
    border-radius: 10px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;

    .avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #dbeafe;
      color: #1e3a8a;
      font-size: 12px;
      font-weight: 600;
    }

    .meta {
      min-width: 0;
    }

    .name {
      font-size: 12px;
      color: #1e293b;
    }

    .status {
      font-size: 11px;
      color: #64748b;
    }

    &.ok {
      border-color: #86efac;
      background: #f0fdf4;
    }

    &.late {
      border-color: #fcd34d;
      background: #fffbeb;
    }

    &.leave {
      border-color: #93c5fd;
      background: #eff6ff;
    }

    &.absent {
      border-color: #fca5a5;
      background: #fef2f2;
    }
  }
</style>
