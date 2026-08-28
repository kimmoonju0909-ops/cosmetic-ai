import streamlit as st
import google.generativeai as genai
import time
import os

# 1. 페이지 및 API 설정
st.set_page_config(page_title="AI 화장품 규제 및 패키징 검토 에이전트", layout="wide")
GOOGLE_API_KEY = "AQ.Ab8RN6IQ3ldMRnAUxyVWuAfa47HkfY8nWOfe6WDHcFsbdrf-Xw"
genai.configure(api_key=GOOGLE_API_KEY)

@st.cache_resource
def initialize_agent():
    """앱 실행 시 규제 파일(9개)을 한 번만 업로드하고 모델을 초기화합니다."""
    file_paths = [
        "포장공간비율_규정.pdf",
        "포장재_재활용_용이성_등급평가_기준.pdf",
        "화장품_안전기준_고시.pdf",
        "화장품에_사용할_수_없는_원료(별표1).pdf", # 반드시 깨지지 않은 정상 파일 사용
        # 나머지 5개 파일 경로 추가
    ]
    
    uploaded_files = []
    ready_files = []
    
    for path in file_paths:
        if os.path.exists(path):
            file_obj = genai.upload_file(path=path)
            uploaded_files.append(file_obj)

    # 파일 인덱싱 상태 대기 (PROCESSING -> ACTIVE)
    for file in uploaded_files:
        while file.state.name == "PROCESSING":
            time.sleep(3)
            file = genai.get_file(file.name)
        if file.state.name == "ACTIVE":
            ready_files.append(file)

    # [핵심] 수리적 추론 및 마스킹 데이터를 처리하는 시스템 프롬프트
    system_instruction = """
    당신은 화장품 법규 및 포장재 환경 규제를 검토하는 '수석 AI 규제 검토관'입니다.
    사용자는 영업기밀 보호를 위해 베이스 성분은 이름만 입력하고, 규제 검토가 필요한 핵심/제한 원료에만 괄호로 비율(%)을 적었습니다(데이터 마스킹).
    비율이 없는 성분은 배합 금지(별표 1) 여부만 검사하고, 비율이 적힌 성분은 배합 한도(별표 2) 초과 여부를 수학적으로 정확히 계산하십시오.
    
    [보고서 필수 목차]
    1. 규제 위반 사항 종합 (전성분 금지/한도 대조, 포장공간비율, 재활용등급)
    2. 주요 성분 CAS No. 및 MSDS 기반 용기 반응성 주의사항 (물리/화학적 상성)
    3. 1차/2차 포장재 재질 후보군 추천 (실무자 최종 선택용 3가지 옵션)
    4. 3D 모델링 시각화 제안 (1차 용기, 2차 단상자 색상코드 및 형태)
    5. 종합 추천 및 실무자 최종 결정 가이드
    """
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=system_instruction
    )
    return model, ready_files

st.title("🧪 AI 화장품 규제/패키징 통합 검토 시스템")
st.markdown("입력된 화장품 처방 및 포장 사양을 바탕으로 법적 리스크를 분석하고 최적의 패키징을 제안합니다.")

# 보안 안내 메시지 UI 추가
st.info("🔒 **[보안 가이드] 영업 기밀(BOM) 보호를 위한 데이터 마스킹 적용**\n\n전체 배합 비율을 입력하실 필요가 없습니다. 정제수, 보습제 등 베이스 성분은 '이름'만 적으시고, **식약처 배합 한도 규제 물질이나 고반응성 성분(예: BHA, 고함량 에탄올 등)에만 괄호로 비율(%)을 기재**해 주세요. 본 시스템은 검토 완료 후 데이터를 즉시 파기합니다.")

# API 초기화
try:
    # 실제 구동 시 아래 주석을 해제하세요.
    # model, document_files = initialize_agent() 
    pass
except Exception as e:
    st.error(f"API 연동 오류: {e}")

# UI 레이아웃 분할
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 화장품 내용물 정보")
    cosmetic_type = st.selectbox("화장품 종류", ["기초화장용 (토너/로션)", "색조화장용", "인체세정용", "영유아용"])
    volume = st.number_input("용량 (ml/g)", min_value=1, value=150)
    viscosity = st.selectbox("점도", ["저점도 (액상)", "중점도 (로션/에멀젼)", "고점도 (크림/밤)"])
    target_age = st.selectbox("타겟 연령층", ["10대~20대", "30대 이상", "영유아(만 3세 이하)", "전연령"])
    
    st.markdown("**성분 정보 (데이터 마스킹 적용)**")
    # 기밀 보호를 위해 특정 성분에만 %를 적은 기본 예시 세팅
    full_ingredients = st.text_area("전성분 입력 (, 로 구분)", "정제수, 에탄올, 부틸렌글라이콜, 살리실릭애씨드(1.5%), 티트리잎추출물, 피이지-60하이드로제네이티드캐스터오일, 탤크, 메칠유게놀(0.005%), 향료")
    key_ingredients = st.text_input("주유효성분 / 특수베이스", "살리실릭애씨드, 고함량 에탄올")
    ethanol_content = st.slider("에탄올 함유량 (%)", 0, 100, 15)

