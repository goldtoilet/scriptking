import streamlit as st
from openai import OpenAI
import os
import json
from json import JSONDecodeError

# -------------------------
# 기본 설정
# -------------------------
st.set_page_config(page_title="대본 마스터", page_icon="📝", layout="centered")

LOGIN_ID_ENV = os.getenv("LOGIN_ID")
LOGIN_PW_ENV = os.getenv("LOGIN_PW")
api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

CONFIG_PATH = "config.json"

# -------------------------
# 세션 기본값
# -------------------------
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("history", [])

# 🔹 로그인 정보 (기본값은 환경변수, 없으면 빈 문자열)
st.session_state.setdefault("login_id", LOGIN_ID_ENV or "")
st.session_state.setdefault("login_pw", LOGIN_PW_ENV or "")
st.session_state.setdefault("remember_login", False)

# 역할 지침 (system)
st.session_state.setdefault(
    "role_instruction",
    "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다."
)

# 작업 지침 (user 프롬프트 템플릿의 공통 부분)
st.session_state.setdefault(
    "task_instruction",
    "다음 주제에 대해 500자 이상의 흥미롭고 몰입감 있는 다큐멘터리 내레이션을 작성해줘.\n"
    "초반은 훅으로 강하게 시작하고, 점차 이야기를 확장해줘."
)

st.session_state.setdefault("current_input", "")
st.session_state.setdefault("last_output", "")
st.session_state.setdefault("model_choice", "gpt-4o-mini")


# -------------------------
# 설정 JSON 로드/저장
# -------------------------
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except JSONDecodeError:
        return

    # 이전 버전 호환: instruction → role_instruction
    if isinstance(data.get("role_instruction"), str):
        st.session_state.role_instruction = data["role_instruction"]
    elif isinstance(data.get("instruction"), str):
        st.session_state.role_instruction = data["instruction"]

    if isinstance(data.get("task_instruction"), str):
        st.session_state.task_instruction = data["task_instruction"]

    hist = data.get("history")
    if isinstance(hist, list):
        st.session_state.history = hist[-5:]

    # 🔹 로그인 관련 정보 로드 (있으면 덮어씀)
    if isinstance(data.get("login_id"), str):
        st.session_state.login_id = data["login_id"]
    if isinstance(data.get("login_pw"), str):
        st.session_state.login_pw = data["login_pw"]
    if "remember_login" in data:
        st.session_state.remember_login = bool(data["remember_login"])


