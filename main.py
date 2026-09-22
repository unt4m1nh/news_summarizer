"""CLI nhỏ để test thủ công llm_client + mock_sources (Phase 1).

Chạy:
    python main.py

Lệnh trong REPL:
    /sources <tech|sport> <normal|source_down>   xem dữ liệu nguồn giả lập
    /exit                                        thoát
    <bất kỳ text nào khác>                       gửi tới model qua llm_client.chat
"""

from mock_sources import get_sources
from llm_client import chat


def handle_sources(args):
    if len(args) != 2:
        print("Cú pháp: /sources <tech|sport> <normal|source_down>")
        return
    topic, scenario = args
    try:
        sources = get_sources(topic, scenario)
    except KeyError as e:
        print(f"Không hợp lệ: {e}")
        return
    for s in sources:
        print(f"- {s.get('title') or '(lỗi)'}: {s.get('content') or s.get('error')}")


def main():
    print("News Digest Demo — CLI test (Phase 1). Gõ /exit để thoát.")
    total_input = 0
    total_output = 0
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line == "/exit":
            break
        if line.startswith("/sources"):
            handle_sources(line.split()[1:])
            continue

        result = chat([{"role": "user", "content": line}])
        print(result["text"])
        usage = result["usage"]
        total_input += usage["input_tokens"]
        total_output += usage["output_tokens"]
        print(f"[usage: +{usage['input_tokens']} in / +{usage['output_tokens']} out | "
              f"total: {total_input} in / {total_output} out]")

    print("Kết thúc.")


if __name__ == "__main__":
    main()
