import pytest

from app.content.domain.body import (
    MAX_ARTICLE_BLOCKS,
    MAX_BODY_BYTES,
    ContentBody,
    ContentBodyNotPublishableError,
    InvalidContentBodyError,
)


def article(blocks):
    return {"schema_version": 1, "kind": "article", "blocks": blocks}


def resource(url=None, description=""):
    return {
        "schema_version": 1,
        "kind": "resource",
        "resource": {"url": url, "description": description},
    }


def test_empty_draft_bodies_are_valid_but_not_publishable() -> None:
    for body in (ContentBody.article_empty(), ContentBody.resource_empty()):
        with pytest.raises(ContentBodyNotPublishableError):
            body.require_publishable()


@pytest.mark.parametrize(
    "block",
    [
        {"type": "paragraph", "text": "Text"},
        {"type": "heading", "level": 2, "text": "Heading"},
        {"type": "code", "language": "python", "code": "print(1)"},
        {"type": "list", "style": "ordered", "items": ["One"]},
        {"type": "link", "url": "https://example.test", "label": "Example"},
    ],
)
def test_article_approved_blocks_are_publishable(block: dict[str, object]) -> None:
    ContentBody.from_dict(article([block])).require_publishable()


@pytest.mark.parametrize(
    "body",
    [
        {"schema_version": 2, "kind": "article", "blocks": []},
        {"schema_version": 1, "kind": "unknown", "blocks": []},
        article([{"type": "unknown"}]),
        article([{"type": "heading", "level": 5, "text": "Wrong"}]),
        article([{"type": "list", "style": "nested", "items": []}]),
        article([{"type": "paragraph", "text": "Text", "html": "<b>Text</b>"}]),
        resource("javascript:alert(1)"),
        resource("https://example.test", description=1),
        {"schema_version": 1, "kind": "resource", "url": "https://example.test"},
    ],
)
def test_malformed_or_unsupported_bodies_are_rejected(body: object) -> None:
    with pytest.raises(InvalidContentBodyError):
        ContentBody.from_dict(body)


def test_article_block_limit_is_enforced() -> None:
    block = {"type": "paragraph", "text": "x"}
    with pytest.raises(InvalidContentBodyError):
        ContentBody.from_dict(article([block] * (MAX_ARTICLE_BLOCKS + 1)))


def test_body_size_limit_is_enforced() -> None:
    with pytest.raises(InvalidContentBodyError):
        ContentBody.from_dict(article([{"type": "paragraph", "text": "x" * MAX_BODY_BYTES}]))


@pytest.mark.parametrize("url", ["http://example.test", "https://example.test/resource"])
def test_resource_http_urls_are_publishable(url: str) -> None:
    ContentBody.from_dict(resource(url, "Resource")).require_publishable()


def test_to_dict_does_not_expose_mutable_internal_state() -> None:
    body = ContentBody.article_empty()
    exported = body.to_dict()
    exported["kind"] = "resource"
    assert body.kind == "article"
