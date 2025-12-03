import streamlit as st
from openai import OpenAI
import os
import json

# =========================
# 초기 설정
# =========================
st.set_page_config(page_title="대본 마스터", page_icon="📝", layout="centered")

# 로그인 환경변수
LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PW = os.getenv("LOGIN_PW")

# GPT 키 로드
api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

# 설정 파일 경로
CONFIG_PATH = "config.json"

# =========================
# 세션 상태 기본값
# =========================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("history", [])
st.session_state.setdefault(
    "instruction",
    "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다."
)
st.session_state.setdefault("current_input", "")
st.session_state.setdefault("last_output", "")
st.session_state.setdefault("model_choice", "gpt-4o-mini")


# =========================
# 설정 JSON 로드/저장 함수
# =========================
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 지침 불러오기
        if isinstance(data.get("instruction"), str):
            st.session_state.instruction = data["instruction"]

        # 최근 검색어 불러오기 (최대 5개)
        if isinstance(data.get("history"), list):
            st.session_state.history = data["history"][-5:]
    except FileNotFoundError:
        # 처음 실행이라 파일이 없을 수 있음
        pass
    except Exception as e:
        st.warning(f"설정 파일을 불러오는 중 오류가 발생했습니다: {e}")


def save_config():
    data = {
        "instruction": st.session_state.instruction,
        "history": st.session_state.history[-5:]
    }
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"설정 파일 저장 중 오류가 발생했습니다: {e}")


# 앱 최초 1회만 설정 로드
if "config_loaded" not in st.session_state:
    load_config()
    st.session_state.config_loaded = True


# =========================
# 로그인 화면
# =========================
def login_screen():
    st.title("🔒 로그인 Required")

    # 폼으로 묶어서 엔터키로 로그인 가능하게
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

# =========================
# 사이드바: 설정 영역 (좁게)
# =========================
with st.sidebar:
    st.markdown("### ⚙️ 설정")

    # GPT 모델 선택 (좁은 영역)
    model = st.selectbox(
        "GPT 모델",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state.model_choice)
    )
    st.session_state.model_choice = model

    # 지침 수정 패널 (사이드바에서 작게)
    with st.expander("지침 수정하기", expanded=False):
        new_inst = st.text_area(
            "GPT 지침",
            st.session_state.instruction,
            height=150
        )

        if st.button("지침 저장"):
            st.session_state.instruction = new_inst
            save_config()
            st.success("지침이 성공적으로 저장되었습니다!")


# =========================
# UI 미세 스타일 (주제 입력 강조)
# =========================
st.markdown(
    """
    <style>
    /* 중앙의 주제 입력 박스를 강조하기 위한 스타일 */
    .topic-box {
        padding: 20px 24px;
        border-radius: 14px;
        background-color: #f8fafc;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .topic-title {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .topic-desc {
        color: #6b7280;
        font-size: 0.9rem;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# 상단 로고 UI
# =========================
st.markdown("""
<div style='text-align:center; margin-top:10px;'>
    <div style='
        width:80px; height:80px;
        border-radius:50%;
        background:#eef2ff;
        display:flex; align-items:center; justify-content:center;
        font-size:34px; margin:auto;
        color:#111827; font-weight:bold;
        box-shadow: 0 3px 8px rgba(0,0,0,0.06);
    '>N</div>
    <h1 style='margin-top:20px; margin-bottom:4px;'>대본 마스터</h1>
    <p style='color:#6b7280; font-size:0.9rem;'>
        한 줄 주제만 입력하면 감성적인 다큐멘터리 내레이션을 생성합니다.
    </p>
</div>
""", unsafe_allow_html=True)


# =========================
# 대본 생성 함수
# =========================
def run_generation():
    topic = st.session_state.current_input.strip()
    if not topic:
        return

    # 최근 검색어 관리: 중복 제거 후 맨 뒤에 추가, 최대 5개
    hist = st.session_state.history
    if topic in hist:
        hist.remove(topic)
    hist.append(topic)
    st.session_state.history = hist[-5:]

    # 설정 저장 (지침 + 최근 검색어)
    save_config()

    # 프롬프트 제작
    prompt = f"""
{st.session_state.instruction}

다음 주제에 대해 500자 이상의 흥미롭고 몰입감 있는 내레이션을 작성해줘.
초반은 훅으로 강하게 시작하고 점차 이야기를 확장해줘.

주제: {topic}
"""

    with st.spinner("🎬 대본을 작성하는 중입니다..."):
        response = client.chat.completions.create(
            model=st.session_state.model_choice,
            messages=[
                {"role": "system", "content": st.session_state.instruction},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
        )

    st.session_state.last_output = response.choices[0].message.content


# =========================
# 메인: 주제 입력 영역 (강조)
# =========================
st.markdown("<div class='topic-box'>", unsafe_allow_html=True)

st.markdown(
    "<div class='topic-title'>📌 내레이션 주제</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div class='topic-desc'>한 문장 또는 짧은 키워드로 주제를 적어주세요. 이 영역이 앱의 중심입니다.</div>",
    unsafe_allow_html=True
)

st.text_input(
    label="주제 입력",
    key="current_input",
    placeholder="예: 축구의 경제학, 인공지능이 바꿀 우리의 일상",
    label_visibility="collapsed",
    on_change=run_generation
)

st.button("🎞️ 대본 생성하기", use_container_width=True, on_click=run_generation)

st.markdown("</div>", unsafe_allow_html=True)


# =========================
# 최근 검색어 (작게, 참고용 / 접힌 상태)
# =========================
with st.expander("🕒 최근 검색어 (최대 5개)", expanded=False):
    if len(st.session_state.history) == 0:
        st.info("최근 검색어가 없습니다.")
    else:
        recent_items = list(reversed(st.session_state.history[-5:]))
        st.caption("버튼을 누르면 해당 주제로 다시 대본을 생성합니다.")
        for idx, item in enumerate(recent_items):
            if st.button(item, key=f"recent_{idx}"):
                st.session_state.current_input = item
                run_generation()


# =========================
# 결과 출력
# =========================
if st.session_state.last_output:
    st.subheader("📄 생성된 내레이션")
    st.write(st.session_state.last_output)
