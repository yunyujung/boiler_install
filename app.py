# app.py
# 대기오염물질배출시설 / 특정가스사용시설 판별 도구
# Streamlit으로 실행:  streamlit run app.py

import streamlit as st

st.set_page_config(
    page_title="대기오염물질배출시설 · 특정가스사용시설 판별",
    layout="centered",
)

st.title("대기오염물질배출시설 · 특정가스사용시설 판별 도구")

TAB1, TAB2 = st.tabs(["대기오염물질배출시설", "특정가스사용시설"])

# -------------------------------------------------------------------
# 1. 대기오염물질배출시설 탭
# -------------------------------------------------------------------
with TAB1:
    st.subheader("대기오염물질배출시설 판별")

    st.markdown(
        """
**가스·경질유 사용 보일러/흡수식 냉·온수기 대상 기준**

- 시간당 증발량이 **2톤 이상**, 또는  
- 시간당 열량이 **1,238,600 kcal/h 이상**인 경우에만 「대기오염물질배출시설」에 해당합니다.

단, 다음의 소형 보일러(환경표지 인증 보일러)는 **용량 산정에서 제외**될 수 있습니다.  
- 시간당 증발량 **0.1톤 미만** 또는  
- 시간당 열량 **61,900 kcal/h 미만**이면서  
- 「환경기술 및 환경산업 지원법」 제17조에 따른 **환경표지 인증**을 받은 보일러  

→ 실제 적용 여부는 **유역환경청장·지방환경청장·수도권대기환경청장 또는 시·도지사 확인이 반드시 필요**합니다.
        """
    )

    st.markdown("### 1) 캐스케이드 용량 입력")

    # 모델별 정격 용량 (kcal/h)
    NPW_CAP = 50_000      # NPW-48K(KD)
    NCB_CAP = 47_500      # NCB790-45LS
    NFB_CAP = 105_500     # NFB790-100LS

    col1, col2 = st.columns(2)
    with col1:
        npw_count = st.number_input("NPW-48K(KD) 대수", min_value=0, step=1, value=0)
        ncb_count = st.number_input("NCB790-45LS 대수", min_value=0, step=1, value=0)
        nfb_count = st.number_input("NFB790-100LS 대수", min_value=0, step=1, value=0)
    with col2:
        st.markdown(
            f"""
            - NPW-48K(KD): **{NPW_CAP:,.0f} kcal/h/대**  
            - NCB790-45LS: **{NCB_CAP:,.0f} kcal/h/대**  
            - NFB790-100LS: **{NFB_CAP:,.0f} kcal/h/대**
            """
        )

    cascade_capacity = (
        npw_count * NPW_CAP
        + ncb_count * NCB_CAP
        + nfb_count * NFB_CAP
    )

    st.markdown("### 2) 타 장비 합산 용량 입력")
    other_capacity = st.number_input(
        "타 장비 합산용량 (kcal/h)",
        min_value=0.0,
        step=10_000.0,
        format="%.0f",
        value=0.0,
    )

    THRESHOLD_AIR = 1_238_600  # 대기오염물질배출시설 기준(사용자 요청값)

    if st.button("대기오염물질배출시설 판별", key="air_judge"):
        total_capacity = cascade_capacity + other_capacity

        st.markdown("#### 🔎 계산 결과")

        st.write(
            f"- 캐스케이드 합산 용량: **{cascade_capacity:,.0f} kcal/h**"
        )
        st.write(
            f"- 타 장비 합산 용량: **{other_capacity:,.0f} kcal/h**"
        )
        st.write(
            f"- 총 합산 용량: **{total_capacity:,.0f} kcal/h**"
        )
        st.write(
            f"- 판정 기준: **{THRESHOLD_AIR:,.0f} kcal/h** 이상이면 대기오염물질배출시설"
        )

        if total_capacity > THRESHOLD_AIR:
            st.error(
                f"✅ 총 용량 **{total_capacity:,.0f} kcal/h** 이(가) "
                f"기준 **{THRESHOLD_AIR:,.0f} kcal/h** 을 **초과**하므로, "
                "**대기오염물질배출시설에 해당됩니다.**"
            )
        else:
            st.success(
                f"✅ 총 용량 **{total_capacity:,.0f} kcal/h** 이(가) "
                f"기준 **{THRESHOLD_AIR:,.0f} kcal/h** **이하**이므로, "
                "**대기오염물질배출시설에 해당되지 않습니다.**"
            )

        st.info(
            "※ 환경표지 인증을 받은 소형 보일러(0.1톤 미만 또는 61,900 kcal/h 미만)는 "
            "지자체에서 용량 산정 제외를 인정하는 경우 합산에서 빼고 입력해야 합니다."
        )

