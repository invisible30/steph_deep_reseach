from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from .api.websocket import router as websocket_router

app = FastAPI(
    title="LangGraph Research Assistant",
    description="AI-powered research assistant with real-time streaming",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应��设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API路由
app.include_router(websocket_router, prefix="/ws")

@app.get("/api")
async def root():
    return {"message": "LangGraph Research Assistant API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# 主页重定向到前端
@app.get("/home", response_class=HTMLResponse)
async def get_home():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
    frontend_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(frontend_index):
        with open(frontend_index, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)

# 挂载静态文件（最后挂载，确保其他路由优先）
# 使用绝对路径
import sys
current_file = os.path.abspath(__file__)
project_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
frontend_path = os.path.join(project_root, "frontend")

print(f"🔍 调试信息:")
print(f"   当前文件: {current_file}")
print(f"   项目根目录: {project_root}")
print(f"   前端目录: {frontend_path}")
print(f"   前端目录存在: {os.path.exists(frontend_path)}")

if os.path.exists(frontend_path):
    # 挂载整个frontend目录到根路径
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    print("✅ 静态文件服务已挂载")
else:
    print("❌ 前端目录不存在")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)