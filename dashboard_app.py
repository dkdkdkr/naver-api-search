import streamlit as st  # Streamlit 라이브러리 임포트
import pandas as pd  # Pandas 라이브러리 임포트
import plotly.express as px  # Plotly Express 라이브러리 임포트
import plotly.graph_objects as go  # Plotly Graph Objects 라이브러리 임포트
import requests  # HTTP 요청을 위한 requests 라이브러리 임포트
import json  # JSON 데이터 처리를 위한 json 라이브러리 임포트
import os  # 운영체제 상호작용을 위한 os 라이브러리 임포트
from datetime import datetime, timedelta  # 날짜 및 시간 처리를 위한 클래스 임포트
from dotenv import load_dotenv  # .env 파일 로드를 위한 함수 임포트
import re  # 정규표현식 처리를 위한 re 라이브러리 임포트
from collections import Counter  # 요소 빈도 계산을 위한 Counter 클래스 임포트

# 1. 환경 설정 및 API 키 로드
load_dotenv()  # .env 파일에 저장된 환경 변수 로드
# Streamlit Secrets(배포 환경) 우선 사용, 없으면 환경 변수(.env) 활용
CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", os.getenv("NAVER_CLIENT_ID"))  # 네이버 API 클라이언트 ID 가져오기
CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", os.getenv("NAVER_CLIENT_SECRET"))  # 네이버 API 클라이언트 시크릿 가져오기

st.set_page_config(page_title="실시간 네이버 검색 분석 대시보드", layout="wide")  # 대시보드 페이지 설정 (제목, 레이아웃)

