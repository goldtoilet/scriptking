import streamlit as st
from openai import OpenAI
import os
import json
from json import JSONDecodeError

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
def write_default_config():
    """현재 세션 상태 기준으로 기본 config를 파일에 저장"""
    data = {
        "instruction": st.session_state.instruction,
        "history": st.session_state.history[-5:]
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config():
    # 파일이 없으면 아무 것도 안 함 (기본값 사용)
    if not os.path.exists(CONFIG_PATH):
        return

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if not raw:
                # 빈 파일이면 기본값으로 다시 저장
                write_default_config()
                return
            data = json.loads(raw)

        # 지침 불러오기
        inst = data.get("instruction")
        if isinstance(inst, str) and inst.strip():
            st.session_state.instruction = inst

        # 최근 검색어 불러오기 (최대 5개)
        hist = data.get("history")
        if isinstance(hist, list):
            st.session_state.history = hist[-5:]

    except JSONDecodeError:
        # JSON이 깨져 있으면 기본값으로 초기화
        write_default_config()
        st.info("설정 파일이 손상되어 기본값으로 다시 초기화했습니다.")
    except Exception:
        # 다른 에러는 조용히 넘어가고 기본값 사용
        st.info("설정 파일을 불러오지 못해 기본값으로 시작합니다.")


def save_config():
    """현재 세션 상태를 config.json에 저장"""
    try:
        write_default_config()
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
# 사이드바: 설정 + 최근 검색어
# =========================
with st.sidebar:
    st.markdown("### ⚙️ 설정")

    # GPT 모델 선택
    model = st.selectbox(
        "GPT 모델",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state.model_choice)
    )
    st.session_state.model_choice = model

    # 지침 수정 패널
    with st.expander("지침 수정하기", expanded=False):
        # 현재 적용 중인 지침을 흐린 글씨로 미리 보여주기
        st.caption(f"현재 적용된 지침:\n{st.session_state.instruction}")

        new_inst = st.text_area(
            "새 지침 입력 (비워두면 기존 지침 유지)",
            st.session_state.instruction,
            height=150
        )

        if st.button("지침 저장"):
            # 공백만 있는 경우는 기존 유지
            if new_inst.strip():
                st.session_state.instruction = new_inst.strip()
            save_config()
            st.success("지침이 성공적으로 저장되었습니다!")

    st.markdown("---")

    # 최근 검색어 (사이드바로 이동)
    st.markdown("### 🕒 최근 검색어")
    if len(st.session_state.history) == 0:
        st.caption("최근 검색어가 없습니다.")
    else:
        st.caption("버튼을 누르면 해당 주제로 다시 대본을 생성합니다.")
        recent_items = list(reversed(st.session_state.history[-5:]))
        for idx, item in enumerate(recent_items):
            if st.button(item, key=f"recent_sidebar_{idx}"):
                st.session_state.current_input = item
                # 바로 생성
                # run_generation()은 아래에 정의되어 있으므로
                # 클릭 시 동작은 메인 영역에서 처리되도록 플래그만 넘길 수도 있음
                # 여기서는 간단히 세션 값만 변경하고, 메인에서 버튼/엔터로 실행하도록 둔다.
                # 필요하면 st.session_state 플래그를 추가해 바로 실행되게 바꿀 수도 있음.
                pass


# =========================
# UI 스타일 (전체 너비 & 입력창 하이라이트)
# =========================
st.markdown(
    """
    <style>
    /* 전체 페이지 폭 조금 좁게 */
    .block-container {
        max-width: 780px;
        padding-top: 1.5rem;
    }

    /* 주제 입력 박스 */
    .topic-box {
        padding: 18px 20px;
        border-radius: 14px;
        background-color: #eff6ff; /* 옅은 파란색 */
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.10);
        margin-top: 30px;
        margin-bottom: 10px;
    }

    /* 텍스트 입력 전반 스타일 (로그인 화면에도 적용될 수 있음) */
    .stTextInput > div > div > input {
        background-color: #eff6ff;
        border: 1px solid #60a5fa;
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
    <h1 style='margin-top:22px; margin-bottom:8px;'>대본 마스터</h1>
    <p style='color:#6b7280; font-size:0.9rem; margin-bottom:26px;'>
        한 줄 주제만 입력하면 감성적인 다큐멘터리 내레이션을 생성합니다.
    </p>
</div>
""", unsafe_allow_html=True)


# =========================
# 대본 생성 함수 (지침은 system에만)
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

    # user 프롬프트 (지침은 포함하지 않음)
    prompt = f"""
다음 주제에 대해 500자 이상의 흥미롭고 몰입감 있는 다큐멘터리 내레이션을 작성해줘.
초반은 훅으로 강하게 시작하고, 점차 이야기를 확장해줘.

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
# 메인: 주제 입력 영역 (강조, 버튼 오른쪽)
# =========================
st.markdown("<div class='topic-box'>", unsafe_allow_html=True)

# 설명 텍스트 (레이블/“이 영역이 앱의 중심입니다” 제거됨)
st.markdown(
    "<div style='color:#1f2933; font-weight:600; margin-bottom:4px;'>📌 내레이션 주제 입력</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='color:#4b5563; font-size:0.9rem; margin-bottom:10px;'>한 문장 또는 짧은 키워드로 주제를 적어주세요.</div>",
    unsafe_allow_html=True
)

# 입력창(좌) + 버튼(우) 2열 구성
col_input, col_btn = st.columns([4, 1])

with col_input:
    st.text_input(
        label="주제 입력",
        key="current_input",
        placeholder="예: 축구의 경제학, 인공지능이 바꿀 우리의 일상",
        label_visibility="collapsed",
        on_change=run_generation
    )

with col_btn:
    st.button("🎞️ 대본 생성", use_container_width=True, on_click=run_generation)

st.markdown("</div>", unsafe_allow_html=True)


# =========================
# 결과 출력
# =========================
if st.session_state.last_output:
    st.subheader("📄 생성된 내레이션")
    st.write(st.session_state.last_output)
