import os
os.system("pip install --disable-pip-version-check -q streamlit reportlab pillow openpyxl requests")

# -*- coding: utf-8 -*-
# 경동나비엔 가스보일러 설치/교체 시 제출서류(현장사진) - 모바일 최적화 (2x2 PDF, 페이지네이션)
# - 한글 폰트 자동 다운로드/임베드 (여러 미러 시도)
# - 폰트 임베드 실패 시 경고 문구 표시 안함(조용히 Helvetica로 폴백)

import io, re, unicodedata, uuid, os
from typing import List, Tuple, Optional
import streamlit as st
from PIL import Image, ImageOps

import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import reportlab.rl_config as rl_config

# ───────────────────────────────
# 페이지/헤더
# ───────────────────────────────
st.set_page_config(page_title="경동나비엔 가스보일러 설치/교체 시 제출서류(현장사진)", layout="wide")
st.markdown("""
    <h4 style='text-align:center; margin: 0.3rem 0; font-size: 1.1rem;'>
        경동나비엔 가스보일러 설치/교체 시 제출서류(현장사진)
    </h4>
    <hr style='border:1px solid #ddd; margin:0.5rem 0 1rem 0;'>
""", unsafe_allow_html=True)

# ───────────────────────────────
# 세션 초기화
# ───────────────────────────────
DEFAULT_OPTIONS = [
    "가스보일러 전면사진",
    "배기통(실내)",
    "배기통(실외)",
    "일산화탄소 경보기",
    "시공표지판",
    "명판",
    "플렉시블호스/가스밸브 사진",
    "직접입력",
]

if "photos" not in st.session_state:
    st.session_state.photos = [{
        "id": str(uuid.uuid4()),
        "choice": DEFAULT_OPTIONS[0],
        "custom": "",
        "checked": False,
        "img": None
    }]
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "add_pending" not in st.session_state:
    st.session_state.add_pending = False

if st.session_state.add_pending:
    st.session_state.photos.append({
        "id": str(uuid.uuid4()),
        "choice": DEFAULT_OPTIONS[0],
        "custom": "",
        "checked": False,
        "img": None
    })
    st.session_state.add_pending = False

# ───────────────────────────────
# 한글 폰트 자동 다운로드 + 등록 (무경고 폴백)
# ───────────────────────────────
# Streamlit Cloud(linux) 폰트 탐색 경로 보강
rl_config.TTFSearchPath.extend([
    ".", "./fonts", "/usr/share/fonts", "/usr/local/share/fonts", "/tmp"
])

FONT_CANDIDATE_LOCAL = [
    "./NanumGothic.ttf",
    "./fonts/NanumGothic.ttf",
    "C:/Windows/Fonts/malgun.ttf",       # 로컬 테스트용
    "C:\\Windows\\Fonts\\malgun.ttf",
]

FONT_MIRRORS = [
    # 나눔고딕 공식 릴리즈 (GitHub)
    "https://github.com/naver/nanumfont/releases/download/VER2.5/NanumGothic.ttf",
    # jsDelivr CDN 미러
    "https://cdn.jsdelivr.net/gh/naver/nanumfont@VER2.5/NanumGothic.ttf",
    # Naver 개발자센터(백업,  ttf 경로가 바뀌면 실패할 수 있음)
    "https://github.com/navermaps/NanumGothic/blob/master/NanumGothic.ttf?raw=1",
]

def ensure_font(path: str) -> str:
    """path에 폰트가 있으면 그대로, 없으면 여러 미러에서 다운로드 시도. 실패하면 '' 반환."""
    if os.path.exists(path):
        return path
    for url in FONT_MIRRORS:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if r.ok and len(r.content) > 100_000:  # 폰트 파일 최소 용량 체크
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(r.content)
                return path
        except Exception:
            pass
    return ""

def try_register_font() -> str:
    # 1) 로컬/동봉 폰트 우선
    for p in FONT_CANDIDATE_LOCAL:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("NanumGothic", p))
                registerFontFamily("NanumGothic", normal="NanumGothic", bold="NanumGothic",
                                   italic="NanumGothic", boldItalic="NanumGothic")
                return "NanumGothic"
            except Exception:
                pass

    # 2) 루트에 다운로드 시도
    dl = ensure_font("./NanumGothic.ttf")
    if dl:
        try:
            pdfmetrics.registerFont(TTFont("NanumGothic", dl))
            registerFontFamily("NanumGothic", normal="NanumGothic", bold="NanumGothic",
                               italic="NanumGothic", boldItalic="NanumGothic")
            return "NanumGothic"
        except Exception:
            pass

    # 3) 마지막 폴백(한글 미지원)
    return "Helvetica"

BASE_FONT = try_register_font()

ss = getSampleStyleSheet()
styles = {
    "title": ParagraphStyle(name="title", parent=ss["Heading1"], fontName=BASE_FONT, fontSize=16, alignment=1),
    "cell": ParagraphStyle(name="cell", parent=ss["Normal"], fontName=BASE_FONT, fontSize=9),
    "small_center": ParagraphStyle(name="small_center", parent=ss["Normal"], fontName=BASE_FONT, fontSize=9, alignment=1),
}

# ※ 요청에 따라 폰트 경고 표시 제거 (성공/실패 모두 조용히 동작)

# ───────────────────────────────
# 유틸
# ───────────────────────────────
def sanitize_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip().strip(".") or "output"

def normalize_orientation(img: Image.Image) -> Image.Image:
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img.convert("RGB")

def _pil_to_bytesio(img: Image.Image, quality=85) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    return buf

