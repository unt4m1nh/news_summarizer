"""Workflow version — pattern Parallel: pipeline CỐ ĐỊNH đúng 5 bước, không loop.

    fetch_tech, fetch_sport -> summarize_tech, summarize_sport -> combine

Chạy dù nguồn có lỗi hay không, số bước luôn cố định — minh hoạ tính cứng nhắc của
Workflow so với Agent (Phase 3).
"""

import time
from concurrent.futures import ThreadPoolExecutor

from tools import fetch_source, summarize


def _sources_to_text(sources) -> str:
    lines = [f"{s['title']}: {s['content']}" for s in sources if not s.get("error")]
    return "\n".join(lines)


def _failed_sources(sources):
    return [s for s in sources if s.get("error")]


def run_workflow(scenario: str = "normal"):
    steps = []

    def log_step(name, start):
        steps.append({"step": name, "seconds": round(time.time() - start, 3)})

    t0 = time.time()

    # Bước 1-2: fetch_tech, fetch_sport (song song)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_tech = pool.submit(fetch_source, "tech", scenario)
        fut_sport = pool.submit(fetch_source, "sport", scenario)
        t1 = time.time()
        tech_sources = fut_tech.result()
        log_step("fetch_tech", t1)
        t2 = time.time()
        sport_sources = fut_sport.result()
        log_step("fetch_sport", t2)

    # Bước 3-4: summarize_tech, summarize_sport
    t3 = time.time()
    tech_summary = summarize(_sources_to_text(tech_sources))
    log_step("summarize_tech", t3)

    t4 = time.time()
    sport_summary = summarize(_sources_to_text(sport_sources))
    log_step("summarize_sport", t4)

    # Bước 5: combine
    t5 = time.time()
    warnings = []
    for topic, sources in (("tech", tech_sources), ("sport", sport_sources)):
        for s in _failed_sources(sources):
            warnings.append(f"⚠ Nguồn {topic} lỗi ({s['error']}): {s['url']}")

    parts = []
    if warnings:
        parts.append("\n".join(warnings))
    parts.append(f"=== BẢN TIN CÔNG NGHỆ ===\n{tech_summary}")
    parts.append(f"=== BẢN TIN THỂ THAO ===\n{sport_summary}")
    report = "\n\n".join(parts)
    log_step("combine", t5)

    total_seconds = round(time.time() - t0, 3)
    return {
        "report": report,
        "steps": steps,
        "num_steps": len(steps),
        "total_seconds": total_seconds,
        "warnings": warnings,
    }


if __name__ == "__main__":
    import sys

    scenario = sys.argv[1] if len(sys.argv) > 1 else "normal"
    result = run_workflow(scenario)

    print(f"Scenario: {scenario}")
    print(f"Số bước: {result['num_steps']} (cố định = 5)")
    for s in result["steps"]:
        print(f"  - {s['step']}: {s['seconds']}s")
    print(f"Tổng thời gian: {result['total_seconds']}s")
    print()
    print(result["report"])
