#!/usr/bin/env python3
"""
LangGraph 研究助手 Web 应用启动脚本
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

def start_backend():
    """启动后端服务"""
    print("🚀 启动后端服务...")

    # 切换到backend目录
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ 未找到 backend 目录")
        return False

    os.chdir(backend_dir)

    # 设置Python路径
    current_dir = Path.cwd().parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    try:
        # 启动FastAPI应用
        print("   启动 FastAPI 服务器...")
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n   🛑 后端服务已停止")
    except Exception as e:
        print(f"   ❌ 后端服务启动失败: {e}")
        return False

    return True

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务器启动

    urls = [
        "http://localhost:8000/home",
        "http://localhost:8000/index.html",  # 直接访问前端文件
        "http://localhost:8000/docs",  # FastAPI 文档
        "http://localhost:8000/api"   # API 根路径
    ]

    for url in urls:
        try:
            print(f"🌐 打开浏览器: {url}")
            webbrowser.open(url)
            break
        except Exception as e:
            print(f"   ⚠️ 无法自动打开浏览器: {e}")
            print(f"   请手动访问: {url}")
            break

def print_startup_info():
    """打印启动信息"""
    print("\n" + "="*60)
    print("🧠 LangGraph 研究助手 Web 应用")
    print("="*60)
    print("\n📍 服务地址:")
    print("   📄 前端界面: http://localhost:8000/home")
    print("   📱 直接访问: http://localhost:8000/index.html")
    print("   📚 API 文档: http://localhost:8000/docs")
    print("   🔗 WebSocket: ws://localhost:8000/ws/research")
    print("   📡 API 状态: http://localhost:8000/api/health")
    print("\n💡 使用说明:")
    print("   1. 在浏览器中打开前端界面")
    print("   2. 输入您想研究的问题")
    print("   3. 实时查看AI分析过程和最终报告")
    print("\n🛠️ 开发模式:")
    print("   - 后端代码修改会自动重启")
    print("   - 按 Ctrl+C 停止服务")
    print("\n" + "="*60 + "\n")

def main():
    """主函数"""
    print("🚀 正在启动 LangGraph 研究助手 Web 应用...\n")

    # 打印启动信息
    print_startup_info()

    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    try:
        # 启动后端服务（这会阻塞主线程）
        start_backend()
    except KeyboardInterrupt:
        print("\n👋 感谢使用 LangGraph 研究助手！")
    except Exception as e:
        print(f"\n❌ 程序异常退出: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()