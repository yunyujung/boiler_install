# -*- coding: utf-8 -*-
# 경동나비엔 가스보일러 설치, 교체시 제출서류(현장사진)
# - 주소 입력을 "기본 주소" + "상세 주소"로 분리
# - PDF에는 두 칸을 합쳐서 설치장소(주소)로 표기
# - 나머지는 동일 (2x2로 4장/페이지, 초과 시 자동으로 다음 페이지)

import io, re, unicodedata, os
from typing import List, Tuple
import streamlit as st
from PIL import Image, ImageOps

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    Image as RLImage,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

APP_TITLE = "경동나비엔 가스보일러 설치, 교체시 제출서류(현장사진)"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# ───────────────────────────────
# 세션 초기화
# ───────────────────────────────
DEFAULT_ITEMS = [
    "전면사진",
    "배기통(실내)",
    "배기통(실외)",
    "일산화탄소 경보기",
    "시공표지판",
    "명판",
    "플랙시블호스/ 가스밸브 사진",
    "계량기 사진",
]

if "photos" not in st.session_state:
    st.session_state.photos = [{"label": label, "img": None} for label in DEFAULT_ITEMS]

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

# 주소 2단 입력 칸 세션 값 초기화
if "install_addr_main" not in st.session_state:
    st.session_state.install_addr_main = ""
if "install_addr_detail" not in st.session_state:
    st.session_state.install_addr_detail = ""


# ───────────────────────────────
# 폰트 등록 (한글 PDF용)
# ───────────────────────────────
def try_register_font():
    candidates = [
        ("NanumGothic", "NanumGothic.ttf"),
        ("MalgunGothic", "C:\\Windows\\Fonts\\malgun.ttf"),
        ("MalgunGothic", "C:/Windows/Fonts/malgun.ttf"),
    ]
    for name, path in candidates:
        try:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                return name, True
        except Exception:
            pass
    return "Helvetica", False

BASE_FONT, _ = try_register_font()
ss = getSampleStyleSheet()
styles = {
    "title": ParagraphStyle(
        name="title",
        parent=ss["Heading1"],
        fontName=BASE_FONT,
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=8,
    ),
    "cell": ParagraphStyle(
        name="cell",
        parent=ss["Normal"],
        fontName=BASE_FONT,
        fontSize=10,
        leading=13,
    ),
    "small_center": ParagraphStyle(
        name="small_center",
        parent=ss["Normal"],
        fontName=BASE_FONT,
        fontSize=9,
        leading=11,
        alignment=1,
    ),
}

# ───────────────────────────────
# 유틸
# ───────────────────────────────
def sanitize_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip().strip(".") or "output"

def normalize_orientation(img: Image.Image) -> Image.Image:
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img.convert("RGB")

