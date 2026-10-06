"""GUIDE Phần 3 - Người tuyển chọn skill (skill curator): tự viết skill từ các lần chạy thất bại.   >>> SINH VIÊN CÀI ĐẶT curate_skills <<<

Pseudo-code: guides/pseudocode/04_curator.md
Kiểm tra:    pytest tests/test_04_curator.py
Chạy thật:   python -m lab.curator
"""
import json
import re
from pathlib import Path

from .tasks import ROOT, eval_markers   # có sẵn: định danh của tác vụ đánh giá, tính lúc chạy

TRACE_TAIL = 6000   # chỉ đưa phần cuối của vết vào prompt (giới hạn token)

# Mẫu prompt theo guides/pseudocode/04_curator.md, viết bằng tiếng Anh vì mô hình và tác vụ dùng tiếng Anh.
CURATOR_PROMPT = """You write SKILLS for a coding and data-analysis agent.
Below are the failed checks (name and the review bot's feedback) and the traces of some runs.
Find the general PROCESS mistakes (not the specific answers) and write at most {max_skills} short skills
that help avoid those mistakes on NEW tasks of the same kind.

Rules:
- Skills must be general: do not mention task ids, file names that belong to one task, answers or numbers.
  Names that a written company convention requires (required output file names, JSON keys, headings) are allowed,
  because they are the rule itself.
- Each skill has a YAML frontmatter with `name` (lower case, hyphens) and `description` (one sentence starting with
  "Use when ..." that names a broad kind of task), then at most 40 lines of imperative instructions
  (a numbered checklist works well, finish with a short self-check list).
- Output format, exactly:
=== SKILL: <name> ===
---
name: <name>
description: <when to use>
---
<body>
=== END ===

{runs}"""


def _load_learning_runs(results_dir: Path, source_condition: str) -> list[dict]:
    """Nạp run.json + phần cuối trace.md của các TÁC VỤ HỌC; bỏ qua mọi run của tác vụ đánh giá."""
    runs = []
    for run_file in sorted((Path(results_dir) / source_condition).glob("*/run.json")):
        r = json.loads(run_file.read_text(encoding="utf-8"))
        if r.get("role") != "learn":
            continue
        trace_file = run_file.parent / "trace.md"
        trace = trace_file.read_text(encoding="utf-8")[-TRACE_TAIL:] if trace_file.exists() else ""
        failed = [(c["name"], c.get("detail", "")) for c in r.get("checks", []) if not c.get("passed")]
        runs.append({"task": r.get("task", run_file.parent.name), "failed": failed, "trace": trace})
    return runs


def _format_runs(runs: list[dict]) -> str:
    parts = []
    for run in runs:
        if not run["failed"]:
            continue
        checks = "\n".join(f"- {name}: {detail}" for name, detail in run["failed"])
        parts.append(f"## Run of learning task {run['task']}\nFailed checks:\n{checks}\n\n"
                     f"End of the trace:\n{run['trace']}")
    return "\n\n".join(parts)

# ---- CÓ SẴN, KHÔNG SỬA: kiểm tra và tách khối skill (phần dễ sai và liên quan bảo mật) ----------------
SAFE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_skill(text: str, expected_name: str | None = None) -> list[str]:
    """Kiểm tra nội dung một SKILL.md. Trả về danh sách vấn đề (rỗng = hợp lệ).

    Quy tắc: có khối YAML frontmatter; `name` chữ thường/số/gạch ngang (tối đa 64 ký tự) và bằng `expected_name`
    nếu được truyền; có `description` (tối đa 1024 ký tự); phần thân tối đa 80 dòng; không chứa chuỗi nào của
    `eval_markers()`. Quy tắc về `name` cũng là biện pháp bảo mật: tên khối do LLM sinh ra được dùng để tạo
    đường dẫn, nên `../evil` không được lọt qua.
    """
    problems = []
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text.strip() + "\n", re.S)
    if not m:
        return ["missing YAML frontmatter"]
    front, body = m.groups()
    name = re.search(r"^name:\s*(.+)$", front, re.M)
    desc = re.search(r"^description:\s*(.+)$", front, re.M)
    n = name.group(1).strip() if name else ""
    if not SAFE_NAME.fullmatch(n) or len(n) > 64:
        problems.append("invalid name")
    elif expected_name is not None and n != expected_name:
        problems.append("name differs from the block name")
    if not desc or len(desc.group(1).strip()) > 1024:
        problems.append("missing or too long description")
    if len(body.strip().splitlines()) > 80:
        problems.append("body longer than 80 lines")
    low = text.lower()
    for marker in eval_markers():
        if marker in low:
            problems.append(f"mentions evaluation material: {marker}")
    return problems


