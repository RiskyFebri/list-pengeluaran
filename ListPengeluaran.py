import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import math
from datetime import datetime
from zoneinfo import ZoneInfo
import calendar
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode


def update_transaction(id_pengeluaran, pengeluaran, harga, kategori):

    records = sheet.get_all_records()

    for i, record in enumerate(records):

        if record["ID Pengeluaran"] == id_pengeluaran:

            row_number = i + 2   # +1 header, +1 karena index mulai 0

            sheet.update(
                f"D{row_number}:F{row_number}",
                [[
                    pengeluaran,
                    harga,
                    kategori
                ]]
            )

            load_data.clear()
            return True

    return False

def delete_transaction(id_pengeluaran):

    records = sheet.get_all_records()

    for i, record in enumerate(records):

        if record["ID Pengeluaran"] == id_pengeluaran:

            row_number = i + 2

            sheet.delete_rows(row_number)

            load_data.clear()

            return True

    return False

# ==========================
# KONFIGURASI HALAMAN
# ==========================
st.set_page_config(
    page_title="List Pengeluaran",
    page_icon="💰",
    layout="wide"
)

# ==========================
# KONEKSI GOOGLE SHEETS
# ==========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

#SECRETS STREAMLIT
#creds = Credentials.from_service_account_info(
#    st.secrets["gcp_service_account"],
#    scopes=SCOPES
#)

