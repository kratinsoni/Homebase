from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import interrupt

from worker.tools.mcp.manager import MCPManager

SYSTEM = SystemMessage(
    "You are Homebase, an assistant that does tasks for the user. "
    "Use the tools to get facts. Work only inside the user's workspace."
)

RISKY_TOOLS = {"write_file"}

def merge_dicts(old: dict | None, new: dict) -> dict | None:
    return {**(old or {}), **new}

class AgentState(MessagesState):
    approvals: Annotated[dict[str, bool], merge_dicts]

def build_graph(model: BaseChatModel, tools: MCPManager, checkpointer=None):
    model_with_tools = model.bind_tools(tools.schemas)

    async def agent_node(state: AgentState):
        response = await model_with_tools.ainvoke([SYSTEM] + state["messages"])
        return {"messages": [response]}

    async def tools_node(state: AgentState):
        approvals = state["approvals"] or {}
        results = []
        for call in state["messages"][-1].tool_calls:
            if call["name"] in RISKY_TOOLS and not approvals[call["id"]]:
                result = "The user rejected this action. Do not try it again unless the user asks."
            else:
                try:
                    result = await tools.call(call["name"], call["args"])
                except Exception as e:
                    result = f"Error: {e}"
            results.append(ToolMessage(content=result, tool_call_id=call["id"], name=call["name"]))
        return {"messages": results}

    def route(state: AgentState):
        calls = state["messages"][-1].tool_calls
        if not calls:
            return END
        if any(c["name"] in RISKY_TOOLS for c in calls):
            return "approval"
        return "tools"

    def approval_node(state: AgentState):
        calls = [c for c in state["messages"][-1].tool_calls if c["name"] in RISKY_TOOLS]

        decision = interrupt({
            "calls": [{"id": c["id"], "name": c["name"], "args": c["args"]} for c in calls]
        })

        approved = bool(decision.get("approved"))

        return {"approvals": {c["id"]: approved for c in calls}}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("approval", approval_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, ["tools", "approval", END])
    graph.add_edge("tools", "agent")
    graph.add_edge("approval", "tools")
    return graph.compile(checkpointer=checkpointer)