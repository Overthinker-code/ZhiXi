<script setup lang="ts">
  import { computed, ref } from 'vue';

  type Conversation = {
    id: string;
    title: string;
    createdAt?: number;
  };

  const props = defineProps<{
    conversations: Conversation[];
    currentId: string;
    collapsed: boolean;
  }>();

  const emit = defineEmits<{
    (e: 'new-chat'): void;
    (e: 'switch', id: string): void;
    (e: 'delete', id: string): void;
    (e: 'clear-all'): void;
    (e: 'toggle'): void;
  }>();

  const keyword = ref('');

  const dateGroup = (timestamp?: number) => {
    if (!timestamp) return '更早';
    const now = new Date();
    const date = new Date(timestamp);
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const target = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    if (target === today) return '今天';
    if (target === today - 24 * 60 * 60 * 1000) return '昨天';
    return '更早';
  };

  const grouped = computed(() => {
    const map: Record<string, Conversation[]> = { 今天: [], 昨天: [], 更早: [] };
    props.conversations
      .filter((item) =>
        item.title.toLowerCase().includes(keyword.value.trim().toLowerCase())
      )
      .forEach((item) => {
        map[dateGroup(item.createdAt)].push(item);
      });
    return map;
  });
</script>

<template>
  <aside :class="['chat-sidebar', { collapsed }]">
    <div class="sidebar-top">
      <button type="button" class="collapse-btn" @click="emit('toggle')">
        {{ collapsed ? '›' : '‹' }}
      </button>
      <button v-if="!collapsed" type="button" class="new-chat" @click="emit('new-chat')">
        新建对话
      </button>
    </div>
    <template v-if="!collapsed">
      <div class="history-search-row">
        <input v-model="keyword" class="history-search" placeholder="搜索历史" />
        <button
          type="button"
          class="clear-all-button"
          :disabled="!conversations.length"
          title="一键清除全部对话记录"
          @click="emit('clear-all')"
        >
          清除
        </button>
      </div>
      <div class="history-tools">
        <span>对话记录</span>
      </div>
      <section v-for="(items, group) in grouped" :key="group" class="history-group">
        <h3 v-if="items.length">{{ group }}</h3>
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          :class="['history-item', { active: item.id === currentId }]"
          @click="emit('switch', item.id)"
        >
          <span>{{ item.title || '新对话' }}</span>
          <small @click.stop="emit('delete', item.id)">删除</small>
        </button>
      </section>
    </template>
    <button v-else type="button" class="collapsed-new" @click="emit('new-chat')">+</button>
  </aside>
</template>

<style scoped lang="scss">
  .chat-sidebar {
    width: 280px;
    min-width: 280px;
    height: 100%;
    padding: 14px 12px;
    border-right: 1px solid rgba(15, 23, 42, 0.08);
    background: #f7f9ff;
    transition: width 0.18s ease, min-width 0.18s ease;

    &.collapsed {
      width: 56px;
      min-width: 56px;
      padding-inline: 8px;
    }
  }

  .sidebar-top {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 12px;
  }

  .collapse-btn,
  .collapsed-new,
  .new-chat {
    height: 38px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 14px;
    background: #fff;
    color: #344054;
    cursor: pointer;
  }

  .collapse-btn,
  .collapsed-new {
    width: 38px;
    font-size: 22px;
  }

  .new-chat {
    flex: 1;
    color: #4f46e5;
    font-weight: 700;
  }

  .history-search-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .history-search {
    width: 100%;
    height: 38px;
    padding: 0 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 14px;
    outline: none;
    color: #101828;
    background: #fff;

    &:focus {
      border-color: #6366f1;
      box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
    }
  }

  .clear-all-button {
    height: 38px;
    padding: 0 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 14px;
    color: #667085;
    background: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;

    &:hover:not(:disabled) {
      color: #4f46e5;
      border-color: rgba(99, 102, 241, 0.3);
      background: #f7f9ff;
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.45;
    }
  }

  .history-tools {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 14px 4px 0;
    color: #98a2b3;
    font-size: 12px;
    font-weight: 700;

  }

  .history-group {
    margin-top: 14px;

    h3 {
      margin: 0 0 8px;
      padding-inline: 8px;
      color: #98a2b3;
      font-size: 12px;
      font-weight: 700;
    }
  }

  .history-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    min-height: 38px;
    padding: 0 8px 0 10px;
    border: 0;
    border-radius: 12px;
    color: #344054;
    background: transparent;
    text-align: left;
    cursor: pointer;

    &:hover,
    &.active {
      background: #eef2ff;
      color: #4f46e5;
    }

    span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      color: #98a2b3;
      opacity: 0;
    }

    &:hover small {
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chat-sidebar {
      transition: none;
    }
  }
</style>
