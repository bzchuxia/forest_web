import os
import json
import threading
from functools import wraps
from typing import Generator, Dict, Any
from dotenv import load_dotenv

# --- LangChain 核心 ---
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool

# --- Spark 引擎 ---
try:
    from tool.spark_engine import spark_engine
except ImportError:
    try:
        from ..tool.spark_engine import spark_engine
    except:
        spark_engine = None

# --- 环境配置 ---
load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("❌ 错误：请在 .env 文件中配置 DASHSCOPE_API_KEY")

# ============================
# 🔥 3 秒超时保护
# ============================
def timeout_decorator(seconds=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            exception = None

            def target():
                nonlocal result, exception
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    exception = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                return "查询超时"
            if exception:
                return "查询失败"
            return result
        return wrapper
    return decorator

# ============================
# 🔥 帽儿山生物量数据查询工具
# ============================
@tool
@timeout_decorator(3)
def query_maoershan_biomass(sql_query: str) -> str:
    """
    帽儿山生物量数字孪生平台数据查询工具
    支持查询：生物量、树高、冠层高度、树种、位置、时间序列
    """
    try:
        if not spark_engine:
            return "Spark 服务未连接"

        # 自动限制最多 50 条，防止数据量爆炸
        sql_query = sql_query.strip().rstrip(";")
        if "limit" not in sql_query.lower():
            sql_query += " LIMIT 50"

        print(f"[帽儿山SQL] {sql_query}")
        result = spark_engine.query_data(sql_query)

        if isinstance(result, list):
            result = result[:50]

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception:
        return "数据查询失败"

tools = [query_maoershan_biomass]

# --- 模型配置 ---
llm = ChatOpenAI(
    model="qwen-plus",
    openai_api_key=DASHSCOPE_API_KEY,
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.1,
    streaming=True,
)

# ============================
# 🔥【最终极美化提示词】
# 干净、专业、无格式符号、前端美观
# ============================
prompt = ChatPromptTemplate.from_messages([
    ("system", """
你是【帽儿山生物量数字孪生平台】官方智能助手。

核心规则（必须严格遵守）：
1.  **优先回答问题**：先直接回答用户的核心问题，再根据需要补充信息，不要用无关的介绍开头。
2.  **禁止答非所问**：如果用户的问题和数据查询相关，必须先回答能不能查、怎么查，再做补充。
3.  **简洁专业**：回答不要冗长，不使用任何Markdown符号，只用纯文本，段落清晰。
4.  **权限说明**：
    - 平台**不提供HDFS底层文件系统的直接访问权限**；
    - 你只能查询通过 `query_maoershan_biomass` 工具封装好的结构化数据；
    - 如果用户问HDFS路径，直接说明无法直接访问，并告知支持的查询方式。

工具调用规则：
- 用户问数据查询、统计、列表类问题，必须优先调用 `query_maoershan_biomass` 工具；
- 表名固定：`biomass_data`；
- 支持字段：`date, location, species, height, biomass, canopy_height`；
- 单条查询最多返回50条记录，自动限制数据量。

异常回复规则：
- 查询超时：您的查询范围过大，为保证平台稳定已自动中断，请缩小范围后重试。
- 查询失败：很抱歉，数据服务暂时不可用，可能正在更新或服务繁忙。
- 问HDFS/底层文件：本平台不提供HDFS底层文件系统的直接访问权限，您可以查询封装好的结构化数据，如生物量、树高、树种等。
"""),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

# --- 智能体 ---
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

# --- 流式输出（干净美观版）---
def get_ai_response(user_input: str, history: list = []) -> Generator[str, None, None]:
    if not user_input.strip():
        yield "👋 你好！我是帽儿山生物量数字孪生平台智能助手，有什么可以帮您？"
        return

    try:
        input_dict = {
            "input": user_input,
            "chat_history": history
        }

        for event in agent_executor.stream(input_dict):
            if "actions" in event:
                yield "🔍 正在查询帽儿山数据...\n\n"

            if "output" in event:
                yield event["output"]

    except Exception:
        yield "⚠️ 智能助手暂时无法响应，请稍后再试。"