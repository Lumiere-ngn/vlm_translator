from __future__ import annotations

import json

from models import LawRecord


PLACEHOLDERS = ("{{law_json}}", "{{title}}", "{{section_number}}", "{{content}}")


def render_prompt(template: str, law: LawRecord) -> str:
    law_json = json.dumps(law.model_dump(), ensure_ascii=False, indent=2)
    rendered = template
    rendered = rendered.replace("{{law_json}}", law_json)
    rendered = rendered.replace("{{title}}", law.title)
    rendered = rendered.replace("{{section_number}}", law.section_number)
    rendered = rendered.replace("{{content}}", law.content)
    if not any(marker in template for marker in PLACEHOLDERS):
        rendered = f"{template.rstrip()}\n\nLaw JSON:\n{law_json}"
    return rendered
