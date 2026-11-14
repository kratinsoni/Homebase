import json
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END

from worker.llm.adapter import ModelAdapter
from worker.tools.mcp.manager import MCPManager

SYSTEM = {
    "role": "system",
    "content": "You are Homebase, an assistant that does tasks for the user. "
               "Use the tools to get facts. Work only inside the user's workspace.",
}

class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]

def build_graph(adapter: ModelAdapter, tools=MCPManager, checkpointer=None):

    async def agent_node(state: AgentState):
        reply = await adapter.chat([SYSTEM] + state["messages"], tools=tools.schemas)
        return {"messages": [reply.model_dump(exclude_none=True)]}

    async def tools_node(state: AgentState):
        results = []
        for call in state["messages"][-1]["tool_calls"]:
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
                result = await tools.call(call["function"]["name"], args)
            except Exception as e:
                result = f"Error: {e}"
            results.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        return {"messages": results}

    def route(state: AgentState):
        return "tools" if state["messages"][-1].get("tool_calls") else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)