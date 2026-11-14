# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - Tác phẩm: *The Great Gatsby* (F. Scott Fitzgerald).
  - Nguồn: Project Gutenberg eBook #64317 (`data/the_great_gatsby.html`).
  - Bản quyền: Public Domain (Project Gutenberg License).
  - Quy mô: 161 trang ảo (vượt xa mức tối thiểu 30 trang).
  - Quy tắc tính trang:
    - Loại bỏ header/footer bản quyền Gutenberg.
    - Trích xuất nội dung từ 9 thẻ `div id="chapter-X"`.
    - Gom đoạn `<p>` liên tiếp đến khi đủ ≥1.500 ký tự chuẩn hóa thì ngắt 1 trang (`page: 1..161`).
    - Bảo toàn nguyên vẹn ranh giới đoạn văn.

- **Chuẩn hóa, lỗi và giới hạn:**
  - Chuẩn hóa Unicode NFKC (`unicodedata.normalize`).
  - Gộp khoảng trắng thừa (`[ \t]+` thành `" "`).
  - Giữ nguyên `\n\n` để phục vụ phân đoạn.
  - Loại bỏ các thẻ HTML phụ (`<span>`, `<i>`).
  - Giới hạn: Trang ảo là phân vùng quy ước (~1.500 ký tự), không phải số trang sách in vật lý.

- **Embedding model, vector store, metric, lệnh chạy, chi phí:**
  - Model: Google Gemini `gemini-embedding-001`, 768 chiều (Matryoshka reduction).
  - Vector Store: PostgreSQL 16 + pgvector 0.8.7 (Docker Compose, cổng 55433).
  - Metric: Cosine Distance (`<=>`), similarity: `1 - (embedding <=> q::vector)`.
  - Lệnh chạy: `uv run python starter/src/run.py`.
  - Chi phí: $0 (Google AI Studio Free Tier).

- **Metadata và trường lọc:**
  - Bắt buộc: `document_id` (`the-great-gatsby`), `source`, `page` (1..161).
  - Trường lọc bổ sung: `chapter` (`Chapter 1` đến `Chapter 9`).
  - Nguồn giá trị: Thuộc tính `id` của thẻ chapter trong file HTML gốc.
  - Lý do chọn: Truyện chia 9 chương rõ rệt; lọc theo `chapter` giúp cô lập sự kiện theo thời điểm, tránh nhiễu ngữ nghĩa giữa các chương.

## Cấu hình và benchmark
- **Cấu hình A / B / C:**
  - Strategy A: Fixed-size 500 ký tự, overlap 50 ký tự, không filter (673 chunks).
  - Strategy B: By-paragraph, tối đa 800 ký tự, không filter (458 chunks).
  - Strategy C: Dùng lại 458 chunks của B; khi search áp dụng `WHERE metadata->>'chapter' = ...` cho câu hỏi có filter.
  - Khác biệt duy nhất B–C: Thêm điều kiện lọc metadata ở khâu truy xuất.

- **Bộ câu hỏi benchmark:**
  - Tổng số: 20 câu (`benchmark/questions.json`).
  - Phân chia: 15 Dev / 5 Test (chốt độc lập trước khi chạy pipeline).
  - Filter: 3 câu có lọc `chapter` (`q05`, `q11` ở Dev; `q17` ở Test).
  - Kiểm chứng evidence: 100% câu có `evidence_quote` khớp từng ký tự trên `gold_page`.

- **Tiêu chí chọn chiến lược:**
  - Ưu tiên 1: Evidence Hit@3 trên tập Dev.
  - Ưu tiên 2: Tính mạch lạc ngữ cảnh (Chunk Coherence).
  - Ưu tiên 3: Tối ưu số lượng chunk và tài nguyên vector store.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **A (Fixed-size 500/50)** | dev<br>test<br>**overall** | 9/15 (60.0%)<br>1/5 (20.0%)<br>**10/20 (50.0%)** | 12/15 (80.0%)<br>2/5 (40.0%)<br>**14/20 (70.0%)** | 673 | ~35s | $0 |
