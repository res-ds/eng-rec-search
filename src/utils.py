import os
from dataclasses import dataclass

import numpy as np
import plotly
import streamlit as st
from plotly import figure_factory as ff

# from __ignore__.mock_vector_search import MockVectorSearcher as VectorSearcher
from eng_rec_search.vector_search import VectorSearcher


def _mock_chart() -> plotly.graph_objs.Figure:
    np.random.seed(42)
    # Add histogram data
    x1 = np.random.randn(200) - 2
    x2 = np.random.randn(200)
    x3 = np.random.randn(200) + 2

    # Group data together
    hist_data = [x1, x2, x3]

    group_labels = ["Turbine 1", "Turbine 2", "Turbine 3"]

    # Create distplot with custom bin_size
    fig = ff.create_distplot(hist_data, group_labels, bin_size=[0.1, 0.25, 0.5])
    fig.update_layout(height=400)
    return fig


@st.cache_resource
def _get_vector_searcher() -> VectorSearcher:
    return VectorSearcher(
        workspace_url=os.environ["WORKSPACE_URL"],
        sp_client_id=os.environ["SP_CLIENT_ID"],
        sp_client_secret=os.environ["SP_CLIENT_SECRET"],
    )


@dataclass
class SimilarIssue:
    title: str
    content: str
    tags: list[dict]


def _parse_issue_tuple(issue_tuple: str) -> SimilarIssue:
    _, title, body = issue_tuple[1].split("#", 2)
    return SimilarIssue(
        title=title.strip(),
        content=body.strip(),
        tags=[{issue_tuple[0].split("-")[0].strip(): "site name"}, {issue_tuple[0].split("-")[1]: "issue no."}],
    )
