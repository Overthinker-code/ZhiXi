<script setup lang="ts">
  import { ref } from 'vue';
  import { Message } from '@arco-design/web-vue';
  import { generateResourcePackage } from '@/api/resource-workshop';

  const STUDENT_TYPES = [
    { key: 'lecture_doc', title: '讲解文档', desc: '章节讲义与知识梳理', icon: '📄' },
    { key: 'mind_map', title: '思维导图', desc: '结构化知识脉络', icon: '🧠' },
    { key: 'practice_set', title: '练习题', desc: '分层练习与小测', icon: '✏️' },
    { key: 'reading', title: '拓展阅读', desc: '延伸阅读材料清单', icon: '📚' },
  ] as const;

  const topic = ref('数据结构与算法');
  const loading = ref(false);
  const result = ref<any>(null);

  const generate = async () => {
    loading.value = true;
    try {
      const res = await generateResourcePackage({
        subject: '计算机科学',
        topic: topic.value,
        goal: '巩固薄弱知识点',
        difficulty: 'standard',
        resource_count: 4,
      });
      result.value = {
        ...res,
        resources: (res.resources || []).filter((item: { type: string }) =>
          ['lecture_doc', 'mind_map', 'practice_set', 'reading'].includes(item.type)
        ),
      };
      Message.success('资源包生成完成');
    } catch (e: any) {
      Message.error(e?.message || '生成失败');
    } finally {
      loading.value = false;
    }
  };
</script>

<template>
  <ZyPageShell title="学习资源" subtitle="学生简化工坊：讲解文档、思维导图、练习题、拓展阅读">
    <template #actions>
      <a-input v-model="topic" placeholder="输入主题，如：SQL 事务" style="width: 220px" />
      <a-button type="primary" :loading="loading" @click="generate">生成资源包</a-button>
    </template>

    <ZyPageEnter>
      <div class="type-grid zy-stagger-child">
        <a-card v-for="t in STUDENT_TYPES" :key="t.key" class="type-card general-card" hoverable>
          <div class="type-icon">{{ t.icon }}</div>
          <h3>{{ t.title }}</h3>
          <p>{{ t.desc }}</p>
        </a-card>
      </div>

      <a-card v-if="result" title="生成结果" class="card-block general-card zy-stagger-child">
        <AgentStagePanel
          v-if="result.agent_steps?.length"
          :nodes="
            result.agent_steps.map((s: any) => ({
              key: s.agent,
              label: s.label,
              sub: s.message,
              status: s.status || 'done',
            }))
          "
        />
        <div class="resource-list">
          <div v-for="item in result.resources" :key="item.title" class="resource-item">
            <div class="resource-item__head">
              <strong>{{ item.title }}</strong>
              <a-tag size="small">{{ item.type }}</a-tag>
            </div>
            <p>{{ item.description }}</p>
          </div>
        </div>
      </a-card>
    </ZyPageEnter>
  </ZyPageShell>
</template>

<style scoped lang="less">
  .card-block {
    border-radius: var(--zy-radius-card);
  }

  .type-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }

  .type-card {
    border-radius: var(--zy-radius-card);
    text-align: center;

    .type-icon {
      font-size: 28px;
      margin-bottom: 8px;
    }

    h3 {
      margin: 0 0 6px;
      font-size: var(--zy-text-sm);
      color: var(--zy-color-text-primary);
    }

    p {
      margin: 0;
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-xs);
    }
  }

  .resource-item {
    padding: 12px 0;
    border-bottom: 1px solid #f1f5f9;

    p {
      margin: 6px 0 0;
      color: var(--zy-color-text-secondary);
      font-size: var(--zy-text-sm);
    }
  }

  .resource-item__head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  @media (max-width: 900px) {
    .type-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
