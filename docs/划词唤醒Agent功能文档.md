# 划词唤醒 Agent 功能文档

## 功能概述

"划词唤醒 Agent"是一个沉浸式学习功能，使学生能够在课堂笔记中选中任意文本，并通过预设的 Prompt 模板快速调用 AI Agent 进行智能解析和讲解。

## 功能特点

- **即时交互**：选中文本后自动弹出上下文菜单，无需切换页面
- **多种模板**：提供4种预设模板（解释概念、举个例子、总结代码、深入讲解）
- **智能上下文**：自动收集选中文本周围的上下文，提供更精准的回答
- **流式响应**：AI 响应以 Markdown 格式实时显示
- **对话记录**：所有交互自动保存到聊天历史中

## 技术架构

### 前端组件

**文件位置**: `/code/education/course/src/views/course/monitor/components/classroom-notes.vue`

**核心功能模块**:

1. **划词检测** (`handleTextSelection`)
   - 监听 `mouseup` 和 `touchend` 事件
   - 使用 `window.getSelection()` API 获取选中文本
   - 自动提取上下文（选中文本前后100个字符）

2. **上下文菜单** (Context Menu)
   - 动态定位在选中文本位置
   - 展示4个操作选项，对应不同的 Prompt 模板
   - 支持鼠标和触摸交互

3. **Prompt 模板**:

   ```javascript
   {
     key: 'explain',
     label: '📖 解释概念',
     prompt: (selected) => `请用简白易懂的方式解释以下数据库概念...\n"${selected}"`
   },
   {
     key: 'example',
     label: '💡 举个例子',
     prompt: (selected) => `关于"${selected}"这个概念，请给出...\n1. 一个具体的现实生活中的例子`
   },
   {
     key: 'summarize',
     label: '📝 总结代码',
     prompt: (selected) => `请总结以下代码段或内容的核心要点...\n"${selected}"`
   },
   {
     key: 'deepdive',
     label: '🔍 深入讲解',
     prompt: (selected) => `请对"${selected}"进行深入讲解...\n1. 原理和机制`
   }
   ```

4. **API 调用** (`sendAIQuery`)
   - 调用 `/api/chat/selection-query` 端点
   - 传递文本、上下文、Prompt 模板等信息
   - 支持自定义系统提示词

### 后端 API

**端点**: `POST /api/v1/chat/selection-query`

**请求体**:
```python
class ChatStreamRequest(BaseModel):
    user_input: str
    selected_text: str | None = None          # 选中的文本
    surrounding_context: str | None = None     # 周围上下文
    thread_id: str                             # 会话 ID
    system_prompt: str = ""                    # 自定义系统提示词
    prompt_key: str = "default"                # Prompt 模板键
    rag_k: int = 4                             # RAG 检索数量
    strict_mode: bool = False
    active_tools: list[str] | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    video_time: str | None = None              # 视频时间戳
    course_module: str | None = None           # 课程模块
    current_file_id: str | None = None
    file_name: str | None = None
```

**响应体**:
```python
class ChatResponse(BaseModel):
    response: str                  # AI 的回答
    tool_calls: list[dict]        # 工具调用记录
    agent: str                    # 使用的 Agent 类型
    intent: str                   # 处理意图
    routing_reason: str           # 路由原因
    thoughts: list[str]           # 代理思考过程
    requires_confirmation: bool   # 是否需要用户确认
    pending_action_id: str | None # 待确认操作 ID
```

**处理流程**:

1. 接收请求时，检查 `selected_text` 字段
2. 如果存在，通过 `_build_selection_prompt()` 函数构建增强提示词
3. 将增强后的提示词作为 `user_input` 传递给主监督代理
4. 返回 AI 的结构化响应

**Prompt 构建逻辑** (`_build_selection_prompt`):

```python
def _build_selection_prompt(request: ChatRequest) -> str:
    selected = (request.selected_text or "").strip()
    context = (request.surrounding_context or "").strip()
    module = (request.course_module or "当前课程").strip()
    video_time = (request.video_time or "").strip()
    
    prompt = (
        f"学生在学习《{module}》时选中了"{selected}"。\n"
        f"上下文片段：{context or '（无）'}\n"
    )
    if video_time:
        prompt += f"当前视频时间点：{video_time}\n"
    prompt += (
        "请用引导式、教学友好的口吻回答。"
        "如果适合，请补充一个简短示例帮助理解。"
    )
    return prompt
```

## 使用流程

### 用户交互流程

