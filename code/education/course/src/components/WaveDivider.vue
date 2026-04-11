<!--
  WaveDivider.vue — 智屿品牌波浪 SVG 分隔线
  可复用组件，用于首页 Hero 区、页面区块分隔
  规格：designup.md §6.2
  
  使用示例：
    <WaveDivider />                    // 默认浅绿
    <WaveDivider fill="#FFFFFF" />     // 白色
    <WaveDivider fill="#F0FDF6" :flip="true" />  // 翻转
-->
<template>
  <div class="wave-divider" :class="{ 'wave-divider--flip': flip }">
    <svg
      viewBox="0 0 1440 60"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="none"
    >
      <path
        d="M0,30 C360,60 1080,0 1440,30 L1440,60 L0,60 Z"
        :fill="fill || '#F0FDF6'"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  fill?: string;
  flip?: boolean;
}>(), {
  fill: '#F0FDF6',
  flip: false,
});
</script>

<style scoped>
.wave-divider {
  line-height: 0;
  overflow: hidden;
}

.wave-divider svg {
  display: block;
  width: 100%;
  height: auto;
}

/* 翻转波浪方向 */
.wave-divider--flip svg {
  transform: scaleY(-1);
}
</style>