#LOCALHOST
creds = Credentials.from_service_account_file(
    "service_account.json",
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
        "ID Pengeluaran",
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

page_df = df.copy()

page_df["Tanggal"] = pd.to_datetime(
    page_df["Tanggal"]
).dt.strftime("%d %b %Y")

gb = GridOptionsBuilder.from_dataframe(page_df)

gb.configure_default_column(
    sortable=True,
    filter=True,
    resizable=True,
)

gb.configure_grid_options(
    suppressCellFocus=True,
    rowHeight=28,
    headerHeight=42,
)

gb.configure_column(
    "ID Pengeluaran",
    width=120
)

gb.configure_column(
    "Tanggal",
    width=120
)

gb.configure_column(
    "Pengeluaran",
    width=250
)

gb.configure_column(
    "Harga",
    width=120,
    type=["numericColumn"],
    valueFormatter="""
        value == null
        ? ''
        : 'Rp ' + Number(value).toLocaleString('id-ID')
    """
)

gb.configure_column(
    "Kategori",
    width=90
)

gb.configure_selection(
    selection_mode="single",
    use_checkbox=False
)

gb.configure_pagination(
    enabled=True,
    paginationAutoPageSize=False,
    paginationPageSize=20
)

grid_options = gb.build()

# Cukup definisikan 1 string CSS gabungan ini:
css_auto = """
/* Default (Light Mode) */
.ag-root-wrapper {
    background-color: white !important;
    border: 1px solid #DDDDDD !important;
    border-radius: 10px !important;
}
.ag-header, .ag-header-cell {
    background-color: #F5F5F5 !important;
    color: #222222 !important;
    font-weight: 600 !important;
}
.ag-cell {
    background-color: white !important;
    color: #222222 !important;
}
.ag-row-hover .ag-cell {
    background-color: #F3F7FC !important;
}
.ag-row-selected .ag-cell {
    background-color: #D6EAF8 !important;
}

/* Auto Dark Mode (Terdeteksi via Browser/Sistem) */
@media (prefers-color-scheme: dark) {
    .ag-root-wrapper {
        background-color: #0E1117 !important;
        border: 1px solid #31333F !important;
    }
    .ag-header, .ag-header-cell {
        background-color: #1E1E1E !important;
        color: white !important;
    }
    .ag-cell {
        background-color: #0E1117 !important;
        color: white !important;
    }
    .ag-row-hover .ag-cell {
        background-color: #1F2937 !important;
    }
    .ag-row-selected .ag-cell {
        background-color: #0B5EA8 !important;
    }
}
"""

# Panggil AgGrid tanpa mengandalkan st.get_option("theme.base") lagi
grid_response = AgGrid(
    page_df,
    gridOptions=grid_options,
    height=634,
    fit_columns_on_grid_load=True,
    theme="streamlit",
    custom_css=css_auto,
)

# ==========================
# Ambil data yang dipilih
# ==========================

grid_state = grid_response.grid_state

selected_index = []

if grid_state is not None:
    selected_index = grid_state.get("rowSelection", [])

if selected_index:

    row = page_df.iloc[int(selected_index[0])]

    st.divider()
    st.subheader("📄 Detail Transaksi")

    st.write(f"**ID** : {row['ID Pengeluaran']}")
    st.write(f"**Tanggal** : {row['Tanggal']}")
    st.write(f"**Pengeluaran** : {row['Pengeluaran']}")
    st.write(f"**Harga** : Rp {int(row['Harga']):,}".replace(",", "."))
    st.write(f"**Kategori** : {row['Kategori']}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✏ Edit", use_container_width=True):
            st.session_state.edit_mode = True

    with col2:
        if st.button("🗑 Delete", use_container_width=True):
            st.session_state.delete_mode = True

    # ==========================
    # FORM EDIT
    # ==========================

    if st.session_state.get("edit_mode", False):

        with st.form("edit_form"):

            nama = st.text_input(
                "Pengeluaran",
                value=row["Pengeluaran"]
            )

            harga = st.number_input(
                "Harga",
                value=int(row["Harga"])
            )

            kategori = st.selectbox(
                "Kategori",
                ["A", "B", "C", "D"],
                index=["A", "B", "C", "D"].index(row["Kategori"])
            )

            simpan = st.form_submit_button(
                "💾 Simpan Perubahan",
                use_container_width=True
            )

            if simpan:

                berhasil = update_transaction(

                    row["ID Pengeluaran"],
                    nama,
                    harga,
                    kategori
                )

                if berhasil:

                    st.success("✅ Data berhasil diperbarui")

                    st.session_state.edit_mode = False

                    st.rerun()

                else:

                    st.error("ID tidak ditemukan.")

    # ==========================
    # DELETE
    # ==========================

    if st.session_state.get("delete_mode", False):

        st.warning("Yakin ingin menghapus transaksi ini?")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Ya, Hapus", use_container_width=True):

                berhasil = delete_transaction(
                    row["ID Pengeluaran"]
                )

                if berhasil:

                    st.success("✅ Data berhasil dihapus")

                    st.session_state.delete_mode = False

                    st.rerun()

                else:

                    st.error("ID tidak ditemukan.")

        with col2:
            if st.button("Batal", use_container_width=True):
                st.session_state.delete_mode = False

# ==========================
# PREPARE DATA DASHBOARD
# ==========================

df_dashboard = load_data().copy()

# Ubah tanggal menjadi datetime
df_dashboard["Tanggal"] = pd.to_datetime(
    df_dashboard["Tanggal"],
    format="%m/%d/%Y %H:%M:%S"
)

# Ubah Harga menjadi angka
df_dashboard["Harga"] = (
    df_dashboard["Harga"]
    .astype(str)
    .str.replace("Rp", "", regex=False)
    .str.replace(",", "", regex=False)
    .str.strip()
)

df_dashboard["Harga"] = pd.to_numeric(
    df_dashboard["Harga"],
    errors="coerce"
)


# ===================================================
# DASHBOARD 1
# ===================================================

bulan_nama = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember"
]

st.header("🗓️ Dashboard")

col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    bulan = st.selectbox(
        "Bulan",
        range(1, 13),
        index=datetime.now().month - 1,
        format_func=lambda x: bulan_nama[x-1]
    )

with col_filter2:
    tahun = st.selectbox(
        "Tahun",
        sorted(df_dashboard["Tanggal"].dt.year.unique(), reverse=True)
    )

# Filter data dashboard
df = df_dashboard[
    (df_dashboard["Tanggal"].dt.month == bulan) &
    (df_dashboard["Tanggal"].dt.year == tahun)
].copy()

daily = (
    df.groupby(df["Tanggal"].dt.day)["Harga"]
    .sum()
    .to_dict()
)

# Layout Dashboard
left, right = st.columns([1.25, 0.75], gap="large")

