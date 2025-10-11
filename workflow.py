from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Literal, TypedDict
from uuid import uuid4

from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage
# from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from pandas import DataFrame

from agents import chart_agent, plot_summary_agent, sql_agent
from tools import PlotData, run_sql

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langchain_core.runnables import RunnableConfig


load_dotenv()


class State(TypedDict):
    """State class for the graph"""
    messages: list[BaseMessage] # just for testing
    user_query: str
    sql_query: str
    plot_data: PlotData
    plot_summary: str


def sql_node(state: State) -> Command[Literal["query_data"]]:
    messages = state.get("messages", [])

    assert messages
    assert isinstance(messages[0].content, str)

    query = messages[0].content
    # query = state.get("user_query", "")
    # assert query

    sql = sql_agent.invoke(query)

    return Command(
        update={
            "messages": state.get("messages", [])
            + [HumanMessage(content=sql.query, name="sql")],
            "sql_query": sql.query,
        },
        goto="query_data",
    )


def query_data_node(state: State) -> Command[Literal["plot"]]:
    data = run_sql(state.get("sql_query", ""))
    # TODO: generate unique path
    path = str(Path("data/queried_data.pkl").resolve())
    data.save_to_path(path)

    return Command(
        update={
            "messages": state.get("messages") + [
                HumanMessage(
                    content=f"Plot the dataset at {path}"
                )
            ],
            "plot_data": data,
        },
        goto="plot",
    )


def plot_node(state: State) -> Command[Literal["plot_summarizer"]]:
    result = chart_agent.invoke(state)

    breakpoint()
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="plot",
    )

    return Command(
        update={
            "messages": state.get("messages", []) + result["messages"],
        },
        goto="plot_summarizer",
    )


def plot_summarizer_node(state: State) -> Command[Literal[END]]:  # type: ignore

    breakpoint()
    result = plot_summary_agent.invoke(state)

    breakpoint()
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="plot_summarizer",
    )

    return Command(
        update={
            "messages": state.get("messages", []) + result["messages"],
            "final_answer": result["messages"][-1].content,
        },
        goto=END,
    )


def save_diagram_image(workflow: "CompiledStateGraph", image_name: str = "diagram.png"):
    """Saves agent's workflow diagram in a png image"""
    image_bytes = workflow.get_graph().draw_mermaid_png()

    with open(image_name, "wb") as file:
        file.write(image_bytes)


def initialize_graph() -> "CompiledStateGraph":
    """Creates graph workflow"""
    memory = InMemorySaver()
    graph = StateGraph(State)

    graph.add_node("sql_generator", sql_node)
    graph.add_node("query_data", query_data_node)
    graph.add_node("plot", plot_node)
    graph.add_node("plot_summarizer", plot_summarizer_node)

    graph.add_edge(START, "sql_generator")

    return graph.compile(checkpointer=memory)


def stream(
    graph: "CompiledStateGraph",
    user_input: str,
    thread_id: str | None = None,
) -> Iterator[dict[str, Any] | Any]:
    """Streams user input to the graph and returns all messages"""
    if thread_id is None:
        thread_id = str(uuid4())

    # test method before tracing
    # langfuse_handler = CallbackHandler()

    config: "RunnableConfig" = {
        "configurable": {"thread_id": thread_id},
        # "callbacks": [langfuse_handler]
    }

    # return list of messages
    return graph.stream(
        # {"user_query": user_input},
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
        },
        config,
        stream_mode="values",
    )


"""
from langfuse import get_client

langfuse = get_client()

# Verify connection
if langfuse.auth_check():
    print("Langfuse client is authenticated and ready!")
else:
    print("Authentication failed. Please check your credentials and host.")
"""
