import setupMock, { successResponseWrap } from '@/utils/setup-mock';
import Mock from 'mockjs';

setupMock({
  setup() {
    // GET /education/courses - 返回 12 条假课程
    Mock.mock(new RegExp('/education/courses'), 'get', () => {
      const courses = Array.from({ length: 12 }, (_, i) => {
        const id = `course-${i + 1}`;
        return {
          id,
          name: `课程 ${i + 1}：${['Python 程序设计', '数据结构', '机器学习基础', 'Web 前端开发', '数据库原理', '操作系统', '计算机网络', '软件工程', '人工智能导论', '深度学习实践', '云计算技术', '大数据处理'][i]}`,
          description: `这是第 ${i + 1} 门课程的描述信息，涵盖了该领域的核心知识点和实践技能。`,
          course_type: ['programming', 'theory', 'ai', 'web', 'database', 'system', 'network', 'engineering', 'ai', 'practice', 'cloud', 'bigdata'][i],
          identifier: `CS${1001 + i}`,
          ud_id: `ud-${(i % 3) + 1}`,
          created_at: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date().toISOString(),
        };
      });
      return successResponseWrap({
        data: courses,
        count: courses.length,
      });
    });

    // GET /education/courses/:id - 返回单个课程详情
    Mock.mock(new RegExp('/education/courses/[^/]+$'), 'get', (params: any) => {
      const url = params.url || '';
      const match = url.match(/\/education\/courses\/([^/?]+)/);
      const id = match ? match[1] : 'course-1';
      const index = parseInt(id.split('-')[1] || '1', 10) - 1;
      const i = Math.max(0, Math.min(index, 11));

      return successResponseWrap({
        id,
        name: `课程 ${i + 1}：${['Python 程序设计', '数据结构', '机器学习基础', 'Web 前端开发', '数据库原理', '操作系统', '计算机网络', '软件工程', '人工智能导论', '深度学习实践', '云计算技术', '大数据处理'][i]}`,
        description: `这是第 ${i + 1} 门课程的详细描述，涵盖了该领域的核心知识点和实践技能。适合有一定基础的学生学习。`,
        course_type: ['programming', 'theory', 'ai', 'web', 'database', 'system', 'network', 'engineering', 'ai', 'practice', 'cloud', 'bigdata'][i],
        identifier: `CS${1001 + i}`,
        ud_id: `ud-${(i % 3) + 1}`,
        created_at: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date().toISOString(),
      });
    });

    // GET /education/tc - 返回 5 个教学班
    Mock.mock(new RegExp('/education/tc'), 'get', () => {
      const teachers = [
        { id: 'teacher-1', name: '张教授' },
        { id: 'teacher-2', name: '李副教授' },
        { id: 'teacher-3', name: '王讲师' },
        { id: 'teacher-4', name: '赵教授' },
        { id: 'teacher-5', name: '陈副教授' },
      ];

      const classes = Array.from({ length: 5 }, (_, i) => ({
        id: `tc-${i + 1}`,
        name: `2024 春季教学班 ${String.fromCharCode(65 + i)}`,
        course_id: `course-${(i % 4) + 1}`,
        lecturer_id: teachers[i].id,
        created_at: new Date(Date.now() - Math.random() * 180 * 24 * 60 * 60 * 1000).toISOString(),
        updated_at: new Date().toISOString(),
      }));

      return successResponseWrap({
        data: classes,
        count: classes.length,
      });
    });

    // GET /education/courses/:id/resources/analysis - 返回空数组 []
    Mock.mock(new RegExp('/education/courses/[^/]+/resources/analysis$'), 'get', () => {
      return successResponseWrap([]);
    });
  },
});
