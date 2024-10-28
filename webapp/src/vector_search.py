import logging
import os
from collections.abc import Sequence

import streamlit as st
from databricks.vector_search.client import VectorSearchClient
from pydantic import BaseModel

from src.resources import get_vector_search_client

logger = logging.getLogger(__name__)


INDEX_PRIMARY_KEY = os.environ["INDEX_PRIMARY_KEY"]
INDEX_NAME = os.environ["INDEX_NAME"]
INDEX_ENDPOINT_NAME = os.environ["INDEX_ENDPOINT_NAME"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]
N_SIMILAR_ISSUES = int(os.getenv("N_SIMILAR_ISSUES", 5))
TABLE_COLS = ("Id", "Market", "Site", "Turbine", "Original", "Summary")


class SimilarIssue(BaseModel):
    id: float
    market: str
    site: str
    turbine: str
    original: str
    summary: str
    score: float

    def get_tags(self) -> list[tuple[str, str]]:
        return [
            (str(self.id), "Issue ID"),
            (self.market, "Market"),
            (self.site, "Site"),
            (self.turbine, "Turbine"),
        ]


class VectorSearcher:
    def __init__(self, vector_search_client: VectorSearchClient):
        self.index = vector_search_client.get_index(endpoint_name=INDEX_ENDPOINT_NAME, index_name=INDEX_NAME)

    def search(
        self, query: str, cols: Sequence[str] = TABLE_COLS, num_results: int = N_SIMILAR_ISSUES
    ) -> list[SimilarIssue]:
        _search_results = self.index.similarity_search(query_text=query, columns=cols, num_results=num_results)
        _cols = [i["name"] for i in _search_results["manifest"]["columns"]]
        _fields = SimilarIssue.model_fields.keys()
        assert tuple(i.lower() for i in _cols) == tuple(_fields), f"Mismatched columns: {_cols} != {_fields}"

        return [
            SimilarIssue(**{k: v for k, v in zip(_fields, _issue_data)})
            for _issue_data in _search_results["result"]["data_array"]
        ]


@st.cache_resource
def get_vector_searcher() -> VectorSearcher:
    if os.getenv("DEBUG", "0") == "1":
        logger.warning("Using mock vector searcher")
        from src.custom_mocks import MockVectorSearcher

        return MockVectorSearcher()  # type: ignore

    return VectorSearcher(vector_search_client=get_vector_search_client())
