from base64 import b64decode

import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.vector_search.client import VectorSearchClient
from openai import OpenAI


def _get_dbx_secret(workspace_client: WorkspaceClient, scope: str, key: str) -> str:
    _encoded_secret = workspace_client.secrets.get_secret(scope=scope, key=key).value
    assert isinstance(_encoded_secret, str)  # mypy fix
    return b64decode(_encoded_secret).decode()


@st.cache_resource
def get_workspace_client() -> WorkspaceClient:
    return WorkspaceClient()


@st.cache_resource
def get_open_ai_client() -> OpenAI:
    workspace_client = get_workspace_client()
    api_key = _get_dbx_secret(workspace_client=workspace_client, scope="eng-rec-scope", key="databricks-token")
    return OpenAI(api_key=api_key, base_url=f"{workspace_client.config.host}/serving-endpoints")


@st.cache_resource
def get_vector_search_client() -> VectorSearchClient:
    workspace_client = get_workspace_client()
    personal_access_token = _get_dbx_secret(
        workspace_client=workspace_client, scope="eng-rec-scope", key="databricks-token"
    )
    return VectorSearchClient(
        workspace_url=workspace_client.config.host,
        personal_access_token=personal_access_token,
    )
