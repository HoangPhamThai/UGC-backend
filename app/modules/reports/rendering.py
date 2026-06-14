# app/modules/reports/rendering.py
"""Render the acceptance report .docx from the vendored template.

Token replacement coalesces a paragraph's runs before substituting, because
python-docx splits text across runs and a {token} can straddle runs. The Điều 2
table's single data row is cloned once per line item."""
import copy
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.table import Table, _Row

TEMPLATE_PATH = str(Path(__file__).parent / "templates" / "acceptance_report.docx")

# The per-row tokens that identify (and fill) the Điều 2 article table.
_ROW_TOKEN = "{article_platform}"
_ROW_KEYS = (
    "article_platform",
    "article_id_autoinc",
    "article_on_air",
    "article_link",
    "article_view",
)


def _replace_in_paragraph(paragraph, mapping: dict) -> None:
    """Replace every {key} in the paragraph with mapping[key], coalescing runs.
    Only rewrites when at least one token is present (preserves formatting
    elsewhere)."""
    full = "".join(run.text for run in paragraph.runs)
    if "{" not in full:
        return
    new = full
    for key, value in mapping.items():
        new = new.replace("{" + key + "}", value)
    if new == full:
        return
    if paragraph.runs:
        paragraph.runs[0].text = new
        for run in paragraph.runs[1:]:
            run.text = ""


def _iter_cell_paragraphs(table: Table):
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                yield paragraph


def _row_contains_token(row, token: str) -> bool:
    return any(token in cell.text for cell in row.cells)


def _fill_row(row, item: dict) -> None:
    mapping = {k: str(item.get(k, "")) for k in _ROW_KEYS}
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            _replace_in_paragraph(paragraph, mapping)


def render_acceptance_report(*, scalars: dict, line_items: list[dict]) -> bytes:
    """Fill the template and return the .docx as bytes.

    `scalars` maps scalar token names (without braces) to string values, e.g.
    {"creator_name": "...", "final_award": "900000"}. `line_items` is a list of
    dicts keyed by the article_* token names for the Điều 2 rows."""
    document = Document(TEMPLATE_PATH)
    scalar_map = {k: str(v) for k, v in scalars.items()}

    # Replace scalar tokens in body paragraphs.
    for paragraph in document.paragraphs:
        _replace_in_paragraph(paragraph, scalar_map)

    # Find the article table (contains the row-template token) and its template row.
    # Snapshot tables list once so we use consistent object identity via _tbl.
    tables = list(document.tables)
    article_table_idx = None
    template_row = None
    for idx, table in enumerate(tables):
        for row in table.rows:
            if _row_contains_token(row, _ROW_TOKEN):
                article_table_idx = idx
                template_row = row
                break
        if article_table_idx is not None:
            break

    # Replace scalar tokens in all table cells, skipping the article template row.
    for idx, table in enumerate(tables):
        for row in table.rows:
            # Skip the article template row itself — it will be cloned per item.
            if idx == article_table_idx and template_row is not None and row._tr is template_row._tr:
                continue
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_in_paragraph(paragraph, scalar_map)

    # Clone the article template row once per line item, fill each clone,
    # then remove the original template row.
    if template_row is not None and article_table_idx is not None:
        article_table = tables[article_table_idx]
        anchor_tr = template_row._tr
        ref = anchor_tr
        for item in line_items:
            new_tr = copy.deepcopy(anchor_tr)
            ref.addnext(new_tr)
            ref = new_tr
            _fill_row(_Row(new_tr, article_table), item)
        anchor_tr.getparent().remove(anchor_tr)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
