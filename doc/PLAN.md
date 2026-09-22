# PLAN.md — News Digest Demo (Workflow / Agent / Manager+Subagent / Memory)

> Tài liệu này là **nguồn sự thật duy nhất** cho việc build project demo. Đưa file này vào root
> repo trước khi mở Claude Code, rồi làm theo hướng dẫn ở mục "Cách dùng với Claude Code" bên dưới.

---

## 0. Mục tiêu & phạm vi

**Bài toán demo:** hệ thống tổng hợp **Bản tin Công nghệ & Thể thao theo yêu cầu** — người dùng
gõ lệnh, hệ thống fetch nguồn, tóm tắt, trả về bản tin. Xây **4 phiên bản kiến trúc** trên cùng 1
bài toán để so sánh trade-off:

| Phiên bản | Minh hoạ khái niệm |
|---|---|
| Workflow (Parallel) | Pipeline cố định, không loop |
| Agent | Tool-use loop, model tự quyết bước tiếp theo |
| Agent + Memory | Context bloat/drift, prune, compaction, memory ngoài |
| Manager + Subagent | Tách việc độc lập, containment, chi phí nhân theo N |

**Ràng buộc:**
- Dùng **Anthropic SDK** (`anthropic`) với `ANTHROPIC_API_KEY` xuyên suốt (code lẫn test lẫn demo
  live/benchmark) — model **Claude Haiku 4.5**. Không dùng Ollama / model chạy local, không cần
  pull model nào cả.
- Ngân sách **$5** cho toàn bộ các lượt chạy (code/test lẫn benchmark cuối) — theo dõi token qua
  `response.usage` để không vượt ngân sách.
- `llm_client.py` vẫn là lớp trừu tượng mỏng bọc quanh `client.messages.create(...)` — mục đích là
  gom logic gọi model + đếm token/usage về 1 chỗ, không phải để switch provider.

---

## 1. Nguyên tắc làm việc với Claude Code

1. **Mỗi Phase dưới đây = 1 đơn vị công việc độc lập.** Sau khi hoàn thành 1 Phase, Claude Code
   phải **DỪNG LẠI**, in tóm tắt kết quả + kết quả test, và **chờ xác nhận** trước khi sang Phase kế —
   không tự động chạy tiếp toàn bộ kế hoạch trong 1 lần.
2. Mỗi Phase có mục **"Acceptance"** — đây là tiêu chí bắt buộc phải đạt trước khi coi Phase đó là xong.
3. Nếu 1 Phase phát sinh thay đổi phải quay lại sửa Phase trước, việc đó phải được nêu rõ, không
   sửa ngầm rồi đi tiếp.
4. Dùng `/clear` giữa các Phase nếu phiên đang dài — mỗi Phase không phụ thuộc context hội thoại
   cũ, chỉ phụ thuộc code đã có trong repo + tài liệu này.

---

## 2. Cấu trúc thư mục mục tiêu

```
news_digest_demo/
├── PLAN.md                  # chính là file này
├── README.md                # hướng dẫn chạy + bảng kết quả (viết ở Phase 7)
├── requirements.txt
├── mock_sources.py          # dữ liệu giả lập: nguồn tech/sport, 2 kịch bản (thường / lỗi nguồn)
├── llm_client.py            # lớp trừu tượng: chat(messages, tools=None) — Anthropic Haiku 4.5
├── tools.py                 # fetch_source(), summarize() — đếm call/latency giả lập
├── workflow_version.py      # pipeline cố định: fetch_tech ∥ fetch_sport → summarize → combine
├── agent_version.py         # tool-use loop: think → call tool → observe → repeat
├── memory_store.py          # JSON lưu tóm tắt theo (topic, ngày, giờ)
├── manager_subagent.py      # Manager tách subtopic, N subagent chạy song song, gộp kết quả
├── benchmark.py             # chạy cả 4 kiến trúc trên cùng input, in bảng so sánh
└── data/
    └── memory.json          # file lưu memory, tạo tự động khi chạy
```

---

## 3. Lộ trình theo Phase

### ☐ Phase 0 — Khởi tạo project

**Việc cần làm:**
- Tạo cấu trúc thư mục ở trên (file rỗng/placeholder, chưa cần logic).
- `requirements.txt`: `anthropic`, không cần thêm gì nặng.
- Tạo virtualenv, cài đặt.
- Khung `README.md` (chỉ tiêu đề + mục lục, nội dung thật viết ở Phase 7).

**Acceptance:**
- [ ] `python -c "import anthropic"` chạy không lỗi.
- [ ] Cây thư mục khớp mục 2.
- [ ] `ANTHROPIC_API_KEY` đã có trong `.env`/biến môi trường và gọi thử API thành công.

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 1.**

