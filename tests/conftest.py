"""Shared fixtures for the galaxy_social unit tests.

The tests never touch the network and never read the repository's real
plugins.yml: fake plugins are injected into a galaxy_social instance
constructed from tests/data/plugins.yml, and the module-level `requests`
object is replaced by a fake.
"""
import random
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

import lib.galaxy_social as galaxy_social_module
import lib.plugins.base as base_module
from lib.galaxy_social import galaxy_social
from lib.plugins.base import prepare_images

TEST_DATA = Path(__file__).parent / "data"


def _image_bytes(image_format, mode="RGB"):
    buffer = BytesIO()
    Image.new(mode, (8, 8)).save(buffer, image_format)
    return buffer.getvalue()


@pytest.fixture
def image_bytes():
    """Factory for a tiny (8x8) in-memory image in a given PIL format."""
    return _image_bytes


class FakeRequests:
    """Stand-in for image downloads (download_image) as used by galaxy_social."""

    def __init__(self, status_code=200, content_type="image/png"):
        self.status_code = status_code
        self.content_type = content_type
        self.content = _image_bytes("PNG")
        self.calls = []

    def download_image(self, url):
        self.calls.append(url)
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")
        return self.content


class FakePlugin:
    """Minimal stand-in for a social media plugin."""

    def __init__(
        self,
        name,
        format_result=("formatted", "PREVIEW", ""),
        post_result=(True, "https://example.test/1"),
        format_error=None,
        post_error=None,
    ):
        self.name = name
        self.format_result = format_result
        self.post_result = post_result
        self.format_error = format_error
        self.post_error = post_error
        self.format_calls = []
        self.post_calls = []

    def format_content(self, content, mentions, hashtags, images, **kwargs):
        self.format_calls.append(
            {
                "content": content,
                "mentions": mentions,
                "hashtags": hashtags,
                "images": images,
            }
        )
        if self.format_error:
            raise self.format_error
        return self.format_result

    def create_post(self, formatted_content, **kwargs):
        self.post_calls.append(formatted_content)
        if self.post_error:
            raise self.post_error
        return self.post_result


@pytest.fixture
def test_plugins_path():
    """Path to the hermetic plugins.yml used by the tests."""
    return str(TEST_DATA / "plugins.yml")


@pytest.fixture
def make_gs():
    """Factory for a galaxy_social instance with fake plugins registered.

    The instance is built from the test plugins.yml; the requested media names
    are then registered directly (config entry + FakePlugin instance), so
    neither the real plugin configuration nor real plugins are involved.
    """

    def _make(preview=False, names=("markdown",), plugins_path=None):
        if plugins_path is None:
            plugins_path = str(TEST_DATA / "plugins.yml")
        gs = galaxy_social(preview=preview, plugins_path=plugins_path)
        fakes = {}
        for name in names:
            fake = FakePlugin(name)
            gs.plugins_config_dict[name] = ("lib.plugins.markdown", "markdown_client", {})
            gs.plugins[name] = fake
            fakes[name] = fake
        return gs, fakes

    return _make


@pytest.fixture
def fake_requests(monkeypatch):
    """Install a FakeRequests instance for galaxy_social's image downloads.

    Mutate `fake_requests.status_code` / `fake_requests.content` before
    exercising the code to simulate broken downloads or wrong file types.
    """
    fake = FakeRequests()
    monkeypatch.setattr(galaxy_social_module, "download_image", fake.download_image)
    return fake


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    """Folder with images prepared by prepare_images, plus the served contents.

    The files were made in a job without tokens (download_image serves them
    from memory); big.png is random noise, which does not compress, so it is
    larger than Bluesky's size limit and gets a small JPEG variant.
    """
    noisy = Image.frombytes("RGB", (900, 900), random.Random(0).randbytes(900 * 900 * 3))
    big = BytesIO()
    noisy.save(big, "PNG")
    files = {
        "https://example.test/a.avif": _image_bytes("AVIF"),
        "https://example.test/b.png": _image_bytes("PNG"),
        "https://example.test/big.png": big.getvalue(),
        "https://example.test/page.jpg": b"<html></html>",
    }
    monkeypatch.setattr(base_module, "download_image", lambda url: files[url])
    folder = tmp_path / "prepared"
    prepare_images(list(files) + ["https://example.test/b.png"], str(folder))
    return str(folder), files
