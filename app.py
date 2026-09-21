import streamlit as st
import sqlite3
import pandas as pd
import io
from io import BytesIO
from datetime import datetime

from datetime import date, timedelta
from PIL import Image

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from xml.sax.saxutils import escape


st.markdown("""
<style>

/* ================================
   SIDEBAR LOGBOOK
   ================================ */

/* Kotak Laboratorium */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: #ffffff !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
    border: none !important;
    overflow: hidden !important;
}

/* Judul Laboratorium */
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    background: transparent !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 12px !important;
}

/* Judul tetap putih ketika dibuka */
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    color: white !important;
    font-weight: 600 !important;
}

/* Area isi pengujian */
[data-testid="stSidebar"] [data-testid="stExpander"] > div {
    background: #ffffff !important;
    padding: 4px 8px 8px 8px !important;
}

/* Semua tulisan pilihan pengujian */
[data-testid="stSidebar"] [data-testid="stExpander"] label {
    color: #1f2937 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* Tulisan di dalam radio */
[data-testid="stSidebar"] [data-testid="stExpander"] label p {
    color: #1f2937 !important;
}

/* Saat pilihan pengujian dipilih */
[data-testid="stSidebar"] [data-testid="stExpander"] label:has(input:checked) {
    color: #123B63 !important;
    font-weight: 700 !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] label:has(input:checked) p {
    color: #123B63 !important;
    font-weight: 700 !important;
}

/* Jarak antar pilihan */
[data-testid="stSidebar"] [data-testid="stExpander"] [role="radiogroup"] {
    gap: 3px !important;
}

/* Hover pilihan */
[data-testid="stSidebar"] [data-testid="stExpander"] label:hover {
    background: #f1f5f9 !important;
    border-radius: 6px !important;
}

/* Hilangkan garis/border bawaan */
[data-testid="stSidebar"] [data-testid="stExpander"] details {
    border: none !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# KONFIGURASI
# =========================================================
st.set_page_config(
    page_title="Quality Assurance Department",
    layout="wide"
)

if "login" not in st.session_state:
    st.session_state["login"] = False

if "username" not in st.session_state:
    st.session_state["username"] = ""

if "role" not in st.session_state:
    st.session_state["role"] = ""

if "data_tersimpan" not in st.session_state:
    st.session_state["data_tersimpan"] = False

if "edit_id" not in st.session_state:
    st.session_state["edit_id"] = None

if "delete_id" not in st.session_state:
    st.session_state["delete_id"] = None

if "detail_id" not in st.session_state:
    st.session_state["detail_id"] = None


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #0B1F3A;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# DATABASE
# =========================================================
conn = sqlite3.connect("incoming.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS incoming (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_no TEXT,
    nama_raw_material TEXT,
    kode_raw_material TEXT,
    pabrik TEXT,
    supplier TEXT,
    prod_date TEXT,
    exp_date TEXT,
    jumlah REAL,
    no_po TEXT,
    no_grn TEXT,
    tanggal_sampling TEXT,
    petugas_sampling TEXT,
    metode_sampling TEXT,
    no_lot_sap TEXT,
    jumlah_sampel TEXT,
    orga_penampakan TEXT,
    orga_rasa TEXT,
    orga_bau TEXT,
    orga_warna_tekstur TEXT,
    orga_ukuran TEXT,
    pest_infestation TEXT,
    logo_halal TEXT,
    exp_halal_cert TEXT,
    no_lot_packing TEXT,
    status TEXT,
    jumlah_status REAL,
    keterangan TEXT,
    analis TEXT,
    tanggal_analis TEXT,
    qa_lab_supervisor TEXT,
    tanggal_qa_lab TEXT,
    qa_incoming_group_leader TEXT,
    tanggal_group_leader TEXT,
    qa_incoming_supervisor TEXT,
    tanggal_supervisor TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS riwayat_perubahan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incoming_id INTEGER,
    aksi TEXT,
    waktu TEXT,
    pengguna TEXT,
    detail TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hasil_analisa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incoming_id INTEGER,
    parameter TEXT,
    hasil_analisa TEXT,
    standar TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Tambahkan kolom lama yang mungkin belum ada.
kolom_baru = [
    ("orga_penampakan", "TEXT"),
    ("orga_rasa", "TEXT"),
    ("orga_bau", "TEXT"),
    ("orga_warna_tekstur", "TEXT"),
    ("orga_ukuran", "TEXT"),
    ("pest_infestation", "TEXT"),
    ("logo_halal", "TEXT"),
    ("exp_halal_cert", "TEXT"),
]

for nama_kolom, tipe_kolom in kolom_baru:
    try:
        cursor.execute(
            f"ALTER TABLE incoming ADD COLUMN {nama_kolom} {tipe_kolom}"
        )
    except sqlite3.OperationalError:
        pass

# Admin awal untuk login.
cursor.execute("SELECT COUNT(*) FROM users")
jumlah_user = cursor.fetchone()[0]

if jumlah_user == 0:
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin123", "Administrator")
    )

cursor.execute("""
CREATE TABLE IF NOT EXISTS master_raw_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_raw_material TEXT UNIQUE,
    nama_raw_material TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS master_standar_analisa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_raw_material TEXT,
    parameter TEXT,
    standar TEXT,
    satuan TEXT
)
""")

conn.commit()
conn.close()

# =========================================================
# DATABASE KHUSUS LOGBOOK
# =========================================================

conn = sqlite3.connect("incoming.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS logbook_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_sampel TEXT UNIQUE,
    tanggal TEXT,
    nama_sampel TEXT,
    kode_sampel TEXT,
    keterangan TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logbook_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    jenis_logbook TEXT,
    parameter TEXT,
    hasil TEXT,
    standar TEXT,
    satuan TEXT,
    analis TEXT,
    tanggal_uji TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logbook_riwayat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    aksi TEXT,
    waktu TEXT,
    pengguna TEXT,
    detail TEXT
)
""")

conn.commit()
conn.close()

conn = sqlite3.connect("incoming.db")
cursor = conn.cursor()

# =========================================================
# FUNGSI DATABASE
# =========================================================
def catat_riwayat(incoming_id, aksi, detail=""):
    conn = sqlite3.connect("incoming.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO riwayat_perubahan
        (incoming_id, aksi, waktu, pengguna, detail)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            incoming_id,
            aksi,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.get("username", ""),
            detail
        )
    )
    conn.commit()
    conn.close()


# =========================================================
# FUNGSI PDF
# =========================================================
def buat_pdf_incoming(data, hasil_analisa):
    buffer_pdf = BytesIO()

    doc = SimpleDocTemplate(
        buffer_pdf,
        pagesize=landscape(A4),
        rightMargin=25,
        leftMargin=25,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    story = []

    header = Table(
        [[
            "Quality Assurance Department",
            "PEMERIKSAAN RAW MATERIAL",
            f"Ref No. {data['ref_no']}"
        ]],
        colWidths=[180, 380, 150]
    )

    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    story.append(header)
    story.append(Spacer(1, 8))

    info_kiri = [
        ["Nama Raw Material", data["nama_raw_material"]],
        ["Kode Raw Material", data["kode_raw_material"]],
        ["Pabrik/Merek – Negara asal", data["pabrik"]],
        ["Supplier", data["supplier"]],
        ["Prod. Date", data["prod_date"]],
        ["Exp. Date", data["exp_date"]],
        ["No. PO", data["no_po"]],
        ["No. GRN", data["no_grn"]],
    ]

    info_kanan = [
        ["Tanggal Sampling", data["tanggal_sampling"]],
        ["Petugas Sampling", data["petugas_sampling"]],
        ["Metode Sampling", data["metode_sampling"]],
        ["Jumlah Sampling", data["jumlah_sampel"]],
        ["No. Lot SAP", data["no_lot_sap"]],
        ["Logo Halal pada Kemasan", data["logo_halal"]],
        ["Masa berlaku Sertifikat Halal", data["exp_halal_cert"]],
        ["No. Lot / Packing Code / Batch", data["no_lot_packing"]],
    ]

    tabel_info = Table(
        [[
            Table(info_kiri, colWidths=[115, 210]),
            Table(info_kanan, colWidths=[130, 210])
        ]],
        colWidths=[335, 340]
    )

    for tabel in tabel_info._cellvalues[0]:
        tabel.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

    story.append(tabel_info)
    story.append(Spacer(1, 8))

    organoleptik = [
        ["Penampakan", data["orga_penampakan"]],
        ["Rasa", data["orga_rasa"]],
        ["Bau", data["orga_bau"]],
        ["Warna / Tekstur", data["orga_warna_tekstur"]],
        ["Ukuran", data["orga_ukuran"]],
        ["Pest Infestation", data["pest_infestation"]],
    ]

    halal = [
        ["Logo Halal", data["logo_halal"]],
        ["Masa Berlaku Sertifikat Halal", data["exp_halal_cert"]],
    ]

    tabel_orga = Table(
        [[
            Table(
                [["Pemeriksaan Organoleptik", "Hasil"]] + organoleptik,
                colWidths=[170, 160]
            ),
            Table(
                [["Legalitas & Halal", "Hasil"]] + halal,
                colWidths=[170, 160]
            )
        ]],
        colWidths=[335, 340]
    )

    for tabel in tabel_orga._cellvalues[0]:
        tabel.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ]))

    story.append(tabel_orga)
    story.append(Spacer(1, 8))

    analisa_data = [["Parameter", "Hasil Analisa", "Standar"]]

    for _, row in hasil_analisa.iterrows():
        analisa_data.append([
            str(row["parameter"]),
            str(row["hasil_analisa"]),
            str(row["standar"])
        ])

    if len(analisa_data) == 1:
        analisa_data.append(["-", "-", "-"])

    tabel_analisa = Table(
        analisa_data,
        colWidths=[250, 180, 245],
        repeatRows=1
    )

    tabel_analisa.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(tabel_analisa)
    story.append(Spacer(1, 8))

    status_data = [
        ["Status", data["status"], "Jumlah", f"{data['jumlah_status']} kg"],
        ["Keterangan", data["keterangan"], "", ""]
    ]

    tabel_status = Table(
        status_data,
        colWidths=[70, 300, 70, 235]
    )

    tabel_status.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))

    story.append(tabel_status)
    story.append(Spacer(1, 8))

    pengesahan = [
        [
            "Analis",
            "QA Lab Supervisor",
            "QA Incoming Group Leader",
            "QA Incoming Supervisor"
        ],
        [
            data["analis"],
            data["qa_lab_supervisor"],
            data["qa_incoming_group_leader"],
            data["qa_incoming_supervisor"]
        ],
        [
            f"Tgl: {data['tanggal_analis']}",
            f"Tgl: {data['tanggal_qa_lab']}",
            f"Tgl: {data['tanggal_group_leader']}",
            f"Tgl: {data['tanggal_supervisor']}"
        ]
    ]

    tabel_pengesahan = Table(
        pengesahan,
        colWidths=[168, 168, 168, 168],
        rowHeights=[20, 35, 20]
    )

    tabel_pengesahan.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(tabel_pengesahan)

    doc.build(story)
    buffer_pdf.seek(0)

    return buffer_pdf


