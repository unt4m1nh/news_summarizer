"""Agent version — Tool-use loop: model tự quyết định bước tiếp theo.

Vòng lặp: gọi llm_client.chat(messages, tools=[...]) -> nếu model trả tool_call thì
chạy tool tương ứng, nhét kết quả vào history, gọi lại -> lặp tới khi `finish` được
gọi hoặc chạm `max_iterations` (Stopping Problem).
"""

import json
import time

import memory_store
import mock_sources
from llm_client import chat

MAX_ITERATIONS = 8
TOPICS = ("tech", "sport")

TOOLS = [
    {
        "name": "fetch_source",
        "description": (
            "Lấy danh sách nguồn tin cho 1 chủ đề (tech hoặc sport). Dùng "
            "backup=true để lấy nguồn dự phòng (mirror) nếu nguồn chính bị lỗi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "enum": ["tech", "sport"]},
                "backup": {
                    "type": "boolean",
                    "description": "true để lấy nguồn dự phòng thay vì nguồn chính",
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "search_more",
        "description": (
            "Tìm kiếm thông tin bổ sung theo từ khoá khi nguồn chính và nguồn dự "
            "phòng đều không đủ dữ liệu."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"],
        },
    },
    {
        "name": "finish",
        "description": (
            "Kết thúc và trả về bản tin tổng hợp cuối cùng (đủ cả tech và sport). "
            "PHẢI gọi hàm này khi đã có đủ thông tin, hoặc khi đã thử hết cách mà "
            "vẫn thiếu dữ liệu (nêu rõ phần nào thiếu)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report": {"type": "string"},
                "tech_summary": {
                    "type": "string",
                    "description": (
                        "Tóm tắt 2-3 câu cho tin tech, CHỈ điền nếu bạn vừa fetch dữ "
                        "liệu tech mới (không lấy từ bộ nhớ) — dùng để lưu vào bộ nhớ."
                    ),
                },
                "sport_summary": {
                    "type": "string",
                    "description": (
                        "Tóm tắt 2-3 câu cho tin sport, CHỈ điền nếu bạn vừa fetch dữ "
                        "liệu sport mới (không lấy từ bộ nhớ) — dùng để lưu vào bộ nhớ."
                    ),
                },
            },
            "required": ["report"],
        },
    },
]

SYSTEM_PROMPT = (
    "Bạn là agent tổng hợp bản tin Công nghệ & Thể thao. Nhiệm vụ: dùng các tool "
    "được cung cấp để lấy tin tech và sport, rồi viết 1 bản tin tổng hợp ngắn gọn "
    "bằng tiếng Việt.\n"
    "QUY TRÌNH BẮT BUỘC cho mỗi chủ đề (tech, sport):\n"
    "1. Gọi fetch_source(topic).\n"
    "2. Kiểm tra TỪNG phần tử trả về: nếu phần tử nào có field 'error' (tức nguồn đó "
    "bị lỗi, không có title/content), đây là dấu hiệu bắt buộc phải xử lý tiếp — "
    "KHÔNG được bỏ qua hay coi như không có chuyện gì.\n"
    "3. Nếu phát hiện lỗi ở bước 2: BẮT BUỘC gọi lại fetch_source(topic, backup=true) "
    "để lấy nguồn dự phòng.\n"
    "4. Nếu nguồn dự phòng ở bước 3 VẪN có 'error': BẮT BUỘC gọi search_more với từ "
    "khoá liên quan đến tin bị lỗi đó để tìm thông tin thay thế.\n"
    "5. Chỉ khi đã thử đủ fetch chính + backup + search_more cho 1 chủ đề mà vẫn "
    "không có dữ liệu, mới được dừng thử cho chủ đề đó — khi viết báo cáo phải ghi rõ "
    "câu 'không lấy được dữ liệu cho mục này' thay vì im lặng bỏ qua.\n"
    "Luôn kết thúc bằng cách gọi tool finish với report là bản tin đầy đủ cuối cùng. "
    "Nếu bạn vừa fetch dữ liệu MỚI (không lấy từ bộ nhớ) cho tech và/hoặc sport, hãy "
    "điền thêm tech_summary/sport_summary tương ứng khi gọi finish để lưu vào bộ nhớ "
    "cho lần hỏi sau — chủ đề nào lấy từ bộ nhớ (nếu có ghi chú BỘ NHỚ bên dưới) thì "
    "không cần điền lại."
)


def _serialize_block(block):
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    raise ValueError(f"Unknown block type: {block.type}")


def _execute_tool(name, tool_input, scenario):
    if name == "fetch_source":
        topic = tool_input["topic"]
        backup = tool_input.get("backup", False)
        if backup:
            result = mock_sources.get_backup_sources(topic, scenario)
        else:
            result = mock_sources.get_sources(topic, scenario)
        return json.dumps(result, ensure_ascii=False)
    if name == "search_more":
        return mock_sources.search_more(tool_input["keyword"], scenario)
    if name == "finish":
        return "ok"
    raise ValueError(f"Unknown tool: {name}")


def run_agent(
    scenario: str = "normal",
    max_iterations: int = MAX_ITERATIONS,
    use_memory: bool = False,
    date: str = None,
    hour: int = None,
    window_hours: int = 6,
    memory_path: str = memory_store.DEFAULT_PATH,
):
    cached = {}
    if use_memory:
        if date is None or hour is None:
            raise ValueError("use_memory=True cần truyền date và hour")
        for topic in TOPICS:
            hit = memory_store.load_recent(topic, date, hour, window_hours, memory_path)
            if hit:
                cached[topic] = hit

    memory_note = ""
    if cached:
        lines = [
            f"- {topic}: đã có tóm tắt lúc {hit['hour']}h hôm nay -> \"{hit['summary']}\""
            for topic, hit in cached.items()
        ]
        memory_note = (
            "\n\nBỘ NHỚ: các chủ đề sau đã có tóm tắt gần đây (trong vòng "
            f"{window_hours} giờ qua), DÙNG LẠI NGUYÊN VĂN, KHÔNG cần gọi fetch_source "
            "cho chủ đề đó nữa:\n" + "\n".join(lines)
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + memory_note},
        {
            "role": "user",
            "content": "Tạo bản tin tổng hợp Công nghệ và Thể thao hôm nay.",
        },
    ]

    log = []
    tool_call_counts = {}
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    final_report = None
    hit_max_iterations = False
    t_start = time.time()

    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        response = chat(messages, tools=TOOLS)
        total_usage["input_tokens"] += response["usage"]["input_tokens"]
        total_usage["output_tokens"] += response["usage"]["output_tokens"]

        assistant_content = [_serialize_block(b) for b in response["raw"].content]
        messages.append({"role": "assistant", "content": assistant_content})

        entry = {
            "iteration": iteration,
            "thought": response["text"],
            "tool_calls": [],
        }

        if response["stop_reason"] != "tool_use":
            # Model kết thúc bằng text thay vì gọi finish — dùng làm fallback.
            final_report = response["text"] or "(model không trả về nội dung)"
            log.append(entry)
            break

        tool_results = []
        called_finish = False
        for tc in response["tool_calls"]:
            tool_call_counts[tc["name"]] = tool_call_counts.get(tc["name"], 0) + 1
            result_str = _execute_tool(tc["name"], tc["input"], scenario)
            entry["tool_calls"].append(
                {"name": tc["name"], "input": tc["input"], "result": result_str}
            )
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tc["id"], "content": result_str}
            )
            if tc["name"] == "finish":
                final_report = tc["input"]["report"]
                called_finish = True
                if use_memory:
                    for topic in TOPICS:
                        if topic in cached:
                            continue  # đã dùng lại từ bộ nhớ, không ghi đè
                        summary = tc["input"].get(f"{topic}_summary")
                        if summary:
                            memory_store.save_summary(topic, date, hour, summary, memory_path)

        log.append(entry)
        messages.append({"role": "user", "content": tool_results})

        if called_finish:
            break
    else:
        pass

    if final_report is None:
        hit_max_iterations = True
        final_report = (
            "[CHƯA HOÀN THÀNH] Agent đã chạm max_iterations "
            f"({max_iterations}) mà chưa gọi finish. Dữ liệu thu thập được ở log."
        )

    return {
        "report": final_report,
        "log": log,
        "num_iterations": iteration,
        "tool_call_counts": tool_call_counts,
        "usage": total_usage,
        "hit_max_iterations": hit_max_iterations,
        "total_seconds": round(time.time() - t_start, 3),
        "cached_topics": list(cached.keys()),
    }


