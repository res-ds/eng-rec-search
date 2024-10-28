from pathlib import Path

import yaml

root_dir = Path(__file__).parents[1]
app_fpath = root_dir / "app.yaml"
dotenv_fpath = root_dir / ".env"

if __name__ == "__main__":
    with open(app_fpath) as f:
        app_cfg = yaml.load(f, Loader=yaml.FullLoader)

    with open(dotenv_fpath, "w") as f:
        for env_spec in app_cfg["env"]:
            f.write(f"{env_spec['name']}={env_spec['value']}\n")

        f.write("\n\n")
        f.write("DEBUG=1\n")
        f.write("DATABRICKS_CONFIG_PROFILE=dev-eng-rec-helper\n")
