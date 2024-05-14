import json
import os
import sys
from argparse import ArgumentParser
from fnmatch import filter
from importlib import import_module

from bs4 import BeautifulSoup
from jsonschema import validate
from markdown import markdown
from yaml import safe_load as yaml


class galaxy_social:
    def __init__(self, preview: bool, json_out: str):
        self.preview = preview
        self.json_out = json_out
        plugins_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "plugins.yml"
        )
        with open(plugins_path, "r") as file:
            self.plugins_config = yaml(file)

        self.plugins = {}
        for plugin in self.plugins_config["plugins"]:
            if preview and plugin["name"].lower() != "markdown":
                continue

            if plugin["enabled"]:
                module_name, class_name = plugin["class"].rsplit(".", 1)
                try:
                    module_path = f"{'lib.' if not os.path.dirname(os.path.abspath(sys.argv[0])).endswith('lib') else ''}plugins.{module_name}"
                    module = import_module(module_path)
                    plugin_class = getattr(module, class_name)
                except Exception as e:
                    raise Exception(
                        f"Error with plugin {module_name}.{class_name}.\n{e}"
                    )

                config = {}
                if plugin.get("config"):
                    for key, value in plugin["config"].items():
                        if isinstance(value, str) and value.startswith("$"):
                            try:
                                config[key] = os.environ[value[1:]]
                            except KeyError:
                                raise Exception(
                                    f"Missing environment variable {value[1:]}."
                                )
                        else:
                            config[key] = value
                else:
                    raise Exception(f"Missing config for {module_name}.{class_name}.")

                try:
                    self.plugins[plugin["name"].lower()] = plugin_class(**config)
                except Exception as e:
                    raise Exception(
                        f"Invalid config for {module_name}.{class_name}.\nChange configs in plugins.yml.\n{e}"
                    )

    def parse_markdown_file(self, file_path):
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
        except Exception as e:
            raise Exception(f"Invalid metadata in {file_path}.\n{e}")

        metadata["media"] = [media.lower() for media in metadata["media"]]

        for media in metadata["media"]:
            if not any(
                item["name"].lower() == media for item in self.plugins_config["plugins"]
            ):
                raise Exception(f"Invalid media {media}.")

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
        markdown_content = markdown(text.strip())
        plain_content = BeautifulSoup(markdown_content, "html.parser").get_text(
            separator="\n"
        )
        return plain_content, metadata

    def process_markdown_file(self, file_path, processed_files):
        content, metadata = self.parse_markdown_file(file_path)
        if self.preview:
            try:
                _, _, message = self.plugins["markdown"].create_post(
                    content=content,
                    mentions=[],
                    hashtags=[],
                    images=metadata.get("images", []),
                    media=metadata["media"],
                    preview=True,
                    file_path=file_path,
                )
                return processed_files, message
            except Exception as e:
                raise Exception(f"Failed to create preview for {file_path}.\n{e}")
        stats = {}
        url = {}
        if file_path in processed_files:
            stats = processed_files[file_path]
        for media in metadata["media"]:
            if file_path in processed_files and media in processed_files[file_path]:
                continue
            mentions = metadata.get("mentions", {}).get(media, [])
            hashtags = metadata.get("hashtags", {}).get(media, [])
            images = metadata.get("images", [])
            stats[media], url[media] = self.plugins[media].create_post(
                content, mentions, hashtags, images, file_path=file_path
            )
        url_text = "\n".join(
            [f"[{media}]({link})" for media, link in url.items() if link]
        )
        message = f"Posted to:\n\n{url_text}" if url_text else "No posts created."

        processed_files[file_path] = stats
        print(f"Processed {file_path}: {stats}")
        return processed_files, message

    def process_files(self, files_to_process):
        processed_files = {}
        messages = "---\n"
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