# =========================================================
# LOGIN
# =========================================================
if not st.session_state["login"]:
    st.title("Login Sistem")
    st.write(
        "Silakan login untuk mengakses Sistem Quality Assurance Department."
    )

    col_login, _ = st.columns([1, 1])

    with col_login:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button(
            "Login",
            type="primary",
            use_container_width=True
        ):
            conn = sqlite3.connect("incoming.db")
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT username, role
                FROM users
                WHERE username = ? AND password = ?
                """,
                (username, password)
            )

            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state["login"] = True
                st.session_state["username"] = user[0]
                st.session_state["role"] = user[1]
                st.rerun()
            else:
                st.error("Username atau password salah.")

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    logo = Image.open("Logo Ceres_Bullet.jpg")
    st.image(logo, width=90)

    st.title("Main Menu")
    st.caption("Quality Assurance Department")
    st.divider()

    menu = st.sidebar.radio(
    "Modul Utama:",
    [
        "Pemeriksaan Raw Material (PRM)",
        "LOGBOOK",
        "Master Data"
    ],
    key="main_menu"
)

pilihan_lab = None
pilihan_pengujian = None
logbook_menu = None


# =========================================================
# MENU LOGBOOK
# =========================================================

if menu == "LOGBOOK":

    logbook_menu = st.sidebar.radio(
        "LOGBOOK",
        [
            "Laboratorium Instrument",
            "Laboratorium Fisika",
            "Laboratorium Kimia",
            "Result",
            "Riwayat Perubahan"
        ],
        key="logbook_menu"
    )

    if logbook_menu == "Laboratorium Instrument":
        pilihan_lab = "Laboratorium Instrument"

    elif logbook_menu == "Laboratorium Fisika":
        pilihan_lab = "Laboratorium Fisika"

    elif logbook_menu == "Laboratorium Kimia":
        pilihan_lab = "Laboratorium Kimia"


# =========================================================
# USER LOGIN
# =========================================================

st.sidebar.divider()

st.sidebar.caption(
    f"User: {st.session_state['username']} "
    f"({st.session_state['role']})"
)

if st.sidebar.button(
    "Logout",
    use_container_width=True,
    key="logout_sidebar"
):
    st.session_state["login"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.rerun()


# =========================================================
# HALAMAN PRM
# =========================================================
if menu == "Pemeriksaan Raw Material (PRM)":

    st.title("Pemeriksaan Raw Material (PRM)")

    tab_input, tab_db, tab_riwayat, tab_user = st.tabs([
        "Input Incoming",
        "Database",
        "Riwayat Perubahan",
        "Manajemen User"
    ])


    # =====================================================
    # 1. INPUT INCOMING
    # =====================================================
    if st.session_state.get("data_tersimpan", False):
        st.success("Data berhasil disimpan ke database!")
        st.session_state["data_tersimpan"] = False

    with tab_input:
        st.subheader("Input Incoming Raw Material")
        st.write(
            "Isi formulir berikut untuk menambahkan data sampel baru."
        )
        st.divider()

        st.markdown("### Nomor Referensi Dokumentasi")

        c_ref1, c_ref2 = st.columns([1, 2])

        with c_ref1:
            ref_prefix = st.text_input(
                "No. Ref",
                placeholder="Contoh: 001"
            )

        with c_ref2:
            ref_suffix = st.text_input(
                "Kode Akhir",
                placeholder="Contoh: QA/IX/2026"
            )

        ref_no_full = (
            f"{ref_prefix}/PRM/{ref_suffix}"
            if ref_prefix or ref_suffix
            else ""
        )

        st.info(
            f"**Format Ref. No:** "
            f"`{ref_no_full if ref_no_full else '... / PRM / ...'}`"
        )

        st.divider()

        today = date.today()
        default_exp = today + timedelta(days=365)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**1. Informasi Raw Material**")

            kode_raw_material = st.text_input(
                "Kode Raw Material *",
                key="kode_raw_material_prm"
            )

            nama_raw_material = ""

            if kode_raw_material.strip():

                conn_master = sqlite3.connect("incoming.db")
                cursor_master = conn_master.cursor()

                cursor_master.execute(
                    """
                    SELECT nama_raw_material
                    FROM master_raw_material
                    WHERE UPPER(TRIM(kode_raw_material)) = UPPER(TRIM(?))
                    """,
                    (kode_raw_material.strip(),)
                )

                hasil_master = cursor_master.fetchone()

                conn_master.close()

                if hasil_master:
                    nama_raw_material = hasil_master[0]
                else:
                    st.warning("Kode Raw Material belum terdaftar di Master Data.")

            st.text_input(
                "Nama Raw Material",
                value=nama_raw_material,
                disabled=True
            )

            pabrik = st.text_input(
                "Pabrik/Merek - Negara Asal *"
            )

            supplier = st.text_input(
                "Supplier *",
                key="supplier-prm"
            )

            # ==========================================
            # PROD DATE & EXP DATE
            # ==========================================

            if "jumlah_tanggal_prm" not in st.session_state:
                st.session_state["jumlah_tanggal_prm"] = 1

            st.markdown("**Prod. Date & Exp. Date**")

            tanggal_prm = []

            for i in range(st.session_state["jumlah_tanggal_prm"]):

                c_prod, c_exp = st.columns(2)

                with c_prod:
                    prod_date = st.date_input(
                        f"Prod. Date {i + 1}",
                        value=today,
                        format="DD-MM-YYYY",
                        key=f"prod_date_prm_{i}"
                    )

                with c_exp:
                    exp_date = st.date_input(
                        f"Exp. Date {i + 1}",
                        value=default_exp,
                        format="DD-MM-YYYY",
                        key=f"exp_date_prm_{i}"
                    )

                if exp_date < prod_date:
                    st.error(
                        f"Exp. Date {i + 1} tidak boleh lebih awal "
                        f"dari Prod. Date {i + 1}."
                    )

                tanggal_prm.append(
                    f"{prod_date.strftime('%d-%m-%Y')} → "
                    f"{exp_date.strftime('%d-%m-%Y')}"
                )


            col_tambah, col_hapus = st.columns(2)

            with col_tambah:
                if st.button(
                    "＋ Tambah Tanggal",
                    key="tambah_tanggal_prm",
                    use_container_width=True
                ):
                    st.session_state["jumlah_tanggal_prm"] += 1
                    st.rerun()

            with col_hapus:
                if (
                    st.session_state["jumlah_tanggal_prm"] > 1
                    and st.button(
                        "− Hapus Tanggal Terakhir",
                        key="hapus_tanggal_prm",
                        use_container_width=True
                    )
                ):
                    st.session_state["jumlah_tanggal_prm"] -= 1
                    st.rerun()


            prod_date_str = " | ".join(tanggal_prm)
            exp_date_str = " | ".join(
                [
                    st.session_state[f"exp_date_prm_{i}"].strftime("%d-%m-%Y")
                    for i in range(st.session_state["jumlah_tanggal_prm"])
                ]
            )

            jumlah_kedatangan = st.number_input(
                "Jumlah Kedatangan (kg) *",
                min_value=0,
                step=1,
                format="%d",
                key="jumlah_kedatangan"
            )

            no_po = st.text_input("No. PO *")
            no_grn = st.text_input("No. GRN *")

        with col2:
            st.markdown("**2. Informasi Sampling**")

            tanggal_sampling = st.date_input(
                "Tanggal Sampling *",
                value=today,
                format="YYYY-MM-DD"
            )

            petugas_sampling = st.selectbox(
                "Petugas Sampling",
                [
                    "FADLY",
                    "PAK DIDING"
                ],
                key="petugas_sampling"
            )

            metode_sampling = st.selectbox(
                "Metode Sampling *",
                [
                    "Military Standard 1916 Verification Level II",
                    "Random",
                    "10% per container",
                    "Based on bag qty",
                    "Batch"
                ]
            )

            jumlah_sampel = st.text_input("Jumlah Sampel (BAG)*")
            # ==========================================
            # NO LOT / PACKING CODE / BATCH
            # ==========================================

            if "jumlah_batch_prm" not in st.session_state:
                st.session_state["jumlah_batch_prm"] = 1

            st.markdown("**No Lot / Packing Code / Batch**")

            batch_prm = []

            for i in range(st.session_state["jumlah_batch_prm"]):

                nomor_lot_sap = st.text_input(
                    f"No Lot / Packing Code / Batch {i + 1}",
                    key=f"no_lot_prm_{i}"
                )

                batch_prm.append(nomor_lot_sap)


            col_tambah_batch, col_hapus_batch = st.columns(2)

            with col_tambah_batch:
                if st.button(
                    "＋ Tambah Batch",
                    key="tambah_batch_prm",
                    use_container_width=True
                ):
                    st.session_state["jumlah_batch_prm"] += 1
                    st.rerun()

            with col_hapus_batch:
                if (
                    st.session_state["jumlah_batch_prm"] > 1
                    and st.button(
                        "− Hapus Batch Terakhir",
                        key="hapus_batch_prm",
                        use_container_width=True
                    )
                ):
                    st.session_state["jumlah_batch_prm"] -= 1
                    st.rerun()


            # Gabungkan semua batch untuk disimpan ke database
            no_lot_packing_str = " | ".join(
                batch_prm
            )

        st.divider()

        st.markdown(
            "**3. Pemeriksaan Organoleptik, Keamanan, & Status Halal**"
        )

        c_orga1, c_orga2 = st.columns(2)

        with c_orga1:
            st.caption("A. Uji Organoleptik & Pest Infestation")

            orga_penampakan = st.selectbox(
                "Penampakan",
                ["OK", "Tidak OK"]
            )

            orga_rasa = st.selectbox(
                "Rasa",
                ["OK", "Tidak OK"]
            )

            orga_bau = st.selectbox(
                "Bau",
                ["OK", "Tidak OK"]
            )

            orga_warna_tekstur = st.selectbox(
                "Warna / Tekstur",
                ["OK", "Tidak OK"]
            )

            orga_ukuran = st.text_input("Ukuran")

            pest_infestation = st.selectbox(
                "Pest Infestation",
                ["Negative", "Positive"]
            )

        with c_orga2:
            st.caption("B. Legalitas & Sertifikasi Halal")

            logo_halal = st.selectbox(
                "Logo Halal pada Kemasan",
                ["Ada", "Tidak Ada"]
            )

            # ==========================================
            # MASA BERLAKU SERTIFIKAT HALAL
            # ==========================================

            pilihan_halal = st.radio(
                "Masa Berlaku Sertifikat Halal",
                [
                    "Ada Tanggal",
                    "Infinity"
                ],
                horizontal=True,
                key="pilihan_halal"
            )

            if pilihan_halal == "Ada Tanggal":

                exp_halal_cert = st.date_input(
                    "Tanggal Berlaku Sertifikat Halal",
                    value=today,
                    format="DD-MM-YYYY",
                    key="exp_halal_cert"
                )

                exp_halal_cert_str = exp_halal_cert.strftime("%d-%m-%Y")

            else:

                exp_halal_cert_str = "Infinity"

        st.divider()

        st.markdown("**4. Lot Packing & Hasil Analisa**")

        no_lot_packing = st.text_input(
            "No. Lot / Packing Code / Batch"
        )

        parameter_kiri = [
            "Acid Value",
            "Alveogram",
            "Berat Jenis",
            "Brix",
            "Dextrose Equivalent",
            "Dry Solid",
            "Fat content",
            "Fineness",
            "Free Fatty Acid",
            "Gluten",
            "Iodine Value",
            "Melting Point",
            "Metanol content"
        ]

        standar_kiri = [
            "mg KOH/g",
            "",
            "g/ml",
            "%",
            "%",
            "%",
            "µm",
            "%",
            "%",
            "%",
            "%",
            "°C",
            "%"
        ]

        parameter_kanan = [
            "Moisture",
            "Peroxide Value",
            "pH",
            "Purity",
            "Rancidity",
            "Total Plate Count",
            "Yeast/Mold",
            "Enterobacteriaceae",
            "Coliform",
            "Escherichia coli",
            "Salmonellae",
            "Others"
        ]

        standar_kanan = [
            "%",
            "meq O2 / kg",
            "",
            "%",
            "%",
            "/gm",
            "/gm",
            "/gm",
            "/gm",
            "negative",
            "negative",
            ""
        ]

        data_kiri = pd.DataFrame({
            "Parameter": parameter_kiri,
            "Hasil Analisa": [""] * len(parameter_kiri),
            "Standar": standar_kiri
        })

        data_kanan = pd.DataFrame({
            "Parameter": parameter_kanan,
            "Hasil Analisa": [""] * len(parameter_kanan),
            "Standar": standar_kanan
        })

        a1, a2 = st.columns(2)

        with a1:
            st.caption("Tabel Analisa (Grup 1)")

            hasil_kiri = st.data_editor(
                data_kiri,
                hide_index=True,
                use_container_width=True,
                disabled=["Parameter"],
                key="hkiri"
            )

        with a2:
            st.caption("Tabel Analisa (Grup 2)")

            hasil_kanan = st.data_editor(
                data_kanan,
                hide_index=True,
                use_container_width=True,
                disabled=["Parameter"],
                key="hkanan"
            )

        st.caption(
            "TD = Tidak Dipakai ; TP = Tidak Produksi"
        )

        keterangan_khusus = st.text_area(
            "Keterangan :",
            placeholder="Isi catatan atau keterangan hasil analisis di sini..."
        )

        st.divider()

        st.markdown("**5. Status & Pengesahan**")

        c_stat1, c_stat2 = st.columns(2)

        with c_stat1:
            status_incoming = st.radio(
                "Status",
                ["GOOD", "REJECTED", "WAIVED"],
                horizontal=True
            )

        with c_stat2:
            jumlah = st.number_input(
                "Jumlah (kg)",
                min_value=0,
                step=1,
                format="%d",
                key="jumlah"
            )

        st.write("---")
        st.markdown("**Pengesahan Personel QA:**")

        p1, p2 = st.columns(2)

        with p1:
            analis = st.text_input("Analis")

            tanggal_analis = st.date_input(
                "Tanggal Analis",
                value=None,
                format="YYYY-MM-DD"
            )

        with p2:
            qa_lab_supervisor = st.text_input(
                "QA Lab Supervisor"
            )

            tanggal_qa_lab = st.date_input(
                "Tanggal QA Lab Supervisor",
                value=None,
                format="YYYY-MM-DD"
            )

        p3, p4 = st.columns(2)

        with p3:
            qa_incoming_group_leader = st.text_input(
                "QA Incoming Group Leader"
            )

            tanggal_group_leader = st.date_input(
                "Tanggal Group Leader",
                value=None,
                format="YYYY-MM-DD"
            )

        with p4:
            qa_incoming_supervisor = st.text_input(
                "QA Incoming Supervisor"
            )

            tanggal_supervisor = st.date_input(
                "Tanggal Supervisor",
                value=None,
                format="YYYY-MM-DD"
            )

        st.divider()

        if st.button(
            "Simpan Draft",
            type="primary",
            use_container_width=True,
            key="simpan_draft_prm"
        ):
            conn = sqlite3.connect("incoming.db")
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO incoming (
                    ref_no,
                    nama_raw_material,
                    kode_raw_material,
                    pabrik,
                    supplier,
                    prod_date,
                    exp_date,
                    jumlah,
                    no_po,
                    no_grn,
                    tanggal_sampling,
                    petugas_sampling,
                    metode_sampling,
                    no_lot_sap,
                    jumlah_sampel,
                    orga_penampakan,
                    orga_rasa,
                    orga_bau,
                    orga_warna_tekstur,
                    orga_ukuran,
                    pest_infestation,
                    logo_halal,
                    exp_halal_cert,
                    no_lot_packing,
                    status,
                    jumlah_status,
                    keterangan,
                    analis,
                    tanggal_analis,
                    qa_lab_supervisor,
                    tanggal_qa_lab,
                    qa_incoming_group_leader,
                    tanggal_group_leader,
                    qa_incoming_supervisor,
                    tanggal_supervisor
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    ref_no_full,
                    nama_raw_material,
                    kode_raw_material,
                    pabrik,
                    supplier,
                    prod_date_str,
                    exp_date_str,
                    jumlah,
                    no_po,
                    no_grn,
                    str(tanggal_sampling),
                    petugas_sampling,
                    metode_sampling,
                    nomor_lot_sap,
                    jumlah_sampel,
                    orga_penampakan,
                    orga_rasa,
                    orga_bau,
                    orga_warna_tekstur,
                    orga_ukuran,
                    pest_infestation,
                    logo_halal,
                    str(exp_halal_cert),
                    no_lot_packing,
                    status_incoming,
                    jumlah,
                    keterangan_khusus,
                    analis,
                    str(tanggal_analis) if tanggal_analis else "",
                    qa_lab_supervisor,
                    str(tanggal_qa_lab) if tanggal_qa_lab else "",
                    qa_incoming_group_leader,
                    str(tanggal_group_leader) if tanggal_group_leader else "",
                    qa_incoming_supervisor,
                    str(tanggal_supervisor) if tanggal_supervisor else ""
                )
            )

            incoming_id = cursor.lastrowid

            semua_analisa = pd.concat(
                [hasil_kiri, hasil_kanan],
                ignore_index=True
            )

            for _, row in semua_analisa.iterrows():
                if (
                    str(row["Hasil Analisa"]).strip() != ""
                    or str(row["Standar"]).strip() != ""
                ):
                    cursor.execute(
                        """
                        INSERT INTO hasil_analisa
                        (incoming_id, parameter, hasil_analisa, standar)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            incoming_id,
                            str(row["Parameter"]),
                            str(row["Hasil Analisa"]),
                            str(row["Standar"])
                        )
                    )

            conn.commit()
            conn.close()

            catat_riwayat(
                incoming_id,
                "Tambah Data",
                f"Menambahkan data {ref_no_full}"
            )

            st.session_state["data_tersimpan"] = True
            st.rerun()


    # =====================================================
    # 2. DATABASE
    # =====================================================
    with tab_db:
        st.subheader("Database Pemeriksaan Raw Material")

        conn = sqlite3.connect("incoming.db")

        df_data = pd.read_sql_query(
            "SELECT * FROM incoming ORDER BY id DESC",
            conn
        )

        conn.close()

        if df_data.empty:
            st.info("Belum ada data yang tersimpan.")

        else:
            kata_kunci = st.text_input(
                "Cari berdasarkan Ref No / Nama / Kode Material / Supplier:"
            )

            if kata_kunci:
                df_filtered = df_data[
                    df_data["ref_no"].astype(str).str.contains(
                        kata_kunci, case=False, na=False
                    )
                    |
                    df_data["nama_raw_material"].astype(str).str.contains(
                        kata_kunci, case=False, na=False
                    )
                    |
                    df_data["kode_raw_material"].astype(str).str.contains(
                        kata_kunci, case=False, na=False
                    )
                    |
                    df_data["supplier"].astype(str).str.contains(
                        kata_kunci, case=False, na=False
                    )
                ]
            else:
                df_filtered = df_data

            st.divider()

            # Header tabel + tombol aksi langsung di baris yang sama.
            header = st.columns(
                [0.5, 1.5, 2, 1.5, 1.5, 1.2, 0.8, 0.8, 0.8]
            )

            with header[0]:
                st.markdown("**ID**")

            with header[1]:
                st.markdown("**Ref. No**")

            with header[2]:
                st.markdown("**Raw Material**")

            with header[3]:
                st.markdown("**Kode**")

            with header[4]:
                st.markdown("**Supplier**")

            with header[5]:
                st.markdown("**Status**")

            with header[6]:
                st.markdown("**Edit**")

            with header[7]:
                st.markdown("**Hapus**")

            with header[8]:
                st.markdown("**Detail**")

            st.divider()

            for _, row in df_filtered.iterrows():

                kolom = st.columns(
                    [0.5, 1.5, 2, 1.5, 1.5, 1.2, 0.8, 0.8, 0.8]
                )

                with kolom[0]:
                    st.write(int(row["id"]))

                with kolom[1]:
                    st.write(row["ref_no"])

                with kolom[2]:
                    st.write(row["nama_raw_material"])

                with kolom[3]:
                    st.write(row["kode_raw_material"])

                with kolom[4]:
                    st.write(row["supplier"])

                with kolom[5]:
                    st.write(row["status"])

                with kolom[6]:
                    if st.button(
                        "Edit",
                        key=f"edit_{row['id']}",
                        use_container_width=True
                    ):
                        st.session_state["edit_id"] = int(row["id"])
                        st.session_state["detail_id"] = None
                        st.session_state["delete_id"] = None
                        st.rerun()

                with kolom[7]:
                    if st.button(
                        "Hapus",
                        key=f"hapus_{row['id']}",
                        use_container_width=True
                    ):
                        st.session_state["delete_id"] = int(row["id"])
                        st.session_state["edit_id"] = None
                        st.session_state["detail_id"] = None
                        st.rerun()

                with kolom[8]:
                    if st.button(
                        "Detail",
                        key=f"detail_{row['id']}",
                        use_container_width=True
                    ):
                        st.session_state["detail_id"] = int(row["id"])
                        st.session_state["edit_id"] = None
                        st.session_state["delete_id"] = None
                        st.rerun()

            # =========================
            # KONFIRMASI HAPUS
            # =========================
            if st.session_state["delete_id"]:
                delete_id = st.session_state["delete_id"]

                conn = sqlite3.connect("incoming.db")

                data_hapus = pd.read_sql_query(
                    "SELECT * FROM incoming WHERE id = ?",
                    conn,
                    params=(delete_id,)
                )

                conn.close()

                if not data_hapus.empty:
                    data_hapus = data_hapus.iloc[0]

                    st.divider()

                    st.warning(
                        f"Apakah kamu yakin ingin menghapus data "
                        f"**{data_hapus['ref_no']} - "
                        f"{data_hapus['nama_raw_material']}**?"
                    )

                    # Masukkan password
                    password_hapus = st.text_input(
                        "Masukkan password untuk menghapus data:",
                        type="password",
                        key=f"password_hapus_{delete_id}"
                    )

                    c_hapus1, c_hapus2 = st.columns(2)

                    with c_hapus1:
                        if st.button(
                            "Ya, Hapus Data",
                            type="primary",
                            use_container_width=True,
                            key=f"konfirmasi_hapus_{delete_id}"
                        ):

                            # Cek password user yang sedang login
                            conn = sqlite3.connect("incoming.db")
                            cursor = conn.cursor()

                            cursor.execute(
                                """
                                SELECT id
                                FROM users
                                WHERE username = ?
                                AND password = ?
                                """,
                                (
                                    st.session_state.get("username", ""),
                                    password_hapus
                                )
                            )

                            password_benar = cursor.fetchone()

                            if password_benar:
                                # Hapus hasil analisa terlebih dahulu
                                cursor.execute(
                                    "DELETE FROM hasil_analisa WHERE incoming_id = ?",
                                    (delete_id,)
                                )

                                # Hapus data incoming
                                cursor.execute(
                                    "DELETE FROM incoming WHERE id = ?",
                                    (delete_id,)
                                )

                                conn.commit()
                                conn.close()

                                # Catat riwayat
                                catat_riwayat(
                                    delete_id,
                                    "Hapus Data",
                                    f"Menghapus data "
                                    f"{data_hapus['ref_no']} - "
                                    f"{data_hapus['nama_raw_material']}"
                                )

                                st.session_state["delete_id"] = None

                                st.success("Data berhasil dihapus.")
                                st.rerun()

                            else:
                                conn.close()
                                st.error("Password salah. Data tidak dihapus.")

                    with c_hapus2:
                        if st.button(
                            "Batal",
                            use_container_width=True,
                            key=f"batal_hapus_{delete_id}"
                        ):
                            st.session_state["delete_id"] = None
                            st.rerun()


            # -------------------------------------------------
            # EDIT DATA
            # -------------------------------------------------
            if st.session_state["edit_id"]:

                edit_id = st.session_state["edit_id"]

                conn = sqlite3.connect("incoming.db")

                data_edit = pd.read_sql_query(
                    "SELECT * FROM incoming WHERE id = ?",
                    conn,
                    params=(edit_id,)
                )

                hasil_edit = pd.read_sql_query(
                    """
                    SELECT parameter, hasil_analisa, standar
                    FROM hasil_analisa
                    WHERE incoming_id = ?
                    ORDER BY id
                    """,
                    conn,
                    params=(edit_id,)
                )

                conn.close()

                if not data_edit.empty:

                    data_edit = data_edit.iloc[0]

                    st.divider()
                    st.subheader("Edit Data Incoming")

                    st.markdown("### 1. Informasi Raw Material")

                    e1, e2 = st.columns(2)

                    with e1:
                        edit_ref_no = st.text_input(
                            "Ref No",
                            value=str(data_edit["ref_no"] or "")
                        )

                        edit_nama = st.text_input(
                            "Nama Raw Material",
                            value=str(
                                data_edit["nama_raw_material"] or ""
                            )
                        )

                        edit_kode = st.text_input(
                            "Kode Raw Material",
                            value=str(
                                data_edit["kode_raw_material"] or ""
                            )
                        )

                        edit_pabrik = st.text_input(
                            "Pabrik/Merek - Negara Asal",
                            value=str(data_edit["pabrik"] or "")
                        )

                        edit_supplier = st.text_input(
                            "Supplier",
                            value=str(data_edit["supplier"] or "")
                        )

                        edit_prod_date = st.text_input(
                            "Prod. Date",
                            value=str(data_edit["prod_date"] or "")
                        )

                        edit_exp_date = st.text_input(
                            "Exp. Date",
                            value=str(data_edit["exp_date"] or "")
                        )

                    with e2:
                        edit_jumlah = st.number_input(
                            "Jumlah (kg)",
                            min_value=0.0,
                            value=float(data_edit["jumlah"] or 0),
                            step=0.01
                        )

                        edit_no_po = st.text_input(
                            "No. PO",
                            value=str(data_edit["no_po"] or "")
                        )

                        edit_no_grn = st.text_input(
                            "No. GRN",
                            value=str(data_edit["no_grn"] or "")
                        )

                        edit_no_lot_sap = st.text_input(
                            "No. Lot SAP",
                            value=str(data_edit["no_lot_sap"] or "")
                        )

                        edit_jumlah_sampel = st.text_input(
                            "Jumlah Sampel",
                            value=str(
                                data_edit["jumlah_sampel"] or ""
                            )
                        )

                    st.markdown("### 2. Informasi Sampling")

                    e1, e2 = st.columns(2)

                    with e1:
                        edit_tanggal_sampling = st.text_input(
                            "Tanggal Sampling",
                            value=str(
                                data_edit["tanggal_sampling"] or ""
                            )
                        )

                        edit_petugas_sampling = st.text_input(
                            "Petugas Sampling",
                            value=str(
                                data_edit["petugas_sampling"] or ""
                            )
                        )

                    with e2:
                        pilihan_metode = [
                            "Military Standard 1916 Verification Level II",
                            "Random",
                            "10% per container",
                            "Based on bag qty",
                            "Batch"
                        ]

                        metode_lama = str(
                            data_edit["metode_sampling"] or ""
                        )

                        if (
                            metode_lama
                            and metode_lama not in pilihan_metode
                        ):
                            pilihan_metode.append(metode_lama)

                        edit_metode_sampling = st.selectbox(
                            "Metode Sampling",
                            pilihan_metode,
                            index=(
                                pilihan_metode.index(metode_lama)
                                if metode_lama in pilihan_metode
                                else 0
                            ),
                            key=f"edit_metode_sampling_{edit_id}"
                        )

                    st.markdown(
                        "### 3. Pemeriksaan Organoleptik & Keamanan"
                    )

                    e1, e2 = st.columns(2)

                    pilihan_ok = ["OK", "Tidak OK"]

                    with e1:
                        nilai_penampakan = str(
                            data_edit["orga_penampakan"] or "OK"
                        )

                        edit_penampakan = st.selectbox(
                            "Penampakan",
                            pilihan_ok,
                            index=(
                                pilihan_ok.index(nilai_penampakan)
                                if nilai_penampakan in pilihan_ok
                                else 0
                            ),
                            key=f"edit_penampakan_{edit_id}"
                        )

                        nilai_rasa = str(
                            data_edit["orga_rasa"] or "OK"
                        )

                        edit_rasa = st.selectbox(
                            "Rasa",
                            pilihan_ok,
                            index=(
                                pilihan_ok.index(nilai_rasa)
                                if nilai_rasa in pilihan_ok
                                else 0
                            ),
                            key=f"edit_rasa_{edit_id}"
                        )

                        nilai_bau = str(
                            data_edit["orga_bau"] or "OK"
                        )

                        edit_bau = st.selectbox(
                            "Bau",
                            pilihan_ok,
                            index=(
                                pilihan_ok.index(nilai_bau)
                                if nilai_bau in pilihan_ok
                                else 0
                            ),
                            key=f"edit_bau_{edit_id}"
                        )

                        nilai_warna = str(
                            data_edit["orga_warna_tekstur"] or "OK"
                        )

                        edit_warna = st.selectbox(
                            "Warna / Tekstur",
                            pilihan_ok,
                            index=(
                                pilihan_ok.index(nilai_warna)
                                if nilai_warna in pilihan_ok
                                else 0
                            ),
                            key=f"edit_warna_{edit_id}"
                        )

                        edit_ukuran = st.text_input(
                            "Ukuran",
                            value=str(data_edit["orga_ukuran"] or ""),
                            key="edit_ukuran_prm"
                            
                        )

                        pilihan_pest = ["Negative", "Positive"]

                        nilai_pest = str(
                            data_edit["pest_infestation"] or "Negative"
                        )

                        edit_pest = st.selectbox(
                            "Pest Infestation",
                            pilihan_pest,
                            index=(
                                pilihan_pest.index(nilai_pest)
                                if nilai_pest in pilihan_pest
                                else 0
                            ),
                            key=f"edit_pest_{edit_id}"
                        )

                    with e2:
                        pilihan_halal = ["Ada", "Tidak Ada"]

                        nilai_halal = str(
                            data_edit["logo_halal"] or "Ada"
                        )

                        edit_logo_halal = st.selectbox(
                            "Logo Halal pada Kemasan",
                            pilihan_halal,
                            index=(
                                pilihan_halal.index(nilai_halal)
                                if nilai_halal in pilihan_halal
                                else 0
                            ),
                            key=f"edit_logo_halal_{edit_id}"
                        )

                        edit_exp_halal = st.text_input(
                            "Masa Berlaku Sertifikat Halal",
                            value=str(
                                data_edit["exp_halal_cert"] or ""
                            )
                        )

                        edit_no_lot_packing = st.text_input(
                            "No. Lot / Packing Code / Batch",
                            value=str(data_edit["no_lot_packing"] or ""),
                            key="edit_no_lot_packing_prm"
                        )

                    st.markdown("### 4. Hasil Analisa")

                    if hasil_edit.empty:
                        edit_hasil = pd.DataFrame({
                            "Parameter": [],
                            "Hasil Analisa": [],
                            "Standar": []
                        })
                    else:
                        edit_hasil = hasil_edit.rename(
                            columns={
                                "parameter": "Parameter",
                                "hasil_analisa": "Hasil Analisa",
                                "standar": "Standar"
                            }
                        )

                    edit_hasil = st.data_editor(
                        edit_hasil,
                        hide_index=True,
                        use_container_width=True,
                        disabled=["Parameter"],
                        key=f"edit_hasil_{edit_id}"
                    )

                    edit_keterangan = st.text_area(
                        "Keterangan",
                        value=str(data_edit["keterangan"] or "")
                    )

                    st.markdown("### 5. Status")

                    e1, e2 = st.columns(2)

                    pilihan_status = [
                        "GOOD",
                        "REJECTED",
                        "WAIVED"
                    ]

                    status_lama = str(
                        data_edit["status"] or "GOOD"
                    )

                    with e1:
                        edit_status = st.radio(
                            "Status",
                            pilihan_status,
                            index=(
                                pilihan_status.index(status_lama)
                                if status_lama in pilihan_status
                                else 0
                            ),
                            horizontal=True,
                            key=f"edit_status_{edit_id}"
                        )

                    with e2:
                        edit_jumlah_status = st.number_input(
                            "Jumlah (kg)",
                            min_value=0.0,
                            value=float(
                                data_edit["jumlah_status"] or 0
                            ),
                            step=0.01,
                            key=f"edit_jumlah_status_{edit_id}"
                        )

                    st.markdown("### 6. Pengesahan Personel QA")

                    e1, e2 = st.columns(2)

                    with e1:
                        edit_analis = st.text_input(
                            "Analis",
                            value=str(data_edit["analis"] or ""),
                            key=f"edit_analis_{edit_id}"
                        )

                        edit_tanggal_analis = st.text_input(
                            "Tanggal Analis",
                            value=str(
                                data_edit["tanggal_analis"] or ""
                        )
                    )

                        edit_qa_lab = st.text_input(
                            "QA Lab Supervisor",
                            value=str(
                                data_edit["qa_lab_supervisor"] or ""),
                                key=f"edit_qa_lab_{edit_id}"
                        
                        )
                        edit_tanggal_qa_lab = st.text_input(
                            "Tanggal QA Lab Supervisor",
                            value=str(
                                data_edit["tanggal_qa_lab"] or ""
                            )
                        )

                    with e2:
                        edit_group_leader = st.text_input(
                            "QA Incoming Group Leader",
                            value=str(data_edit["qa_incoming_group_leader"] or ""),
                            key=f"edit_group_leader_{edit_id}"
                            
                        )

                        edit_tanggal_group = st.text_input(
                            "Tanggal Group Leader",
                            value=str(
                                data_edit["tanggal_group_leader"] or ""
                            )
                        )

                        edit_supervisor = st.text_input(
                            "QA Incoming Supervisor",
                            value=str(data_edit["qa_incoming_supervisor"] or ""),
                            key=f"edit_supervisor_{edit_id}"
                            
                        )

                        edit_tanggal_supervisor = st.text_input(
                            "Tanggal Supervisor",
                            value=str(
                                data_edit["tanggal_supervisor"] or ""
                            )
                        )

                    st.divider()

                    simpan_edit, batal_edit = st.columns(2)

                    with simpan_edit:
                        if st.button(
                            "Simpan Perubahan",
                            type="primary",
                            use_container_width=True
                        ):
                            conn = sqlite3.connect("incoming.db")
                            cursor = conn.cursor()

                            cursor.execute(
                                """
                                UPDATE incoming
                                SET
                                    ref_no = ?,
                                    nama_raw_material = ?,
                                    kode_raw_material = ?,
                                    pabrik = ?,
                                    supplier = ?,
                                    prod_date = ?,
                                    exp_date = ?,
                                    jumlah = ?,
                                    no_po = ?,
                                    no_grn = ?,
                                    tanggal_sampling = ?,
                                    petugas_sampling = ?,
                                    metode_sampling = ?,
                                    no_lot_sap = ?,
                                    jumlah_sampel = ?,
                                    orga_penampakan = ?,
                                    orga_rasa = ?,
                                    orga_bau = ?,
                                    orga_warna_tekstur = ?,
                                    orga_ukuran = ?,
                                    pest_infestation = ?,
                                    logo_halal = ?,
                                    exp_halal_cert = ?,
                                    no_lot_packing = ?,
                                    status = ?,
                                    jumlah_status = ?,
                                    keterangan = ?,
                                    analis = ?,
                                    tanggal_analis = ?,
                                    qa_lab_supervisor = ?,
                                    tanggal_qa_lab = ?,
                                    qa_incoming_group_leader = ?,
                                    tanggal_group_leader = ?,
                                    qa_incoming_supervisor = ?,
                                    tanggal_supervisor = ?
                                WHERE id = ?
                                """,
                                (
                                    edit_ref_no,
                                    edit_nama,
                                    edit_kode,
                                    edit_pabrik,
                                    edit_supplier,
                                    edit_prod_date,
                                    edit_exp_date,
                                    edit_jumlah,
                                    edit_no_po,
                                    edit_no_grn,
                                    edit_tanggal_sampling,
                                    edit_petugas_sampling,
                                    edit_metode_sampling,
                                    edit_no_lot_sap,
                                    edit_jumlah_sampel,
                                    edit_penampakan,
                                    edit_rasa,
                                    edit_bau,
                                    edit_warna,
                                    edit_ukuran,
                                    edit_pest,
                                    edit_logo_halal,
                                    edit_exp_halal,
                                    edit_no_lot_packing,
                                    edit_status,
                                    edit_jumlah_status,
                                    edit_keterangan,
                                    edit_analis,
                                    edit_tanggal_analis,
                                    edit_qa_lab,
                                    edit_tanggal_qa_lab,
                                    edit_group_leader,
                                    edit_tanggal_group,
                                    edit_supervisor,
                                    edit_tanggal_supervisor,
                                    edit_id
                                )
                            )

                            cursor.execute(
                                "DELETE FROM hasil_analisa WHERE incoming_id = ?",
                                (edit_id,)
                            )

                            for _, hasil in edit_hasil.iterrows():
                                if (
                                    str(
                                        hasil["Hasil Analisa"]
                                    ).strip() != ""
                                    or str(
                                        hasil["Standar"]
                                    ).strip() != ""
                                ):
                                    cursor.execute(
                                        """
                                        INSERT INTO hasil_analisa
                                        (
                                            incoming_id,
                                            parameter,
                                            hasil_analisa,
                                            standar
                                        )
                                        VALUES (?, ?, ?, ?)
                                        """,
                                        (
                                            edit_id,
                                            str(hasil["Parameter"]),
                                            str(
                                                hasil["Hasil Analisa"]
                                            ),
                                            str(hasil["Standar"])
                                        )
                                    )

                            conn.commit()
                            conn.close()

                            catat_riwayat(
                                edit_id,
                                "Edit Data",
                                f"Memperbarui data {edit_ref_no}"
                            )

                            st.session_state["edit_id"] = None
                            st.success(
                                "Data berhasil diperbarui."
                            )
                            st.rerun()

                    with batal_edit:
                        if st.button(
                            "Batal Edit",
                            use_container_width=True
                        ):
                            st.session_state["edit_id"] = None
                            st.rerun()

            # =========================================================
            # PROSES HAPUS DATA
            # =========================================================
            if "hapus_sample_id" in st.session_state:

                hapus_id = st.session_state["hapus_sample_id"]

                st.warning("Data ini akan dihapus beserta seluruh hasil pengujiannya.")

                konfirmasi_hapus = st.checkbox(
                    "Saya yakin ingin menghapus data ini.",
                    key=f"konfirmasi_hapus_{hapus_id}"
                )

                if konfirmasi_hapus:

                    if st.button(
                        "Konfirmasi Hapus",
                        key=f"konfirmasi_hapus_button_{hapus_id}"
                    ):

                        conn_hapus = sqlite3.connect("incoming.db")
                        cursor_hapus = conn_hapus.cursor()

                        # Hapus riwayat
                        cursor_hapus.execute(
                            """
                            DELETE FROM logbook_riwayat
                            WHERE sample_id = ?
                            """,
                            (hapus_id,)
                        )

                        # Hapus hasil pengujian
                        cursor_hapus.execute(
                            """
                            DELETE FROM logbook_result
                            WHERE sample_id = ?
                            """,
                            (hapus_id,)
                        )

                        # Hapus data sampel
                        cursor_hapus.execute(
                            """
                            DELETE FROM logbook_sample
                            WHERE id = ?
                            """,
                            (hapus_id,)
                        )

                        conn_hapus.commit()
                        conn_hapus.close()

                        del st.session_state["hapus_sample_id"]

                        st.success("Data berhasil dihapus.")
                        st.rerun()

            # -------------------------------------------------
            # DETAIL DATA
            # -------------------------------------------------
            if st.session_state["detail_id"]:

                detail_id = st.session_state["detail_id"]

                conn = sqlite3.connect("incoming.db")

                detail = pd.read_sql_query(
                    "SELECT * FROM incoming WHERE id = ?",
                    conn,
                    params=(detail_id,)
                )

                hasil_analisa_detail = pd.read_sql_query(
                    """
                    SELECT parameter, hasil_analisa, standar
                    FROM hasil_analisa
                    WHERE incoming_id = ?
                    ORDER BY id
                    """,
                    conn,
                    params=(detail_id,)
                )

                conn.close()

                if not detail.empty:

                    data = detail.iloc[0]

                    st.divider()
                    st.subheader(
                        "Detail Pemeriksaan Raw Material"
                    )

                    st.markdown("### 1. Informasi Raw Material")

                    d1, d2 = st.columns(2)

                    with d1:
                        st.write(
                            "**Ref No:**",
                            data["ref_no"]
                        )
                        st.write(
                            "**Nama Raw Material:**",
                            data["nama_raw_material"]
                        )
                        st.write(
                            "**Kode Raw Material:**",
                            data["kode_raw_material"]
                        )
                        st.write(
                            "**Pabrik/Merek - Negara Asal:**",
                            data["pabrik"]
                        )
                        st.write(
                            "**Supplier:**",
                            data["supplier"]
                        )
                        st.write(
                            "**Prod. Date:**",
                            data["prod_date"]
                        )
                        st.write(
                            "**Exp. Date:**",
                            data["exp_date"]
                        )

                    with d2:
                        st.write(
                            "**Jumlah:**",
                            data["jumlah"],
                            "kg"
                        )
                        st.write(
                            "**No. PO:**",
                            data["no_po"]
                        )
                        st.write(
                            "**No. GRN:**",
                            data["no_grn"]
                        )
                        st.write(
                            "**No. Lot SAP:**",
                            data["no_lot_sap"]
                        )
                        st.write(
                            "**Jumlah Sampel:**",
                            data["jumlah_sampel"]
                        )

                    st.divider()

                    st.markdown("### 2. Informasi Sampling")

                    d1, d2 = st.columns(2)

                    with d1:
                        st.write(
                            "**Tanggal Sampling:**",
                            data["tanggal_sampling"]
                        )
                        st.write(
                            "**Petugas Sampling:**",
                            data["petugas_sampling"]
                        )

                    with d2:
                        st.write(
                            "**Metode Sampling:**",
                            data["metode_sampling"]
                        )

                    st.divider()

                    st.markdown(
                        "### 3. Pemeriksaan Organoleptik & Keamanan"
                    )

                    d1, d2 = st.columns(2)

                    with d1:
                        st.write(
                            "**Penampakan:**",
                            data["orga_penampakan"]
                        )
                        st.write(
                            "**Rasa:**",
                            data["orga_rasa"]
                        )
                        st.write(
                            "**Bau:**",
                            data["orga_bau"]
                        )
                        st.write(
                            "**Warna / Tekstur:**",
                            data["orga_warna_tekstur"]
                        )
                        st.write(
                            "**Ukuran:**",
                            data["orga_ukuran"]
                        )
                        st.write(
                            "**Pest Infestation:**",
                            data["pest_infestation"]
                        )

                    with d2:
                        st.write(
                            "**Logo Halal pada Kemasan:**",
                            data["logo_halal"]
                        )
                        st.write(
                            "**Masa Berlaku Sertifikat Halal:**",
                            data["exp_halal_cert"]
                        )
                        st.write(
                            "**No. Lot / Packing Code / Batch:**",
                            data["no_lot_packing"]
                        )

                    st.divider()

                    st.markdown("### 4. Hasil Analisa")

                    if hasil_analisa_detail.empty:
                        st.info("Belum ada hasil analisa.")
                    else:
                        st.dataframe(
                            hasil_analisa_detail,
                            use_container_width=True,
                            hide_index=True
                        )

                    st.write(
                        "**Keterangan:**",
                        data["keterangan"]
                    )

                    st.divider()

                    st.markdown("### 5. Status")

                    d1, d2 = st.columns(2)

                    with d1:
                        st.write(
                            "**Status:**",
                            data["status"]
                        )

                    with d2:
                        st.write(
                            "**Jumlah:**",
                            data["jumlah_status"],
                            "kg"
                        )

                    st.divider()

                    st.markdown(
                        "### 6. Pengesahan Personel QA"
                    )

                    d1, d2 = st.columns(2)

                    with d1:
                        st.write(
                            "**Analis:**",
                            data["analis"]
                        )
                        st.write(
                            "**Tanggal Analis:**",
                            data["tanggal_analis"]
                        )
                        st.write(
                            "**QA Lab Supervisor:**",
                            data["qa_lab_supervisor"]
                        )
                        st.write(
                            "**Tanggal QA Lab:**",
                            data["tanggal_qa_lab"]
                        )

                    with d2:
                        st.write(
                            "**QA Incoming Group Leader:**",
                            data["qa_incoming_group_leader"]
                        )
                        st.write(
                            "**Tanggal Group Leader:**",
                            data["tanggal_group_leader"]
                        )
                        st.write(
                            "**QA Incoming Supervisor:**",
                            data["qa_incoming_supervisor"]
                        )
                        st.write(
                            "**Tanggal Supervisor:**",
                            data["tanggal_supervisor"]
                        )

                    st.divider()

                    # PDF langsung menggunakan data detail yang sedang dibuka.
                    pdf_file = buat_pdf_incoming(
                        data,
                        hasil_analisa_detail
                    )

                    st.download_button(
                        label="Download PDF",
                        data=pdf_file,
                        file_name=(
                            f"Incoming_"
                            f"{str(data['ref_no']).replace('/', '_')}.pdf"
                        ),
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"download_pdf_{detail_id}"
                    )

                    if st.button(
                        "Tutup Detail",
                        use_container_width=True,
                        key=f"tutup_detail_{detail_id}"
                    ):
                        st.session_state["detail_id"] = None
                        st.rerun()

            # -------------------------------------------------
            # DOWNLOAD EXCEL
            # -------------------------------------------------
            st.divider()

            buffer_excel = BytesIO()

            with pd.ExcelWriter(
                buffer_excel,
                engine="openpyxl"
            ) as writer:

                df_filtered.to_excel(
                    writer,
                    index=False,
                    sheet_name="Database Incoming"
                )

                conn = sqlite3.connect("incoming.db")

                df_analisa = pd.read_sql_query(
                    """
                    SELECT
                        hasil_analisa.id,
                        hasil_analisa.incoming_id,
                        incoming.ref_no,
                        incoming.nama_raw_material,
                        hasil_analisa.parameter,
                        hasil_analisa.hasil_analisa,
                        hasil_analisa.standar
                    FROM hasil_analisa
                    LEFT JOIN incoming
                        ON hasil_analisa.incoming_id = incoming.id
                    ORDER BY hasil_analisa.id DESC
                    """,
                    conn
                )

                conn.close()

                df_analisa.to_excel(
                    writer,
                    index=False,
                    sheet_name="Hasil Analisa"
                )

            buffer_excel.seek(0)

            st.download_button(
                label="Download Excel",
                data=buffer_excel,
                file_name="Database_Incoming_Raw_Material.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="download_excel_database"
            )


    # =====================================================
    # 3. RIWAYAT PERUBAHAN
    # =====================================================
    with tab_riwayat:
        st.subheader("Riwayat Perubahan Data")

        conn = sqlite3.connect("incoming.db")

        df_riwayat = pd.read_sql_query(
            """
            SELECT *
            FROM riwayat_perubahan
            ORDER BY id DESC
            """,
            conn
        )

        conn.close()

        if df_riwayat.empty:
            st.info("Belum ada riwayat perubahan data.")
        else:
            st.dataframe(
                df_riwayat,
                use_container_width=True,
                hide_index=True
            )


    # =====================================================
    # 5. MANAJEMEN USER
    # =====================================================
    with tab_user:
        st.subheader("Manajemen User")

        # Hanya Administrator yang boleh mengelola user.
        if st.session_state["role"] != "Administrator":
            st.warning(
                "Hanya Administrator yang dapat mengakses Manajemen User."
            )

        else:
            st.markdown("### Tambah User")

            u1, u2 = st.columns(2)

            with u1:
                new_username = st.text_input(
                    "Username Baru",
                    key="new_username"
                )

                new_password = st.text_input(
                    "Password Baru",
                    type="password",
                    key="new_password"
                )

            with u2:
                new_role = st.selectbox(
                    "Role",
                    [
                        "Operator",
                        "QA",
                        "Administrator"
                    ],
                    key="new_role"
                )

            if st.button(
                "Tambah User",
                type="primary",
                use_container_width=True
            ):
                if not new_username.strip():
                    st.error("Username wajib diisi.")

                elif not new_password:
                    st.error("Password wajib diisi.")

                else:
                    conn = sqlite3.connect("incoming.db")
                    cursor = conn.cursor()

                    try:
                        cursor.execute(
                            """
                            INSERT INTO users
                            (username, password, role)
                            VALUES (?, ?, ?)
                            """,
                            (
                                new_username.strip(),
                                new_password,
                                new_role
                            )
                        )

                        conn.commit()
                        st.success(
                            f"User {new_username} berhasil ditambahkan."
                        )
                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error(
                            "Username tersebut sudah digunakan."
                        )

                    finally:
                        conn.close()

            st.divider()

            st.markdown("### Daftar User")

            conn = sqlite3.connect("incoming.db")

            df_users = pd.read_sql_query(
                """
                SELECT id, username, role
                FROM users
                ORDER BY id
                """,
                conn
            )

            conn.close()

            if df_users.empty:
                st.info("Belum ada user.")

            else:
                st.dataframe(
                    df_users,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("### Hapus User")

                user_options = df_users[
                    df_users["username"] != "admin"
                ]["username"].tolist()

                if user_options:
                    username_hapus = st.selectbox(
                        "Pilih username yang akan dihapus",
                        user_options
                    )

                    if st.button(
                        "Hapus User",
                        use_container_width=True
                    ):
                        conn = sqlite3.connect("incoming.db")
                        cursor = conn.cursor()

                        cursor.execute(
                            "DELETE FROM users WHERE username = ?",
                            (username_hapus,)
                        )

                        conn.commit()
                        conn.close()

                        st.success(
                            f"User {username_hapus} berhasil dihapus."
                        )
                        st.rerun()
                else:
                    st.info(
                        "User admin tidak dapat dihapus "
                        "melalui menu ini."
                    )

elif menu == "Master Data":

    st.title("Master Data")

    st.subheader("Raw Material")

    kode_master = st.text_input(
        "Kode Raw Material",
        key="kode_master_raw"
    )

    nama_master = st.text_input(
        "Nama Raw Material",
        key="nama_master_raw"
    )

    if st.button(
        "Simpan Raw Material",
        type="primary",
        use_container_width=True,
        key="simpan_master_raw"
    ):
        if not kode_master or not nama_master:
            st.error(
                "Kode Raw Material dan Nama Raw Material wajib diisi."
            )
        else:
            conn_master = sqlite3.connect("incoming.db")
            cursor_master = conn_master.cursor()

            try:
                cursor_master.execute(
                    """
                    INSERT INTO master_raw_material
                    (
                        kode_raw_material,
                        nama_raw_material
                    )
                    VALUES (?, ?)
                    """,
                    (
                        kode_master,
                        nama_master
                    )
                )

                conn_master.commit()
                st.success("Raw Material berhasil disimpan.")

            except sqlite3.IntegrityError:
                st.error(
                    "Kode Raw Material sudah ada."
                )

            finally:
                conn_master.close()

    st.divider()
    st.subheader("Data Raw Material")

    conn_master = sqlite3.connect("incoming.db")

    data_master = pd.read_sql_query(
        """
        SELECT
            kode_raw_material AS "Kode Raw Material",
            nama_raw_material AS "Nama Raw Material"
        FROM master_raw_material
        ORDER BY id DESC
        """,
        conn_master
    )

    conn_master.close()

    st.dataframe(
        data_master,
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.subheader("Import Banyak Data")

    file_master = st.file_uploader(
        "Upload Excel Master Data",
        type=["xlsx"],
        key="upload_master_data"
    )

    if file_master is not None:

        data_import = pd.read_excel(file_master)

        # Rapikan nama kolom
        data_import.columns = data_import.columns.astype(str).str.strip()

        kolom_wajib = [
            "material",
            "material description"
        ]

        # Cek kolom wajib
        if not all(kolom in data_import.columns for kolom in kolom_wajib):

            data_import = pd.read_excel(file_master)

            # Rapikan nama kolom Excel
            data_import.columns = (
                data_import.columns
                .astype(str)
                .str.strip()
                .str.lower()
            )

            # Cari kolom kode dan nama berdasarkan nama Excel
            kolom_kode = None
            kolom_nama = None

            for kolom in data_import.columns:

                if kolom.strip().lower() == "material":
                    kolom_kode = kolom

                if kolom.strip().lower() == "material description":
                    kolom_nama = kolom

            if kolom_kode is None or kolom_nama is None:

                st.error(
                    "Kolom Excel tidak ditemukan. "
                    "Harus ada kolom 'material' dan "
                    "'material description'."
                )

            else:

                # Ambil hanya kode dan nama
                data_import = data_import[
                    [kolom_kode, kolom_nama]
                ].copy()

                # Ubah nama menjadi nama yang dipakai sistem
                data_import.columns = [
                    "Kode Raw Material",
                    "Nama Raw Material"
                ]

                # Hapus baris kosong
                data_import = data_import.dropna(
                    subset=[
                        "Kode Raw Material",
                        "Nama Raw Material"
                    ]
                )

                # Rapikan isi
                data_import["Kode Raw Material"] = (
                    data_import["Kode Raw Material"]
                    .astype(str)
                    .str.strip()
                )

                data_import["Nama Raw Material"] = (
                    data_import["Nama Raw Material"]
                    .astype(str)
                    .str.strip()
                )

                st.write("Data yang akan diimport:")

                st.dataframe(
                    data_import,
                    use_container_width=True,
                    hide_index=True
                )

                if st.button(
                    "Import ke Master Data",
                    type="primary",
                    use_container_width=True,
                    key="import_master_data"
                ):

                    conn_import = sqlite3.connect("incoming.db")
                    cursor_import = conn_import.cursor()

                    berhasil = 0
                    dilewati = 0

                    for _, row in data_import.iterrows():

                        kode = row["Kode Raw Material"]
                        nama = row["Nama Raw Material"]

                        try:

                            cursor_import.execute(
                                """
                                INSERT INTO master_raw_material
                                (
                                    kode_raw_material,
                                    nama_raw_material
                                )
                                VALUES (?, ?)
                                """,
                                (kode, nama)
                            )

                            berhasil += 1

                        except sqlite3.IntegrityError:

                            dilewati += 1

                    conn_import.commit()
                    conn_import.close()

                    st.success(
                        f"{berhasil} data berhasil diimport."
                    )

                    if dilewati > 0:
                        st.warning(
                            f"{dilewati} data dilewati karena "
                            f"kode sudah ada."
                        )

        else:

            # Hanya mengambil 2 kolom yang diperlukan
            data_import = data_import[
                ["material", "material description"]
            ].copy()

            data_import = data_import.rename(
                columns={
                    "material": "Kode Raw Material",
                    "material description": "Nama Raw Material"
                }
            )

            # Hapus baris yang kosong
            data_import = data_import.dropna(
                subset=["Kode Raw Material", "Nama Raw Material"]
            )

            # Tampilkan data sebelum diimport
            st.write("Data yang akan diimport:")

            st.dataframe(
                data_import,
                use_container_width=True,
                hide_index=True
            )

            if st.button(
                "Import ke Master Data",
                type="primary",
                use_container_width=True,
                key="import_master_data"
            ):

                conn_import = sqlite3.connect("incoming.db")
                cursor_import = conn_import.cursor()

                berhasil = 0
                dilewati = 0

                for _, row in data_import.iterrows():

                    kode = str(row["Kode Raw Material"]).strip()
                    nama = str(row["Nama Raw Material"]).strip()

                    if not kode or not nama:
                        dilewati += 1
                        continue

                    try:

                        cursor_import.execute(
                            """
                            INSERT INTO master_raw_material
                            (
                                kode_raw_material,
                                nama_raw_material
                            )
                            VALUES (?, ?)
                            """,
                            (kode, nama)
                        )

                        berhasil += 1

                    except sqlite3.IntegrityError:
                        dilewati += 1

                conn_import.commit()
                conn_import.close()

                st.success(
                    f"{berhasil} data berhasil diimport ke Master Data."
                )

                if dilewati > 0:
                    st.warning(
                        f"{dilewati} data dilewati "
                        f"karena kode sudah ada atau data kosong."
                    )

    # ==================================================
    # EDIT MASTER DATA
    # ==================================================

    st.divider()
    st.subheader("Edit Master Data")

    conn_edit = sqlite3.connect("incoming.db")

    data_edit_list = pd.read_sql_query(
        """
        SELECT
            kode_raw_material AS "Kode Raw Material",
            nama_raw_material AS "Nama Raw Material"
        FROM master_raw_material
        ORDER BY id DESC
        """,
        conn_edit
    )

    conn_edit.close()

    if data_edit_list.empty:

        st.info("Belum ada data Master Data yang bisa diedit.")

    else:

        pilihan_edit = st.selectbox(
            "Pilih Kode Raw Material",
            data_edit_list["Kode Raw Material"].tolist(),
            key="pilihan_edit_master"
        )

        verifikasi_edit = st.checkbox(
            "Verifikasi Administrator untuk mengedit",
            key="verifikasi_edit_master"
        )

        if verifikasi_edit:

            password_edit = st.text_input(
                "Password Administrator",
                type="password",
                key="password_edit_master"
            )

            if password_edit:

                if password_edit == "admin123":

                    conn_edit = sqlite3.connect("incoming.db")
                    cursor_edit = conn_edit.cursor()

                    cursor_edit.execute(
                        """
                        SELECT
                            kode_raw_material,
                            nama_raw_material
                        FROM master_raw_material
                        WHERE kode_raw_material = ?
                        """,
                        (pilihan_edit,)
                    )

                    data_lama = cursor_edit.fetchone()

                    conn_edit.close()

                    if data_lama:

                        kode_baru = st.text_input(
                            "Kode Raw Material",
                            value=data_lama[0],
                            key="kode_edit_master"
                        )

                        nama_baru = st.text_input(
                            "Nama Raw Material",
                            value=data_lama[1],
                            key="nama_edit_master"
                        )

                        if st.button(
                            "Simpan Perubahan",
                            type="primary",
                            use_container_width=True,
                            key="simpan_edit_master"
                        ):

                            if not kode_baru.strip() or not nama_baru.strip():

                                st.error(
                                    "Kode dan Nama Raw Material wajib diisi."
                                )

                            else:

                                conn_edit = sqlite3.connect("incoming.db")
                                cursor_edit = conn_edit.cursor()

                                try:

                                    cursor_edit.execute(
                                        """
                                        UPDATE master_raw_material
                                        SET
                                            kode_raw_material = ?,
                                            nama_raw_material = ?
                                        WHERE kode_raw_material = ?
                                        """,
                                        (
                                            kode_baru.strip(),
                                            nama_baru.strip(),
                                            pilihan_edit
                                        )
                                    )

                                    conn_edit.commit()

                                    st.success(
                                        "Master Data berhasil diperbarui."
                                    )

                                except sqlite3.IntegrityError:

                                    st.error(
                                        "Kode Raw Material tersebut sudah digunakan."
                                    )

                                finally:

                                    conn_edit.close()

                else:

                    st.error("Password Administrator salah.")



# =========================================================
# FUNGSI PDF LOGBOOK
# =========================================================

def buat_pdf_logbook(sample_id):

    conn = sqlite3.connect("incoming.db")

    # ==============================
    # DATA SAMPEL
    # ==============================

    sample = pd.read_sql_query(
        """
        SELECT
            no_sampel,
            tanggal,
            nama_sampel,
            kode_sampel,
            keterangan,
            status
        FROM logbook_sample
        WHERE id = ?
        """,
        conn,
        params=(sample_id,)
    )

    # ==============================
    # HASIL PENGUJIAN
    # ==============================

    hasil = pd.read_sql_query(
        """
        SELECT
            r.jenis_logbook,
            r.parameter,
            r.hasil,
            r.analis,
            r.tanggal_uji
        FROM logbook_result r
        WHERE r.sample_id = ?
        AND r.id = (
            SELECT MAX(r2.id)
            FROM logbook_result r2
            WHERE r2.sample_id = r.sample_id
                AND r2.jenis_logbook = r.jenis_logbook
        )
        ORDER BY r.id
        """,
        conn,
        params=(sample_id,)
    )

    conn.close()

    if sample.empty:
        return None

    data = sample.iloc[0]

    # ==============================
    # PDF LANDSCAPE
    # ==============================

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    # ==============================
    # STYLE
    # ==============================

    style_title = ParagraphStyle(
        "LogbookTitle",
        parent=styles["Title"],
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    style_header = ParagraphStyle(
        "LogbookHeader",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER
    )

    style_cell = ParagraphStyle(
        "LogbookCell",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        alignment=TA_LEFT
    )

    style_info_label = ParagraphStyle(
        "InfoLabel",
        parent=styles["Normal"],
        fontSize=8,
        leading=10
    )

    style_info_value = ParagraphStyle(
        "InfoValue",
        parent=styles["Normal"],
        fontSize=8,
        leading=10
    )

    isi = []

    # ==============================
    # JUDUL
    # ==============================

    isi.append(
        Paragraph(
            "<b>LOGBOOK HASIL ANALISA</b>",
            style_title
        )
    )

    # ==============================
    # INFORMASI SAMPEL
    # ==============================

    info_data = [
        [
            Paragraph("<b>LOT Sampel</b>", style_info_label),
            Paragraph(
                escape(str(data["no_sampel"] or "-")),
                style_info_value
            ),

            Paragraph("<b>Tanggal</b>", style_info_label),
            Paragraph(
                escape(str(data["tanggal"] or "-")),
                style_info_value
            )
        ],
        [
            Paragraph("<b>Nama Sampel</b>", style_info_label),
            Paragraph(
                escape(str(data["nama_sampel"] or "-")),
                style_info_value
            ),

            Paragraph("<b>Kode Sampel</b>", style_info_label),
            Paragraph(
                escape(str(data["kode_sampel"] or "-")),
                style_info_value
            )
        ],
        [
            Paragraph("<b>Keterangan</b>", style_info_label),
            Paragraph(
                escape(str(data["keterangan"] or "-")),
                style_info_value
            ),

            Paragraph("<b>Status</b>", style_info_label),
            Paragraph(
                escape(str(data["status"] or "-")),
                style_info_value
            )
        ]
    ]

    tabel_info = Table(
        info_data,
        colWidths=[
            80,
            250,
            80,
            250
        ]
    )

    tabel_info.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
        ])
    )

    isi.append(tabel_info)
    isi.append(Spacer(1, 12))

    # ==============================
    # TABEL HASIL PENGUJIAN
    # ==============================

    hasil_data = [
        [
            Paragraph("<b>Pengujian</b>", style_header),
            Paragraph("<b>Parameter</b>", style_header),
            Paragraph("<b>Hasil</b>", style_header),
            Paragraph("<b>Analis</b>", style_header),
            Paragraph("<b>Tanggal Uji</b>", style_header)
        ]
    ]

    if not hasil.empty:

        for _, row in hasil.iterrows():

            pengujian = str(row["jenis_logbook"] or "-")
            parameter = str(row["parameter"] or "-")
            hasil_uji = str(row["hasil"] or "-")
            analis = str(row["analis"] or "-")
            tanggal_uji = str(row["tanggal_uji"] or "-")

            hasil_data.append(
                [
                    Paragraph(
                        escape(pengujian),
                        style_cell
                    ),

                    Paragraph(
                        escape(parameter),
                        style_cell
                    ),

                    Paragraph(
                        escape(hasil_uji),
                        style_cell
                    ),

                    Paragraph(
                        escape(analis),
                        style_cell
                    ),

                    Paragraph(
                        escape(tanggal_uji),
                        style_cell
                    )
                ]
            )

    else:

        hasil_data.append(
            [
                Paragraph("-", style_cell),
                Paragraph("-", style_cell),
                Paragraph("Belum ada hasil pengujian.", style_cell),
                Paragraph("-", style_cell),
                Paragraph("-", style_cell)
            ]
        )

    # ==============================
    # BUAT TABEL
    # ==============================

    tabel_hasil = Table(
        hasil_data,
        colWidths=[
            110,   # Pengujian
            100,   # Parameter
            400,   # Hasil
            90,    # Analis
            90     # Tanggal Uji
        ],
        repeatRows=1
    )

    tabel_hasil.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),

            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),

            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),

            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    isi.append(tabel_hasil)

    isi.append(Spacer(1, 15))

    # ==============================
    # BUILD PDF
    # ==============================

    doc.build(isi)

    buffer.seek(0)

    return buffer

