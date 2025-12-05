import streamlit as st
from openai import OpenAI
import os
import json
from json import JSONDecodeError
from uuid import uuid4

st.set_page_config(page_title="대본 마스터", page_icon="📝", layout="centered")

LOGIN_ID_ENV = os.getenv("LOGIN_ID")
LOGIN_PW_ENV = os.getenv("LOGIN_PW")
api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

CONFIG_PATH = "config.json"

st.markdown(
    """
    <style>
    textarea {
        font-size: 0.8rem !important;
        line-height: 1.3 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------- 기본 세션값 ---------
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("history", [])
st.session_state.setdefault("login_id", LOGIN_ID_ENV or "")
st.session_state.setdefault("login_pw", LOGIN_PW_ENV or "")
st.session_state.setdefault("remember_login", False)

st.session_state.setdefault(
    "inst_role",
    "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다."
)
st.session_state.setdefault(
    "inst_tone",
    "톤은 진지하고 서정적이며, 첫 문장은 강렬한 훅으로 시작한다."
)
st.session_state.setdefault(
    "inst_structure",
    "인트로 → 배경 → 사건/전개 → 여운이 남는 결론 순서로 전개한다."
)
st.session_state.setdefault(
    "inst_depth",
    "사실 기반 정보를 충분히 포함하되, 사건의 핵심 원인과 결과를 반드시 드러낸다."
)
st.session_state.setdefault(
    "inst_forbidden",
    "선정적 표현, 과도한 비유, 독자에게 말을 거는 질문형 표현은 사용하지 않는다."
)
st.session_state.setdefault(
    "inst_format",
    "전체 분량은 500자 이상으로 하고, 소제목 없이 자연스러운 내레이션만 생성하며, 문단 사이에는 한 줄 공백을 둔다."
)
st.session_state.setdefault(
    "inst_user_intent",
    "사용자가 입력한 주제를 내러티브의 중심축으로 삼고, 배경 정보를 자연스럽게 녹여 스토리화한다."
)

st.session_state.setdefault("current_input", "")
st.session_state.setdefault("last_output", "")
st.session_state.setdefault("model_choice", "gpt-4o-mini")

# 지침 set 관련 세션값
st.session_state.setdefault("instruction_sets", [])
st.session_state.setdefault("active_instruction_set_id", None)
st.session_state.setdefault("show_add_instruction_set_editor", False)


def load_config():
    """config.json에서 설정값 로드"""
    if not os.path.exists(CONFIG_PATH):
        return
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except JSONDecodeError:
        return

    # 기존 지침 필드
    if isinstance(data.get("inst_role"), str):
        st.session_state.inst_role = data["inst_role"]
    elif isinstance(data.get("role_instruction"), str):
        st.session_state.inst_role = data["role_instruction"]

    for key in [
        "inst_tone",
        "inst_structure",
        "inst_depth",
        "inst_forbidden",
        "inst_format",
        "inst_user_intent",
    ]:
        if isinstance(data.get(key), str):
            setattr(st.session_state, key, data[key])

    # history
    hist = data.get("history")
    if isinstance(hist, list):
        st.session_state.history = hist[-5:]

    # 로그인 정보
    if isinstance(data.get("login_id"), str):
        st.session_state.login_id = data["login_id"]
    if isinstance(data.get("login_pw"), str):
        st.session_state.login_pw = data["login_pw"]
    if "remember_login" in data:
        st.session_state.remember_login = bool(data["remember_login"])

    # 지침 set 관련
    if isinstance(data.get("instruction_sets"), list):
        st.session_state.instruction_sets = data["instruction_sets"]
    if "active_instruction_set_id" in data:
        st.session_state.active_instruction_set_id = data["active_instruction_set_id"]


def save_config():
    """현재 세션값을 config.json으로 저장"""
    data = {
        "inst_role": st.session_state.inst_role,
        "inst_tone": st.session_state.inst_tone,
        "inst_structure": st.session_state.inst_structure,
        "inst_depth": st.session_state.inst_depth,
        "inst_forbidden": st.session_state.inst_forbidden,
        "inst_format": st.session_state.inst_format,
        "inst_user_intent": st.session_state.inst_user_intent,
        "history": st.session_state.history[-5:],
        "login_id": st.session_state.login_id,
        "login_pw": st.session_state.login_pw,
        "remember_login": st.session_state.remember_login,
        "instruction_sets": st.session_state.get("instruction_sets", []),
        "active_instruction_set_id": st.session_state.get("active_instruction_set_id"),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def reset_config():
    """config.json 및 세션 전체 초기화"""
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)

    for key in [
        "inst_role",
        "inst_tone",
        "inst_structure",
        "inst_depth",
        "inst_forbidden",
        "inst_format",
        "inst_user_intent",
        "history",
        "login_id",
        "login_pw",
        "remember_login",
        "current_input",
        "last_output",
        "model_choice",
        "instruction_sets",
        "active_instruction_set_id",
        "show_add_instruction_set_editor",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.session_state["logged_in"] = False
    if "config_loaded" in st.session_state:
        del st.session_state["config_loaded"]

    st.rerun()


def apply_instruction_set(set_obj: dict):
    """선택된 지침 set을 현재 지침(inst_*)에 적용"""
    for key in [
        "inst_role",
        "inst_tone",
        "inst_structure",
        "inst_depth",
        "inst_forbidden",
        "inst_format",
        "inst_user_intent",
    ]:
        if key in set_obj:
            setattr(st.session_state, key, set_obj.get(key, ""))
    save_config()


def sync_active_set_field(field_name: str, value: str):
    """현재 active 지침 set의 필드를 수정 내용으로 동기화"""
    active_id = st.session_state.get("active_instruction_set_id")
    sets = st.session_state.get("instruction_sets", [])
    if not active_id or not sets:
        return
    for s in sets:
        if s.get("id") == active_id:
            s[field_name] = value
            break
    st.session_state.instruction_sets = sets
    save_config()


def sync_inst_to_edit_widgets():
    """inst_* 값을 각 textarea 위젯 상태(st.session_state[..._edit])와 동기화"""
    mapping = [
        ("inst_role", "inst_role_edit"),
        ("inst_tone", "inst_tone_edit"),
        ("inst_structure", "inst_structure_edit"),
        ("inst_depth", "inst_depth_edit"),
        ("inst_forbidden", "inst_forbidden_edit"),
        ("inst_format", "inst_format_edit"),
        ("inst_user_intent", "inst_user_intent_edit"),
    ]
    for inst_key, widget_key in mapping:
        if inst_key in st.session_state:
            st.session_state[widget_key] = st.session_state[inst_key]


def ensure_active_set_applied():
    """매 렌더링마다 active set 내용이 inst_*에 반영되도록 보정"""
    sets = st.session_state.get("instruction_sets", [])
    active_id = st.session_state.get("active_instruction_set_id")
    if not sets or not active_id:
        return
    active_set = next((s for s in sets if s.get("id") == active_id), None)
    if active_set:
        for key in [
            "inst_role",
            "inst_tone",
            "inst_structure",
            "inst_depth",
            "inst_forbidden",
            "inst_format",
            "inst_user_intent",
        ]:
            if key in active_set:
                setattr(st.session_state, key, active_set.get(key, ""))


def login_screen():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 420px;
            padding-top: 4.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div style='text-align:center;'>
        <div style='
            width:100px; height:100px;
            border-radius:50%;
            background:#93c5fd;
            display:flex; align-items:center; justify-content:center;
            font-size:40px; margin:auto;
            color:#111827; font-weight:bold;
            box-shadow: 0 3px 8px rgba(0,0,0,0.08);
        '>N</div>
        <h1 style='margin-top:26px; margin-bottom:24px;'>대본 마스터</h1>
    </div>""",
        unsafe_allow_html=True,
    )

    default_id = st.session_state.login_id if st.session_state.remember_login else ""
    default_pw = st.session_state.login_pw if st.session_state.remember_login else ""

    with st.form(key="login_form"):
        user = st.text_input("아이디", placeholder="ID 입력", value=default_id)
        pw = st.text_input("비밀번호", type="password", placeholder="비밀번호", value=default_pw)
        remember = st.checkbox("로그인 정보 저장", value=st.session_state.remember_login)

        submitted = st.form_submit_button("로그인")
        if submitted:
            valid_id = st.session_state.login_id or LOGIN_ID_ENV or ""
            valid_pw = st.session_state.login_pw or LOGIN_PW_ENV or ""

            if user == valid_id and pw == valid_pw:
                st.session_state["logged_in"] = True
                st.session_state["remember_login"] = remember
                if remember:
                    st.session_state.login_id = user
                    st.session_state.login_pw = pw
                save_config()
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")


