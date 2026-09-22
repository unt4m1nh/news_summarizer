"""Lưu/đọc tóm tắt theo (topic, date, hour) trong 1 file JSON — bộ nhớ ngoài dùng
cho Agent + Memory (Phase 4)."""

import json
import os

DEFAULT_PATH = "data/memory.json"


def _load_all(path: str = DEFAULT_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: dict, path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clear(path: str = DEFAULT_PATH) -> None:
    """Xoá sạch bộ nhớ — dùng để tạo baseline sạch giữa các lần benchmark."""
    _save_all({}, path)


def save_summary(topic: str, date: str, hour: int, summary: str, path: str = DEFAULT_PATH) -> None:
    data = _load_all(path)
    data.setdefault(topic, {}).setdefault(date, {})[str(hour)] = summary
    _save_all(data, path)


def load_recent(topic: str, date: str, before_hour: int, window_hours: int = 6, path: str = DEFAULT_PATH):
    """Trả về {"hour": int, "summary": str} gần nhất trong ngày `date`, không muộn
    hơn `before_hour` và cách `before_hour` không quá `window_hours`. None nếu
    không có bản ghi phù hợp."""
    data = _load_all(path)
    day_data = data.get(topic, {}).get(date, {})
    if not day_data:
        return None

    candidates = [int(h) for h in day_data.keys() if int(h) <= before_hour]
    if not candidates:
        return None

    latest_hour = max(candidates)
    if before_hour - latest_hour > window_hours:
        return None

    return {"hour": latest_hour, "summary": day_data[str(latest_hour)]}
