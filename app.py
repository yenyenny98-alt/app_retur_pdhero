import streamlit as st

st.set_page_config(
    page_title="Pencatatan Retur PD Hero ke PT CAPP",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
from datetime import date, datetime
import os
import time
from supabase import create_client, Client
import json


# Custom CSS untuk tampilan e-commerce
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 1rem;
        padding: 12px;
        background-color: #F8F9FA;
        border-radius: 10px;
        border: 2px solid #2E86AB;
        font-weight: bold;
    }
    .badge {
        padding: 3px 6px;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .badge-waiting {
        background-color: #FFE9C9;
        color: #D35400;
    }
    .badge-approved {
        background-color: #D4F7E8;
        color: #27AE60;
    }
    .badge-destroyed {
        background-color: #E8DAFF;
        color: #8E44AD;
    }
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 4px solid #2E86AB;
    }
</style>
""", unsafe_allow_html=True)

# ==================== KONFIGURASI SUPABASE ====================
@st.cache_resource
def init_supabase_connection():
    """Initialize Supabase connection"""
    try:
        # Menggunakan secrets Streamlit
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        supabase = create_client(supabase_url, supabase_key)
        st.sidebar.success("✅ Koneksi Supabase berhasil!")
        return supabase
    except Exception as e:
        st.sidebar.error(f"❌ Koneksi Supabase gagal: {e}")
        return None

# ==================== INISIALISASI SESSION STATE ====================
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.retur_data = None
    st.session_state.show_destroy_form = None
    st.session_state.show_add_form = False
    st.session_state.supabase = init_supabase_connection()

# Inisialisasi expanded_cards jika belum ada
if 'expanded_cards' not in st.session_state:
    st.session_state.expanded_cards = {}

# ==================== FUNGSI DATABASE SUPABASE ====================
def load_data():
    """Load data dari Supabase"""
    try:
        supabase = st.session_state.supabase
        if supabase:
            response = supabase.table("retur").select("*").order("created_at", desc=True).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                
                # DEBUG: Tampilkan kolom yang ada
                st.sidebar.write("📊 Kolom dari database:", list(df.columns))
                
                # Mapping column names - pastikan sesuai dengan database
                column_mapping = {
                    'id': 'ID',
                    'no_nota_retur': 'No Nota Retur',
                    'tanggal_pengajuan': 'Tanggal Pengajuan',
                    'nama_barang': 'Nama Barang',
                    'quantity': 'Quantity',
                    'satuan': 'Satuan',
                    'tanggal_ed': 'Tanggal ED',
                    'alasan': 'Alasan',
                    'form_retur': 'Form Retur',
                    'berita_acara': 'Berita Acara',
                    'status': 'Status',  # Pastikan ini 'status' bukan 'Status'
                    'created_at': 'Dibuat Pada',
                    'updated_at': 'Diupdate Pada'
                }
                
                # Rename columns
                df = df.rename(columns=column_mapping)
                
                # Pastikan kolom Status ada
                if 'Status' not in df.columns:
                    st.sidebar.error("❌ Kolom 'Status' tidak ditemukan setelah mapping")
                    st.sidebar.write("Kolom yang ada:", list(df.columns))
                
                return df
            else:
                st.sidebar.info("📝 Database kosong")
                return pd.DataFrame()
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def save_data_automatic(df):
    """Simpan data ke Supabase"""
    try:
        supabase = st.session_state.supabase
        if supabase:
            # Convert dataframe to records
            records = df.to_dict('records')
            
            for record in records:
                # Prepare data for Supabase
                supabase_data = {
                    'no_nota_retur': record['No Nota Retur'],
                    'tanggal_pengajuan': record['Tanggal Pengajuan'],
                    'nama_barang': record['Nama Barang'],
                    'quantity': record['Quantity'],
                    'satuan': record['Satuan'],
                    'tanggal_ed': record['Tanggal ED'],
                    'alasan': record['Alasan'],
                    'form_retur': record.get('Form Retur', ''),
                    'berita_acara': record.get('Berita Acara', ''),
                    'status': record['Status'],
                    'created_at': record['Dibuat Pada'],
                    'updated_at': record['Diupdate Pada']
                }
                
                # Check if record exists
                existing = supabase.table("retur").select("*").eq("no_nota_retur", supabase_data["no_nota_retur"]).execute()
                
                if existing.data:
                    # Update existing record
                    result = supabase.table("retur").update(supabase_data).eq("no_nota_retur", supabase_data["no_nota_retur"]).execute()
                    st.sidebar.success(f"✅ Updated: {supabase_data['no_nota_retur']}")
                else:
                    # Insert new record
                    result = supabase.table("retur").insert(supabase_data).execute()
                    st.sidebar.success(f"✅ Inserted: {supabase_data['no_nota_retur']}")
            
            return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

def delete_retur(no_nota_retur):
    """Hapus data retur dari Supabase"""
    try:
        supabase = st.session_state.supabase
        if supabase:
            result = supabase.table("retur").delete().eq("no_nota_retur", no_nota_retur).execute()
            st.sidebar.success(f"✅ Deleted: {no_nota_retur}")
            return True
    except Exception as e:
        st.error(f"Error deleting data: {e}")
        return False

# ==================== FUNGSI UTILITAS ====================
def format_tanggal(tanggal):
    """Format tanggal untuk display"""
    if pd.notna(tanggal):
        try:
            if isinstance(tanggal, str):
                try:
                    tanggal = datetime.strptime(tanggal, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        tanggal = datetime.strptime(tanggal, '%Y-%m-%d')
                    except:
                        return str(tanggal)[:10]
            if isinstance(tanggal, (pd.Timestamp, datetime)):
                return tanggal.strftime('%d %b %Y')
        except:
            try:
                return str(tanggal)[:10]
            except:
                return "Format tanggal tidak valid"
    return "Tanggal tidak tersedia"

def generate_nota_number():
    """Generate nomor nota otomatis"""
    today = date.today()
    year_month = today.strftime("%Y/%m")
    
    last_number = 0
    if st.session_state.retur_data is not None and not st.session_state.retur_data.empty:
        current_month_data = st.session_state.retur_data[
            st.session_state.retur_data["No Nota Retur"].str.startswith(year_month, na=False)
        ]
        
        if not current_month_data.empty:
            for nota in current_month_data["No Nota Retur"]:
                try:
                    parts = nota.split('/')
                    if len(parts) == 3:
                        number = int(parts[2])
                        if number > last_number:
                            last_number = number
                except:
                    continue
    
    new_number = last_number + 1
    return f"{year_month}/{new_number:03d}"

# ==================== FUNGSI TAMPILAN ====================
def toggle_card_expansion(card_id):
    """Toggle status expand card"""
    st.session_state.expanded_cards[card_id] = not st.session_state.expanded_cards.get(card_id, False)

def display_retur_card(retur, badge_class, idx):
    """Tampilkan card retur dengan expandable detail"""
    retur_id = retur['No Nota Retur']
    is_expanded = st.session_state.expanded_cards.get(retur_id, False)
    
    quantity_display = f"{retur['Quantity']} {retur['Satuan']}" if 'Satuan' in retur and pd.notna(retur['Satuan']) else f"{retur['Quantity']}"
    
    # Tampilkan panah expand/collapse
    arrow_icon = "▼" if is_expanded else "▶"
    
    # Gunakan container untuk membuat card yang bisa di-expand
    with st.container():
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            # Tombol expand dengan hanya nomor retur dan panah
            if st.button(f"Retur #{retur['No Nota Retur']} {arrow_icon}", 
                        key=f"expand_{retur_id}_{idx}", 
                        use_container_width=True,
                        help="Klik untuk melihat detail"):
                toggle_card_expansion(retur_id)
                st.rerun()
        
        with col2:
            # Tombol status badge
            st.markdown(f"<span class='badge {badge_class}'>{retur['Status']}</span>", unsafe_allow_html=True)
        
        # Tampilkan detail jika expanded
        if is_expanded:
            st.markdown("---")
            st.markdown("### 📋 Detail Retur")
            
            col5, col6 = st.columns(2)
            with col5:
                st.write(f"**No Nota Retur:** {retur['No Nota Retur']}")
                st.write(f"**Nama Barang:** {retur['Nama Barang']}")
                st.write(f"**Quantity:** {quantity_display}")
                st.write(f"**Tanggal Pengajuan:** {format_tanggal(retur['Tanggal Pengajuan'])}")
                st.write(f"**Dibuat Pada:** {format_tanggal(retur['Dibuat Pada'])}")
            
            with col6:
                st.write(f"**Tanggal ED:** {format_tanggal(retur['Tanggal ED'])}")
                st.write(f"**Alasan:** {retur['Alasan']}")
                st.write(f"**Status:** {retur['Status']}")
                st.write(f"**Diupdate Pada:** {format_tanggal(retur['Diupdate Pada'])}")
            
            st.markdown("---")
            
            # Tombol aksi
            col7, col8 = st.columns(2)
            
            with col7:
                if retur['Status'] == "Menunggu Persetujuan":
                    if st.button("✅ Setujui", key=f"approve_{retur_id}_{idx}", use_container_width=True):
                        # Update status di Supabase
                        retur_df = st.session_state.retur_data
                        main_idx = retur_df[retur_df['No Nota Retur'] == retur_id].index[0]
                        retur_df.loc[main_idx, "Status"] = "Sudah Disetujui"
                        retur_df.loc[main_idx, "Diupdate Pada"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if save_data_automatic(retur_df):
                            st.success("✅ Retur disetujui dan disimpan otomatis!")
                            time.sleep(1)
                            st.rerun()
                elif retur['Status'] == "Sudah Disetujui":
                    if st.button("🔥 Musnahkan", key=f"destroy_{retur_id}_{idx}", use_container_width=True):
                        st.session_state.show_destroy_form = idx
                        st.rerun()
            
            with col8:
                if st.button("🗑️ Hapus", key=f"delete_{retur_id}_{idx}", use_container_width=True):
                    # Hapus dari Supabase
                    if delete_retur(retur_id):
                        # Refresh data
                        st.session_state.retur_data = load_data()
                        st.success("✅ Retur dihapus dan disimpan otomatis!")
                        time.sleep(1)
                        st.rerun()
        
        st.markdown("---")

# ==================== BAGIAN UTAMA APLIKASI ====================
# Load data jika belum diload
if st.session_state.retur_data is None:
    st.session_state.retur_data = load_data()

retur_df = st.session_state.retur_data

# ==================== SIDEBAR NAVIGASI ====================
with st.sidebar:
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.header("📊 Dashboard")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Info koneksi
    if st.session_state.supabase:
        st.success("✅ Terhubung ke Supabase")
        try:
            # Hitung total data
            result = st.session_state.supabase.table("retur").select("id", count="exact").execute()
            st.info(f"📊 Total data: {result.count} retur")
        except:
            st.info("📊 Total data: Loading...")
    else:
        st.error("❌ Tidak terhubung ke database")
    
    # Debug info
    if not retur_df.empty:
        st.write("🔍 Kolom DataFrame:", list(retur_df.columns))
    
    st.markdown("---")
    
    # Tombol refresh
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.session_state.retur_data = load_data()
        st.rerun()
    
    if st.button("🗑️ Clear Cache", use_container_width=True):
        st.cache_resource.clear()
        st.session_state.retur_data = load_data()
        st.rerun()
    
    st.markdown("---")
    
    # Statistik
    if not retur_df.empty and 'Status' in retur_df.columns:
        stats = retur_df['Status'].value_counts()
        st.markdown("### 📈 Statistik Status")
        for status, count in stats.items():
            st.write(f"**{status}:** {count}")
    else:
        st.info("📝 Tidak ada data atau kolom Status tidak ditemukan")

# ==================== HALAMAN UTAMA ====================
st.markdown('<h1 class="main-header">📦 Pencatatan Retur PD Hero ke PT CAPP</h1>', unsafe_allow_html=True)

# Cek koneksi database
if st.session_state.supabase is None:
    st.error("""
    ❌ **Koneksi Database Gagal**
    
    Pastikan:
    1. Supabase URL dan Key benar di secrets.toml
    2. Tabel 'retur' sudah dibuat di Supabase
    3. Internet connection stabil
    """)
    st.stop()

# Tombol untuk tambah retur
if st.button("➕ Ajukan Retur Baru", use_container_width=True, key="add_retur_main"):
    st.session_state.show_add_form = True
    st.rerun()

# Form tambah retur baru
if st.session_state.show_add_form:
    st.markdown("---")
    st.markdown("### ➕ Ajukan Retur Baru")
    
    with st.form("form_retur"):
        col1, col2 = st.columns(2)
        
        with col1:
            nota = generate_nota_number()
            st.text_input("No Nota Retur*", value=nota, disabled=True)
            tanggal_pengajuan = st.date_input("Tanggal Pengajuan*", date.today())
            barang = st.text_input("Nama Barang*", placeholder="Masukkan nama barang")
            
        with col2:
            st.markdown("**Quantity***")
            qty_col, unit_col = st.columns([2, 1])
            with qty_col:
                qty = st.number_input("Jumlah", min_value=1, step=1, label_visibility="collapsed")
            with unit_col:
                satuan = st.selectbox("Satuan", ["DUS", "BKS", "PAIL", "UNIT", "PCS"], 
                                    index=0, label_visibility="collapsed")
            
            tanggal_ed = st.date_input("Tanggal ED*")
            alasan_option = st.selectbox("Alasan Retur*", [
                "Kadarluasa", 
                "Plastik Dalam Pecah", 
                "Lembab dan Menggumpal", 
                "Isi sendiri"
            ])
            
            if alasan_option == "Isi sendiri":
                custom_reason = st.text_input("Masukkan alasan retur*", placeholder="Ketik alasan retur di sini")
                alasan = custom_reason
            else:
                alasan = alasan_option
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("📤 Ajukan Retur", use_container_width=True)
        with col2:
            if st.form_submit_button("❌ Batal", use_container_width=True):
                st.session_state.show_add_form = False
                st.rerun()
        
        if submitted:
            if not barang or (alasan_option == "Isi sendiri" and not custom_reason):
                st.error("Harap isi semua field yang wajib (*)")
            else:
                new_data = pd.DataFrame([{
                    "No Nota Retur": nota,
                    "Tanggal Pengajuan": tanggal_pengajuan.strftime('%Y-%m-%d'),
                    "Nama Barang": barang,
                    "Quantity": qty,
                    "Satuan": satuan,
                    "Tanggal ED": tanggal_ed.strftime('%Y-%m-%d'),
                    "Alasan": alasan,
                    "Form Retur": "",
                    "Berita Acara": "",
                    "Status": "Menunggu Persetujuan",
                    "Dibuat Pada": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "Diupdate Pada": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }])

                # SIMPAN OTOMATIS ke Supabase
                updated_df = pd.concat([retur_df, new_data], ignore_index=True)
                if save_data_automatic(updated_df):
                    st.session_state.show_add_form = False
                    st.session_state.retur_data = load_data()  # Reload data
                    st.success("✅ Retur berhasil diajukan dan disimpan di cloud!")
                    time.sleep(1)
                    st.rerun()

# Tab Status Retur
st.markdown("### 📊 Status Retur")
tab1, tab2, tab3 = st.tabs(["Menunggu Persetujuan", "Sudah Disetujui", "Sudah Dimusnahkan"])

# Fungsi untuk filter data dengan safety check
def filter_data_by_status(df, status):
    if df.empty:
        return pd.DataFrame()
    
    if 'Status' not in df.columns:
        st.error(f"❌ Kolom 'Status' tidak ditemukan dalam data")
        st.write("Kolom yang tersedia:", list(df.columns))
        return pd.DataFrame()
    
    return df[df["Status"] == status]

with tab1:
    filtered_df = filter_data_by_status(retur_df, "Menunggu Persetujuan")
    if filtered_df.empty:
        st.info("Tidak ada retur yang menunggu persetujuan")
    else:
        for idx, retur in filtered_df.iterrows():
            display_retur_card(retur, "badge-waiting", idx)

with tab2:
    filtered_df = filter_data_by_status(retur_df, "Sudah Disetujui")
    if filtered_df.empty:
        st.info("Tidak ada retur yang sudah disetujui")
    else:
        for idx, retur in filtered_df.iterrows():
            display_retur_card(retur, "badge-approved", idx)

with tab3:
    filtered_df = filter_data_by_status(retur_df, "Sudah Dimusnahkan")
    if filtered_df.empty:
        st.info("Tidak ada retur yang sudah dimusnahkan")
    else:
        for idx, retur in filtered_df.iterrows():
            display_retur_card(retur, "badge-destroyed", idx)

# Form Pemusnahan
if st.session_state.show_destroy_form is not None:
    st.markdown("---")
    st.subheader("📝 Konfirmasi Pemusnahan")
    
    idx = st.session_state.show_destroy_form
    retur_data = retur_df.loc[idx]
    
    quantity_display = f"{retur_data['Quantity']} {retur_data['Satuan']}" if 'Satuan' in retur_data and pd.notna(retur_data['Satuan']) else f"{retur_data['Quantity']}"
    
    st.write(f"**No Nota Retur:** {retur_data['No Nota Retur']}")
    st.write(f"**Nama Barang:** {retur_data['Nama Barang']}")
    st.write(f"**Quantity:** {quantity_display}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Konfirmasi Pemusnahan", key="confirm_destroy"):
            # Update status di Supabase
            retur_df.loc[idx, "Status"] = "Sudah Dimusnahkan"
            retur_df.loc[idx, "Diupdate Pada"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if save_data_automatic(retur_df):
                st.session_state.show_destroy_form = None
                st.session_state.retur_data = load_data()  # Reload data
                st.success("✅ Pemusnahan berhasil dikonfirmasi!")
                time.sleep(1)
                st.rerun()
    
    with col2:
        if st.button("❌ Batal", key="cancel_destroy"):
            st.session_state.show_destroy_form = None
            st.rerun()

# ==================== FOOTER ====================
st.markdown("---")
st.caption("© 2024 PD Hero - PT CAPP Retur Management System | Cloud Database | Data tersimpan permanen")