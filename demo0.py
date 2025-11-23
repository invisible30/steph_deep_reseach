import os
from typing import List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessageChunk
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain.chat_models import init_chat_model

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
        min_items=1,
        max_items=3,
    )
# ===================== 2. 定义 State =====================
class ResearchState(MessagesState):
    # 继承 MessagesState：已经有 messages: list[AnyMessage]
    plan: Optional[ResearchPlan] = None   # 第一步产生的研究问题
    drafts: Optional[List[str]] = None    # 第二步每个子问题的分析
    report: Optional[str] = None          # 第三步最终报告


# ===================== 3. 初始化 LLM =====================
# llm=ChatOpenAI(model=DEEPSEEK_CHAT_MODEL,api_key=DEEPSEEK_API_KEY,base_url=DEEPSEEK_BASE_URL)

# ===================== 4. 三个节点的实现 =====================
def plan_node(state: ResearchState) -> dict:
    """根据用户输入生成 1-3 个子问题的 ResearchPlan。"""
    # 取最后一条用户消息作为“研究目标”
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    user_query = user_messages[-1].content if user_messages else "帮我做一个研究"
    planner_llm = llm.with_structured_output(ResearchPlan)
    plan = planner_llm.invoke([
        SystemMessage(
            content=(
                "你是一个研究规划助手。\n"
                "根据用户提出的问题，拆分出 1-3 个关键研究子问题。\n"
                "注意：子问题要具体、互补、覆盖原始问题的核心维度。"
            )
        ),
        HumanMessage(content=user_query),
    ])

    # 顺便在对话历史里加一条“规划说明”（可选）
    plan_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(plan.questions))
    plan_msg = AIMessage(
        content=f"我将围绕以下子问题展开研究：\n{plan_text}"
    )

    return {
        "plan": plan,
        "messages": state["messages"] + [plan_msg],
    }

def research_node(state: ResearchState) -> dict:
    """对 plan 中的每个子问题生成一段分析（drafts）。"""
    if state["plan"] is None or not state["plan"].questions:
        # 理论上不该发生，这里做个兜底
        warn_msg = AIMessage(content="未找到研究计划，无法展开研究。")
        return {"messages": state["messages"] + [warn_msg]}

    drafts: List[str] = []

    for idx, q in enumerate(state["plan"].questions, start=1):
        # 对每个子问题单独让 LLM 展开分析
        resp = llm.invoke([
            SystemMessage(
                content=(
                    "你是一名严谨的研究助理。\n"
                    "请对给定的子问题做一段深入分析，包含：背景、关键因素、"
                    "当前现状、潜在问题或挑战。不要写成报告，只写该子问题的分析段落。"
                )
            ),
            HumanMessage(content=f"子问题 {idx}: {q}"),
        ])
        drafts.append(resp.content)

    # 在对话中追加一条说明（可选）
    summary_msg = AIMessage(
        content="我已经针对每个子问题分别写好了分析草稿。"
    )

    return {
        "drafts": drafts,
        "messages": state["messages"] + [summary_msg],
    }


def report_node(state: ResearchState) -> dict:
    """根据 plan.questions + drafts 生成最终报告。"""
    if state["drafts"] is None or state["plan"] is None:
        err_msg = AIMessage(content="缺少 drafts 或 plan，无法生成最终报告。")
        return {"messages": state["messages"] + [err_msg]}

    # 把子问题和对应草稿组织成一个 prompt
    bullets = []
    for i, (q, d) in enumerate(zip(state["plan"].questions, state["drafts"]), start=1):
        bullets.append(f"【子问题 {i}】{q}\n【分析草稿】{d}")

    joined = "\n\n".join(bullets)

    resp = llm.invoke([
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
    ])

    final_report = resp.content
    report_msg = AIMessage(
        content="下面是根据分析草稿整合出的最终报告：\n\n" + final_report
    )

    return {
        "report": final_report,
        "messages": state["messages"] + [report_msg],
    }


# ===================== 5. 搭建 LangGraph =====================

workflow = StateGraph(ResearchState)

workflow.add_node("plan", plan_node)
workflow.add_node("research", research_node)
workflow.add_node("report", report_node)

workflow.add_edge(START, "plan")
workflow.add_edge("plan", "research")
workflow.add_edge("research", "report")
workflow.add_edge("report", END)

app = workflow.compile()


# ===================== 6. 调用示例 =====================
user_question = "请帮我系统分析一下：未来 5 年中国大模型产业的发展机会和挑战。"

initial_state = ResearchState(
    messages=[HumanMessage(content=user_question)]
)

result = app.invoke(initial_state)

# 打印最终报告
print("===== 最终报告 =====")
print(result["report"])