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
# CSS – תיקון סופי למובייל ולטקסט אנכי
# ===============================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    
    /* מניעת הפיכת טקסט לטור אנכי צר */
    div[data-testid="stVerticalBlock"] > div {
        width: 100% !important;
        flex: unset !important;
    }

    .coupon-card {
        padding: 1.2rem; border-radius: 12px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        width: 100%;
    }
    
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f8f9fa; padding: 10px; border-radius: 6px;
        font-family: monospace; word-break: break-all; margin: 10px 0;
        border: 1px dashed #adb5bd;
        white-space: normal;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# Helpers – תיקון ה-AttributeError
# ===============================
def parse_amount(val):
    try:
        nums = re.findall(r"\d+\.?\d*", str(val))
        return float(nums[0]) if nums else 0.0
    except: return 0.0

def parse_expiry(val):
    try: return datetime.strptime(str(val), "%d/%m/%Y").date()
    except: return None

def is_url(string):
    # וידוא שהערך הוא מחרוזת כדי למנוע AttributeError
    s = str(string).lower().strip()
    return s.startswith(('http://', 'https://', 'www.'))

# ===============================
# Load data
# ===============================
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=0)
df = df.fillna("")

# ===============================
# Sidebar & Navigation
# ===============================
page = st.sidebar.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון"])

# ===============================
# Page: Add Coupon
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        network = st.text_input("רשת / חנות")
        value = st.text_input("ערך (לדוגמה: 100)")
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
    
    df["amount_calc"] = df["value"].apply(parse_amount)
    total_all = df["amount_calc"].sum()
    st.info(f"💰 **סה\"כ בארנק:** ₪ {total_all:,.0f} | {len(df)} קופונים")

    # שליטה על Expander
    if "expand_state" not in st.session_state: st.session_state.expand_state = True
    c1, c2 = st.columns(2)
    if c1.button("↔️ הרחב הכל", use_container_width=True): st.session_state.expand_state = True; st.rerun()
    if c2.button("↕️ קבץ הכל", use_container_width=True): st.session_state.expand_state = False; st.rerun()

    networks = sorted(df["network"].unique())
    
    for net in networks:
        net_df = df[df["network"] == net]
        group_sum = net_df["amount_calc"].sum()
        
        with st.expander(f"📦 {net} ({len(net_df)}) | ₪ {group_sum:,.0f}", expanded=st.session_state.expand_state):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745"
                if exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"
                    elif days <= 14: color = "#ffa500"

                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between;">
                        <b>{row['value']}</b>
                        <span style="color:#666; font-size:0.8rem;">תוקף: {row['expiry']}</span>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                </div>
                """, unsafe_allow_html=True)

                # כפתורי פעולה
                b1, b2, b3 = st.columns(3)
                with b1:
                    with st.popover("✏️ עריכה", use_container_width=True):
                        edit_net = st.text_input("רשת", value=row['network'], key=f"n_{i}")
                        edit_val = st.text_input("ערך", value=row['value'], key=f"v_{i}")
                        edit_exp = st.date_input("תוקף", value=exp_dt or date.today(), key=f"d_{i}")
                        edit_link = st.text_input("קוד/לינק", value=row['code_or_link'], key=f"l_{i}")
                        if st.button("עדכן", key=f"upd_{i}"):
                            df.at[i, "network"] = edit_net
                            df.at[i, "value"] = edit_val
                            df.at[i, "expiry"] = edit_exp.strftime("%d/%m/%Y")
                            df.at[i, "code_or_link"] = edit_link
                            conn.update(worksheet="Sheet1", data=df.drop(columns=["amount_calc"]))
                            st.rerun()
                
                with b2:
                    link_text = str(row['code_or_link'])
                    if is_url(link_text):
                        url = link_text if link_text.startswith('http') else f"https://{link_text}"
                        st.link_button("🌐 לינק", url, use_container_width=True)
                    else:
                        st.button("🔗 אין לינק", disabled=True, use_container_width=True)

                with b3:
                    if st.button("🗑️ מחק", key=f"del_{i}", use_container_width=True):
                        df = df.drop(i)
                        conn.update(worksheet="Sheet1", data=df.reset_index(drop=True).drop(columns=["amount_calc"]))
                        st.rerun()
                        
