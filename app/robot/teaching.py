"""Đọc teaching_points.json (do teach_record.py lưu) → trả góc khớp từng điểm."""
from __future__ import annotations
import json
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PATH = os.path.join(_ROOT, "teaching_points.json")


def load_points() -> dict:
    if not os.path.exists(_PATH):
        return {}
    with open(_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def joints(name: str) -> list | None:
    """Trả [j1..j6] của teaching point `name`, None nếu chưa dạy."""
    p = load_points().get(name)
    return p.get("joints") if p else None