# =========================================================
# FUNGSI LOGBOOK - AMBIL / BUAT SAMPLE
# =========================================================

def dapatkan_atau_buat_sample(
    no_sampel,
    tanggal,
    nama_sampel,
    kode_sampel="",
    keterangan="",
    status="OK"
):
    conn = sqlite3.connect("incoming.db")
    cursor = conn.cursor()

    # Cek apakah LOT sudah ada
    cursor.execute(
        """
        SELECT id
        FROM logbook_sample
        WHERE no_sampel = ?
        """,
        (no_sampel,)
    )

    data = cursor.fetchone()

    if data:
        # LOT sudah ada → gunakan ID yang lama
        sample_id = data[0]

        cursor.execute(
            """
            UPDATE logbook_sample
            SET tanggal = ?,
                nama_sampel = ?,
                kode_sampel = ?,
                keterangan = ?,
                status = ?
            WHERE id = ?
            """,
            (
                tanggal,
                nama_sampel,
                kode_sampel,
                keterangan,
                status,
                sample_id
            )
        )

    else:
        # LOT belum ada → buat sample baru
        cursor.execute(
            """
            INSERT INTO logbook_sample
            (
                no_sampel,
                tanggal,
                nama_sampel,
                kode_sampel,
                keterangan,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                no_sampel,
                tanggal,
                nama_sampel,
                kode_sampel,
                keterangan,
                status
            )
        )

        sample_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return sample_id

# =========================================================
# LOGBOOK - FULL CODE
# =========================================================

if menu == "LOGBOOK":


    from datetime import datetime
    import io
    import pandas as pd
    import sqlite3

    # =========================================================
# DATABASE LOGBOOK
# =========================================================

import sqlite3
import streamlit as st


# =========================================================
# BUAT TABEL LOGBOOK
# =========================================================

conn_logbook = sqlite3.connect("incoming.db")

cursor_logbook = conn_logbook.cursor()

cursor_logbook.execute("""
CREATE TABLE IF NOT EXISTS logbook_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no_sampel TEXT UNIQUE,
    tanggal TEXT,
    nama_sampel TEXT,
    kode_sampel TEXT,
    keterangan TEXT,
    status TEXT
)
""")

cursor_logbook.execute("""
CREATE TABLE IF NOT EXISTS logbook_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    jenis_logbook TEXT,
    parameter TEXT,
    hasil TEXT,
    standar TEXT,
    satuan TEXT,
    analis TEXT,
    tanggal_uji TEXT
)
""")

cursor_logbook.execute("""
CREATE TABLE IF NOT EXISTS logbook_riwayat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    aksi TEXT,
    waktu TEXT,
    pengguna TEXT,
    detail TEXT
)
""")

conn_logbook.commit()
conn_logbook.close()


# =========================================================
# HALAMAN LOGBOOK
# =========================================================

if menu == "LOGBOOK":

    # ============================================
    # LABORATORIUM INSTRUMENT
    # ============================================

    if logbook_menu == "Laboratorium Instrument":

        st.title("Laboratorium Instrument")

        pilihan_pengujian = st.radio(
            "Pilih Pengujian:",
            [
                "Water Activity (AW)"
            ],
            horizontal=True,
            key="uji_lab_instrument"
        )

        # =================================================
        # WATER ACTIVITY
        # =================================================

        if pilihan_pengujian == "Water Activity (AW)":

            st.subheader("Water Activity (AW)")

            tanggal_aw = st.date_input(
                "Tanggal Pelaksanaan",
                key="tanggal_aw"
            )

            pengirim_aw = st.text_input(
                "Pengirim",
                key="pengirim_aw"
            )

            nama_aw = st.text_input(
                "Nama Sampel",
                key="nama_aw"
            )

            lot_aw = st.text_input(
                "LOT Sampel",
                key="lot_aw"
            )

            st.number_input(
                "Suhu",
                min_value=-100.0,
                max_value=200.0,
                value=25.00,
                step=0.01,
                format="%.2f",
                key="suhu_aw"
            )

            suhu_aw = st.session_state["suhu_aw"]

            st.number_input(
                "AW",
                min_value=0.000,
                max_value=1.000,
                value=0.000,
                step=0.001,
                format="%.3f",
                key="hasil_aw"
            )

            hasil_aw = st.session_state["hasil_aw"]

            pelaksana_aw = st.text_input(
                "Pelaksana",
                key="pelaksana_aw"
            )


            # =============================================
            # SIMPAN AW
            # =============================================

            if st.button(
                "Simpan Water Activity",
                key="simpan_aw"
            ):

                if not pengirim_aw:
                    st.error("Pengirim belum diisi.")

                elif not nama_aw:
                    st.error("Nama Sampel belum diisi.")

                elif not lot_aw:
                    st.error("LOT Sampel belum diisi.")

                elif not pelaksana_aw:
                    st.error("Pelaksana belum diisi.")

                else:

                    conn_aw = sqlite3.connect("incoming.db")
                    cursor_aw = conn_aw.cursor()

                    # -------------------------------------
                    # CARI SAMPLE
                    # -------------------------------------

                    cursor_aw.execute(
                        """
                        SELECT id
                        FROM logbook_sample
                        WHERE no_sampel = ?
                        """,
                        (lot_aw,)
                    )

                    data_sample = cursor_aw.fetchone()

                    if data_sample:

                        sample_id = data_sample[0]

                    else:

                        cursor_aw.execute(
                            """
                            INSERT INTO logbook_sample
                            (
                                no_sampel,
                                tanggal,
                                nama_sampel,
                                kode_sampel,
                                keterangan,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                lot_aw,
                                str(tanggal_aw),
                                nama_aw,
                                "",
                                "Water Activity",
                                "OK"
                            )
                        )

                        sample_id = cursor_aw.lastrowid


                    # -------------------------------------
                    # SIMPAN SUHU
                    # -------------------------------------

                    cursor_aw.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Water Activity (AW)",
                            "Suhu",
                            f"{suhu_aw:.2f}",
                            "",
                            "°C",
                            pelaksana_aw,
                            str(tanggal_aw)
                        )
                    )


                    # -------------------------------------
                    # SIMPAN AW
                    # -------------------------------------

                    cursor_aw.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Water Activity (AW)",
                            "AW",
                            f"{hasil_aw:.3f}",
                            "",
                            "",
                            pelaksana_aw,
                            str(tanggal_aw)
                        )
                    )


                    # -------------------------------------
                    # RIWAYAT
                    # -------------------------------------

                    cursor_aw.execute(
                        """
                        INSERT INTO logbook_riwayat
                        (
                            sample_id,
                            aksi,
                            waktu,
                            pengguna,
                            detail
                        )
                        VALUES (?, ?, datetime('now','localtime'), ?, ?)
                        """,
                        (
                            sample_id,
                            "TAMBAH",
                            st.session_state.get(
                                "username",
                                "Admin"
                            ),
                            f"Input Water Activity - LOT {lot_aw}"
                        )
                    )


                    conn_aw.commit()
                    conn_aw.close()

                    st.success(
                        f"Data Water Activity LOT {lot_aw} berhasil disimpan."
                    )

                    st.rerun()


    # ============================================
    # LABORATORIUM FISIKA
    # ============================================

    elif logbook_menu == "Laboratorium Fisika":

        st.title("Laboratorium Fisika")

        pilihan_pengujian = st.radio(
            "Pilih Pengujian:",
            [
                "Moist Oven",
                "Moist Analyzer Halogen"
            ],
            horizontal=True,
            key="uji_lab_fisika"
        )


        # =================================================
        # MOIST OVEN
        # =================================================

        if pilihan_pengujian == "Moist Oven":

            st.subheader("Moist Oven")

            tanggal_moist = st.date_input(
                "Tanggal Pelaksanaan",
                key="tanggal_moist"
            )

            nama_moist = st.text_input(
                "Sampel",
                key="nama_moist"
            )

            lot_moist = st.text_input(
                "LOT Sampel",
                key="lot_moist"
            )

            no_cawan = st.text_input(
                "No. Cawan",
                key="no_cawan"
            )

            berat_cawan_kosong = st.number_input(
                "Berat Cawan Kosong (g)",
                min_value=0.0,
                step=0.0001,
                format="%.4f",
                key="berat_cawan_kosong"
            )

            berat_cawan_sampel = st.number_input(
                "Berat Cawan + Sampel (g)",
                min_value=0.0,
                step=0.0001,
                format="%.4f",
                key="berat_cawan_sampel"
            )

            berat_sampel_moist = (
                berat_cawan_sampel -
                berat_cawan_kosong
            )

            st.number_input(
                "Berat Sampel (g)",
                value=float(berat_sampel_moist),
                format="%.4f",
                key="hasil_berat_sampel"
            )

            berat_ex_oven = st.number_input(
                "Berat Ex-Oven (g)",
                min_value=0.0,
                step=0.0001,
                format="%.4f",
                key="berat_ex_oven"
            )


            # ---------------------------------------------
            # HITUNG KADAR AIR
            # ---------------------------------------------

            if berat_sampel_moist > 0:

                kadar_air = (
                    (
                        berat_cawan_sampel -
                        berat_ex_oven
                    )
                    / berat_sampel_moist
                ) * 100

            else:

                kadar_air = 0.0


            st.number_input(
                "Kadar Air (%)",
                value=float(kadar_air),
                disabled=True,
                format="%.4f",
                key="hasil_kadar_air"
            )

            pelaksana_moist = st.text_input(
                "Pelaksana",
                key="pelaksana_moist"
            )


            # =============================================
            # SIMPAN MOIST OVEN
            # =============================================

            if st.button(
                "Simpan Moist Oven",
                key="simpan_moist"
            ):

                if not nama_moist:
                    st.error("Sampel belum diisi.")

                elif not lot_moist:
                    st.error("LOT Sampel belum diisi.")

                elif not no_cawan:
                    st.error("No. Cawan belum diisi.")

                elif berat_sampel_moist <= 0:
                    st.error("Berat Sampel harus lebih dari 0.")

                elif berat_ex_oven <= 0:
                    st.error("Berat Ex-Oven belum diisi.")

                elif not pelaksana_moist:
                    st.error("Pelaksana belum diisi.")

                else:

                    conn_moist = sqlite3.connect("incoming.db")
                    cursor_moist = conn_moist.cursor()

                    # -------------------------------------
                    # CARI SAMPLE
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        SELECT id
                        FROM logbook_sample
                        WHERE no_sampel = ?
                        """,
                        (lot_moist,)
                    )

                    data_sample = cursor_moist.fetchone()

                    if data_sample:

                        sample_id = data_sample[0]

                    else:

                        cursor_moist.execute(
                            """
                            INSERT INTO logbook_sample
                            (
                                no_sampel,
                                tanggal,
                                nama_sampel,
                                kode_sampel,
                                keterangan,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                lot_moist,
                                str(tanggal_moist),
                                nama_moist,
                                "",
                                "Moist Oven",
                                "OK"
                            )
                        )

                        sample_id = cursor_moist.lastrowid


                    # -------------------------------------
                    # NO CAWAN
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Moist Oven",
                            "No. Cawan",
                            no_cawan,
                            "",
                            "",
                            pelaksana_moist,
                            str(tanggal_moist)
                        )
                    )


                    # -------------------------------------
                    # CAWAN KOSONG
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Moist Oven",
                            "Berat Cawan Kosong",
                            f"{berat_cawan_kosong:.4f}",
                            "",
                            "g",
                            pelaksana_moist,
                            str(tanggal_moist)
                        )
                    )


                    # -------------------------------------
                    # CAWAN + SAMPEL
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Moist Oven",
                            "Berat Cawan + Sampel",
                            f"{berat_cawan_sampel:.4f}",
                            "",
                            "g",
                            pelaksana_moist,
                            str(tanggal_moist)
                        )
                    )


                    # -------------------------------------
                    # BERAT SAMPEL
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Moist Oven",
                            "Berat Sampel",
                            f"{berat_sampel_moist:.4f}",
                            "",
                            "g",
                            pelaksana_moist,
                            str(tanggal_moist)
                        )
                    )


                    # -------------------------------------
                    # EX-OVEN
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Moist Oven",
                            "Berat Ex-Oven",
                            f"{berat_ex_oven:.4f}",
                            "",
                            "g",
                            pelaksana_moist,
                            str(tanggal_moist)
                        )
                    )


                    # -------------------------------------
                    # KADAR AIR
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id,
                            "Moist Oven",
                            "Kadar Air",
                            f"{kadar_air:.4f}",
                            "",
                            "%",
                            pelaksana_moist,
                            str(tanggal_moist)
                        )
                    )


                    # -------------------------------------
                    # RIWAYAT
                    # -------------------------------------

                    cursor_moist.execute(
                        """
                        INSERT INTO logbook_riwayat
                        (
                            sample_id,
                            aksi,
                            waktu,
                            pengguna,
                            detail
                        )
                        VALUES (?, ?, datetime('now','localtime'), ?, ?)
                        """,
                        (
                            sample_id,
                            "TAMBAH",
                            st.session_state.get(
                                "username",
                                "Admin"
                            ),
                            f"Input Moist Oven - LOT {lot_moist}"
                        )
                    )


                    conn_moist.commit()
                    conn_moist.close()

                    st.success(
                        f"Data Moist Oven LOT {lot_moist} berhasil disimpan."
                    )

                    st.rerun()

        if pilihan_pengujian == "Moist Analyzer Halogen":

            st.subheader("Moist Analyzer Halogen")

            tanggal_halogen = st.date_input(
                "Tanggal",
                key="tanggal_halogen"
            )

            sampel_halogen = st.text_input(
                "Sampel",
                key="sampel_halogen"
            )

            lot_halogen = st.text_input(
                "LOT Sampel",
                key="lot_halogen"
            )

            jumlah_uji_halogen = st.radio(
                "Jumlah Pengujian",
                ["Simplo", "Duplo", "Triplo"],
                horizontal=True,
                key="jumlah_uji_halogen"
            )

            moist_halogen_1 = st.number_input(
                "Moisture 1 (%)",
                min_value=0.00,
                step=0.01,
                format="%.2f",
                key="moist_halogen_1"
            )

            if jumlah_uji_halogen in ["Duplo", "Triplo"]:

                moist_halogen_2 = st.number_input(
                    "Moisture 2 (%)",
                    min_value=0.00,
                    step=0.01,
                    format="%.2f",
                    key="moist_halogen_2"
                )

            if jumlah_uji_halogen == "Triplo":

                moist_halogen_3 = st.number_input(
                    "Moisture 3 (%)",
                    min_value=0.00,
                    step=0.01,
                    format="%.2f",
                    key="moist_halogen_3"
                )

            if jumlah_uji_halogen == "Simplo":

                rata_halogen = moist_halogen_1

            elif jumlah_uji_halogen == "Duplo":

                rata_halogen = (
                    moist_halogen_1 + moist_halogen_2
                ) / 2

            else:

                rata_halogen = (
                    moist_halogen_1 +
                    moist_halogen_2 +
                    moist_halogen_3
                ) / 3

            st.number_input(
                "Rata-rata (X)",
                value=float(rata_halogen),
                format="%.2f",
                disabled=True,
                key="rata_halogen"
            )

            pelaksana_halogen = st.text_input(
                "Pelaksana",
                key="pelaksana_halogen"
            )

            keterangan_halogen = st.text_area(
                "Keterangan",
                key="keterangan_halogen"
            )

            if st.button(
                "Simpan Moist Analyzer Halogen",
                key="simpan_halogen"
            ):

                if not sampel_halogen.strip():
                    st.warning("Sampel wajib diisi.")

                elif not lot_halogen.strip():
                    st.warning("LOT Sampel wajib diisi.")

                elif not pelaksana_halogen.strip():
                    st.warning("Pelaksana wajib diisi.")

                else:

                    conn_halogen = sqlite3.connect("incoming.db")
                    cursor_halogen = conn_halogen.cursor()

                    # Cari berdasarkan LOT
                    cursor_halogen.execute(
                        """
                        SELECT id
                        FROM logbook_sample
                        WHERE no_sampel = ?
                        """,
                        (lot_halogen,)
                    )

                    sample_halogen = cursor_halogen.fetchone()

                    if sample_halogen:
                        sample_id_halogen = sample_halogen[0]

                    else:
                        cursor_halogen.execute(
                            """
                            INSERT INTO logbook_sample
                            (
                                no_sampel,
                                tanggal,
                                nama_sampel,
                                keterangan,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                lot_halogen,
                                str(tanggal_halogen),
                                sampel_halogen,
                                keterangan_halogen,
                                "SELESAI"
                            )
                        )

                        sample_id_halogen = cursor_halogen.lastrowid


                    hasil_halogen = f"Moisture 1: {moist_halogen_1:.2f}%"

                    if jumlah_uji_halogen in ["Duplo", "Triplo"]:
                        hasil_halogen += f" | Moisture 2: {moist_halogen_2:.2f}%"

                    if jumlah_uji_halogen == "Triplo":
                        hasil_halogen += f" | Moisture 3: {moist_halogen_3:.2f}%"

                    hasil_halogen += f" | Rata-rata (X): {rata_halogen:.2f}%"


                    # Simpan hasil
                    cursor_halogen.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id_halogen,
                            "Moist Analyzer Halogen",
                            "Moisture",
                            hasil_halogen,
                            "",
                            "%",
                            pelaksana_halogen,
                            str(tanggal_halogen)
                        )
                    )

                    # Simpan riwayat
                    cursor_halogen.execute(
                        """
                        INSERT INTO logbook_riwayat
                        (
                            sample_id,
                            aksi,
                            waktu,
                            pengguna,
                            detail
                        )
                        VALUES (?, ?, datetime('now'), ?, ?)
                        """,
                        (
                            sample_id_halogen,
                            "TAMBAH",
                            st.session_state["username"],
                            f"Menambahkan hasil Moist Analyzer Halogen: {rata_halogen:.2f}%"
                        )
                    )

                    conn_halogen.commit()
                    conn_halogen.close()

                    st.success("Data Moist Analyzer Halogen berhasil disimpan.")
                    st.rerun()



    # ============================================
    # LABORATORIUM KIMIA
    # ============================================

    elif logbook_menu == "Laboratorium Kimia":

        st.title("Laboratorium Kimia")

        pilihan_pengujian = st.radio(
            "Pilih Pengujian:",
            [
                "%FFA / %AV",
                "Moist Karl Fischer",
                "Fat Content"
            ],
            horizontal=True,
            key="uji_lab_kimia"
        )


        if pilihan_pengujian == "%FFA / %AV":

            st.subheader("%FFA / %AV")

            tanggal_ffa = st.date_input(
                "Tanggal",
                key="tanggal_ffa"
            )

            sampel_ffa = st.text_input(
                "Sampel",
                key="sampel_ffa"
            )

            lot_ffa = st.text_input(
                "LOT Sampel",
                key="lot_ffa"
            )

            tujuan_analisis_ffa = st.radio(
                "Tujuan Analisis",
                ["%FFA", "%AV"],
                horizontal=True,
                key="tujuan_analisis_ffa"
            )

            jenis_ffa = st.radio(
                "Jenis Pengujian",
                ["Simplo", "Duplo"],
                horizontal=True,
                key="jenis_ffa"
            )

            berat_sampel_1 = st.number_input(
                "Berat Sampel (g)",
                min_value=0.0000,
                step=0.0001,
                format="%.4f",
                key="berat_sampel_ffa_1"
            )

            volume_1 = st.number_input(
                "Volume (mL)",
                min_value=0.00,
                step=0.01,
                format="%.2f",
                key="volume_ffa_1"
            )

            hasil_ffa_1 = st.number_input(
                "%FFA / %AV",
                min_value=0.00,
                step=0.01,
                format="%.2f",
                key="hasil_ffa_1"
            )

            if jenis_ffa == "Duplo":

                berat_sampel_2 = st.number_input(
                    "Berat Sampel 2 (g)",
                    min_value=0.0000,
                    step=0.0001,
                    format="%.4f",
                    key="berat_sampel_ffa_2"
                )

                volume_2 = st.number_input(
                    "Volume 2 (mL)",
                    min_value=0.00,
                    step=0.01,
                    format="%.2f",
                    key="volume_ffa_2"
                )

                hasil_ffa_2 = st.number_input(
                    "%FFA / %AV 2",
                    min_value=0.00,
                    step=0.01,
                    format="%.2f",
                    key="hasil_ffa_2"
                )

                rata_ffa = (hasil_ffa_1 + hasil_ffa_2) / 2

            else:
                rata_ffa = hasil_ffa_1

            st.number_input(
                "Rata-rata (X)",
                value=float(rata_ffa),
                format="%.2f",
                disabled=True,
                key="rata_ffa"
            )

            pelaksana_ffa = st.text_input(
                "Pelaksana",
                key="pelaksana_ffa"
            )

            keterangan_ffa = st.text_area(
                "Keterangan",
                key="keterangan_ffa"
            )

            if st.button(
                "Simpan %FFA / %AV",
                key="simpan_ffa_av"
            ):

                if not sampel_ffa.strip():
                    st.warning("Sampel wajib diisi.")

                elif not lot_ffa.strip():
                    st.warning("LOT Sampel wajib diisi.")

                elif not pelaksana_ffa.strip():
                    st.warning("Pelaksana wajib diisi.")

                else:

                    conn_ffa = sqlite3.connect("incoming.db")
                    cursor_ffa = conn_ffa.cursor()

                    # Cari sample berdasarkan LOT
                    cursor_ffa.execute(
                        """
                        SELECT id
                        FROM logbook_sample
                        WHERE no_sampel = ?
                        """,
                        (lot_ffa,)
                    )

                    sample_ffa = cursor_ffa.fetchone()

                    if sample_ffa:
                        sample_id_ffa = sample_ffa[0]

                    else:
                        cursor_ffa.execute(
                            """
                            INSERT INTO logbook_sample
                            (
                                no_sampel,
                                tanggal,
                                nama_sampel,
                                keterangan,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                lot_ffa,
                                str(tanggal_ffa),
                                sampel_ffa,
                                keterangan_ffa,
                                "SELESAI"
                            )
                        )

                        sample_id_ffa = cursor_ffa.lastrowid

                    # Hasil pertama
                    hasil_pertama = (
                        f"Berat: {berat_sampel_1:.4f} g | "
                        f"Volume: {volume_1:.2f} mL | "
                        f"%FFA/%AV: {hasil_ffa_1:.2f}"
                    )

                    cursor_ffa.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id_ffa,
                            "%FFA / %AV",
                            "Pengujian 1",
                            hasil_pertama,
                            "",
                            "",
                            pelaksana_ffa,
                            str(tanggal_ffa)
                        )
                    )

                    # Kalau Duplo, simpan hasil kedua
                    if jenis_ffa == "Duplo":

                        hasil_kedua = (
                            f"Berat: {berat_sampel_2:.4f} g | "
                            f"Volume: {volume_2:.2f} mL | "
                            f"%FFA/%AV: {hasil_ffa_2:.2f}"
                        )

                        cursor_ffa.execute(
                            """
                            INSERT INTO logbook_result
                            (
                                sample_id,
                                jenis_logbook,
                                parameter,
                                hasil,
                                standar,
                                satuan,
                                analis,
                                tanggal_uji
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                sample_id_ffa,
                                "%FFA / %AV",
                                "Pengujian 2",
                                hasil_kedua,
                                "",
                                "",
                                pelaksana_ffa,
                                str(tanggal_ffa)
                            )
                        )

                    # Simpan rata-rata
                    cursor_ffa.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id_ffa,
                            "%FFA / %AV",
                            "Rata-rata (X)",
                            f"{rata_ffa:.2f}",
                            "",
                            "%",
                            pelaksana_ffa,
                            str(tanggal_ffa)
                        )
                    )

                    # Simpan riwayat
                    cursor_ffa.execute(
                        """
                        INSERT INTO logbook_riwayat
                        (
                            sample_id,
                            aksi,
                            waktu,
                            pengguna,
                            detail
                        )
                        VALUES (?, ?, datetime('now'), ?, ?)
                        """,
                        (
                            sample_id_ffa,
                            "TAMBAH",
                            st.session_state["username"],
                            f"Menyimpan hasil %FFA / %AV - Rata-rata: {rata_ffa:.2f}%"
                        )
                    )

                    conn_ffa.commit()
                    conn_ffa.close()

                    st.success("Data %FFA / %AV berhasil disimpan.")
                    st.rerun()


        if pilihan_pengujian == "Moist Karl Fischer":

            st.subheader("Moist Karl Fischer")

            tanggal_kf = st.date_input(
                "Tanggal",
                key="tanggal_kf"
            )

            sampel_kf = st.text_input(
                "Sampel",
                key="sampel_kf"
            )

            lot_kf = st.text_input(
                "LOT Sampel",
                key="lot_kf"
            )

            moisture_kf = st.number_input(
                "Moisture (%)",
                min_value=0.00,
                step=0.01,
                format="%.2f",
                key="moisture_kf"
            )

            pelaksana_kf = st.text_input(
                "Pelaksana",
                key="pelaksana_kf"
            )

            if st.button(
                "Simpan Moist Karl Fischer",
                key="simpan_karl_fischer"
            ):

                if not sampel_kf.strip():
                    st.warning("Sampel wajib diisi.")

                elif not lot_kf.strip():
                    st.warning("LOT Sampel wajib diisi.")

                elif not pelaksana_kf.strip():
                    st.warning("Pelaksana wajib diisi.")

                else:

                    conn_kf = sqlite3.connect("incoming.db")
                    cursor_kf = conn_kf.cursor()

                    # Cari sample berdasarkan LOT
                    cursor_kf.execute(
                        """
                        SELECT id
                        FROM logbook_sample
                        WHERE no_sampel = ?
                        """,
                        (lot_kf,)
                    )

                    sample_kf = cursor_kf.fetchone()

                    if sample_kf:
                        sample_id_kf = sample_kf[0]

                    else:
                        cursor_kf.execute(
                            """
                            INSERT INTO logbook_sample
                            (
                                no_sampel,
                                tanggal,
                                nama_sampel,
                                keterangan,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                lot_kf,
                                str(tanggal_kf),
                                sampel_kf,
                                "Moist Karl Fischer",
                                "SELESAI"
                            )
                        )

                        sample_id_kf = cursor_kf.lastrowid

                    # Simpan hasil
                    cursor_kf.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id_kf,
                            "Moist Karl Fischer",
                            "Moisture",
                            f"{moisture_kf:.2f}",
                            "",
                            "%",
                            pelaksana_kf,
                            str(tanggal_kf)
                        )
                    )

                    # Simpan riwayat
                    cursor_kf.execute(
                        """
                        INSERT INTO logbook_riwayat
                        (
                            sample_id,
                            aksi,
                            waktu,
                            pengguna,
                            detail
                        )
                        VALUES (?, ?, datetime('now'), ?, ?)
                        """,
                        (
                            sample_id_kf,
                            "TAMBAH",
                            st.session_state["username"],
                            f"Menambahkan hasil Moist Karl Fischer: {moisture_kf:.2f}%"
                        )
                    )

                    conn_kf.commit()
                    conn_kf.close()

                    st.success("Data Moist Karl Fischer berhasil disimpan.")
                    st.rerun()


        # =================================================
        # FAT CONTENT
        # =================================================

        if pilihan_pengujian == "Fat Content":

            st.subheader("Fat Content")

            tanggal_fat = st.date_input(
                "Tanggal Pelaksanaan",
                key="tanggal_fat"
            )

            sampel_fat = st.text_input(
                "Sampel",
                key="sampel_fat"
            )

            lot_fat = st.text_input(
                "LOT Sampel",
                key="lot_fat"
            )

            berat_sampel_fat = st.number_input(
                "Berat Sampel (g)",
                min_value=0.0000,
                value=0.0000,
                step=0.0001,
                format="%.4f",
                key="berat_sampel_fat"
            )

            berat_labu_awal_fat = st.number_input(
                "Berat Labu + Batu Didih (g)",
                min_value=0.0000,
                value=0.0000,
                step=0.0001,
                format="%.4f",
                key="berat_labu_awal_fat"
            )

            berat_labu_ex_fat = st.number_input(
                "Berat Labu + Batu Didih + Sampel Ex. Ekstraksi (g)",
                min_value=0.0000,
                value=0.0000,
                step=0.0001,
                format="%.4f",
                key="berat_labu_ex_fat"
            )

            # ==============================
            # PERHITUNGAN FAT
            # ==============================

            if berat_sampel_fat > 0:

                fat_persen = (
                    (
                        berat_labu_ex_fat
                        - berat_labu_awal_fat
                    )
                    / berat_sampel_fat
                ) * 100

            else:

                fat_persen = 0.0

            st.number_input(
                "Fat (%)",
                value=fat_persen,
                format="%.2f",
                disabled=True,
                key="fat_persen_display"
            )

            pelaksana_fat = st.text_input(
                "Pelaksana",
                key="pelaksana_fat"
            )

            keterangan_fat = st.text_area(
                "Keterangan",
                key="keterangan_fat"
            )

            if st.button(
                "Simpan Fat Content",
                type="primary",
                use_container_width=True,
                key="simpan_fat_content"
            ):

                if not sampel_fat:
                    st.error("Sampel wajib diisi.")

                elif not lot_fat:
                    st.error("LOT Sampel wajib diisi.")

                elif not pelaksana_fat:
                    st.error("Pelaksana wajib diisi.")

                elif berat_sampel_fat <= 0:
                    st.error("Berat Sampel harus lebih dari 0.")

                else:

                    conn_fat = sqlite3.connect("incoming.db")
                    cursor_fat = conn_fat.cursor()

                    # Cari sampel berdasarkan LOT
                    cursor_fat.execute(
                        """
                        SELECT id
                        FROM logbook_sample
                        WHERE no_sampel = ?
                        """,
                        (lot_fat,)
                    )

                    sample_fat = cursor_fat.fetchone()

                    # Kalau LOT belum ada → buat sampel baru
                    if sample_fat:

                        sample_id_fat = sample_fat[0]

                    else:

                        cursor_fat.execute(
                            """
                            INSERT INTO logbook_sample
                            (
                                no_sampel,
                                tanggal,
                                nama_sampel,
                                kode_sampel,
                                keterangan,
                                status
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                lot_fat,
                                str(tanggal_fat),
                                sampel_fat,
                                "",
                                keterangan_fat,
                                "Belum Diuji"
                            )
                        )

                        sample_id_fat = cursor_fat.lastrowid

                    # ==============================
                    # SIMPAN HASIL
                    # ==============================

                    hasil_fat = (
                        f"Berat Sampel: {berat_sampel_fat:.4f} g | "
                        f"Berat Labu + Batu Didih: "
                        f"{berat_labu_awal_fat:.4f} g | "
                        f"Berat Labu + Batu Didih Ex. Ekstraksi: "
                        f"{berat_labu_ex_fat:.4f} g | "
                        f"Fat: {fat_persen:.2f}%"
                    )

                    cursor_fat.execute(
                        """
                        INSERT INTO logbook_result
                        (
                            sample_id,
                            jenis_logbook,
                            parameter,
                            hasil,
                            standar,
                            satuan,
                            analis,
                            tanggal_uji
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sample_id_fat,
                            "Fat Content",
                            "Fat",
                            hasil_fat,
                            "",
                            "%",
                            pelaksana_fat,
                            str(tanggal_fat)
                        )
                    )

                    # ==============================
                    # RIWAYAT
                    # ==============================

                    cursor_fat.execute(
                        """
                        INSERT INTO logbook_riwayat
                        (
                            sample_id,
                            aksi,
                            waktu,
                            pengguna,
                            detail
                        )
                        VALUES (?, ?, datetime('now'), ?, ?)
                        """,
                        (
                            sample_id_fat,
                            "Tambah",
                            st.session_state.get(
                                "username",
                                pelaksana_fat
                            ),
                            f"Menambahkan hasil Fat Content "
                            f"untuk LOT {lot_fat}"
                        )
                    )

                    conn_fat.commit()
                    conn_fat.close()

                    st.success(
                        "Data Fat Content berhasil disimpan."
                    )

                    st.rerun()


