# Databricks notebook source
# !pip install sqlalchemy==2.0.35 instructor==1.5.0 pandas==2.2.3 openai==1.50.2 databricks-sdk==0.33.0 databricks-sql-connector==3.4.0
# dbutils.library.restartPython()

# COMMAND ----------

import os
import yaml
import random
import warnings
from typing import Callable, TypeVar, Type, Union

from pydantic import BaseModel
from openai import AzureOpenAI
import instructor
import pandas as pd
from tqdm import tqdm
from difflib import Differ
from sqlalchemy import create_engine

from pydantic import Field

# COMMAND ----------

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

instructor_client = instructor.from_openai(client)
T = TypeVar('T', bound=Union[str, BaseModel])


def generate_response(prompt: str, return_type: Type[T]) -> T:
    if issubclass(return_type, BaseModel):
        response = instructor_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            response_model=return_type,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response
    elif return_type == str:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    else:
        raise ValueError("Invalid return type. Must be either a Pydantic model or str.")
        
def load_prompts(file_path: str) -> dict:
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
    

def print_issue(issue):
    print(f"Symptoms: {issue.symptoms}")
    print(f"Recommendation: {issue.recommendation}")
    print(f"Resolution: {issue.resolution}")

def get_databricks_sql_engine():
    _access_token = os.environ["DATABRICKS_TOKEN"]
    _server_hostname = os.environ["DATABRICKS_SERVER_HOSTNAME"]
    _http_path = os.environ["DATABRICKS_HTTP_PATH"]
    _catalog = "workspace_innovation_db"
    _schema = "default"
    return create_engine(url=f"databricks://token:{_access_token}@{_server_hostname}?http_path={_http_path}&catalog={_catalog}&schema={_schema}")

# COMMAND ----------

all_eng_recs = pd.read_sql("SELECT * FROM raw_eng_recs;", con=get_databricks_sql_engine())
all_eng_recs

# COMMAND ----------

# SAMPLE_ISSUE_RANGE = slice(None, 5)
SAMPLE_ISSUE_RANGE = slice(None, None)

# COMMAND ----------

the_data = (
    all_eng_recs
    .query("MarketApiKey.isin(['uki', 'americas', 'aus']) and Status=='Closed'")
    .assign(issue_id=lambda d: d['SiteID'] + d['IssueID'])
    .filter(['issue_id', 'Market', 'Site', 'Title', 'OpeningComment', 'ClosingComment', 'Turbines', 'Comments', 'Subsystem'])
    .iloc[SAMPLE_ISSUE_RANGE]
)

# COMMAND ----------

def combine_fields(row: pd.Series) -> str:
    opening_section = f"\n\n## Issue history:\n{row.OpeningComment}"
    mid_section = (
        "" if (pd.isnull(row.Comments) or row.Comments == "NULL") else row.Comments
    )
    closing_section = f"\n\n## Closing comment:\n{row.ClosingComment}"
    return f"# {row.Title}{opening_section}{mid_section}{closing_section}".replace(
        "_x000D_", " "
    )
 
 
tracked_issues = [
    combine_fields(row) for _, row in tqdm(the_data.iterrows(), total=the_data.shape[0])
]

# COMMAND ----------

class BaseRunner:
    main_prompt: str
    return_class: object

    def construct_prompt(self, issue) -> str:
        return f"{self.main_prompt}:\n{issue}"
        
    def run(self, issue):
        return generate_response(self.construct_prompt(issue), self.return_class)

class Distiller(BaseRunner):
    def __init__(self, spec_dict: dict):
        class DistilledIssue(BaseModel):
            symptoms: str = Field(..., description=spec_dict['symptoms_prompt'])
            recommendation: str = Field(..., description=spec_dict['recommendation_prompt'])
            resolution: str = Field(..., description=spec_dict['resolution_prompt'])

        self.return_class = DistilledIssue
        self.main_prompt = spec_dict['main_prompt']

class Censor(BaseRunner):
    def __init__(self, spec_dict: dict):    
        class CensorIssue(BaseModel):
            symptoms: str = Field(..., description=spec_dict['symptoms_prompt'])
            recommendation: str = Field(..., description=spec_dict['recommendation_prompt'])
            resolution: str = Field(..., description=spec_dict['resolution_prompt'])
    
        self.return_class = CensorIssue
        self.main_prompt = spec_dict['main_prompt']

def _default_compare_result(i1, i2):
    print(i1, "\n==== vs ===\n", i2)

