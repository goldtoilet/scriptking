import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import streamlit as st
import os

# ====== LOGIN SYSTEM ======
LOGIN_ID = os.getenv("LOGIN_ID")
LOGIN_PW = os.getenv("LOGIN_PW")

st.session_state.setdefault("logged_in", False)

def login_screen():
    st.title("🔒 로그인 Required")

    user = st.text_input("아이디", placeholder="ID를 입력하세요")
    pw = st.text_input("비밀번호", type="password", placeholder="비밀번호")

    if st.button("로그인"):
        if user == LOGIN_ID and pw == LOGIN_PW:
            st.session_state["logged_in"] = True
            st.experimental_rerun()
        else:
            st.error("❌ 아이디 또는 비밀번호가 틀렸습니다.")

if not st.session_state["logged_in"]:
    login_screen()
    st.stop()

# ===== 로그인 성공 이후 실제 앱 시작 =====
st.write("🎉 로그인 성공! 앱을 사용할 수 있습니다.")



# Load API Key
load_dotenv()
api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="대본 마스터", page_icon="📝", layout="centered")

# 초기 상태
if "history" not in st.session_state:
    st.session_state.history = []

if "current_input" not in st.session_state:
    st.session_state.current_input = ""

# ─────────────────────────────────────────────
# 엔터 키 입력 시 실행되는 함수
# ─────────────────────────────────────────────
def run_generation():
    user_input = st.session_state.current_input.strip()
    if not user_input:
        return
    
    st.session_state.history.append(user_input)

    prompt = f"""
너는 전문 다큐멘터리 기자야.
다음 주제에 대해 500자 정도의 흥미롭고 몰입감 있는 다큐멘터리 내레이션을 작성해줘.
초반에는 훅으로 시선을 강하게 끌고 점차 이야기를 확장해줘.

주제: {user_input}
"""

    with st.spinner("GPT가 대본을 작성하는 중..."):
        response = client.chat.completions.create(
            model=st.session_state.model_choice,
            messages=[
                {"role": "system", "content": "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
        )
    
    st.session_state.last_output = response.choices[0].message.content


# ─────────────────────────────────────────────
# 상단 디자인
# ─────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; margin-top:20px;'>
    <div style='
        width:80px; height:80px;
        border-radius:50%;
        background:#dbe8ff;
        display:flex; align-items:center; justify-content:center;
        font-size:34px; margin:auto;
        color:#2c3e50; font-weight:bold;
    '>N</div>
    <h1 style='margin-top:25px; margin-bottom:10px;'>대본 마스터</h1>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GPT 모델 선택
# ─────────────────────────────────────────────
model = st.selectbox(
    "사용할 GPT 모델 선택",
    ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
    index=0
)
st.session_state.model_choice = model

# ─────────────────────────────────────────────
# 최근 검색어
# ─────────────────────────────────────────────
st.subheader("최근 검색어")

if len(st.session_state.history) == 0:
    st.write("최근 검색어 없음")
else:
    for item in reversed(st.session_state.history[-5:]):
        if st.button(item, key=f"history_{item}"):
            st.session_state.current_input = item
            run_generation()

# ─────────────────────────────────────────────
# 검색창 (엔터 자동 실행)
# ─────────────────────────────────────────────
st.text_input(
    "gpt에게 물어보기",
    key="current_input",
    placeholder="예: 축구의 경제학",
    on_change=run_generation  # 엔터 치면 자동 실행
)

# 버튼으로 실행하기
if st.button("생성하기", use_container_width=True):
    run_generation()

# ─────────────────────────────────────────────
# 생성 결과 출력
# ─────────────────────────────────────────────
if "last_output" in st.session_state:
    st.subheader("결과")
    st.write(st.session_state.last_output)
