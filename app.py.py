import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile

# 1. 페이지 설정
st.set_page_config(page_title="AI 화장품 규제/패키징 통합 검토 시스템", layout="wide")

# 2. 사이드바: API 키 및 규제 파일 업로드 (Step 1 완수)
st.sidebar.title("⚙️ 시스템 설정")
api_key_input = st.sidebar.text_input("Google Gemini API 키 입력", type="password")
uploaded_docs = st.sidebar.file_uploader("규제 데이터베이스 업로드 (PDF 9개)", accept_multiple_files=True, type=['pdf'])

st.title("🧪 AI 화장품 규제/패키징 통합 검토 에이전트")
st.info("🔒 **[보안 가이드] 영업 기밀(BOM) 보호를 위한 데이터 마스킹 적용**\n\n화장품 규제의 사각지대를 없애기 위해 **'전성분'을 모두 입력**해 주십시오. 단, 기획안의 기밀 보호를 위해 정제수, 보습제 등 일반 베이스는 이름만 적으시고, **식약처 배합 한도 확인이 필요한 핵심 원료(예: 살리실릭애씨드, 에탄올 등)에만 괄호로 비율(%)을 기재**해 주세요. (예: 정제수, 글리세린, 살리실릭애씨드(1.5%), 향료)")

# 3. 화장품 정보 입력란 (Step 2 완수)
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

# 4. 분석 실행 및 보고서 작성 (Step 3 완수)
if st.button("🚀 규제 검토 및 패키징 솔루션 생성", type="primary"):
    if not api_key_input:
        st.error("사이드바에 Gemini API 키를 입력해주세요.")
    elif len(uploaded_docs) == 0:
        st.error("사이드바에 규제 PDF 파일들을 업로드해주세요.")
    else:
        try:
            genai.configure(api_key=api_key_input)
            
            # 진행 상태 표시 UI
            status_text = st.empty()
            status_text.info("🔄 1/3: 규제 파일 서버 업로드 및 인덱싱 중...")
            
            # Streamlit에서 업로드된 파일을 임시 저장 후 Gemini로 전송
            gemini_files = []
            for doc in uploaded_docs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(doc.getvalue())
                    tmp_path = tmp.name
                g_file = genai.upload_file(path=tmp_path)
                gemini_files.append(g_file)
            
            # 파일 처리 대기 (ACTIVE 상태 확인)
            for file in gemini_files:
                while file.state.name == "PROCESSING":
                    time.sleep(2)
                    file = genai.get_file(file.name)
            
            status_text.info("🧪 2/3: 전성분 교차 검증 및 MSDS 화학 반응성 평가 중...")
            
            system_instruction = """
            당신은 화장품 법규 및 포장재 규제를 검토하는 '수석 AI 규제 검토관'입니다.
            사용자가 입력한 전성분 중 금지 원료(별표 1)가 있는지 찾고, 괄호로 표시된 비율(%)이 배합 한도(별표 2)를 초과하는지 수리적으로 계산하십시오.
            
            반드시 아래 목차에 맞추어 실무자가 최종 결정할 수 있는 '추천 보고서' 형태로 작성하십시오.
            1. 규제 위반 사항 종합 (성분 금지/한도 위반, 포장공간비율 10~15% 룰, 재활용등급 등)
            2. 주요 성분 CAS No. 및 MSDS 기반 용기 반응성 분석 (예: 에탄올/산성 물질이 1차 용기에 미치는 영향)
            3. 1차/2차 포장재 재질 후보군 추천 (실무자 최종 선택용 3가지 옵션 제시)
            4. 3D 모델링 시각화 제안 (1차 용기와 2차 단상자를 명확히 구분하여 형태와 색상(Hex Code)을 구체적으로 제안)
            5. 종합 추천 및 실무자 최종 결정 가이드
            """
            
            model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=system_instruction)
            
            user_prompt = f"""
            [화장품 기획안 분석 요청]
            - 종류: {cosmetic_type} / 용량: {volume}ml / 점도: {viscosity} / 타겟: {target_age}
            - 전성분: {full_ingredients}
            - 주성분/특수베이스: {key_ingredients} / 에탄올: {ethanol_content}%
            - 1차 용기: {primary_material} / 토출기구: {dispenser_type}
            - 2차 포장: {secondary_material} / 단상자 용적: {box_volume}ml
            """
            
            status_text.info("📦 3/3: 최종 규제 검토 및 추천 보고서 생성 중 (실시간 출력)...")
            
            report_placeholder = st.empty()
            request_data = gemini_files + [user_prompt]
            
            # 실시간 스트리밍 출력 (타자 치는 효과)
            response = model.generate_content(request_data, stream=True)
            full_report = ""
            for chunk in response:
                full_report += chunk.text
                report_placeholder.markdown(full_report + "▌")
            
            report_placeholder.markdown(full_report)
            status_text.success("✅ 규제 검토 보고서 생성이 완료되었습니다.")
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")