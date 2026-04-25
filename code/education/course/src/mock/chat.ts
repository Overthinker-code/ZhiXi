import setupMock, { successResponseWrap } from '@/utils/setup-mock';
import Mock from 'mockjs';

setupMock({
  setup() {
    // GET /rag/files - 返回 3 个假文件
    Mock.mock(new RegExp('/rag/files'), 'get', () => {
      return successResponseWrap({
        files: [
          {
            file_id: 'file-1',
            name: '课程大纲.pdf',
            size: 1024 * 1024 * 2.5,
            created: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
            scope: 'system',
            owner_id: null,
            can_manage: false,
          },
          {
            file_id: 'file-2',
            name: '教学PPT.zip',
            size: 1024 * 1024 * 15.8,
            created: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
            scope: 'personal',
            owner_id: 'user-1',
            can_manage: true,
          },
          {
            file_id: 'file-3',
            name: '参考资料.docx',
            size: 1024 * 512,
            created: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
            scope: 'personal',
            owner_id: 'user-1',
            can_manage: true,
          },
        ],
      });
    });

    // GET /api/chat/settings - 返回默认设置对象
    Mock.mock(new RegExp('/api/chat/settings'), 'get', () => {
      return successResponseWrap({
        provider: 'openai',
        model: 'gpt-4',
        rag_k_options: [3, 4, 5],
        rag_k_default: 4,
        strict_mode_default: false,
        default_prompt_key: 'default',
        prompt_options: [
          {
            key: 'default',
            label: '默认助手',
            description: '通用的 AI 助手，可以回答各类问题',
          },
          {
            key: 'teacher',
            label: '教学助手',
            description: '专注于教学场景，帮助解答课程相关问题',
          },
          {
            key: 'programmer',
            label: '编程助手',
            description: '专注于编程问题，提供代码示例和调试建议',
          },
          {
            key: 'analyst',
            label: '数据分析助手',
            description: '帮助分析数据、生成报表和可视化建议',
          },
        ],
        tool_options: [
          {
            key: 'search',
            label: '知识检索',
            description: '从知识库中检索相关信息',
          },
          {
            key: 'calculator',
            label: '计算器',
            description: '执行数学计算',
          },
        ],
        default_active_tools: ['search'],
      });
    });

    // POST /api/chat/ - 返回固定一段 Markdown
    Mock.mock(new RegExp('/api/chat/$'), 'post', () => {
      return successResponseWrap({
        id: 1,
        thread_id: 'default',
        user_input: '',
        system_prompt: '',
        response: '## 演示模式\n\n当前为本地 Mock 环境。\n\n智屿 AI 助手的完整能力包括：\n- 基于 RAG 的知识检索\n- 4 种教学 Prompt 模式\n- 多模态资源问答',
        created_at: new Date().toISOString(),
      });
    });

    // GET /chat/history/:threadId - 返回 2 条示例对话
    Mock.mock(new RegExp('/chat/history/[^/]+$'), 'get', () => {
      return successResponseWrap([
        {
          id: 1,
          thread_id: 'default',
          user_input: '你好，请介绍一下这个课程平台的功能',
          system_prompt: '',
          response: '你好！智屿教育平台是一个综合性的在线学习管理系统，主要功能包括：\n\n1. **课程管理**：支持多种课程类型的创建和管理\n2. **AI 助教**：基于 RAG 技术的智能问答助手\n3. **教学资源**：支持文档、视频等多种资源格式\n4. **学习分析**：提供详细的学习行为数据分析\n5. **数字人**：支持 AI 数字人教学',
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: 2,
          thread_id: 'default',
          user_input: '如何上传课程资料？',
          system_prompt: '',
          response: '您可以通过以下步骤上传课程资料：\n\n1. 进入课程详情页\n2. 点击"资源管理"标签\n3. 选择"上传文件"按钮\n4. 支持 PDF、Word、PPT、视频等多种格式\n\n上传后，AI 助手会自动解析内容，学生可以通过对话方式查询资料内容。',
          created_at: new Date().toISOString(),
        },
      ]);
    });

    // GET /api/chat/threads - 返回会话列表
    Mock.mock(new RegExp('/api/chat/threads'), 'get', () => {
      return successResponseWrap([
        {
          id: 1,
          thread_id: 'default',
          title: '默认会话',
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: 2,
          thread_id: 'thread-2',
          title: 'Python 学习讨论',
          created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ]);
    });
  },
});
