= 知曦 (Zhi Xi) 项目前端页面与互动需求拆解
根据提供的《知曦--Agent驱动的个性化学习支持系统》PPT ，系统采用了Vue + Element UI + Echarts的技术栈 。以下是完整的页面路由、UI组件、交互需求以及用于本地前端开发的默认 Mock 数据拆解。

== 0. 全局布局 (Global Layout)

导航栏/侧边栏: 包含系统四大核心模块：仪表盘、课程中心、智能助手、个人中心 。

状态栏: 登录用户信息、全局搜索、消息提醒、全局设置。
== 1. 登录模块 (Login)
=== 页面需求
账号与密码输入框 。

记住密码勾选框、忘记密码链接、注册账号链接 。

登录按钮 。

=== 互动需求
基础的表单校验（非空、格式）。
登录成功后，前端路由跳转至“仪表盘”。
== 2. 仪表盘 (Dashboard)
仪表盘按业务场景可分为“实时数据总览”和“实时课堂监测”两个核心视图。
=== 2.1 实时数据总览页
UI组件:
欢迎提示语 。

顶部核心指标卡片：展示课堂总数、教师人数、平台资源数 。

平台访问量折线图 (Echarts 渲染) 。

内容类型占比饼图 (Echarts 渲染) 。

线上热门内容排行榜 (Table 组件) 。

互动需求:
图表 Hover 显示具体数值和浮层。
“查看更多”跳转及时间范围筛选 。

Mock 数据:
JSON
{
  "coreMetrics": { "classrooms": 3735, "teachers": 768, "resources": 8874 },
  "visits": [
    {"date": "2025-05-23", "count": 600},
    {"date": "2025-05-24", "count": 800},
    {"date": "2025-05-25", "count": 550}
  ],
  "popularContent": [
    {"rank": 1, "title": "MySQL入门教程", "clicks": 367, "trend": "5%-"},
    {"rank": 2, "title": "Ollama本地部署...", "clicks": 352, "trend": "17%-"},
    {"rank": 3, "title": "MCP从入门到实战", "clicks": 340, "trend": "30%-"}
  ],
  "contentType": [
    {"type": "课程", "percentage": 24.78},
    {"type": "资源", "percentage": 55.77},
    {"type": "讨论", "percentage": 12.02},
    {"type": "作业", "percentage": 7.43}
  ]
}

=== 2.2 实时课堂监测页 (视频监控与行为识别)
UI组件:
实时视频流播放区域，叠加后端返回的 YOLO 检测识别框（如 study_one, phone_user 等标签） 。

视频流物理参数显示（码率、帧率、CDN 等） 。

课堂签到网格：展示学生头像、姓名以及当前状态（已签到/迟到/缺席/请假） 。

学生状态统计仪表盘（抬头率、专注率、互动次数、瞌睡人数等） 。

实时聊天窗口 。

互动需求:
切换视频清晰度与直播线路（主备流切换） 。

开启/关闭课堂行为检测（控制 YOLO 识别框的显隐） 。

Mock 数据:
JSON
{
  "streamInfo": { "bitrate": "6 Mbps", "fps": 60, "format": "FLV" },
  "attendance": [
    {"name": "张伟", "status": "已签到"},
    {"name": "孙倩", "status": "迟到"},
    {"name": "刘洋", "status": "缺席"}
  ],
  "behaviorStats": {
    "headUpRate": "0.6",
    "focusRate": "0.5",
    "interactionCount": 20,
    "sleepCount": 2,
    "phoneCount": 10
  }
}

== 3. 课程中心 (Course Center)
=== 3.1 课程总览页
UI组件:
顶部搜索栏，支持按教师或课程名称检索 。

学院分类 Tab（全部、计算机学院、经管学院等） 。

课程卡片列表（包含课程名称、教师姓名、邮箱、所属学院） 。

Mock 数据:
JSON
{
  "courses": [
    {"id": 1, "name": "人工智能", "teacher": "潘教授", "email": "Ruiiii.teacher@...", "college": "计算机学院"},
    {"id": 2, "name": "宏观经济学", "teacher": "王教授", "email": "wang.teacher@...", "college": "经管学院"}
  ]
}

=== 3.2 课程信息详情页
UI组件:
课程基础属性（学分、课程性质、课堂数量） 。

授课信息表格（授课老师、上课地点、上课时间、上课人数） 。

学生作业完成情况综合评价排行榜 。

课程模式雷达图 (讲授型、混合型、对话型、联系型) 。

课程资源占比图（文档、视频、图片、作业等大小和百分比） 。

课程资源访问量折线图 。

Mock 数据:
JSON
{
  "courseInfo": {
    "credits": 2.5,
    "type": "专业主干课",
    "description": "《接口技术》介绍了微型计算机..."
  },
  "schedule": [
    {"teacher": "姚华雄", "location": "n112", "time": "星期一 第1-2节", "students": 43}
  ],
  "assignments": [
    {"rank": 1, "name": "张三", "score": 99.62},
    {"rank": 2, "name": "李四", "score": 98.42}
  ],
  "courseMode": {"lecture": 67, "hybrid": 52, "dialogue": 43, "practice": 17}
}

=== 3.3 课堂内容 (视频解析与 AI 伴学)
UI组件:
主视频点播播放器 。

