import re
from typing import List, Optional

from app.models.schemas import FigureRegion, LayoutPage, MCQQuestion

# Matches: "1.", "1)", "Q1.", "Q. 1.", "Question 1."
_QUESTION_RE = re.compile(
    r"^\s*(?:question\s*|q\.?\s*)?(\d+)\s*[.)]\s*(.*)$",
    re.IGNORECASE,
)
# Matches: "A.", "A)", "(A)", "A:"
_OPTION_RE = re.compile(r"^\s*\(?([A-E])\)?\s*[.):\s]\s*(.*)", re.IGNORECASE)
# Matches: "Answer: B" or "Ans: B" anywhere in a line
_ANSWER_RE = re.compile(r"\bans(?:wer)?\s*[:\-]\s*([A-E])\b", re.IGNORECASE)


def _figure_overlaps(fig: FigureRegion, y_start: float, y_end: float) -> bool:
    _, fy0, _, fy1 = fig.bbox
    return fy0 <= y_end and fy1 >= y_start


def structure(layout_page: LayoutPage) -> List[MCQQuestion]:
    """Convert a LayoutPage into a list of MCQQuestion objects deterministically."""
    # Flatten all text blocks into (line_text, bbox) sorted by top→bottom, left→right
    lines: list[tuple[str, tuple[float, float, float, float]]] = []
    for block in sorted(layout_page.text_blocks, key=lambda b: (b.bbox[1], b.bbox[0])):
        for raw in block.text.split("\n"):
            stripped = raw.strip()
            if stripped:
                lines.append((stripped, block.bbox))

    # Parse lines into raw question groups
    groups: list[dict] = []
    current: Optional[dict] = None
    in_options = False
    last_option: Optional[str] = None

    for line, bbox in lines:
        ans_match = _ANSWER_RE.search(line)
        q_match = _QUESTION_RE.match(line)
        opt_match = _OPTION_RE.match(line)

        if q_match:
            if current is not None:
                groups.append(current)
            current = {
                "question_number": int(q_match.group(1)),
                "question_text": q_match.group(2).strip(),
                "options": {},
                "answer": None,
                "bboxes": [bbox],
            }
            in_options = False
            last_option = None
            if ans_match:
                current["answer"] = ans_match.group(1).upper()
        elif opt_match and current is not None:
            letter = opt_match.group(1).upper()
            text = opt_match.group(2).strip()
            current["options"][letter] = text
            current["bboxes"].append(bbox)
            in_options = True
            last_option = letter
            if ans_match:
                current["answer"] = ans_match.group(1).upper()
        elif current is not None:
            if in_options and last_option:
                current["options"][last_option] += " " + line
            else:
                sep = " " if current["question_text"] else ""
                current["question_text"] += sep + line
            current["bboxes"].append(bbox)
            if ans_match:
                current["answer"] = ans_match.group(1).upper()

    if current is not None:
        groups.append(current)

    # Build MCQQuestion objects
    questions: List[MCQQuestion] = []
    for grp in groups:
        n_opts = len(grp["options"])
        if n_opts <= 1:
            continue  # likely noise or a non-MCQ line

        if n_opts >= 4 and grp["question_text"]:
            confidence = "high"
        elif n_opts >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Determine vertical span of this question
        y_start = min(b[1] for b in grp["bboxes"])
        y_end = max(b[3] for b in grp["bboxes"])

        # Associate figures whose vertical range overlaps this question's span
        has_image = any(_figure_overlaps(fig, y_start, y_end) for fig in layout_page.figures)

        # Also flag if question text references a figure/diagram by name
        if not has_image and re.search(
            r"\b(?:fig(?:ure)?|diagram|chart|graph|image|illustration)\b",
            grp["question_text"],
            re.IGNORECASE,
        ):
            has_image = True

        questions.append(
            MCQQuestion(
                question_number=grp["question_number"],
                page=layout_page.page_num,
                question_text=grp["question_text"],
                has_image=has_image,
                options=grp["options"],
                answer=grp["answer"],
                confidence=confidence,
            )
        )

    return questions
