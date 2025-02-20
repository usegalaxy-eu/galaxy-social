import json
import os
import re
import sys

import github
import yaml

from lib.galaxy_social import galaxy_social


class github_run:
    def __init__(
        self, pr_number, processed_files_path, processed_files_branch="processed_files"
    ):
        g = github.Github(os.getenv("GITHUB_TOKEN"))
        self.repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        self.pr = self.repo.get_pull(pr_number)
        self.processed_files_path = processed_files_path
        self.processed_files_branch = processed_files_branch

    def comment(self, comment_text, **kwargs):
        if not comment_text:
            return
        # Hide old comments of the bot
        if kwargs.get("preview"):
            for comment in self.pr.get_issue_comments():
                if comment.user.login == "github-actions[bot]":
                    comment.minimize()

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
        files_to_process = []
        for file in self.pr.get_files():
            file_path = file.filename
            if file_path.endswith(".md"):
                head_branch = self.pr.head
                pr_content = head_branch.repo.get_contents(
                    file_path, ref=head_branch.sha
                ).decoded_content.decode()
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(pr_content)
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
                f"retry-{self.pr.number}_{os.path.basename(file_path)}",
            )
            message = f"Add failed post for file {file_path} from PR {self.pr.number}"
            with open(file_path, "r") as f:
                md_content = f.read()
            _, metadata, text = md_content.split("---\n", 2)
            metadata = yaml.safe_load(metadata)
            if media:
                metadata["media"] = media
                for meta in ["mentions", "hashtags"]:
                    if meta in metadata:
                        new_metadata = {}
                        for key, value in metadata[meta].items():
                            if key in media:
                                new_metadata[key] = value
                        metadata[meta] = new_metadata
            new_md_content = f"---\n{yaml.dump(metadata, sort_keys=False)}---\n{text}"
            self.repo.create_file(
                path=new_file_path,
                message=message,
                content=new_md_content,
                branch=branch_name,
            )
            created_files.append(f"`{file_path}` to `{', '.join(metadata['media'])}`")

        title = f"Try to post failed posts from #{self.pr.number}"
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

        self.repo.get_workflow("galaxy_social.yml").create_dispatch(
            ref="main", inputs={"pr_number": str(new_pr.number)}
        )

        self.comment(
            f"Unfortunately, there was a problem!\n"
            f"I created a new PR for failed posts: {new_pr.html_url}"
        )

    def initialize_processed_files_branch(self):
        try:
            branch = self.repo.get_branch(self.processed_files_branch)
        except Exception as e:
            print(e)
            self.repo.create_git_ref(
                ref=f"refs/heads/{self.processed_files_branch}",
                sha=self.repo.get_branch("main").commit.sha,
            )
            message = f"Initialize {self.processed_files_branch} with {self.processed_files_path}"
            self.repo.create_file(
                path=self.processed_files_path,
                message=message,
                content="{}",
                branch=self.processed_files_branch,
            )
            print(message)
            branch = self.repo.get_branch(self.processed_files_branch)

        file_content = self.repo.get_contents(
            self.processed_files_path, ref=branch.commit.sha
        )
        processed_files = file_content.decoded_content.decode()
        with open(self.processed_files_path, "w") as f:
            f.write(processed_files)
        print(f"processed_files:\n {processed_files}")

    def commit_processed_files(self):
        with open(self.processed_files_path, "r") as file:
            file_data = file.read()
        processed_files_content_file = self.repo.get_contents(
            self.processed_files_path, ref=self.processed_files_branch
        )
        message = f"Update {self.processed_files_path}"
        self.repo.update_file(
            path=self.processed_files_path,
            message=message,
            content=file_data,
            sha=processed_files_content_file.sha,
            branch=self.processed_files_branch,
        )
        print(message)
        return json.loads(file_data)


if __name__ == "__main__":
    with open(os.getenv("GITHUB_EVENT_PATH", ""), "r") as f:
        event_data = json.load(f)
    pr_number = event_data.get("number") or int(
        event_data.get("inputs", {}).get("pr_number")
    )
    closed = event_data.get("action") == "closed"
    merged = event_data.get("pull_request", {}).get("merged", False)
    preview = not merged and not closed
    if not merged and closed:
        print("No action to take")
        sys.exit(0)

    github_instance = github_run(pr_number, "processed_files.json")
    files_to_process = github_instance.get_files()
    if not files_to_process:
        github_instance.comment("No files to process.")
        sys.exit()

    gs = galaxy_social(preview)
    try:
        github_instance.initialize_processed_files_branch()
        message = gs.process_files(
            files_to_process, github_instance.processed_files_path
        )
        github_instance.comment(message, preview=preview)
        if preview:
            sys.exit()

        processed_files = github_instance.commit_processed_files()
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
        if preview:
            github_instance.comment("Something went wrong, an Admin will take a look.")
        else:
            not_posted = {file_path: [] for file_path in files_to_process}
            github_instance.new_pr(not_posted)
        raise e
