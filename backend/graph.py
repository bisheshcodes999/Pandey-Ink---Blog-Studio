"""Builds and compiles the full pipeline.

    router -> (research?) -> orchestrator -> [worker, ...] -> reducer

`reducer` is itself a subgraph:

    merge_content -> fact_check -> critic -> decide_images ->
    generate_and_place_images -> repurpose

Node names matter to the frontend (NODE_LABELS / NODE_ORDER_HINT in
bwa_frontend.py use them for the pipeline tracker), so keep them in
sync if any of these get renamed.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.nodes.orchestrator import fanout, orchestrator_node
from backend.nodes.research import research_node
from backend.nodes.router import route_next, router_node
from backend.nodes.worker import worker_node
from backend.reducer.critic import critic_node
from backend.reducer.fact_check import fact_check_node
from backend.reducer.images import decide_images, generate_and_place_images
from backend.reducer.merge import merge_content
from backend.reducer.repurpose import repurpose_node
from backend.state import State


def _build_reducer_subgraph():
    reducer_graph = StateGraph(State)
    reducer_graph.add_node("merge_content", merge_content)
    reducer_graph.add_node("fact_check", fact_check_node)
    reducer_graph.add_node("critic", critic_node)
    reducer_graph.add_node("decide_images", decide_images)
    reducer_graph.add_node("generate_and_place_images", generate_and_place_images)
    reducer_graph.add_node("repurpose", repurpose_node)

    reducer_graph.add_edge(START, "merge_content")
    reducer_graph.add_edge("merge_content", "fact_check")
    reducer_graph.add_edge("fact_check", "critic")
    reducer_graph.add_edge("critic", "decide_images")
    reducer_graph.add_edge("decide_images", "generate_and_place_images")
    reducer_graph.add_edge("generate_and_place_images", "repurpose")
    reducer_graph.add_edge("repurpose", END)

    return reducer_graph.compile()


def _build_graph():
    graph = StateGraph(State)
    graph.add_node("router", router_node)
    graph.add_node("research", research_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("worker", worker_node)
    graph.add_node("reducer", _build_reducer_subgraph())

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
    graph.add_edge("research", "orchestrator")

    graph.add_conditional_edges("orchestrator", fanout, ["worker"])
    graph.add_edge("worker", "reducer")
    graph.add_edge("reducer", END)

    return graph.compile()


app = _build_graph()
