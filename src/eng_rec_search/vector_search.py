from databricks.vector_search.client import VectorSearchClient
from databricks.vector_search.index import VectorSearchIndex


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
            endpoint_name="eng_rec_vector_search_endpoint",
            index_name="workspace_innovation_db.default.sample_eng_rec_content_index",
        )

    def search(self, query: str, num_results: int = 5) -> dict:
        return self.index.similarity_search(
            query_text=query, columns=["primary_key", "content"], num_results=num_results
        )
