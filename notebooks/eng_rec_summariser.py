# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.4
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# +
import os
import random
import warnings
from collections.abc import Callable
from difflib import Differ

import instructor
import pandas as pd
import sqlalchemy.engine
import yaml
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from tqdm import tqdm

load_dotenv()
# +
client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
)

instructor_client = instructor.from_openai(client)


class _BaseIssue(BaseModel):
    symptoms: str
    recommendation: str
    resolution: str


def generate_response(prompt: str, return_type: type[_BaseIssue]) -> _BaseIssue:
    if issubclass(return_type, _BaseIssue):
        response = instructor_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            response_model=return_type,
            messages=[{"role": "user", "content": prompt}],
        )
        return response
    else:
        raise ValueError("Invalid return type. Must be either a Pydantic model or str.")


def load_prompts(file_path: str) -> dict:
    with open(file_path) as file:
        return yaml.safe_load(file)


def print_issue(issue: _BaseIssue) -> None:
    print(f"Symptoms: {issue.symptoms}")
    print(f"Recommendation: {issue.recommendation}")
    print(f"Resolution: {issue.resolution}")


def get_databricks_sql_engine() -> sqlalchemy.engine.Engine:
    _access_token = os.environ["DATABRICKS_TOKEN"]
    _server_hostname = os.environ["DATABRICKS_SERVER_HOSTNAME"]
    _http_path = os.environ["DATABRICKS_HTTP_PATH"]
    _catalog = "workspace_innovation_db"
    _schema = "default"
    return create_engine(
        url=f"databricks://token:{_access_token}@{_server_hostname}?http_path={_http_path}&catalog={_catalog}&schema={_schema}"
    )


# +

all_eng_recs = pd.read_sql(
    "SELECT * FROM `workspace_innovation_db`.`default`.`raw_eng_recs`;", con=get_databricks_sql_engine()
)
all_eng_recs
# the_data = pd.read_excel("__ignore__/EngRecSubset.xlsx")
# -

SAMPLE_ISSUE_RANGE = slice(None, 5)
# SAMPLE_ISSUE_RANGE = slice(None, None)

the_data = (
    all_eng_recs.query("MarketApiKey.isin(['uki', 'americas', 'aus']) and Status=='Closed'")
    .assign(issue_id=lambda d: d["SiteID"] + d["IssueID"])
    .filter(
        ["issue_id", "Market", "Site", "Title", "OpeningComment", "ClosingComment", "Turbines", "Comments", "Subsystem"]
    )
    .iloc[SAMPLE_ISSUE_RANGE]
)


# +
def combine_fields(row: pd.Series) -> str:
    opening_section = f"\n\n## Issue history:\n{row.OpeningComment}"
    mid_section = "" if (pd.isnull(row.Comments) or row.Comments == "NULL") else row.Comments
    closing_section = f"\n\n## Closing comment:\n{row.ClosingComment}"
    return f"# {row.Title}{opening_section}{mid_section}{closing_section}".replace("_x000D_", " ")


tracked_issues = [combine_fields(row) for _, row in tqdm(the_data.iterrows(), total=the_data.shape[0])]

# +


class BaseRunner:
    main_prompt: str
    return_class: type[_BaseIssue]

    def construct_prompt(self, issue: _BaseIssue) -> str:
        return f"{self.main_prompt}:\n{issue}"

    def run(self, issue: _BaseIssue) -> _BaseIssue:
        return generate_response(self.construct_prompt(issue), return_type=self.return_class)


class Distiller(BaseRunner):
    def __init__(self, spec_dict: dict):
        class DistilledIssue(_BaseIssue):
            symptoms: str = Field(..., description=spec_dict["symptoms_prompt"])
            recommendation: str = Field(..., description=spec_dict["recommendation_prompt"])
            resolution: str = Field(..., description=spec_dict["resolution_prompt"])

        self.return_class = DistilledIssue
        self.main_prompt = spec_dict["main_prompt"]


class Censor(BaseRunner):
    def __init__(self, spec_dict: dict):
        class CensorIssue(_BaseIssue):
            symptoms: str = Field(..., description=spec_dict["symptoms_prompt"])
            recommendation: str = Field(..., description=spec_dict["recommendation_prompt"])
            resolution: str = Field(..., description=spec_dict["resolution_prompt"])

        self.return_class = CensorIssue
        self.main_prompt = spec_dict["main_prompt"]


def _default_compare_result(i1: _BaseIssue, i2: _BaseIssue) -> None:
    print(i1, "\n==== vs ===\n", i2)


def show_sample_performance(
    all_issues: list,
    runner: BaseRunner,
    issue_index: int | None = None,
    compare_func: Callable = _default_compare_result,
) -> _BaseIssue:
    if issue_index is None:
        issue_index = random.randint(0, len(all_issues) - 1)

    sample_issue = all_issues[issue_index]
    print(
        "=" * 100,
        f"\nPROMPT for issue {issue_index}:\n\n{runner.construct_prompt(sample_issue)}",
        "\n",
        "-" * 50,
        "\n\n",
    )
    result = runner.run(sample_issue)
    print("-" * 100)
    compare_func(sample_issue, result)
    print("=" * 100)

    reponse_text = "".join(result.model_dump().values())
    for i in [i.lower() for i in "Jan Feb Mar Apr May Jun Jul Aug Sept Oct Nov Dec".split(" ")]:
        if i in reponse_text.lower():
            warnings.warn(f"{i} in {reponse_text}")

    return result


def print_issue_diff(issue_1: _BaseIssue, issue_2: _BaseIssue) -> None:
    differ = Differ()

    fields = ["symptoms", "recommendation", "resolution"]

    for field in fields:
        print(f"\n=== Differences in {field} ===")

        text1 = getattr(issue_1, field).split("\n")
        text2 = getattr(issue_2, field).split("\n")

        diff = list(differ.compare(text1, text2))

        for line in diff:
            if line.startswith("  "):  # unchanged
                continue
            elif line.startswith("- "):  # in issue_1 but not in issue_2
                print(f"Only in distilled: {line[2:]}")
            elif line.startswith("+ "):  # in issue_2 but not in issue_1
                print(f"Only in censored: {line[2:]}")


# -

prompt_spec = load_prompts("../prompts.yaml")
distiller = Distiller(spec_dict=prompt_spec["prompts"]["distilled_issue"])

# +
# distilled_issue = show_sample_performance(tracked_issues, runner=distiller)
# -

distilled_issues = []
for issue in tqdm(tracked_issues[SAMPLE_ISSUE_RANGE]):
    distilled_issue = distiller.run(issue)
    distilled_issues.append(distilled_issue)

prompt_spec = load_prompts("../prompts.yaml")
censor = Censor(spec_dict=prompt_spec["prompts"]["censor_issue"])

# +
# _censored_issue = show_sample_performance(distilled_issues, runner=censor,
# issue_index=None, compare_func=print_issue_diff)

# +
# print_issue_diff(distilled_issues[8], _censored_issue)
# -

censored_issues = []
for issue in distilled_issues:
    censored_issue = censor.run(issue)
    censored_issues.append(censored_issue)

# +
# for i, (_distilled, _censored) in enumerate(zip(distilled_issues, censored_issues)):
#     print("-"*100, "\nIssue", i)
#     print_issue_diff(_distilled, _censored)
# -

df_to_save = the_data.assign(
    summary=[
        "\n\n".join([f"### {k.title()}:\n{v}" for k, v in _issue.model_dump().items()]) for _issue in censored_issues
    ]
)

df_to_save.to_sql(name="summarised_eng_recs", con=get_databricks_sql_engine(), index=False, if_exists="replace")
