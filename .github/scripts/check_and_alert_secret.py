import os
from datetime import datetime, timezone

from github import Github


def main():
    threshold_days = 50
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")

    g = Github(token)
    repo = g.get_repo(repo_name)
    for secret in repo.get_secrets():
        secret_name = secret.name
        if "linkedin" in secret_name.lower():
            updated_at = secret.updated_at
            today = datetime.now(timezone.utc)
            days_since = (today - updated_at).days
            print(
                f"Secret '{secret_name}' last updated at: {updated_at} ({days_since} days ago)"
            )

            if days_since >= threshold_days:
                issue_title = "Secret Update Reminder"
                issue_body = (
                    f"The secret **{secret_name}** was last updated **{days_since}** days ago.\n\n"
                    "Please update this secret as soon as possible."
                )
                issue = repo.create_issue(title=issue_title, body=issue_body)
                print(f"Issue created: {issue.html_url}")
            else:
                print("Secret is up-to-date; no alert needed.")


if __name__ == "__main__":
    main()