def save_config():
    data = {
        "role_instruction": st.session_state.role_instruction,
        "task_instruction": st.session_state.task_instruction,
        "history": st.session_state.history[-5:],
        "login_id": st.session_state.login_id,
        "login_pw": st.session_state.login_pw,
        "remember_login": st.session_state.remember_login,
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if "config_loaded" not in st.session_state:
    load_config()
    st.session_state.config_loaded = True


# -------------------------
# 로그인 화면
# -------------------------
def login_screen():
    # 로그인 전용 스타일: 폭 좁게 + 세로 중앙 근처
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 420px;
            padding-top: 18vh;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🔒 로그인 Required")

    # remember_login 이 True면 값을 미리 채워두되, 비밀번호는 ●●● 로 표시됨
    default_id = st.session_state.login_id if st.session_state.remember_login else ""
    default_pw = st.session_state.login_pw if st.session_state.remember_login else ""

    with st.form(key="login_form"):
        user = st.text_input("아이디", placeholder="ID 입력", value=default_id)
        pw = st.text_input("비밀번호", type="password", placeholder="비밀번호", value=default_pw)
        remember = st.checkbox("로그인 정보 저장", value=st.session_state.remember_login)

        submitted = st.form_submit_button("로그인")
        if submitted:
            # 현재 저장된 로그인 정보와 비교
            valid_id = st.session_state.login_id or LOGIN_ID_ENV or ""
            valid_pw = st.session_state.login_pw or LOGIN_PW_ENV or ""

            if user == valid_id and pw == valid_pw:
                # 로그인 성공
                st.session_state["logged_in"] = True
                st.session_state["remember_login"] = remember

                # 로그인 정보 저장 옵션이 켜져 있으면 ID/PW를 저장
                if remember:
                    st.session_state.login_id = user
                    st.session_state.login_pw = pw
                save_config()

                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")


if not st.session_state["logged_in"]:
    login_screen()
    st.stop()


# -------------------------
# 메인 화면 공통 스타일
# -------------------------
st.markdown(
    """
    <style>
    .block-container {
        max-width: 620px;
        padding-top: 4.5rem;
    }
    /* 검색 입력창만 파란 느낌 주기 위해 class 대신 전체 input 스타일 사용 (간단 버전) */
    .search-input > div > div > input {
        background-color: #eff6ff;
        border: 1px solid #60a5fa;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# 대본 생성 함수
# -------------------------
def run_generation():
    topic = st.session_state.current_input.strip()
    if not topic:
        return

    # 최근 검색어 관리
    hist = st.session_state.history
    if topic in hist:
        hist.remove(topic)
    hist.append(topic)
    st.session_state.history = hist[-5:]
    save_config()

    # 작업 지침 + 주제
    task = st.session_state.task_instruction.strip()
    prompt = f"{task}\n\n주제: {topic}"

    with st.spinner("🎬 대본을 작성하는 중입니다..."):
        res = client.chat.completions.create(
            model=st.session_state.model_choice,
            messages=[
                {"role": "system", "content": st.session_state.role_instruction},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )

    st.session_state.last_output = res.choices[0].message.content


# -------------------------
# 사이드바: 모델 + 역할/작업 지침 + 최근 검색어 + 계정 관리
# -------------------------
with st.sidebar:
    st.markdown("### ⚙️ 설정")

    model = st.selectbox(
        "GPT 모델",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state.model_choice),
    )
    st.session_state.model_choice = model

    # 역할 지침
    with st.expander("역할 지침 수정하기", expanded=False):
        st.caption("현재 역할 지침을 아래에서 바로 수정할 수 있습니다.")
        role_edit = st.text_area(
            "역할 지침",
            st.session_state.role_instruction,
            height=120,
            key="role_edit",
        )
        if st.button("역할 지침 저장"):
            if role_edit.strip():
                st.session_state.role_instruction = role_edit.strip()
                save_config()
            st.success("역할 지침이 저장되었습니다.")

    # 작업 지침
    with st.expander("작업 지침 수정하기", expanded=False):
        st.caption("현재 작업 지침(매번 프롬프트에 공통으로 들어가는 문장입니다):")
        task_edit = st.text_area(
            "작업 지침",
            st.session_state.task_instruction,
            height=140,
            key="task_edit",
        )
        if st.button("작업 지침 저장"):
            if task_edit.strip():
                st.session_state.task_instruction = task_edit.strip()
                save_config()
            st.success("작업 지침이 저장되었습니다.")

    st.markdown("---")

    # 최근 검색어
    st.markdown("### 🕒 최근 검색어")
    if not st.session_state.history:
        st.caption("최근 검색어가 없습니다.")
    else:
        for i, item in enumerate(reversed(st.session_state.history[-5:])):
            if st.button(item, key=f"recent_{i}"):
                st.session_state.current_input = item
                run_generation()

    st.markdown("---")

    # 🔹 계정 관리 (비밀번호 변경 + 로그아웃) - 공간 최소화, expander로 감싸기
    with st.expander("👤 계정 관리", expanded=False):
        st.caption("비밀번호 변경 및 로그아웃")

        # 비밀번호 변경 폼 (작게)
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

        # 작은 로그아웃 버튼
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_input = ""
            st.session_state.last_output = ""
            st.rerun()


# -------------------------
# 메인 화면 상단 로고/타이틀
# -------------------------
st.markdown(
    """
<div style='text-align:center;'>
    <div style='
        width:80px; height:80px;
        border-radius:50%;
        background:#bfdbfe;
        display:flex; align-items:center; justify-content:center;
        font-size:34px; margin:auto;
        color:#111827; font-weight:bold;
        box-shadow: 0 3px 8px rgba(0,0,0,0.06);
    '>N</div>
    <h1 style='margin-top:20px; margin-bottom:6px;'>대본 마스터</h1>
    <p style='color:#6b7280; font-size:0.9rem; margin-bottom:40px;'>
        한 줄 주제만 입력하면 감성적인 다큐멘터리 내레이션을 생성합니다.
    </p>
</div>
<div style='height:40px;'></div>
""",
    unsafe_allow_html=True,
)

# -------------------------
# 주제 입력 + 버튼 (조금 더 아래쪽, 가운데)
# -------------------------
st.markdown(
    "<div style='color:#4b5563; font-size:0.9rem; margin-bottom:6px;'>한 문장 또는 짧은 키워드로 주제를 적어주세요.</div>",
    unsafe_allow_html=True,
)

input_col, btn_col = st.columns([4, 1])

with input_col:
    st.text_input(
        label="주제 입력",
        key="current_input",
        placeholder="예: 축구의 경제학, 인공지능이 바꿀 우리의 일상",
        label_visibility="collapsed",
        on_change=run_generation,
        help="한 줄로 간단히 적어주세요.",
    )

with btn_col:
    st.button("대본 생성", use_container_width=True, on_click=run_generation)

# 아래쪽 여유
st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

# -------------------------
# 결과 출력
# -------------------------
if st.session_state.last_output:
    st.subheader("📄 생성된 내레이션")
    st.write(st.session_state.last_output)