def show_sample_performance(all_issues: list, runner: BaseRunner, issue_index: int | None = None, compare_func: Callable = _default_compare_result) -> None:
    if issue_index is None:
        issue_index = random.randint(0,len(all_issues)-1)
        
    sample_issue = all_issues[issue_index]
    print("="*100, f"\nPROMPT for issue {issue_index}:\n\n{runner.construct_prompt(sample_issue)}", "\n", "-"*50, "\n\n")
    result = runner.run(sample_issue)
    print("-"*100)
    compare_func(sample_issue, result)
    print("="*100)

    reponse_text = "".join(result.model_dump().values())
    for i in [i.lower() for i in "Jan Feb Mar Apr May Jun Jul Aug Sept Oct Nov Dec".split(" ")]:
        if i in reponse_text.lower():
            warnings.warn(f"{i} in {reponse_text}")
            
    return result

def print_issue_diff(issue_1, issue_2):
    differ = Differ()
    
    fields = ['symptoms', 'recommendation', 'resolution']
    
    for field in fields:
        print(f"\n=== Differences in {field} ===")
        
        text1 = getattr(issue_1, field).split('\n')
        text2 = getattr(issue_2, field).split('\n')
        
        diff = list(differ.compare(text1, text2))
        
        for line in diff:
            if line.startswith('  '):  # unchanged
                continue
            elif line.startswith('- '):  # in issue_1 but not in issue_2
                print(f"Only in distilled: {line[2:]}")
            elif line.startswith('+ '):  # in issue_2 but not in issue_1
                print(f"Only in censored: {line[2:]}")

# COMMAND ----------

# prompt_spec = load_prompts('prompts.yaml')
prompt_spec = {
    'prompts': {
        'distilled_issue': {
            'main_prompt': 'Distill the following issue into its symptoms, recommendations, and resolution. Remember to: - Think step by step - Do not include anything that is not there - Remove any dates from the output\n', 
            'symptoms_prompt': "The symptoms of the issue.  Make sure to include all the symptoms here, focusing on the actual engineering and physics on what happened.  I want to see something like 'So and so happened'. Keep it to two sentences.\n", 
            'recommendation_prompt': "The recommendation of the engineer who diagnosed the issue. Make sure to include all the recommendations here. I want to see an objective 'this is what was recommended'. Keep it to two sentences.\n", 
            'resolution_prompt': 'The actual resolution of the issue.  Sometimes it is not there, if so - Leave empty.  Make sure to include all the resolution here.  Keep it to one sentence.\n'
        }, 
        'censor_issue': {
            'main_prompt': "Censor the following issue by applying the following rules: - Objects should be called by what they are. - Censor any identifying details about personnel, turbines, equipment identifiers (e.g. T4), as well as site names. - Personnel name should be turned to their job title (E.G.: Asset Manager) or 'Individual' if not there.  - Think carefully about site names, they are usually capitalised. Replace site name with 'SITE'. - Turbine identifiers should be replaced with 'TURBINE/S'. - Replace turbine manufacturers (e.g. GE, Nordex, Siemens) with 'OEM'. - Remove turbine specific parameters like power output (e.g. 2 MW), rotor diameter (e.g. 120 m), hub hight (e.g. 200 meters).\n",
            'symptoms_prompt': 'The problem that a performance engineer has identified.', 
            'recommendation_prompt': 'The recommendation that the performance engineer has made to resolve the issue.', 
            'resolution_prompt': 'The action that was taken to resolve the issue.'}
        }}


# COMMAND ----------


distiller = Distiller(spec_dict=prompt_spec['prompts']['distilled_issue'])

# COMMAND ----------

distilled_issues = []
for issue in tqdm(tracked_issues[SAMPLE_ISSUE_RANGE]):
    distilled_issue = distiller.run(issue)
    distilled_issues.append(distilled_issue)

# COMMAND ----------

censor = Censor(spec_dict=prompt_spec['prompts']['censor_issue'])

# COMMAND ----------

censored_issues = []
for issue in tqdm(distilled_issues):
    censored_issue = censor.run(issue)
    censored_issues.append(censored_issue)

# COMMAND ----------

df_to_save = the_data.assign(summary=["\n\n".join([f"### {k.title()}:\n{v}" for k,v in _issue.model_dump().items()]) for _issue in censored_issues])

# COMMAND ----------

df_to_save.to_sql(name='summarised_eng_recs', con=get_databricks_sql_engine(), index=False, if_exists="replace")

# COMMAND ----------

