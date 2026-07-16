import { App, defineAsyncComponent } from 'vue';
import Breadcrumb from './breadcrumb/index.vue';
import LoadingState from './state/LoadingState.vue';
import EmptyState from './state/EmptyState.vue';
import ErrorState from './state/ErrorState.vue';
import ZyPageEnter from './zy/ZyPageEnter.vue';
import ZyPageShell from './zy/ZyPageShell.vue';
import ZySkeleton from './zy/ZySkeleton.vue';
import ZyEmptyGuide from './zy/ZyEmptyGuide.vue';
import AiProcessTimeline from './zy/AiProcessTimeline.vue';
import MetricCountUp from './zy/MetricCountUp.vue';
import ResultReveal from './zy/ResultReveal.vue';
import SegmentTabs from './zy/SegmentTabs.vue';
import AgentStagePanel from './zy/AgentStagePanel.vue';
import ZyMediaHero from './zy/ZyMediaHero.vue';

const Chart = defineAsyncComponent(() => import('./chart/index.vue'));
const PortraitRadarChart = defineAsyncComponent(
  () => import('./zy/PortraitRadarChart.vue')
);

export default {
  install(Vue: App) {
    Vue.component('Chart', Chart);
    Vue.component('Breadcrumb', Breadcrumb);
    Vue.component('LoadingState', LoadingState);
    Vue.component('EmptyState', EmptyState);
    Vue.component('ErrorState', ErrorState);
    Vue.component('ZyPageEnter', ZyPageEnter);
    Vue.component('ZyPageShell', ZyPageShell);
    Vue.component('ZySkeleton', ZySkeleton);
    Vue.component('ZyEmptyGuide', ZyEmptyGuide);
    Vue.component('AiProcessTimeline', AiProcessTimeline);
    Vue.component('MetricCountUp', MetricCountUp);
    Vue.component('ResultReveal', ResultReveal);
    Vue.component('SegmentTabs', SegmentTabs);
    Vue.component('PortraitRadarChart', PortraitRadarChart);
    Vue.component('AgentStagePanel', AgentStagePanel);
    Vue.component('ZyMediaHero', ZyMediaHero);
  },
};
