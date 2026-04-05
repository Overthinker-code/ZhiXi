<script setup lang="ts">
  import { computed } from 'vue';

  const props = defineProps<{
    thoughts: string[];
    /** 流式生成中：最后一阶高亮脉冲 */
    streaming?: boolean;
  }>();

  /** 解析「【阶段】详情」；无前缀则整段作为详情 */
  const parsed = computed(() =>
    (props.thoughts || []).map((raw, idx) => {
      const m = String(raw).match(/^【([^】]+)】([\s\S]*)$/);
      if (m) {
        return { id: idx, tag: m[1].trim(), detail: (m[2] || '').trim() || '进行中…' };
      }
      return { id: idx, tag: '协作', detail: String(raw).trim() };
    })
  );

  const stageClass = (tag: string) => {
    if (tag.includes('主管') || tag.includes('拆解')) return 'tag-supervisor';
    if (tag.includes('知识检索') || tag.includes('工具')) return 'tag-kb';
    if (tag.includes('代码验证') || tag.includes('工具执行')) return 'tag-code';
    if (tag.includes('学科') || tag.includes('规划') || tag.includes('学情')) return 'tag-worker';
    if (tag.includes('汇总')) return 'tag-final';
    if (tag.includes('流水线') || tag.includes('策略')) return 'tag-meta';
    return 'tag-default';
  };
</script>

<template>
  <div v-if="parsed.length || streaming" class="pipeline-wrap">
    <div class="pipeline-head">
      <span class="pulse-dot" />
      <span class="title">多智能体协作流水线</span>
      <span v-if="streaming" class="live">实时</span>
    </div>
    <div class="pipeline-track">
      <template v-if="!parsed.length && streaming">
        <div class="step active">
          <span class="tag tag-wait">等待</span>
          <span class="detail">正在连接协作图，等待首条事件…</span>
        </div>
      </template>
      <template v-for="(item, i) in parsed" :key="item.id">
        <div
          class="step"
          :class="{
            active: streaming && i === parsed.length - 1,
            done: !streaming || i < parsed.length - 1,
          }"
        >
          <span class="tag" :class="stageClass(item.tag)">{{ item.tag }}</span>
          <span class="detail">{{ item.detail }}</span>
        </div>
        <span v-if="i < parsed.length - 1" class="arrow" aria-hidden="true">→</span>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
  .pipeline-wrap {
    margin: 0 0 12px 4px;
    padding: 10px 12px;
    border-radius: 12px;
    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
    border: 1px solid #e2e8f0;
  }

  .pipeline-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;

    .title {
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
    }

    .live {
      margin-left: auto;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #22c55e;
      color: #fff;
      animation: blink 1.2s ease-in-out infinite;
    }
  }

  .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6366f1;
    animation: pulse 1.4s ease infinite;
  }

  .pipeline-track {
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    gap: 6px 4px;
  }

  .step {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 120px;
    max-width: 280px;
    padding: 8px 10px;
    border-radius: 10px;
    background: #fff;
    border: 1px solid #e2e8f0;
    transition:
      border-color 0.2s,
      box-shadow 0.2s;

    &.active {
      border-color: #818cf8;
      box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
    }

    &.done {
      opacity: 0.92;
    }
  }

  .tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    width: fit-content;
  }

  .tag-supervisor {
    background: #ede9fe;
    color: #5b21b6;
  }
  .tag-kb {
    background: #dbeafe;
    color: #1d4ed8;
  }
  .tag-code {
    background: #ffedd5;
    color: #c2410c;
  }
  .tag-worker {
    background: #d1fae5;
    color: #047857;
  }
  .tag-final {
    background: #fce7f3;
    color: #9d174d;
  }
  .tag-meta {
    background: #f1f5f9;
    color: #475569;
  }
  .tag-wait {
    background: #e2e8f0;
    color: #64748b;
  }
  .tag-default {
    background: #f1f5f9;
    color: #334155;
  }

  .detail {
    font-size: 12px;
    line-height: 1.45;
    color: #475569;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .arrow {
    align-self: center;
    color: #94a3b8;
    font-weight: 700;
    font-size: 14px;
    padding: 0 2px;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.5;
      transform: scale(1.15);
    }
  }

  @keyframes blink {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.65;
    }
  }
</style>
