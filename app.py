import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# ===============================
# Page config
# ===============================
st.set_page_config(page_title="ארנק קופונים חכם", page_icon="🎫", layout="wide")

# ===============================
# CSS – RTL & Mobile Fixes
# ===============================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    .coupon-card {
        padding: 15px;
        border-radius: 12px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        width: 100%;
        box-sizing: border-box;
    }
    .code-container {
        direction: ltr !important;
        text-align: left !important;
        background: #f8f9fa;
        padding: 10px;
        border-radius: 6px;
        font-family: monospace;
        word-break: break-all;
        margin-top: 10px;
        border: 1px dashed #adb5bd;
    }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ===============================
# Helpers
# ===============================
def parse_amount(val):
    try:
        nums = re.findall(r"\d+\.?\d*", str(val))
        return float(nums[0]) if nums else 0.0
    except: return 0.0

def parse_expiry(val):
    try:
        val_str = str(val).split(" ")[0] 
        return datetime.strptime(val_str, "%d/%m/%Y").date()
    except: return None

def is_url(string):
    try:
        s = str(string).lower().strip()
        return s.startswith(('http://', 'https://', 'www.'))
    except: return False

# ===============================
# Load data
# ===============================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    
    # --- התיקון הקריטי כאן ---
    # אם העמודה ריקה, נשים "פעיל" כברירת מחדל כדי שהקופונים לא ייעלמו
    if "sstatus" in df.columns:
        df["sstatus"] = df["sstatus"].replace("", "פעיל").fillna("פעיל")
    else:
        df["sstatus"] = "פעיל"
    
    df = df.fillna("")
            
except Exception as e:
    st.error(f"שגיאה בחיבור: {e}")
    st.stop()

def save_to_sheets(target_df):
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)

# ===============================
# Sidebar Navigation
# ===============================
page = st.sidebar.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])

# ===============================
# Page: Add Coupon
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        col_r1, col_r2 = st.columns(2)
        network = col_r1.text_input("רשת / חנות")
        value = col_r2.text_input("ערך (לדוגמה: 100)")
        
        col_r3, col_r4 = st.columns(2)
        expiry_date = col_r3.date_input("תוקף", min_value=date.today())
        cvv = col_r4.text_input("CVV (אם יש)")
        
        link = st.text_input("קוד או קישור")
        note = st.text_area("הערות")
        
        if st.form_submit_button("שמור בארנק"):
            if network and value:
                new_row = pd.DataFrame([{
                    "network": network, "value": value, 
                    "expiry": expiry_date.strftime("%d/%m/%Y"),
                    "code_or_link": link, "cvv": cvv, 
                    "note": note, "sstatus": "פעיל"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheets(df)
                st.success("נשמר בהצלחה!")
                st.rerun()
            else:
                st.warning("חובה למלא שם רשת וערך")

# ===============================
# Page: Wallet & Archive
# ===============================
else:
    is_archive = (page == "📁 ארכיון (נוצלו)")
    target_status = "נוצל" if is_archive else "פעיל"
    
    st.header("🎫 הארנק שלי" if not is_archive else "📁 ארכיון קופונים")
    
    df["amount_calc"] = df["value"].apply(parse_amount)
    # סינון לפי הסטטוס
    display_df = df[df["sstatus"] == target_status].copy()
    
    total_val = display_df["amount_calc"].sum()
    st.info(f"💰 **סה\"כ:** ₪ {total_val:,.0f} | {len(display_df)} קופונים")

    search = st.text_input("🔍 חיפוש...")
    if search:
        display_df = display_df[display_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    networks = sorted(display_df["network"].unique())
    
    for net in networks:
        net_df = display_df[display_df["network"] == net]
        with st.expander(f"📦 {net} ({len(net_df)})", expanded=True):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" if target_status == "פעיל" else "#6c757d"
                
                if target_status == "פעיל" and exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"
                    elif days <= 14: color = "#ffa500"

                cvv_txt = f" | CVV: {row['cvv']}" if row['cvv'] else ""
                note_txt = f"<div style='font-size:0.85rem; color:#555; margin-top:5px;'>📝 {row['note']}</div>" if row['note'] else ""
                
                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between;">
                        <div style="font-weight:bold;">{row['value']}{cvv_txt}</div>
                        <div style="font-size:0.85rem; color:#666;">תוקף: {row['expiry']}</div>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                    {note_txt}
                </div>
                """, unsafe_allow_html=True)

                b1, b2, b3 = st.columns([1, 1, 1])
                
                with b1:
                    label = "⏪ החזר" if is_archive else "✅ מומש"
                    if st.button(label, key=f"stat_{i}"):
                        df.at[i, "sstatus"] = "פעיל" if is_archive else "נוצל"
                        save_to_sheets(df)
                        st.rerun()
                
                with b2:
                    with st.popover("✏️"):
                        u_net = st.text_input("רשת", value=row['network'], key=f"u_n_{i}")
                        u_val = st.text_input("ערך", value=row['value'], key=f"u_v_{i}")
                        u_exp = st.date_input("תוקף", value=exp_dt if exp_dt else date.today(), key=f"u_e_{i}")
                        u_cvv = st.text_input("CVV", value=row['cvv'], key=f"u_c_{i}")
                        u_link = st.text_input("קוד/לינק", value=row['code_or_link'], key=f"u_l_{i}")
                        u_note = st.text_area("הערה", value=row['note'], key=f"u_nt_{i}")
                        if st.button("עדכן", key=f"upd_{i}"):
                            df.at[i, ["network", "value", "code_or_link", "cvv", "note"]] = [u_net, u_val, u_link, u_cvv, u_note]
                            df.at[i, "expiry"] = u_exp.strftime("%d/%m/%Y")
                            save_to_sheets(df)
                            st.rerun()

                with b3:
                    if st.button("🗑️", key=f"del_{i}"):
                        df = df.drop(i)
                        save_to_sheets(df)
                        st.rerun()
