import logging
import textwrap
from base64 import b64decode
from collections.abc import Mapping

import instructor
from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm.auto import tqdm

DATABRICKS_TOKEN_SECRET = dict(scope="eng-rec-scope", key="databricks-token")
INSTRUCT_MODEL = "databricks-meta-llama-3-1-70b-instruct"
SOURCE_TABLE = "workspace.default.raw_tracked_issues"
DESTINATION_TABLE = "workspace.default.summarized_tracked_issues"

logger = logging.getLogger(__name__)

prompt_spec = {
    "distiller": {
        "main_prompt": (
            "Distill the following issue into its symptoms, recommendations, and resolution. "
            "Remember to: "
            "- Think step by step "
            "- Do not include anything that is not there "
            "- Remove any dates from the output"
        ),
        "symptoms_prompt": (
            "The symptoms of the issue. Make sure to include all the symptoms here, focusing on the actual "
            "engineering and physics on what happened.  I want to see something like 'So and so happened'. "
            "Keep it to two sentences."
        ),
        "recommendation_prompt": (
            "The recommendation of the engineer who diagnosed the issue. Make sure to include all "
            "the recommendations here. I want to see an objective 'this is what was recommended'. "
            "Keep it to two sentences."
        ),
        "resolution_prompt": (
            "The actual resolution of the issue.  Sometimes it is not there, if so - Leave empty. "
            "Make sure to include all the resolution here. "
            "Keep it to one sentence."
        ),
    },
    "censor": {
        "main_prompt": (
            "Censor the following issue by applying the following rules: "
            "- Objects should be called by what they are. "
            "- Censor any identifying details about personnel, turbines, equipment identifiers"
            " (e.g. T4), as well as site names. "
            "- Personnel name should be turned to their job title (E.G.: Asset Manager)"
            " or 'Individual' if not there.  "
            "- Think carefully about site names, they are usually capitalised. Replace site name with 'SITE'. "
            "- Turbine identifiers should be replaced with 'TURBINE/S'. "
            "- Replace turbine manufacturers (e.g. GE, Nordex, Siemens) with 'OEM'. "
            "- Remove turbine specific parameters like power output (e.g. 2 MW),"
            " rotor diameter (e.g. 120 m), hub height (e.g. 200 meters).\n"
        ),
        "symptoms_prompt": ("The problem that a performance engineer has identified."),
        "recommendation_prompt": ("The recommendation that the performance engineer has made to resolve the issue."),
        "resolution_prompt": ("The action that was taken to resolve the issue."),
    },
}


def _raw_issue_to_single_markdown(issue: Mapping) -> str:
    return textwrap.dedent(f"""\
    # {issue['Issue Title']}

    ## Description
    {issue['Description']}

    ## Closing Comment
    {issue['Closing Comment']}
    """)


class DistilledIssue(BaseModel):
    symptoms: str = Field(..., description=prompt_spec["distiller"]["symptoms_prompt"])
    recommendation: str = Field(..., description=prompt_spec["distiller"]["recommendation_prompt"])
    resolution: str = Field(..., description=prompt_spec["distiller"]["resolution_prompt"])


class Distiller:
    def __init__(self, main_prompt: str):
        self.main_prompt = main_prompt

    def run_instructor(self, issue: Mapping, instructor_client: instructor.client.Instructor) -> DistilledIssue:
        issue_markdown = _raw_issue_to_single_markdown(issue)
        return instructor_client.chat.completions.create(
            model=INSTRUCT_MODEL,
            response_model=DistilledIssue,
            messages=[{"role": "user", "content": f"{self.main_prompt}:\n{issue_markdown}"}],
        )


def _distilled_issue_to_single_markdown(distilled_issue: DistilledIssue) -> str:
    return textwrap.dedent(f"""\
    # Issue
    ## Symptoms
    {distilled_issue.symptoms}

    ## Recommendation
    {distilled_issue.recommendation}

    ## Resolution
    {distilled_issue.resolution}
    """)


class CensorIssue(BaseModel):
    symptoms: str = Field(..., description=prompt_spec["censor"]["symptoms_prompt"])
    recommendation: str = Field(..., description=prompt_spec["censor"]["recommendation_prompt"])
    resolution: str = Field(..., description=prompt_spec["censor"]["resolution_prompt"])


class Censor:
    def __init__(self, main_prompt: str):
        self.main_prompt = main_prompt

    def run_instructor(self, issue: DistilledIssue, instructor_client: instructor.client.Instructor) -> CensorIssue:
        issue_markdown = _distilled_issue_to_single_markdown(distilled_issue=issue)
        return instructor_client.chat.completions.create(
            model=INSTRUCT_MODEL,
            response_model=CensorIssue,
            messages=[{"role": "user", "content": f"{self.main_prompt}:\n{issue_markdown}"}],
        )


def _get_dbx_secret(workspace_client: WorkspaceClient, scope: str, key: str) -> str:
    _encoded_secret = workspace_client.secrets.get_secret(scope=scope, key=key).value
    assert isinstance(_encoded_secret, str)  # mypy fix
    return b64decode(_encoded_secret).decode()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    w = WorkspaceClient()
    spark = DatabricksSession.builder.profile(w.config.profile).getOrCreate()
    spark.conf.set("spark.sql.ansi.enabled", "false")

    DATABRICKS_TOKEN = _get_dbx_secret(workspace_client=w, **DATABRICKS_TOKEN_SECRET)
    client = OpenAI(api_key=DATABRICKS_TOKEN, base_url=f"{w.config.host}/serving-endpoints")
    instructor_client = instructor.from_openai(client, mode=instructor.Mode.MD_JSON)

    logger.info(f"Reading raw issues from {SOURCE_TABLE}")
    raw_df = spark.read.table(SOURCE_TABLE)

    logger.info(f"Distilling and censoring {raw_df.count()} issues")
    distiller = Distiller(main_prompt=prompt_spec["distiller"]["main_prompt"])

    distilled_issues = []
    raw_df_pandas = raw_df.pandas_api()
    for _, row in tqdm(raw_df_pandas.iterrows(), total=raw_df_pandas.shape[0]):
        distilled_issues.append(distiller.run_instructor(issue=row, instructor_client=instructor_client))

    logger.info(f"Censoring {len(distilled_issues)} distilled issues")
    censor = Censor(main_prompt=prompt_spec["censor"]["main_prompt"])

    censored_issues = []
    for issue in tqdm(distilled_issues):
        censored_issues.append(censor.run_instructor(issue=issue, instructor_client=instructor_client))

    logger.info(f"Writing {len(censored_issues)} summarized issues to {DESTINATION_TABLE}")
    _original = [_raw_issue_to_single_markdown(i) for _, i in raw_df_pandas.iterrows()]
    _summaries = [
        "\n\n".join([f"### {k.title()}:\n{v}" for k, v in _issue.model_dump().items()]) for _issue in censored_issues
    ]
    summarized_df = spark.createDataFrame(
        raw_df.select(["Id", "Market", "Site", "Turbine"]).toPandas().assign(Original=_original, Summary=_summaries)
    )
    summarized_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(DESTINATION_TABLE)
