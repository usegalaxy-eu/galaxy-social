import argparse
import fnmatch
import os
import re
import sys

import requests

from lib.galaxy_social import galaxy_social


class github_run:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")
        self.pr_number = os.getenv("PR_NUMBER")

    def comment(self, comment_text, **kwargs):
        # Hide old comments of the bot
        if kwargs.get("preview"):
            query = "mutation($input: MinimizeCommentInput!) { minimizeComment(input: $input) { minimizedComment { isMinimized minimizedReason } } }"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
            }
            for comment in self.pr.get_issue_comments():
                if comment.user.login == "github-actions[bot]":
                    comment_node_id = requests.get(comment.url).json()["node_id"]
                    variables = {
                        "subjectId": comment_node_id,
                        "classifier": "OUTDATED",
                    }
                    response = requests.post(
                        "https://api.github.com/graphql",
                        headers=headers,
                        json=({"query": query, "variables": {"input": variables}}),
                    )
        # Enclose mentions and hashtags in backticks before commenting
        # so that they stand out for the reviewer and to prevent accidental
        # mentioning of github users.
        # When replacing mentions we explicitly handle mastodon-style ones
        # (i.e. @user@server patterns).
        # We deliberately leave "#"s and "@"s alone if they are following a "/"
        # to avoid destroying links.
        # by accident.
        comment_text = re.sub(
            r"([^a-zA-Z0-9_/])((?:[@][\w-]+)(?:[@.][\w.-]+)?)",
            lambda m: f"{m.group(1)}`{m.group(2)}`",
            comment_text,
        )
        comment_text = re.sub(
            r"([^a-zA-Z0-9_/])([#][\w]+)",
            lambda m: f"{m.group(1)}`{m.group(2)}`",
            comment_text,
        )
        print(f"\nGitHub Comments:\n\n---\n{comment_text}")
        if (
            not comment_text
            or not self.github_token
            or not self.repo
            or not self.pr_number
        ):
            return
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = (
            f"https://api.github.com/repos/{self.repo}/issues/{self.pr_number}/comments"
        )
        for comment_body in comment_text.split("\n\n---\n"):
            if not comment_body:
                continue
            data = {"body": str(comment_body)}
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 201:
                raise Exception(f"Failed to create github comment!, {response.json()}")
        return True

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
                        os.makedirs(
                            os.path.dirname(changed_file_path),
                            exist_ok=True,
                        )
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
        github.comment(message, preview=args.preview)
    except Exception as e:
        github.comment("Something went wrong, an Admin will take a look.")
        raise e
