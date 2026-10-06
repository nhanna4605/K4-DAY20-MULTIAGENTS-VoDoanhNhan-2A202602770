# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Võ Doanh Nhân | 2A202602770 | Toàn bộ (làm cá nhân) |

- Nhà cung cấp và mô hình (`LAB_MODEL`, không ghi khóa API), nhiệt độ (`LAB_TEMPERATURE`), `recursion_limit`: endpoint tương thích OpenAI (`LAB_BASE_URL=https://api.shopaikey.com/v1`, một cổng trung gian), `LAB_MODEL=gpt-4.1-mini`, `LAB_TEMPERATURE=0`, `recursion_limit=60` (mặc định của `lab.runner`). Lần chạy thử đầu tiên dùng `gpt-4o-mini` và bị loại (xem Phụ lục).
- Phiên bản Deep Agents (`pip show deepagents`), hệ điều hành, chạy trực tiếp hay trong Docker: `deepagents 0.7.21`, Python 3.12 trong container Docker dựng từ `Dockerfile` của kho (`python:3.12-slim`), máy chủ Windows 11 + Docker Desktop (engine 29.7.2). Để chạy được `scripts/verify_freeze.py` và `scripts/check_breakdown.py` (cần `git`), tôi dựng thêm một image cục bộ `FROM lab-deepagents` + `apt-get install git`; image này không đổi môi trường Python của tác tử.
- Số lần chạy tác vụ đã dùng / ngân sách: (điền sau khi chạy chính thức)
- Commit của tag `freeze`: (điền sau khi đóng băng)

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

- H1 (subagents so với baseline): `subagents` KHÔNG cao hơn `baseline` trên tác vụ đánh giá: chênh lệch điểm trung bình nằm trong khoảng ±0,10, còn token trung bình cao hơn `baseline` từ 20% đến 100%. Căn cứ: ở tác vụ học, check kỹ thuật của hai điều kiện bằng nhau (12/18) và cả hai đạt 0/9 check quy ước. Tác tử chính chỉ giao việc ở 2/3 tác vụ, một lần cho `general-purpose` chứ không cho subagent tự định nghĩa. Lời giao việc còn làm mất thông tin (logs-learn mất cấu trúc khóa `errors`). Không subagent nào biết quy ước Acme, nên không thể sửa nhóm lỗi E. Bài viết của Anthropic về hệ đa tác tử cũng ghi nhận chi phí token cao hơn nhiều so với một tác tử.
- H2 (skills-auto so với baseline): `skills-auto` KHÔNG cải thiện đáng kể so với `baseline` trên tác vụ đánh giá (|chênh lệch điểm trung bình| ≤ 0,10), và check quy ước `rule_` của tác vụ đánh giá vẫn đạt gần 0, kể cả quy ước mới. Căn cứ: ở Phần 3.4 `skills_read = 0` ở cả 3/3 tác vụ học, tức tác tử không mở skill nào. Ba skill do curator sinh chỉ nêu quy trình chung, không chứa quy ước cụ thể (khối `meta`, `clean.csv`, CHANGELOG, header của log-triage). SkillsBench cũng ghi nhận skill do mô hình tự sinh trung bình không có lợi.
- H3 (tác vụ học so với tác vụ đánh giá): Chênh lệch giữa các điều kiện quan sát được ở tác vụ học sẽ KHÔNG chuyển sang tác vụ đánh giá, và điểm trung bình tác vụ đánh giá của mỗi điều kiện không cao hơn điểm tác vụ học của chính điều kiện đó, vì tác vụ đánh giá thêm một quy ước mới mà không điều kiện nào biết. Nhiễu giữa hai lần chạy gần như cùng cấu hình có thể lên tới 4 check trên một tác vụ: logs-learn đạt 0/9 ở `baseline` nhưng 4/9 ở `skills-auto` dù tác tử không đọc skill. Vì vậy mọi chênh lệch điểm trung bình dưới khoảng 0,15 được xem là nhiễu. Điều này khớp với SkillEvolBench (lợi ích trên tác vụ học thường không chuyển sang tác vụ mới).

## 3. Làm quen Deep Agents (Phần 0.3)

Nguồn: kết quả `python scripts/tour.py` (mô hình giả, 0 token).

