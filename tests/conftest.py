"""Shared fixtures for the galaxy_social unit tests.

The tests never touch the network and never read the repository's real
plugins.yml: fake plugins are injected into a galaxy_social instance
constructed from tests/data/plugins.yml, and the module-level `requests`
object is replaced by a fake.
"""
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

import lib.galaxy_social as galaxy_social_module
from lib.galaxy_social import galaxy_social

TEST_DATA = Path(__file__).parent / "data"


def png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (1, 1)).save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status_code, content_type, content):
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.content = content


class FakeRequests:
    """Stand-in for the `requests` module as used by galaxy_social."""

    def __init__(self, status_code=200, content_type="image/png"):
        self.status_code = status_code
        self.content_type = content_type
        self.content = png_bytes()
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return FakeResponse(self.status_code, self.content_type, self.content)


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
    """Install a FakeRequests instance as galaxy_social's `requests` module.

    Mutate `fake_requests.status_code` / `fake_requests.content` before
    exercising the code to simulate broken downloads or wrong file types.
    """
    fake = FakeRequests()
    monkeypatch.setattr(galaxy_social_module, "requests", fake)
    return fake
