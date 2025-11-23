import os
from typing import List, Optional, AsyncGenerator, Dict, Any
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain.chat_models import init_chat_model
import json

# 加载环境变量
load_dotenv()

# 从环境变量读取配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY 环境变量未设置，请在 .env 文件中配置")

llm = init_chat_model(
    model=DEEPSEEK_CHAT_MODEL,
    model_provider="deepseek",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# ===================== 1. 定义结构化 Plan =====================
class ResearchPlan(BaseModel):
    questions: List[str] = Field(
        description="List of 1-3 key research questions to investigate",
        max_items=3,
    )

# ===================== 2. 定义 State =====================
class ResearchState(MessagesState):
    # 继承 MessagesState：已经有 messages: list[AnyMessage]
    plan: Optional[ResearchPlan] = None   # 第一步产生的研究问题
    drafts: Optional[List[str]] = None    # 第二步每个子问题的分析
    report: Optional[str] = None          # 第三步最终报告

# ===================== 3. 三个节点的实现 =====================

async def plan_node(state: ResearchState, websocket=None) -> dict:
    """根据用户输入生成 1-3 个子问题的 ResearchPlan。"""
    # 取最后一条用户消息作为"研究目标"
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    user_query = user_messages[-1].content if user_messages else "帮我做一个研究"

    # 发送状态消息
    if websocket:
        await websocket.send_text(json.dumps({
            "type": "status",
            "content": "正在生成研究计划...",
            "stage": "plan"
        }))

    # 先流式输出规划说明
    plan_text = ""
    async for chunk in llm.astream([
        SystemMessage(
            content=(
                "你是一个研究规划助手。\n"
                "根据用户提出的问题，拆分出 1-3 个关键研究子问题。\n"
                "注意：子问题要具体、互补、覆盖原始问题的核心维度。\n"
                "请直接输出你的规划说明，说明你将围绕哪些子问题展开研究。"
            )
        ),
        HumanMessage(content=user_query),
    ]):
        piece = chunk.content
        plan_text += piece

        # 通过WebSocket实时发送
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "plan",
                "content": piece,
                "stage": "plan"
            }))

    # 然后获取结构化输出用于后续处理
    planner_llm = llm.with_structured_output(ResearchPlan)
    plan = await planner_llm.ainvoke([
        SystemMessage(
            content=(
                "你是一个研究规划助手。\n"
                "根据用户提出的问题，拆分出 1-3 个关键研究子问题。\n"
                "注意：子问题要具体、互补、覆盖原始问题的核心维度。"
            )
        ),
        HumanMessage(content=user_query),
    ])

    # 在对话历史里加一条"规划说明"
    plan_msg = AIMessage(
        content=f"我将围绕以下子问题展开研究：\n{plan_text}"
    )

    return {
        "plan": plan,
        "messages": state["messages"] + [plan_msg],
    }


async def research_node(state: ResearchState, websocket=None) -> dict:
    if state["plan"] is None or not state["plan"].questions:
        warn_msg = AIMessage(content="未找到研究计划，无法展开研究。")
        return {"messages": state["messages"] + [warn_msg]}

    drafts: List[str] = []

    for idx, q in enumerate(state["plan"].questions, start=1):
        # 发送状态消息
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "status",
                "content": f"正在分析子问题 {idx}: {q}",
                "stage": "research",
                "question_index": idx,
                "total_questions": len(state["plan"].questions)
            }))

        # 累积完整内容
        full_text = ""

        # 异步流式输出
        async for chunk in llm.astream([
            SystemMessage(
                content=(
                    "你是一名严谨的研究助理。\n"
                    "请对给定的子问题做一段深入分析，包含：背景、关键因素、"
                    "当前现状、潜在问题或挑战。不要写成报告，只写该子问题的分析段落。"
                )
            ),
            HumanMessage(content=f"子问题 {idx}: {q}"),
        ]):
            piece = chunk.content
            full_text += piece

            # 通过WebSocket实时发送
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "research",
                    "content": piece,
                    "stage": "research",
                    "question_index": idx,
                    "question": q,
                    "total_questions": len(state["plan"].questions)
                }))

        drafts.append(full_text)

    summary_msg = AIMessage(
        content="我已经针对每个子问题分别写好了分析草稿。"
    )

    return {
        "drafts": drafts,
        "messages": state["messages"] + [summary_msg],
    }


