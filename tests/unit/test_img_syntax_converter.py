"""Tests for the ImgSyntaxConverter helper in lib.galaxy_social."""
from lib.galaxy_social import ImgSyntaxConverter


def test_converts_img_tag_to_markdown():
    converter = ImgSyntaxConverter()
    assert converter.convert('<img src="https://example.test/y.png" alt="some alt">') == (
        "![some alt](https://example.test/y.png)"
    )


def test_attribute_order_does_not_matter():
    converter = ImgSyntaxConverter()
    assert converter.convert('<img alt="alt" src="https://example.test/y.png">') == (
        "![alt](https://example.test/y.png)"
    )


def test_missing_alt_text_gives_empty_alt():
    converter = ImgSyntaxConverter()
    assert converter.convert('<img src="https://example.test/y.png">') == (
        "![](https://example.test/y.png)"
    )


def test_converter_is_reusable_between_calls():
    converter = ImgSyntaxConverter()
    first = converter.convert('<img src="https://a/1.png" alt="one">')
    second = converter.convert('<img src="https://b/2.png" alt="two">')
    assert first == "![one](https://a/1.png)"
    assert second == "![two](https://b/2.png)"
