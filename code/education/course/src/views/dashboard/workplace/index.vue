<template>
  <div class="container">
    <div class="left-side">
      <div class="panel">
        <Banner />
        <AdBanner />
        <DataPanel />
        <ContentChart />
      </div>
      <a-grid :cols="24" :col-gap="16" :row-gap="16" style="margin-top: 16px">
        <a-grid-item
          :span="{ xs: 24, sm: 24, md: 24, lg: 12, xl: 12, xxl: 12 }"
        >
          <PopularContent />
        </a-grid-item>
        <a-grid-item
          :span="{ xs: 24, sm: 24, md: 24, lg: 12, xl: 12, xxl: 12 }"
        >
          <CategoriesPercent />
        </a-grid-item>
      </a-grid>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import Banner from './components/banner.vue';
  import AdBanner from './components/ad-banner.vue';
  import DataPanel from './components/data-panel.vue';
  import ContentChart from './components/content-chart.vue';
  import PopularContent from './components/popular-content.vue';
  import CategoriesPercent from './components/categories-percent.vue';
</script>

<script lang="ts">
  export default {
    name: 'Dashboard', // If you want the include property of keep-alive to take effect, you must name the component
  };
</script>

<style lang="less" scoped>
  /**
   * 智屿教师 Dashboard 品牌化
   * 文档：designup.md §5
   */
  .container {
    background:
      radial-gradient(
        circle at 0% 0%,
        rgba(99, 102, 241, 0.12),
        rgba(99, 102, 241, 0) 42%
      ),
      radial-gradient(
        circle at 100% 20%,
        rgba(14, 165, 233, 0.08),
        rgba(14, 165, 233, 0) 40%
      ),
      linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    padding: 16px 20px;
    padding-bottom: 0;
    display: flex;
  }

  .left-side {
    flex: 1;
    overflow: auto;
  }

  .right-side {
    width: 280px;
    margin-left: 16px;
  }

  .panel {
    background-color: var(--zy-bg-card, #FFFFFF);
    border-radius: var(--zy-radius-card, 16px);
    overflow: auto;
    /* 品牌绿光晕阴影 */
    box-shadow: var(--zy-shadow-card, 0 8px 32px rgba(31, 38, 135, 0.07));
    border: 1px solid rgba(99, 102, 241, 0.1);
  }

  :deep(.panel-border) {
    margin-bottom: 0;
    border-bottom: 1px solid rgb(var(--gray-2));
  }

  .moduler-wrap {
    border-radius: 4px;
    background-color: var(--color-bg-2);

    :deep(.text) {
      font-size: 12px;
      text-align: center;
      color: rgb(var(--gray-8));
    }

    :deep(.wrapper) {
      margin-bottom: 8px;
      text-align: center;
      cursor: pointer;

      &:last-child {
        .text {
          margin-bottom: 0;
        }
      }

      &:hover {
        .icon {
          color: rgb(var(--arcoblue-6));
          background-color: #e8f3ff;
        }

        .text {
          color: rgb(var(--arcoblue-6));
        }
      }
    }

    :deep(.icon) {
      display: inline-block;
      width: 32px;
      height: 32px;
      margin-bottom: 4px;
      color: rgb(var(--dark-gray-1));
      line-height: 32px;
      font-size: 16px;
      text-align: center;
      background-color: rgb(var(--gray-1));
      border-radius: 4px;
    }
  }
</style>

<style lang="less" scoped>
  // responsive
  .mobile {
    .container {
      display: block;
    }

    .right-side {
      // display: none;
      width: 100%;
      margin-left: 0;
      margin-top: 16px;
    }
  }
</style>
