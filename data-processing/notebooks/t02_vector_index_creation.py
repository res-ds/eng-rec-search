import contextlib
import logging
from base64 import b64decode

from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient
from databricks.vector_search.index import VectorSearchIndex

SOURCE_TABLE = "workspace.default.summarized_tracked_issues"
PRIMARY_KEY = "Id"
EMBEDDING_SOURCE_COLUMN = "Summary"

ENDPOINT_NAME = "eng_rec_endpoint"
INDEX_NAME = "eng_rec_index"
EMBEDDING_MODEL = "databricks-gte-large-en"
INDEX_PIPELINE_TYPE = "TRIGGERED"
FORCE_RECREATE = False

DATABRICKS_TOKEN_SECRET = dict(scope="eng-rec-scope", key="databricks-token")


def _get_dbx_secret(workspace_client: WorkspaceClient, scope: str, key: str) -> str:
    _encoded_secret = workspace_client.secrets.get_secret(scope=scope, key=key).value
    assert isinstance(_encoded_secret, str)  # mypy fix
    return b64decode(_encoded_secret).decode()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    w = WorkspaceClient()
    DATABRICKS_TOKEN = _get_dbx_secret(workspace_client=w, **DATABRICKS_TOKEN_SECRET)

    client = VectorSearchClient(
        workspace_url=w.config.host, personal_access_token=DATABRICKS_TOKEN, disable_notice=True
    )

    spark = DatabricksSession.builder.profile(w.config.profile).getOrCreate()
    spark.sql(f"ALTER TABLE {SOURCE_TABLE} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    if ENDPOINT_NAME not in {i["name"] for i in client.list_endpoints().get("endpoints", {})}:
        client.create_endpoint(name=ENDPOINT_NAME, endpoint_type="STANDARD")

    index_name = ".".join([*SOURCE_TABLE.split(".")[:-1], INDEX_NAME])

    if FORCE_RECREATE:
        idx: VectorSearchIndex | None = None
        with contextlib.suppress(Exception):
            idx = client.get_index(endpoint_name=ENDPOINT_NAME, index_name=index_name)

        if idx is not None:
            client.delete_index(endpoint_name=ENDPOINT_NAME, index_name=index_name)

    index = client.create_delta_sync_index(
        endpoint_name=ENDPOINT_NAME,
        index_name=index_name,
        primary_key=PRIMARY_KEY,
        source_table_name=SOURCE_TABLE,
        pipeline_type=INDEX_PIPELINE_TYPE,
        embedding_source_column=EMBEDDING_SOURCE_COLUMN,
        embedding_model_endpoint_name=EMBEDDING_MODEL,
    )
