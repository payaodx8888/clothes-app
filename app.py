import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from google import genai
from PIL import Image
from pydantic import BaseModel
import io
import datetime
import uuid
import time
import base64
import html
import hashlib

try:
    from streamlit_paste_button import paste_image_button
    HAS_PASTE_BTN = True
except Exception:
    HAS_PASTE_BTN = False

# ==========================================
# 設定エリア
# ==========================================
_K1 = "AQ.Ab8RN6IHJDmDYNheq3LAZyIO"
_K2 = "qxY6KwNa5ouLQGFCnb7uLjxAlQ"
GEMINI_API_KEY = _K1 + _K2
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

SPREADSHEET_NAME = "洋服管理_DB"

EXPECTED_HEADERS = [
    "アイテムID", "ブランド", "アイテム名", "カテゴリ",
    "色", "表記サイズ", "着丈", "身幅", "肩幅", "袖丈",
    "ウエスト", "股下", "ヒップ", "わたり幅",
    "メイン画像URL", "サブ画像URL", "登録日", "メモ"
]

st.set_page_config(
    page_title="WARDROBE",
    layout="wide",
    initial_sidebar_state="collapsed"
)

CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 1.0rem !important;
    padding-bottom: 2rem !important;
    max-width: 920px !important;
}
.app-header {
    display: flex;
    align-items: baseline;
    gap: 10px;
    border-bottom: 1px solid rgba(128,128,128,0.25);
    padding-bottom: 6px;
    margin-bottom: 8px;
}
.app-title {
    font-size: 1.2rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    margin: 0;
}
.app-sub {
    font-size: 0.68rem;
    opacity: 0.55;
    letter-spacing: 0.08em;
}
.spec-card {
    display: flex;
    gap: 12px;
    padding: 10px;
    border: 1px solid rgba(128,128,128,0.24);
    border-radius: 10px 10px 4px 4px;
    margin-bottom: 2px;
    background: rgba(128,128,128,0.03);
    align-items: center;
}
.spec-thumb {
    width: 66px;
    height: 66px;
    border-radius: 8px;
    object-fit: cover;
    flex-shrink: 0;
    background: rgba(128,128,128,0.1);
}
.spec-body {
    flex: 1;
    min-width: 0;
}
.spec-top {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 3px;
}
.sz-badge {
    background: #111;
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 5px;
    letter-spacing: 0.03em;
}
.brand-txt {
    font-size: 0.78rem;
    font-weight: 700;
    opacity: 0.85;
}
.item-txt {
    font-size: 0.82rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
}
.color-txt {
    font-size: 0.72rem;
    opacity: 0.65;
}
.metrics-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
}
.m-pill {
    font-size: 0.72rem;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(128,128,128,0.12);
    font-weight: 500;
}
.m-pill b {
    font-weight: 700;
}
.memo-preview {
    margin-top: 5px;
    font-size: 0.73rem;
    color: inherit;
    opacity: 0.82;
    background: rgba(255, 193, 7, 0.12);
    border-left: 3px solid #f59e0b;
    padding: 3px 7px;
    border-radius: 3px;
    white-space: pre-wrap;
}
.closet-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}
@media (min-width: 768px) {
    .closet-grid {
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
    }
}
.closet-card {
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 10px;
    overflow: hidden;
    background: rgba(128,128,128,0.02);
}
.closet-img-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 1 / 1;
    background: rgba(128,128,128,0.08);
}
.closet-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}
.closet-badge {
    position: absolute;
    top: 6px;
    left: 6px;
    background: rgba(0,0,0,0.75);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
}
.closet-sub-cnt {
    position: absolute;
    bottom: 6px;
    right: 6px;
    background: rgba(0,0,0,0.65);
    color: #fff;
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 4px;
}
.closet-info {
    padding: 8px;
}
.closet-b {
    font-size: 0.7rem;
    font-weight: 700;
    opacity: 0.65;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.closet-n {
    font-size: 0.78rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 3px;
}
.closet-m {
    font-size: 0.68rem;
    opacity: 0.75;
    line-height: 1.35;
}
.closet-memo {
    font-size: 0.68rem;
    opacity: 0.85;
    margin-top: 3px;
    padding-top: 3px;
    border-top: 1px dashed rgba(128,128,128,0.25);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
<div class="app-header">
  <p class="app-title">WARDROBE</p>
  <span class="app-sub">ARCHIVE & SIZING</span>
</div>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

class ClothInfo(BaseModel):
    brand: str = ""
    item_name: str = ""
    category: str = "トップス"
    color: str = ""
    detected_size_label: str = ""
    length: float = 0.0
    width: float = 0.0
    shoulder: float = 0.0
    sleeve: float = 0.0
    waist: float = 0.0
    inseam: float = 0.0
    hip: float = 0.0
    thigh: float = 0.0
    crop_image_index: int = 0
    crop_ymin: int = 0
    crop_xmin: int = 0
    crop_ymax: int = 1000
    crop_xmax: int = 1000

def prepare_image_for_ai(img: Image.Image) -> Image.Image:
    w, h = img.size
    max_w, max_h = 1400, 3200
    ratio = min(max_w / w, max_h / h, 1.0)
    if ratio < 1.0:
        new_size = (int(w * ratio), int(h * ratio))
        return img.resize(
            new_size,
            Image.Resampling.LANCZOS
        )
    return img

def encode_img_for_sheet(
    pil_img: Image.Image, max_chars: int = 44000
) -> str:
    for dim in [550, 440, 340, 260, 200]:
        for q in [80, 68, 55, 45]:
            w, h = pil_img.size
            r = min(dim / w, dim / h, 1.0)
            resized = pil_img.resize(
                (int(w * r), int(h * r)),
                Image.Resampling.LANCZOS
            )
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=q)
            b64 = base64.b64encode(
                buf.getvalue()
            ).decode("utf-8")
            if len(b64) <= max_chars:
                return f"B64:{b64}"
    return ""

def decode_str_to_pil(val: str):
    s = str(val).strip()
    if s.startswith("B64:"):
        try:
            raw = base64.b64decode(s[4:])
            return Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            return None
    return None

def get_img_src(val: str) -> str:
    s = str(val).strip()
    if s.startswith("B64:"):
        return f"data:image/jpeg;base64,{s[4:]}"
    if s.startswith("http"):
        return s
    return ""

def show_saved_image(val: str, caption: str = ""):
    s = str(val).strip()
    if not s:
        return
    try:
        if s.startswith("B64:"):
            raw = base64.b64decode(s[4:])
            st.image(
                raw,
                caption=caption if caption else None,
                use_container_width=True
            )
        elif s.startswith("http"):
            st.image(
                s,
                caption=caption if caption else None,
                use_container_width=True
            )
    except Exception:
        pass

def fmt_num(v) -> str:
    try:
        f = float(v)
        if f <= 0:
            return ""
        return str(int(f)) if f.is_integer() else str(f)
    except Exception:
        return ""

def pack_images_for_row(img_list):
    if not img_list:
        return "", ""
    main_data = encode_img_for_sheet(
        img_list[0], max_chars=44000
    )
    sub_list = []
    sub_imgs = img_list[1:6]
    if sub_imgs:
        per_sub = int(43000 / len(sub_imgs))
        for s_img in sub_imgs:
            enc = encode_img_for_sheet(
                s_img, max_chars=per_sub
            )
            if enc:
                sub_list.append(enc)
    return main_data, ",".join(sub_list)

@st.cache_resource
def init_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    c_info = dict(st.secrets["gcp_service_account"])
    creds = (
        service_account.Credentials
        .from_service_account_info(c_info, scopes=scopes)
    )
    return gspread.authorize(creds)

try:
    gc = init_google_sheet()
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.sheet1
    current_headers = worksheet.row_values(1)
    if current_headers != EXPECTED_HEADERS:
        worksheet.update(
            range_name="A1:R1",
            values=[EXPECTED_HEADERS]
        )
except Exception as e:
    st.error(f"Google連携エラー: {e}")
    st.stop()

def save_memo_quickly(item_id: str, new_memo: str):
    id_col = worksheet.col_values(1)
    if item_id in id_col:
        row_num = id_col.index(item_id) + 1
        worksheet.update_cell(row_num, 18, new_memo)
        return True
    return False

if "staged_images" not in st.session_state:
    st.session_state.staged_images = []
if "edit_staged_images" not in st.session_state:
    st.session_state.edit_staged_images = []
if "processed_hashes_t3" not in st.session_state:
    st.session_state.processed_hashes_t3 = set()
if "processed_hashes_t4" not in st.session_state:
    st.session_state.processed_hashes_t4 = set()
if "up_key_t3" not in st.session_state:
    st.session_state.up_key_t3 = 0
if "up_key_t4" not in st.session_state:
    st.session_state.up_key_t4 = 0

default_form_values = {
    "f_brand": "",
    "f_item_name": "",
    "f_category": "トップス",
    "f_color": "",
    "f_size_label": "",
    "f_length": 0.0,
    "f_width": 0.0,
    "f_shoulder": 0.0,
    "f_sleeve": 0.0,
    "f_waist": 0.0,
    "f_inseam": 0.0,
    "f_hip": 0.0,
    "f_thigh": 0.0,
    "f_memo": ""
}
for k, v in default_form_values.items():
    if k not in st.session_state:
        st.session_state[k] = v

tab1, tab2, tab3, tab4 = st.tabs([
    "📏 サイズ比較",
    "🖼️ クローゼット",
    "➕ 登録",
    "✏️ 編集"
])

records = worksheet.get_all_records()
df = pd.DataFrame(records)

# ==========================================
# タブ1：サイズ比較
# ==========================================
with tab1:
    if not df.empty:
        fc1, fc2 = st.columns([2, 1])
        with fc1:
            sel_cat = st.radio(
                "カテゴリ",
                ["ALL", "トップス", "アウター", "ボトムス", "その他"],
                horizontal=True,
                label_visibility="collapsed",
                key="t1_cat_radio"
            )
        with fc2:
            view_mode = st.selectbox(
                "表示切替",
                ["📱 カード", "📊 表"],
                label_visibility="collapsed",
                key="t1_view_mode"
            )

        df_f = (
            df[df["カテゴリ"] == sel_cat]
            if sel_cat != "ALL"
            else df
        )

        if "📱" in view_mode:
            m_keys = [
                ("ウエスト", "W"),
                ("股下", "股下"),
                ("わたり幅", "わたり"),
                ("ヒップ", "H"),
                ("着丈", "着丈"),
                ("身幅", "身幅"),
                ("肩幅", "肩幅"),
                ("袖丈", "袖丈")
            ]
            for idx, r in df_f.iterrows():
                iid = str(r.get("アイテムID", f"row_{idx}"))
                m_raw = str(r.get("メイン画像URL", "")).strip()
                s_raw = str(r.get("サブ画像URL", "")).strip()
                sub_list = [
                    x.strip() for x in s_raw.split(",")
                    if x.strip()
                ]
                total_imgs = (1 if m_raw else 0) + len(sub_list)

                src = get_img_src(m_raw)
                img_tag = (
                    f'<img src="{src}" class="spec-thumb">'
                    if src
                    else '<div class="spec-thumb"></div>'
                )

                sz = html.escape(
                    str(r.get("表記サイズ") or "-")
                )
                br = html.escape(
                    str(r.get("ブランド") or "")
                )
                nm = html.escape(
                    str(r.get("アイテム名") or "")
                )
                cl = html.escape(str(r.get("色") or ""))
                cl_str = f"({cl})" if cl else ""
                cur_memo = str(r.get("メモ") or "").strip()

                pills = []
                for col_k, short_k in m_keys:
                    val_s = fmt_num(r.get(col_k, 0))
                    if val_s:
                        pills.append(
                            f'<span class="m-pill">'
                            f'{short_k} <b>{val_s}</b></span>'
                        )
                pills_html = "".join(pills)

                memo_html = (
                    f'<div class="memo-preview">'
                    f'📝 {html.escape(cur_memo)}</div>'
                    if cur_memo
                    else ""
                )

                card_html = (
                    f'<div class="spec-card">{img_tag}'
                    f'<div class="spec-body">'
                    f'<div class="spec-top">'
                    f'<span class="sz-badge">{sz}</span>'
                    f'<span class="brand-txt">{br}</span>'
                    f'<span class="color-txt">{cl_str}</span>'
                    f'</div>'
                    f'<div class="item-txt">{nm}</div>'
                    f'<div class="metrics-wrap">'
                    f'{pills_html}</div>'
                    f'{memo_html}'
                    f'</div></div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                with st.expander(
                    f"📸 写真({total_imgs})・メモ"
                ):
                    all_img_strs = []
                    if m_raw:
                        all_img_strs.append(("メイン", m_raw))
                    for s_i, s_u in enumerate(sub_list):
                        all_img_strs.append(
                            (f"サブ #{s_i+1}", s_u)
                        )

                    if all_img_strs:
                        img_cols = st.columns(2)
                        for p_i, (cap_t, u_str) in enumerate(
                            all_img_strs
                        ):
                            with img_cols[p_i % 2]:
                                show_saved_image(u_str, cap_t)

                    new_memo_val = st.text_area(
                        "📝 メモ",
                        value=cur_memo,
                        height=68,
                        label_visibility="collapsed",
                        placeholder="メモを入力...",
                        key=f"t1_memo_in_{iid}_{idx}"
                    )
                    if st.button(
                        "💾 メモ保存",
                        key=f"t1_memo_btn_{iid}_{idx}",
                        type="primary"
                    ):
                        if save_memo_quickly(iid, new_memo_val):
                            st.toast("保存しました", icon="📝")
                            time.sleep(0.4)
                            st.rerun()
        else:
            if sel_cat == "ボトムス":
                t_cols = [
                    "表記サイズ", "アイテム名", "ブランド",
                    "色", "ウエスト", "股下", "わたり幅",
                    "ヒップ", "着丈", "メモ"
                ]
            elif sel_cat in ["トップス", "アウター"]:
                t_cols = [
                    "表記サイズ", "アイテム名", "ブランド",
                    "色", "着丈", "身幅", "肩幅", "袖丈", "メモ"
                ]
            else:
                t_cols = [
                    "表記サイズ", "アイテム名", "ブランド",
                    "色", "着丈", "身幅", "肩幅", "袖丈",
                    "ウエスト", "股下", "わたり幅",
                    "ヒップ", "メモ"
                ]
            disp_cols = [
                c for c in t_cols if c in df_f.columns
            ]
            df_show = df_f[disp_cols].rename(
                columns={
                    "表記サイズ": "サイズ",
                    "わたり幅": "わたり"
                }
            )
            st.dataframe(
                df_show,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("データがありません。")

# ==========================================
# タブ2：クローゼット
# ==========================================
with tab2:
    if not df.empty:
        c_cat = st.radio(
            "絞り込み",
            ["ALL", "トップス", "アウター", "ボトムス", "その他"],
            horizontal=True,
            label_visibility="collapsed",
            key="t2_cat_radio"
        )
        df_c = (
            df[df["カテゴリ"] == c_cat]
            if c_cat != "ALL"
            else df
        )

        grid_items = ['<div class="closet-grid">']
        for _, r in df_c.iterrows():
            m_raw = str(r.get("メイン画像URL", "")).strip()
            s_raw = str(r.get("サブ画像URL", "")).strip()
            s_cnt = len([
                x for x in s_raw.split(",") if x.strip()
            ])
            src = get_img_src(m_raw)
            img_el = (
                f'<img src="{src}" class="closet-img">'
                if src
                else '<div class="closet-img"></div>'
            )
            sub_badge = (
                f'<span class="closet-sub-cnt">+{s_cnt}</span>'
                if s_cnt > 0
                else ""
            )
            sz = html.escape(
                str(r.get("表記サイズ") or "-")
            )
            br = html.escape(str(r.get("ブランド") or ""))
            nm = html.escape(str(r.get("アイテム名") or ""))
            cl = html.escape(str(r.get("色") or ""))
            b_line = f"{br} / {cl}" if cl else br

            m_parts = []
            for k, lbl in [
                ("着丈", "丈"), ("身幅", "幅"),
                ("ウエスト", "W"), ("股下", "股")
            ]:
                v = fmt_num(r.get(k, 0))
                if v:
                    m_parts.append(f"{lbl}{v}")
            m_line = " ".join(m_parts)

            memo_tx = str(r.get("メモ") or "").strip()
            memo_div = (
                f'<div class="closet-memo">'
                f'📝 {html.escape(memo_tx)}</div>'
                if memo_tx
                else ""
            )

            item_html = (
                f'<div class="closet-card">'
                f'<div class="closet-img-wrap">{img_el}'
                f'<span class="closet-badge">{sz}</span>'
                f'{sub_badge}</div>'
                f'<div class="closet-info">'
                f'<div class="closet-b">{b_line}</div>'
                f'<div class="closet-n">{nm}</div>'
                f'<div class="closet-m">{m_line}</div>'
                f'{memo_div}'
                f'</div></div>'
            )
            grid_items.append(item_html)
        grid_items.append("</div>")
        st.markdown(
            "".join(grid_items),
            unsafe_allow_html=True
        )
    else:
        st.info("データがありません。")

# ==========================================
# タブ3：新規アイテム登録（案A：アルバム選択＋PCワンクリック貼付）
# ==========================================
with tab3:
    reg_files = st.file_uploader(
        "📁 アルバム・ファイルから選択",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=f"t3_up_{st.session_state.up_key_t3}"
    )
    if reg_files:
        for rf in reg_files:
            raw_b = rf.getvalue()
            h_val = hashlib.md5(raw_b).hexdigest()
            if h_val not in st.session_state.processed_hashes_t3:
                st.session_state.processed_hashes_t3.add(h_val)
                st.session_state.staged_images.append(
                    Image.open(io.BytesIO(raw_b)).convert("RGB")
                )

    bar1, bar2, bar3, bar4 = st.columns([1.2, 1.1, 1.5, 0.8])
    with bar1:
        if HAS_PASTE_BTN:
            p_res = paste_image_button(
                label="📋 スクショ貼付",
                background_color="#2563eb",
                hover_background_color="#1d4ed8",
                key=f"t3_paste_{st.session_state.up_key_t3}"
            )
            if p_res.image_data is not None:
                b_io = io.BytesIO()
                p_res.image_data.save(b_io, format="PNG")
                p_hash = hashlib.md5(
                    b_io.getvalue()
                ).hexdigest()
                if p_hash not in st.session_state.processed_hashes_t3:
                    st.session_state.processed_hashes_t3.add(p_hash)
                    st.session_state.staged_images.append(
                        p_res.image_data.convert("RGB")
                    )
        else:
            st.button(
                "📋 貼付(要Reboot)",
                disabled=True,
                use_container_width=True,
                key="t3_paste_disabled"
            )
    with bar2:
        target_size = st.text_input(
            "サイズ指定",
            value="",
            placeholder="サイズ指定(任意)",
            label_visibility="collapsed",
            key="t3_target_size"
        )
    with bar3:
        run_ai = st.button(
            "🪄 AI自動入力",
            type="primary",
            use_container_width=True,
            key="t3_btn_run_ai"
        )
    with bar4:
        if st.button(
            "🗑️ クリア",
            use_container_width=True,
            key="t3_btn_clear"
        ):
            st.session_state.staged_images = []
            st.session_state.processed_hashes_t3 = set()
            st.session_state.up_key_t3 += 1
            st.rerun()

    with st.expander("⚙️ AI詳細設定"):
        ac1, ac2 = st.columns(2)
        ai_model = ac1.selectbox(
            "モデル",
            ["gemini-3.8-flash", "gemini-3.8-pro"],
            key="t3_ai_model"
        )
        auto_crop = ac2.checkbox(
            "✂️ 服の写真だけ自動切り抜き",
            value=True,
            key="t3_auto_crop"
        )

    if run_ai:
        if st.session_state.staged_images:
            with st.spinner("AI解析中..."):
                try:
                    client = genai.Client(
                        api_key=GEMINI_API_KEY
                    )
                    ai_imgs = [
                        prepare_image_for_ai(img)
                        for img in st.session_state.staged_images
                    ]
                    s_cond = (
                        f"サイズ「{target_size}」の数値を抽出。"
                        if target_size.strip()
                        else "代表サイズ（88, 34, L等）を抽出し"
                             " detected_size_label に入れる。"
                    )
                    prompt = (
                        "通販スクショから以下を抽出してください。\n"
                        "1. brand, item_name, category"
                        "（トップス/アウター/ボトムス/その他）\n"
                        "2. color：文字表記を最優先、なければ"
                        "写真の見た目から色名を判断。\n"
                        f"3. {s_cond}\n"
                        "4. サイズルール：88や34等の数値は"
                        "勝手にL等に変えず数値のままにする。"
                        "XXLや2Lは2XLに、XXXLや3Lは3XLに統一。\n"
                        "5. 採寸(cm)：length, width, shoulder,"
                        " sleeve, waist, inseam, hip, thigh。"
                        "該当なしは0。\n"
                        "6. 写真切り抜き：メインの服の大きな写真が"
                        "ある画像番号(0始まり)をcrop_image_indexに、"
                        "文字や余白やUIを除いた服の写真枠のみの"
                        "座標(0〜1000)をcrop_ymin, crop_xmin,"
                        " crop_ymax, crop_xmaxに指定。"
                    )
                    contents = ai_imgs + [prompt]

                    response = None
                    for attempt in range(3):
                        try:
                            cfg = genai.types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=ClothInfo,
                            )
                            response = (
                                client.models.generate_content(
                                    model=ai_model,
                                    contents=contents,
                                    config=cfg,
                                )
                            )
                            break
                        except Exception as req_err:
                            if "503" in str(req_err) and attempt < 2:
                                time.sleep(2)
                                continue
                            raise req_err

                    result = ClothInfo.model_validate_json(
                        response.text
                    )
                    f_size = (
                        result.detected_size_label.strip().upper()
                    )
                    if f_size in ["XXL", "2L"]:
                        f_size = "2XL"
                    elif f_size in ["XXXL", "3L"]:
                        f_size = "3XL"
                    if target_size.strip() and not f_size:
                        f_size = target_size.strip().upper()
                        if f_size in ["XXL", "2L"]:
                            f_size = "2XL"

                    st.session_state.f_brand = result.brand
                    st.session_state.f_item_name = result.item_name
                    valid_cats = [
                        "トップス", "アウター",
                        "ボトムス", "その他"
                    ]
                    if result.category in valid_cats:
                        st.session_state.f_category = (
                            result.category
                        )
                    st.session_state.f_color = result.color
                    st.session_state.f_size_label = f_size
                    st.session_state.f_length = float(result.length)
                    st.session_state.f_width = float(result.width)
                    st.session_state.f_shoulder = float(
                        result.shoulder
                    )
                    st.session_state.f_sleeve = float(result.sleeve)
                    st.session_state.f_waist = float(result.waist)
                    st.session_state.f_inseam = float(result.inseam)
                    st.session_state.f_hip = float(result.hip)
                    st.session_state.f_thigh = float(result.thigh)

                    if (
                        auto_crop
                        and result.crop_ymax > result.crop_ymin
                        and result.crop_xmax > result.crop_xmin
                    ):
                        t_idx = result.crop_image_index
                        max_i = len(st.session_state.staged_images)
                        if t_idx < 0 or t_idx >= max_i:
                            t_idx = 0
                        base_img = (
                            st.session_state.staged_images[t_idx]
                        )
                        w, h = base_img.size
                        ymin = max(0, min(1000, result.crop_ymin))
                        xmin = max(0, min(1000, result.crop_xmin))
                        ymax = max(0, min(1000, result.crop_ymax))
                        xmax = max(0, min(1000, result.crop_xmax))
                        area = (
                            (ymax - ymin) * (xmax - xmin)
                        ) / 1000000.0
                        if 0.03 < area < 0.95:
                            left = int(xmin * w / 1000)
                            top = int(ymin * h / 1000)
                            right = int(xmax * w / 1000)
                            bottom = int(ymax * h / 1000)
                            cropped = base_img.crop(
                                (left, top, right, bottom)
                            )
                            st.session_state.staged_images.insert(
                                0, cropped
                            )
                    st.rerun()
                except Exception as e:
                    st.error(f"AIエラー: {e}")
        else:
            st.warning("先に画像を追加してください。")

    images_to_save = []
    if st.session_state.staged_images:
        p_cols = st.columns(4)
        for idx, img in enumerate(
            st.session_state.staged_images
        ):
            with p_cols[idx % 4]:
                st.image(img, use_container_width=True)
                def_chk = True if idx == 0 else False
                lbl = "メイン保存" if idx == 0 else f"保存 #{idx+1}"
                if st.checkbox(
                    lbl,
                    value=def_chk,
                    key=f"t3_save_img_{idx}"
                ):
                    images_to_save.append(img)

    with st.form("register_form"):
        c1, c2 = st.columns(2)
        brand = c1.text_input("ブランド", key="f_brand")
        item_name = c2.text_input("アイテム名", key="f_item_name")

        c3, c4, c5 = st.columns(3)
        category = c3.selectbox(
            "カテゴリ",
            ["トップス", "アウター", "ボトムス", "その他"],
            key="f_category"
        )
        color = c4.text_input("色", key="f_color")
        size_label = c5.text_input("サイズ", key="f_size_label")

        sc1, sc2, sc3, sc4 = st.columns(4)
        length = sc1.number_input(
            "着丈", step=0.5, key="f_length"
        )
        width = sc2.number_input(
            "身幅", step=0.5, key="f_width"
        )
        shoulder = sc3.number_input(
            "肩幅", step=0.5, key="f_shoulder"
        )
        sleeve = sc4.number_input(
            "袖丈", step=0.5, key="f_sleeve"
        )

        sc5, sc6, sc7, sc8 = st.columns(4)
        waist = sc5.number_input(
            "ウエスト", step=0.5, key="f_waist"
        )
        inseam = sc6.number_input(
            "股下", step=0.5, key="f_inseam"
        )
        hip = sc7.number_input(
            "ヒップ", step=0.5, key="f_hip"
        )
        thigh = sc8.number_input(
            "わたり幅", step=0.5, key="f_thigh"
        )

        memo = st.text_area(
            "メモ",
            placeholder="サイズ感・着心地など",
            height=60,
            key="f_memo"
        )

        submitted = st.form_submit_button(
            "💾 登録する",
            type="primary",
            use_container_width=True
        )

        if submitted:
            with st.spinner("保存中..."):
                main_img_data, sub_img_str = (
                    pack_images_for_row(images_to_save)
                )
                new_row = [
                    str(uuid.uuid4())[:8],
                    brand, item_name, category, color,
                    size_label, length, width, shoulder,
                    sleeve, waist, inseam, hip, thigh,
                    main_img_data,
                    sub_img_str,
                    str(datetime.date.today()),
                    memo
                ]
                worksheet.append_row(new_row)
                st.session_state.staged_images = []
                st.session_state.processed_hashes_t3 = set()
                st.session_state.up_key_t3 += 1
                st.success("保存しました！")
                time.sleep(0.6)
                st.rerun()

# ==========================================
# タブ4：編集・画像追加
# ==========================================
with tab4:
    if df.empty:
        st.info("データがありません。")
    else:
        options = [
            f"{r.get('アイテムID')} | "
            f"{r.get('ブランド')} - {r.get('アイテム名')} "
            f"({r.get('表記サイズ')})"
            for _, r in df.iterrows()
        ]
        sel_opt = st.selectbox(
            "対象アイテム",
            options,
            label_visibility="collapsed",
            key="t4_select_item"
        )
        sel_id = sel_opt.split(" | ")[0]
        sel_row = df[
            df["アイテムID"].astype(str) == sel_id
        ].iloc[0]

        existing_pils = []
        m_str = str(sel_row.get("メイン画像URL", "")).strip()
        if m_str:
            p_m = decode_str_to_pil(m_str)
            if p_m:
                existing_pils.append(p_m)
        s_str_all = str(sel_row.get("サブ画像URL", "")).strip()
        if s_str_all:
            for part in s_str_all.split(","):
                p_s = decode_str_to_pil(part)
                if p_s:
                    existing_pils.append(p_s)

        kept_existing_pils = []
        if existing_pils:
            e_cols = st.columns(4)
            for idx, e_img in enumerate(existing_pils):
                with e_cols[idx % 4]:
                    st.image(e_img, use_container_width=True)
                    lbl = "メイン残す" if idx == 0 else f"サブ#{idx}"
                    if st.checkbox(
                        lbl,
                        value=True,
                        key=f"t4_keep_{sel_id}_{idx}"
                    ):
                        kept_existing_pils.append(e_img)

        edit_add_files = st.file_uploader(
            "📁 追加する画像を選択",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"t4_up_{st.session_state.up_key_t4}"
        )
        if edit_add_files:
            for eaf in edit_add_files:
                raw_b4 = eaf.getvalue()
                h4 = hashlib.md5(raw_b4).hexdigest()
                if h4 not in st.session_state.processed_hashes_t4:
                    st.session_state.processed_hashes_t4.add(h4)
                    st.session_state.edit_staged_images.append(
                        Image.open(io.BytesIO(raw_b4)).convert("RGB")
                    )

        eb1, eb2, eb3 = st.columns([1.2, 1, 1.8])
        with eb1:
            if HAS_PASTE_BTN:
                p_res4 = paste_image_button(
                    label="📋 スクショ貼付",
                    background_color="#2563eb",
                    hover_background_color="#1d4ed8",
                    key=f"t4_paste_{st.session_state.up_key_t4}"
                )
                if p_res4.image_data is not None:
                    b_io4 = io.BytesIO()
                    p_res4.image_data.save(b_io4, format="PNG")
                    h_p4 = hashlib.md5(
                        b_io4.getvalue()
                    ).hexdigest()
                    if h_p4 not in st.session_state.processed_hashes_t4:
                        st.session_state.processed_hashes_t4.add(h_p4)
                        st.session_state.edit_staged_images.append(
                            p_res4.image_data.convert("RGB")
                        )
            else:
                st.button(
                    "📋 貼付(要Reboot)",
                    disabled=True,
                    use_container_width=True,
                    key="t4_paste_disabled"
                )
        with eb2:
            if st.button(
                "🗑️ 追加クリア",
                use_container_width=True,
                key="t4_btn_clear"
            ):
                st.session_state.edit_staged_images = []
                st.session_state.processed_hashes_t4 = set()
                st.session_state.up_key_t4 += 1
                st.rerun()
        with eb3:
            add_mode = st.radio(
                "追加位置",
                ["サブに追加", "メインに差替"],
                horizontal=True,
                label_visibility="collapsed",
                key="t4_add_mode"
            )

        new_to_add = []
        if st.session_state.edit_staged_images:
            n_cols = st.columns(4)
            for idx, n_img in enumerate(
                st.session_state.edit_staged_images
            ):
                with n_cols[idx % 4]:
                    st.image(n_img, use_container_width=True)
                    if st.checkbox(
                        f"追加 #{idx+1}",
                        value=True,
                        key=f"t4_add_chk_{idx}"
                    ):
                        new_to_add.append(n_img)

        with st.form("edit_item_form"):
            fc1, fc2 = st.columns(2)
            e_brand = fc1.text_input(
                "ブランド",
                value=str(sel_row.get("ブランド", "")),
                key=f"t4_br_{sel_id}"
            )
            e_name = fc2.text_input(
                "アイテム名",
                value=str(sel_row.get("アイテム名", "")),
                key=f"t4_nm_{sel_id}"
            )

            fc3, fc4, fc5 = st.columns(3)
            cat_list = ["トップス", "アウター", "ボトムス", "その他"]
            cur_cat = str(sel_row.get("カテゴリ", "トップス"))
            cat_idx = (
                cat_list.index(cur_cat)
                if cur_cat in cat_list
                else 0
            )
            e_cat = fc3.selectbox(
                "カテゴリ",
                cat_list,
                index=cat_idx,
                key=f"t4_ct_{sel_id}"
            )
            e_color = fc4.text_input(
                "色",
                value=str(sel_row.get("色", "")),
                key=f"t4_cl_{sel_id}"
            )
            e_size = fc5.text_input(
                "サイズ",
                value=str(sel_row.get("表記サイズ", "")),
                key=f"t4_sz_{sel_id}"
            )

            sc1, sc2, sc3, sc4 = st.columns(4)
            e_len = sc1.number_input(
                "着丈",
                value=float(sel_row.get("着丈") or 0.0),
                step=0.5,
                key=f"t4_ln_{sel_id}"
            )
            e_wid = sc2.number_input(
                "身幅",
                value=float(sel_row.get("身幅") or 0.0),
                step=0.5,
                key=f"t4_wd_{sel_id}"
            )
            e_shd = sc3.number_input(
                "肩幅",
                value=float(sel_row.get("肩幅") or 0.0),
                step=0.5,
                key=f"t4_sh_{sel_id}"
            )
            e_slv = sc4.number_input(
                "袖丈",
                value=float(sel_row.get("袖丈") or 0.0),
                step=0.5,
                key=f"t4_sl_{sel_id}"
            )

            sc5, sc6, sc7, sc8 = st.columns(4)
            e_wst = sc5.number_input(
                "ウエスト",
                value=float(sel_row.get("ウエスト") or 0.0),
                step=0.5,
                key=f"t4_ws_{sel_id}"
            )
            e_ins = sc6.number_input(
                "股下",
                value=float(sel_row.get("股下") or 0.0),
                step=0.5,
                key=f"t4_in_{sel_id}"
            )
            e_hip = sc7.number_input(
                "ヒップ",
                value=float(sel_row.get("ヒップ") or 0.0),
                step=0.5,
                key=f"t4_hp_{sel_id}"
            )
            e_thg = sc8.number_input(
                "わたり幅",
                value=float(sel_row.get("わたり幅") or 0.0),
                step=0.5,
                key=f"t4_th_{sel_id}"
            )

            e_memo = st.text_area(
                "メモ",
                value=str(sel_row.get("メモ") or ""),
                height=60,
                key=f"t4_mm_{sel_id}"
            )

            save_edit = st.form_submit_button(
                "💾 更新する",
                type="primary",
                use_container_width=True
            )

            if save_edit:
                with st.spinner("更新中..."):
                    if "メイン" in add_mode:
                        final_imgs = (
                            new_to_add + kept_existing_pils
                        )
                    else:
                        final_imgs = (
                            kept_existing_pils + new_to_add
                        )

                    new_main, new_sub = pack_images_for_row(
                        final_imgs
                    )

                    id_col = worksheet.col_values(1)
                    if sel_id in id_col:
                        row_num = id_col.index(sel_id) + 1
                        reg_date = str(
                            sel_row.get(
                                "登録日",
                                str(datetime.date.today())
                            )
                        )
                        updated_row = [
                            sel_id, e_brand, e_name, e_cat,
                            e_color, e_size, e_len, e_wid,
                            e_shd, e_slv, e_wst, e_ins,
                            e_hip, e_thg, new_main,
                            new_sub, reg_date, e_memo
                        ]
                        worksheet.update(
                            range_name=f"A{row_num}:R{row_num}",
                            values=[updated_row]
                        )
                        st.session_state.edit_staged_images = []
                        st.session_state.processed_hashes_t4 = set()
                        st.session_state.up_key_t4 += 1
                        st.success("更新しました！")
                        time.sleep(0.6)
                        st.rerun()

        with st.expander("🗑️ アイテム削除"):
            if st.button(
                "このアイテムを削除する",
                type="secondary",
                key=f"t4_del_{sel_id}"
            ):
                id_col = worksheet.col_values(1)
                if sel_id in id_col:
                    row_num = id_col.index(sel_id) + 1
                    worksheet.delete_rows(row_num)
                    st.rerun()
