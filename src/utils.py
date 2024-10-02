import numpy as np
import plotly
from plotly import figure_factory as ff

# from __ignore__.mock_vector_search import MockVectorSearcher as VectorSearcher


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