# 스타일 설정
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;  /* 메인 배경색 설정 */
    }
    .stMetric {
        background-color: #1e2130;  /* 메트릭 카드 배경색 설정 */
        padding: 15px;  /* 안쪽 여백 설정 */
        border-radius: 10px;  /* 모서리 둥글게 설정 */
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);  /* 그림자 효과 추가 */
    }
    </style>
    """, unsafe_allow_html=True)  # 커스텀 CSS 적용

# 2. API 인증 확인
def check_api_auth():  # API 자격 증명 유효성 확인 함수 정의
    if not CLIENT_ID or not CLIENT_SECRET:  # 클라이언트 ID 또는 시크릿이 없는 경우
        st.error("🔑 네이버 API 자격 증명이 설정되지 않았습니다. .env 파일을 확인해 주세요.")  # 에러 메시지 출력
        return False  # 인증 실패 반환
    return True  # 인증 성공 반환

# 3. API 연동 함수
def get_datalab_trend(keywords, start_date, end_date):  # 네이버 데이터랩 트렌드 조회 함수 정의
    """네이버 데이터랩 검색어 트렌드 조회"""
    url = "https://openapi.naver.com/v1/datalab/search"  # 데이터랩 API 엔드포인트 URL
    headers = {  # HTTP 헤더 설정
        "X-Naver-Client-Id": CLIENT_ID,  # 클라이언트 ID 헤더 추가
        "X-Naver-Client-Secret": CLIENT_SECRET,  # 클라이언트 시크릿 헤더 추가
        "Content-Type": "application/json"  # 콘텐츠 타입을 JSON으로 설정
    }
    
    body = {  # API 요청 바디 구성
        "startDate": start_date,  # 조회 시작일
        "endDate": end_date,  # 조회 종료일
        "timeUnit": "month",  # 시간 단위 (월별)
        "keywordGroups": [  # 키워드 그룹 목록 생성
            {"groupName": k, "keywords": [k]} for k in keywords
        ]
    }
    
    try:  # 예외 처리를 위한 try 블록 시작
        response = requests.post(url, headers=headers, data=json.dumps(body))  # API에 POST 요청 전송
        if response.status_code == 200:  # 요청이 성공한 경우 (상태 코드 200)
            data = response.json()  # 응답 데이터를 JSON으로 파싱
            results = []  # 결과를 담을 리스트 초기화
            for res in data['results']:  # 각 결과 항목 순회
                group_name = res['title']  # 키워드 그룹 이름 추출
                for entry in res['data']:  # 데이터 포인트 순회
                    results.append({  # 결과 리스트에 데이터 추가
                        "date": entry['period'],  # 날짜 정보
                        "keyword": group_name,  # 키워드
                        "ratio": entry['ratio']  # 검색 비중
                    })
            return pd.DataFrame(results)  # 결과를 데이터프레임으로 변환하여 반환
    except Exception as e:  # 오류 발생 시
        st.error(f"트렌드 API 호출 중 오류 발생: {e}")  # 에러 메시지 출력
    return pd.DataFrame()  # 실패 시 빈 데이터프레임 반환

def search_naver(channel, query, display=100):  # 네이버 통합 검색 API 호출 함수 정의
    """네이버 검색 API 호출"""
    url = f"https://openapi.naver.com/v1/search/{channel}.json"  # 검색 분야별 엔드포인트 URL
    headers = {  # HTTP 헤더 설정
        "X-Naver-Client-Id": CLIENT_ID,  # 클라이언트 ID 헤더 추가
        "X-Naver-Client-Secret": CLIENT_SECRET,  # 클라이언트 시크릿 헤더 추가
    }
    params = {  # 쿼리 파라미터 설정
        "query": query,  # 검색어
        "display": display,  # 출력 결과 개수
        "start": 1,  # 검색 시작 위치
        "sort": "sim"  # 유사도순 정렬
    }
    
    try:  # 예외 처리 시작
        response = requests.get(url, headers=headers, params=params)  # API에 GET 요청 전송
        if response.status_code == 200:  # 성공 시
            items = response.json().get('items', [])  # 검색 결과 아이템 목록 추출
            for item in items:  # 각 아이템 순회
                item['channel'] = channel  # 채널 정보 명시
                item['search_keyword'] = query  # 검색 키워드 명시
            return pd.DataFrame(items)  # 데이터프레임으로 변환하여 반환
    except Exception as e:  # 오류 시
        st.error(f"{channel} API 호출 중 오류 발생: {e}")  # 에러 출력
    return pd.DataFrame()  # 빈 데이터프레임 반환

# 4. 데이터 전처리 및 분석 함수
def process_text_frequency(df, column):  # 텍스트 빈도 분석 함수 정의
    """텍스트 빈도 분석 (공백 기준 상위 30개)"""
    all_text = " ".join(df[column].dropna().astype(str))  # 지정한 컬럼의 모든 텍스트를 하나로 결합
    # 태그 제거 및 정규표현식 클렌징
    clean_text = re.sub(r'<.*?>|[^\w\s]', ' ', all_text)  # HTML 태그 및 특수문자 제거
    words = clean_text.split()  # 공백 기준으로 단어 분리
    # 불용어 처리 (간단히)
    stop_words = ['있는', '대한', '및', '위한', '등', '합니다', '입니다', '하고', '으로', '에서', '를', '을', '의', '가', '이', '와', '과']  # 분석에서 제외할 단어 목록
    filtered_words = [w for w in words if len(w) > 1 and w not in stop_words]  # 한 글자 이하 또는 불용어 제외
    
    counts = Counter(filtered_words)  # 단어 빈도 계산
    return pd.DataFrame(counts.most_common(30), columns=['word', 'count'])  # 상위 30개 단어를 데이터프레임으로 반환

# 5. UI 구성
st.title("📈 실시간 네이버 검색 데이터 분석 대시보드")  # 대시보드 제목 표시
st.markdown("사용자가 입력한 키워드에 대해 네이버 API를 실시간 호출하여 트렌드 및 검색 결과를 분석합니다.")  # 대시보드 설명 표시

# 사이드바 설정
st.sidebar.header("🛠️ 검색 설정")  # 사이드바 헤더 표시
keyword_input = st.sidebar.text_input("분석 키워드 (쉼표로 구분)", value="경마, 경마장")  # 키워드 입력 필드 (기본값 설정)
keywords = [k.strip() for k in keyword_input.split(",") if k.strip()]  # 입력된 키워드 분리 및 공백 제거

date_range = st.sidebar.date_input(  # 조회 기간 선택 필드
    "트렌드 조회 기간",  # 라벨
    value=(datetime.now() - timedelta(days=365), datetime.now()),  # 기본값 (최근 1년)
    max_value=datetime.now()  # 최대 선택 가능일 (오늘)
)

search_channels = st.sidebar.multiselect(  # 검색 채널 다중 선택 필드
    "검색 채널 선택",  # 라벨
    options=["shop", "blog", "news", "cafearticle"],  # 선택 가능한 옵션
    default=["shop", "blog", "news", "cafearticle"]  # 기본 선택값
)

fetch_button = st.sidebar.button("🚀 실시간 데이터 수집 및 분석 실행")  # 분석 실행 버튼

# 데이터 세션 상태 관리 (페이지 리로드 시에도 데이터 유지)
if 'trend_data' not in st.session_state:  # 트렌드 데이터가 세션에 없는 경우
    st.session_state.trend_data = None  # 초기화
if 'search_data' not in st.session_state:  # 검색 데이터가 세션에 없는 경우
    st.session_state.search_data = None  # 초기화

# 실시간 수집 실행 조건문
if fetch_button:  # 버튼이 클릭되었을 때
    if check_api_auth():  # API 자격 증명이 유효한 경우
        with st.spinner("네이버 API로부터 데이터를 수집 중입니다..."):  # 로딩 스피너 표시
            # 1. 트렌드 데이터 수집
            start_dt = date_range[0].strftime("%Y-%m-%d")  # 시작일 포맷팅
            end_dt = date_range[1].strftime("%Y-%m-%d")  # 종료일 포맷팅
            st.session_state.trend_data = get_datalab_trend(keywords, start_dt, end_dt)  # 데이터 수집 및 세션 저장
            
            # 2. 통합 검색 데이터 수집
            all_results = []  # 모든 채널 결과를 담을 리스트
            for kw in keywords:  # 각 키워드별 순회
                for ch in search_channels:  # 각 채널별 순회
                    df = search_naver(ch, kw)  # 각 키워드/채널에 대한 검색 API 호출
                    if not df.empty:  # 결과가 비어있지 않으면
                        all_results.append(df)  # 리스트에 추가
            
            if all_results:  # 결과가 하나라도 있으면
                st.session_state.search_data = pd.concat(all_results, ignore_index=True)  # 데이터 통합 및 세션 저장
            else:  # 결과가 없으면
                st.session_state.search_data = pd.DataFrame()  # 빈 데이터프레임 저장
            
            st.success("데이터 수집 완료!")  # 성공 메시지 표시

# 결과 렌더링
if st.session_state.search_data is not None and not st.session_state.search_data.empty:
    df = st.session_state.search_data
    
    # 탭 메뉴 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 프로파일링", "📈 트렌드", "🗂️ 채널/시장 분석", "📝 텍스트 분석", "📋 원본 데이터"])
    
    with tab1:
        st.header("🔍 데이터 프로파일링 요약")
        col1, col2, col3 = st.columns(3)
        col1.metric("전체 수집 건수", f"{len(df)}건")
        col2.metric("키워드 수", f"{len(keywords)}개")
        col3.metric("채널 수", f"{df['channel'].nunique()}개")
        
        st.subheader("데이터셋 정보")
        info_df = pd.DataFrame({
            "컬럼명": df.columns,
            "데이터 타입": [str(df[c].dtype) for c in df.columns],  # 각 컬럼의 데이터 타입을 문자열로 변환하여 리스트 생성
            "결측치 수": [df[c].isna().sum() for c in df.columns]  # 각 컬럼의 결측치(NaN) 개수를 계산하여 리스트 생성
        })  # 데이터프레임 생성 완료
        st.table(info_df)  # 요약 정보를 표 형태로 화면에 표시

    with tab2:  # '트렌드' 탭 구성
        st.header("📈 실시간 검색어 트렌드 추이 (DataLab)")  # 탭 헤더 표시
        if st.session_state.trend_data is not None and not st.session_state.trend_data.empty:  # 트렌드 데이터가 있는 경우
            trend_df = st.session_state.trend_data  # 세션에서 데이터 가져오기
            fig_trend = px.line(trend_df, x='date', y='ratio', color='keyword',   # 선 그래프 생성 (x축: 날짜, y축: 비중, 색상: 키워드)
                                title="월별 검색 비중 변화 (상대치)", markers=True,  # 제목 설정 및 마커 표시
                                template="plotly_dark")  # 다크 테마 적용
            st.plotly_chart(fig_trend, use_container_width=True)  # 그래프를 화면 너비에 맞춰 표시
        else:  # 데이터가 없는 경우
            st.warning("트렌드 데이터를 불러올 수 없습니다.")  # 경고 메시지 표시

    with tab3:  # '채널/시장 분석' 탭 구성
        st.header("🗂️ 통합 검색 채널 및 시장 구조")  # 탭 헤더 표시
        
        col_c1, col_c2 = st.columns(2)  # 2개의 컬럼으로 레이아웃 분할
        
        with col_c1:  # 첫 번째 컬럼
            st.subheader("채널별 데이터 비중")  # 서브헤더 표시
            fig_pie = px.pie(df, names='channel', title="수집 채널 분포",   # 파이 차트 생성
                             hole=0.4, template="plotly_dark")  # 도넛 모양(hole) 및 다크 테마 설정
            st.plotly_chart(fig_pie, use_container_width=True)  # 차트 표시
        
        with col_c2:  # 두 번째 컬럼
            st.subheader("키워드별 채널 교차 분석")  # 서브헤더 표시
            # 트리맵 시각화
            fig_tree = px.treemap(df, path=['search_keyword', 'channel'],   # 트리맵 생성 (계층: 키워드 > 채널)
                                  title="키워드/채널별 분포 (Treemap)",  # 제목 설정
                                  template="plotly_dark")  # 다크 테마 적용
            st.plotly_chart(fig_tree, use_container_width=True)  # 차트 표시
            
        # 쇼핑 가격 분석 (쇼핑 데이터가 있는 경우에만 실행)
        if 'shop' in df['channel'].values:  # 채널 컬럼에 'shop'이 포함된 경우
            st.divider()  # 구분선 추가
            st.subheader("💰 쇼핑 섹션 정밀 분석")  # 쇼핑 분석 섹션 제목
            shop_df = df[df['channel'] == 'shop'].copy()  # 쇼핑 데이터만 복사하여 추출
            shop_df['lprice'] = pd.to_numeric(shop_df['lprice'], errors='coerce')  # 가격 데이터를 수치형으로 변환
            
            c1, c2 = st.columns(2)  # 다시 2개의 컬럼으로 분할
            with c1:  # 왼쪽 컬럼
                fig_price = px.box(shop_df, x='search_keyword', y='lprice', points="all",  # 박스 플롯 생성 (가격 분포)
                                   title="키워드별 쇼핑 가격 분포 (Boxplot)", template="plotly_dark")  # 제목 및 테마 설정
                st.plotly_chart(fig_price, use_container_width=True)  # 차트 표시
            with c2:  # 오른쪽 컬럼
                # 선버스트 차트 (브랜드/제조사 계층 구조)
                sunburst_df = shop_df.dropna(subset=['brand', 'maker']).head(100)  # 브랜드/제조사가 있는 상위 100건 추출
                if not sunburst_df.empty:  # 데이터가 있으면
                    fig_sun = px.sunburst(sunburst_df, path=['search_keyword', 'brand'],   # 선버스트 차트 생성
                                          title="브랜드 포지셔닝 (Sunburst)",  # 제목 설정
                                          template="plotly_dark")  # 다크 테마 적용
                    st.plotly_chart(fig_sun, use_container_width=True)  # 차트 표시

    with tab4:  # '텍스트 분석' 탭 구성
        st.header("📝 핵심 키워드 빈도 분석 (Top 30)")  # 탭 헤더 표시
        col_t1, col_t2 = st.columns(2)  # 2개의 컬럼 레이아웃
        
        with col_t1:  # 첫 번째 컬럼
            st.subheader("제목(Title) 키워드")  # 서브헤더
            title_freq = process_text_frequency(df, 'title')  # 제목 컬럼 빈도 분석 실행
            fig_title = px.bar(title_freq, x='count', y='word', orientation='h',  # 가로 바 차트 생성
                               title="제목 상위 30개 단어", template="plotly_dark",  # 제목 및 테마 설정
                               color='count', color_continuous_scale='Viridis')  # 빈도에 따른 색상 설정
            fig_title.update_layout(yaxis={'categoryorder':'total ascending'})  # 빈도 순으로 정렬
            st.plotly_chart(fig_title, use_container_width=True)  # 차트 표시
            
        with col_t2:  # 두 번째 컬럼
            st.subheader("설명(Description) 키워드")  # 서브헤더
            desc_freq = process_text_frequency(df, 'description')  # 설명 컬럼 빈도 분석 실행
            fig_desc = px.bar(desc_freq, x='count', y='word', orientation='h',  # 가로 바 차트 생성
                              title="설명 상위 30개 단어", template="plotly_dark",  # 제목 및 테마 설정
                              color='count', color_continuous_scale='Plasma')  # 색상 설정
            fig_desc.update_layout(yaxis={'categoryorder':'total ascending'})  # 정렬 설정
            st.plotly_chart(fig_desc, use_container_width=True)  # 차트 표시

    with tab5:  # '원본 데이터' 탭 구성
        st.header("📋 수집 원본 데이터 조회")  # 탭 헤더 표시
        st.write("사이드바의 필터에 따라 수집된 실시간 데이터프레임입니다.")  # 설명 텍스트
        st.dataframe(df, use_container_width=True)  # 전체 데이터프레임 표시
        
        # CSV 다운로드 버튼 구성
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')  # 데이터프레임을 CSV 바이너리로 인코딩
        st.download_button(  # 다운로드 버튼 생성
            label="📥 검색 결과 CSV 다운로드",  # 버튼 라벨
            data=csv,  # 다운로드할 데이터
            file_name=f"naver_live_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",  # 파일명 설정 (현재 시간 포함)
            mime="text/csv",  # MIME 타입 설정
        )

elif st.session_state.search_data is not None and st.session_state.search_data.empty:  # 데이터 수집 후 결과가 없는 경우
    st.warning("결과를 찾을 수 없습니다. 다른 키워드로 검색해 보세요.")  # 경고 메시지 표시
else:  # 초기 상태 (데이터가 아직 수집되지 않은 경우)
    st.info("사이드바에서 키워드를 입력하고 분석 실행 버튼을 눌러주세요.")  # 안내 메시지 표시
