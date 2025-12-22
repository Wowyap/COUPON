import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
import smtplib
from email.message import EmailMessage
from streamlit_gsheets import GSheetsConnection

# ===============================
# Page config
# ===============================
st.set_page_config(page_title="ארנק קופונים חכם", page_icon="🎫", layout="wide")

# ===============================
# CSS – RTL + Mobile Fixes
# ===============================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] { direction: rtl; text-align: right; }
    div[data-testid="stVerticalBlock"] > div { width: 100% !important; }
    .coupon-card {
        padding: 1rem; border-radius: 10px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 5px;
    }
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f1f3f5; padding: 8px; border-radius: 6px;
        font-family: monospace; word-break: break-all; margin: 5px 0;
    }
    /* עיצוב כותרת הקבוצה */
    .stExpander { border: 1px solid #d1d1d1; border-radius: 8px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ===============================
# Helpers
# ===============================
def parse_expiry(val):
    try: return datetime.strptime(val, "%d/%m/%Y").date()
    except: return None

# ===============================
# Load data
# ===============================
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=0)
df = df.fillna("")

# ===============================
# Sidebar
# ===============================
page = st.sidebar.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון", "⚙️ הגדרות"])

# ===============================
# Page: Add/Edit Coupon
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון")
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
                st.success("נשמר!")
                st.rerun()

# ===============================
# Page: Wallet (With Grouping & Edit)
# ===============================
elif page == "📂 הארנק שלי":
    st.header("🎫 הקופונים שלי")
    
    # חיפוש
    search = st.text_input("🔍 חיפוש...")
    if search:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    # שליטה גלובלית על הרחבה/כיווץ
    col_ctrl1, col_ctrl2 = st.columns(2)
    expand_all = col_ctrl1.button("↔️ הרחב הכל", use_container_width=True)
    collapse_all = col_ctrl2.button("↕️ קבץ הכל", use_container_width=True)
    
    # הגדרת מצב פתיחה ראשוני
    if "expand_state" not in st.session_state: st.session_state.expand_state = False
    if expand_all: st.session_state.expand_state = True
    if collapse_all: st.session_state.expand_state = False

    # קיבוץ לפי רשת
    networks = df["network"].unique()
    
    for net in networks:
        net_df = df[df["network"] == net]
        with st.expander(f"📦 {net} ({len(net_df)} קופונים)", expanded=st.session_state.expand_state):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" if exp_dt and (exp_dt - date.today()).days > 14 else "#ffa500"
                
                st.markdown(f"""
                <div class="coupon-card" style="border-right: 5px solid {color};">
                    <div style="display:flex; justify-content:space-between;">
                        <b>{row['value']}</b> <span>תוקף: {row['expiry']}</span>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # כפתורי פעולה בתוך הקבוצה
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"✏️ ערוך", key=f"edit_{i}", use_container_width=True):
                        st.session_state.editing_idx = i
                with c2:
                    if st.button(f"🗑️ מחק", key=f"del_{i}", use_container_width=True):
                        df = df.drop(i)
                        conn.update(worksheet="Sheet1", data=df.reset_index(drop=True))
                        st.rerun()

    # מודאל עריכה (מופיע רק כשלוחצים על עריכה)
    if "editing_idx" in st.session_state:
        idx = st.session_state.editing_idx
        st.divider()
        st.subheader(f"עריכת קופון: {df.loc[idx, 'network']}")
        with st.form("edit_form"):
            new_net = st.text_input("רשת", value=df.loc[idx, "network"])
            new_val = st.text_input("ערך", value=df.loc[idx, "value"])
            curr_exp = parse_expiry(df.loc[idx, "expiry"]) or date.today()
            new_exp = st.date_input("תוקף חדש", value=curr_exp)
            new_link = st.text_input("קוד/קישור", value=df.loc[idx, "code_or_link"])
            
            cb1, cb2 = st.columns(2)
            if cb1.form_submit_button("✅ עדכן שינויים"):
                df.at[idx, "network"] = new_net
                df.at[idx, "value"] = new_val
                df.at[idx, "expiry"] = new_exp.strftime("%d/%m/%Y")
                df.at[idx, "code_or_link"] = new_link
                conn.update(worksheet="Sheet1", data=df)
                del st.session_state.editing_idx
                st.rerun()
            if cb2.form_submit_button("❌ ביטול"):
                del st.session_state.editing_idx
                st.rerun()

# ===============================
# Page: Settings
# ===============================
else:
    st.header("⚙️ הגדרות")
    st.info("כאן תוכל להגדיר התראות מייל (כפי שהוגדר בקוד הקודם)")
    
