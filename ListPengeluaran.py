import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import math
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================
# KONEKSI GOOGLE SHEETS
# ==========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)

# GANTI DENGAN NAMA SPREADSHEET KAMU
spreadsheet = client.open("List Pengeluaran")

# GANTI DENGAN NAMA SHEET
sheet = spreadsheet.worksheet("Pengeluaran")


@st.cache_data(ttl=100)
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

# ==========================
# STREAMLIT
# ==========================

st.title("💰 Input Pengeluaran")

# Data awal
default_df = pd.DataFrame(
    {
        "Pengeluaran": [None] * 5,
        "Harga": [None] * 5,
        "Kategori": [""] * 5,
    }
)

kategori_map = {
    "A - Pengeluaran Makan/Minum": "A",
    "B - Pengeluaran Rumah Tangga": "B",
    "C - Pengeluaran Tersier": "C",
    "D - Pengeluaran Tidak Terduga": "D",
}

edited_df = st.data_editor(
    default_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Harga": st.column_config.NumberColumn(
            "Harga",
            format="Rp %d",
            step=1000,
            min_value=0
        ),

        "Kategori": st.column_config.SelectboxColumn(
            "Kategori",
            options=list(kategori_map.keys()),
            required=True,
        ),
    }
)

temp_df = edited_df.copy()

temp_df = temp_df.dropna(subset=["Harga"])

if len(temp_df):

    total = int(temp_df["Harga"].sum())

    col1, col2 = st.columns(2)

    col1.metric(
        "Jumlah Transaksi",
        len(temp_df)
    )

    col2.metric(
        "Total Pengeluaran",
        f"Rp {total:,.0f}".replace(",", ".")
    )


if st.button(
    "💾 Simpan Semua",
    use_container_width=True
):

    # Ambil data yang benar-benar diisi
    edited_df = edited_df.dropna(subset=["Pengeluaran", "Harga"])
    edited_df = edited_df[edited_df["Pengeluaran"] != ""]

    if edited_df.empty:
        st.warning("Belum ada data.")
        st.stop()

    data_sheet = sheet.get_all_values()

    last_no = int(data_sheet[-1][0])
    last_ord = int(data_sheet[-1][1].split("-")[1])

    rows = []

    for _, row in edited_df.iterrows():

        last_no += 1
        last_ord += 1

        now = datetime.now(ZoneInfo("Asia/Jakarta"))

        tanggal = f"{now.month}/{now.day}/{now.year} {now.strftime('%H:%M:%S')}"

        kategori = kategori_map[row["Kategori"]]

        rows.append([
            last_no,
            f"ORD-{last_ord}",
            tanggal,
            row["Pengeluaran"],
            int(row["Harga"]),
            kategori,
            "Streamlit"
        ])

    sheet.append_rows(rows)

    load_data.clear()

    st.success(f"✅ {len(rows)} transaksi berhasil disimpan!")

    st.rerun()


# ===========================================
#                SEARCH TRANSAKSI
# ===========================================

st.divider()

st.subheader("📋 Search Transaksi ")

# Search
def reset_page():
    st.session_state.page = 1

keyword = st.text_input(
    "",
    placeholder="🔍 Cari pengeluaran...",
    key="search",
    on_change=reset_page
)

# Ambil data
df = (
    load_data()
    .iloc[::-1]
    .reset_index(drop=True)
)

# Filter realtime
if keyword:
    df = df[
        df["Pengeluaran"]
        .astype(str)
        .str.contains(keyword, case=False, na=False)
    ]

df = df[
    [
        "Tanggal",
        "Pengeluaran",
        "Harga",
        "Kategori"
    ]
]

# Ubah Harga dari "Rp30,000" menjadi angka
df["Harga"] = (
    df["Harga"]
    .astype(str)
    .str.replace("Rp", "", regex=False)
    .str.replace(",", "", regex=False)
    .str.strip()
)

df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce")


# ==========================
# Pagination
# ==========================

ROWS_PER_PAGE = 10

if "page" not in st.session_state:
    st.session_state.page = 1

total_rows = len(df)
total_pages = max(math.ceil(total_rows / ROWS_PER_PAGE), 1)

# Kalau hasil search berkurang, pastikan page tidak melebihi total halaman
if st.session_state.page > total_pages:
    st.session_state.page = total_pages

start = (st.session_state.page - 1) * ROWS_PER_PAGE
end = start + ROWS_PER_PAGE

page_df = df.iloc[start:end]

table_height = min(len(page_df) * 35 + 40, 420)

st.dataframe(
    page_df,
    use_container_width=True,
    hide_index=True,
    height=table_height,
    column_config={
        "Harga": st.column_config.NumberColumn(
            "Harga",
            format="Rp %.0f"
        )
    }
)

st.caption(
    f"Menampilkan {start+1}-{min(end, total_rows)} dari {total_rows} transaksi"
)

col1, col2, col3 = st.columns([1,2,1])

with col1:
    if st.button("◀ Sebelumnya", disabled=st.session_state.page == 1):
        st.session_state.page -= 1
        st.rerun()

with col2:
    st.markdown(
        f"<div style='text-align:center'><b>Halaman {st.session_state.page} / {total_pages}</b></div>",
        unsafe_allow_html=True
    )

with col3:
    if st.button("Berikutnya ▶", disabled=st.session_state.page == total_pages):
        st.session_state.page += 1
        st.rerun()