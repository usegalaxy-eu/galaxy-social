"""Unit tests for the galaxy_social class in lib.galaxy_social.

Real plugins are never instantiated: the tests register FakePlugin instances
under valid media names, and image downloads go through a fake `requests`.
"""
import json
from datetime import datetime, timezone

import pytest

import lib.galaxy_social as galaxy_social_module
from lib.galaxy_social import galaxy_social


def write_post(
    tmp_path,
    name="post.md",
    media=("markdown",),
    schedule=None,
    body="Body text",
    extra="",
):
    metadata = "media:\n" + "".join(f"  - {m}\n" for m in media)
    if schedule is not None:
        metadata += f"schedule: {schedule}\n"
    metadata += extra
    path = tmp_path / name
    path.write_text(f"---\n{metadata}---\n\n{body}\n")
    return path


class TestInit:
    def test_reads_config_from_plugins_path(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        assert set(gs.plugins_config_dict) == {"fake-a", "fake-env", "fake-broken"}

    def test_does_not_load_disabled_plugins(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        assert "fake-disabled" not in gs.plugins_config_dict

    def test_config_dict_keys_are_lowercase(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        assert all(key == key.lower() for key in gs.plugins_config_dict)

    def test_resolves_class_and_config(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        module_path, class_name, config = gs.plugins_config_dict["fake-a"]
        # module_path is prefixed with "lib." unless the script itself lives in
        # the lib directory; endswith keeps the assertion invocation-agnostic.
        assert module_path.endswith("plugins.markdown")
        assert class_name == "markdown_client"
        assert config == {"save_path": "markdown_cache"}

    def test_plugins_are_not_instantiated_until_needed(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        assert gs.plugins == {}

    def test_default_plugins_path_loads_repo_config(self):
        # Anchors the default (repo-relative) path resolution.
        gs = galaxy_social(preview=False)
        assert "markdown" in gs.plugins_config_dict


class TestInitPlugin:
    def test_instantiates_the_plugin_class(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        gs.init_plugin("fake-a")
        assert gs.plugins["fake-a"].save_path.endswith("markdown_cache")

    def test_env_var_is_substituted_in_config(self, test_plugins_path, monkeypatch):
        monkeypatch.setenv("GALAXY_SOCIAL_TEST_TOKEN", "secret")
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        gs.init_plugin("fake-env")
        # Documents the in-place mutation of the shared config dict.
        assert gs.plugins_config_dict["fake-env"][2]["token"] == "secret"

    def test_missing_env_var_is_reported(self, test_plugins_path, monkeypatch):
        monkeypatch.delenv("GALAXY_SOCIAL_TEST_TOKEN", raising=False)
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        with pytest.raises(Exception, match="GALAXY_SOCIAL_TEST_TOKEN"):
            gs.init_plugin("fake-env")

    def test_unimportable_class_is_reported(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        with pytest.raises(Exception, match="Invalid config"):
            gs.init_plugin("fake-broken")


class TestLintMarkdownFile:
    def test_valid_post_passes(self, tmp_path):
        gs = galaxy_social(preview=False)
        path = write_post(tmp_path)
        result, ok = gs.lint_markdown_file(str(path))
        assert ok
        metadata, text = result
        assert metadata["media"] == ["markdown"]
        assert "Body text" in text

    def test_file_without_front_matter_fails(self, tmp_path):
        gs = galaxy_social(preview=False)
        path = tmp_path / "bad.md"
        path.write_text("no front matter at all\n")
        result, ok = gs.lint_markdown_file(str(path))
        assert not ok
        assert isinstance(result, Exception)

    def test_schema_violation_fails(self, tmp_path):
        gs = galaxy_social(preview=False)
        path = tmp_path / "bad.md"
        path.write_text("---\nmedia: markdown\n---\n\nBody text\n")  # media must be a list
        result, ok = gs.lint_markdown_file(str(path))
        assert not ok


class TestParseMarkdownFile:
    def test_extracts_content_images_and_schedule(self, tmp_path, make_gs):
        gs, _ = make_gs()
        path = write_post(
            tmp_path,
            body="Hello :tada: ![alt](https://example.test/i.png)",
            schedule="2026-10-20 07:00 UTC",
        )
        content, metadata, errors = gs.parse_markdown_file(str(path))
        assert errors == ""
        assert content == "Hello 🎉"
        assert metadata["images"] == [
            {"url": "https://example.test/i.png", "alt_text": "alt"}
        ]
        assert metadata["schedule"] == datetime(2026, 10, 20, 7, 0, tzinfo=timezone.utc)

    def test_converts_html_img_tags(self, tmp_path, make_gs):
        gs, _ = make_gs()
        path = write_post(
            tmp_path,
            body='Before <img src="https://example.test/i.png" alt="pic"> after',
        )
        content, metadata, errors = gs.parse_markdown_file(str(path))
        assert errors == ""
        assert "<img" not in content
        assert "Before" in content and "after" in content
        assert metadata["images"] == [
            {"url": "https://example.test/i.png", "alt_text": "pic"}
        ]

    def test_lowercases_media_mentions_and_hashtags(self, tmp_path, make_gs):
        gs, _ = make_gs(names=("markdown", "mastodon"))
        extra = (
            "mentions:\n  MastoDon:\n    - SomeOne\n"
            "hashtags:\n  Markdown:\n    - tag1\n"
        )
        path = write_post(tmp_path, media=("markdown", "mastodon"), extra=extra)
        _, metadata, errors = gs.parse_markdown_file(str(path))
        assert errors == ""
        assert metadata["media"] == ["markdown", "mastodon"]
        assert metadata["mentions"] == {"mastodon": ["SomeOne"]}
        assert metadata["hashtags"] == {"markdown": ["tag1"]}

    def test_missing_media_reports_error(self, tmp_path, make_gs):
        gs, _ = make_gs()
        path = tmp_path / "bad.md"
        path.write_text("---\nmentions: {}\n---\n\nBody text\n")
        _, _, errors = gs.parse_markdown_file(str(path))
        assert "Missing media" in errors

    def test_invalid_media_reports_error(self, tmp_path, make_gs):
        gs, _ = make_gs()
        path = write_post(tmp_path, media=("nonexistent",))
        _, _, errors = gs.parse_markdown_file(str(path))
        assert "Invalid media" in errors
        assert "nonexistent" in errors

    def test_mentions_for_media_not_in_list_reports_error(self, tmp_path, make_gs):
        gs, _ = make_gs()
        extra = "mentions:\n  mastodon:\n    - SomeOne\n"
        path = write_post(tmp_path, media=("markdown",), extra=extra)
        _, _, errors = gs.parse_markdown_file(str(path))
        assert "Mentions for `mastodon`" in errors

    def test_hashtags_for_media_not_in_list_reports_error(self, tmp_path, make_gs):
        gs, _ = make_gs()
        extra = "hashtags:\n  mastodon:\n    - tag1\n"
        path = write_post(tmp_path, media=("markdown",), extra=extra)
        _, _, errors = gs.parse_markdown_file(str(path))
        assert "Hashtags for `mastodon`" in errors

    def test_invalid_schedule_reports_error(self, tmp_path, make_gs):
        gs, _ = make_gs()
        path = write_post(tmp_path, schedule="nonsense")
        _, _, errors = gs.parse_markdown_file(str(path))
        assert "Invalid schedule" in errors

    def test_does_not_download_images(self, tmp_path, make_gs, monkeypatch):
        # Image validation lives in validate_images(); parsing must stay offline.
        class Boom:
            def get(self, *args, **kwargs):
                raise AssertionError("parse_markdown_file must not download images")

        monkeypatch.setattr(galaxy_social_module, "requests", Boom())
        gs, _ = make_gs()
        path = write_post(tmp_path, body="Body ![alt](https://example.test/i.png)")
        content, metadata, errors = gs.parse_markdown_file(str(path))
        assert errors == ""
        assert len(metadata["images"]) == 1


class TestValidateImages:
    def parse_post_with_image(self, tmp_path, make_gs):
        gs, _ = make_gs()
        path = write_post(tmp_path, body="Body ![alt](https://example.test/i.png)")
        _, metadata, errors = gs.parse_markdown_file(str(path))
        assert errors == ""
        return gs, metadata

    def test_no_images_means_no_errors(self, tmp_path, make_gs):
        gs, _ = make_gs()
        assert gs.validate_images({"images": []}) == ""

    def test_reachable_image_passes(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        assert gs.validate_images(metadata) == ""
        assert fake_requests.calls == ["https://example.test/i.png"]

    def test_failed_download_is_reported(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        fake_requests.status_code = 404
        errors = gs.validate_images(metadata)
        assert "Failed to download image from URL: https://example.test/i.png" in errors

    def test_unsupported_content_type_is_reported(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        fake_requests.content_type = "text/html"
        errors = gs.validate_images(metadata)
        assert "does not point to a supported image file" in errors


class TestProcessMarkdownFilePublish:
    def test_posts_to_all_media_and_records_stats(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False, names=("markdown", "mastodon"))
        path = write_post(tmp_path, media=("markdown", "mastodon"), schedule="2020-01-01 00:00 UTC")
        processed = {}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert fakes["markdown"].post_calls and fakes["mastodon"].post_calls
        assert processed[str(path)] == {"markdown": True, "mastodon": True}
        assert "🎉" in message

    def test_skips_future_scheduled_post(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        path = write_post(tmp_path, schedule="2099-01-01 00:00 UTC")
        processed = {}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert "⏰ This post is scheduled" in message
        assert fakes["markdown"].post_calls == []
        assert str(path) not in processed

    def test_future_post_does_not_download_images(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        path = write_post(
            tmp_path,
            schedule="2099-01-01 00:00 UTC",
            body="Body ![alt](https://example.test/i.png)",
        )
        gs.process_markdown_file(str(path), {})
        assert fake_requests.calls == []

    def test_skips_media_that_were_already_posted(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False, names=("markdown", "mastodon"))
        path = write_post(tmp_path, media=("markdown", "mastodon"), schedule="2020-01-01 00:00 UTC")
        processed = {str(path): {"markdown": True}}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert fakes["markdown"].post_calls == []
        assert len(fakes["mastodon"].post_calls) == 1
        assert processed[str(path)] == {"markdown": True, "mastodon": True}

    def test_fully_posted_file_is_skipped_cheaply(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        path = write_post(
            tmp_path,
            schedule="2020-01-01 00:00 UTC",
            body="Body ![alt](https://example.test/i.png)",
        )
        processed = {str(path): {"markdown": True}}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert "Nothing created for this post" in message
        assert fake_requests.calls == []  # no image downloads
        assert fakes["markdown"].post_calls == []

    def test_broken_image_marks_post_handled(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        path = write_post(
            tmp_path,
            schedule="2020-01-01 00:00 UTC",
            body="Body ![alt](https://example.test/i.png)",
        )
        fake_requests.status_code = 404
        processed = {}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert "⚠️" in message
        assert processed[str(path)] == {}
        assert fakes["markdown"].post_calls == []

    def test_format_failure_posts_nothing(self, tmp_path, make_gs, fake_requests):
        # A formatting error for one media must happen before ANY create_post,
        # so no successful post can lose its record to a later crash.
        gs, fakes = make_gs(preview=False, names=("markdown", "mastodon"))
        fakes["mastodon"].format_error = Exception("matrix lookup failed")
        path = write_post(tmp_path, media=("markdown", "mastodon"), schedule="2020-01-01 00:00 UTC")
        with pytest.raises(Exception, match="Failed to format post"):
            gs.process_markdown_file(str(path), {})
        assert fakes["markdown"].post_calls == []


class TestProcessMarkdownFilePreview:
    def test_shows_previews_without_posting(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=True)
        path = write_post(tmp_path, schedule="2026-10-20 07:00 UTC")
        processed = {}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert "👋 Hello!" in message
        assert "## markdown" in message
        assert "PREVIEW" in message
        assert fakes["markdown"].post_calls == []
        assert processed == {}  # preview never writes state

    def test_shows_schedule_note_for_future_post(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=True)
        path = write_post(tmp_path, schedule="2099-01-01 00:00 UTC")
        _, message = gs.process_markdown_file(str(path), {})
        assert "⏰ Scheduled for" in message
        assert "After merge it will be posted around this time" in message

    def test_shows_note_when_schedule_has_passed(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=True)
        path = write_post(tmp_path, schedule="2020-01-01 00:00 UTC")
        _, message = gs.process_markdown_file(str(path), {})
        assert "This time has already passed" in message

    def test_reports_skipped_media(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=True, names=("markdown", "mastodon"))
        path = write_post(tmp_path, media=("markdown", "mastodon"))
        processed = {str(path): {"markdown": True}}
        _, message = gs.process_markdown_file(str(path), processed)
        assert "Skipping post to markdown" in message
        assert fakes["markdown"].format_calls == []  # skipped media is not formatted
        assert "## mastodon" in message

    def test_broken_image_gates_the_preview(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=True)
        path = write_post(tmp_path, body="Body ![alt](https://example.test/i.png)")
        fake_requests.status_code = 404
        _, message = gs.process_markdown_file(str(path), {})
        assert "⚠️" in message
        assert "PREVIEW" not in message


class TestProcessFiles:
    def test_aggregates_messages_and_writes_state(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        post1 = write_post(tmp_path, "a.md", schedule="2020-01-01 00:00 UTC")
        post2 = write_post(tmp_path, "b.md", schedule="2020-01-02 00:00 UTC")
        state_path = tmp_path / "processed.json"
        message = gs.process_files([str(post1), str(post2)], str(state_path))
        assert "a.md" in message and "b.md" in message
        state = json.loads(state_path.read_text())
        assert state[str(post1)] == {"markdown": True}
        assert state[str(post2)] == {"markdown": True}

    def test_loads_existing_state(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=False)
        post = write_post(tmp_path, schedule="2020-01-01 00:00 UTC")
        state_path = tmp_path / "processed.json"
        state_path.write_text(json.dumps({"some/other/post.md": {"markdown": True}}))
        gs.process_files([str(post)], str(state_path))
        state = json.loads(state_path.read_text())
        assert state["some/other/post.md"] == {"markdown": True}
        assert state[str(post)] == {"markdown": True}

    def test_preview_does_not_write_state(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=True)
        post = write_post(tmp_path)
        state_path = tmp_path / "processed.json"
        gs.process_files([str(post)], str(state_path))
        assert not state_path.exists()


class TestGetDueScheduledFiles:
    def test_returns_only_due_unprocessed_files_sorted_by_schedule(self, tmp_path, make_gs):
        gs, _ = make_gs()
        posts = tmp_path / "posts"
        posts.mkdir()
        later = write_post(posts, "later.md", schedule="2020-01-02 00:00 UTC")
        earlier = write_post(posts, "earlier.md", schedule="2020-01-01 00:00 UTC")
        write_post(posts, "future.md", schedule="2099-01-01 00:00 UTC")
        write_post(posts, "badschedule.md", schedule="nonsense")
        (posts / "broken.md").write_text("no front matter\n")
        already_done = write_post(posts, "done.md", schedule="2020-01-01 00:00 UTC")
        state_path = tmp_path / "processed.json"
        state_path.write_text(json.dumps({str(already_done): {"markdown": True}}))

        due = gs.get_due_scheduled_files(str(posts), str(state_path))

        assert due == [str(earlier), str(later)]

    def test_empty_folder_returns_nothing(self, tmp_path, make_gs):
        gs, _ = make_gs()
        posts = tmp_path / "posts"
        posts.mkdir()
        state_path = tmp_path / "processed.json"
        assert gs.get_due_scheduled_files(str(posts), str(state_path)) == []
