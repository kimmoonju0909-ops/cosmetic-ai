import streamlit as st
import google.generativeai as genai
import time
import os

# 1. 페이지 설정
st.set_page_config(page_title="AI 화장품 규제/패키징 통합 검토 시스템", layout="wide")

# API 키 설정 (본인의 키로 반드시 변경하세요)
GOOGLE_API_KEY = "AQ.Ab8RN6IQ3ldMRnAUxyVWuAfa47HkfY8nWOfe6WDHcFsbdrf-Xw"
genai.configure(api_key=GOOGLE_API_KEY)

@st.cache_resource
def initialize_agent():
    """앱 실행 시 '같은 폴더'에 있는 규제 파일(9개)들을 자동으로 한 번만 업로드합니다."""
    # 🔥 주의: 실제 같은 폴더에 있는 9개 파일의 정확한 이름으로 변경해주세요.
    file_paths = [
        "포장공간비율_규정.pdf",
        "포장재_재활용_용이성_등급평가_기준.pdf",
        "화장품_안전기준_고시.pdf",
        "화장품에_사용할_수_없는_원료(별표1).pdf", # 교체된 정상 파일
        # "나머지_파일5.pdf",
        # "나머지_파일6.pdf",
        # "나머지_파일7.pdf",
        # "나머지_파일8.pdf",
        # "나머지_파일9.pdf"
    ]
    
    uploaded_files = []
    ready_files = []
    
    # 1. 로컬 폴더에서 파일 읽어서 서버로 자동 업로드
    for path in file_paths:
        if os.path.exists(path):
            file_obj = genai.upload_file(path=path)
            uploaded_files.append(file_obj)
        else:
            st.warning(f"⚠️ 폴더에 파일이 없습니다. 이름을 확인하세요: {path}")

    # 2. 파일 인덱싱 상태 대기 (PROCESSING -> ACTIVE)
    for file in uploaded_files:
        while file.state.name == "PROCESSING":
            time.sleep(3)
            file = genai.get_file(file.name)
        if file.state.name == "ACTIVE":
            ready_files.append(file)

    # 3. 시스템 프롬프트 설정 (데이터 마스킹, 수리적 계산, 보고서 목차)
    system_instruction = """
    당신은 화장품 법규 및 포장재 규제를 검토하는 '수석 AI 규제 검토관'입니다.
    사용자가 기밀 보호를 위해 핵심 성분에만 괄호로 비율(%)을 적은 '데이터 마스킹' 방식을 사용합니다.
    비율이 없는 성분은 배합 금지(별표 1) 여부를, 비율이 있는 성분은 한도(별표 2) 초과 여부를 정확히 계산하세요.
    
    [보고서 필수 목차]
    1. 규제 위반 사항 종합 (성분 금지/한도 위반, 포장공간비율, 재활용등급)
    2. 주요 성분 CAS No. 및 MSDS 기반 용기 화학 반응성 분석
    3. 1차/2차 포장재 재질 후보군 추천 (실무자 최종 선택용 3가지 옵션 제시)
    4. 3D 모델링 시각화 제안 (1차 용기/2차 단상자 형태 및 색상 Hex Code)
    5. 종합 추천 및 실무자 최종 결정 가이드
    """
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-latest",
        system_instruction=system_instruction
    )
    return model, ready_files

st.title("🧪 AI 화장품 규제/패키징 통합 검토 에이전트")
st.info("🔒 **[보안 가이드] 영업 기밀(BOM) 보호를 위한 데이터 마스킹 적용**\n\n'전성분'을 모두 입력하되, 정제수 같은 일반 베이스는 이름만 적으시고, **식약처 배합 한도 확인이 필요한 핵심 원료에만 괄호로 비율(%)을 기재**해 주세요. (예: 살리실릭애씨드(1.5%))")

# 에이전트 초기화 (자동으로 같은 폴더의 파일을 불러옴)
with st.spinner("같은 폴더의 규제 파일을 불러와 AI를 세팅 중입니다. 잠시만 기다려주세요..."):
    try:
        model, document_files = initialize_agent()
    except Exception as e:
        st.error(f"초기화 오류: API 키나 파일 경로를 확인해주세요. ({e})")
        st.stop()

# UI 레이아웃
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 화장품 내용물 정보")
    cosmetic_type = st.selectbox("화장품 종류", ["기초화장용 (토너/로션)", "색조화장용", "인체세정용", "두발용", "영유아용"])
    volume = st.number_input("용량 (ml/g)", min_value=1, value=150)
    viscosity = st.selectbox("점도", ["저점도 (액상)", "중점도 (로션/에멀젼)", "고점도 (크림/밤)"])
    target_age = st.selectbox("타겟 연령층", ["10대~20대", "30대 이상", "영유아(만 3세 이하)", "전연령"])
    
    full_ingredients = st.text_area("전성분 입력 (, 로 구분)", "정제수, 에탄올, 부틸렌글라이콜, 살리실릭애씨드(1.5%), 티트리잎추출물, 피이지-60하이드로제네이티드캐스터오일, 탤크, 메칠유게놀(0.005%), 향료")
    key_ingredients = st.text_input("주유효성분 / 특수베이스", "살리실릭애씨드, 고함량 에탄올")
    ethanol_content = st.slider("에탄올 함유량 (%)", 0, 100, 15)

with col2:
    st.subheader("📦 기획 중인 패키징 사양")
    primary_material = st.selectbox("1차 용기 재질", ["유색 PET", "무색 PET", "유리", "PP/PE", "알루미늄", "아크릴"])
    dispenser_type = st.selectbox("토출 기구", ["메탈 스프링 펌프", "일반 캡", "플라스틱 단일재질 펌프", "스포이드"])
    secondary_material = st.selectbox("2차 포장(단상자) 재질", ["일반 코팅 종이", "FSC 인증 재생지", "플라스틱 단상자", "없음"])
    box_volume = st.number_input("단상자 용적 (ml, 포장공간 계산용)", min_value=1, value=250)

# 검토 실행 버튼
if st.button("🚀 규제 검토 및 패키징 솔루션 생성", type="primary"):
    
    status_text = st.empty()
    status_text.info("🔄 전성분 교차 검증 및 MSDS 반응성, 포장 규제 평가 중...")
    
    user_prompt = f"""
    [화장품 기획안 분석 요청]
    - 종류: {cosmetic_type} / 용량: {volume}ml / 점도: {viscosity} / 타겟: {target_age}
    - 전성분: {full_ingredients}
    - 주성분/특수베이스: {key_ingredients} / 에탄올: {ethanol_content}%
    - 1차 용기: {primary_material} / 토출기구: {dispenser_type}
    - 2차 포장: {secondary_material} / 단상자 용적: {box_volume}ml
    """
    
    st.divider()
    st.subheader("📑 최종 규제 검토 및 추천 보고서")
    report_placeholder = st.empty()
    
    try:
        # 실제 API 호출 및 스트리밍 (화면에 코드가 노출되던 버그 완벽 해결)
        request_data = document_files + [user_prompt]
        response = model.generate_content(request_data, stream=True)
        
        full_report = ""
        for chunk in response:
            full_report += chunk.text
            report_placeholder.markdown(full_report + "▌") # 스트리밍 커서 효과
        
        report_placeholder.markdown(full_report) # 분석 끝나면 커서 제거
        status_text.success("✅ 규제 검토 완료!")
        
    except Exception as e:
        st.error(f"분석 중 오류 발생: {e}")