1. Tác tử mặc định có 9 công cụ: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep` (công cụ tệp), `execute` (shell) và `task` (giao việc cho subagent). Chỉ `execute` chạy được lệnh hệ điều hành; `task` gián tiếp cho phép chạy lệnh qua subagent `general-purpose`, vì subagent này có cùng bộ công cụ với tác tử chính.
2. Mô tả `task` nói `general-purpose` dùng cho nghiên cứu câu hỏi phức tạp, tìm tệp/nội dung và tác vụ nhiều bước, và nó "has access to all tools as the main agent". Về ngữ cảnh: mỗi lần gọi mặc định không giữ trạng thái; subagent chỉ thấy đúng prompt mà tác tử chính gửi (không thấy hội thoại của tác tử chính, trừ loại subagent được ghi là kế thừa hội thoại) và trả về một báo cáo cuối duy nhất.
3. Câu trích từ mô tả `task`: "Each invocation is stateless by default: the agent sees only the prompt you give it and returns a single final report." Câu trích từ mô tả `execute`: "You MUST avoid using search commands like find and grep." Ghi chú: mô tả `execute` còn khuyên "Use absolute paths and avoid `cd`", trái với quy ước đường dẫn tương đối của `BASE_PROMPT`/`PATHS_NOTE`; vì vậy harness phải nhắc lại quy ước tương đối trong system prompt và trong prompt của mỗi subagent.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Nguồn: `results/baseline/<task>/run.json` (khóa `checks`) và `trace.md`, chỉ tác vụ học. Có 15 check thất bại.

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| code-learn | `rule_type_hints` | E | `detail`: "RULE: every public function ... has type annotations on all parameters and on the return value." |
| code-learn | `rule_regression_tests` | E | `detail`: "RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3)". Tác tử không tạo tệp này. |
| code-learn | `rule_changelog` | E (kèm A) | `detail`: "RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' ...". Vết: tác tử chỉ đọc mã nguồn và test, không mở `workspace/CHANGELOG.md` hay `workspace/README.md`, dù CHANGELOG có sẵn mục `## Unreleased` để trống. |
| data-learn | `rule_money_in_cents` | E | `detail`: "RULE: money values in answer.json are integer cents (1606.67 USD is written 160667)." |
| data-learn | `rule_meta_block` | E | `detail`: "RULE: answer.json has an object `meta` = {"source": ..., "rows_in": ..., "rows_used": ...}". |
| data-learn | `rule_clean_csv` | E | `detail`: "RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents ...". |
| logs-learn | `valid_structure`, `entry_count`, `timestamps_utc`, `exception_fields`, `repeat_counts`, `counts_by_service` (6 check kỹ thuật) | F (kèm B) | Vết: lần ghi duy nhất là `write_file {"file_path": "/workspace/errors.json", "content": ""}` (tệp rỗng), sau đó câu trả lời cuối nói "wrote the results to workspace/errors.json in the required JSON structure". `detail` của cả 6 check: "JSONDecodeError: Expecting value: line 1 column 1 (char 0)". Tác tử không chạy lệnh nào để kiểm chứng (4 tool call: 3 `read_file` + 1 `write_file`). |
| logs-learn | `rule_service_names`, `rule_sorted_errors`, `rule_schema_header` | F (hệ quả) | Cùng `detail` "JSONDecodeError ...": bot không chấm được quy ước vì tệp rỗng, nên ở lần chạy này không có phản hồi `RULE:` nào cho họ `logs`. |

Bằng chứng phủ định cho nhóm A đến D (`python scripts/check_breakdown.py`, trước khi đóng băng): `baseline` đạt 12/18 check kỹ thuật và 0/9 check quy ước. Ở `code-learn` cả 7/7 check kỹ thuật đạt, gồm `low_stock_follows_docstring`, `csv_quoting_follows_docstring` (đọc docstring: không phải A) và `other_caller_fixed` (sửa ở hàm dùng chung, không vá triệu chứng: không phải C). Ở `data-learn` 5/5 check kỹ thuật đạt (`duplicate_rows_removed`, `missing_amount_orders`, `north_q1_revenue` theo UTC: không phải D). 6 check kỹ thuật thất bại đều thuộc `logs-learn` và có chung một nguyên nhân là tệp rỗng (F/B).

