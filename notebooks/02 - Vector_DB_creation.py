# Databricks notebook source
# MAGIC %md
# MAGIC # TODO
# MAGIC add this library to the compute: databricks-vectorsearch==0.40

# COMMAND ----------

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

spark.sql(
    f"""
    ALTER TABLE {CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_NAME} 
    SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """
)

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

client = VectorSearchClient()

# COMMAND ----------

if ENDPOINT_NAME not in {i['name'] for i in client.list_endpoints()['endpoints']}:
    client.create_endpoint(name=ENDPOINT_NAME, endpoint_type="STANDARD")

# COMMAND ----------

index = client.create_delta_sync_index(
    endpoint_name=ENDPOINT_NAME,
    source_table_name=f"{CATALOG_NAME}.{SCHEMA_NAME}.{TABLE_NAME}",
    index_name=f"{CATALOG_NAME}.{SCHEMA_NAME}.{INDEX_NAME}",
    pipeline_type="TRIGGERED",
    primary_key=PRIMARY_KEY,
    embedding_source_column=EMBEDDING_SOURCE_COLUMN,
    embedding_model_endpoint_name=EMBEDDING_MODEL_ENDPOINT_NAME,
)

# COMMAND ----------

