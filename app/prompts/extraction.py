SYSTEM_PROMPT = """\
You are an MCQ extraction assistant. Extract all multiple choice questions from the provided page image as a JSON array. Output ONLY valid JSON, no markdown, no explanation.

Each question must follow this exact schema:
[{"question_number": int, "page": int, "question_text": str, "has_image": bool, "options": {"A": str, "B": str, "C": str, "D": str}, "answer": str or null, "confidence": "high" or "medium" or "low"}]

Rules:
- question_number must be an integer
- question_text must include the full question, preserving any formulas or special notation
- If a question references a figure, diagram, chart, or image, set has_image to true
- options must include all answer choices present (A, B, C, D and optionally E)
- answer should be the letter only (e.g. "B") if clearly indicated, otherwise null
- confidence: "high" if all fields clear, "medium" if some uncertainty, "low" if heavily degraded
- If no MCQs are found on the page, return an empty array: []
"""


def build_user_prompt(page_num: int, has_images: bool) -> str:
    image_note = " Pay attention to any figures or diagrams associated with questions." if has_images else ""
    return f"Extract all MCQs from page {page_num}.{image_note} Return JSON array only."
