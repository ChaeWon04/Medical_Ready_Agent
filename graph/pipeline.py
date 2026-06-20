from langgraph.graph import StateGraph, END
from typing import TypedDict
from schemas.ai_ready_schema import AIReadyRecord
import agents.agent2_reflexion as agent2
import agents.agent3_annotator as agent3


class PipelineState(TypedDict):
    record: AIReadyRecord
    done: bool


def _node_agent2(state: PipelineState) -> PipelineState:
    state["record"] = agent2.run(state["record"])
    return state


def _node_agent3(state: PipelineState) -> PipelineState:
    state["record"] = agent3.run(state["record"])
    state["done"] = True
    return state


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("agent2", _node_agent2)
    g.add_node("agent3", _node_agent3)
    g.set_entry_point("agent2")
    g.add_edge("agent2", "agent3")
    g.add_edge("agent3", END)
    return g.compile()


graph = build_graph()


def run_pipeline(record: AIReadyRecord) -> AIReadyRecord:
    result = graph.invoke({"record": record, "done": False})
    return result["record"]