def pad_to_ratio(img: Image.Image, target_ratio: float = 4/3) -> Image.Image:
    w, h = img.size
    cur_ratio = w / h
    if abs(cur_ratio - target_ratio) < 1e-3:
        return img

    if cur_ratio > target_ratio:
        # 가로가 더 긴 경우 -> 세로 캔버스 늘림
        new_h = int(round(w / target_ratio))
        new_w = w
    else:
        # 세로가 더 긴 경우 -> 가로 캔버스 늘림
        new_w = int(round(h * target_ratio))
        new_h = h

    from PIL import Image as PILImage
    canvas = PILImage.new("RGB", (new_w, new_h), (255, 255, 255))
    canvas.paste(img, ((new_w - w)//2, (new_h - h)//2))
    return canvas

def _pil_to_bytesio(img: Image.Image, quality=85) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    return buf


# ───────────────────────────────
# PDF 생성 (2x2 레이아웃, 여러 페이지)
#   header_title: 문서 제목
#   addr_full: install_addr_main + " " + install_addr_detail
#   photos: [(label, img), ...]
#
# 첫 페이지:
#   - 제목
#   - 설치장소(주소) 표
#   - 첫 4장(2x2)
# 이후 페이지는
#   - 나머지 4장씩(2x2)
# ───────────────────────────────
def build_pdf(header_title: str,
              addr_full: str,
              photos: List[Tuple[str, Image.Image]]) -> bytes:

    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN = 20

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        title=header_title,
    )

    story = []

    # 제목
    story.append(Paragraph(header_title, styles["title"]))
    story.append(Spacer(1, 4))

    # 주소 표 (1행)
    meta_tbl = Table(
        [
            [
                Paragraph("설치장소(주소)", styles["cell"]),
                Paragraph(addr_full.strip() or "-", styles["cell"]),
            ]
        ],
        colWidths=[110, PAGE_W - 2*MARGIN - 110],
    )
    meta_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(meta_tbl)
    story.append(Spacer(1, 10))

    # 2x2 레이아웃 설정
    usable_width = PAGE_W - 2 * MARGIN
    col_width = usable_width / 2.0  # 2열

    CELL_TOTAL_H = 320        # 셀 높이
    CAPTION_H = 28            # 캡션 영역
    IMAGE_MAX_H = CELL_TOTAL_H - CAPTION_H - 8
    IMAGE_MAX_W = col_width - 8

    # 4장씩 끊기
    chunks = [photos[i:i+4] for i in range(0, len(photos), 4)]

    for ci, chunk in enumerate(chunks):
        # 첫 chunk는 이미 제목/주소 뒤에서 시작
        # 두 번째 chunk부터는 페이지 나누기 + (주소표 없이 바로 사진)
        if ci > 0:
            story.append(PageBreak())

        # 셀 테이블들 준비
        cell_tables = []
        for (label, pil_img) in chunk:
            fixed = normalize_orientation(pil_img)
            fixed = pad_to_ratio(fixed, target_ratio=4/3)

            bio = _pil_to_bytesio(fixed)
            rl_img = RLImage(bio, width=IMAGE_MAX_W, height=IMAGE_MAX_H)

            cell_tbl = Table(
                [
                    [rl_img],
                    [Paragraph(label, styles["small_center"])],
                ],
                colWidths=[col_width],
                rowHeights=[CELL_TOTAL_H - CAPTION_H, CAPTION_H],
            )
            cell_tbl.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
                        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )
            cell_tables.append(cell_tbl)

        # 만약 마지막 페이지가 1~3장만 있다면 빈 칸으로 채워서 레이아웃 유지
        while len(cell_tables) < 4:
            empty_tbl = Table(
                [
                    [Paragraph("", styles["small_center"])],
                    [Paragraph("", styles["small_center"])],
                ],
                colWidths=[col_width],
                rowHeights=[CELL_TOTAL_H - CAPTION_H, CAPTION_H],
            )
            empty_tbl.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
                        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )
            cell_tables.append(empty_tbl)

        # 2x2로 묶어서 큰 표 하나 만들기
        grid_tbl = Table(
            [
                [cell_tables[0], cell_tables[1]],
                [cell_tables[2], cell_tables[3]],
            ],
            colWidths=[col_width, col_width],
            rowHeights=[CELL_TOTAL_H, CELL_TOTAL_H],
        )
        grid_tbl.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        story.append(grid_tbl)

    doc.build(story)
    return buf.getvalue()


# ───────────────────────────────
# 화면 UI
# ───────────────────────────────
st.markdown(f"### {APP_TITLE}")

col_main, col_detail = st.columns(2)
with col_main:
    st.session_state.install_addr_main = st.text_input(
        "주소 (기본)",
        value=st.session_state.install_addr_main,
        placeholder="예: 서울특별시 강서구 마곡동 123-4",
        key="install_addr_main_input",
    )
with col_detail:
    st.session_state.install_addr_detail = st.text_input(
        "상세 주소",
        value=st.session_state.install_addr_detail,
        placeholder="예: 302동 1203호 보일러실",
        key="install_addr_detail_input",
    )

st.divider()
st.markdown("#### 현장사진 업로드 (각 항목별로 사진을 등록하세요)")

for idx, p in enumerate(st.session_state.photos):
    block = st.container(border=True)
    with block:
        st.markdown(f"**{p['label']}**")
        upload = st.file_uploader(
            "사진 등록",
            type=["jpg", "jpeg", "png"],
            key=f"up_{idx}",
        )
        if upload:
            from PIL import Image as PILImage
            original = PILImage.open(upload)
            st.session_state.photos[idx]["img"] = normalize_orientation(original)

        if st.session_state.photos[idx]["img"]:
            st.image(st.session_state.photos[idx]["img"], use_container_width=True)

st.divider()

left_btn, right_dummy = st.columns([1, 3])
download_area = st.empty()

with left_btn:
    if st.button("📄 PDF 생성", type="primary", use_container_width=True):
        # 업로드된 사진만 모아서 (순서는 DEFAULT_ITEMS 순서대로)
        valid_photos = []
        for item in st.session_state.photos:
            if item["img"] is not None:
                valid_photos.append((item["label"], item["img"]))

        if not valid_photos:
            st.warning("📸 업로드된 사진이 없습니다.")
        else:
            full_addr = (
                st.session_state.get("install_addr_main", "").strip()
                + " "
                + st.session_state.get("install_addr_detail", "").strip()
            ).strip()

            pdf_bytes = build_pdf(
                APP_TITLE,
                full_addr,
                valid_photos
            )
            st.session_state.pdf_bytes = pdf_bytes

if st.session_state.pdf_bytes:
    # 파일명은 기본주소만 사용 (너무 길어지는 것 방지)
    fname = f"{sanitize_filename(st.session_state.get('install_addr_main',''))}_현장사진제출서류.pdf"
    with download_area.container():
        st.success("✅ PDF 생성 완료! 아래 버튼으로 바로 다운로드하세요.")
        st.download_button(
            "⬇️ PDF 다운로드",
            st.session_state.pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            key="dl_pdf",
            use_container_width=True,
        )
