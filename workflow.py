import os
from typing import TYPE_CHECKING, Any, Iterator, Literal, TypedDict
from uuid import uuid4

from dotenv import load_dotenv
from httpx import ConnectError
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from pydantic import BaseModel

from agents import chart_agent, data_manager, plot_summary_agent, sql_agent

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langchain_core.runnables import RunnableConfig


load_dotenv()


def test_langfuse_connection():
    langfuse = get_client()

    # TODO: logging instead of print
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
        return True
    else:
        print("Authentication failed. Please check your credentials and host.")
        return False


class PlotData(BaseModel):
    data_path: str | None = None
    data_columns: list[str] = []
    data_head: str | None = None
    plot_path: str | None = None
    plot_caption: str = ""


class State(TypedDict):
    """State class for the graph"""

    unique_id: str
    user_query: str
    sql_query: str
    data_query: str
    plot_data: PlotData
    plot_summary: str


def sql_node(state: State) -> Command[Literal["extract_data"]]:
    user_query = state.get("user_query", "")
    if not user_query:
        raise ValueError("Query can't be empty")

    sql = sql_agent.invoke(user_query)

    return Command(
        update={
            "sql_query": sql.query,
            "data_query": user_query,
        },
        goto="extract_data",
    )


def extract_data_node(state: State) -> Command[Literal["plot"]]:
    data_path = data_manager.get_data_and_save(
        state.get("sql_query", ""), state.get("unique_id")
    )

    return Command(
        update={
            "plot_data": PlotData(
                data_path=data_path,
                data_columns=data_manager.data.columns.to_list(),
            ),
        },
        goto="plot",
    )


def plot_node(state: State) -> Command[Literal["plot_summarizer"]]:
    plot_path = chart_agent.invoke(state)
    plot_data = state.get("plot_data")
    plot_data.plot_path = plot_path

    return Command(
        update={
            "plot_data": plot_data,
        },
        goto="plot_summarizer",
    )


def plot_summarizer_node(state: State) -> Command[Literal[END]]:  # type: ignore

    result = plot_summary_agent.invoke(state)
    plot_data = state.get("plot_data")
    plot_data.plot_caption = result.caption

    return Command(
        update={
            "plot_summary": result.summary,
            "plot_data": plot_data,
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
    graph.add_node("extract_data", extract_data_node)
    graph.add_node("plot", plot_node)
    graph.add_node("plot_summarizer", plot_summarizer_node)

    graph.add_edge(START, "sql_generator")

    return graph.compile(checkpointer=memory)


def create_config(thread_id: str | None = None) -> "RunnableConfig":
    if thread_id is None:
        thread_id = str(uuid4())

    config: "RunnableConfig" = {
        "configurable": {"thread_id": thread_id},
    }

    try:
        langfuse_connected = test_langfuse_connection()
        if langfuse_connected:
            config["callbacks"] = [CallbackHandler()]
        else:
            # TODO: logging instead of print
            print("Can't connect to Langfuse, tracing will be disabled.")
            os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
    except ConnectError as e:
        print("Connection error, tracing will be disabled!")
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"

    return config
