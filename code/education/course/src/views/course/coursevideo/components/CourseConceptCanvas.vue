<template>
  <div class="concept-canvas" :class="`concept-canvas--${mode}`">
    <svg
      ref="svgRef"
      class="concept-svg"
      viewBox="0 0 760 420"
      preserveAspectRatio="xMidYMid meet"
      xmlns="http://www.w3.org/2000/svg"
      :aria-label="`${title}${mode === 'mind' ? '思维导图' : '知识图谱'}`"
      :style="{ transform: `scale(${zoom})` }"
    >
      <rect width="760" height="420" rx="22" fill="#fbfcff" />
      <g class="grid-dots">
        <circle
          v-for="dot in dots"
          :key="`${dot.x}-${dot.y}`"
          :cx="dot.x"
          :cy="dot.y"
          r="1.2"
        />
      </g>

      <g class="edges">
        <template v-for="(concept, index) in concepts" :key="concept.title">
          <path
            :d="branchLayouts[index].path"
            :stroke="branchColors[index]"
            class="branch-edge"
          />
          <path
            v-for="(point, pointIndex) in concept.points"
            :key="point"
            :d="leafPath(index, pointIndex)"
            :stroke="branchColors[index]"
            class="leaf-edge"
          />
        </template>
      </g>

      <g
        class="center-node node-button"
        role="button"
        tabindex="0"
        @click.stop="emitNode(title, $event)"
        @keydown.enter.stop="emitNode(title, $event)"
      >
        <rect x="298" y="178" width="164" height="64" rx="16" :fill="accent" />
        <text x="380" y="207" text-anchor="middle">{{ shortTitle }}</text>
        <text x="380" y="226" text-anchor="middle" class="center-subtitle">
          {{ mode === 'mind' ? '核心知识框架' : '概念关系网络' }}
        </text>
      </g>

      <template v-for="(concept, index) in concepts" :key="`${concept.title}-nodes`">
        <g
          class="branch-node node-button"
          role="button"
          tabindex="0"
          @click.stop="emitNode(concept.title, $event)"
          @keydown.enter.stop="emitNode(concept.title, $event)"
        >
          <rect
            :x="branchLayouts[index].x"
            :y="branchLayouts[index].y"
            width="126"
            height="44"
            rx="11"
            :fill="branchFills[index]"
            :stroke="branchColors[index]"
          />
          <circle
            :cx="branchLayouts[index].x + 15"
            :cy="branchLayouts[index].y + 22"
            r="4"
            :fill="branchColors[index]"
          />
          <text
            :x="branchLayouts[index].x + 69"
            :y="branchLayouts[index].y + 27"
            text-anchor="middle"
            :fill="branchTextColors[index]"
          >
            {{ concept.title }}
          </text>
        </g>

        <g
          v-for="(point, pointIndex) in concept.points"
          :key="point"
          class="leaf-node node-button"
          role="button"
          tabindex="0"
          @click.stop="emitNode(point, $event)"
          @keydown.enter.stop="emitNode(point, $event)"
        >
          <rect
            :x="leafPosition(index, pointIndex).x"
            :y="leafPosition(index, pointIndex).y"
            width="96"
            height="29"
            rx="8"
            fill="#fff"
            :stroke="branchColors[index]"
          />
          <text
            :x="leafPosition(index, pointIndex).x + 48"
            :y="leafPosition(index, pointIndex).y + 19"
            text-anchor="middle"
          >
            {{ shortLabel(point, 8) }}
          </text>
        </g>
      </template>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ClassroomConcept } from '@/data/classroomCourses';

const props = withDefaults(
  defineProps<{
    title: string;
    shortTitle: string;
    concepts: ClassroomConcept[];
    accent?: string;
    mode?: 'mind' | 'graph';
    zoom?: number;
  }>(),
  {
    accent: '#596bfa',
    mode: 'mind',
    zoom: 1,
  }
);

const emit = defineEmits<{
  nodePrompt: [payload: { text: string; rect: DOMRect }];
}>();

