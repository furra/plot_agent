from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt

from src.agents import data_manager, plot_agent, plot_summary_agent, sql_agent
from src.workflow import PlotData, State

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


load_dotenv()


def sql_node(state: State) -> Command[Literal["user_confirm_sql"]]:
    query = state.get("user_query", "")
    if not query:
        raise ValueError("Query can't be empty")

    sql = sql_agent.invoke(query)
    return Command(
        update={"sql_query": sql.query},
        goto="user_confirm_sql",
    )


def user_confirm_sql_node(state: State) -> Command[Literal["extract_data", END]]:  # type: ignore
    """This node intentionally pauses execution for user to confirm the SQL query generated"""

    is_approved = interrupt(
        f"Generated SQL query:\n{state["sql_query"]}\nDo you want to continue? (yes/no) "
    ).lower() in {"yes", "y", "ye", "yeah", "sure"}

    if is_approved:
        return Command(goto="extract_data")
    return Command(goto=END)


def extract_data_node(state: State) -> Command[Literal["user_confirm_data"]]:
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
        goto="user_confirm_data",
    )


def user_confirm_data_node(state: State) -> Command[Literal["data_query", END]]:  # type: ignore
    """This node intentionally pauses execution for user to confirm the the extracted data"""

    is_approved = interrupt(
        f"First five rows of the data:\n```{data_manager.data.head()}\n```\nDo you want to continue? (yes/no)"
    ).lower() in {"yes", "y", "ye", "yeah", "sure"}

    if is_approved:
        return Command(goto="data_query")
    return Command(goto=END)


def data_query_node(state: State) -> Command[Literal["plot", END]]:  # type: ignore
    """This node prompts the user for information on the extracted data or terminate"""

    data_query: str = interrupt(
        f"Write intructions for the data plot. Leave empty for original query: \\`{state.get("user_query")}\\`\nType 'quit' or 'stop' to exit."
    ).strip()

    if data_query.lower() in ["quit", "stop", "end", "finish"]:
        return Command(goto=END)

    plot_data = state.get("plot_data")
    plot_data.plot_caption = ""

    return Command(
        update={
            "data_query": data_query if data_query else state.get("user_query"),
            "plot_summary": "",
            "plot_data": plot_data,
        },
        goto="plot",
    )


def plot_node(state: State) -> Command[Literal["plot_summarizer"]]:
    plot_path = plot_agent.invoke(state)
    plot_data = state.get("plot_data")
    plot_data.plot_path = plot_path

    return Command(
        update={
            "plot_data": plot_data,
        },
        goto="plot_summarizer",
    )


def plot_summarizer_node(state: State) -> Command[Literal["data_query"]]:

    result = plot_summary_agent.invoke(state)
    plot_data = state.get("plot_data")
    plot_data.plot_caption = result.caption

    return Command(
        update={
            "plot_summary": result.summary,
            "plot_data": plot_data,
        },
        goto="data_query",
    )


def initialize_graph() -> "CompiledStateGraph":
    """Creates graph workflow"""
    memory = InMemorySaver()
    graph = StateGraph(State)

    graph.add_node("sql_generator", sql_node)
    graph.add_node("user_confirm_sql", user_confirm_sql_node)
    graph.add_node("extract_data", extract_data_node)
    graph.add_node("user_confirm_data", user_confirm_data_node)
    graph.add_node("data_query", data_query_node)
    graph.add_node("plot", plot_node)
    graph.add_node("plot_summarizer", plot_summarizer_node)

    graph.add_edge(START, "sql_generator")

    return graph.compile(checkpointer=memory)
