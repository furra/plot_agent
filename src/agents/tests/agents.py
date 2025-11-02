from pathlib import Path
import pickle
from typing import TYPE_CHECKING
from pandas import DataFrame
from baml_client.types import PlotSummary, SQLQuery

if TYPE_CHECKING:
    from src.workflow import State


class SQLTestAgent:
    """This agent is used for testing"""

    def invoke(self, _query: str, _engine: str = "sqlite") -> SQLQuery:
        return SQLQuery(
            query="SELECT category, COUNT(*) FROM purchases GROUP BY category;",
        )


class TestDataManager:
    """This manager is used for testing"""

    sql: str = ""
    data: DataFrame

    def get_data_and_save(self, query: str, _uid: str) -> str:
        self.sql = query
        path = Path("tests/data/data_12345.pkl").resolve()
        with open(path, "rb") as file:
            self.data = pickle.load(file)
        return str(path)


class PlotTestAgent:
    """This agent is used for testing"""

    def invoke(self, _state: "State") -> str:
        return str(Path("tests/data/plot_12345.png").resolve())


class PlotSummaryTestAgent:
    """This agent analyzes and summarizes a plot"""

    def invoke(self, _state: "State") -> PlotSummary:
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