# =========================================================
# TAB RESULT
# =========================================================
    elif logbook_menu == "Result":
        st.title("LOGBOOK - RESULT")

        st.subheader("Result")
        search_logbook = st.text_input(
        "Search",
        placeholder="Cari LOT Sampel, Nama Sampel, atau Pengujian...",
        key="search_logbook_result"
)

        conn_result = sqlite3.connect("incoming.db")

        data_sample = pd.read_sql_query(
            """
            SELECT DISTINCT
                s.id,
                s.no_sampel,
                s.nama_sampel,
                (
                    SELECT MAX(lr.waktu)
                    FROM logbook_riwayat lr
                    WHERE lr.sample_id = s.id
                ) AS waktu
            FROM logbook_sample s
            LEFT JOIN logbook_result r
                ON s.id = r.sample_id
            WHERE s.no_sampel LIKE ?
            OR s.nama_sampel LIKE ?
            OR r.jenis_logbook LIKE ?
            ORDER BY s.id DESC
            """,
            conn_result,
            params=(
                f"%{search_logbook}%",
                f"%{search_logbook}%",
                f"%{search_logbook}%"
            )
        )

        if not data_sample.empty:
            data_sample["Waktu"] = pd.to_datetime(
                data_sample["waktu"],
                errors="coerce"
            ).dt.strftime("%d-%m-%Y %H:%M:%S")

        conn_result.close()

        if data_sample.empty:

            st.info("Belum ada data sampel.")

        else:

            # Header tabel
            c1, c2, c3, c4, c5, c6 = st.columns(
                [0.5, 1.5, 2, 2.5, 1.8, 2.5]
            )

            c1.write("No")
            c2.write("LOT Sampel")
            c3.write("Nama Sampel")
            c4.write("Pengujian yang Dilakukan")
            c5.write("Waktu")
            # c6 sengaja tidak diberi judul

            st.divider()

            for nomor, row in data_sample.iterrows():

                sample_id = int(row["id"])

                # =================================================
                # AMBIL JENIS PENGUJIAN SAMPEL
                # =================================================

                conn_test = sqlite3.connect("incoming.db")
                cursor_test = conn_test.cursor()

                cursor_test.execute(
                    """
                    SELECT DISTINCT jenis_logbook
                    FROM logbook_result
                    WHERE sample_id = ?
                    """,
                    (sample_id,)
                )

                jenis_uji = cursor_test.fetchall()

                conn_test.close()

                daftar_uji = [
                    x[0]
                    for x in jenis_uji
                    if x[0]
                ]

                pengujian = ", ".join(daftar_uji)

                # =================================================
                # TAMPILKAN BARIS
                # =================================================

                c1, c2, c3, c4, c5, c6 = st.columns(
                    [0.5, 1.5, 2, 2.5, 1.8, 2.5]
                )

                c1.write(nomor + 1)

                c2.write(
                    row["no_sampel"]
                )

                c3.write(
                    row["nama_sampel"]
                )

                c4.write(
                    pengujian
                )

                c5.write(
                    pd.to_datetime(row["waktu"]).strftime("%d-%m-%Y %H:%M:%S")
                    if pd.notna(row["waktu"])
                    else "-"
                )

                # =================================================
                # TOMBOL
                # =================================================

                tombol_detail, tombol_edit, tombol_hapus = c6.columns(3)

                if tombol_detail.button(
                    "Detail",
                    key=f"detail_{sample_id}"
                ):

                    st.session_state[
                        "detail_sample_id"
                    ] = sample_id

                    st.rerun()

                if tombol_edit.button(
                    "Edit",
                    key=f"edit_{sample_id}"
                ):
                    st.session_state["edit_sample_id"] = sample_id
                    st.session_state.pop("detail_sample_id", None)
                    st.session_state.pop("hapus_sample_id", None)
                    st.rerun()

                if tombol_hapus.button("Hapus",key=f"hapus_{sample_id}"):
                    st.session_state["hapus_sample_id"] = sample_id
                    st.rerun()


            # ==============================
            # KONFIRMASI HAPUS
            # ==============================
            if "hapus_sample_id" in st.session_state:

                hapus_id = st.session_state["hapus_sample_id"]

                st.warning(
                    "⚠️ Data LOGBOOK ini akan dihapus permanen "
                    "beserta seluruh hasil pengujiannya."
                )

                konfirmasi = st.checkbox(
                    "Saya yakin ingin menghapus data ini.",
                    key=f"konfirmasi_hapus_{hapus_id}"
                )

                password_hapus = st.text_input(
                    "Masukkan Password",
                    type="password",
                    key=f"password_hapus_{hapus_id}"
                )

                col_konfirmasi, col_batal = st.columns(2)

                with col_konfirmasi:
                    if st.button(
                        "Konfirmasi Hapus",
                        key=f"btn_konfirmasi_hapus_{hapus_id}"
                    ):

                        if not konfirmasi:
                            st.error("Centang konfirmasi terlebih dahulu.")

                        elif password_hapus != "admin123":
                            st.error("Password salah.")

                        else:

                            conn_hapus = sqlite3.connect("incoming.db")
                            cursor_hapus = conn_hapus.cursor()

                            # Ambil informasi sampel SEBELUM dihapus
                            cursor_hapus.execute(
                                """
                                SELECT no_sampel, nama_sampel
                                FROM logbook_sample
                                WHERE id = ?
                                """,
                                (hapus_id,)
                            )

                            data_hapus = cursor_hapus.fetchone()

                            if data_hapus:

                                lot_hapus = data_hapus[0]
                                nama_hapus = data_hapus[1]

                                # SIMPAN RIWAYAT PENGHAPUSAN
                                cursor_hapus.execute(
                                    """
                                    INSERT INTO logbook_riwayat
                                    (
                                        sample_id,
                                        aksi,
                                        waktu,
                                        pengguna,
                                        detail
                                    )
                                    VALUES (?, ?, datetime('now'), ?, ?)
                                    """,
                                    (
                                        hapus_id,
                                        "Hapus",
                                        st.session_state.get("username", "admin"),
                                        f"Menghapus data LOGBOOK - LOT: {lot_hapus} | "
                                        f"Nama Sampel: {nama_hapus}"
                                    )
                                )

                                # HAPUS HASIL PENGUJIAN
                                cursor_hapus.execute(
                                    """
                                    DELETE FROM logbook_result
                                    WHERE sample_id = ?
                                    """,
                                    (hapus_id,)
                                )

                                # HAPUS DATA SAMPLE
                                cursor_hapus.execute(
                                    """
                                    DELETE FROM logbook_sample
                                    WHERE id = ?
                                    """,
                                    (hapus_id,)
                                )

                                conn_hapus.commit()
                                conn_hapus.close()

                                del st.session_state["hapus_sample_id"]

                                st.success("Data LOGBOOK berhasil dihapus.")
                                st.rerun()

                            else:

                                conn_hapus.close()

                                st.error("Data yang akan dihapus tidak ditemukan.")

                with col_batal:
                    if st.button(
                        "Batal",
                        key=f"btn_batal_hapus_{hapus_id}"
                    ):
                        del st.session_state["hapus_sample_id"]
                        st.rerun()




