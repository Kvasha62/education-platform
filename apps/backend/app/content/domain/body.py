"""Content-owned structured educational body contract from ADR-0004."""

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

MAX_BODY_BYTES = 256 * 1024
MAX_ARTICLE_BLOCKS = 500
MAX_URL_LENGTH = 2048


class InvalidContentBodyError(ValueError):
    pass


class ContentBodyNotPublishableError(ValueError):
    pass


def _require_keys(value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise InvalidContentBodyError


def _require_string(value: Any) -> str:
    if not isinstance(value, str):
        raise InvalidContentBodyError
    return value


def _valid_url(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > MAX_URL_LENGTH:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validate_block(block: Any) -> dict[str, Any]:
    if not isinstance(block, dict) or not isinstance(block.get("type"), str):
        raise InvalidContentBodyError
    block_type = block["type"]
    if block_type == "paragraph":
        _require_keys(block, {"type", "text"})
        _require_string(block["text"])
    elif block_type == "heading":
        _require_keys(block, {"type", "level", "text"})
        level = block["level"]
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 4:
            raise InvalidContentBodyError
        _require_string(block["text"])
    elif block_type == "code":
        if set(block) not in ({"type", "code"}, {"type", "language", "code"}):
            raise InvalidContentBodyError
        _require_string(block["code"])
        if "language" in block and block["language"] is not None:
            _require_string(block["language"])
    elif block_type == "list":
        _require_keys(block, {"type", "style", "items"})
        if block["style"] not in {"ordered", "unordered"}:
            raise InvalidContentBodyError
        if not isinstance(block["items"], list):
            raise InvalidContentBodyError
        for item in block["items"]:
            _require_string(item)
    elif block_type == "link":
        _require_keys(block, {"type", "url", "label"})
        if not _valid_url(block["url"]):
            raise InvalidContentBodyError
        _require_string(block["label"])
    else:
        raise InvalidContentBodyError
    return block


def _is_meaningful(block: dict[str, Any]) -> bool:
    block_type = block["type"]
    if block_type in {"paragraph", "heading"}:
        return bool(block["text"].strip())
    if block_type == "code":
        return bool(block["code"].strip())
    if block_type == "list":
        return any(item.strip() for item in block["items"])
    if block_type == "link":
        return bool(block["label"].strip())
    return False


@dataclass(frozen=True, slots=True)
class ContentBody:
    _data: dict[str, Any]

    @classmethod
    def article_empty(cls) -> "ContentBody":
        return cls.from_dict({"schema_version": 1, "kind": "article", "blocks": []})

    @classmethod
    def resource_empty(cls) -> "ContentBody":
        return cls.from_dict(
            {
                "schema_version": 1,
                "kind": "resource",
                "resource": {"url": None, "description": ""},
            }
        )

    @classmethod
    def from_dict(cls, value: Any) -> "ContentBody":
        if not isinstance(value, dict):
            raise InvalidContentBodyError
        if value.get("schema_version") != 1:
            raise InvalidContentBodyError
        kind = value.get("kind")
        if kind == "article":
            _require_keys(value, {"schema_version", "kind", "blocks"})
            blocks = value["blocks"]
            if not isinstance(blocks, list) or len(blocks) > MAX_ARTICLE_BLOCKS:
                raise InvalidContentBodyError
            for block in blocks:
                _validate_block(block)
        elif kind == "resource":
            _require_keys(value, {"schema_version", "kind", "resource"})
            resource = value["resource"]
            if not isinstance(resource, dict):
                raise InvalidContentBodyError
            _require_keys(resource, {"url", "description"})
            url = resource["url"]
            if url is not None and not _valid_url(url):
                raise InvalidContentBodyError
            _require_string(resource["description"])
        else:
            raise InvalidContentBodyError

        data = deepcopy(value)
        serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        if len(serialized) > MAX_BODY_BYTES:
            raise InvalidContentBodyError
        return cls(data)

    @property
    def kind(self) -> str:
        return self._data["kind"]

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._data)

    def require_publishable(self) -> None:
        if self.kind == "article":
            if not any(_is_meaningful(block) for block in self._data["blocks"]):
                raise ContentBodyNotPublishableError
            return
        if not _valid_url(self._data["resource"]["url"]):
            raise ContentBodyNotPublishableError