st.markdown("""
<style>
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}
.head{background:#0b5ea8;color:#fff;text-align:center;padding:8px;font-weight:bold}
.cell{border:1px solid #ccc;background:#ececec;min-height:80px;padding:5px}
.empty{background:#d8d8d8}
.day{font-size:22px;color:#2d73c7;font-weight:bold}
.amt{
    margin-top:12px;
    font-size:12px;
    padding:2px;
    font-weight:bold;
    border-radius:4px;
    text-align:center;
}
</style>""",unsafe_allow_html=True)

with left:

    html='<div class="cal">'

    for h in ["SUN","MON","TUE","WED","THU","FRI","SAT"]:
        html+=f'<div class="head">{h}</div>'

    cal=calendar.Calendar(firstweekday=6)

    weeks=cal.monthdayscalendar(tahun,bulan)

    while len(weeks)<6: weeks.append([0]*7)
    for w in weeks:
        for d in w:
            if d==0:
                html+='<div class="cell empty"></div>'
            else:
                amount = daily.get(d, 0)
                rp = f"Rp{amount:,.0f}".replace(",", ".")

                # Warna berdasarkan ada/tidaknya pengeluaran
                if amount == 0:
                    bg = "#C6EFCE"      # Hijau muda
                    color = "#006100"   # Hijau tua
                else:
                    bg = "#FFC7CE"      # Merah muda
                    color = "#9C0006"   # Merah tua

                html += (
                    f'<div class="cell">'
                    f'<div class="day">{d}</div>'
                    f'<div class="amt" '
                    f'style="background:{bg}; color:{color};">'
                    f'{rp}'
                    f'</div>'
                    f'</div>'
                )

    html+='</div>'

    st.markdown(html,unsafe_allow_html=True)


with right:

    st.subheader("📊 Ringkasan Bulanan")

    total = int(df["Harga"].sum())
    total_trx = len(df)
    avg = int(total / total_trx) if total_trx else 0

    kategori = (
        df.groupby("Kategori")["Harga"]
        .sum()
        .to_dict()
    )

    makan = kategori.get("A", 0)
    rumah = kategori.get("B", 0)
    tersier = kategori.get("C", 0)
    tak_terduga = kategori.get("D", 0)

    if total_trx:
        harian = (
        df.groupby(df["Tanggal"].dt.date)["Harga"]
        .sum()
        )

        idx = harian.idxmax()
        max_day = harian.max()
    else:
        idx = "-"
        max_day = 0

    st.info(
        f"""
### 💰 Total Pengeluaran
**Rp {total:,.0f}**
""".replace(",", ".")
    )

    c1, c2 = st.columns(2)

    c1.metric("Transaksi", total_trx)
    c2.metric("Rata-rata", f"Rp {avg:,.0f}".replace(",", "."))

    st.markdown("<hr style='margin:-25px 0 10px 0;'>", unsafe_allow_html=True)

    st.markdown(
    "<div style='margin-top:-8px; margin-bottom:15px; font-weight:600;'>Kategori</div>",
    unsafe_allow_html=True
)

    colA, colB = st.columns(2)

    with colA:
        st.progress(makan / total if total else 0,
                    text=f"🍜 Makan: Rp {makan:,.0f}".replace(",", "."))
        st.progress(tersier / total if total else 0,
                    text=f"🛍️ Tersier: Rp {tersier:,.0f}".replace(",", "."))

    with colB:
        st.progress(rumah / total if total else 0,
                    text=f"🏠 Rumah: Rp {rumah:,.0f}".replace(",", "."))
        st.progress(tak_terduga / total if total else 0,
                    text=f"🚨 Tak Terduga: Rp {tak_terduga:,.0f}".replace(",", "."))

    st.markdown("<hr style='margin:-1px 0 10px 0;'>", unsafe_allow_html=True)

    tanggal_terboros = pd.to_datetime(idx).strftime("%d %b %Y")

    st.success(
    f"🔥 Hari terboros : **{tanggal_terboros}**\n\nRp {max_day:,.0f}".replace(",", ".")
    )

    # Tambah ruang agar tinggi panel sama dengan kalender
    for _ in range(2):
        st.write("")



