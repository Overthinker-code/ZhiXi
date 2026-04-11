import axios from 'axios';

// 行为分析相关接口

/**
 * 检测到人
 */
export interface Person {
  id: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  behavior: string;
  confidence: number;
  score: number;
  color: string;
  reason: string;
}

/**
 * 行为检测结果
 */
export interface BehaviorDetection {
  behavior: string;
  confidence: number;
  description: string;
  score_contribution: number;
}

/**
 * 图片分析结果
 */
export interface ImageAnalysisResult {
  status: string;
  behaviors: BehaviorDetection[];
  persons: Person[];
  overall_score: number;
  learning_status: string;
  timestamp: string;
  image_width?: number;
  image_height?: number;
}

/**
 * 帧分析结果
 */
export interface FrameAnalysis {
  timestamp: number;
  frame_number: number;
  behaviors: BehaviorDetection[];
  score: number;
}

/**
 * 视频信息
 */
export interface VideoInfo {
  total_frames: number;
  fps: number;
  duration: number;
  frames_analyzed: number;
}

/**
 * 行为统计
 */
export interface BehaviorStatistics {
  count: number;
  duration: number;
  percentage: number;
}

/**
 * 视频分析汇总
 */
export interface VideoSummary {
  average_score: number;
  overall_status: string;
  behavior_statistics: Record<string, BehaviorStatistics>;
  key_moments: Array<{
    timestamp: number;
    behaviors: string[];
    score: number;
  }>;
}

/**
 * 视频分析结果
 */
export interface VideoAnalysisResult {
  status: string;
  frame_analyses: FrameAnalysis[];
  summary: VideoSummary;
  video_info: VideoInfo;
  persons: Person[];  // 第一帧检测到的人员数据（用于预览）
}

/**
 * 分析记录
 */
export interface AnalysisRecord {
  id: string;
  course_id: string;
  timestamp: string;
  duration: number;
  average_score: number;
  overall_status: string;
  behavior_statistics: Record<string, BehaviorStatistics>;
  key_moments?: Array<{
    timestamp: number;
    behaviors: string[];
    score: number;
  }>;
}

/**
 * 行为定义
 */
export interface BehaviorDefinition {
  id: number;
  name: string;
  score: number;
  description: string;
  color: string;
}

/**
 * 分数范围
 */
export interface ScoreRange {
  min: number;
  max: number;
  status: string;
  color: string;
}

/**
 * 行为定义响应
 */
export interface BehaviorDefinitionsResponse {
  behaviors: BehaviorDefinition[];
  score_ranges: ScoreRange[];
}

/**
 * 课程统计
 */
export interface CourseStatistics {
  course_id: string;
  analysis_count: number;
  average_score: number;
  behavior_distribution: Record<string, { count: number; duration: number }>;
  recent_records: AnalysisRecord[];
  message?: string;
}

/**
 * 实时分析会话
 */
export interface RealtimeSession {
  status: string;
  session_id: string;
  message: string;
  camera_id?: string;
  course_id: string;
}

/**
 * 分析图片中的行为
 * @param file 图片文件
 */
export function analyzeImage(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return axios.post<ImageAnalysisResult>(
    '/api/behavior/analyze/image',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
}

/**
 * 分析视频中的行为
 * @param file 视频文件
 * @param courseId 可选，关联的课程ID
 * @param sampleInterval 采样间隔（帧数），默认30帧
 */
export function analyzeVideo(
  file: File,
  courseId?: string,
  sampleInterval = 30
) {
  const formData = new FormData();
  formData.append('file', file);
  if (courseId) {
    formData.append('course_id', courseId);
  }
  formData.append('sample_interval', sampleInterval.toString());
  return axios.post<VideoAnalysisResult>(
    '/api/behavior/analyze/video',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
}

/**
 * 获取分析记录列表
 * @param courseId 可选，筛选特定课程
 * @param skip 分页偏移
 * @param limit 分页限制
 */
export function getAnalysisRecords(courseId?: string, skip = 0, limit = 100) {
  const params: Record<string, string | number> = { skip, limit };
  if (courseId) {
    params.course_id = courseId;
  }
  return axios.get<{ data: AnalysisRecord[]; total: number }>(
    '/api/behavior/records',
    {
      params,
    }
  );
}

/**
 * 获取单个分析记录详情
 * @param recordId 记录ID
 */
export function getAnalysisRecordDetail(recordId: string) {
  return axios.get<AnalysisRecord>(`/api/behavior/records/${recordId}`);
}

/**
 * 获取课程行为统计
 * @param courseId 课程ID
 */
export function getCourseStatistics(courseId: string) {
  return axios.get<CourseStatistics>(`/api/behavior/statistics/${courseId}`);
}

/**
 * 启动实时行为分析
 * @param courseId 课程ID
 * @param cameraId 可选，摄像头ID
 */
export function startRealtimeAnalysis(courseId: string, cameraId?: string) {
  const formData = new FormData();
  formData.append('course_id', courseId);
  if (cameraId) {
    formData.append('camera_id', cameraId);
  }
  return axios.post<RealtimeSession>('/api/behavior/realtime/start', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

/**
 * 获取行为定义列表
 */
export function getBehaviorDefinitions() {
  return axios.get<BehaviorDefinitionsResponse>(
    '/api/behavior/behaviors/definitions'
  );
}