with col2:
    st.subheader("📦 기획 중인 패키징 사양")
    primary_material = st.selectbox("1차 용기 재질", ["유색 PET", "무색 PET", "유리", "PP/PE", "알루미늄", "아크릴"])
    dispenser_type = st.selectbox("토출 기구", ["메탈 스프링 펌프", "일반 캡", "플라스틱 단일재질 펌프", "스포이드"])
    secondary_material = st.selectbox("2차 포장(단상자) 재질", ["일반 코팅 종이", "FSC 인증 재생지", "플라스틱 단상자", "없음"])
    box_volume = st.number_input("단상자 용적 (ml, 포장공간 계산용)", min_value=1, value=250)

if st.button("🚀 규제 검토 및 패키징 솔루션 생성", type="primary"):
    
    # 1. 진행 상태 시각화 (UX 개선)
    status_text = st.empty()
    status_text.info("🔄 1단계: 전성분 및 식약처 금지 원료 데이터베이스 교차 검증 중...")
    time.sleep(1) # 시연용 딜레이
    status_text.info("🧪 2단계: 주요 성분 MSDS 데이터와 용기 화학적 반응성 평가 중...")
    time.sleep(1)
    status_text.info("📦 3단계: 최종 패키징 추천 솔루션 및 3D 모델링 생성 중...")
    time.sleep(1)
    status_text.empty() # 로딩 메시지 삭제
    
    user_prompt = f"""
    기획안 분석 요청:
    - 종류: {cosmetic_type} / 용량: {volume}ml / 점도: {viscosity} / 타겟: {target_age}
    - 전성분: {full_ingredients}
    - 주성분/베이스: {key_ingredients} / 에탄올: {ethanol_content}%
    - 1차 용기: {primary_material} / 토출기구: {dispenser_type}
    - 2차 포장: {secondary_material} / 단상자 용적: {box_volume}ml
    """
    
    st.subheader("📑 최종 규제 검토 및 추천 보고서")
    report_placeholder = st.empty()
    
    # 2. 스트리밍(Streaming) 출력 구현
    # 실제 API 연동 시 아래 주석 해제
    """
    request_data = document_files + [user_prompt]
    response = model.generate_content(request_data, stream=True)
    full_text = ""
    for chunk in response:
        full_text += chunk.text
        report_placeholder.markdown(full_text + "▌") # 타자기가 쳐지는 듯한 커서 효과
    report_placeholder.markdown(full_text)
    """
    
    # API 연결 전 UI 확인을 위한 목업(Mock) 스트리밍
    mock_response = "## 1. 규제 위반 사항 종합\n* **[부적합] 살리실릭애씨드 한도 초과:** 기초화장용 한도(0.5%)를 초과한 1.5%입니다. 배합률 수정이 필요합니다.\n* **[경고] 재활용 어려움:** 유색 PET와 금속 스프링 조합은 재활용 등급 하락 요인입니다.\n\n## 2. MSDS 용기 반응성\n* 산성(BHA) 및 고함량 에탄올로 인해 금속 펌프 부식 및 아크릴 크랙 우려가 있습니다.\n\n## 3. 포장재 추천\n* Option A (친환경): 무색 PET + Metal-free 펌프\n\n## 4. 3D 모델링 제안\n* 1차 용기: Hex #E0F7FA\n* 2차 단상자: Hex #D7CCC8"
    
    full_text = ""
    for char in mock_response:
        full_text += char
        report_placeholder.markdown(full_text + "▌")
        time.sleep(0.01) # 타자 속도 조절
    report_placeholder.markdown(full_text)
    
    # 3D 모델링 색상 픽커 표시
    st.divider()
    st.subheader("🎨 3D 모델링 컨셉 색상 프리뷰")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.color_picker("1차 용기 추천 색상 (재활용 우수 타겟)", "#E0F7FA", disabled=True)
    with col_c2:
        st.color_picker("2차 단상자 추천 색상 (FSC 종이 타겟)", "#D7CCC8", disabled=True)