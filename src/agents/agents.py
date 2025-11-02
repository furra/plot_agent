import base64
import os
import pickle

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from baml_client.sync_client import b
from baml_client.types import PlotSummary, SQLQuery
from baml_py import Image
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import init_chat_model

from langfuse import observe
from langfuse.langchain import CallbackHandler
from pandas import DataFrame

from .tests.agents import (
    PlotSummaryTestAgent,
    PlotTestAgent,
    SQLTestAgent,
    TestDataManager,
)
from src.tools import get_schema, python_repl_tool, run_sql


load_dotenv()

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

if TYPE_CHECKING:
    from langchain.agents.agent import AgentExecutor
    from langgraph.graph.state import CompiledStateGraph
    from src.workflow import State


class SQLAgent:
    """This agent converts the text query to a SQL query"""

    @observe(name="sql-agent", as_type="generation")
    def invoke(self, query: str, engine: str = "sqlite") -> SQLQuery:
        return b.GenerateSQLQuery(
            query,
            get_schema(),
            engine,
        )


sql_agent = SQLTestAgent() if TEST_MODE else SQLAgent()


class DataManager:
    """This manager retrieves data from the database and handles data serialization"""

    sql: str = ""
    data: DataFrame

    def save_data(self, uid: str) -> str:
        path = str(self.generate_data_path(uid))
        with open(path, "wb") as f:
            pickle.dump(self.data, f)
        return path

    def generate_data_path(self, uid: str) -> Path:
        path = Path(f"/tmp/data_{uid}.pkl").resolve()
        return path

    def get_data_and_save(self, query: str, uid: str) -> str:
        if not query:
            raise ValueError(f"SQL query is empty")
        self.sql = query
        self.data = run_sql(self.sql)
        data_path = self.save_data(uid)
        return data_path


data_manager = TestDataManager() if TEST_MODE else DataManager()


# TODO: check BAML tool calling
class PlotAgent:
    llm: "AgentExecutor | CompiledStateGraph"
    prompt: str = (
        "You are a plotting agent that uses plotly and seaborn to generate plots."
        "You are working with a data extractor colleague. You will be given a pickled DataFrame file path to plot. "
        "The user will give you the instructions of the plot or a query that the plot should answer.\n\n"
        "You are NOT allowed to transform or aggregate data in any way. "
        "The DataFrame is already processed and ready for visualization. "
        "Do NOT call pandas methods such as groupby, pivot, or apply. "
        "Use the existing columns directly for plotting.\n\n"
        "Generate one plot file; you can do a multiplot if it applies. "
        "If the user's query is too complex, focus on the main question.\n\n"
        "Generate the plot first, then save the plot to a file (png) in the same folder that the data file is and "
        "provide its path in your final output, e.g., `Final Answer: /path/to/plot/file.png` (without the backticks).\n"
        "Choose a name for the plot and include the user's unique_id in the file name, e.g., `boxplot_categories_{unique_id}.png`"
    )
    data_columns: list[str]

    def __init__(self, provider: Literal["google", "groq"] = "google") -> None:
        callback = CallbackHandler()

        # TODO: look another alternative, it will be deprecated
        agent = initialize_agent(
            [python_repl_tool],
            init_chat_model("gemini-2.5-flash", model_provider="google_genai"),
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            callbacks=[callback],
        )

        self.llm = agent

    def _prepare_input(self, state: "State") -> dict[str, Any]:
        return {
            "input": (
                f"{self.prompt}\n"
                f"File is located at `{state.get("plot_data").data_path}`\n"
                f"Data columns: {state.get("plot_data").data_columns}"
                f"User's query:\n{state.get("data_query")}"
                f"User unique id:\n{state.get("unique_id")}"
            )
        }

    @observe(name="plot-agent", as_type="generation")
    def invoke(self, state: "State") -> str:
        llm_input = self._prepare_input(state)
        llm_response = self.llm.invoke(llm_input)

        response_content = llm_response["output"]

        return response_content


plot_agent = PlotTestAgent() if TEST_MODE else PlotAgent()


class PlotSummaryAgent:
    """This agent analyzes and summarizes a plot"""

    def _get_base64_img(self, path_str: str | None) -> Image:
        if not isinstance(path_str, str):
            raise TypeError(f"Variable plot_path {path_str} is not a valid str")

        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"File {path_str} doesn't exist")

        if path.is_dir():
            raise IsADirectoryError(f"File {path_str} is a directory, not a file.")

        with open(path_str, "rb") as image_file:
            image_b64 = image_file.read()
            return Image.from_base64(
                "image/png", base64.b64encode(image_b64).decode("utf-8")
            )

    @observe(name="sql-agent", as_type="generation")
    def invoke(self, state: "State") -> PlotSummary:
        img = self._get_base64_img(state.get("plot_data").plot_path)
        return b.GeneratePlotSummary(
            img,
            state.get("data_query"),
        )


plot_summary_agent = PlotSummaryTestAgent() if TEST_MODE else PlotSummaryAgent()