# ───────────────────────────────
# PDF 생성 (2x2 그리드, 페이지네이션)
# ───────────────────────────────
def build_pdf(doc_title: str, site_addr: str, items: List[Tuple[str, Optional[Image.Image]]]) -> bytes:
    """
    items: List of (label, PIL Image)
    - 한 페이지에 2x2(4장). 4장을 넘으면 자동으로 다음 페이지로 넘어감.
    - 이미지 캡션은 각 셀 하단에 표시.
    """
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4
    LEFT, RIGHT, TOP, BOTTOM = 20, 20, 20, 20
    content_w = PAGE_W - LEFT - RIGHT

    doc = SimpleDocTemplate(
        buf, pagesize=A4, title=doc_title,
        leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP, bottomMargin=BOTTOM
    )

    story = []
    # 제목
    story.append(Paragraph(doc_title, styles["title"]))
    story.append(Spacer(1, 8))

    # 현장 주소 표
    meta = Table(
        [[Paragraph("현장 주소", styles["cell"]), Paragraph(site_addr or "-", styles["cell"])]],
        colWidths=[70, content_w - 70]
    )
    meta.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta)
    story.append(Spacer(1, 10))

    # 2열 너비, 이미지 박스 크기
    cols = 2
    col_w = content_w / cols  # 각 셀 너비
    img_w = col_w - 10
    img_h = 240  # 크게 보이도록 고정 높이

    # 셀 생성 함수
    def _make_cell(label: str, img: Image.Image):
        bio = _pil_to_bytesio(normalize_orientation(img))
        rl_img = RLImage(bio, width=img_w, height=img_h)  # 고정 박스에 맞춰 확대/축소
        cell = Table(
            [[rl_img], [Paragraph(label, styles["small_center"])]],
            colWidths=[col_w - 10]
        )
        cell.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return cell

    # 4장씩 끊어서 페이지별 테이블 생성
    page_cells = []
    for label, img in items:
        page_cells.append(_make_cell(label, img))

    # 2x2로 재배열
    def chunk(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i+n]

    # 4개(2x2)씩 묶음
    for i, four in enumerate(chunk(page_cells, 4)):
        while len(four) < 4:
            empty = Table([[" "]], colWidths=[col_w - 10])
            empty.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 100)]))
            four.append(empty)
        rows = [four[0:2], four[2:4]]
        grid = Table(rows, colWidths=[col_w, col_w])
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(grid)
        if (i + 1) * 4 < len(page_cells):
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()

# ───────────────────────────────
# 입력 영역
# ───────────────────────────────
site_addr = st.text_input("현장 주소", "")
st.divider()

# ───────────────────────────────
# 한 줄 구성 UI (체크박스 | 항목 | 직접입력/사진)
# ───────────────────────────────
for p in st.session_state.photos:
    with st.container(border=True):
        col1, col2, col3 = st.columns([0.6, 2, 2])
        with col1:
            p["checked"] = st.checkbox("", key=f"chk_{p['id']}", value=p.get("checked", False))
        with col2:
            current_choice = p.get("choice", DEFAULT_OPTIONS[0])
            if current_choice not in DEFAULT_OPTIONS:
                current_choice = DEFAULT_OPTIONS[0]
            p["choice"] = st.selectbox("항목", DEFAULT_OPTIONS, key=f"choice_{p['id']}",
                                       index=DEFAULT_OPTIONS.index(current_choice), label_visibility="collapsed")
        with col3:
            if p["choice"] == "직접입력":
                p["custom"] = st.text_input("직접입력", p.get("custom", ""), key=f"custom_{p['id']}",
                                            label_visibility="collapsed", placeholder="항목 직접 입력")
            upload = st.file_uploader("사진", type=["jpg","jpeg","png"], key=f"up_{p['id']}",
                                      label_visibility="collapsed")
            if upload:
                p["img"] = normalize_orientation(Image.open(upload))
            if p["img"]:
                st.image(p["img"], use_container_width=True, caption=p["custom"] or p["choice"], clamp=True)

st.divider()

# ───────────────────────────────
# 버튼 영역
# ───────────────────────────────
b1, b2, b3 = st.columns([1,1,2])
with b1:
    if st.button("➕ 추가", use_container_width=True):
        st.session_state.add_pending = True
        st.rerun()
with b2:
    if st.button("🗑 삭제", use_container_width=True):
        st.session_state.photos = [x for x in st.session_state.photos if not x["checked"]]
        st.rerun()
with b3:
    if st.button("📄 PDF 생성 (2×2)", type="primary", use_container_width=True):
        valid = []
        for p in st.session_state.photos:
            if p.get("img"):
                label = p["custom"].strip() if (p["choice"] == "직접입력" and p.get("custom")) else p["choice"]
                valid.append((label, p["img"]))
        if not valid:
            st.warning("📸 사진이 등록된 항목이 없습니다.")
        else:
            st.session_state.pdf_bytes = build_pdf(
                "경동나비엔 가스보일러 설치/교체 시 제출서류(현장사진)",
                site_addr,
                valid
            )
            st.rerun()

# ───────────────────────────────
# 다운로드
# ───────────────────────────────
if st.session_state.pdf_bytes:
    fname = f"{sanitize_filename(site_addr)}_현장사진_2x2.pdf"
    st.success("✅ PDF 생성 완료! 아래 버튼으로 다운로드하세요.")
    st.download_button("⬇️ PDF 다운로드", st.session_state.pdf_bytes,
                       file_name=fname, mime="application/pdf", use_container_width=True)
