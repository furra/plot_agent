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
from langchain_core.messages import AIMessage, HumanMessage

from langfuse import observe
from langfuse.langchain import CallbackHandler
from langgraph.prebuilt import create_react_agent
from pandas import DataFrame

from tools import get_schema, python_repl_tool_react, python_repl_tool, run_sql

load_dotenv()

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

if TYPE_CHECKING:
    from langchain.agents.agent import AgentExecutor
    from langgraph.graph.state import CompiledStateGraph
    from workflow import State


class SQLAgent:
    """This agent converts the text query to a SQL query"""

    @observe(name="sql-agent", as_type="generation")
    def invoke(self, query: str, engine: str = "sqlite") -> SQLQuery:
        if TEST_MODE:
            return SQLQuery(
                query="SELECT category, COUNT(*) FROM purchases GROUP BY category;",
            )
        return b.GenerateSQLQuery(
            query,
            get_schema(),
            engine,
        )


sql_agent = SQLAgent()


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
        path = Path(f"data/data_{uid}.pkl").resolve()
        return path

    def get_data_and_save(self, query: str, uid: str) -> str:
        if TEST_MODE:
            return self.get_data_test(query, uid)
        if not query:
            raise ValueError(f"SQL query is empty")
        self.sql = query
        self.data = run_sql(self.sql)
        data_path = self.save_data(uid)
        return data_path

    def get_data_test(self, query: str, uid: str) -> str:
        self.sql = query
        path = Path("tests/data/data_12345.pkl").resolve()
        with open(path, "rb") as file:
            self.data = pickle.load(file)
        return str(path)


data_manager = DataManager()


# TODO: check BAML tool calling
class PlotAgent:
    llm: "AgentExecutor | CompiledStateGraph"
    provider: Literal["google", "groq"] = "google"
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
        supported_providers = {"groq", "google"}
        if provider not in supported_providers:
            # TODO: Log this
            return
        if provider == "groq":
            agent = create_react_agent(
                init_chat_model("qwen/qwen3-32b", model_provider="groq"),
                [python_repl_tool_react],
                prompt=self.prompt,
            )
            self.provider = provider
        elif provider == "google":
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
        if self.provider == "google":
            llm_input = {
                "input": (
                    f"{self.prompt}\n"
                    f"File is located at `{state.get("plot_data").data_path}`\n"
                    f"Data columns: {state.get("plot_data").data_columns}"
                    f"User's query:\n{state.get("data_query")}"
                    f"User unique id:\n{state.get("unique_id")}"
                )
            }
        elif self.provider == "groq":
            llm_input = {
                "messages": [
                    HumanMessage(
                        content=state.get("data_query"),
                        name="user",
                    ),
                    AIMessage(
                        content=str(state.get("plot_data").plot_path),
                        name="data_agent",
                    ),
                ]
            }
        else:
            # TODO: log this
            llm_input = {}
        return llm_input

    def _extract_output(self, llm_response: dict[str, Any]) -> str:
        if self.provider == "google":
            output = llm_response["output"]
        elif self.provider == "groq":
            # TODO: check react agent response
            output = llm_response["messages"][-1].content
        else:
            # TODO: log this
            output = ""
        return output

    @observe(name="plot-agent", as_type="generation")
    def invoke(self, state: "State") -> str:
        if TEST_MODE:
            return self.plot_path_test(state)
        llm_input = self._prepare_input(state)
        llm_response = self.llm.invoke(llm_input)

        response_content = self._extract_output(llm_response)

        return response_content

    def plot_path_test(self, state: "State") -> str:
        return str(Path("tests/data/plot_12345.png").resolve())


chart_agent = PlotAgent()


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
        if TEST_MODE:
            return PlotSummary(
                summary=(
                    "Among various product categories, clothing items are the most numerous, with approximately "
                    "1700 instances. Accessories represent the second-largest category, totaling around 1200 "
                    "instances. Footwear has a count of about 600, while outerwear is the least frequent category, "
                    "with roughly 350 instances. This distribution suggests a significantly higher volume or demand "
                    "for clothing and accessories compared to footwear and outerwear."
                ),
                caption="Distribution of item counts across different product categories.",
            )
        img = self._get_base64_img(state.get("plot_data").plot_path)
        return b.GeneratePlotSummary(
            img,
            state.get("data_query"),
        )


plot_summary_agent = PlotSummaryAgent()
