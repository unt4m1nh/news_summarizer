"""Dữ liệu giả lập cho các nguồn tin tech/sport, dùng cho mọi kiến trúc demo."""

SCENARIO_NORMAL = {
    "tech": [
        {
            "title": "OpenAI ra mắt model reasoning mới",
            "url": "https://example.com/tech/openai-reasoning",
            "content": (
                "OpenAI công bố model reasoning thế hệ mới, cải thiện đáng kể khả năng "
                "suy luận nhiều bước và giảm chi phí inference so với thế hệ trước."
            ),
        },
        {
            "title": "Apple trình làng chip M5",
            "url": "https://example.com/tech/apple-m5",
            "content": (
                "Apple giới thiệu chip M5 với hiệu năng GPU tăng 30%, tập trung vào "
                "khối lượng công việc AI on-device cho MacBook thế hệ mới."
            ),
        },
        {
            "title": "Google phát hành bản vá bảo mật Chrome khẩn cấp",
            "url": "https://example.com/tech/chrome-patch",
            "content": (
                "Google phát hành bản vá khẩn cấp cho Chrome, khắc phục lỗ hổng zero-day "
                "đang bị khai thác trong thực tế, khuyến nghị người dùng cập nhật ngay."
            ),
        },
    ],
    "sport": [
        {
            "title": "Đội tuyển Việt Nam thắng trận giao hữu",
            "url": "https://example.com/sport/vn-friendly-win",
            "content": (
                "Đội tuyển Việt Nam giành chiến thắng 2-1 trong trận giao hữu quốc tế, "
                "ghi dấu ấn với lối chơi kiểm soát bóng chủ động."
            ),
        },
        {
            "title": "Manchester City giữ ngôi đầu bảng",
            "url": "https://example.com/sport/mancity-top",
            "content": (
                "Manchester City tiếp tục dẫn đầu Premier League sau chiến thắng "
                "thuyết phục trước đối thủ cạnh tranh trực tiếp."
            ),
        },
        {
            "title": "Djokovic vào chung kết Grand Slam",
            "url": "https://example.com/sport/djokovic-final",
            "content": (
                "Djokovic xuất sắc vượt qua bán kết để góp mặt ở trận chung kết Grand "
                "Slam thứ ba liên tiếp trong năm."
            ),
        },
    ],
}

SCENARIO_SOURCE_DOWN = {
    "tech": [
        {
            "title": None,
            "url": "https://example.com/tech/openai-reasoning",
            "content": None,
            "error": "timeout",
        },
        SCENARIO_NORMAL["tech"][1],
        SCENARIO_NORMAL["tech"][2],
    ],
    "sport": SCENARIO_NORMAL["sport"],
}

# tech nguồn chính lỗi VÀ nguồn dự phòng cũng lỗi — dùng để test agent bị ép lặp
# nhiều vòng / chạm max_iterations (Phase 3, "Stopping Problem").
SCENARIO_ALWAYS_DOWN = {
    "tech": SCENARIO_SOURCE_DOWN["tech"],
    "sport": SCENARIO_NORMAL["sport"],
}

SCENARIOS = {
    "normal": SCENARIO_NORMAL,
    "source_down": SCENARIO_SOURCE_DOWN,
    "always_down": SCENARIO_ALWAYS_DOWN,
}

# Nguồn dự phòng (mirror) dùng khi agent gọi fetch_source(topic, backup=True).
BACKUP_SOURCES = {
    "source_down": {
        "tech": [
            {
                "title": "OpenAI ra mắt model reasoning mới (nguồn dự phòng)",
                "url": "https://mirror.example.com/tech/openai-reasoning",
                "content": (
                    "[Nguồn dự phòng] OpenAI công bố model reasoning thế hệ mới, cải "
                    "thiện khả năng suy luận nhiều bước và giảm chi phí inference."
                ),
            }
        ],
    },
    "always_down": {
        # Nguồn dự phòng cũng lỗi — mô phỏng tình huống không thể fetch được.
        "tech": [
            {
                "title": None,
                "url": "https://mirror.example.com/tech/openai-reasoning",
                "content": None,
                "error": "timeout",
            }
        ],
    },
}

# Kết quả giả lập cho search_more(keyword) — dùng khi agent tìm thông tin bổ sung
# thay vì fetch lại nguồn gốc.
SEARCH_RESULTS = {
    "source_down": (
        "Theo các nguồn tin công nghệ khác, OpenAI vừa công bố model reasoning mới "
        "với cải tiến về tốc độ suy luận và chi phí inference thấp hơn thế hệ trước."
    ),
    "always_down": (
        "Không tìm thấy thông tin bổ sung đáng tin cậy nào về chủ đề này vào lúc này."
    ),
}


def get_sources(topic: str, scenario: str = "normal"):
    """Trả về danh sách nguồn giả lập cho 1 topic ("tech"/"sport") theo kịch bản."""
    return SCENARIOS[scenario][topic]


def get_backup_sources(topic: str, scenario: str = "normal"):
    """Trả về nguồn dự phòng (mirror) cho 1 topic. Rỗng nếu kịch bản không có backup."""
    return BACKUP_SOURCES.get(scenario, {}).get(topic, SCENARIO_NORMAL[topic])


def search_more(keyword: str, scenario: str = "normal") -> str:
    """Giả lập tìm kiếm bổ sung theo từ khoá."""
    return SEARCH_RESULTS.get(
        scenario, f"Không có kết quả tìm kiếm bổ sung nào cho '{keyword}'."
    )
