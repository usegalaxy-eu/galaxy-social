import json
import os
import re
import sys
from argparse import ArgumentParser
from fnmatch import filter
from importlib import import_module
from typing import Any, Dict

from jsonschema import validate
from yaml import safe_load as yaml


class galaxy_social:
    def __init__(self, preview: bool, json_out: str):
        self.preview = preview
        self.json_out = json_out
        plugins_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "plugins.yml"
        )
        with open(plugins_path, "r") as file:
            plugins_config = yaml(file)

        self.plugins: Dict[str, Any] = {}
        self.plugins_config_dict = {}
        for plugin in plugins_config["plugins"]:
            if not plugin["enabled"]:
                continue
            module_name, class_name = plugin["class"].rsplit(".", 1)
            module_path = f"{'lib.' if not os.path.dirname(os.path.abspath(sys.argv[0])).endswith('lib') else ''}plugins.{module_name}"

            self.plugins_config_dict[plugin["name"].lower()] = (
                module_path,
                class_name,
                plugin.get("config", {}),
            )

    def init_plugin(self, plugin: str):
        module_path, class_name, config = self.plugins_config_dict[plugin]
        missing_env_vars = []
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("$"):
                if value[1:] in os.environ:
                    config[key] = os.environ[value[1:]]
                else:
                    missing_env_vars.append(value[1:])
        if missing_env_vars:
            raise Exception(
                f"Missing environment variables: {', '.join(missing_env_vars)} for {plugin} plugin."
            )
        try:
            module = import_module(module_path)
            plugin_class = getattr(module, class_name)
            self.plugins[plugin] = plugin_class(**config)
        except Exception as e:
            raise Exception(
                f"Invalid config for {module_path}.{class_name}.\nChange configs in plugins.yml.\n{e}"
            )

    def lint_markdown_file(self, file_path):
        with open(file_path, "r") as file:
            content = file.read()
        try:
            _, metadata, text = content.split("---\n", 2)
            metadata = yaml(metadata)
            schema_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", ".schema.yaml"
            )
            with open(schema_path, "r") as f:
                schema = yaml(f)
            validate(instance=metadata, schema=schema)
            return [metadata, text], True
        except Exception as e:
            return e, False

    def parse_markdown_file(self, file_path):
        errors = ""
        result, status = self.lint_markdown_file(file_path)
        if not status:
            return (
                "",
                {},
                f"Please check your meradata schema.",
            )

        metadata, text = result

        if "media" not in metadata:
            return (
                "",
                {},
                f"Missing media in metadata.\nAdd media to metadata.",
            )

        metadata["media"] = [media.lower() for media in metadata["media"]]

        invalid_media = [
            media
            for media in metadata["media"]
            if media not in self.plugins_config_dict
        ]
        if invalid_media:
            errors += f"- Invalid media `{', '.join(invalid_media)}` in metadata. You can only use `{', '.join(self.plugins_config_dict.keys())}` defined in your `plugins.yml` file.\n"

        for media in metadata["media"]:
            if media in self.plugins_config_dict and media not in self.plugins:
                self.init_plugin(media)

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

        mentions_invalid = metadata["mentions"].keys() - metadata["media"]
        if mentions_invalid:
            errors += f"- Mentions for `{', '.join(mentions_invalid)}` social medias are not in medias list of metadata.\n"

        hashtags_invalid = metadata["hashtags"].keys() - metadata["media"]
        if hashtags_invalid:
            errors += f"- Hashtags for `{', '.join(hashtags_invalid)}` social medias are not in medias list of metadata.\n"

        image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        images = image_pattern.findall(text)
        plain_content = re.sub(image_pattern, "", text).strip()

        metadata["images"] = [
            {"url": image[1], "alt_text": image[0]} for image in images
        ]

        return plain_content, metadata, errors

    def process_markdown_file(self, file_path, processed_files):
        content, metadata, errors = self.parse_markdown_file(file_path)
        if errors:
            return processed_files, f"⚠️ Failed to process `{file_path}`.\n{errors}"
        formatting_results = {}
        for media in metadata["media"]:
            try:
                formatting_results[media] = self.plugins[media].format_content(
                    content=content,
                    mentions=metadata.get("mentions", {}).get(media, []),
                    hashtags=metadata.get("hashtags", {}).get(media, []),
                    images=metadata.get("images", []),
                )
            except Exception as e:
                raise Exception(f"Failed to format post for {file_path}.\n{e}")

        stats = processed_files[file_path] if file_path in processed_files else {}
        skiped_media = [media for media in metadata["media"] if stats.get(media)]
        if self.preview:
            message = f"👋 Hello! I'm your friendly social media assistant. Below are the previews of this post:\n`{file_path}`"
            if skiped_media:
                message += f"\n\nSkipping post to {', '.join(skiped_media)}. because it was already posted."
            for media in set(metadata["media"]) - set(skiped_media):
                formatted_content, preview, warning = formatting_results[media]
                message += f"\n\n## {media}\n\n"
                message += preview
                if warning:
                    message += f"\nWARNING: {warning}"
            return processed_files, message.strip()

        url = {}
        for media in set(metadata["media"]) - set(skiped_media):
            formatted_content, _, _ = formatting_results[media]
            stats[media], url[media] = self.plugins[media].create_post(
                formatted_content, file_path=file_path
            )
        url_text = "\n".join(
            [
                f"- [{media}]({link})" if link else f"- {media}"
                for media, link in url.items()
                if stats[media]
            ]
        )
        message = (
            f"Below are the links of this post:\n`{file_path}`\n\n{url_text}"
            if url_text
            else f"Nothing created for this post:\n`{file_path}`"
        )

        processed_files[file_path] = stats
        print(f"Processed {file_path}: {stats}")
        return processed_files, message

    def process_files(self, files_to_process):
        processed_files = {}
        messages = ""
        processed_files_path = self.json_out
        if os.path.exists(processed_files_path):
            with open(processed_files_path, "r") as file:
                processed_files = json.load(file)
        for file_path in files_to_process:
            processed_files, message = self.process_markdown_file(
                file_path, processed_files
            )
            messages += f"{message}\n\n---\n"
            if not self.preview:
                with open(processed_files_path, "w") as file:
                    json.dump(processed_files, file)
        return messages


if __name__ == "__main__":
    parser = ArgumentParser(description="Galaxy Social.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--files", nargs="+", help="List of files to process")
    group.add_argument("--folder", help="Folder containing files to process")
    parser.add_argument("--preview", action="store_true", help="Preview the post")
    parser.add_argument(
        "--json-out",
        help="Output json file for processed files",
        default="processed_files.json",
    )
    args = parser.parse_args()

    if args.files:
        files_to_process = args.files
        files_not_exist = [
            file for file in files_to_process if not os.path.isfile(file)
        ]
        if files_not_exist:
            raise Exception(f"{', '.join(files_not_exist)} -> not exist.")
    elif args.folder:
        if not os.path.isdir(args.folder):
            raise Exception(f"{args.folder} -> not exist.")
        files_to_process = [
            os.path.join(root, filename)
            for root, _, files in os.walk(args.folder)
            for filename in filter(files, "*.md")
        ]
    if not files_to_process:
        print("No files to process.")
        sys.exit()
    print(f"Processing {len(files_to_process)} file(s): {files_to_process}\n")
    gs = galaxy_social(args.preview, args.json_out)
    message = gs.process_files(files_to_process)
    print(message)
