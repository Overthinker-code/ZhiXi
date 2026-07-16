<script setup lang="ts">
  import { computed } from 'vue';

  const props = withDefaults(
    defineProps<{
      title: string;
      subtitle?: string;
      image?: string;
      overlay?: 'light' | 'dark';
      height?: string;
    }>(),
    {
      subtitle: '',
      overlay: 'dark',
      height: '220px',
    }
  );

  const heroStyle = computed(() => {
    if (!props.image) {
      return {
        minHeight: props.height,
        background:
          'linear-gradient(135deg, rgba(22, 93, 255, 0.12) 0%, rgba(99, 102, 241, 0.08) 45%, rgba(247, 248, 250, 1) 100%)',
      };
    }
    return {
      minHeight: props.height,
      backgroundImage: `url(${props.image})`,
    };
  });
</script>

<template>
  <section class="zy-media-hero" :style="heroStyle">
    <div class="zy-media-hero__overlay" :class="`zy-media-hero__overlay--${overlay}`" />
    <div class="zy-media-hero__content zy-stagger-child">
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
      <slot />
    </div>
  </section>
</template>

<style scoped lang="less">
  .zy-media-hero {
    position: relative;
    border-radius: 16px;
    overflow: hidden;
    background-size: cover;
    background-position: center;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  }

  .zy-media-hero__overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;

    &--dark {
      background: linear-gradient(
        120deg,
        rgba(15, 23, 42, 0.72) 0%,
        rgba(15, 23, 42, 0.35) 55%,
        rgba(15, 23, 42, 0.15) 100%
      );
    }

    &--light {
      background: linear-gradient(
        180deg,
        rgba(255, 255, 255, 0.08) 0%,
        rgba(255, 255, 255, 0.72) 100%
      );
    }
  }

  .zy-media-hero__content {
    position: relative;
    z-index: 1;
    padding: 28px 32px;
    color: #fff;

    h1 {
      margin: 0 0 8px;
      font-size: clamp(24px, 3vw, 32px);
      font-weight: 700;
      letter-spacing: 0.02em;
    }

    p {
      margin: 0;
      max-width: 640px;
      font-size: 14px;
      line-height: 1.6;
      opacity: 0.92;
    }
  }
</style>
