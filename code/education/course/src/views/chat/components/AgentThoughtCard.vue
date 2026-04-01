<script setup lang="ts">
  import { computed, ref } from 'vue';

  const props = defineProps<{
    thoughts: string[];
  }>();

  const expanded = ref(true);
  const parsed = computed(() =>
    (props.thoughts || []).map((text, idx) => {
      const icon = text.includes('工具') || text.includes('🛠️')
        ? '🛠️'
        : text.includes('路由') || text.includes('Router')
          ? '🤖'
          : text.includes('策略') || text.includes('降级')
            ? '🔄'
            : '💡';
      return { id: idx, icon, text };
    })
  );
</script>

<template>
  <div v-if="parsed.length" class="thought-card">
    <div class="head" @click="expanded = !expanded">
      <span class="pulse"></span>
      <span class="title">智能体思维链</span>
      <span class="toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    <div v-if="expanded" class="tree">
      <div v-for="item in parsed" :key="item.id" class="node">
        <span class="icon">{{ item.icon }}</span>
        <span class="text">{{ item.text }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .thought-card {
    margin: 0 0 10px 8px;
    border: 1px solid #dbe2ee;
    border-radius: 12px;
    background: #f4f7fb;
    overflow: hidden;

    .head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      cursor: pointer;

      .title {
        margin-right: auto;
        margin-left: 8px;
        font-size: 12px;
        font-weight: 600;
        color: #334155;
      }

      .toggle {
        font-size: 12px;
        color: #64748b;
      }

      .pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #64748b;
        animation: pulse 1.5s ease infinite;
      }
    }

    .tree {
      padding: 0 10px 10px;

      .node {
        display: flex;
        align-items: flex-start;
        gap: 6px;
        padding: 6px 0;
        border-top: 1px dashed #d3dbe8;

        .icon {
          line-height: 1.3;
        }

        .text {
          font-size: 12px;
          color: #475569;
          line-height: 1.5;
        }
      }
    }
  }

  @keyframes pulse {
    0% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.4;
      transform: scale(1.4);
    }
    100% {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>