def _print_result(scenario, result, max_iterations=MAX_ITERATIONS):
    print(f"Scenario: {scenario}")
    for entry in result["log"]:
        print(f"--- Vòng {entry['iteration']} ---")
        if entry["thought"]:
            print(f"  Model nghĩ: {entry['thought']}")
        for tc in entry["tool_calls"]:
            preview = tc["result"][:200] + ("..." if len(tc["result"]) > 200 else "")
            print(f"  Gọi tool: {tc['name']}({tc['input']}) -> {preview}")
    print()
    print(f"Số vòng lặp: {result['num_iterations']} (max={max_iterations})")
    print(f"Số lần gọi từng tool: {result['tool_call_counts']}")
    print(f"Chạm max_iterations: {result['hit_max_iterations']}")
    print(f"Token: {result['usage']}")
    print(f"Thời gian: {result['total_seconds']}s")
    print()
    print("=== BẢN TIN CUỐI CÙNG ===")
    print(result["report"])


def simulate_day(
    scenario: str = "normal",
    date: str = "2026-09-22",
    hours=(9, 12, 18),
    use_memory: bool = True,
    window_hours: int = 12,
    max_iterations: int = MAX_ITERATIONS,
    memory_path: str = memory_store.DEFAULT_PATH,
):
    """Mô phỏng 1 ngày, gọi agent liên tiếp ở các giờ trong `hours`, dùng chung 1
    memory store. Trả về list kết quả từng lượt kèm hour."""
    if use_memory:
        memory_store.clear(memory_path)

    rounds = []
    for hour in hours:
        result = run_agent(
            scenario,
            max_iterations,
            use_memory=use_memory,
            date=date,
            hour=hour,
            window_hours=window_hours,
            memory_path=memory_path,
        )
        rounds.append({"hour": hour, **result})
    return rounds


