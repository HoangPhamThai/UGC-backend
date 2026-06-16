"""Code-defined registry of every report field a rule may read or write.
Single source of truth for the LLM prompt, the IR validator, and the engine.
Field keys are the EXACT template token names used in report_to_render_inputs."""
from dataclasses import dataclass
from typing import Literal, Optional

Scope = Literal["scalar", "line_item"]
FieldType = Literal["money_int", "int", "string", "enum"]

_PLATFORMS = ("Threads", "Tiktok", "Facebook", "Youtube")


@dataclass(frozen=True)
class FieldDef:
    key: str
    scope: Scope
    type: FieldType
    writable: bool
    description: str  # Vietnamese; fed to the LLM prompt
    enum_values: Optional[tuple[str, ...]] = None


_FIELDS: list[FieldDef] = [
    # --- scalar, writable (financials) ---
    FieldDef("tax", "scalar", "money_int", True,
             "Thuế TNCN của báo cáo (Điều 3). Base = round(total_award * tax_rate)."),
    FieldDef("total_award", "scalar", "money_int", True,
             "Tổng thù lao (Điều 3). Base = article_award_price * số bài."),
    FieldDef("final_award", "scalar", "money_int", True,
             "Thực nhận sau thuế (Điều 3). Base = total_award - tax."),
    FieldDef("article_award_price", "scalar", "money_int", True,
             "Đơn giá mỗi bài được duyệt."),
    # --- scalar, input-only ---
    FieldDef("total_approved_articles", "scalar", "int", False,
             "Số bài được duyệt trong kỳ."),
    FieldDef("total_articles", "scalar", "int", False,
             "Tổng số bài (bằng total_approved_articles)."),
    # --- line_item, writable ---
    FieldDef("article_bonus_money", "line_item", "money_int", True,
             "Tiền thưởng của 1 bài trong bảng Điều 2."),
    # --- line_item, input-only ---
    FieldDef("article_view", "line_item", "int", False,
             "Lượt xem của bài (cột view trong bảng Điều 2)."),
    FieldDef("article_platform", "line_item", "enum", False,
             "Nền tảng đăng bài.", enum_values=_PLATFORMS),
]

FIELD_REGISTRY: dict[str, FieldDef] = {f.key: f for f in _FIELDS}


def get_field(key: str) -> Optional[FieldDef]:
    return FIELD_REGISTRY.get(key)


def writable_keys() -> set[str]:
    return {f.key for f in _FIELDS if f.writable}


def field_keys_in_scope(scope: Scope) -> set[str]:
    """Keys a rule of `scope` may READ. line_item rules see line_item + scalar;
    scalar rules see only scalar."""
    if scope == "line_item":
        return set(FIELD_REGISTRY.keys())
    return {f.key for f in _FIELDS if f.scope == "scalar"}
