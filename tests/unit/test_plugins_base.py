"""Unit tests for lib.plugins.base.

Image downloads never touch the network: download_image is replaced by fakes
that serve in-memory images (see the fixtures in tests/conftest.py).
"""
import json
import random
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

import lib.plugins.base as base_module
from lib.plugins.base import (
    TARGET_IMAGE_SIZES,
    image_format,
    load_image,
    prepare_images,
    shrink_to_limits,
    to_supported_image,
)
from lib.plugins.bluesky import IMAGE_SIZE_LIMIT as BS_IMAGE_SIZE_LIMIT


def noisy_image_bytes(width=900, height=900):
    """Random noise does not compress, so this PNG is larger than any limit below."""
    noisy = Image.frombytes("RGB", (width, height), random.Random(0).randbytes(width * height * 3))
    buffer = BytesIO()
    noisy.save(buffer, "PNG")
    return buffer.getvalue()


class TestShrinkToLimit:
    """shrink_to_limits yields at most one lower-quality JPEG per size limit."""

    @pytest.fixture
    def big_png(self):
        return noisy_image_bytes()

    def test_yields_one_image_for_each_limit(self, big_png):
        limits = [1_200_000, 450_000, 100_000]
        images = list(shrink_to_limits(big_png, limits))
        limits.sort()
        # the smallest image satisfies the smallest limit, the next smaller image
        # all the limits except the lowest, and so on
        for n, image in enumerate(reversed(images)):
            assert len(image) <= limits[n]
            decoded = Image.open(BytesIO(image))
            assert (decoded.format, decoded.size) == ("JPEG", (900, 900))

    def test_limits_may_be_given_unsorted_as_any_iterator(self, big_png):
        limits = [100_000, 450_000, 1_200_000]
        from_generator = list(shrink_to_limits(big_png, (limit for limit in limits)))
        assert from_generator == list(shrink_to_limits(big_png, reversed(limits)))
        assert len(from_generator) == len(limits)

    def test_no_images_when_the_content_fits_every_limit(self, image_bytes):
        content = image_bytes("PNG")
        assert list(shrink_to_limits(content, [10**6, 1000])) == []

    def test_limits_at_least_as_large_as_the_content_are_skipped(self, big_png):
        # the 2.4 MB content already fits 3 MB, so only the 450 KB limit needs a smaller image
        images = list(shrink_to_limits(big_png, [3_000_000, 450_000]))
        assert len(images) == 1
        assert len(images[0]) <= 450_000

    def test_unreachable_limit_does_not_block_the_other_limits(self, big_png):
        # no JPEG quality gets 900x900 noise under 1 KB, but the 1 MB limit still yields
        images = list(shrink_to_limits(big_png, [1_000_000, 1_000]))
        assert len(images) == 1
        assert len(images[0]) <= 1_000_000


class TestToSupportedImage:
    def test_jpeg_png_and_gif_are_kept_as_they_are(self, image_bytes):
        for name in ["JPEG", "PNG", "GIF"]:
            content = image_bytes(name)
            assert to_supported_image(content) == content

    def test_avif_and_webp_are_converted_to_jpeg(self, image_bytes):
        for name in ["AVIF", "WEBP"]:
            converted = to_supported_image(image_bytes(name))
            assert Image.open(BytesIO(converted)).format == "JPEG"

    def test_transparent_webp_is_converted_to_png(self, image_bytes):
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

    def test_other_formats_are_refused_without_decoding(self, image_bytes):
        for other in ["BMP", "TIFF", "TGA"]:
            with pytest.raises(ValueError):
                to_supported_image(image_bytes(other))

    def test_image_format_reads_only_the_first_bytes(self, image_bytes):
        for name in ["JPEG", "PNG", "GIF", "WEBP", "AVIF"]:
            assert image_format(image_bytes(name)) == name
        # mif1 is used by AVIF and HEIC: only AVIF when "avif" is a compatible brand
        assert image_format(b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00mif1avif") == "AVIF"
        assert image_format(b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00mif1heic") is None
        assert image_format(b"<html></html>") is None


class TestPrepareImages:
    """prepare_images writes the images and a manifest.json for load_image."""

    def test_small_variant_for_every_target_size(self, tmp_path, monkeypatch):
        monkeypatch.setattr(base_module, "TARGET_IMAGE_SIZES", [1_500_000, 450_000])
        content = noisy_image_bytes()
        monkeypatch.setattr(base_module, "download_image", lambda url: content)
        folder = tmp_path / "prepared"
        prepare_images(["https://example.test/big.png"], str(folder))
        manifest = json.loads((folder / "manifest.json").read_text())
        entry = manifest["https://example.test/big.png"]
        assert (entry["file"], entry["width"], entry["height"]) == ("0", 900, 900)
        assert entry["small"] == ["0-0", "0-1"]
        for n, name in enumerate(reversed(entry["small"])):
            path = Path(folder) / name
            assert path.stat().st_size <= TARGET_IMAGE_SIZES[n]
            image = Image.open(path)
            assert (image.format, image.size) == ("JPEG", (900, 900))

    def test_no_small_variants_when_the_content_is_small_enough(self, tmp_path, monkeypatch, image_bytes):
        monkeypatch.setattr(base_module, "download_image", lambda url: image_bytes("PNG"))
        folder = tmp_path / "prepared"
        prepare_images(["https://example.test/tiny.png"], str(folder))
        manifest = json.loads((folder / "manifest.json").read_text())
        entry = manifest["https://example.test/tiny.png"]
        assert "small" not in entry

    def test_duplicate_urls_are_prepared_once(self, tmp_path, monkeypatch, image_bytes):
        downloads = []

        def download(url):
            downloads.append(url)
            return image_bytes("PNG")

        monkeypatch.setattr(base_module, "download_image", download)
        folder = tmp_path / "prepared"
        prepare_images(["https://example.test/a.png"] * 2, str(folder))
        assert downloads == ["https://example.test/a.png"]
        manifest = json.loads((folder / "manifest.json").read_text())
        assert list(manifest) == ["https://example.test/a.png"]


class TestLoadImage:
    """Images are downloaded and converted in a job without tokens; the job that posts only checks them."""

    def test_prepared_images_are_loaded_without_opening_them(self, prepared, monkeypatch):
        folder, files = prepared
        monkeypatch.setattr(base_module.Image, "open", lambda *a, **k: pytest.fail("opened an image"))
        avif = load_image("https://example.test/a.avif", folder)
        assert (avif["mime"], avif["width"], avif["height"]) == ("image/jpeg", 8, 8)
        assert load_image("https://example.test/b.png", folder)["content"] == files["https://example.test/b.png"]

    def test_small_copy_for_bluesky(self, prepared):
        folder, _ = prepared
        big = load_image("https://example.test/big.png", folder)["content"]
        small = load_image("https://example.test/big.png", folder, max_size=BS_IMAGE_SIZE_LIMIT)
        assert len(big) > BS_IMAGE_SIZE_LIMIT >= len(small["content"])
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
        manifest["https://example.test/a.avif"]["file"] = "0-0"
        (folder / "manifest.json").write_text(json.dumps(manifest))
        (folder / "0-0").write_bytes(b"<html></html>")
        with pytest.raises(ValueError, match="Unexpected prepared file name"):
            load_image("https://example.test/b.png", str(folder))
        with pytest.raises(ValueError, match="not a JPEG, PNG or GIF"):
            load_image("https://example.test/a.avif", str(folder))

    def test_without_folder_images_are_downloaded_and_converted(self, monkeypatch, image_bytes):
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