async def report_node(state: ResearchState, websocket=None) -> dict:
    """根据 plan.questions + drafts 生成最终报告。"""
    if state["drafts"] is None or state["plan"] is None:
        err_msg = AIMessage(content="缺少 drafts 或 plan，无法生成最终报告。")
        return {"messages": state["messages"] + [err_msg]}

    # 把子问题和对应草稿组织成一个 prompt
    bullets = []
    for i, (q, d) in enumerate(zip(state["plan"].questions, state["drafts"]), start=1):
        bullets.append(f"【子问题 {i}】{q}\n【分析草稿】{d}")

    joined = "\n\n".join(bullets)

    # 发送状态消息
    if websocket:
        await websocket.send_text(json.dumps({
            "type": "status",
            "content": "正在生成最终报告...",
            "stage": "report"
        }))

    # 异步流式输出
    final_report = ""
    async for chunk in llm.astream([
        SystemMessage(
            content=(
                "你是一名擅长写结构化研究报告的写作者。\n"
                "现在给你若干子问题及它们的分析草稿，请你将它们整合成一篇完整的中文报告。\n"
                "要求：\n"
                "1. 报告结构包括：引言、主体分节、小结/展望。\n"
                "2. 主体部分可以按子问题/主题分段。\n"
                "3. 语言要自然流畅，逻辑清晰，不要逐句照抄草稿，可以适当重写和融合。\n"
                "4. 不要添加与草稿无关的硬事实；可以做合理的概括与归纳。"
            )
        ),
        HumanMessage(
            content=(
                "以下是子问题及对应分析草稿，请据此生成最终报告：\n\n"
                f"{joined}"
            )
        ),
    ]):
        piece = chunk.content
        final_report += piece

        # 通过WebSocket实时发送
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "report",
                "content": piece,
                "stage": "report"
            }))

    report_msg = AIMessage(
        content="下面是根据分析草稿整合出的最终报告：\n\n" + final_report
    )

    return {
        "report": final_report,
        "messages": state["messages"] + [report_msg],
    }

# ===================== 4. 搭建 LangGraph =====================

workflow = StateGraph(ResearchState)

workflow.add_node("plan", plan_node)
workflow.add_node("research", research_node)
workflow.add_node("report", report_node)

workflow.add_edge(START, "plan")
workflow.add_edge("plan", "research")
workflow.add_edge("research", "report")
workflow.add_edge("report", END)

app = workflow.compile()

# ===================== 5. 主要的异步研究函数 =====================

async def conduct_research_stream(user_question: str, websocket=None):
    """
    进行研究并通过WebSocket流式返回结果

    Args:
        user_question: 用户问题
        websocket: WebSocket连接对象
    """
    try:
        # 发送开始消息
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "start",
                "content": "开始分析您的问题...",
                "stage": "start"
            }))

        # 创建初始状态
        initial_state = ResearchState(
            messages=[HumanMessage(content=user_question)]
        )

        # 直接调用节点函数以保持流式输出
        # 步骤1: 计划节点
        plan_result = await plan_node(initial_state, websocket)

        # 更新状态
        initial_state["plan"] = plan_result["plan"]
        initial_state["messages"] = plan_result["messages"]

        # 步骤2: 研究节点
        research_result = await research_node(initial_state, websocket)

        # 更新状态
        initial_state["drafts"] = research_result["drafts"]
        initial_state["messages"] = research_result["messages"]

        # 步骤3: 报告节点
        report_result = await report_node(initial_state, websocket)

        # 发送完成消息
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "complete",
                "content": "研究完成！",
                "stage": "complete"
            }))

    except Exception as e:
        # 发送错误消息
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"研究过程中发生错误: {str(e)}",
                "stage": "error"
            }))
        raise

# 非WebSocket版本的同步接口（保持兼容性）
def conduct_research_sync(user_question: str) -> Dict[str, Any]:
    """
    同步版本的研究接口，用于REST API
    """
    initial_state = ResearchState(
        messages=[HumanMessage(content=user_question)]
    )

    result = app.invoke(initial_state)
    return {
        "plan": result["plan"].dict() if result["plan"] else None,
        "drafts": result["drafts"],
        "report": result["report"],
        "messages": [msg.content for msg in result["messages"]]
    }