def compare_memory(scenario: str = "normal", date: str = "2026-09-22", hours=(9, 12, 18)):
    """Chạy lại 3 lượt hỏi 2 lần — có memory và không memory (baseline) — rồi in
    bảng so sánh tổng token."""
    with_memory = simulate_day(scenario, date, hours, use_memory=True, memory_path="data/memory_with.json")
    without_memory = simulate_day(scenario, date, hours, use_memory=False, memory_path="data/memory_without.json")

    print(f"=== So sánh CÓ memory vs KHÔNG memory (scenario={scenario}, {len(hours)} lượt/ngày) ===\n")
    header = f"{'Giờ':>5} | {'Có memory (in/out tok)':>26} | {'Không memory (in/out tok)':>28} | {'Vòng lặp (có/không)':>20}"
    print(header)
    print("-" * len(header))

    total_with = {"input_tokens": 0, "output_tokens": 0}
    total_without = {"input_tokens": 0, "output_tokens": 0}
    for w, wo in zip(with_memory, without_memory):
        total_with["input_tokens"] += w["usage"]["input_tokens"]
        total_with["output_tokens"] += w["usage"]["output_tokens"]
        total_without["input_tokens"] += wo["usage"]["input_tokens"]
        total_without["output_tokens"] += wo["usage"]["output_tokens"]
        print(
            f"{w['hour']:>5} | "
            f"{w['usage']['input_tokens']:>10}/{w['usage']['output_tokens']:<10} | "
            f"{wo['usage']['input_tokens']:>13}/{wo['usage']['output_tokens']:<10} | "
            f"{w['num_iterations']:>8}/{wo['num_iterations']:<8}"
        )

    print("-" * len(header))
    print(
        f"{'Tổng':>5} | "
        f"{total_with['input_tokens']:>10}/{total_with['output_tokens']:<10} | "
        f"{total_without['input_tokens']:>13}/{total_without['output_tokens']:<10} |"
    )
    saved_in = total_without["input_tokens"] - total_with["input_tokens"]
    saved_out = total_without["output_tokens"] - total_with["output_tokens"]
    print(f"\nTiết kiệm nhờ memory: {saved_in} input tokens, {saved_out} output tokens.")
    for w in with_memory:
        if w["cached_topics"]:
            print(f"  Giờ {w['hour']}h dùng lại từ bộ nhớ: {w['cached_topics']}")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

    if mode == "memory_demo":
        compare_memory()
    else:
        scenario_arg = mode
        max_iter_arg = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_ITERATIONS
        result = run_agent(scenario_arg, max_iter_arg)
        _print_result(scenario_arg, result, max_iter_arg)