Nhận xét: theo số check, nhóm F chiếm 9/15, nhưng đều bắt nguồn từ **một** sự kiện (một lần ghi tệp rỗng rồi báo hoàn thành). Theo nguyên nhân độc lập, nhóm E chiếm đa số: 6 quy ước ở `code-learn` và `data-learn` bị vi phạm, đúng như kỳ vọng của GUIDE. Nguyên nhân chung là quy ước Acme không có trong đề, và tác tử không đi tìm tài liệu quy ước trong workspace. Một skill có thể phòng ngừa E nếu nó ghi đúng quy ước (đây là tri thức thủ tục ổn định giữa các tác vụ cùng họ), và có thể phòng ngừa F/B bằng một bước bắt buộc "đọc lại tệp đầu ra và kiểm tra không rỗng, đúng khóa". Với họ `logs`, curator không nhận được phản hồi `RULE:` nào ở `baseline` nên không thể suy ra quy ước của họ này.

## 5. Điều kiện `subagents` (Phần 2.3)

- Các subagent đã định nghĩa (tên, vai trò, lý do thiết kế), xem `src/lab/subagents.py`:
  - `explorer`: gọi ĐẦU TIÊN để đọc README/tài liệu quy ước/docstring/mẫu dữ liệu và báo cáo sự thật (kể cả các quy tắc trích nguyên văn), không sửa tệp. Lý do: lỗi nhóm A/E đến từ việc không đọc tài liệu trong workspace.
  - `implementer`: thực hiện thay đổi khi đã có dữ kiện, chạy test/script để kiểm chứng, liệt kê tệp đã đổi. Lý do: tách phần làm khỏi phần đọc để ngữ cảnh của tác tử chính gọn.
  - `reviewer`: gọi CUỐI CÙNG để kiểm tra độc lập (tính lại số, chạy lại test), không sửa. Lý do: phòng nhóm B/F (báo xong mà không kiểm chứng).
- `subagent_calls` ở từng tác vụ và nhận xét (kể cả trường hợp bằng 0):

  | Tác vụ học | `subagent_calls` | Subagent được gọi | Điểm `subagents` / `baseline` |
  |---|---|---|---|
  | code-learn | 0 | (không gọi) | 7/10 / 7/10 |
  | data-learn | 1 | `implementer` | 5/8 / 5/8 |
  | logs-learn | 1 | `general-purpose` (mặc định của Deep Agents, không phải subagent tự định nghĩa) | 0/9 / 0/9 |

  Ở `code-learn`, tác tử chính tự làm toàn bộ (16 tool call) dù `SUBAGENTS_NOTE` khuyến khích giao việc. Vết cho thấy nó đọc mã nguồn, sửa trực tiếp và chạy pytest; với mô hình này, việc nhiều bước nhỏ trên cùng tệp có vẻ được xem là "trivial step". `explorer` và `reviewer` không được gọi ở tác vụ nào, tức hai vai trò được thiết kế để phòng lỗi A/B/F đã không phát huy tác dụng.
- Thông tin thiếu hoặc thừa khi giao việc (nếu có giao việc):
  - `data-learn` → `implementer`: lời giao việc viết lại quy tắc khử trùng thành "Remove duplicate rows (exact duplicates)", trong khi README nói "keep one row per order_id" (mất thông tin; check `duplicate_rows_removed` vẫn đạt vì trong dữ liệu này hai cách cho cùng kết quả). Câu "Follow Acme reporting conventions for output formatting" được chuyển đi nhưng không có nội dung, vì tác tử chính cũng không biết quy ước.
  - `logs-learn` → `general-purpose`: lời giao việc liệt kê các trường nhưng bỏ mẫu JSON của đề (khóa gốc `errors`). Subagent ghi `{"entries":[],"counts_by_service":{}}`. Tác tử chính đọc lại tệp, thấy danh sách rỗng và kết luận "the log file did not have any entries with level ERROR or CRITICAL". Kết luận này sai: log có các dòng `[ERROR]`, `[error]`, `[Error]`, thấy ngay trong vết `baseline`. Đây là trường hợp "kiểm tra nhưng không đối chiếu": có đọc báo cáo của subagent nhưng không so với dữ liệu nguồn, trái với yêu cầu "Check what a subagent returns" của `SUBAGENTS_NOTE`.
- Ảnh hưởng đến token và thời gian: token trung bình trên tác vụ học là 44.155 (`subagents`) so với 35.146 (`baseline`), cao hơn 26%. Lần giao việc cho `implementer` ở `data-learn` làm token tăng 1,95 lần (51.836 so với 26.626) và thời gian từ 26,3 s lên 50,9 s mà không thêm check nào. Hai tác vụ còn lại có token tương đương `baseline` (60.065 so với 56.590; 20.565 so với 22.222).

## 6. Self-evolving: skill do curator sinh (Phần 3)

