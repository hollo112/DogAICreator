# CLAUDE.md - DogAICreator 프로젝트 가이드

## 프로젝트 개요

강아지 사진을 업로드하고 프롬프트를 입력하면 Gemini API로 AI 영상을 생성하는 Streamlit 웹앱.
자세한 요구사항은 `PRD.md`를 참고할 것.

## 기술 스택

- Python 3.14+
- Streamlit (웹 프레임워크)
- Google Gemini API (영상 생성)
- python-dotenv (환경변수 관리)

## 프로젝트 구조

```
DogAICreator/
├── app.py              # Streamlit 메인 앱
├── services/
│   └── gemini.py       # Gemini API 연동 로직
├── utils/
│   └── file_handler.py # 파일 업로드/다운로드 처리
├── .env                # API 키 (gitignore 대상)
├── .env.example        # 환경변수 템플릿
├── requirements.txt    # 의존성 목록
├── PRD.md              # 제품 요구사항 문서
├── CLAUDE.md           # 이 파일
└── .gitignore
```

## 개발 규칙

- 한국어 주석 사용
- Streamlit 컴포넌트 활용 (st.file_uploader, st.text_area, st.video 등)
- API 키는 절대 코드에 하드코딩하지 않는다 (.env 또는 st.secrets 사용)
- 모바일 호환성을 항상 고려한다
- 에러 처리를 꼼꼼히 한다 (API 실패, 파일 형식 오류 등)

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
streamlit run app.py
```

## 환경변수

- `GEMINI_API_KEY`: Google Gemini API 키