def parse_skill_blocks(reply: str) -> list[tuple[str, str]]:
    """Tách câu trả lời của LLM thành danh sách (name, nội dung SKILL.md).

    Khuôn dạng: `=== SKILL: <name> ===` ... `=== END ===`. Một khối kết thúc ở điểm nào đến trước trong ba điểm:
    `=== END ===`, tiêu đề `=== SKILL:` kế tiếp, hoặc cuối văn bản (LLM đôi khi quên dòng END).
    """
    pattern = re.compile(r"^=== SKILL: (\S+) ===[ \t]*\n(.*?)(?=^=== END ===|^=== SKILL: |\Z)", re.S | re.M)
    return [(name, text.strip()) for name, text in pattern.findall(str(reply))]
# --------------------------------------------------------------------------------------------------


def curate_skills(results_dir="results", source_condition="baseline", out_dir=None, model=None, max_skills: int = 3) -> list[Path]:
    """Đọc các lần chạy của TÁC VỤ HỌC (role == "learn") trong `source_condition`, nhờ LLM viết skill, ghi file.

    Các bước: nạp run.json + trace.md -> (nếu không có check nào thất bại: in cảnh báo và trả về [] mà KHÔNG gọi LLM)
    -> dựng prompt -> model.invoke(prompt) -> parse_skill_blocks -> validate_skill(text, expected_name=name)
    -> ghi `<out_dir>/<name>/SKILL.md`. Mặc định `out_dir` = <gốc lab>/skills/auto (dùng `ROOT` từ lab.tasks).
    Giữ tối đa `max_skills` skill hợp lệ; skill không hợp lệ bị bỏ qua.
    Prompt chứa, với mỗi check thất bại, TÊN và trường `detail` (lời nhận xét của bot đánh giá: phát biểu quy tắc bị vi phạm)
    cùng phần cuối của vết (trace). Với tác vụ học, `detail` chỉ phát biểu quy tắc, không chứa đáp án.
    Tuyệt đối KHÔNG đưa dữ liệu của tác vụ đánh giá (role == "eval") vào prompt.
    model mặc định: make_model() (lab.model).
    Trả về: danh sách đường dẫn SKILL.md đã ghi.
    """
    out_dir = Path(out_dir) if out_dir is not None else ROOT / "skills" / "auto"
    runs = _load_learning_runs(Path(results_dir), source_condition)
    if not any(run["failed"] for run in runs):
        print(f"WARNING: no failed check in the learning runs of '{source_condition}', nothing to curate")
        return []

    if model is None:
        from .model import make_model
        model = make_model()
    prompt = CURATOR_PROMPT.format(max_skills=max_skills, runs=_format_runs(runs))
    reply = model.invoke(prompt).content

    written = []
    for name, text in parse_skill_blocks(reply):
        if len(written) >= max_skills:
            break
        problems = validate_skill(text, expected_name=name)
        if problems:
            print(f"skip skill {name!r}: {', '.join(problems)}")
            continue
        path = out_dir / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    for p in curate_skills():
        print("wrote", p)
