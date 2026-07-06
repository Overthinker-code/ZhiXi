<script setup lang="ts">
  defineProps<{
    artifacts: Array<Record<string, any>>;
    packageId?: string;
  }>();

  const labelMap: Record<string, string> = {
    lecture_markdown: '讲义',
    lecture_note: '讲义',
    practice_markdown: '练习题',
    quiz: '练习题',
    mind_map: '思维导图',
    reading_list: '拓展阅读',
    reading: '拓展阅读',
    case_project: '代码案例',
    code_case: '代码案例',
    video_script: '视频脚本',
  };
</script>

<template>
  <section v-if="artifacts.length" class="artifact-cards">
    <header>
      <span>资源包</span>
      <strong v-if="packageId">{{ packageId }}</strong>
    </header>
    <div class="artifact-cards__grid">
      <a
        v-for="item in artifacts"
        :key="item.file_name || item.title || item.kind"
        class="artifact-card"
        :href="item.download_url"
        target="_blank"
        rel="noopener"
      >
        <span>{{ labelMap[item.kind] || item.kind || '资源' }}</span>
        <strong>{{ item.title || item.file_name || '生成资源' }}</strong>
        <p>{{ item.preview || '已生成，可进入资料库继续核验。' }}</p>
      </a>
    </div>
  </section>
</template>

<style scoped lang="scss">
  .artifact-cards {
    margin-top: 14px;

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #667085;
      font-size: 13px;

      strong {
        color: #4f46e5;
        font-weight: 700;
      }
    }
  }

  .artifact-cards__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 8px;
  }

  .artifact-card {
    min-height: 96px;
    padding: 12px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    background: #fff;
    text-decoration: none;
    transition: box-shadow 0.18s ease, transform 0.18s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
    }

    span {
      color: #6366f1;
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      display: block;
      margin-top: 5px;
      color: #101828;
      font-size: 14px;
    }

    p {
      display: -webkit-box;
      margin: 6px 0 0;
      overflow: hidden;
      color: #667085;
      font-size: 12px;
      line-height: 1.5;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }
  }

  @media (max-width: 760px) {
    .artifact-cards__grid {
      grid-template-columns: 1fr;
    }
  }
</style>
