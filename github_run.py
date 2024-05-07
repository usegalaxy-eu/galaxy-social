import argparse
import fnmatch
import os
import sys

import requests

from lib.galaxy_social import galaxy_social


class github_run:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")
        self.pr_number = os.getenv("PR_NUMBER")

    def comment(self, comment_text):
        print(comment_text)
        if not comment_text or not self.github_token or not self.repo or not self.pr_number:
            return
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = (
            f"https://api.github.com/repos/{self.repo}/issues/{self.pr_number}/comments"
        )
        data = {"body": comment_text}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            return True
        else:
            raise Exception(
                f"Failed to create github comment!, {response.json().get('message')}"
            )

    def get_files(self):
        url = f"https://api.github.com/repos/{self.repo}/pulls/{self.pr_number}/files"
        response = requests.get(url)
        if response.status_code == 200:
            changed_files = response.json()
            for file in changed_files:
                raw_url = file["raw_url"]
                if raw_url.endswith(".md"):
                    response = requests.get(raw_url)
                    if response.status_code == 200:
                        changed_file_path = file["filename"]
                        with open(changed_file_path, "w") as f:
                            f.write(response.text)

        changed_files = os.environ.get("CHANGED_FILES")
        files_to_process = []
        if changed_files:
            for file_path in eval(changed_files.replace("\\", "")):
                if file_path.endswith(".md"):
                    files_to_process.append(file_path)
        else:
            for root, _, files in os.walk("posts"):
                for filename in fnmatch.filter(files, "*.md"):
                    file_path = os.path.join(root, filename)
                    files_to_process.append(file_path)

        return files_to_process


if __name__ == "__main__":
    github = github_run()
    files_to_process = github.get_files()
    if not files_to_process:
        github.comment("No files to process.")
        sys.exit()

    parser = argparse.ArgumentParser(description="Galaxy Social.")
    parser.add_argument("--preview", action="store_true", help="Preview the post")
    parser.add_argument(
        "--json-out",
        help="Output json file for processed files",
        default="processed_files.json",
    )
    args = parser.parse_args()

    gs = galaxy_social(args.preview, args.json_out)
    try:
        message = gs.process_files(files_to_process)
    except Exception as e:
        message = e
    github.comment(message)
