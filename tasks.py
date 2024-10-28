from invoke import task
from pathlib import Path
import sys


@task(default=True)
def list_tasks(c):
    """Show the current list of tasks"""
    filepath = Path(__file__)
    with c.cd(filepath.parent):
        c.run(f"{sys.executable} -m invoke -c {filepath.stem} -l")

@task
def deploy_processing(c):
    c.run("databricks bundle validate")
    c.run("databricks bundle deploy -t dev")

@task
def deploy_webapp(c):
    """Upload and deploy the webapp to Databricks."""

    dbx_app_name = "eng-rec-app"
    local_dir = "webapp"
    remote_dir = '/Workspace/Users/gabriele.calvo@res-group.com/eng-rec-app'

    c.run("echo Deploying webapp to Databricks...")
    c.run(f"databricks sync {local_dir} {remote_dir} --profile dev-eng-rec-helper")
    c.run(f"databricks apps deploy {dbx_app_name} --source-code-path {remote_dir}")

@task
def cleanup(c):
    """Runs all the pre-commit steps of the subprojects"""
    for subproject_dir in ["webapp", "data-processing"]:
        print(f"=== Cleaning up {subproject_dir} ===")
        c.run(f"cd {subproject_dir} && uv run poe all")
        print("\n"*3)
