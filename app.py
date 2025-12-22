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
# CSS – RTL + Mobile + Card Design
# ===============================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] { direction: rtl; text-align: right; }
    div[data-testid="stVerticalBlock"] > div { width: 100% !important; }
    
    .coupon-card {
        padding: 1.2rem; border-radius: 12px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .group-summary {
        background-color: #f0f2f6; padding: 10px; border-radius: 8px;
        margin-bottom: 15px; border-right: 5px solid #007bff;
        font-weight: bold;
    }
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f8f9fa; padding: 10px; border-radius: 6px;
        font-family: monospace; word-break: break-all; margin: 10px 0;
        border: 1px dashed #adb5bd;
    }
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
    try: return datetime.strptime(val, "%d/%m/%Y").date()
    except: return None

def is_url(string):
    return string.startswith(('http://', 'https://', 'www.'))

# ===============================
# Load data
# ===============================
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=0)
df = df.fillna("")

# ===============================
# Sidebar
# ===============================
page = st.sidebar.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון"])

# ===============================
# Page: Add Coupon
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        network = st.text_input("רשת / חנות")
        value = st.text_input("ערך (לדוגמה: 100 שח)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        link = st.text_input("קוד או קישור")
        if st.form_submit_button("שמור בארנק"):
            if network and value:
                new_row = pd.DataFrame([{"network": network, "value": value, "expiry": expiry_date.strftime("%d/%m/%Y"), "code_or_link": link}])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df)
                st.success("הקופון נשמר!")
                st.rerun()

# ===============================
# Page: Wallet
# ===============================
else:
    st.header("🎫 הארנק שלי")
    
    # חישוב שווי כללי
    df["amount_calc"] = df["value"].apply(parse_amount)
    total_all = df["amount_calc"].sum()
    st.info(f"💰 **שווי כולל בארנק:** ₪ {total_all:,.0f} ({len(df)} קופונים)")

    # חיפוש
    search = st.text_input("🔍 חיפוש מהיר...")
    if search:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    # שליטה גלובלית
    col_c1, col_c2 = st.columns(2)
    expand_all = col_c1.button("↔️ הרחב הכל", use_container_width=True)
    collapse_all = col_c2.button("↕️ קבץ הכל", use_container_width=True)
    
    if "expand_state" not in st.session_state: st.session_state.expand_state = True
    if expand_all: st.session_state.expand_state = True
    if collapse_all: st.session_state.expand_state = False

    # קיבוץ לפי רשת
    networks = sorted(df["network"].unique())
    
    for net in networks:
        net_df = df[df["network"] == net]
        group_total = net_df["amount_calc"].sum()
        
        with st.expander(f"📦 {net} | {len(net_df)} קופונים | ₪ {group_total:,.0f}", expanded=st.session_state.expand_state):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" # ברירת מחדל ירוק
                if exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"
                    elif days <= 14: color = "#ffa500"

                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.2rem; font-weight:bold;">{row['value']}</span>
                        <span style="color:#666;">תוקף: {row['expiry']}</span>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                </div>
                """, unsafe_allow_html=True)

                # שורת כפתורי פעולה
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
                
                with btn_col1:
                    # חלון עריכה קופץ (Popover)
                    with st.popover("✏️ עריכה", use_container_width=True):
                        st.write(f"עדכון פרטים: {row['network']}")
                        e_net = st.text_input("רשת", value=row['network'], key=f"e_net_{i}")
                        e_val = st.text_input("ערך", value=row['value'], key=f"e_val_{i}")
                        e_exp = st.date_input("תוקף", value=parse_expiry(row['expiry']) or date.today(), key=f"e_exp_{i}")
                        e_link = st.text_input("קוד/לינק", value=row['code_or_link'], key=f"e_link_{i}")
                        if st.button("שמור שינויים", key=f"save_{i}"):
                            df.at[i, "network"] = e_net
                            df.at[i, "value"] = e_val
                            df.at[i, "expiry"] = e_exp.strftime("%d/%m/%Y")
                            df.at[i, "code_or_link"] = e_link
                            conn.update(worksheet="Sheet1", data=df.drop(columns=["amount_calc"]))
                            st.success("עודכן!")
                            st.rerun()

                with btn_col2:
                    # כפתור לינק חכם
                    link_val = row['code_or_link']
                    if is_url(link_val):
                        # אם זה לינק, הקישור יתחיל ב-https אם חסר
                        url_to_open = link_val if link_val.startswith('http') else f"https://{link_val}"
                        st.link_button("🌐 מעבר ללינק", url_to_open, use_container_width=True)
                    else:
                        st.button("🔗 אין לינק", disabled=True, use_container_width=True)

                with btn_col3:
                    if st.button("🗑️ מחיקה", key=f"del_{i}", use_container_width=True):
                        df = df.drop(i)
                        conn.update(worksheet="Sheet1", data=df.reset_index(drop=True).drop(columns=["amount_calc"]))
                        st.rerun()
                        
