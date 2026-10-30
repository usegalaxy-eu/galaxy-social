import json
import os
import re
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone
from fnmatch import filter
from html.parser import HTMLParser
from importlib import import_module
from typing import Any, Dict
from zoneinfo import ZoneInfo

import emoji
import requests
from jsonschema import validate
from yaml import safe_load as yaml


def parse_schedule(value):
    """Return the scheduled time as a UTC datetime, or None if not scheduled."""
    if value is None:
        return None
    try:
        date_time, zone = str(value).strip().rsplit(" ", 1)
        local_time = datetime.strptime(date_time, "%Y-%m-%d %H:%M")
        time_zone = ZoneInfo(zone)
        schedule = local_time.replace(tzinfo=time_zone).astimezone(timezone.utc)
        if schedule.astimezone(time_zone).replace(tzinfo=None) != local_time:
            raise ValueError
        return schedule
    except Exception:
        raise ValueError(
            f"Invalid schedule `{value}`. Use a date, time and time zone like `schedule: 2026-10-20 07:00 UTC` or `schedule: 2026-10-20 09:00 Europe/Berlin`."
        )


def describe_schedule(schedule):
    local_times = " / ".join(
        f"{schedule.astimezone(ZoneInfo(zone)):%a %H:%M} {city}"
        for city, zone in [
            ("Berlin", "Europe/Berlin"),
            ("New York", "America/New_York"),
            ("Los Angeles", "America/Los_Angeles"),
        ]
    )
    return f"{schedule:%a %d %b %Y, %H:%M} UTC ({local_times})"


class ImgSyntaxConverter(HTMLParser):
    """Convert html img tags into markdown image syntax."""

    def reset(self):
        self.image_markdown = ""
        super().reset()

    def handle_starttag(self, tag, attrs):
        alt_text = src = ""
        for k, v in attrs:
            if k == "alt":
                alt_text = v
            elif k == "src":
                src = v
            self.image_markdown = f"![{alt_text}]({src})"

    def convert(self, img_tag):
        self.reset()
        self.feed(img_tag)
        return self.image_markdown


