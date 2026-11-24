"""Unit tests for the galaxy_social class in lib.galaxy_social.

Real plugins are never instantiated: the tests register FakePlugin instances
under valid media names, and image downloads go through a fake `requests`.
"""
import json
import random
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO

import pytest
from PIL import Image

import lib.galaxy_social as galaxy_social_module
from lib.galaxy_social import galaxy_social
import lib.plugins.base as base_module
from lib.plugins.base import image_format, load_image, prepare_images, to_supported_image


def image_bytes(image_format, mode="RGB"):
    buffer = BytesIO()
    Image.new(mode, (8, 8)).save(buffer, image_format)
    return buffer.getvalue()


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
        assert set(gs.plugins_config_dict) == {
            "fake-a",
            "fake-env",
            "fake-broken",
            "fake-uppercase",  # "Fake-Uppercase" in the file, lowercased on load
        }

    def test_does_not_load_disabled_plugins(self, test_plugins_path):
        gs = galaxy_social(preview=False, plugins_path=test_plugins_path)
        assert "fake-disabled" not in gs.plugins_config_dict

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
        # Intentional test of the default (repo-relative) path resolution.
        # This specific test needs to read the default config and,
        # for now, will fail if the config is corrupted or lacks the
        # "markdown" plugin.
        # TO DO: code refactoring to let us test path resolution in isolation
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
        gs = galaxy_social  # since this is testing a classmethod, instantiation isn't needed here
        path = write_post(tmp_path)
        result, ok = gs.lint_markdown_file(str(path))
        assert ok
        metadata, text = result
        assert metadata["media"] == ["markdown"]
        assert "Body text" in text

    def test_file_without_front_matter_fails(self, tmp_path):
        gs = galaxy_social  # testing a classmethod
        path = tmp_path / "bad.md"
        path.write_text("no front matter at all\n")
        result, ok = gs.lint_markdown_file(str(path))
        assert not ok
        assert isinstance(result, Exception)

    def test_schema_violation_fails(self, tmp_path):
        gs = galaxy_social  # testing a classmethod
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
        # The front matter uses mixed-case names; the fakes are registered under
        # the lowercase forms, so matching keys prove the lowercasing happened.
        gs, _ = make_gs(names=("markdown", "mastodon"))
        extra = (
            "mentions:\n  MastoDon:\n    - SomeOne\n"
            "hashtags:\n  Markdown:\n    - tag1\n"
        )
        path = write_post(tmp_path, media=("Markdown", "MastoDon"), extra=extra)
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
        def boom(*args, **kwargs):
            raise AssertionError("parse_markdown_file must not download images")

        monkeypatch.setattr(galaxy_social_module, "download_image", boom)
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

    def test_non_image_is_reported_even_with_image_header(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        fake_requests.content_type = "image/jpeg"
        fake_requests.content = b"<html></html>"
        errors = gs.validate_images(metadata)
        assert "does not point to a supported image file" in errors

    def test_avif_sent_as_jpeg_is_accepted(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        fake_requests.content_type = "image/jpeg"
        fake_requests.content = image_bytes("AVIF")
        assert gs.validate_images(metadata) == ""

    def test_image_is_not_opened(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        # starts like an AVIF but is broken: only the first bytes are checked
        fake_requests.content = b"\x00\x00\x00\x14ftypavif\x00\x00\x00\x00broken"
        assert gs.validate_images(metadata) == ""

    def test_other_image_formats_are_reported(self, tmp_path, make_gs, fake_requests):
        gs, metadata = self.parse_post_with_image(tmp_path, make_gs)
        fake_requests.content = image_bytes("BMP")
        assert "does not point to a supported image file" in gs.validate_images(metadata)


class TestToSupportedImage:
    def test_jpeg_png_and_gif_are_kept_as_they_are(self):
        for name in ["JPEG", "PNG", "GIF"]:
            content = image_bytes(name)
            assert to_supported_image(content) == content

    def test_avif_and_webp_are_converted_to_jpeg(self):
        for name in ["AVIF", "WEBP"]:
            converted = to_supported_image(image_bytes(name))
            assert Image.open(BytesIO(converted)).format == "JPEG"

    def test_transparent_webp_is_converted_to_png(self):
        converted = to_supported_image(image_bytes("WEBP", mode="RGBA"))
        assert Image.open(BytesIO(converted)).format == "PNG"

    def test_svg_is_recognised_and_converted_to_png(self, monkeypatch):
        svg = b'<?xml version="1.0"?>\n<!-- logo -->\n<!DOCTYPE svg>\n<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="40" height="20"/></svg>'
        assert image_format(svg) == "SVG"
        assert image_format(b"<!DOCTYPE html><html><body><svg></svg></body></html>") is None
        converted = Image.open(BytesIO(to_supported_image(svg)))
        assert (converted.format, converted.size) == ("PNG", (1600, 800))

    def test_svg_links_are_not_loaded(self, monkeypatch):
        import cairosvg.url

        monkeypatch.setattr(cairosvg.url, "urlopen", lambda *a, **k: pytest.fail("the SVG loaded a link"))
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><image href="https://example.test/x.png" width="10" height="10"/></svg>'
        assert Image.open(BytesIO(to_supported_image(svg))).format == "PNG"

    def test_other_formats_are_refused_without_decoding(self):
        for other in ["BMP", "TIFF", "TGA"]:
            with pytest.raises(ValueError):
                to_supported_image(image_bytes(other))

    def test_image_format_reads_only_the_first_bytes(self):
        for name in ["JPEG", "PNG", "GIF", "WEBP", "AVIF"]:
            assert image_format(image_bytes(name)) == name
        # mif1 is used by AVIF and HEIC: only AVIF when "avif" is a compatible brand
        assert image_format(b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00mif1avif") == "AVIF"
        assert image_format(b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00mif1heic") is None
        assert image_format(b"<html></html>") is None


class TestPreparedImages:
    """Images are downloaded and converted in a job without tokens; the job that posts only checks them."""

    @pytest.fixture
    def prepared(self, tmp_path, monkeypatch):
        # random noise does not compress, so this PNG is larger than Bluesky's limit
        noisy = Image.frombytes("RGB", (900, 900), random.Random(0).randbytes(900 * 900 * 3))
        big = BytesIO()
        noisy.save(big, "PNG")
        files = {
            "https://example.test/a.avif": image_bytes("AVIF"),
            "https://example.test/b.png": image_bytes("PNG"),
            "https://example.test/big.png": big.getvalue(),
            "https://example.test/page.jpg": b"<html></html>",
        }
        monkeypatch.setattr(base_module, "download_image", lambda url: files[url])
        folder = tmp_path / "prepared"
        prepare_images(list(files) + ["https://example.test/b.png"], str(folder))
        return str(folder), files

    def test_prepared_images_are_loaded_without_opening_them(self, prepared, monkeypatch):
        folder, files = prepared
        monkeypatch.setattr(base_module.Image, "open", lambda *a, **k: pytest.fail("opened an image"))
        avif = load_image("https://example.test/a.avif", folder)
        assert (avif["mime"], avif["width"], avif["height"]) == ("image/jpeg", 8, 8)
        assert load_image("https://example.test/b.png", folder)["content"] == files["https://example.test/b.png"]

    def test_small_copy_for_bluesky(self, prepared):
        folder, _ = prepared
        big = load_image("https://example.test/big.png", folder)["content"]
        small = load_image("https://example.test/big.png", folder, small=True)
        assert len(big) > base_module.BLUESKY_IMAGE_LIMIT >= len(small["content"])
        assert small["mime"] == "image/jpeg"

    def test_failed_image_is_reported(self, prepared):
        folder, _ = prepared
        with pytest.raises(ValueError, match="Not a JPEG"):
            load_image("https://example.test/page.jpg", folder)
        with pytest.raises(ValueError, match="not prepared"):
            load_image("https://example.test/other.png", folder)

    def test_prepared_files_are_not_trusted(self, prepared):
        folder, _ = prepared
        folder = Path(folder)
        manifest = json.loads((folder / "manifest.json").read_text())
        manifest["https://example.test/b.png"]["file"] = "../../etc/passwd"
        manifest["https://example.test/a.avif"]["file"] = "0-small"
        (folder / "manifest.json").write_text(json.dumps(manifest))
        (folder / "0-small").write_bytes(b"<html></html>")
        with pytest.raises(ValueError, match="Unexpected prepared file name"):
            load_image("https://example.test/b.png", str(folder))
        with pytest.raises(ValueError, match="not a JPEG, PNG or GIF"):
            load_image("https://example.test/a.avif", str(folder))

    def test_validate_images_uses_prepared_images(self, prepared, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs()
        gs.prepared_images = prepared[0]
        metadata = {"images": [{"url": "https://example.test/a.avif"}, {"url": "https://example.test/page.jpg"}]}
        errors = gs.validate_images(metadata)
        assert fake_requests.calls == []
        assert "page.jpg" in errors and "a.avif" not in errors

    def test_scheduled_post_with_images_not_prepared_waits_for_next_run(self, prepared, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        gs.prepared_images = prepared[0]
        path = write_post(tmp_path, schedule="2020-01-01 00:00 UTC", body="Body ![x](https://example.test/new.png)")
        processed, message = gs.process_markdown_file(str(path), {})
        assert message == "" and processed == {} and fakes["markdown"].post_calls == []

    def test_other_post_with_images_not_prepared_is_reported(self, prepared, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False)
        gs.prepared_images = prepared[0]
        path = write_post(tmp_path, body="Body ![x](https://example.test/new.png)")
        processed, message = gs.process_markdown_file(str(path), {})
        assert "Could not use image https://example.test/new.png: not prepared" in message
        assert processed == {str(path): {}} and fakes["markdown"].post_calls == []

    def test_nothing_is_posted_when_preparing_failed(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False, names=("markdown", "mastodon"))
        gs.prepared_images = str(tmp_path / "missing")  # no manifest: the prepare job failed
        path = write_post(tmp_path, media=("markdown", "mastodon"), body="Body ![x](https://example.test/a.png)")
        processed, message = gs.process_markdown_file(str(path), {})
        assert "Could not prepare the images" in message
        assert processed == {str(path): {"markdown": False, "mastodon": False}}
        assert fakes["markdown"].post_calls == fakes["mastodon"].post_calls == []

    def test_without_folder_images_are_downloaded_and_converted(self, monkeypatch):
        monkeypatch.setattr(base_module, "download_image", lambda url: image_bytes("AVIF"))
        image = load_image("https://example.test/a.avif")
        assert (image["mime"], image["width"]) == ("image/jpeg", 8)


class TestImageDownloads:
    class Response:
        def __init__(self, chunks=(), text="", status_code=200):
            self.chunks, self.text, self.status_code = chunks, text, status_code

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            return iter(self.chunks)

    def test_download_stops_at_the_size_limit(self, monkeypatch):
        monkeypatch.setattr(base_module, "MAX_IMAGE_BYTES", 10)
        monkeypatch.setattr(base_module.requests, "get", lambda *a, **k: self.Response(chunks=[b"123456", b"789012"]))
        with pytest.raises(ValueError, match="larger"):
            base_module.download_image("https://example.test/huge.png")

    def test_link_image_url_reads_og_image(self, monkeypatch):
        page = '<html><head><meta property="og:image" content="https://example.test/card.webp"></head></html>'
        monkeypatch.setattr(base_module.requests, "get", lambda *a, **k: self.Response(text=page))
        assert base_module.link_image_url("https://example.test/page") == "https://example.test/card.webp"
        monkeypatch.setattr(base_module.requests, "get", lambda *a, **k: self.Response(text="<html></html>"))
        assert base_module.link_image_url("https://example.test/page") is None

    def test_urls_to_prepare(self, tmp_path):
        body = "See https://example.test/page.\n\n![alt](https://example.test/i.png)"
        path = write_post(tmp_path, body=body)
        assert galaxy_social.urls_to_prepare(str(path)) == (["https://example.test/i.png"], ["https://example.test/page"])
        later = write_post(tmp_path, name="later.md", schedule="2099-01-01 00:00 UTC", body=body)
        assert galaxy_social.urls_to_prepare(str(later)) == ([], [])


class TestProcessMarkdownFilePublish:
    def test_posts_to_all_media_and_records_stats(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False, names=("markdown", "mastodon"))
        path = write_post(tmp_path, media=("markdown", "mastodon"), schedule="2020-01-01 00:00 UTC")
        processed = {}
        processed, message = gs.process_markdown_file(str(path), processed)
        assert fakes["markdown"].post_calls and fakes["mastodon"].post_calls
        assert processed[str(path)] == {"markdown": True, "mastodon": True}
        assert "🎉" in message

    def test_failing_platform_does_not_stop_the_others(self, tmp_path, make_gs, fake_requests):
        gs, fakes = make_gs(preview=False, names=("markdown", "mastodon"))
        fakes["markdown"].post_error = RuntimeError("boom")
        path = write_post(tmp_path, media=("markdown", "mastodon"), schedule="2020-01-01 00:00 UTC")
        processed, _ = gs.process_markdown_file(str(path), {})
        assert len(fakes["mastodon"].post_calls) == 1
        assert processed[str(path)] == {"markdown": False, "mastodon": True}
        assert gs.crashed_files == [str(path)]

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

    def test_warns_when_hub_page_was_already_posted(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=True, names=("markdown", "mastodon"))
        earlier = write_post(tmp_path, "earlier.md", media=("markdown", "mastodon"), body="See http://www.galaxyproject.org/news/2026-06-09-rnaseq.")
        path = write_post(tmp_path, media=("markdown", "mastodon"), body="New https://galaxyproject.org/news/2026-06-09-rnaseq/")
        processed = {str(earlier): {"markdown": True, "mastodon": "https://mstdn.science/@g/1"}}
        _, message = gs.process_markdown_file(str(path), processed)
        assert (
            f"⚠️ This links to https://galaxyproject.org/news/2026-06-09-rnaseq/, which was already posted from `{earlier}` to: markdown, [mastodon](https://mstdn.science/@g/1)."
            in message
        )

    def test_no_repost_warning_without_a_published_account_in_common(self, tmp_path, make_gs, fake_requests):
        gs, _ = make_gs(preview=True, names=("markdown", "mastodon"))
        body = "https://galaxyproject.org/events/gcc2026/"
        other_account = write_post(tmp_path, "a.md", media=("mastodon",), body=body)
        failed = write_post(tmp_path, "b.md", body=body)
        path = write_post(tmp_path, body=body)
        processed = {
            str(other_account): {"mastodon": True},
            str(failed): {"markdown": False},
            "posts/deleted.md": {"markdown": True},
        }
        _, message = gs.process_markdown_file(str(path), processed)
        assert "⚠️" not in message

    def test_hub_links_are_only_news_and_event_pages(self):
        assert galaxy_social.hub_links(
            "https://galaxyproject.org/images/news/a.png https://training.galaxyproject.org/news/b/ "
            "https://galaxyproject.org/news/ https://galaxyproject.org/projects/c/ "
            "https://GalaxyProject.org/Events/D/#register"
        ) == {"galaxyproject.org/events/d"}


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