# ===================================================
# DASHBOARD 2
# ===================================================

st.markdown(
    "<hr style='margin:-15px 0 15px 0;'>",
    unsafe_allow_html=True
)

left2, right2 = st.columns(2, gap="large")

# ===========================================
# KIRI - TOP 5 PENGELUARAN
# ===========================================

with left2:

    st.subheader("🏆 Top 5 Pengeluaran")

    top_pengeluaran = (
        df.groupby("Pengeluaran", as_index=False)["Harga"]
        .sum()
        .sort_values("Harga", ascending=False)
        .head(5)
    )

    fig1 = px.bar(
        top_pengeluaran,
        x="Harga",
        y="Pengeluaran",
        orientation="h",
        text="Harga",
        color="Harga",
        color_continuous_scale="Blues"
    )

    fig1.update_traces(
        texttemplate="Rp %{x:,.0f}",
        textposition="outside"
    )

    fig1.update_layout(
        height=380,
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="",
        yaxis_title="",
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

# ===========================================
# KANAN - TOP 5 HARI TERBOROS
# ===========================================

with right2:

    st.subheader("🔥 Top 5 Hari Terboros")

    top_hari = (
        df.groupby(df["Tanggal"].dt.date, as_index=False)["Harga"]
        .sum()
        .sort_values("Harga", ascending=False)
        .head(5)
    )

    top_hari["Tanggal"] = pd.to_datetime(
        top_hari["Tanggal"]
    ).dt.strftime("%d %b")

    fig2 = px.bar(
        top_hari,
        x="Harga",
        y="Tanggal",
        orientation="h",
        text="Harga",
        color="Harga",
        color_continuous_scale="Reds"
    )

    fig2.update_traces(
        texttemplate="Rp %{x:,.0f}",
        textposition="outside"
    )

    fig2.update_layout(
        height=380,
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="",
        yaxis_title="",
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )



# ==========================
# DASHBOARD 3
# ==========================

st.markdown(
    "<hr style='margin:-15px 0 15px 0;'>",
    unsafe_allow_html=True
)

# ==========================
# FILTER TAHUN
# ==========================

# Menggunakan slicer Tahun dari Dashboard 1
df3 = df_dashboard[
    df_dashboard["Tanggal"].dt.year == tahun
].copy()

# Nama bulan
bulan_nama = [
    "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
]

# Layout
left3, right3 = st.columns(2, gap="large")

with left3:

    st.subheader("📈 Trend Pengeluaran Bulanan")

    trend = (
        df3.groupby(df3["Tanggal"].dt.month)["Harga"]
        .sum()
        .reindex(range(1, 13), fill_value=0)
        .reset_index()
    )

    trend.columns = ["Bulan", "Total"]

    trend["Nama"] = bulan_nama

    fig = px.line(
        trend,
        x="Nama",
        y="Total",
        markers=True
    )

    fig.update_traces(
        line=dict(width=4),
        marker=dict(size=8)
    )

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with right3:

    st.subheader("🍜 Makan / Minum VS 🏠 Rumah Tangga")

    makan = (
        df3[df3["Kategori"] == "A"]
        .groupby(df3["Tanggal"].dt.month)["Harga"]
        .sum()
        .reindex(range(1, 13), fill_value=0)
    )

    rumah = (
        df3[df3["Kategori"] == "B"]
        .groupby(df3["Tanggal"].dt.month)["Harga"]
        .sum()
        .reindex(range(1, 13), fill_value=0)
    )

    compare = pd.DataFrame({
        "Bulan": bulan_nama,
        "Makan / Minum": makan.values,
        "Rumah Tangga": rumah.values
    })

    fig2 = px.bar(
        compare,
        x="Bulan",
        y=["Makan / Minum", "Rumah Tangga"],
        barmode="group",
        color_discrete_sequence=[
            "#0D47A1",   # Biru tua
            "#64B5F6"    # Biru muda
        ]
    )

    fig2.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="",
        yaxis_title="",
        legend_title=""
    )

    st.plotly_chart(
        fig2,
        use_container_width=True,
        config={"displayModeBar": False}
    )