# -------------------------------------------------------------------
# 2. 특정가스사용시설 탭
# -------------------------------------------------------------------
with TAB2:
    st.subheader("특정가스사용시설 판별")

    st.markdown(
        """
**특정가스사용시설이란?**

1. 산업통상자원부장관이 정하는 기준에 따라 산정된 **월사용 예정량(Q)** 이  
   - 일반 시설: **2,000 m³ 이상**  
   - 제1종 보호시설: **1,000 m³ 이상**  
   인 가스사용시설

2. 또는 시·도지사가 안전관리를 위하여 필요하다고 인정하여 **지정한 시설**

---

### 월사용 예정량 산출식  
(도시가스사업법 시행규칙 【별표7】, 통합고시 제6장 4절 제6-4-2조)

\\[
Q = \\frac{(A \\times 240) + (B \\times 90)}{11{,}000}
\\]

- **Q** : 월사용 예정량 (m³)  
- **A** : *산업용* 연소기 가스소비량 합계 (kcal/h)  
- **B** : *산업용이 아닌* 연소기 가스소비량 합계 (kcal/h)
        """
    )

    st.markdown("### 1) 명판 소비량 입력")

    col1, col2 = st.columns(2)
    with col1:
        A = st.number_input(
            "A : 산업용 연소기 가스소비량 합계 (kcal/h)",
            min_value=0.0,
            step=10_000.0,
            format="%.0f",
            value=0.0,
        )
    with col2:
        B = st.number_input(
            "B : 산업용이 아닌 연소기 가스소비량 합계 (kcal/h)",
            min_value=0.0,
            step=10_000.0,
            format="%.0f",
            value=0.0,
        )

    st.markdown("### 2) 시설 유형 선택")
    facility_type = st.radio(
        "시설 유형을 선택하세요.",
        ["일반 시설", "제1종 보호시설"],
        horizontal=True,
    )

    if st.button("특정가스사용시설 판별", key="gas_judge"):
        # 월사용 예정량 계산
        Q_industrial = A * 240 / 11_000
        Q_general = B * 90 / 11_000
        Q_total = Q_industrial + Q_general

        threshold = 1_000 if facility_type == "제1종 보호시설" else 2_000

        st.markdown("#### 🔎 계산 결과")

        st.write(f"- 산업용 사용량: **{Q_industrial:,.1f} m³/월**")
        st.write(f"- 일반용 사용량: **{Q_general:,.1f} m³/월**")
        st.write(f"- 월사용 예정량 Q: **{Q_total:,.1f} m³/월**")
        st.write(
            f"- 적용 기준: **{facility_type} → {threshold:,.0f} m³/월 이상이면 특정가스사용시설**"
        )

        if Q_total >= threshold:
            st.error(
                f"✅ 월사용 예정량 **{Q_total:,.1f} m³/월** 이(가) "
                f"기준 **{threshold:,.0f} m³/월** 이상이므로, "
                "**특정가스사용시설에 해당됩니다.**"
            )
        else:
            st.success(
                f"✅ 월사용 예정량 **{Q_total:,.1f} m³/월** 이(가) "
                f"기준 **{threshold:,.0f} m³/월** 미만이므로, "
                "**특정가스사용시설에 해당되지 않습니다.**"
            )

    st.info(
        "※ 제1종 보호시설에는 학교·유치원·어린이집·병원·공중목욕탕·호텔 등, "
        "사람을 수용하는 건축물 중 일정 규모 이상 시설이 포함됩니다. "
        "실제 판정 시에는 해당 지자체 고시 및 개별 지정 여부를 함께 확인해야 합니다."
    )
