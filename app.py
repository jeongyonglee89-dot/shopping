import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).parent / "shopping_list.json"


# ---------- 데이터 함수 ----------

def load_items() -> list[dict]:
    """shopping_list.json에서 아이템 목록을 읽는다. 파일이 없거나 손상되면 빈 목록."""
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def save_items(items: list[dict]) -> None:
    """아이템 목록을 shopping_list.json에 저장한다."""
    DATA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def new_item(name: str, quantity: int = 1) -> dict:
    """PRD 6장 데이터 모델에 맞는 새 아이템을 만든다."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": quantity,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


MAX_NAME_LEN = 50


def _items() -> list[dict]:
    return st.session_state["items"]


def _clean(name: str, quantity) -> tuple[str, int] | None:
    """이름을 trim하고 유효성을 검사한다. 유효하지 않으면 None."""
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME_LEN:
        return None
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return None
    if quantity < 1:
        return None
    return name, quantity


def add_item(name: str, quantity: int = 1) -> bool:
    """이름·수량으로 아이템을 추가한다. 유효하지 않으면 False."""
    cleaned = _clean(name, quantity)
    if cleaned is None:
        return False
    _items().append(new_item(*cleaned))
    save_items(_items())
    return True


def update_item(item_id: str, name: str, quantity: int) -> bool:
    """아이템의 이름·수량을 수정한다. 유효하지 않으면 False."""
    cleaned = _clean(name, quantity)
    if cleaned is None:
        return False
    for item in _items():
        if item["id"] == item_id:
            item["name"], item["quantity"] = cleaned
            save_items(_items())
            return True
    return False


def delete_item(item_id: str) -> None:
    """아이템 하나를 삭제한다."""
    st.session_state["items"] = [i for i in _items() if i["id"] != item_id]
    if st.session_state["editing_id"] == item_id:
        st.session_state["editing_id"] = None
    save_items(_items())


def toggle_item(item_id: str) -> None:
    """아이템의 구매 완료 상태를 토글한다."""
    for item in _items():
        if item["id"] == item_id:
            item["checked"] = not item["checked"]
            break
    save_items(_items())


def clear_checked() -> None:
    """체크된 아이템을 모두 삭제한다."""
    st.session_state["items"] = [i for i in _items() if not i["checked"]]
    if st.session_state["editing_id"] not in {i["id"] for i in _items()}:
        st.session_state["editing_id"] = None
    save_items(_items())


# ---------- 위젯 콜백 ----------

INVALID_MSG = f"이름을 입력해 주세요. (1~{MAX_NAME_LEN}자, 수량 1 이상)"


def on_add() -> None:
    if not add_item(st.session_state["new_name"], st.session_state["new_qty"]):
        st.session_state["flash"] = INVALID_MSG


def on_start_edit(item: dict) -> None:
    st.session_state["editing_id"] = item["id"]
    st.session_state[f"edit_name_{item['id']}"] = item["name"]
    st.session_state[f"edit_qty_{item['id']}"] = item["quantity"]


def on_save_edit(item_id: str) -> None:
    ok = update_item(
        item_id,
        st.session_state[f"edit_name_{item_id}"],
        st.session_state[f"edit_qty_{item_id}"],
    )
    if ok:
        st.session_state["editing_id"] = None
    else:
        st.session_state["flash"] = INVALID_MSG


def on_cancel_edit() -> None:
    st.session_state["editing_id"] = None


# ---------- 상태 초기화 ----------

st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒", layout="centered")

# session_state.items는 dict 메서드와 겹치므로 대괄호로 접근한다.
if "items" not in st.session_state:
    st.session_state["items"] = load_items()
if "editing_id" not in st.session_state:
    st.session_state["editing_id"] = None


# ---------- 화면 ----------

# 아이템 행은 좁은 화면에서도 줄바꿈하지 않고, 긴 이름만 여러 줄로 감싼다.
st.html(
    """<style>
    div[class*="st-key-row_"] { flex-wrap: nowrap; }
    div[class*="st-key-row_"] > * { min-width: 0; }
    </style>"""
)

items = _items()
done = sum(1 for item in items if item["checked"])

st.title("🛒 쇼핑 리스트")
st.progress(
    done / len(items) if items else 0.0,
    text=f"전체 {len(items)}개 · 완료 {done}개",
)

# F1. 추가 — 한 줄 입력 폼 (이름 넓게, 수량 좁게, 추가 버튼)
with st.form("add_form", clear_on_submit=True):
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.text_input(
            "이름",
            key="new_name",
            max_chars=MAX_NAME_LEN,
            placeholder="살 물건 (예: 우유)",
            label_visibility="collapsed",
        )
        st.number_input(
            "수량",
            key="new_qty",
            min_value=1,
            value=1,
            step=1,
            width=80,
            label_visibility="collapsed",
        )
        st.form_submit_button(
            "추가", on_click=on_add, type="primary", icon=":material/add:"
        )

if msg := st.session_state.pop("flash", None):
    st.warning(msg, icon=":material/warning:")

# F2~F4. 목록 — 아이템마다 카드 한 장
if not items:
    st.info(
        "목록이 비어 있습니다. 아이템을 추가해 보세요.",
        icon=":material/shopping_basket:",
    )
else:
    for item in items:
        item_id = item["id"]
        with st.container(
            border=True,
            horizontal=True,
            vertical_alignment="center",
            key=f"row_{item_id}",
        ):
            if st.session_state["editing_id"] == item_id:
                st.text_input(
                    "이름",
                    key=f"edit_name_{item_id}",
                    max_chars=MAX_NAME_LEN,
                    label_visibility="collapsed",
                )
                st.number_input(
                    "수량",
                    key=f"edit_qty_{item_id}",
                    min_value=1,
                    step=1,
                    width=80,
                    label_visibility="collapsed",
                )
                st.button(
                    ":material/check:",
                    key=f"save_{item_id}",
                    help="저장",
                    type="primary",
                    on_click=on_save_edit,
                    args=(item_id,),
                )
                st.button(
                    ":material/close:",
                    key=f"cancel_{item_id}",
                    help="취소",
                    on_click=on_cancel_edit,
                )
            else:
                name = item["name"]
                label = f":gray[~~{name}~~]" if item["checked"] else name
                st.checkbox(
                    label,
                    value=item["checked"],
                    key=f"check_{item_id}",
                    on_change=toggle_item,
                    args=(item_id,),
                    width="stretch",
                )
                # 배지와 버튼은 한 묶음으로 두어, 이름이 길어도 함께 움직이게 한다.
                with st.container(
                    horizontal=True,
                    width="content",
                    vertical_alignment="center",
                    gap="small",
                ):
                    st.badge(
                        f"x{item['quantity']}",
                        color="gray" if item["checked"] else "blue",
                    )
                    st.button(
                        ":material/edit:",
                        key=f"edit_{item_id}",
                        help="수정",
                        type="tertiary",
                        on_click=on_start_edit,
                        args=(item,),
                    )
                    st.button(
                        ":material/delete:",
                        key=f"del_{item_id}",
                        help="삭제",
                        type="tertiary",
                        on_click=delete_item,
                        args=(item_id,),
                    )

with st.container(horizontal_alignment="right"):
    st.button(
        "완료 항목 모두 삭제",
        key="clear_checked",
        icon=":material/delete_sweep:",
        on_click=clear_checked,
        disabled=done == 0,
    )