# --------- config 최초 로드 ---------
if "config_loaded" not in st.session_state:
    load_config()
    st.session_state.config_loaded = True

# 지침 set이 없다면 현재 지침으로 기본 set 생성
if not st.session_state.instruction_sets:
    default_set = {
        "id": "default",
        "name": "기본 지침",
        "inst_role": st.session_state.inst_role,
        "inst_tone": st.session_state.inst_tone,
        "inst_structure": st.session_state.inst_structure,
        "inst_depth": st.session_state.inst_depth,
        "inst_forbidden": st.session_state.inst_forbidden,
        "inst_format": st.session_state.inst_format,
        "inst_user_intent": st.session_state.inst_user_intent,
    }
    st.session_state.instruction_sets = [default_set]
    st.session_state.active_instruction_set_id = "default"
    save_config()
else:
    ensure_active_set_applied()

if not st.session_state["logged_in"]:
    login_screen()
    st.stop()

# 메인 영역 폭 넓게 조정 + div3 인풋 스타일
st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 4.5rem;
    }
    [data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    .sidebar-top {
        flex-grow: 1;
    }
    .sidebar-bottom {
        margin-top: auto;
        padding-top: 16px;
    }

    div[data-testid="stTextInput"] input[aria-label="주제 입력"] {
        background-color: #f9fafb !important;
        border: 2px solid #4f46e5 !important;
        border-radius: 999px !important;
        padding: 14px 20px !important;
        font-size: 0.95rem !important;
        box-shadow: 0 0 0 1px rgba(79, 70, 229, 0.18);
    }
    div[data-testid="stTextInput"] input[aria-label="주제 입력"]::placeholder {
        color: #9ca3af;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def run_generation():
    topic = st.session_state.current_input.strip()
    if not topic:
        return

    hist = st.session_state.history
    if topic in hist:
        hist.remove(topic)
    hist.append(topic)
    st.session_state.history = hist[-5:]
    save_config()

    system_parts = [
        st.session_state.inst_role,
        st.session_state.inst_tone,
        st.session_state.inst_structure,
        st.session_state.inst_depth,
        st.session_state.inst_forbidden,
        st.session_state.inst_format,
        st.session_state.inst_user_intent,
    ]
    system_text = "\n\n".join(
        part.strip() for part in system_parts if isinstance(part, str) and part.strip()
    )

    user_text = f"다음 주제에 맞는 다큐멘터리 내레이션을 작성해줘.\n\n주제: {topic}"

    with st.spinner("🎬 대본을 작성하는 중입니다..."):
        res = client.chat.completions.create(
            model=st.session_state.model_choice,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            max_tokens=600,
        )

    st.session_state.last_output = res.choices[0].message.content


# -------- 사이드바 --------
with st.sidebar:
    st.markdown("<div class='sidebar-top'>", unsafe_allow_html=True)

    # ===== 지침 set 섹션 =====
    st.markdown("### 🎛 지침 set")

    inst_sets = st.session_state.instruction_sets
    active_id = st.session_state.active_instruction_set_id

    if inst_sets:
        names = [s.get("name", f"셋 {i+1}") for i, s in enumerate(inst_sets)]

        # active id에 해당하는 index 찾기
        active_index = 0
        for i, s in enumerate(inst_sets):
            if s.get("id") == active_id:
                active_index = i
                break

        selected_index = st.radio(
            "지침 set 선택",
            options=list(range(len(inst_sets))),
            format_func=lambda i: names[i],
            index=active_index,
            label_visibility="collapsed",
        )

        # 선택 변경 시: 지침만 바꾸고 자동 생성은 안 함
        selected_set = inst_sets[selected_index]
        if selected_set.get("id") != active_id:
            st.session_state.active_instruction_set_id = selected_set.get("id")
            apply_instruction_set(selected_set)
            sync_inst_to_edit_widgets()
            st.rerun()

    # 새 지침 set 추가 버튼
    if st.button("➕ 지침 set 추가하기", use_container_width=True):
        st.session_state.show_add_instruction_set_editor = True

    st.markdown("### 📘 지침")

    # ===== 개별 지침 편집 (현재 active set 반영) =====
    with st.expander("1. 역할 지침 (Role Instructions)", expanded=False):
        st.caption("ChatGPT가 어떤 캐릭터 / 전문가 / 화자인지 정의합니다.")
        st.markdown(
            "- 예: `당신은 다큐멘터리 전문 내레이터이다.`\n"
            "- 예: `당신은 사건의 흐름을 촘촘히 짜주는 스토리텔링 편집자다.`\n"
            "- 예: `당신은 유튜브 쇼츠용 대본을 압축해주는 전문가다.`"
        )
        inst_role_edit = st.text_area(
            "역할 지침",
            st.session_state.inst_role,
            height=125,
            key="inst_role_edit",
        )
        if st.button("역할 지침 저장", key="save_role"):
            if inst_role_edit.strip():
                st.session_state.inst_role = inst_role_edit.strip()
                sync_active_set_field("inst_role", st.session_state.inst_role)
            st.success("역할 지침이 저장되었습니다.")

    with st.expander("2. 톤 & 스타일 지침", expanded=False):
        st.caption("어떤 분위기/문체/리듬으로 말할지 정의합니다.")
        st.markdown(
            "- 예: `톤은 진지하고 저널리즘 스타일을 유지한다.`\n"
            "- 예: `첫 문장은 100% 강렬한 훅으로 시작한다.`\n"
            "- 예: `문장은 짧고 간결하며 리듬감 있게 구성한다.`"
        )
        inst_tone_edit = st.text_area(
            "톤 & 스타일 지침",
            st.session_state.inst_tone,
            height=125,
            key="inst_tone_edit",
        )
        if st.button("톤 & 스타일 지침 저장", key="save_tone"):
            if inst_tone_edit.strip():
                st.session_state.inst_tone = inst_tone_edit.strip()
                sync_active_set_field("inst_tone", st.session_state.inst_tone)
            st.success("톤 & 스타일 지침이 저장되었습니다.")

    with st.expander("3. 콘텐츠 구성 지침", expanded=False):
        st.caption("초반–중반–후반 또는 장면 흐름을 어떻게 짤지 정의합니다.")
        st.markdown(
            "- 예: `인트로 → 배경 → 사건 → 인물 → 결론 단계로 전개하라.`\n"
            "- 예: `각 문단은 3~4문장으로 제한한다.`\n"
            "- 예: `스토리 전개는 시간순으로 배열한다.`"
        )
        inst_structure_edit = st.text_area(
            "콘텐츠 구성 지침",
            st.session_state.inst_structure,
            height=125,
            key="inst_structure_edit",
        )
        if st.button("콘텐츠 구성 지침 저장", key="save_structure"):
            if inst_structure_edit.strip():
                st.session_state.inst_structure = inst_structure_edit.strip()
                sync_active_set_field("inst_structure", st.session_state.inst_structure)
            st.success("콘텐츠 구성 지침이 저장되었습니다.")

    with st.expander("4. 정보 밀도 & 조사 심도 지침", expanded=False):
        st.caption("얼마나 깊게, 얼마나 촘촘하게 설명할지 정의합니다.")
        st.markdown(
            "- 예: `사실 기반의 정보 비율을 50% 이상 유지.`\n"
            "- 예: `불필요한 수식어는 최소화.`\n"
            "- 예: `사건의 핵심 원인·결과를 반드시 포함.`"
        )
        inst_depth_edit = st.text_area(
            "정보 밀도 & 조사 심도 지침",
            st.session_state.inst_depth,
            height=125,
            key="inst_depth_edit",
        )
        if st.button("정보 밀도 지침 저장", key="save_depth"):
            if inst_depth_edit.strip():
                st.session_state.inst_depth = inst_depth_edit.strip()
                sync_active_set_field("inst_depth", st.session_state.inst_depth)
            st.success("정보 밀도 지침이 저장되었습니다.")

    with st.expander("5. 금지 지침 (Forbidden Rules)", expanded=False):
        st.caption("절대 쓰지 말아야 할 표현/스타일/토픽을 정의합니다.")
        st.markdown(
            "- 예: `예시나 비유를 남발하지 마라.`\n"
            "- 예: `독자에게 질문 형태로 말 걸지 말라.`\n"
            "- 예: `선정적 표현은 제외.`"
        )
        inst_forbidden_edit = st.text_area(
            "금지 지침",
            st.session_state.inst_forbidden,
            height=125,
            key="inst_forbidden_edit",
        )
        if st.button("금지 지침 저장", key="save_forbidden"):
            if inst_forbidden_edit.strip():
                st.session_state.inst_forbidden = inst_forbidden_edit.strip()
                sync_active_set_field("inst_forbidden", st.session_state.inst_forbidden)
            st.success("금지 지침이 저장되었습니다.")

    with st.expander("6. 출력 형식 지침 (Output Format)", expanded=False):
        st.caption("길이, 단락, 제목, 마크다운 형식 등을 정의합니다.")
        st.markdown(
            "- 예: `전체 500자 이상.`\n"
            "- 예: `소제목 없이 자연스러운 내레이션만 생성.`\n"
            "- 예: `문단 간 공백 1줄 유지.`"
        )
        inst_format_edit = st.text_area(
            "출력 형식 지침",
            st.session_state.inst_format,
            height=125,
            key="inst_format_edit",
        )
        if st.button("출력 형식 지침 저장", key="save_format"):
            if inst_format_edit.strip():
                st.session_state.inst_format = inst_format_edit.strip()
                sync_active_set_field("inst_format", st.session_state.inst_format)
            st.success("출력 형식 지침이 저장되었습니다.")

    with st.expander("7. 사용자 요청 반영 지침", expanded=False):
        st.caption("사용자가 준 주제/키워드를 어떻게 스토리 안에 녹일지 정의합니다.")
        st.markdown(
            "- 예: `사용자가 입력한 키워드를 내러티브 중심축으로 사용한다.`\n"
            "- 예: `주제의 배경 정보를 먼저 파악한 뒤 스토리화한다.`"
        )
        inst_user_intent_edit = st.text_area(
            "사용자 요청 반영 지침",
            st.session_state.inst_user_intent,
            height=125,
            key="inst_user_intent_edit",
        )
        if st.button("사용자 요청 지침 저장", key="save_user_intent"):
            if inst_user_intent_edit.strip():
                st.session_state.inst_user_intent = inst_user_intent_edit.strip()
                sync_active_set_field("inst_user_intent", st.session_state.inst_user_intent)
            st.success("사용자 요청 반영 지침이 저장되었습니다.")

    st.markdown("</div><div class='sidebar-bottom'>", unsafe_allow_html=True)

    # ===== 설정 섹션 =====
    st.markdown("### ⚙️ 설정")

    with st.expander("GPT 모델 선택", expanded=False):
        model = st.selectbox(
            "",
            ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
            index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(
                st.session_state.model_choice
            ),
            label_visibility="collapsed",
        )
        st.session_state.model_choice = model

    with st.expander("👤 계정 관리", expanded=False):
        st.caption("비밀번호 변경 및 로그아웃")

        with st.form("change_password_form"):
            current_pw = st.text_input("현재 비밀번호", type="password")
            new_pw = st.text_input("새 비밀번호", type="password")
            new_pw2 = st.text_input("새 비밀번호 확인", type="password")
            pw_submitted = st.form_submit_button("비밀번호 변경")

            if pw_submitted:
                valid_pw = st.session_state.login_pw or LOGIN_PW_ENV or ""
                if current_pw != valid_pw:
                    st.error("현재 비밀번호가 올바르지 않습니다.")
                elif not new_pw:
                    st.error("새 비밀번호를 입력하세요.")
                elif new_pw != new_pw2:
                    st.error("새 비밀번호와 확인이 일치하지 않습니다.")
                else:
                    st.session_state.login_pw = new_pw
                    save_config()
                    st.success("비밀번호가 변경되었습니다.")

        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_input = ""
            st.session_state.last_output = ""
            st.rerun()

    # config 초기화
    with st.expander("🧹 설정 초기화 (config.json)", expanded=False):
        st.caption("모든 지침, 최근 입력, 로그인 정보, config.json 파일을 초기화합니다. 되돌릴 수 없습니다.")
        if st.button("config.json 초기화", use_container_width=True):
            reset_config()

    # config 내보내기 / 불러오기
    with st.expander("💾 config.json 내보내기 / 불러오기", expanded=False):
        st.caption("현재 설정을 파일로 저장하거나, 기존 config.json 파일을 불러올 수 있습니다.")

        export_data = {
            "inst_role": st.session_state.inst_role,
            "inst_tone": st.session_state.inst_tone,
            "inst_structure": st.session_state.inst_structure,
            "inst_depth": st.session_state.inst_depth,
            "inst_forbidden": st.session_state.inst_forbidden,
            "inst_format": st.session_state.inst_format,
            "inst_user_intent": st.session_state.inst_user_intent,
            "history": st.session_state.history[-5:],
            "login_id": st.session_state.login_id,
            "login_pw": st.session_state.login_pw,
            "remember_login": st.session_state.remember_login,
            "instruction_sets": st.session_state.get("instruction_sets", []),
            "active_instruction_set_id": st.session_state.get("active_instruction_set_id"),
        }
        export_json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ config.json 내보내기",
            data=export_json_str.encode("utf-8"),
            file_name="config.json",
            mime="application/json",
            use_container_width=True,
        )

        st.markdown("---")

        uploaded_file = st.file_uploader(
            "config.json 불러오기", type=["json"], help="이전 백업한 config.json 파일을 업로드하세요."
        )

        if uploaded_file is not None:
            try:
                raw = uploaded_file.read().decode("utf-8")
                new_data = json.loads(raw)
            except Exception:
                st.error("❌ JSON 파일을 읽는 중 오류가 발생했습니다. 올바른 config.json인지 확인해주세요.")
            else:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    f.write(raw)

                if "config_loaded" in st.session_state:
                    del st.session_state["config_loaded"]
                load_config()
                ensure_active_set_applied()
                sync_inst_to_edit_widgets()

                if not st.session_state.instruction_sets:
                    default_set = {
                        "id": "default",
                        "name": "기본 지침",
                        "inst_role": st.session_state.inst_role,
                        "inst_tone": st.session_state.inst_tone,
                        "inst_structure": st.session_state.inst_structure,
                        "inst_depth": st.session_state.inst_depth,
                        "inst_forbidden": st.session_state.inst_forbidden,
                        "inst_format": st.session_state.inst_format,
                        "inst_user_intent": st.session_state.inst_user_intent,
                    }
                    st.session_state.instruction_sets = [default_set]
                    st.session_state.active_instruction_set_id = "default"
                    save_config()

                st.success("✅ config.json이 성공적으로 불러와졌습니다. 설정이 적용됩니다.")
                st.rerun()

    # === 지침 set 삭제 ===
    with st.expander("🗑 지침 set 삭제", expanded=False):
        sets = st.session_state.instruction_sets
        if not sets:
            st.info("삭제할 지침 set이 없습니다.")
        else:
            names = [s.get("name", f"셋 {i+1}") for i, s in enumerate(sets)]
            del_index = st.selectbox(
                "삭제할 지침 set 선택",
                options=list(range(len(sets))),
                format_func=lambda i: names[i],
                label_visibility="collapsed",
                key="delete_instruction_set_select",
            )
            if st.button("선택한 지침 set 삭제", use_container_width=True):
                delete_id = sets[del_index].get("id")
                st.session_state.instruction_sets = [
                    s for s in sets if s.get("id") != delete_id
                ]
                if delete_id == st.session_state.active_instruction_set_id:
                    if st.session_state.instruction_sets:
                        st.session_state.active_instruction_set_id = (
                            st.session_state.instruction_sets[0].get("id")
                        )
                        ensure_active_set_applied()
                        sync_inst_to_edit_widgets()
                    else:
                        st.session_state.active_instruction_set_id = None
                save_config()
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# -------- 메인 영역 --------

# 지침 set 추가 에디터
if st.session_state.get("show_add_instruction_set_editor", False):
    st.markdown("## ✨ 새 지침 set 추가")

    with st.form("add_instruction_set_form"):
        set_name = st.text_input("지침 set 이름", placeholder="예: 다큐 기본셋 / 연애의 경제학 셋 등")

        role_txt = st.text_area("1. 역할 지침", "", height=80)
        tone_txt = st.text_area("2. 톤 & 스타일 지침", "", height=80)
        struct_txt = st.text_area("3. 콘텐츠 구성 지침", "", height=80)
        depth_txt = st.text_area("4. 정보 밀도 & 조사 심도 지침", "", height=80)
        forbid_txt = st.text_area("5. 금지 지침", "", height=80)
        format_txt = st.text_area("6. 출력 형식 지침", "", height=80)
        intent_txt = st.text_area("7. 사용자 요청 반영 지침", "", height=80)

        col_a, col_b = st.columns(2)
        with col_a:
            submitted = st.form_submit_button("💾 지침 set 저장")
        with col_b:
            cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state.show_add_instruction_set_editor = False
            st.rerun()

        if submitted:
            if not set_name.strip():
                st.error("지침 set 이름을 입력해주세요.")
            else:
                new_id = str(uuid4())
                new_set = {
                    "id": new_id,
                    "name": set_name.strip(),
                    "inst_role": role_txt.strip(),
                    "inst_tone": tone_txt.strip(),
                    "inst_structure": struct_txt.strip(),
                    "inst_depth": depth_txt.strip(),
                    "inst_forbidden": forbid_txt.strip(),
                    "inst_format": format_txt.strip(),
                    "inst_user_intent": intent_txt.strip(),
                }
                st.session_state.instruction_sets.append(new_set)
                st.session_state.active_instruction_set_id = new_id

                ensure_active_set_applied()
                sync_inst_to_edit_widgets()

                st.session_state.show_add_instruction_set_editor = False
                save_config()
                st.success("✅ 새 지침 set이 저장되었습니다.")
                st.rerun()

# -------- div1: 상단 로고 + 타이틀 --------
st.markdown(
    """<div style='text-align:center;'>
    <div style='
        width:100px; height:100px;
        border-radius:50%;
        background:#93c5fd;
        display:flex; align-items:center; justify-content:center;
        font-size:40px; margin:auto;
        color:#111827; font-weight:bold;
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
    '>N</div>
    <h1 style='margin-top:26px; margin-bottom:6px;'>대본 마스터</h1>
</div>""",
    unsafe_allow_html=True,
)

# -------- div2: 최근 검색어 --------
if st.session_state.history:
    items = st.session_state.history[-5:]
    html_items = ""
    for h in items:
        html_items += f"""
<div style="
    font-size:0.85rem;
    color:#797979;
    margin-bottom:4px;
">{h}</div>
"""
    st.markdown(
        f"""<div style="
    max-width:460px;
    margin:64px auto 72px auto;
">
  <div style="margin-left:100px; text-align:left;">
    <div style="font-size:0.8rem; color:#9ca3af; margin-bottom:10px;">
      최근
    </div>
    {html_items}
  </div>
</div>""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """<div style="
    max-width:460px;
    margin:64px auto 72px auto;
">
  <div style="margin-left:100px; font-size:0.8rem; color:#d1d5db; text-align:left;">
    최근 입력이 없습니다.
  </div>
</div>""",
        unsafe_allow_html=True,
    )

# -------- div3: 입력 영역 --------
pad_left, center_col, pad_right = st.columns([1, 7, 1])

with center_col:
    st.markdown(
        "<div style='color:#BDC6D2; font-size:0.9rem; margin-bottom:10px; text-align:center;'>한 문장 또는 짧은 키워드로 주제를 적어주세요.</div>",
        unsafe_allow_html=True,
    )

    st.text_input(
        label="주제 입력",
        key="current_input",
        placeholder="gpt에게 물어보기",
        label_visibility="collapsed",
        on_change=run_generation,
    )

st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)

# -------- 결과 --------
if st.session_state.last_output:
    st.subheader("📄 생성된 내레이션")
    st.write(st.session_state.last_output)
