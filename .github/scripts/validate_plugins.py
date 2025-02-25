import json
import logging
import os
import re
import sys
from datetime import datetime

import yaml
from github import Github, GithubException

logging.basicConfig(level=logging.INFO)

errors = []

event_path = os.getenv("GITHUB_EVENT_PATH", "")
with open(event_path, "r") as f:
    event_data = json.load(f)
pr_number = event_data.get("number")
merged = event_data.get("pull_request", {}).get("merged", False)
if event_data.get("action") == "closed" and not merged:
    logging.info("No action to take")
    sys.exit(0)

g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo(os.getenv("GITHUB_REPOSITORY", ""))
pr = repo.get_pull(int(pr_number))
files_to_process = pr.get_files()

plugins_file = "plugins.yml"
workflow_file = os.path.join(".github", "workflows", "galaxy_social.yml")
readme_file = "README.md"


def extract_secrets_from_plugins(plugins_data):
    found_secrets = set()
    for plugin in plugins_data.get("plugins", []):
        if not isinstance(plugin, dict):
            logging.error(f"Invalid plugin data: {plugin}")
            continue
        config = plugin.get("config", {})
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("$"):
                found_secrets.add(value.strip("$"))
    return found_secrets


def extract_secrets_from_workflow(workflow_data):
    workflow_secrets = set()
    for job in workflow_data.get("jobs", {}).values():
        for step in job.get("steps", []):
            env_vars = step.get("env", {})
            for key, value in env_vars.items():
                if isinstance(value, str) and "secrets." in value:
                    match = re.search(r"secrets\.([A-Za-z0-9_]+)", value)
                    if match:
                        workflow_secrets.add(match.group(1))
    return workflow_secrets


def validate_secrets(plugins_file, workflow_file):
    logging.info(f"Validating secrets in {plugins_file} and {workflow_file} ...")
    head_branch = pr.head
    head_repo = head_branch.repo
    branch_name = head_branch.ref
    plugins_contents = head_repo.get_contents(plugins_file, ref=branch_name)
    plugins_data = yaml.safe_load(plugins_contents.decoded_content.decode())
    workflow_contents = head_repo.get_contents(workflow_file, ref=branch_name)
    workflow_data = yaml.safe_load(workflow_contents.decoded_content.decode())
    if plugins_data is None or workflow_data is None:
        logging.error("Failed to load plugins or workflow data.")
        return

    plugin_secrets = extract_secrets_from_plugins(plugins_data)
    workflow_secrets = extract_secrets_from_workflow(workflow_data) - {"GITHUB_TOKEN"}

    plugins_url = f"[plugins.yml]({plugins_contents.html_url})"
    workflow_url = f"[galaxy_social.yml]({workflow_contents.html_url})"

    missing_in_workflow = plugin_secrets - workflow_secrets
    if missing_in_workflow:
        guide_lines = "\n".join(
            [
                f"          {secret}: ${{{{ secrets.{secret} }}}}"
                for secret in missing_in_workflow
            ]
        )
        errors.append(
            "The following secrets are defined in **enabled plugins** in "
            f"{plugins_url} but are missing from the workflow environment in "
            f"{workflow_url}: {', '.join(missing_in_workflow)}. "
            "Please either add them to the workflow environment or remove them from `plugins.yml`.\n"
            "Make sure to add the secrets to the repository secrets as well.\n"
            "For example, update your workflow to include:\n"
            "```yaml\n"
            f"{guide_lines}\n"
            "```"
        )

    missing_in_plugins = workflow_secrets - plugin_secrets
    if missing_in_plugins:
        errors.append(
            "The following secrets are defined in **workflow env** in "
            f"{workflow_url} but are not used by any enabled plugin in "
            f"{plugins_url}: {', '.join(missing_in_plugins)}. "
            "Please either remove them from the workflow environment or ensure they are used in `plugins.yml`."
        )

    for file in files_to_process:
        if file.filename == plugins_file:
            break
    else:
        return []


def update_readme_link(readme_content):
    match = re.search(r"```yaml\s*(.*?)\s*```", readme_content, flags=re.DOTALL)
    yaml_sample = match.group(1)
    encoded_yaml = yaml_sample.replace("\n", "%0A").replace(" ", "%20")
    new_link = f"../../new/main/?filename=posts/{datetime.now().year}/<your-path>.md&value={encoded_yaml}"

    updated_readme = re.sub(
        r'(<div align="center">.*?<kbd><a href=")([^"]+)(".*?</kbd>\s*</div>)',
        rf"\1{new_link}\3",
        readme_content,
        flags=re.DOTALL,
    )

    return updated_readme


def create_pr(body, readme_content, readme_sha):
    branch_name = f"update-readme-{pr.number}"
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=repo.get_branch(pr.base.ref).commit.sha,
    )
    repo.update_file(
        path=readme_file,
        message="Update README.md",
        content=readme_content,
        sha=readme_sha,
        branch=pr.base.ref,
    )
    try:
        new_pr = repo.create_pull(
            title="Update README file",
            body=body,
            base=pr.base.ref,
            head=branch_name,
        )
        logging.info(f"{body}\nCreated PR: {new_pr.html_url}")
    except GithubException as e:
        repo.get_git_ref(f"heads/{branch_name}").delete()
        logging.error(
            f"Error in creating PR: {e.data.get('errors')[0].get('message')}\nRemoving branch {branch_name}"
        )


def enabled_plugins(branch):
    plugins_contents = branch.repo.get_contents(plugins_file, ref=branch.sha)
    plugins_data = yaml.safe_load(plugins_contents.decoded_content.decode())
    enabled_plugins = set()
    for plugin in plugins_data.get("plugins", []):
        if plugin.get("enabled", False):
            enabled_plugins.add(plugin.get("name"))
    return enabled_plugins


def update_readme(readme_path, new_media_names=[]):
    try:
        readme_contents = repo.get_contents(readme_path, ref=pr.base.ref)
        readme_content = readme_contents.decoded_content.decode("utf-8")
    except Exception as e:
        logging.error(f"Error fetching {readme_path}: {e}")
        return

    post_template_section = re.search(
        r"```yaml\n---\nmedia:\n((?: .+\n)+)", readme_content
    )
    media_list = post_template_section.group(1)
    for new_media_name in new_media_names:
        if f" - {new_media_name}\n" not in media_list:
            updated_media_list = media_list + f" - {new_media_name}\n"
            readme_content = readme_content.replace(media_list, updated_media_list)
        else:
            logging.info(f"{new_media_name} already exists in the media list.")

    readme_content = update_readme_link(readme_content)

    if new_media_names:
        body = f"Updated README.md with new media names: {', '.join(new_media_names)}"
    else:
        body = "Updated README.md with new link"
    create_pr(body, readme_content, readme_contents.sha)


if __name__ == "__main__":
    if any(f.filename in {plugins_file, workflow_file} for f in files_to_process):
        if not merged:
            validate_secrets(plugins_file, workflow_file)
            if errors:
                error_message = "⚠️ **Validation Errors Found:**\n\n" + "\n".join(
                    f"- {e}" for e in errors
                )
                logging.error(error_message)
                pr.create_issue_comment(error_message)
                logging.info(f"Posted comment on PR #{pr_number}")
                sys.exit(1)
            else:
                logging.info("All validations passed successfully.")
        else:
            new_plugin_names = enabled_plugins(pr.head) - enabled_plugins(pr.base)
            update_readme(readme_file, new_plugin_names)
    elif readme_file in {f.filename for f in files_to_process} and merged:
        update_readme(readme_file)