---

### ☐ Phase 1 — Dữ liệu giả lập + lớp LLM client trừu tượng

**Việc cần làm:**
- `mock_sources.py`: mỗi chủ đề (tech, sport) có 2-3 nguồn giả lập (title, url, nội dung ngắn).
  Viết **2 kịch bản dữ liệu**:
  - `SCENARIO_NORMAL`: mọi nguồn trả kết quả bình thường.
  - `SCENARIO_SOURCE_DOWN`: 1 nguồn tech timeout/lỗi, cần nguồn dự phòng hoặc mở rộng khung giờ.
- `llm_client.py`: 1 hàm duy nhất `chat(messages, tools=None, model="claude-haiku-4-5-20251001")`
  bọc quanh `anthropic.Anthropic().messages.create(...)`. Trả về format thống nhất (text, tool
  calls nếu có, usage token) để các file khác không cần biết chi tiết SDK.

**Acceptance:**
- [ ] Gọi `llm_client.chat([{"role":"user","content":"Xin chào"}])` (dùng `ANTHROPIC_API_KEY` từ
      `.env`) trả về text hợp lệ kèm usage token.
- [ ] Gọi lại với `tools=[...]` (tool giả bất kỳ) → nhận đúng tool_call từ response.

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 2.**

---

### ☐ Phase 2 — Workflow version (pattern Parallel)

**Việc cần làm:**
- `tools.py`: `fetch_source(topic, scenario)` (đọc từ `mock_sources`, không gọi model),
  `summarize(text)` (gọi `llm_client.chat`, **không** truyền `tools=`).
- `workflow_version.py`: pipeline **cố định** đúng 5 bước —
  `fetch_tech, fetch_sport → summarize_tech, summarize_sport → combine`.
  Log lại số bước + thời gian mỗi lần chạy.

**Acceptance:**
- [ ] Chạy 2-3 lần với `SCENARIO_NORMAL` → log **luôn đúng 5 bước**, không đổi.
- [ ] Chạy với `SCENARIO_SOURCE_DOWN` → pipeline vẫn chỉ chạy đúng 5 bước cố định (kể cả khi
      nguồn lỗi) để **chứng minh tính cứng nhắc** — đây là điểm sẽ đối chiếu với Agent ở Phase 3.

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 3.**

---

### ☐ Phase 3 — Agent version (Tool-use loop)

**Việc cần làm:**
- Định nghĩa 3 tool: `fetch_source(topic, backup=False)`, `search_more(keyword)`, `finish(report)`.
- Viết vòng lặp: gọi `llm_client.chat(messages, tools=[...])` → nếu model trả tool_call thì chạy
  tool tương ứng, nhét kết quả vào history, gọi lại → lặp tới khi `finish` được gọi hoặc chạm
  `max_iterations` (đặt cứng, ví dụ 8 — **Stopping Problem**).
- In log rõ từng vòng lặp: model nghĩ gì → gọi tool nào → kết quả gì.

**Acceptance:**
- [ ] Chạy trên `SCENARIO_NORMAL` → khoảng 3 vòng lặp.
- [ ] Chạy trên `SCENARIO_SOURCE_DOWN` → nhiều vòng lặp hơn rõ rệt (agent tự thử nguồn dự phòng /
      mở rộng khung giờ) — số liệu thật để đối chiếu với slide đã có (3 vs 6 vòng).
- [ ] Nếu ép agent lặp vô hạn (dữ liệu giả cố tình gây loop) → dừng đúng tại `max_iterations`,
      không treo.

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 4.**

---

### ☐ Phase 4 — Memory

**Việc cần làm:**
- `memory_store.py`: `save_summary(topic, date, hour, summary)` / `load_recent(topic, date)` —
  đọc/ghi `data/memory.json`.
- Sửa `agent_version.py`: trước khi gọi `fetch_source`, kiểm tra memory — nếu đã có bản tóm tắt
  trong khung giờ gần nhất, dùng lại, chỉ fetch phần **mới phát sinh**.
- Viết kịch bản test: mô phỏng **1 ngày, 3 lượt hỏi** (9h, 12h, 18h) gọi liên tiếp
  `agent_version` với cùng memory store.

**Acceptance:**
- [ ] Lượt 9h: fetch đầy đủ (số lệnh gọi ~ giống Phase 3).
- [ ] Lượt 12h, 18h: số lệnh gọi/token **giảm rõ rệt** so với lượt đầu nhờ dùng lại memory.
- [ ] In ra bảng so sánh tổng token "có memory" vs "không memory" cho cả ngày (chạy lại 3 lượt mà
      **không** áp dụng memory để làm baseline đối chứng).

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 5.**

