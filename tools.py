import pickle

from pandas import DataFrame
from pydantic import BaseModel, ConfigDict
from typing import Annotated

# from langchain.tools import Tool
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from sqlalchemy import create_engine, Row, text


class PlotData(BaseModel):
    data: DataFrame
    data_path: str | None = None
    plot_path: str | None = None

    # TODO: validate DataFrame
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def save_to_path(self, path: str):
        self.data_path = path
        with open(path, "wb") as f:
            pickle.dump(self.data, f)

# Add this to the agent
engine = create_engine("sqlite:///data/database.db")

def run_sql(query: str):
    """Executes validated SQL on the database"""
    with engine.connect() as conn:
        result = conn.execute(text(query))
        columns = list(result.keys())
        data = result.fetchall()

        return PlotData(data=DataFrame(data, columns=columns))


def get_schema():
    """Gets information on the schema as context for the LLM"""
    with engine.connect() as conn:
        schema = conn.execute(text("PRAGMA table_info(purchases);")).fetchall()
        # add metainfo on each column
        return f'Table: "purchases":\n{schema}'


repl = PythonREPL()

# for not gemini models
@tool
def python_repl_tool(
    code: Annotated[str, "Python code to execute that generate a plot."],
):
    """Use this to execute python code. You will be used to execute python code
    that generates plots. Only print the plot once.
    This is visible to the user."""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"

    return f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"

# for gemini
# def gemini_repl_tool(code: str) -> str:
#     try:
#         result = repl.run(code)
#     except BaseException as e:
#         return f"Failed to execute. Error: {repr(e)}"

#     return f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"

# python_repl_tool = Tool(
#     name="Python REPL",
#     description="Executes Python code that generates and prints a plot. Use seaborn or plotly and only print the plot once. Save plots under `.data/`.",
#     func=gemini_repl_tool,
# )
