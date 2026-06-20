import { getClassroomCourse } from '@/data/classroomCourses';
import {
  buildCourseResources,
  type CourseResourceItem,
} from '@/data/courseWorkspace';

export interface CourseResourceReference {
  file_id: string;
  file_name: string;
  name: string;
  size: number;
  scope: 'system';
  created: string;
  courseId: string;
  courseTitle: string;
  resourceId: string;
  title: string;
  type: CourseResourceItem['type'];
  chapter: string;
  sizeLabel: string;
  downloads: number;
  evidence: string[];
  prompts: string[];
}

function parseSizeLabel(sizeLabel: string) {
  const match = sizeLabel.trim().match(/^([\d.]+)\s*(KB|MB|GB|B)$/i);
  if (!match) return 0;
  const value = Number(match[1]) || 0;
  const unit = match[2].toUpperCase();
  const multiplier =
    unit === 'GB'
      ? 1024 ** 3
      : unit === 'MB'
        ? 1024 ** 2
        : unit === 'KB'
          ? 1024
          : 1;
  return Math.round(value * multiplier);
}

export function resolveCourseResourceReference(
  courseId: string,
  resourceId: string
): CourseResourceReference | null {
  if (!courseId || !resourceId) return null;
  const course = getClassroomCourse(courseId);
  if (!course) return null;
  const resources = buildCourseResources(course);
  const resource = resources.find((item) => item.id === resourceId);
  if (!resource) return null;
  const resourceIndex = Math.max(resources.findIndex((item) => item.id === resource.id), 0);
  const concepts = course.concepts.length ? course.concepts : [];
  const concept = concepts[resourceIndex % Math.max(concepts.length, 1)];
  const firstPoint = concept?.points[0] || resource.chapter;
  const fileName = `${resource.title}.${resource.type === '数据集' ? 'csv' : 'md'}`;
  return {
    file_id: resource.id,
    file_name: fileName,
    name: fileName,
    size: parseSizeLabel(resource.size),
    scope: 'system',
    created: resource.updatedAt,
    courseId: course.id,
    courseTitle: course.title,
    resourceId: resource.id,
    title: resource.title,
    type: resource.type,
    chapter: resource.chapter,
    sizeLabel: resource.size,
    downloads: resource.downloads,
    evidence: [
      `课程：${course.title}`,
      `章节：${resource.chapter}`,
      `资料类型：${resource.type}`,
      concept ? `知识主题：${concept.title}` : '',
      firstPoint ? `关键知识点：${firstPoint}` : '',
    ].filter(Boolean),
    prompts: [
      `请先概括《${resource.title}》解决的学习问题。`,
      `请指出 ${firstPoint} 在本资料中的定义、条件和常见误区。`,
      `请把 ${resource.chapter} 整理成 20 分钟复习路径。`,
    ],
  };
}