| **B (Paragraph max 800)** | dev<br>test<br>**overall** | 9/15 (60.0%)<br>3/5 (60.0%)<br>**12/20 (60.0%)** | 13/15 (86.7%)<br>3/5 (60.0%)<br>**16/20 (80.0%)** | 458 | ~25s | $0 |
| **C (Paragraph + Filter)** | dev<br>test<br>**overall** | 9/15 (60.0%)<br>3/5 (60.0%)<br>**12/20 (60.0%)** | 13/15 (86.7%)<br>3/5 (60.0%)<br>**16/20 (80.0%)** | 458 | ~25s | $0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|:---:|:---:|:---:|:---:|
| **A (Fixed-size 500/50)** | **0.4 / 2.0** (n=10) | 15/15 (100%) | N/A | 0: 1 câu \| 1: 2 câu \| 2: 2 câu $\rightarrow$ **1.2 / 2.0** |
| **B (Paragraph max 800)** | **2.0 / 2.0** (n=10) | 15/15 (100%) | N/A | 0: 1 câu \| 1: 1 câu \| 2: 3 câu $\rightarrow$ **1.4 / 2.0** |
| **C (Paragraph + Filter)** | **2.0 / 2.0** (n=10) | 15/15 (100%) | **1/1 (100%)** | 0: 0 câu \| 1: 2 câu \| 2: 3 câu $\rightarrow$ **1.6 / 2.0** |

- **Đường dẫn artifacts:**
  - Traces chi tiết: [results/traces.json](../../results/traces.json)
  - Tóm tắt kết quả: [results/summary.json](../../results/summary.json)
  - Nhật ký thí nghiệm: [artifacts/experiment_log.csv](../../artifacts/experiment_log.csv)
- **Mẫu kiểm tra thủ công:**
  - Coherence: Chunk đầu tiên của 10 trang đầu tiên (Page 1..10).
  - Metadata & Grounding: Toàn bộ 5 câu Test (`q16`..`q20`) $\times$ Top-3 chunks.

## Phân tích và kết luận
- **So sánh A–B:**
  - Hit@3: B vượt trội A ở cả Dev (86.7% vs 80.0%) và Test (60.0% vs 40.0%).
  - Coherence: B đạt 2.0/2.0 (không gãy câu), A chỉ đạt 0.4/2.0 (6/10 vị trí bị cắt đứt từ ngữ).
  - Tài nguyên: B giảm 31.9% số chunk (458 vs 673), tiết kiệm chi phí embed và dung lượng DB.

- **So sánh B–C:**
  - Hit@3: Bằng nhau (16/20 câu), do các câu hỏi đã tìm trúng ngay từ Rank 1.
  - Tác dụng của C: Loại bỏ 100% tài liệu nhiễu xuyên chương trong top-3 (100% tuân thủ filter).

- **2 ví dụ lỗi cụ thể:**
  - `q18` (Gatsby giải thích lý do không dám nhận là Oxford man, trang 113):
    - Strategy A: Cắt cố định 500 ký tự chém đôi câu nói *"It was in nineteen-nineteen..."* sang 2 chunks $\rightarrow$ cả 2 chunk đều cụt ý $\rightarrow$ Hit@1=False, Hit@3=False.
    - Strategy B: Giữ nguyên đoạn thoại trong 1 chunk $\rightarrow$ Hit@1=True, Hit@3=True.
  - `q17` (Nhận xét về giọng nói của Daisy ở Chapter 7, trang 105):
    - Strategy B (không filter): Bị trôi dạt sang Chapter 6 (trang 85) và Chapter 8 (trang 131) do cùng từ khóa "Daisy", "voice".
    - Strategy C (có filter `Chapter 7`): Kéo toàn bộ top-3 về đúng Chapter 7 (trang 104, 105, 116), loại sạch nhiễu ngoài chương.

- **Chiến lược chọn và đánh đổi:**
  - Chọn: **Strategy B** (kết hợp **Strategy C** khi câu hỏi có filter).
  - Đánh đổi: Chunk theo đoạn văn có kích thước không đều (100–800 ký tự), nhưng đổi lại ngữ nghĩa toàn vẹn và giảm dung lượng lưu trữ.
  - Áp dụng: Phù hợp với dữ liệu có cấu trúc đoạn văn rõ ràng (sách báo, hợp đồng, cẩm nang).

- **Hạn chế:**
  - Tập Test nhỏ (5 câu), mỗi câu chiếm tỷ trọng 20%.
  - Trang ảo 1.500 ký tự là phân vùng nhân tạo, một số câu ở mép trang có thể bị ngắt nhẹ.

- **Hướng cải tiến:**
  - Chunking: Dùng Recursive Character Splitter theo thứ tự ưu tiên `["\n\n", "\n", ". ", " "]`.
  - Metadata: Trích xuất thêm `speaker` (nhân vật phát ngôn) để hỗ trợ tìm kiếm hội thoại.
  - Retrieval: Kết hợp Hybrid Search (BM25 sparse + pgvector dense) để bắt chính xác cả tên riêng và ngữ nghĩa.