# =========================================================
# EDIT LOGBOOK
# =========================================================

            if "edit_sample_id" in st.session_state:

                edit_sample_id = st.session_state["edit_sample_id"]

                conn_edit = sqlite3.connect("incoming.db")
                cursor_edit = conn_edit.cursor()

                cursor_edit.execute(
                    """
                    SELECT
                        no_sampel,
                        tanggal,
                        nama_sampel,
                        keterangan
                    FROM logbook_sample
                    WHERE id = ?
                    """,
                    (edit_sample_id,)
                )

                data_edit = cursor_edit.fetchone()

                cursor_edit.execute(
                    """
                    SELECT
                        id,
                        jenis_logbook,
                        parameter,
                        hasil,
                        satuan,
                        analis,
                        tanggal_uji
                    FROM logbook_result
                    WHERE id IN (
                        SELECT MAX(id)
                        FROM logbook_result
                        WHERE sample_id = ?
                        GROUP BY jenis_logbook
                    )
                    ORDER BY id
                    """,
                    (edit_sample_id,)
                )

                hasil_edit = cursor_edit.fetchall()

                conn_edit.close()

                if data_edit is None:

                    st.error("Data yang akan diedit tidak ditemukan.")

                    if st.button(
                        "Tutup",
                        key="tutup_edit_error"
                    ):
                        del st.session_state["edit_sample_id"]
                        st.rerun()

                else:

                    st.divider()
                    st.subheader("Edit Data LOGBOOK")

                    edit_lot = st.text_input(
                        "LOT Sampel",
                        value=data_edit[0] or "",
                        key=f"edit_lot_{edit_sample_id}"
                    )

                    edit_tanggal = st.date_input(
                        "Tanggal",
                        value=pd.to_datetime(
                            data_edit[1]
                        ).date(),
                        key=f"edit_tanggal_{edit_sample_id}"
                    )

                    edit_nama = st.text_input(
                        "Nama Sampel",
                        value=data_edit[2] or "",
                        key=f"edit_nama_{edit_sample_id}"
                    )

                    edit_keterangan = st.text_area(
                        "Keterangan",
                        value=data_edit[3] or "",
                        key=f"edit_keterangan_{edit_sample_id}"
                    )

                    st.markdown("### Hasil Pengujian")

                    hasil_baru = []

                    for item in hasil_edit:

                        st.markdown(
                            f"**{item[1]}**"
                        )

                        edit_parameter = st.text_input(
                            "Parameter",
                            value=item[2] or "",
                            key=f"edit_parameter_{item[0]}"
                        )

                        edit_hasil = st.text_area(
                            "Hasil",
                            value=item[3] or "",
                            key=f"edit_hasil_{item[0]}"
                        )

                        edit_satuan = st.text_input(
                            "Satuan",
                            value=item[4] or "",
                            key=f"edit_satuan_{item[0]}"
                        )

                        edit_analis = st.text_input(
                            "Pelaksana",
                            value=item[5] or "",
                            key=f"edit_analis_{item[0]}"
                        )

                        edit_tanggal_uji = st.date_input(
                            "Tanggal Uji",
                            value=pd.to_datetime(
                                item[6]
                            ).date(),
                            key=f"edit_tanggal_uji_{item[0]}"
                        )

                        hasil_baru.append(
                            (
                                item[0],
                                edit_parameter,
                                edit_hasil,
                                edit_satuan,
                                edit_analis,
                                str(edit_tanggal_uji)
                            )
                        )

                    col_simpan, col_batal = st.columns(2)

                    with col_simpan:

                        if st.button(
                            "Simpan Perubahan",
                            type="primary",
                            use_container_width=True,
                            key=f"simpan_edit_{edit_sample_id}"
                        ):

                            conn_edit = sqlite3.connect(
                                "incoming.db"
                            )
                            cursor_edit = conn_edit.cursor()

                            cursor_edit.execute(
                                """
                                UPDATE logbook_sample
                                SET
                                    no_sampel = ?,
                                    tanggal = ?,
                                    nama_sampel = ?,
                                    keterangan = ?
                                WHERE id = ?
                                """,
                                (
                                    edit_lot,
                                    str(edit_tanggal),
                                    edit_nama,
                                    edit_keterangan,
                                    edit_sample_id
                                )
                            )

                            for item in hasil_baru:

                                cursor_edit.execute(
                                    """
                                    UPDATE logbook_result
                                    SET
                                        parameter = ?,
                                        hasil = ?,
                                        satuan = ?,
                                        analis = ?,
                                        tanggal_uji = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        item[1],
                                        item[2],
                                        item[3],
                                        item[4],
                                        item[5],
                                        item[0]
                                    )
                                )

                            cursor_edit.execute(
                                """
                                INSERT INTO logbook_riwayat
                                (
                                    sample_id,
                                    aksi,
                                    waktu,
                                    pengguna,
                                    detail
                                )
                                VALUES (
                                    ?,
                                    ?,
                                    datetime('now'),
                                    ?,
                                    ?
                                )
                                """,
                                (
                                    edit_sample_id,
                                    "Edit",
                                    st.session_state.get(
                                        "username",
                                        "admin"
                                    ),
                                    f"Mengubah data LOGBOOK - LOT: {edit_lot}"
                                )
                            )

                            conn_edit.commit()
                            conn_edit.close()

                            del st.session_state["edit_sample_id"]

                            st.success(
                                "Data LOGBOOK berhasil diperbarui."
                            )

                            st.rerun()

                    with col_batal:

                        if st.button(
                            "Batal Edit",
                            use_container_width=True,
                            key=f"batal_edit_{edit_sample_id}"
                        ):

                            del st.session_state[
                                "edit_sample_id"
                            ]

                            st.rerun()

            # =========================================================
            # DETAIL
            # =========================================================

            if "detail_sample_id" in st.session_state:

                sample_id = st.session_state[
                    "detail_sample_id"
                ]

                conn_detail = sqlite3.connect(
                    "incoming.db"
                )

                cursor_detail = conn_detail.cursor()

                cursor_detail.execute(
                    """
                    SELECT
                        no_sampel,
                        tanggal,
                        nama_sampel,
                        status,
                        keterangan
                    FROM logbook_sample
                    WHERE id = ?
                    """,
                    (sample_id,)
                )

                sample = cursor_detail.fetchone()

                cursor_detail.execute(
                    """
                    SELECT
                        jenis_logbook,
                        parameter,
                        hasil,
                        satuan,
                        analis,
                        tanggal_uji
                    FROM (
                        SELECT
                            jenis_logbook,
                            parameter,
                            hasil,
                            satuan,
                            analis,
                            tanggal_uji,
                            ROW_NUMBER() OVER (
                                PARTITION BY
                                    jenis_logbook,
                                    parameter,
                                    hasil,
                                    satuan,
                                    analis,
                                    tanggal_uji
                                ORDER BY id DESC
                            ) AS nomor
                        FROM logbook_result
                        WHERE sample_id = ?
                    )
                    WHERE nomor = 1
                    ORDER BY jenis_logbook
                    """,
                    (sample_id,)
                )

                hasil = cursor_detail.fetchall()

                conn_detail.close()

                st.divider()
                st.subheader("Detail Sampel")

                if sample:

                    st.write(
                        f"**LOT Sampel:** {sample[0]}"
                    )

                    st.write(
                        f"**Tanggal:** {sample[1]}"
                    )

                    st.write(
                        f"**Nama Sampel:** {sample[2]}"
                    )

                    st.write(
                        f"**Status:** {sample[3]}"
                    )

                    st.divider()

                    # =================================================
                    # KELOMPOKKAN HASIL BERDASARKAN JENIS UJI
                    # =================================================

                    hasil_per_uji = {}

                    for item in hasil:

                        jenis = item[0]

                        if jenis not in hasil_per_uji:
                            hasil_per_uji[jenis] = []

                        hasil_per_uji[jenis].append(item)

                    # =================================================
                    # TAMPILKAN DETAIL PER PENGUJIAN
                    # =================================================

                    for jenis, data_uji in hasil_per_uji.items():

                        st.markdown(
                            f"### {jenis}"
                        )

                        detail_data = []

                        for item in data_uji:

                            detail_data.append(
                                {
                                    "Parameter": item[1],
                                    "Hasil": item[2],
                                    "Satuan": item[3],
                                    "Pelaksana": item[4],
                                    "Tanggal Uji": item[5]
                                }
                            )

                        st.dataframe(
                            pd.DataFrame(detail_data),
                            use_container_width=True,
                            hide_index=True
                        )

                    if st.button(
                        "Tutup Detail",
                        key="tutup_detail"
                    ):

                        del st.session_state[
                            "detail_sample_id"
                        ]

                        st.rerun()
                    # =========================
                    # DOWNLOAD PDF
                    # =========================

                    pdf_file = buat_pdf_logbook(sample_id)

                    if pdf_file is not None:
                        st.download_button(
                            label="Download PDF",
                            data=pdf_file.getvalue(),
                            file_name=f"LOGBOOK_{sample_id}.pdf",
                            mime="application/pdf",
                            key=f"download_pdf_{sample_id}"
                        )

            st.divider()

            st.subheader("Download Data Result")

            def buat_excel_logbook():

                conn = sqlite3.connect("incoming.db")

                data_result = pd.read_sql_query(
                    """
                    SELECT
                        s.no_sampel AS "LOT Sampel",
                        s.tanggal AS "Tanggal Sampel",
                        s.nama_sampel AS "Nama Sampel",
                        s.kode_sampel AS "Kode Sampel",
                        s.keterangan AS "Keterangan",
                        s.status AS "Status",

                        r.jenis_logbook AS "Pengujian",
                        r.parameter AS "Parameter",
                        r.hasil AS "Hasil",
                        r.standar AS "Standar",
                        r.satuan AS "Satuan",
                        r.analis AS "Pelaksana",
                        r.tanggal_uji AS "Tanggal Uji"

                    FROM logbook_sample s

                    LEFT JOIN logbook_result r
                        ON s.id = r.sample_id

                    ORDER BY s.id DESC, r.id ASC
                    """,
                    conn
                )

                conn.close()

                output = io.BytesIO()

                with pd.ExcelWriter(
                    output,
                    engine="openpyxl"
                ) as writer:

                    data_result.to_excel(
                        writer,
                        index=False,
                        sheet_name="Result"
                    )

                output.seek(0)

                return output


            excel_file = buat_excel_logbook()

            st.download_button(
                label="📥 Download Excel",
                data=excel_file,
                file_name="database_logbook.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_logbook",
                use_container_width=True
            )

    elif logbook_menu == "Riwayat Perubahan":

        st.title("LOGBOOK - Riwayat Perubahan")

        conn_riwayat = sqlite3.connect("incoming.db")

        data_riwayat = pd.read_sql_query(
            """
            SELECT
                lr.id,
                ls.no_sampel AS "LOT Sampel",
                ls.nama_sampel AS "Nama Sampel",
                lr.aksi AS "Aksi",
                lr.waktu AS "Waktu",
                lr.pengguna AS "Pengguna",
                lr.detail AS "Detail"
            FROM logbook_riwayat lr
            LEFT JOIN logbook_sample ls
                ON lr.sample_id = ls.id
            ORDER BY lr.id DESC
            """,
            conn_riwayat
        )

        conn_riwayat.close()

        if data_riwayat.empty:

            st.info("Belum ada riwayat perubahan.")

        else:

            data_riwayat["Waktu"] = pd.to_datetime(
                data_riwayat["Waktu"],
                errors="coerce"
            ).dt.strftime("%d-%m-%Y %H:%M:%S")

            st.dataframe(
                data_riwayat,
                use_container_width=True,
                hide_index=True
            )