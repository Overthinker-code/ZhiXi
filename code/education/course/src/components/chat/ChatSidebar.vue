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
    (e: 'newChat'): void;
    (e: 'switch', id: string): void;
    (e: 'delete', id: string): void;
    (e: 'clearAll'): void;
    (e: 'toggle'): void;
  }>();

  const keyword = ref('');
  const visibleLimit = ref(12);

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

  const filteredConversations = computed(() =>
    props.conversations.filter((item) =>
      item.title.toLowerCase().includes(keyword.value.trim().toLowerCase())
    )
  );
  const visibleConversations = computed(() => {
    const currentIndex = filteredConversations.value.findIndex(
      (item) => item.id === props.currentId
    );
    const limit = Math.max(visibleLimit.value, currentIndex + 1);
    return filteredConversations.value.slice(0, limit);
  });
  const hasMore = computed(
    () => visibleConversations.value.length < filteredConversations.value.length
  );
  const grouped = computed(() => {
    const map: Record<string, Conversation[]> = { 今天: [], 昨天: [], 更早: [] };
    visibleConversations.value.forEach((item) => {
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
      <button v-if="!collapsed" type="button" class="new-chat" @click="emit('newChat')">
        新建对话
      </button>
    </div>
    <template v-if="!collapsed">
      <div class="history-search-row">
        <input
          v-model="keyword"
          class="history-search"
          aria-label="搜索对话记录"
          placeholder="搜索历史"
        />
        <button
          type="button"
          class="clear-all-button"
          :disabled="!conversations.length"
          title="一键清除全部对话记录"
          @click="emit('clearAll')"
        >
          清除
        </button>
      </div>
      <div class="history-tools">
        <span>对话记录</span>
        <small>{{ visibleConversations.length }}/{{ filteredConversations.length }}</small>
      </div>
      <section v-for="(items, group) in grouped" :key="group" class="history-group">
        <h3 v-if="items.length">{{ group }}</h3>
        <div
          v-for="item in items"
          :key="item.id"
          :class="['history-row', { active: item.id === currentId }]"
        >
          <button type="button" class="history-item" @click="emit('switch', item.id)">
            <span>{{ item.title || '新对话' }}</span>
          </button>
          <button
            type="button"
            class="history-delete"
            :aria-label="`删除对话：${item.title || '新对话'}`"
            @click="emit('delete', item.id)"
          >删除</button>
        </div>
      </section>
      <button
        v-if="hasMore"
        type="button"
        class="show-more"
        @click="visibleLimit += 12"
      >显示更多</button>
    </template>
    <button v-else type="button" class="collapsed-new" @click="emit('newChat')">+</button>
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
    outline: none !important;
    color: #101828;
    background: #fff;

    &:focus {
      border-color: #94a3b8;
      outline: none !important;
      box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
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
    color: #5b6575;
    font-size: 12px;
    font-weight: 700;

    small {
      font-size: 11px;
      font-weight: 600;
    }
  }

  .history-group {
    margin-top: 14px;

    h3 {
      margin: 0 0 8px;
      padding-inline: 8px;
      color: #5b6575;
      font-size: 12px;
      font-weight: 700;
    }
  }

  .history-row {
    display: flex;
    align-items: center;
    width: 100%;
    min-height: 38px;
    border-radius: 12px;

    &:hover,
    &.active {
      background: #eef2ff;
      color: #4f46e5;
    }

    &:focus-within {
      box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1);
    }
  }

  .history-item {
    flex: 1;
    min-width: 0;
    height: 38px;
    padding: 0 8px 0 10px;
    border: 0;
    color: inherit;
    background: transparent;
    text-align: left;
    cursor: pointer;

    span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .history-delete {
    width: 42px;
    height: 30px;
    border: 0;
    color: #5b6575;
    background: transparent;
    font-size: 11px;
    opacity: 0;
    cursor: pointer;
  }

  .history-row:hover .history-delete,
  .history-row:focus-within .history-delete {
    opacity: 1;
  }

  .show-more {
    width: 100%;
    height: 34px;
    margin-top: 12px;
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 12px;
    color: #4f46e5;
    background: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  @media (prefers-reduced-motion: reduce) {
    .chat-sidebar {
      transition: none;
    }
  }
</style>
