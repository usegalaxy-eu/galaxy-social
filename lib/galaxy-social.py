import fnmatch
import importlib
import json
import os
import sys

import jsonschema
import markdown
import requests
import yaml
from bs4 import BeautifulSoup
from github_comment import comment_to_github

with open("plugins.yml", "r") as file:
    plugins_config = yaml.safe_load(file)

plugins = {}
for plugin in plugins_config["plugins"]:
    if "preview" in sys.argv and plugin["name"].lower() != "markdown":
        continue

    if plugin["enabled"]:
        module_name, class_name = plugin["class"].rsplit(".", 1)

        try:
            module = importlib.import_module(f"plugins.{module_name}")
            plugin_class = getattr(module, class_name)
        except:
            comment_to_github(
                f"Error with plugin {module_name}.{class_name}.", error=True
            )

        try:
            config = {
                key: os.environ.get(value)
                for key, value in plugin["config"].items()
                if (not isinstance(value, int) and os.environ.get(value) is not None)
            }
        except:
            comment_to_github(
                f"Missing config for {module_name}.{class_name}.", error=True
            )

        try:
            plugins[plugin["name"].lower()] = plugin_class(**config)
        except:
            comment_to_github(
                f"Invalid config for {module_name}.{class_name}.", error=True
            )


def parse_markdown_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    _, metadata, text = content.split("---\n", 2)
    try:
        metadata = yaml.safe_load(metadata)
        with open(".schema.yaml", "r") as f:
            schema = yaml.safe_load(f)
        jsonschema.validate(instance=metadata, schema=schema)
    except:
        comment_to_github(f"Invalid metadata in {file_path}.", error=True)

    metadata["media"] = [media.lower() for media in metadata["media"]]

    for media in metadata["media"]:
        if not any(item["name"].lower() == media for item in plugins_config["plugins"]):
            comment_to_github(f"Invalid media {media}.", error=True)

    metadata["mentions"] = (
        {key.lower(): value for key, value in metadata["mentions"].items()}
        if metadata.get("mentions")
        else {}
    )
    metadata["hashtags"] = (
        {key.lower(): value for key, value in metadata["hashtags"].items()}
        if metadata.get("hashtags")
        else {}
    )
    markdown_content = markdown.markdown(text.strip())
    plain_content = BeautifulSoup(markdown_content, "html.parser").get_text(
        separator="\n"
    )
    return plain_content, metadata


def process_markdown_file(file_path, processed_files):
    content, metadata = parse_markdown_file(file_path)
    if "preview" in sys.argv:
        try:
            plugins["markdown"].create_post(
                content, [], [], metadata.get("images", []), media=metadata["media"]
            )
            return processed_files
        except:
            comment_to_github(f"Failed to create preview for {file_path}.", error=True)
    stats = {}
    url = {}
    for media in metadata["media"]:
        if file_path in processed_files and media in processed_files[file_path]:
            stats[media] = processed_files[file_path][media]
            continue
        mentions = metadata.get("mentions", {}).get(media, [])
        hashtags = metadata.get("hashtags", {}).get(media, [])
        images = metadata.get("images", [])
        stats[media], url[media] = plugins[media].create_post(
            content, mentions, hashtags, images
        )
    url_text = "\n".join([f"[{media}]({link})" for media, link in url.items() if link])
    comment_to_github(f"Posted to:\n\n{url_text}")

    processed_files[file_path] = stats
    print(f"Processed {file_path}: {stats}")
    return processed_files


def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    response = requests.get(url)
    print(response.json(), url)
    if response.status_code == 200:
        changed_files = response.json()
        for file in changed_files:
            raw_url = file["raw_url"]
            if raw_url.endswith(".md"):
                response = requests.get(raw_url)
                if response.status_code == 200:
                    with open(file["filename"], "w") as f:
                        f.write(response.text)

    processed_files = {}
    if os.path.exists("processed_files.json"):
        with open("processed_files.json", "r") as file:
            processed_files = json.load(file)
    changed_files = os.environ.get("CHANGED_FILES")
    if changed_files:
        for file_path in eval(changed_files.replace("\\", "")):
            if file_path.endswith(".md"):
                processed_files = process_markdown_file(file_path, processed_files)
    else:
        for root, _, files in os.walk("posts"):
            for filename in fnmatch.filter(files, "*.md"):
                file_path = os.path.join(root, filename)
                processed_files = process_markdown_file(file_path, processed_files)
    with open("processed_files.json", "w") as file:
        json.dump(processed_files, file)


if __name__ == "__main__":
    main()