---

### ☐ Phase 5 — Manager + Subagent

**Việc cần làm:**
- `manager_subagent.py`: Manager (1 lệnh gọi) quyết định danh sách subtopic (tech, sport, ...).
  Với mỗi subtopic, chạy **1 instance độc lập của agent_version** (context riêng, không chia sẻ
  history) — dùng `concurrent.futures.ThreadPoolExecutor` để giả lập chạy song song.
  Manager gọi thêm 1 lần cuối để gộp kết quả các subagent thành 1 bản tin.
- Test containment: cho 1 subagent (sport) chạy trên `SCENARIO_SOURCE_DOWN` gây lỗi hẳn (không
  có nguồn dự phòng) trong khi subagent khác chạy `SCENARIO_NORMAL`.

**Acceptance:**
- [ ] Khi 1 subagent thất bại hoàn toàn, kết quả cuối vẫn có đủ nội dung từ các subagent còn lại
      (không toàn bộ báo lỗi).
- [ ] Tổng số lệnh gọi/token = Manager + tổng tất cả Subagent — in ra rõ con số này để so với
      Agent đơn ở Phase 3.

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 6.**

---

### ☐ Phase 6 — Benchmark tổng hợp

**Việc cần làm:**
- `benchmark.py`: chạy cả 4 kiến trúc (Workflow, Agent, Agent+Memory, Manager+Subagent) trên
  cùng kịch bản mô phỏng "1 ngày có 3 lượt hỏi".
- Với mỗi kiến trúc, ghi lại: số bước, số lệnh gọi model, tổng input/output token, thời gian chạy,
  độ lệch (variance) giữa các lần chạy lặp lại.
- In bảng so sánh cuối cùng (đúng format bảng trade-off đã dùng trong slide thuyết trình).
- Cộng dồn `response.usage` sau mỗi lệnh gọi, quy đổi ra USD theo giá Haiku 4.5 ($1/$5 mỗi MTok
  input/output), in tổng chi phí thực tế của lượt benchmark — theo dõi để không vượt ngân sách $5.

**Acceptance:**
- [ ] Bảng in ra đủ 4 cột kiến trúc × các chỉ số ở trên.
- [ ] Khi chạy trên Haiku 4.5 thật, tổng chi phí 1 lượt benchmark đầy đủ nằm quanh mức đã ước
      tính trước (~$0.10–0.15).

**→ DỪNG LẠI, chờ xác nhận trước khi qua Phase 7.**

---

### ☐ Phase 7 — Hoàn thiện README + chuẩn bị demo

**Việc cần làm:**
- Viết `README.md` đầy đủ: cách cài đặt, cách chạy từng file, giải thích ngắn gọn 4 kiến trúc,
  dán bảng kết quả benchmark thật vào.
- Chạy `benchmark.py` một lần cuối trên Haiku 4.5, **lưu lại log/output** (file text hoặc
  screenshot) để dùng làm dự phòng khi thuyết trình live nếu mạng/model lỗi.

**Acceptance:**
- [ ] `python benchmark.py` chạy từ đầu tới cuối không lỗi, ra đủ bảng so sánh.
- [ ] README đọc độc lập (không cần đọc PLAN.md) vẫn hiểu được cách chạy và ý nghĩa kết quả.

**→ Hoàn tất toàn bộ project.**

---

## 4. Cách dùng file này với Claude Code

1. Copy `PLAN.md` vào root của repo.
2. Mở Claude Code trong thư mục đó, gõ:

   ```
   Đọc PLAN.md. Bắt đầu Phase 0. Sau khi xong, dừng lại, tóm tắt kết quả và
   liệt kê acceptance đã đạt/chưa đạt — chờ tôi xác nhận trước khi làm Phase 1.
   ```
3. Sau mỗi lần Claude Code báo cáo xong 1 Phase, kiểm tra checklist Acceptance tương ứng, rồi trả
   lời "OK, làm Phase tiếp theo" hoặc yêu cầu sửa nếu chưa đạt.
4. Nếu muốn lặp lại thao tác này nhanh hơn, có thể tạo custom command
   `.claude/commands/next-phase.md` với nội dung: *"Đọc PLAN.md, xác định Phase đầu tiên chưa được
   đánh dấu xong, thực hiện Phase đó, dừng lại và chờ xác nhận."* — rồi chỉ cần gõ `/next-phase`
   sau mỗi lần duyệt.
