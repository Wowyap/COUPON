import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta

# --- 1. הגדרות עיצוב גלובליות ---
PASSWORD = "1"
GLOBAL_FONT_SIZE = "20px" 

# מילון לוגואים
LOGOS = {
    "רמי לוי": "https://he.wikipedia.org/wiki/%D7%A8%D7%9E%D7%99_%D7%9C%D7%95%D7%99_%D7%A9%D7%99%D7%95%D7%95%D7%A7_%D7%94%D7%A9%D7%A7%D7%9E%D7%94#/media/%D7%A7%D7%95%D7%91%D7%A5:RAMILEVI.png",
    "Dream Card": "https://www.just4u.co.il/Pictures/12621111.jpg",
    "ויקטורי": "https://upload.wikimedia.org/wikipedia/he/c/c9/Victory_Supermarket_Chain_Logo.png",
}
DEFAULT_LOGO = "https://cdn-icons-png.flaticon.com/512/726/726476.png"

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

# הזרקת CSS (כולל גודל פונט ואופטימיזציה לכפתורי הכיווץ)
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
    if not date_str or date_str == "" or date_str == "None":
        return datetime.max
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

# --- 3. חלון עריכה ---
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

# --- 4. כניסה ---
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

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = clean_data(df)
    except Exception as e:
        st.error(f"שגיאת חיבור: {e}"); st.stop()

    st.title("🎫 My Coupon Wallet")

    # מדדים
    if not df.empty:
        total_value = df['value'].apply(parse_amount).sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 שווי כולל", f"{total_value:,.2f} ₪")
        c2.metric("🎟️ קופונים", len(df))
        near_expiry = len([x for x in df['expiry'] if parse_expiry(x) < datetime.now() + timedelta(days=7)])
        c3.metric("📅 פגי תוקף בקרוב", near_expiry)

    st.sidebar.header("🕹️ תפריט")
    action = st.sidebar.radio("עבור אל:", ["הארנק שלי", "הוספה ידנית", "טעינה מרוכזת"])

    if action == "הוספה ידנית":
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            net = col1.text_input("רשת")
            val_input = col2.text_input("ערך")
            type_input = col1.selectbox("סוג", ["Link", "Code", "Credit Card"])
            exp_input = col2.text_input("תוקף (DD/MM/YY)")
            code_input = st.text_input("קוד או קישור")
            cvv_input = st.text_input("CVV")
            notes_input = st.text_area("הערות")
            if st.form_submit_button("🚀 שמור"):
                new_row = pd.DataFrame([{"network": net, "type": type_input, "value": val_input, 
                                         "code_or_link": code_input, "expiry": exp_input, 
                                         "cvv": cvv_input, "notes": notes_input}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("נשמר!"); st.rerun()

    elif action == "הארנק שלי":
        # --- הגדרת מצב כיווץ/הרחבה ב-Session State ---
        if "all_expanded" not in st.session_state:
            st.session_state.all_expanded = True # ברירת מחדל פתוח

        search = st.text_input("🔍 חיפוש רשת...")
        
        # כפתורי שליטה גלובליים
        col_exp1, col_exp2, _ = st.columns([1, 1, 4])
        if col_exp1.button("📂 הרחב הכל", use_container_width=True):
            st.session_state.all_expanded = True
            st.rerun()
        if col_exp2.button("📁 כווץ הכל", use_container_width=True):
            st.session_state.all_expanded = False
            st.rerun()

        st.markdown("---")

        df['temp_date'] = df['expiry'].apply(parse_expiry)
        display_df = df.sort_values(by='temp_date', ascending=True)
        if search:
            display_df = display_df[display_df['network'].str.contains(search, case=False, na=False)]

        if display_df.empty:
            st.info("אין קופונים.")
        else:
            networks = display_df['network'].unique()
            for net in networks:
                net_coupons = display_df[display_df['network'] == net]
                logo_url = LOGOS.get(net, DEFAULT_LOGO)
                
                # השינוי כאן: expanded מקבל את הערך מה-Session State
                with st.expander(f"🏢 **{net.upper()}** — ({len(net_coupons)} פריטים)", expanded=st.session_state.all_expanded):
                    st.image(logo_url, width=80)
                    for i, row in net_coupons.iterrows():
                        expiry_date = parse_expiry(row['expiry'])
                        bg_color = "#F8F9FA"
                        status_msg = ""
                        if expiry_date < datetime.now():
                            status_msg = "❌ פג תוקף"; bg_color = "#FFEBEE"
                        elif expiry_date < datetime.now() + timedelta(days=7):
                            status_msg = "⚠️ פג בקרוב!"; bg_color = "#FFF3E0"

                        with st.container(border=True):
                            st.markdown(f'<div style="background-color:{bg_color}; padding:15px; border-radius:10px;">', unsafe_allow_html=True)
                            c1, c2, c3 = st.columns([1, 2, 0.5])
                            with c1:
                                st.markdown(f"**ערך: {row['value']} ₪**")
                                if status_msg: st.markdown(f"*{status_msg}*")
                                st.write(f"תוקף: {row['expiry']}")
                                if row['cvv']: st.write(f"CVV: {row['cvv']}")
                            with c2:
                                val = str(row['code_or_link']).strip()
                                if val.startswith("http"): st.link_button("🌐 פתח קישור", val, use_container_width=True)
                                else: st.code(val, language="text")
                                if row['notes']: st.caption(f"💡 {row['notes']}")
                            with c3:
                                if st.button("✏️", key=f"edit_{i}"): edit_coupon_dialog(i, row, df, conn)
                                if st.button("🗑️", key=f"del_{i}"):
                                    conn.update(worksheet="Sheet1", data=df.drop(i).reset_index(drop=True))
                                    st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

    if st.sidebar.button("🔓 Logout"):
        st.session_state.authenticated = False
        st.rerun()
