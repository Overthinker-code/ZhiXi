<template>
  <a-card
    class="general-card chat-panel"
    title="课堂 AI 伴学"
    :bordered="false"
    :header-style="{ paddingBottom: '0' }"
    :body-style="{
      height: '100%',
      padding: '12px',
      display: 'flex',
      flexFlow: 'column',
      minHeight: 0,
    }"
  >
    <div class="chat-panel-content">
      <ClassroomQuickChat />
    </div>
  </a-card>
</template>

<script lang="ts" setup>
  import ClassroomQuickChat from '@/components/float-ai/ClassroomQuickChat.vue';
</script>

<style scoped lang="less">
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 520px;
    // padding: 20px;
    background-color: var(--color-bg-2);

    &-content {
      flex: 1;
      min-height: 0;
      margin: 0;
      overflow: hidden;
    }
  }
</style>
