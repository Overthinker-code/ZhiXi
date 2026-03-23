前端：
- npm run  dev   开始运行。
- 看到VITE v3.2.11 ready 时，表示前端已成功启动。

后端：
- 进入backend文件夹，使用uvicorn app.main:app reload
- 看到 INFO: Uvicorn running on http://127.0.0.1:8000 时，表示后端服
  务器已成功启动。
- 

前端启动

在项目根目录执行：
cd d:\MyCode\edu\code\education\course
npm run dev
看到 VITE v3.2.11 ready 表示前端已成功启动。
后端启动

在项目根目录执行：
cd d:\MyCode\edu\code\backend
uvicorn app.main:app --reload
看到 127.0.0.1 (line 8000) 表示后端已成功启动。



Ollama：
启动 Ollama 服务
ollama serve



数据库：
docker start education-postgres