const svgRef = ref<SVGSVGElement | null>(null);
const concepts = computed(() =>
  props.concepts.slice(0, 4).map((concept) => ({
    ...concept,
    points: [
      ...concept.points,
      ...(concept.checks || []).map((item) => item.replace(/^我能否/, '能否')),
    ].slice(0, 5),
  }))
);
const dots = Array.from({ length: 13 * 7 }, (_, index) => ({
  x: 20 + (index % 13) * 60,
  y: 22 + Math.floor(index / 13) * 62,
}));

const branchLayouts = [
  { x: 116, y: 72, path: 'M 306 188 C 260 150, 242 110, 242 94' },
  { x: 518, y: 72, path: 'M 454 188 C 500 150, 518 110, 518 94' },
  { x: 116, y: 304, path: 'M 306 232 C 260 270, 242 304, 242 326' },
  { x: 518, y: 304, path: 'M 454 232 C 500 270, 518 304, 518 326' },
];

const branchColors = ['#32a776', '#3d8ed0', '#9a65d3', '#e28b42'];
const branchFills = ['#eaf8f1', '#eaf5fd', '#f5effc', '#fff4e9'];
const branchTextColors = ['#176b4a', '#246b9b', '#70449e', '#9a5b25'];

function leafPosition(branchIndex: number, pointIndex: number) {
  const isLeft = branchIndex === 0 || branchIndex === 2;
  const isTop = branchIndex < 2;
  const x = isLeft ? 8 + Math.min(pointIndex, 2) * 8 : 656 - Math.min(pointIndex, 2) * 8;
  const yBase = isTop ? 16 : 374;
  return {
    x,
    y: yBase + pointIndex * (isTop ? 31 : -31),
  };
}

function shortLabel(value: string, limit = 9) {
  const text = String(value || '').trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function leafPath(branchIndex: number, pointIndex: number) {
  const branch = branchLayouts[branchIndex];
  const leaf = leafPosition(branchIndex, pointIndex);
  const startX = branchIndex === 0 || branchIndex === 2 ? branch.x : branch.x + 126;
  const startY = branch.y + 22;
  const endX = branchIndex === 0 || branchIndex === 2 ? leaf.x + 96 : leaf.x;
  const endY = leaf.y + 14.5;
  const midX = (startX + endX) / 2;
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

function emitNode(text: string, event: Event) {
  const element = event.currentTarget as SVGGraphicsElement | null;
  if (!element) return;
  emit('nodePrompt', { text, rect: element.getBoundingClientRect() });
}

function exportSvg(filename: string) {
  if (!svgRef.value) return;
  const source = new XMLSerializer().serializeToString(svgRef.value);
  const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

defineExpose({ exportSvg });
</script>

<style scoped lang="less">
.concept-canvas {
  width: 100%;
  height: 100%;
  overflow: auto;
  background: #fbfcff;
  scrollbar-width: thin;
}

.concept-svg {
  display: block;
  width: 100%;
  height: 100%;
  min-width: 620px;
  transform-origin: center;
  transition: transform 180ms ease;
}

.grid-dots {
  fill: #dce3f0;
  opacity: .58;
}

.edges {
  fill: none;
  stroke-linecap: round;
}

.branch-edge {
  stroke-width: 2.4;
  opacity: .78;
}

.leaf-edge {
  stroke-width: 1.25;
  opacity: .48;
  stroke-dasharray: 4 4;
}

.node-button {
  cursor: pointer;
  outline: none;

  rect {
    transition: filter 160ms ease, transform 160ms ease;
    transform-box: fill-box;
    transform-origin: center;
  }

  &:hover rect,
  &:focus-visible rect {
    filter: drop-shadow(0 7px 10px rgba(37, 50, 88, .16));
    transform: translateY(-2px);
  }
}

.center-node {
  text {
    fill: #fff;
    font-size: 16px;
    font-weight: 700;
  }

  .center-subtitle {
    fill: rgba(255, 255, 255, .72);
    font-size: 9px;
    font-weight: 500;
  }
}

.branch-node text {
  font-size: 12px;
  font-weight: 650;
}

.leaf-node {
  text {
    fill: #66738a;
    font-size: 9.5px;
  }

  rect {
    opacity: .96;
  }
}

.concept-canvas--graph {
  .branch-edge {
    stroke-dasharray: 8 6;
  }

  .leaf-edge {
    stroke-dasharray: 2 5;
  }
}
</style>
