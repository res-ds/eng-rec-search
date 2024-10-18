import numpy as np
import plotly
from plotly import figure_factory as ff

from src.vector_search import SimilarIssue


def mock_chart() -> plotly.graph_objs.Figure:
    np.random.seed(42)

    x1 = np.random.randn(200) - 2
    x2 = np.random.randn(200)
    x3 = np.random.randn(200) + 2

    hist_data = [x1, x2, x3]
    group_labels = ["Turbine 1", "Turbine 2", "Turbine 3"]

    fig = ff.create_distplot(hist_data, group_labels, bin_size=[0.1, 0.25, 0.5])
    fig.update_layout(height=400)
    return fig


SAMPLE_SEARCH_RESULTS = [
    SimilarIssue(
        id=9.0,
        market="US",
        site="Windwhisper Park",
        turbine="T29",
        original="# Pitch motor overtemperature alarms",
        summary="### Symptoms:\nThe pitch motor",
        score=0.0028252013,
    ),
    SimilarIssue(
        id=8.0,
        market="Australia",
        site="Galeforce Energy Center",
        turbine="T13",
        original="# Pitch motor overtemperature",
        summary="### Symptoms:\nHigh and frequent",
        score=0.0027907745,
    ),
    SimilarIssue(
        id=11.0,
        market="US",
        site="Sirocco Fields Energy",
        turbine="T28",
        original="# Pitch motor overtemperature",
        summary="### Symptoms:\nOvertemperature",
        score=0.0027659389,
    ),
]


class MockVectorSearcher:
    def search(self, query: str, num_results: int = 5) -> list[SimilarIssue]:
        return SAMPLE_SEARCH_RESULTS
