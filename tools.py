"""Tool functions dùng chung: fetch_source (đọc mock, không gọi model) và
summarize (gọi model, không truyền tools=)."""

from mock_sources import get_sources
from llm_client import chat


def fetch_source(topic: str, scenario: str = "normal"):
    """Đọc nguồn giả lập cho 1 topic theo kịch bản. Không gọi model."""
    return get_sources(topic, scenario)


def summarize(text: str) -> str:
    """Tóm tắt 1 đoạn text bằng model (không có tools)."""
    result = chat(
        [
            {
                "role": "system",
                "content": (
                    "Bạn là trợ lý tóm tắt tin tức. Tóm tắt ngắn gọn, súc tích bằng "
                    "tiếng Việt, giữ lại các ý chính."
                ),
            },
            {"role": "user", "content": text},
        ]
    )
    return result["text"]
