from __future__ import annotations

from typing import Any


def best_thumbnail(thumbnails: Any) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in iter_thumbnail_items(thumbnails):
        url = str(item.get("url") or "").strip()
        if not url.startswith("https://") or url in seen:
            continue
        seen.add(url)
        candidates.append(item)
    if not candidates:
        return None

    def score(index_and_item: tuple[int, dict[str, Any]]) -> tuple[int, int, int, int]:
        index, item = index_and_item
        width = positive_int(item.get("width"))
        height = positive_int(item.get("height"))
        area = width * height if width and height else 0
        return (area, width, height, index)

    selected = max(enumerate(candidates), key=score)[1]
    return {
        "url": str(selected["url"]),
        "width": positive_int(selected.get("width")) or None,
        "height": positive_int(selected.get("height")) or None,
    }


def best_thumbnail_url(thumbnails: Any) -> str | None:
    selected = best_thumbnail(thumbnails)
    return str(selected["url"]) if selected else None


def iter_thumbnail_items(value: Any, depth: int = 0) -> list[dict[str, Any]]:
    if value is None or depth > 4:
        return []
    if isinstance(value, str):
        return [{"url": value}]
    if isinstance(value, list):
        result: list[dict[str, Any]] = []
        for item in value:
            result.extend(iter_thumbnail_items(item, depth + 1))
        return result
    if isinstance(value, dict):
        result: list[dict[str, Any]] = []
        if value.get("url"):
            result.append(value)
        for key in ("thumbnails", "thumbnail", "images", "image", "sources"):
            child = value.get(key)
            if child is not value:
                result.extend(iter_thumbnail_items(child, depth + 1))
        return result
    return []


def positive_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0
