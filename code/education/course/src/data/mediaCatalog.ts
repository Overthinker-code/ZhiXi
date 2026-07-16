/**
 * 真实教育场景图片资源（Unsplash，本地缓存）
 */
import heroStudents from '@/assets/media/hero-students.jpg';
import heroLibrary from '@/assets/media/hero-library.jpg';
import heroOnlineLearning from '@/assets/media/hero-online-learning.jpg';
import heroCoding from '@/assets/media/hero-coding.jpg';
import heroTeamwork from '@/assets/media/hero-teamwork.jpg';
import bannerLecture from '@/assets/media/banner-lecture.jpg';
import bannerAiClassroom from '@/assets/media/banner-ai-classroom.jpg';
import featureStudy from '@/assets/media/feature-study.jpg';

export const landingHeroPhotos = {
  primary: heroStudents,
  secondary: heroLibrary,
  accent: heroCoding,
  teamwork: heroTeamwork,
};

export const landingBanners = [
  {
    id: 1,
    image: bannerAiClassroom,
    tag: '智慧课堂',
    title: 'AI 赋能的沉浸式学习体验',
    desc: '大模型伴学、实时行为分析与个性化路径，让每一堂课都可感知、可追踪。',
  },
  {
    id: 2,
    image: bannerLecture,
    tag: '优质课程',
    title: '1200+ 精品课程资源等你探索',
    desc: '覆盖经管、计算机、人工智能等学科，支持视频、文档与 RAG 联合检索。',
  },
  {
    id: 3,
    image: heroOnlineLearning,
    tag: '随时随地',
    title: '多端同步 · 碎片化学习不断档',
    desc: '手机、平板、PC 一致体验，学习进度与 AI 对话上下文实时同步。',
  },
];

export const featureThumbnails = {
  ai: heroOnlineLearning,
  path: featureStudy,
  behavior: bannerLecture,
  resource: heroLibrary,
  modes: heroCoding,
  alert: heroTeamwork,
};

export default landingHeroPhotos;
