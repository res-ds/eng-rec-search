import numpy as np
import plotly
from plotly import figure_factory as ff


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


SAMPLE_SEARCH_ROW = [
    0.0,
    "UK & Ireland",
    "Site 1",
    "Hydraulic oil temperature",
    "The Pitch Hydraulic oil temperatures were observed to have increased 8 degrees ...",
    "Valve was exchanged on 09/05 which caused the oil temps to drop down to the site level.",
    "ST1_T03",
    "10 Nov 2017 - A service order has been received from May 2017 that shows that Vestas ...",
    "WTG Forced - Hub/Pitch System",
    "### Symptoms:\nThe Pitch Hydraulic oil temperatures increased 8 degrees above SITE average...\n\n"
    "### Recommendation:\nIt is recommended that OEM investigate ...\n\n"
    "### Resolution:\nThe faulty valve was exchanged...",
    0.004,
]


class MockVectorSearcher:
    def search(self, query: str, num_results: int = 5) -> dict:
        def _make_sample_search_row(title: str) -> list:
            _new_row = SAMPLE_SEARCH_ROW.copy()
            _new_row[3] = title
            return _new_row

        return {
            "result": {
                "data_array": [
                    _make_sample_search_row("Pitch hydraulic oil issue"),
                    _make_sample_search_row("Some other issue 1"),
                    _make_sample_search_row("Some other issue 2"),
                    _make_sample_search_row("Some other issue 3"),
                    _make_sample_search_row("Some other issue 4"),
                ]
            }
        }