class galaxy_social:
    def __init__(self, preview: bool):
        self.preview = preview
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

    @classmethod
    def lint_markdown_file(cls, file_path: str):
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

    def parse_markdown_file(self, file_path: str):
        errors = ""
        result, status = self.lint_markdown_file(file_path)
        if not status:
            return (
                "",
                {},
                "There's an issue with your post file format. Please check that it follows the template.",
            )

        metadata, text = result

        if "media" not in metadata:
            return (
                "",
                {},
                "Missing media in metadata.\nAdd media to metadata.",
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

        try:
            metadata["schedule"] = parse_schedule(metadata.get("schedule"))
        except ValueError as e:
            errors += f"- {e}\n"

        # convert html img tags to markdown image syntax
        converter = ImgSyntaxConverter()
        text = re.sub(r"<img [^>]+>", lambda x: converter.convert(x[0]), text)

        # extract markdown image syntax elements
        image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        images = image_pattern.findall(text)
        plain_content = image_pattern.sub("", text).strip()

        # convert github emoji to unicode
        plain_content = emoji.emojize(plain_content, language="alias")

        metadata["images"] = [
            {"url": image[1], "alt_text": image[0]} for image in images
        ]

        return plain_content, metadata, errors

    def validate_images(self, metadata: Dict[str, Any]):
        """Download all images of a post and check that they are reachable and supported."""
        errors = ""
        for image in metadata["images"]:
            response = requests.get(image["url"])
            if response.status_code != 200:
                errors += f"- Failed to download image from URL: {image['url']}\n"

            if response.headers["Content-Type"] not in [
                "image/jpeg",
                "image/png",
                "image/gif",
            ]:
                errors += f"- URL does not point to a supported image file: {image['url']}\n"

        return errors

    def _mark_handled(self, file_path: str, processed_files: Dict[str, Any]):
        if not self.preview:
            # Mark as handled so scheduled runs don't retry a broken post every time
            processed_files.setdefault(file_path, {})

    def _format_for_media(
        self, file_path: str, media: Iterable[str], content: str, metadata: Dict[str, Any]
    ):
        formatting_results = {}
        for m in media:
            try:
                formatting_results[m] = self.plugins[m].format_content(
                    content=content,
                    mentions=metadata.get("mentions", {}).get(m, []),
                    hashtags=metadata.get("hashtags", {}).get(m, []),
                    images=metadata.get("images", []),
                )
            except Exception as e:
                raise Exception(f"Failed to format post for {file_path}.\n{e}")

        return formatting_results

    def process_markdown_file(self, file_path: str, processed_files: Dict[str, Any]):
        content, metadata, errors = self.parse_markdown_file(file_path)
        if errors:
            self._mark_handled(file_path, processed_files)
            return processed_files, f"⚠️ Failed to process `{file_path}`.\n{errors}"

        stats = processed_files[file_path] if file_path in processed_files else {}
        skipped_media = [media for media in metadata["media"] if stats.get(media)]
        remaining_media = set(metadata["media"]) - set(skipped_media)
        schedule = metadata["schedule"]
        is_future = schedule is not None and schedule > datetime.now(timezone.utc)

        if self.preview:
            errors += self.validate_images(metadata)
            if errors:
                return processed_files, f"⚠️ Failed to process `{file_path}`.\n{errors}"

            message = f"👋 Hello! I'm your friendly social media assistant. Below are the previews of this post:\n`{file_path}`"
            if schedule:
                message += f"\n\n⏰ Scheduled for {describe_schedule(schedule)}. "
                message += (
                    "After merge it will be posted around this time (it can be a bit late)."
                    if is_future
                    else "This time has already passed, so it will be posted right after merge."
                )
            if skipped_media:
                message += f"\n\nSkipping post to {', '.join(skipped_media)}. because it was already posted."

            formatting_results = self._format_for_media(
                file_path, remaining_media, content, metadata
            )
            for media in remaining_media:
                formatted_content, preview, warning = formatting_results[media]
                message += f"\n\n## {media}\n\n"
                message += preview
                if warning:
                    message += f"\nWARNING: {warning}"
            return processed_files, message.strip()

        # two early exit checks that are possible when NOT in preview mode
        # before doing image validation and formatting for different media
        if not remaining_media:
            return processed_files, f"Nothing created for this post:\n`{file_path}`"

        if is_future:
            if not stats:
                processed_files.pop(file_path, None)
            return (
                processed_files,
                f"⏰ This post is scheduled for {describe_schedule(schedule)}:\n`{file_path}`",
            )

        errors += self.validate_images(metadata)
        if errors:
            self._mark_handled(file_path, processed_files)
            return processed_files, f"⚠️ Failed to process `{file_path}`.\n{errors}"

        url = {}
        formatting_results = self._format_for_media(
            file_path, remaining_media, content, metadata
        )
        for media in remaining_media:
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
            f"🎉 The post is now online. The links may take a few minutes to become active. Here are the links for this post:\n`{file_path}`\n\n{url_text}"
            if url_text
            else f"Nothing created for this post:\n`{file_path}`"
        )

        processed_files[file_path] = stats
        print(f"Processed {file_path}: {stats}")
        return processed_files, message

    @classmethod
    def get_due_scheduled_files(cls, folder: str, processed_files_path: str):
        """Return posts in folder whose schedule has passed and that were not processed yet."""
        processed_files = {}
        if os.path.exists(processed_files_path):
            with open(processed_files_path, "r") as file:
                processed_files = json.load(file)
        due_files = []
        for root, _, files in os.walk(folder):
            for filename in filter(files, "*.md"):
                file_path = os.path.join(root, filename)
                if file_path in processed_files:
                    continue
                result, status = cls.lint_markdown_file(file_path)
                if not status:
                    continue
                try:
                    schedule = parse_schedule(result[0].get("schedule"))
                except ValueError:
                    continue
                if schedule and schedule <= datetime.now(timezone.utc):
                    due_files.append((schedule, file_path))
        return [file_path for _, file_path in sorted(due_files)]

    def process_files(self, files_to_process: list, processed_files_path: str):
        processed_files = {}
        messages = ""
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
    group.add_argument(
        "--scheduled", help="Folder to publish scheduled posts from that are due"
    )
    parser.add_argument("--preview", action="store_true", help="Preview the post")
    parser.add_argument(
        "--json-out",
        help="Output json file for processed files",
        default="processed_files.json",
    )
    args = parser.parse_args()
    gs = galaxy_social(args.preview)

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
    elif args.scheduled:
        files_to_process = gs.get_due_scheduled_files(args.scheduled, args.json_out)
    if not files_to_process:
        print("No files to process.")
        sys.exit()
    print(f"Processing {len(files_to_process)} file(s): {files_to_process}\n")
    message = gs.process_files(files_to_process, args.json_out)
    print(message)
