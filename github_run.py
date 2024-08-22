import argparse
import fnmatch
import json
import os
import re
import sys

import github
import requests
import yaml

from lib.galaxy_social import galaxy_social


class github_run:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        g = github.Github(self.github_token)
        self.repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        self.pr = self.repo.get_pull(int(os.getenv("PR_NUMBER")))

    def comment(self, comment_text, **kwargs):
        if not comment_text:
            return
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
                    variables = {"subjectId": comment_node_id, "classifier": "OUTDATED"}
                    requests.post(
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

        for comment_body in comment_text.split("\n\n---\n"):
            if not comment_body:
                continue
            try:
                self.pr.create_issue_comment(comment_body)
            except Exception as e:
                print(f"Error creating comment: {e}")
                return False
        return True

    def get_files(self):
        for file in self.pr.get_files():
            raw_url = file.raw_url
            if raw_url.endswith(".md"):
                response = requests.get(raw_url)
                if response.status_code == 200:
                    changed_file_path = file.filename
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
            print("No changed files found, processing all files.")
            for root, _, files in os.walk("posts"):
                for filename in fnmatch.filter(files, "*.md"):
                    file_path = os.path.join(root, filename)
                    files_to_process.append(file_path)

        return files_to_process

    def new_pr(self, not_posted):
        if not not_posted:
            return
        branch_name = f"Failed-posts-{self.pr.number}"
        self.repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=self.repo.get_branch("main").commit.sha,
        )
        created_files = []
        for file_path, media in not_posted.items():
            new_file_path = os.path.join(
                os.path.dirname(file_path),
                f"retry-{self.pr.number}-{os.path.basename(file_path)}",
            )
            message = f"Add failed post for file {file_path} from PR {self.pr.number}"
            with open(file_path, "r") as f:
                md_content = f.read()
            _, metadata, text = md_content.split("---\n", 2)
            metadata = yaml.safe_load(metadata)
            if media:
                metadata["media"] = media
                metadata["mentions"] = {
                    key: value
                    for key, value in metadata.get("mentions", {}).items()
                    if key in media
                }
                metadata["hashtags"] = {
                    key: value
                    for key, value in metadata.get("hashtags", {}).items()
                    if key in media
                }
            new_md_content = f"---\n{yaml.dump(metadata)}---\n{text}"
            self.repo.create_file(
                path=new_file_path,
                message=message,
                content=new_md_content,
                branch=branch_name,
            )
            created_files.append(f"`{file_path}` to `{', '.join(metadata['media'])}`")

        title = f"Try to post failed posts from PR {self.pr.number}"
        body = (
            f"Failed to post the following from #{self.pr.number}:\n- "
            + "\n- ".join(created_files)
        )
        new_pr = self.repo.create_pull(
            title=title,
            body=body,
            base="main",
            head=branch_name,
        )

        self.repo.get_workflow("preview.yml").create_dispatch(
            ref="main",
            inputs={"pr_number": new_pr.number},
        )

        self.comment(
            f"Unfortunately, there was a problem!\n"
            f"I created a new PR for failed posts: {new_pr.html_url}"
        )


if __name__ == "__main__":
    github_instance = github_run()
    files_to_process = github_instance.get_files()
    if not files_to_process:
        github_instance.comment("No files to process.")
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
        github_instance.comment(message, preview=args.preview)
        if args.preview:
            sys.exit()

        with open(args.json_out, "r") as file:
            processed_files = json.load(file)

        not_posted = {}
        for file_path, social_stat_dict in processed_files.items():
            if file_path in files_to_process:
                media_list = []
                for media, stat in social_stat_dict.items():
                    if not stat:
                        media_list.append(media)
                if media_list:
                    not_posted[file_path] = media_list

        github_instance.new_pr(not_posted)

    except Exception as e:
        if args.preview:
            github_instance.comment("Something went wrong, an Admin will take a look.")
        else:
            not_posted = {file_path: [] for file_path in files_to_process}
            github_instance.new_pr(not_posted)

        raise e