智能识别的内容时段划分轴 (Timeline) 与知识点导航列表 。

侧边悬浮的 AI 助手对话框 。

课堂笔记提取区、思维导图生成区、课程知识图谱渲染区 。

互动需求:
点击知识点列表，视频播放器无缝跳转至对应时间戳。
AI 助手实时上下文解答：学生在特定视频帧暂停提问，系统需连带当前视频时间戳作为 Context 发送给后端 。

一键生成当前视频章节的结构化思维导图或知识图谱。
Mock 数据:
JSON
{
  "chapters": [
    {"time": "00:00", "title": "并发控制概述"},
    {"time": "01:10", "title": "多事务执行方式", "keyInfo": "基础概念"}
  ],
  "aiChat": [
    {"role": "assistant", "content": "同学你好！课程遇到什么问题了吗？"},
    {"role": "user", "content": "老师，课程这里提到的控制方式有没有具体例子？"},
    {"role": "assistant", "content": "当然有，事务串行执行是..."}
  ],
  "notes": "一、并发控制\n1.多用户数据库系统\n(1)允许多个用户同时访问和操作数据库。"
}

== 4. 智能助手 (Smart Assistant / Agent)
=== 页面需求
类似标准大语言模型的流式对话主界面 。

Markdown 解析渲染器（用于格式化显示学习计划、SQL 代码块等） 。

参数设置面板 (Drawer 或 Dialog) 。

模型下拉选择器 (如 deepseek-chat) 。

流式响应 Toggle 拨动开关 。

API Key 填入框 。

MCP 工具列表多选框（获取MCP工具、与PostgreSQL数据库交互、知识图谱记忆、实时网络搜索等） 。

模型生成参数滑块：Max Tokens, Temperature, Top-P, Top-K 。

历史对话侧边栏（新建对话按钮、历史 Session 列表） 。

=== 互动需求
SSE (Server-Sent Events) 或 WebSocket 实现消息打字机流式输出。
前端需根据勾选的 MCP 工具状态，在对话时展示后端的 Tool Calling 进度（如：“正在搜索网络...”）。
Mock 数据:
JSON
{
  "settings": {
    "model": "deepseek-chat",
    "temperature": 0.7,
    "topP": 0.7,
    "maxTokens": 4096,
    "activeTools": ["realtime_search", "local_knowledge", "postgresql"]
  },
  "history": [
    {"id": "h1", "title": "数据库原理学习计划"},
    {"id": "h2", "title": "日常问候"}
  ]
}

== 5. 个人中心 (Personal Center)
=== 5.1 学习数据 (学情分析)
UI组件:
学生基础画像（姓名、学号、专业、本学期选修课程列表） 。

日历提醒组件（高亮标记作业、实验截止日期） 。

学生学情概况看板（云端时长、讨论次数、互动次数、平均成绩等） 。

学情预警列表（展示日期、课程名及预警原因） 。

学习时长分布环形图 。

Mock 数据:
JSON
{
  "profile": {
    "name": "卡布奇",
    "studentId": "12345689",
    "major": "计算机科学与技术",
    "activeCourses": ["《计算机组成原理》", "《操作系统》", "《计算机网络》"]
  },
  "overview": { "cloudTime": 11, "discussions": 2, "score": 91 },
  "alerts": [
    {"date": "2025.4.27", "course": "操作系统课程", "reason": "上课无故缺席"},
    {"date": "2025.4.23", "course": "计算机网络", "reason": "实验作业未提交"}
  ],
  "timeDistribution": [
    {"course": "计算机网络", "percentage": 26.27},
    {"course": "操作系统", "percentage": 22.88},
    {"course": "算法设计与分析", "percentage": 21.19}
  ]
}

=== 5.2 用户信息与课程
UI组件:
我的课程宫格列表（显示课程名、英文名、报名人数） 。

最新动态 Feed 流时间线 。

消息中心面板（包含消息、通知、待办三个切换 Tab） 。

我的小组及人数统计侧边栏 。

Mock 数据:
JSON
{
  "messages": [
    {"type": "message", "sender": "郑曦月", "content": "我已批改你的作业，请查收！", "time": "今天12:30:01"},
    {"type": "notification", "title": "规则开通成功", "content": "内容屏蔽规则于2025-02-01生效"},
    {"type": "todo", "title": "提交截止通知", "content": "您的算法作业即将截止..."}
  ],
  "groups": [
    {"name": "智能应用小组", "members": 80},
    {"name": "产品设计团队", "members": 51}
  ]
}

=== 5.3 用户设置
UI组件:
侧边基础信息只读展示（用户名、账号ID、实名认证状态、脱敏手机号、注册时间） 。

主区域信息编辑表单（必填项：邮箱、昵称、国家/地区、所在区域；选填项：具体地址、200字以内个人简介） 。

表单底部的保存与重置操作按钮 。

在初期开发中，前端可以直接挂载上述 Mock JSON 来实现 Vue 组件的渲染与交互流转。由于后端采用了 FastAPI 以及 LangGraph + MCP 框架 ，后续联调时，核心需要关注“智能助手”的流式接口对接，以及“实时课堂”页面的 WebRTC 或 HLS 视频流接入。

