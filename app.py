"""
DogAICreator - 강아지 AI 영상 생성기 (v3.1 - 모바일 최적화)
"""
import streamlit as st
import io
from datetime import datetime
from PIL import Image
from services.gemini import get_gemini_service, GeminiService
from services.kling import get_kling_service, KlingService

# 페이지 설정 (centered로 모바일 친화적)
st.set_page_config(page_title="DogAICreator", page_icon="🐕", layout="centered")

# ─── 모바일 최적화 CSS ───
st.markdown("""
<style>
    /* 전체 패딩 축소 (모바일 공간 확보) */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 720px !important;
    }

    /* 그라데이션 헤더 */
    .main-header {
        text-align: center;
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 50%, #FFC857 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
        padding: 0;
    }
    .sub-header {
        text-align: center;
        color: #888;
        font-size: 0.95rem;
        margin-top: 0;
        margin-bottom: 1rem;
    }

    /* 버튼 - 터치 친화적 크기 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        min-height: 3em;
        font-weight: bold;
        font-size: 1rem;
    }

    /* 생성 버튼 강조 */
    .stButton>button[kind="primary"] {
        min-height: 3.5em;
        font-size: 1.1rem;
    }

    /* 결과 영역 */
    .result-box {
        border: 2px solid #FF8E53;
        padding: 16px;
        border-radius: 16px;
        background: linear-gradient(135deg, #FFF5F5 0%, #FFF8F0 100%);
        margin-top: 8px;
    }

    /* 업로드 영역 */
    .stFileUploader>div {
        border-radius: 12px;
    }

    /* 영상 플레이어 전체 너비 */
    video {
        width: 100% !important;
        border-radius: 12px;
    }

    /* 업로드 이미지 라운드 처리 */
    .stImage img {
        border-radius: 12px;
    }

    /* 예시 버튼 작게 */
    .example-btn button {
        font-size: 0.85rem !important;
        min-height: 2.4em !important;
        padding: 4px 8px !important;
    }

    /* 섹션 구분선 */
    .section-divider {
        border: none;
        border-top: 1px solid #eee;
        margin: 1rem 0;
    }

    /* 사이드바 */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }

    /* 모바일 반응형 */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .main-header {
            font-size: 1.6rem;
        }
        .sub-header {
            font-size: 0.85rem;
        }
        .result-box {
            padding: 12px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ─── 세션 상태 초기화 ───
# 서비스 인스턴스가 없거나 이전 버전이면 새로 생성
if 'gemini_service' not in st.session_state or not hasattr(st.session_state.gemini_service, 'MODELS'):
    try:
        st.session_state.gemini_service = get_gemini_service()
    except Exception as e:
        st.error(f"Gemini 서비스 연결 실패: {e}")

if 'kling_service' not in st.session_state or not hasattr(st.session_state.kling_service, 'MODELS'):
    try:
        st.session_state.kling_service = get_kling_service()
    except Exception as e:
        st.error(f"Kling AI 서비스 연결 실패: {e}")

if 'image_bytes' not in st.session_state:
    st.session_state.image_bytes = None
if 'video_data' not in st.session_state:
    st.session_state.video_data = None
if 'video_prompt' not in st.session_state:
    st.session_state.video_prompt = None
if 'history' not in st.session_state:
    st.session_state.history = []
if 'selected_example' not in st.session_state:
    st.session_state.selected_example = ""
if 'selected_mode' not in st.session_state:
    st.session_state.selected_mode = "speech"

# ─── 사이드바 ───
with st.sidebar:
    st.markdown("### 🐕 DogAICreator")
    st.markdown("강아지 사진으로 AI 영상을 만들어보세요!")

    st.markdown("---")
    st.markdown("#### 📖 사용 가이드")
    st.markdown("""
1. 강아지 사진을 업로드합니다
2. 강아지가 할 대사를 입력합니다
3. **AI 영상 생성하기** 버튼을 클릭합니다
4. 생성된 영상을 확인하고 다운로드합니다
""")

    st.markdown("---")
    st.markdown("#### 💡 팁")
    st.markdown("""
- 정면 사진이 가장 좋은 결과를 줍니다
- 짧고 재미있는 대사를 입력해보세요
- 세로 영상은 9:16 비율을 선택하세요
""")

    # 생성 이력 표시
    if st.session_state.history:
        st.markdown("---")
        st.markdown("#### 📜 생성 이력")
        for idx, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"🎬 {item['time']} - {item['prompt'][:20]}..."):
                st.video(item['video_data'])
                st.download_button(
                    label="📥 다운로드",
                    data=item['video_data'],
                    file_name=f"dog_ai_{item['time'].replace(':', '')}.mp4",
                    mime="video/mp4",
                    key=f"history_dl_{idx}"
                )

# ─── 메인 헤더 ───
st.markdown("<h1 class='main-header'>🐕 DogAICreator</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>우리 강아지가 말하는 마법 같은 순간을 만들어보세요</p>", unsafe_allow_html=True)

# ─── STEP 1: 사진 업로드 (세로 스택) ───
st.markdown("#### 📸 1. 강아지 사진 업로드")
file = st.file_uploader("JPG 또는 PNG 파일을 선택하세요", type=['jpg', 'jpeg', 'png'])

if file:
    st.session_state.image_bytes = file.getvalue()
    st.image(st.session_state.image_bytes, caption="업로드된 사진", use_container_width=True)

    # 이미지 정보 표시
    try:
        img = Image.open(io.BytesIO(st.session_state.image_bytes))
        width, height = img.size
        file_size_kb = len(st.session_state.image_bytes) / 1024
        if file_size_kb >= 1024:
            size_str = f"{file_size_kb / 1024:.1f} MB"
        else:
            size_str = f"{file_size_kb:.0f} KB"
        st.caption(f"📐 {width} x {height}px | 📦 {size_str}")
    except Exception:
        pass

# ─── STEP 2: 모드 선택 ───
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
st.markdown("#### 🎬 2. 영상 모드 선택")

# 모드 선택 (사진이 업로드된 경우에만 활성화)
mode_disabled = not st.session_state.image_bytes
mode = st.radio(
    "원하는 영상 스타일을 선택하세요",
    ["💬 대사 말하기", "🕺 춤 추기"],
    horizontal=True,
    disabled=mode_disabled,
    label_visibility="collapsed"
)

if mode_disabled:
    st.info("👆 먼저 강아지 사진을 업로드해주세요!")

# 모드를 세션 상태에 저장
st.session_state.selected_mode = "speech" if "대사" in mode else "dance"

# ─── STEP 3: 모드별 입력 ───
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

if st.session_state.selected_mode == "speech":
    # 대사 모드
    st.markdown("#### ✏️ 3. 대사 입력")

    # 예시 프롬프트 버튼
    st.markdown("**💬 예시 대사** (터치하면 자동 입력)")
    examples = [
        "주인님, 나랑 산책 가요! 밖에 날씨 좋잖아요~",
        "밥 주세요! 배고파 죽겠다구요!",
        "오늘도 열심히 집 지켰어요. 칭찬해주세요!",
        "안녕하세요~ 저는 세상에서 제일 귀여운 강아지입니다!",
        "간식 어디 숨겼어요? 다 알고 있다구요!",
    ]

    for i, ex in enumerate(examples):
        short_label = ex[:25] + "..." if len(ex) > 25 else ex
        if st.button(f"💬 {short_label}", key=f"ex_{i}", use_container_width=True):
            st.session_state.selected_example = ex
            st.rerun()

    # 대사 입력
    default_prompt = st.session_state.selected_example or ""
    prompt = st.text_area(
        "강아지가 할 말",
        value=default_prompt,
        placeholder="주인님, 나랑 공놀이 하러 가요!",
        height=100
    )
else:
    # 춤 모드 - 자동 프롬프트 생성
    st.markdown("#### 💃 3. 춤 스타일 선택")

    # 춤 스타일 옵션
    dance_style = st.selectbox(
        "춤 스타일을 선택하세요",
        [
            "😎 힙합 댄스 - 시원한 쩍쩍이와 터치더무브",
            "🎤 K-POP 댄스 - 그룹 안무처럼 역동적으로",
            "💃 재즈댄스 - 우아하고 부드러운 움직임",
            "🎹 클래식 발레 - 우아한 회전과 점프",
            "🪘 라틴 댄스 - 삼바와 차차차 같은 열정적인 춤",
            "🎭 브레이크댄스 - 스피닝과 파워무브",
            "🪗 틱톡 댄스 - 유행하는 챌린지 안무",
            "🎊 파티 댄스 - 신나고 즐거운 분위기"
        ],
        label_visibility="collapsed"
    )

    # 자동 프롬프트 생성 (사용자가 직접 입력하지 않음)
    # 강아지가 두 발로 서서 춤을 추며 가사 없는 음악에 맞춰 말하는 대사
    prompt = f"강아지가 두 발로 일어나서 {dance_style.split(' - ')[1]} 춤을 추면서 말해요. 배경음악은 가사 없는 인스트루멘탈이고, 강아지가 신나게 춤추는 모습이에요!"

    st.info(f"선택된 스타일: {dance_style}")
    st.caption("💡 강아지가 두 발로 일어나 춤을 추며 말합니다! (가사 없는 음악)")

# ─── STEP 4: 고급 설정 ───
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

with st.expander("🔧 고급 설정"):
    # AI 엔진 선택 (Kling AI가 기본값)
    engine_options = {"kling": "Kling AI", "gemini": "Google Gemini"}
    selected_engine = st.selectbox(
        "AI 엔진",
        list(engine_options.keys()),
        format_func=lambda x: engine_options[x],
        index=0,  # Kling AI가 기본값
    )

    # 선택된 엔진에 따라 모델 목록 동적 변경
    if selected_engine == "kling":
        model_options = list(KlingService.MODELS.keys())
        default_kling_model = "kling-v3-0"
        default_index = model_options.index(default_kling_model) if default_kling_model in model_options else 0
        selected_model = st.selectbox(
            "AI 모델",
            model_options,
            index=default_index,
            format_func=lambda x: KlingService.MODELS[x]
        )
    else:
        model_options = list(GeminiService.MODELS.keys())
        selected_model = st.selectbox("AI 모델", model_options, format_func=lambda x: GeminiService.MODELS[x])

    if selected_engine == "kling":
        video_duration = st.select_slider("영상 길이 (초)", options=KlingService.ALLOWED_DURATIONS, value=5)
    else:
        video_duration = 4
        st.caption("Gemini는 4초 길이로 고정됩니다.")
    aspect_ratio = st.selectbox("화면 비율", ["16:9", "9:16"])

# ─── STEP 5: 생성 버튼 ───
st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# 비밀번호 입력
password = st.text_input(
    "🔒 생성 비밀번호",
    type="password",
    placeholder="비밀번호를 입력하세요",
    max_chars=20
)

if st.button("🎬 AI 영상 생성하기", type="primary", use_container_width=True):
    # 비밀번호 확인
    if not password:
        st.error("비밀번호를 입력해주세요!")
    elif password != st.secrets.ADMIN_PASSWORD:
        st.error("비밀번호가 올바르지 않습니다!")
    elif not st.session_state.image_bytes:
        st.error("먼저 강아지 사진을 업로드해주세요!")
    elif st.session_state.selected_mode == "speech" and not prompt.strip():
        st.error("강아지가 할 대사를 입력해주세요!")
    elif selected_engine == "kling" and 'kling_service' not in st.session_state:
        st.error("Kling AI 서비스에 연결되지 않았습니다. API 키를 확인해주세요.")
    elif selected_engine == "gemini" and 'gemini_service' not in st.session_state:
        st.error("Gemini 서비스에 연결되지 않았습니다. API 키를 확인해주세요.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(p, msg):
            progress_bar.progress(min(p, 1.0))
            status_text.text(f"⏳ {msg}")

        # 선택된 엔진에 따라 서비스 호출
        if selected_engine == "kling":
            service = st.session_state.kling_service
        else:
            service = st.session_state.gemini_service

        # 영상 생성 호출
        generate_kwargs = {
            "image_bytes": st.session_state.image_bytes,
            "prompt": prompt,
            "progress_callback": update_progress,
            "model": selected_model,
            "duration": video_duration,
            "aspect_ratio": aspect_ratio,
        }
        if selected_engine == "kling":
            generate_kwargs["mode_type"] = st.session_state.selected_mode

        success, result_msg, video_data = service.generate_video(**generate_kwargs)

        # 진행바/상태 텍스트 정리
        progress_bar.empty()
        status_text.empty()

        if success and video_data:
            # 세션 스테이트에 저장 (리렌더링 후에도 유지)
            st.session_state.video_data = video_data
            st.session_state.video_prompt = prompt

            # 이력에 추가
            st.session_state.history.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'prompt': prompt,
                'video_data': video_data
            })

            st.balloons()
            st.rerun()
        else:
            st.error(f"생성 실패: {result_msg}")

# ─── 결과 영상 표시 (session_state 기반, 버튼 블록 밖) ───
if st.session_state.video_data:
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='result-box'>", unsafe_allow_html=True)
    st.success("🎉 영상 생성이 완료되었습니다!")

    if st.session_state.video_prompt:
        st.caption(f"💬 대사: {st.session_state.video_prompt}")

    # 영상 재생 (전체 너비)
    st.video(st.session_state.video_data)

    # 다운로드 버튼 (전체 너비, 터치 친화적)
    st.download_button(
        label="📥 영상 파일(MP4) 저장하기",
        data=st.session_state.video_data,
        file_name=f"dog_ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
        mime="video/mp4",
        use_container_width=True
    )

    if st.button("🔄 새 영상 만들기", use_container_width=True):
        st.session_state.video_data = None
        st.session_state.video_prompt = None
        st.session_state.selected_example = ""
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ─── 푸터 ───
st.markdown("---")
st.caption("© 2026 DogAICreator | Powered by Kling AI & Google Gemini")
