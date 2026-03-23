import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "backend/app/main.py",  # 主程序入口
        "--name=backend_app",  # 生成的可执行文件名
        "--onefile",  # 打包成单个文件
        "--clean",  # 清理临时文件
        "--add-data=backend/app/email-templates:email-templates",  # 包含邮件模板
        "--hidden-import=uvicorn",
        "--hidden-import=fastapi",
        "--hidden-import=sqlalchemy",
        "--hidden-import=alembic",
        "--noconsole",  # 不显示控制台窗口
    ]
)
