"""Lớp trừu tượng gọi model — bọc quanh Anthropic SDK (Claude Haiku 4.5).

Mục đích: gom logic gọi model + đếm token/usage về 1 chỗ, trả về format thống nhất
(text, tool_calls, usage) để các file khác (workflow/agent/manager) không cần biết
chi tiết Anthropic SDK.
"""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def chat(messages, tools=None, model=None, max_tokens=1024):
    """Gọi model và trả về response ở format thống nhất.

    Args:
        messages: list [{"role": "user"|"assistant", "content": ...}]. Một message
            với role "system" (nếu có, chỉ 1, phải ở đầu) được tách ra làm system prompt.
        tools: list tool schema theo format Anthropic (name/description/input_schema),
            hoặc None nếu không cần tool-use.
        model: override model, mặc định DEFAULT_MODEL.
        max_tokens: giới hạn output token.

    Returns:
        dict:
            text: str | None — phần text model trả lời (nếu có).
            tool_calls: list[{"id", "name", "input"}] — các tool model muốn gọi.
            stop_reason: str.
            usage: {"input_tokens": int, "output_tokens": int}.
            raw: response gốc từ SDK (để debug khi cần).
    """
    system_prompt = None
    chat_messages = messages
    if messages and messages[0].get("role") == "system":
        system_prompt = messages[0]["content"]
        chat_messages = messages[1:]

    kwargs = {
        "model": model or DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "messages": chat_messages,
    }
    if system_prompt is not None:
        kwargs["system"] = system_prompt
    if tools:
        kwargs["tools"] = tools

    response = _get_client().messages.create(**kwargs)

    text = None
    tool_calls = []
    for block in response.content:
        if block.type == "text":
            text = (text or "") + block.text
        elif block.type == "tool_use":
            tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

    return {
        "text": text,
        "tool_calls": tool_calls,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "raw": response,
    }
