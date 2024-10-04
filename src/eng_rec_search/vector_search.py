import logging
import os

import streamlit as st
from databricks.vector_search.client import VectorSearchClient
from databricks.vector_search.index import VectorSearchIndex
from pydantic import BaseModel

from custom_mocks import MockVectorSearcher
from eng_rec_search.constants import SUMMARY_COL, ENDPOINT_NAME, CATALOG_NAME, SCHEMA_NAME, INDEX_NAME

logger = logging.getLogger(__name__)

TABLE_COLS = [
    "issue_id",
    "Market",
    "Site",
    "Title",
    "OpeningComment",
    "ClosingComment",
    "Turbines",
    "Comments",
    "Subsystem",
    SUMMARY_COL,
]

DETAILS_COLS = [
    "Market",
    "Site",
    "Title",
    "OpeningComment",
    "ClosingComment",
    "Comments",
    "Turbines",
    "Subsystem",
]


class SimilarIssue(BaseModel):
    issue_id: float
    market: str
    site: str
    title: str
    opening_comment: str
    closing_comment: str
    turbines: str
    comments: str | None
    subsystem: str
    summary: str
    score: float

    @classmethod
    def from_search_result(cls, search_result: list) -> "SimilarIssue":
        return cls(**{k: v for k, v in zip(cls.__fields__.keys(), search_result)})  # type: ignore

    def get_tags(self) -> list[tuple[str, str]]:
        return [
            (str(self.issue_id), "Issue ID"),
            (self.market, "Market"),
            (self.site, "Site"),
            (self.turbines, "Turbines"),
            (self.subsystem, "Subsystem"),
        ]


class VectorSearcher:
    def __init__(self, workspace_url: str, sp_client_id: str, sp_client_secret: str):
        self.index = self._get_vector_index(workspace_url, sp_client_id, sp_client_secret)

    @staticmethod
    def _get_vector_index(workspace_url: str, sp_client_id: str, sp_client_secret: str) -> VectorSearchIndex:
        vsc = VectorSearchClient(
            workspace_url=workspace_url,
            service_principal_client_id=sp_client_id,
            service_principal_client_secret=sp_client_secret,
        )
        return vsc.get_index(
            endpoint_name=ENDPOINT_NAME,
            index_name=f"{CATALOG_NAME}.{SCHEMA_NAME}.{INDEX_NAME}",
        )

    def search(self, query: str, num_results: int = 5) -> dict:
        return self.index.similarity_search(query_text=query, columns=TABLE_COLS, num_results=num_results)


@st.cache_resource
def get_vector_searcher() -> VectorSearcher | MockVectorSearcher:
    if os.getenv("DEBUG", "0") == "1":
        logger.warning("Using mock vector searcher")
        return MockVectorSearcher()
    return VectorSearcher(
        workspace_url=os.environ["WORKSPACE_URL"],
        sp_client_id=os.environ["SP_CLIENT_ID"],
        sp_client_secret=os.environ["SP_CLIENT_SECRET"],
    )
