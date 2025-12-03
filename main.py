import streamlit as st
from openai import OpenAI
import os

# =========================
# 초기 설정
# =========================
st.set_page_config(page_title="대본 마스터", page_icon="📝", layout="centered")

# 로그인 환경변수
LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PW = os.getenv("LOGIN_PW")

st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("history", [])
st.session_state.setdefault("current_input", "")
st.session_state.setdefault("last_output", "")
st.session_state.setdefault("instruction", "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다.")

# GPT 키 로드
api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

# =========================
# 로그인 화면
# =========================
def login_screen():
    st.title("🔒 로그인 Required")

    user = st.text_input("아이디", placeholder="ID 입력")
    pw = st.text_input("비밀번호", type="password", placeholder="비밀번호")

    if st.button("로그인"):
        if user == LOGIN_ID and pw == LOGIN_PW:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")

if not st.session_state["logged_in"]:
    login_screen()
    st.stop()

# =========================
# 상단 로고 UI
# =========================
st.markdown("""
<div style='text-align:center; margin-top:20px;'>
    <div style='
        width:85px; height:85px;
        border-radius:50%;
        background:#eef4ff;
        display:flex; align-items:center; justify-content:center;
        font-size:35px; margin:auto;
        color:#1f2d3d; font-weight:bold;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    '>N</div>
    <h1 style='margin-top:25px; margin-bottom:10px;'>대본 마스터</h1>
    <p style='color:gray;'>주제만 입력하면 감성적인 다큐멘터리 내레이션을 자동으로 생성합니다.</p>
</div>
""", unsafe_allow_html=True)

# =========================
# GPT 모델 선택
# =========================
model = st.selectbox(
    "사용할 GPT 모델 선택",
    ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
    index=0
)
st.session_state.model_choice = model

# =========================
# 지침 수정 패널
# =========================
with st.expander("⚙️ 지침 수정하기", expanded=False):
    new_inst = st.text_area(
        "GPT에게 적용할 지침",
        st.session_state.instruction,
        height=150
    )

    if st.button("지침 저장"):
        st.session_state.instruction = new_inst
        st.success("지침이 성공적으로 저장되었습니다!")

# =========================
# 대본 생성 함수
# =========================
def run_generation():
    topic = st.session_state.current_input.strip()
    if not topic:
        return

    # 최근 검색어 저장
    if topic not in st.session_state.history:
        st.session_state.history.append(topic)

    # 프롬프트 제작
    prompt = f"""
{st.session_state.instruction}

다음 주제에 대해 500자 이상의 흥미롭고 몰입감 있는 내레이션을 작성해줘.
초반은 훅으로 강하게 시작하고 점차 이야기를 확장해줘.

주제: {topic}
"""

    with st.spinner("🎬 대본을 작성하는 중..."):
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
# 최근 검색어 UI
# =========================
st.subheader("🕒 최근 검색어")

if len(st.session_state.history) == 0:
    st.info("최근 검색어가 없습니다.")
else:
    cols = st.columns(5)
    recent_items = list(reversed(st.session_state.history[-5:]))

    for idx, item in enumerate(recent_items):
        if cols[idx].button(item, key=f"recent_{idx}"):
            st.session_state.current_input = item
            run_generation()

# =========================
# 검색 입력창
# =========================
st.text_input(
    "📌 주제를 입력하세요",
    key="current_input",
    placeholder="예: 축구의 경제학",
    on_change=run_generation
)

# 버튼 실행
st.button("🎞️ 대본 생성하기", use_container_width=True, on_click=run_generation)

# =========================
# 결과 출력
# =========================
if st.session_state.last_output:
    st.subheader("📄 생성된 내레이션")
    st.write(st.session_state.last_output)
