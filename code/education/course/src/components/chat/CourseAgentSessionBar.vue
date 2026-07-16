<script setup lang="ts">
  import { IconLeft, IconRobot } from '@arco-design/web-vue/es/icon';
  import type { CourseAgentContractSummary } from '@/api/ai-chat';

  defineProps<{
    agent: CourseAgentContractSummary;
    courseTitle?: string;
  }>();

  const emit = defineEmits<{
    (event: 'back'): void;
  }>();
</script>

<template>
  <header class="course-agent-session">
    <button type="button" class="course-agent-session__back" aria-label="返回课程助手" @click="emit('back')">
      <icon-left />
    </button>
    <span class="course-agent-session__avatar"><icon-robot /></span>
    <div class="course-agent-session__identity">
      <div>
        <strong>{{ agent.label }}</strong>
        <span>{{ courseTitle || '当前课程' }} · 专用执行会话</span>
      </div>
      <p>{{ agent.description }}</p>
    </div>
    <div class="course-agent-session__scope" aria-label="本智能体交付范围">
      <span v-for="item in agent.outputs.slice(0, 4)" :key="item">{{ item }}</span>
    </div>
    <span class="course-agent-session__bound">课程上下文已绑定</span>
  </header>
</template>

<style scoped lang="scss">
  .course-agent-session {
    z-index: 6;
    min-height: 76px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 22px;
    border-bottom: 1px solid #e8ebf4;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 8px 24px rgba(48, 54, 103, 0.045);
  }

  .course-agent-session__back {
    width: 34px;
    height: 34px;
    display: inline-grid;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid #e0e5f0;
    border-radius: 11px;
    color: #526078;
    background: #fff;
    cursor: pointer;

    &:hover {
      border-color: #c9d0ff;
      color: #4f46e5;
      background: #f7f7ff;
    }
  }

  .course-agent-session__avatar {
    width: 40px;
    height: 40px;
    display: inline-grid;
    flex: 0 0 auto;
    place-items: center;
    border-radius: 14px;
    color: #fff;
    background: linear-gradient(135deg, #5f6df8, #7768ed);
    box-shadow: 0 8px 18px rgba(91, 82, 225, 0.2);
    font-size: 18px;
  }

  .course-agent-session__identity {
    min-width: 220px;

    > div {
      display: flex;
      align-items: baseline;
      gap: 9px;
    }

    strong {
      color: #1c2437;
      font-size: 15px;
    }

    span,
    p {
      color: #7a8498;
      font-size: 12px;
    }

    p {
      max-width: 520px;
      margin: 3px 0 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .course-agent-session__scope {
    min-width: 0;
    display: flex;
    flex: 1;
    justify-content: flex-end;
    gap: 6px;

    span {
      padding: 5px 9px;
      border-radius: 999px;
      color: #57627a;
      background: #f3f5fa;
      font-size: 11px;
      white-space: nowrap;
    }
  }

  .course-agent-session__bound {
    flex: 0 0 auto;
    padding: 6px 10px;
    border: 1px solid #d8dcff;
    border-radius: 999px;
    color: #5147c7;
    background: #f5f4ff;
    font-size: 11px;
    font-weight: 700;
  }

  @media (max-width: 1120px) {
    .course-agent-session__scope,
    .course-agent-session__identity p {
      display: none;
    }
  }

  @media (max-width: 760px) {
    .course-agent-session {
      padding-inline: 12px;
    }

    .course-agent-session__identity {
      min-width: 0;
      flex: 1;

      > div span {
        display: none;
      }
    }

    .course-agent-session__bound {
      display: none;
    }
  }
</style>
