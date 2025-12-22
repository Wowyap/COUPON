import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta

# --- 1. הגדרות עיצוב ---
PASSWORD = "3430"
GLOBAL_FONT_SIZE = "20px" 

LOGOS = {
    "רמי לוי": "https://upload.wikimedia.org/wikipedia/he/thumb/6/6a/Rami_Levy_logo.svg/250px-Rami_Levy_logo.svg.png",
    "Dream Card": "https://www.just4u.co.il/Pictures/12621111.jpg",
    "ויקטורי": "https://upload.wikimedia.org/wikipedia/he/c/c9/Victory_Supermarket_Chain_Logo.png",
}
DEFAULT_LOGO = "https://cdn-icons-png.flaticon.com/512/726/726476.png"

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

st.markdown(f"""
    <style>
    html, body, [class*="st-"], p, div, span, input, label, button {{
        font-size: {GLOBAL_FONT_SIZE} !important;
    }}
    code {{ font-size: {GLOBAL_FONT_SIZE} !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר ---
def clean_data(df):
    for col in df.columns:
        df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
    return df

def parse_expiry(date_str):
    if not date_str or date_str in ["", "None", "nan"]: return datetime.max
    formats = ["%d/%m/%Y", "%d/%m/%y", "%m/%y", "%m/%Y", "%Y-%m-%d"]
    for fmt in formats:
        try: return datetime.strptime(date_str, fmt)
        except: continue
    return datetime.max

def parse_amount(val):
    try:
        val = str(val).lower().replace('₪', '').strip()
        if 'x' in val:
            parts = val.split('x')
            return float(parts[0]) * float(parts[1])
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
        return float(numbers[0]) if numbers else 0.0
    except: return 0.0

@st.dialog("ערוך קופון ✏️")
def edit_coupon_dialog(index, row_data, df, conn):
    with st.form("edit_form"):
        st.markdown(f"### עריכה: **{row_data['network']}**")
        new_net = st.text_input("שם הרשת", value=row_data['network'])
        new_val = st.text_input("ערך", value=row_data['value'])
        new_type = st.selectbox("סוג", ["Link", "Code", "Credit Card"], 
                               index=["Link", "Code", "Credit Card"].index(row_data['type']) if row_data['type'] in ["Link", "Code", "Credit Card"] else 0)
        new_code = st.text_input("קוד/קישור", value=row_data['code_or_link'])
        new_exp = st.text_input("תוקף", value=row_data['expiry'])
        new_cvv = st.text_input("CVV", value=row_data['cvv'])
        new_notes = st.text_area("הערות", value=row_data['notes'])
        if st.form_submit_button("💾 שמור"):
            df.at[index, 'network'] = new_net
            df.at[index, 'value'] = new_val
            df.at[index, 'type'] = new_type
            df.at[index, 'code_or_link'] = new_code
            df.at[index, 'expiry'] = new_exp
            df.at[index, 'cvv'] = new_cvv
            df.at[index, 'notes'] = new_notes
            conn.update(worksheet="Sheet1", data=df)
            st.rerun()

def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Login")
        pwd = st.text_input("Password:", type="password")
        if st.button("Enter"):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Wrong password")
        return False
    return True

# --- 3. הרצה ---
if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = clean_data(conn.read(worksheet="Sheet1", ttl="0"))

    st.title("🎫 My Coupon Wallet")
    
    # תפריט צד
    action = st.sidebar.radio("עבור אל:", ["הארנק שלי", "הוספה ידנית"])

    if action == "הוספה ידנית":
        with st.form("add_form"):
            net = st.text_input("רשת")
            val = st.text_input("ערך")
            type_i = st.selectbox("סוג", ["Link", "Code", "Credit Card"])
            exp = st.text_input("תוקף")
            code = st.text_input("קוד")
            cvv = st.text_input("CVV")
            notes = st.text_area("הערות")
            if st.form_submit_button("שמור"):
                new_row = pd.DataFrame([{"network": net, "type": type_i, "value": val, "code_or_link": code, "expiry": exp, "cvv": cvv, "notes": notes}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("נשמר!"); st.rerun()

    elif action == "הארנק שלי":
        if "all_expanded" not in st.session_state: st.session_state.all_expanded = True
        c_exp1, c_exp2, _ = st.columns([1, 1, 4])
        if c_exp1.button("📂 הרחב"): st.session_state.all_expanded = True; st.rerun()
        if c_exp2.button("📁 כווץ"): st.session_state.all_expanded = False; st.rerun()

        display_df = df.sort_values(by='network')
        for net in display_df['network'].unique():
            with st.expander(f"🏢 {net}", expanded=st.session_state.all_expanded):
                st.image(LOGOS.get(net, DEFAULT_LOGO), width=80)
                for i, row in display_df[display_df['network'] == net].iterrows():
                    with st.container(border=True):
                        st.write(f"**ערך: {row['value']}** | תוקף: {row['expiry']}")
                        if str(row['code_or_link']).startswith("http"): st.link_button("פתח", row['code_or_link'])
                        else: st.code(row['code_or_link'])
                        if st.button("✏️", key=f"ed_{i}"): edit_coupon_dialog(i, row, df, conn)