```
1. 学生打开"课堂笔记"页面
   ↓
2. 在笔记内容中选中感兴趣的文本
   ↓
3. 自动显示上下文菜单（包含4个操作选项）
   ↓
4. 学生点击其中一个选项
   ↓
5. 前端调用选中的 Prompt 模板
   ↓
6. 发送请求到后端 /chat/selection-query 端点
   ↓
7. 后端使用 LangGraph Agent 协作编排处理
   ↓
8. 返回 AI 的智能回答（Markdown 格式）
   ↓
9. 前端渲染响应并展示在 "AI 解答" 面板中
   ↓
10. 对话自动保存到聊天历史中
```

### 集成步骤

#### 1. 前端集成

已完成。课堂笔记组件已在 `/views/course/monitor/index.vue` 中导入：

```vue
<script lang="ts" setup>
  import ClassroomNotes from './components/classroom-notes.vue';
</script>

<template>
  <ClassroomNotes />
</template>
```

#### 2. 后端集成

后端已完全支持。无需额外集成。已存在的端点：

- `POST /api/v1/chat/selection-query` - 处理划词查询
- `POST /api/v1/chat/resume` - 处理用户确认
- `GET /api/v1/chat/settings` - 获取 AI 设置

#### 3. API 调用流程

前端通过 `/src/api/rag.ts` 中的 `askSelectionQuery()` 函数调用：

```typescript
export function askSelectionQuery(
  selectedText: string,
  surroundingContext: string,
  threadId: string,
  options: ChatAdvancedOptions
) {
  return axios.post('/chat/selection-query', {
    user_input: selectedText,
    selected_text: selectedText,
    surrounding_context: surroundingContext,
    thread_id: threadId,
    // ... 其他选项
  });
}
```

## 预设的硬编码笔记内容

课堂笔记组件使用了数据库教学课程的示例内容：

- **位置**: `/components/classroom-notes.vue` 中的 `notesContent` 变量
- **内容**: 包含7个主要部分：
  1. 关系模型概述
  2. 关键概念
  3. 数据完整性约束
  4. 规范化理论
  5. SQL操作
  6. 事务处理
  7. 索引机制

## 测试指南

### 本地测试

1. **启动应用**:
   ```bash
   cd code/education/course
   npm run dev
   ```

2. **访问课堂笔记**:
   - 打开浏览器访问 `http://localhost:5173`
   - 导航到"实时课堂"页面（Course Monitor）
   - 找到"课堂笔记"卡片

3. **测试划词功能**:
   - 在笔记内容中选中文本（如 "关系模型"）
   - 验证上下文菜单是否显示
   - 点击一个操作选项（如"解释概念"）
   - 等待 AI 响应
   - 验证响应是否正确渲染

4. **验证集成**:
   - 检查浏览器控制台是否有错误
   - 检查网络请求是否正确发送
   - 验证响应是否正确保存到聊天历史

### 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| 上下文菜单不显示 | 选中文本为空或事件未触发 | 确保正确选中非空文本 |
| AI 响应为空 | 后端服务未运行或 API 错误 | 检查后端错误日志 |
| 响应渲染不正确 | Markdown 渲染失败 | 检查 `renderMarkdown` 函数 |
| 聊天记录未保存 | 数据库连接或设置问题 | 检查后端数据库状态 |

## 国际化支持

已支持中文和英文。相关文本定义在：

- 中文: `/views/course/monitor/locale/zh-CN.ts`
- 英文: `/views/course/monitor/locale/en-US.ts`

新增的国际化键：

```typescript
'monitor.title.classroomNotes': '课堂笔记' // 中文
'monitor.title.classroomNotes': 'Classroom Notes' // 英文
```

## 扩展建议

1. **添加更多笔记内容**: 在 `classroom-notes.vue` 中修改 `notesContent` 变量
2. **自定义 Prompt 模板**: 在 `promptTemplates` 数组中添加新模板
3. **添加笔记搜索**: 实现笔记内容的搜索功能
4. **支持笔记导入**: 允许上传外部笔记文件
5. **添加笔记批注**: 支持高亮和添加个人备注

## 性能优化建议

1. **缓存 Markdown 渲染结果**: 避免重复渲染相同内容
2. **实现虚拟滚动**: 处理大量笔记内容时提高性能
3. **流式 Markdown 渲染**: 在 AI 响应流式返回时实时渲染
4. **上下文预加载**: 预加载笔记相关的 RAG 知识库

## 安全性考虑

1. **输入验证**: 后端验证 `selected_text` 和 `surrounding_context` 的长度和内容
2. **权限检查**: 确保用户只能访问自己的对话记录
3. **XSS 防护**: Markdown 渲染时进行适当的 HTML 清理
4. **速率限制**: 限制单个用户的 API 调用频率