- Số lần chạy curator, số skill bị xóa và lý do: chạy `python -m lab.curator` **1 lần** (nguồn: `baseline`, 3 tác vụ học), sinh 3 skill hợp lệ, **không xóa** skill nào và **không chạy lại**. Lý do không chạy lại: không skill nào sai hoặc có hại (xem bảng). `skills_read = 0` ở Phần 3.4 không do `description` hẹp: cả ba đều bắt đầu bằng "Use when ..." và nêu loại tác vụ rộng. Tôi đã kiểm tra bằng mô hình giả rằng cả ba skill nằm trong system prompt (mục "Available Skills" với đường dẫn `/skills/<tên>/SKILL.md`) và `skills_sha256` của các lần chạy khớp `hash_skills(skills/auto)`. Nguyên nhân là mô hình bỏ qua chỉ dẫn đọc skill, mà chạy lại curator không sửa được điều đó. Không sửa tay skill nào.

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `enforce-type-annotations` | Tổng quát (mọi mã Python có hàm công khai), không nêu tên tệp/hàm của tác vụ học. | Đúng với `rule_type_hints`. Bước 6 "Run static type checkers (e.g., mypy)" không làm được trong môi trường này (container không cài `mypy`), tác tử có thể tốn bước. Không có hướng dẫn gây hại. | 15 dòng (thân 12 dòng, 7 bước + 3 câu tự kiểm tra); `description` "Use when writing or refactoring Python code ..." đúng tình huống; không được đọc ở `code-learn` (`skills_read = 0`). |
| `add-regression-tests-for-bug-fixes` | Tổng quát; nêu `tests/test_regressions.py` là tên do quy ước Acme yêu cầu (được phép theo `05_skill_quality.md`). | Đúng với `rule_regression_tests` (một test cho mỗi lỗi đã sửa). Thiếu ngưỡng "ít nhất 3". Bước 4 "fail before the fix" tốn thêm bước nhưng không sai. | 15 dòng; `description` "Use when fixing bugs in code ..." khớp `code-learn`; không được đọc (`skills_read = 0`). |
| `follow-data-formatting-and-output-rules` | Rất tổng quát (mọi tệp đầu ra), gần như một danh sách kiểm tra chung. | Đúng hướng (tiền tệ theo cent, chuẩn hóa vùng, UTC, siêu dữ liệu) nhưng thiếu cụ thể: không nêu khối `meta`, không nêu `clean.csv` và header của nó, không nêu quy ước CHANGELOG. Bước 8 "Test the output with the review bot" không làm được vì tác tử không có bot. Không gây hại. | 16 dòng; `description` "Use when preparing output files or data to meet strict formatting ..." đủ rộng cho `data-learn` và `logs-learn`; không được đọc (`skills_read = 0`). |

Nhận xét thêm: không skill nào phủ quy ước CHANGELOG (`rule_changelog`) hoặc quy ước của họ `logs`, vì `baseline` logs-learn không cho phản hồi `RULE:`. Không skill nào phủ lỗi F/B (kiểm tra tệp đầu ra không rỗng), vì lỗi này không có nhận xét của bot dạng quy tắc. Không có tên hay con số của tác vụ đánh giá: `validate_skill` đã lọc theo `eval_markers()`, và tôi không mở tệp nào của tác vụ đánh giá trước khi đóng băng.

Kết quả Phần 3.4 (`skills-auto --tasks learn`, đã sao lưu ở `results/skills-auto-dev/`): code-learn 7/10, data-learn 5/8, logs-learn 4/9, `skills_read = 0` ở cả ba, `skills_modified = false`. logs-learn tăng từ 0/9 lên 4/9 so với `baseline` dù không đọc skill. Đây là nhiễu giữa hai lần chạy. Lần này tác tử cũng ghi `errors.json` rỗng trước (giống `baseline`), nhưng sau đó chạy thêm một script `python3 -c` để phân tích log, ghi lại tệp và đọc lại kết quả. `baseline` thì dừng ngay sau khi ghi tệp rỗng.

## 7. Kết quả so sánh (Phần 4.3, 4.4)

(điền sau khi chạy chính thức)

## 8. Phân tích

(điền sau khi chạy chính thức)

## 9. Hạn chế và tính hợp lệ

(điền sau khi chạy chính thức)

## 10. Kết luận

(điền sau khi chạy chính thức)

## Phụ lục

- Lệnh đã chạy (theo thứ tự): (điền sau khi chạy chính thức)
- Thử thách mở rộng (nếu có): không làm.
- Ghi chú khác: (điền sau khi chạy chính thức)
