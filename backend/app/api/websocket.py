from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
import logging
from typing import Dict, Any
from ..services.research import conduct_research_stream

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 存储活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}

@router.websocket("/research")
async def websocket_research_endpoint(websocket: WebSocket):
    """
    WebSocket端点用于实时研究分析

    客户端发送的消息格式:
    {
        "type": "question",
        "content": "用户的问题"
    }

    服务器返回的消息格式:
    {
        "type": "status|plan|research|report|complete|error",
        "content": "消息内容",
        "stage": "当前阶段",
        "question_index": int,  # 可选，研究阶段使用
        "total_questions": int, # 可选，研究阶段使用
        "question": str         # 可选，研究阶段使用
    }
    """
    await websocket.accept()

    # 生成连接ID
    connection_id = f"conn_{len(active_connections)}"
    active_connections[connection_id] = websocket

    logger.info(f"WebSocket连接已建立: {connection_id}")

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "question":
                user_question = message.get("content", "").strip()

                if not user_question:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "问题不能为空",
                        "stage": "error"
                    }))
                    continue

                logger.info(f"接收到问题: {user_question}")

                # 执行研究并流式返回结果
                try:
                    # conduct_research_stream 是一个异步函数，会处理所有WebSocket通信
                    await conduct_research_stream(user_question, websocket)
                except Exception as e:
                    logger.error(f"研究过程中发生错误: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": f"研究失败: {str(e)}",
                        "stage": "error"
                    }))

            elif message.get("type") == "ping":
                # 心跳检测
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "stage": "heartbeat"
                }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": f"未知的消息类型: {message.get('type')}",
                    "stage": "error"
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        # 清理连接
        if connection_id in active_connections:
            del active_connections[connection_id]

@router.get("/connections")
async def get_active_connections():
    """获取当前活跃连接数（用于监控）"""
    return {
        "active_connections": len(active_connections),
        "connections": list(active_connections.keys())
    }

# REST API端点，用于非WebSocket请求
@router.post("/ask")
async def ask_question(request: Dict[str, str]):
    """
    非流式的研究接口

    请求格式:
    {
        "question": "用户的问题"
    }
    """
    try:
        question = request.get("question", "").strip()
        if not question:
            return JSONResponse(
                status_code=400,
                content={"error": "问题不能为空"}
            )

        # 导入同步版本的研究函数
        from ..services.research import conduct_research_sync

        # 执行研究
        result = conduct_research_sync(question)

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        logger.error(f"REST API研究错误: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"研究失败: {str(e)}"}
        )