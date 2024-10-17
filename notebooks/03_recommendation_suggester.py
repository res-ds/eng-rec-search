# Databricks notebook source
TABLE_NAME = "summarised_eng_recs"
PRIMARY_KEY = "issue_id"
EMBEDDING_SOURCE_COLUMN = "summary"

# usual defaults
CATALOG_NAME = "workspace_innovation_db"
SCHEMA_NAME = "default"
INDEX_NAME = "summarised_eng_recs_index"
ENDPOINT_NAME = "summarised_eng_rec_endpoint"
EMBEDDING_MODEL_ENDPOINT_NAME = "databricks-gte-large-en"

# COMMAND ----------

import os

from databricks.vector_search.client import VectorSearchClient
from openai import OpenAI

open_ai_client = OpenAI(api_key=os.getenv("AZURE_OPENAI_KEY"), base_url=os.getenv("DATABRICKS_ENDPOINT"))

vector_search_client = VectorSearchClient()


def get_similar_issues(vector_search_client: VectorSearchClient):
    index = vector_search_client.get_index(
        endpoint_name=ENDPOINT_NAME, index_name=f"{CATALOG_NAME}.{SCHEMA_NAME}.{INDEX_NAME}"
    )
    return index.similarity_search(query_text=query, columns="summary", num_results=5)


def generate_response(open_ai_client: OpenAI, prompt: str) -> str:
    response = open_ai_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"), messages=[{"role": "user", "content": prompt}], temperature=0.0
    )
    return response.choices[0].message.content


# COMMAND ----------

# MAGIC %md
# MAGIC # Defining a prompt

# COMMAND ----------

augmented_prompt_template = """
You are an expert turbine performance engineer.
Based on the current issue symptoms and documented previous issues with their symptoms, recommendations, and resolutions, provide a concise recommendation (max. 50 words) to resolve the current issue.
Use only the provided previous issues to recommend actions.

# Current Issue Symptoms:
{current_issue_symptoms}

# Previous Issues:
{previous_issues}
"""

# COMMAND ----------

# auto_prompt = generate_response(open_ai_client, prompt=f"How can I update the following prompt to generate a better recommendation?\n{augmented_prompt_template}")
# print(auto_prompt)

# COMMAND ----------

# MAGIC %md
# MAGIC # Entering a sample issue (and expected recommendation)

# COMMAND ----------

query = """T01 Main Bearing Temperature is trending at a significantly higher temperature ..."""

expected_rec = """\
Site technicians ...
"""

# COMMAND ----------

similar_issues = [i[0] for i in get_similar_issues(vector_search_client=vector_search_client)["result"]["data_array"]]

print(f"[Closest issue (which will be NOT provided to the generation)]\n{similar_issues[0]}")
previous_issues = "\n\n".join([f"## Issue {i}:\n{_issue}" for i, _issue in enumerate(similar_issues, start=1)])

# COMMAND ----------

augmented_prompt = augmented_prompt_template.format(current_issue_symptoms=query, previous_issues=previous_issues)
suggested_reccomandation = generate_response(open_ai_client, prompt=augmented_prompt)

print("GIVEN_SYMPTOM-------------------------------------")
print(f"\n{query}")
print("\n\nSUGGESTED_REC-------------------------------------")
print(suggested_reccomandation)
print("\n\nREAL_ENG_REC-------------------------------------")
print(expected_rec)

# COMMAND ----------
