import streamlit as st
from openai import OpenAI
import os
import json
from json import JSONDecodeError

# 기본 설정
st.set_page_config(page_title="대본 마스터", page_icon="📝", layout="centered")

LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PW = os.getenv("LOGIN_PW")
api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

CONFIG_PATH = "config.json"

# 세션 기본값
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("history", [])
st.session_state.setdefault(
    "instruction",
    "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다."
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

    inst = data.get("instruction")
    if isinstance(inst, str) and inst.strip():
        st.session_state.instruction = inst

    hist = data.get("history")
    if isinstance(hist, list):
        st.session_state.history = hist[-5:]


def save_config():
    data = {
        "instruction": st.session_state.instruction,
        "history": st.session_state.history[-5:]
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
    st.title("🔒 로그인 Required")
    with st.form(key="login_form"):
        user = st.text_input("아이디", placeholder="ID 입력")
        pw = st.text_input("비밀번호", type="password", placeholder="비밀번호")
        submitted = st.form_submit_button("로그인")
        if submitted:
            if user == LOGIN_ID and pw == LOGIN_PW:
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")


if not st.session_state["logged_in"]:
    login_screen()
    st.stop()


# -------------------------
# 대본 생성 함수
# -------------------------
def run_generation():
    topic = st.session_state.current_input.strip()
    if not topic:
        return

    # 최근 검색어 관리 (중복 제거 + 최대 5개)
    hist = st.session_state.history
    if topic in hist:
        hist.remove(topic)
    hist.append(topic)
    st.session_state.history = hist[-5:]
    save_config()

    prompt = f"""
다음 주제에 대해 500자 이상의 흥미롭고 몰입감 있는 다큐멘터리 내레이션을 작성해줘.
초반은 훅으로 강하게 시작하고, 점차 이야기를 확장해줘.

주제: {topic}
"""

    with st.spinner("🎬 대본을 작성하는 중입니다..."):
        res = client.chat.completions.create(
            model=st.session_state.model_choice,
            messages=[
                {"role": "system", "content": st.session_state.instruction},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
        )
    st.session_state.last_output = res.choices[0].message.content


# -------------------------
# 공통 스타일 (폭/위치/입력창)
# -------------------------
st.markdown(
    """
    <style>
    .block-container {
        max-width: 620px;
        padding-top: 4rem;
    }
    .stTextInput > div > div > input {
        background-color: #eff6ff;
        border: 1px solid #60a5fa;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# -------------------------
# 사이드바: 설정 + 최근 검색어
# -------------------------
with st.sidebar:
    st.markdown("### ⚙️ 설정")

    model = st.selectbox(
        "GPT 모델",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state.model_choice),
    )
    st.session_state.model_choice = model

    with st.expander("지침 수정하기", expanded=False):
        st.caption(f"현재 적용된 지침:\n{st.session_state.instruction}")
        new_inst = st.text_area("새 지침", st.session_state.instruction, height=150)
        if st.button("지침 저장"):
            if new_inst.strip():
                st.session_state.instruction = new_inst.strip()
                save_config()
            st.success("지침이 저장되었습니다.")

    st.markdown("---")
    st.markdown("### 🕒 최근 검색어")
    if not st.session_state.history:
        st.caption("최근 검색어가 없습니다.")
    else:
        for i, item in enumerate(reversed(st.session_state.history[-5:])):
            if st.button(item, key=f"recent_{i}"):
                st.session_state.current_input = item
                run_generation()


# -------------------------
# 메인: 중앙에만 심플하게 배치
# -------------------------
# 상단 로고 / 타이틀
st.markdown("""
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
    <p style='color:#6b7280; font-size:0.9rem; margin-bottom:36px;'>
        한 줄 주제만 입력하면 감성적인 다큐멘터리 내레이션을 생성합니다.
    </p>
</div>
""", unsafe_allow_html=True)

# 주제 입력 + 버튼 (한 줄)
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
    )

with btn_col:
    st.button("대본 생성", use_container_width=True, on_click=run_generation)

# 결과
if st.session_state.last_output:
    st.subheader("📄 생성된 내레이션")
    st.write(st.session_state.last_output)
