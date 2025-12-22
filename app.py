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
# CSS – תיקון מקיף למובייל ו-RTL
# ===============================
st.markdown("""
<style>
    /* כיווניות כללית */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    
    /* מניעת קריסת טקסט לטור אנכי - פתרון אגרסיבי */
    div[data-testid="stVerticalBlock"] > div {
        width: 100% !important;
        flex: unset !important;
        max-width: 100% !important;
    }
    
    /* הבטחת שבירת שורות תקינה */
    p, h1, h2, h3, div, span {
        white-space: normal !important;
        overflow-wrap: break-word;
    }

    /* עיצוב הכרטיסייה */
    .coupon-card {
        padding: 15px;
        border-radius: 12px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        width: 100%;
        box-sizing: border-box; /* חשוב למובייל */
    }
    
    /* עיצוב קונטיינר הקוד/קישור */
    .code-container {
        direction: ltr !important;
        text-align: left !important;
        background: #f8f9fa;
        padding: 10px;
        border-radius: 6px;
        font-family: monospace;
        word-break: break-all; /* שובר קישורים ארוכים */
        margin-top: 10px;
        margin-bottom: 10px;
        border: 1px dashed #adb5bd;
    }

    /* התאמת כפתורים במובייל */
    .stButton button {
        width: 100%;
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
    try:
        # המרה לסטרינג למקרה שהתא ב-Excel הוא תאריך או מספר
        val_str = str(val).split(" ")[0] 
        return datetime.strptime(val_str, "%d/%m/%Y").date()
    except:
        return None

def is_url(string):
    # תיקון ה-AttributeError: המרה בטוחה ל-String
    try:
        s = str(string).lower().strip()
        return s.startswith(('http://', 'https://', 'www.'))
    except:
        return False

# ===============================
# Load data
# ===============================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df = df.fillna("")
except Exception as e:
    st.error(f"שגיאה בחיבור לגוגל שיטס: {e}")
    df = pd.DataFrame(columns=["network", "value", "expiry", "code_or_link"])

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
        value = st.text_input("ערך (לדוגמה: 100)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        link = st.text_input("קוד או קישור")
        
        if st.form_submit_button("שמור בארנק"):
            if network and value:
                new_row = pd.DataFrame([{
                    "network": network,
                    "value": value,
                    "expiry": expiry_date.strftime("%d/%m/%Y"),
                    "code_or_link": link
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=df)
                st.success("הקופון נשמר בהצלחה!")
                st.rerun()
            else:
                st.warning("חובה למלא שם רשת וערך")

# ===============================
# Page: Wallet
# ===============================
else:
    st.header("🎫 הארנק שלי")
    
    # חישוב שווי
    df["amount_calc"] = df["value"].apply(parse_amount)
    total_all = df["amount_calc"].sum()
    st.info(f"💰 **סה\"כ בארנק:** ₪ {total_all:,.0f} | {len(df)} קופונים")

    # חיפוש
    search = st.text_input("🔍 חיפוש קופון...")
    if search:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    # כפתורי שליטה
    c1, c2 = st.columns(2)
    if "expand_state" not in st.session_state: st.session_state.expand_state = False
    
    if c1.button("↔️ הרחב הכל", use_container_width=True):
        st.session_state.expand_state = True
        st.rerun()
    if c2.button("↕️ קבץ הכל", use_container_width=True):
        st.session_state.expand_state = False
        st.rerun()

    # לוגיקת תצוגה
    networks = sorted(df["network"].unique())
    
    for net in networks:
        net_df = df[df["network"] == net]
        group_sum = net_df["amount_calc"].sum()
        
        with st.expander(f"📦 {net} ({len(net_df)}) | ₪ {group_sum:,.0f}", expanded=st.session_state.expand_state):
            for i, row in net_df.iterrows():
                # בדיקת תוקף
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" # ירוק
                exp_text = row["expiry"]
                
                if exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: 
                        color = "#ff4b4b" # אדום
                    elif days <= 14: 
                        color = "#ffa500" # כתום

                # כרטיסייה
                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="font-weight:bold; font-size:1.1rem;">{row['value']}</div>
                        <div style="color:#666; font-size:0.9rem;">תוקף: {exp_text}</div>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                </div>
                """, unsafe_allow_html=True)

                # כפתורים - תיקון ה-Duplicate ID
                b1, b2, b3 = st.columns([1, 1, 1])
                
                # כפתור עריכה
                with b1:
                    with st.popover("✏️", use_container_width=True):
                        st.write(f"עריכה: {row['network']}")
                        e_net = st.text_input("רשת", value=row['network'], key=f"e_n_{i}")
                        e_val = st.text_input("ערך", value=row['value'], key=f"e_v_{i}")
                        
                        # טיפול בתאריך לעריכה
                        default_date = exp_dt if exp_dt else date.today()
                        e_exp = st.date_input("תוקף", value=default_date, key=f"e_d_{i}")
                        
                        e_link = st.text_input("קוד/לינק", value=row['code_or_link'], key=f"e_l_{i}")
                        
                        if st.button("שמור", key=f"save_{i}"):
                            df.at[i, "network"] = e_net
                            df.at[i, "value"] = e_val
                            df.at[i, "expiry"] = e_exp.strftime("%d/%m/%Y")
                            df.at[i, "code_or_link"] = e_link
                            # מחיקת עמודת עזר לפני שמירה
                            save_df = df.drop(columns=["amount_calc"], errors="ignore")
                            conn.update(worksheet="Sheet1", data=save_df)
                            st.success("עודכן")
                            st.rerun()

                # כפתור קישור - כאן היה הבאג
                with b2:
                    link_val = str(row['code_or_link'])
                    if is_url(link_val):
                        final_url = link_val if link_val.startswith('http') else f"https://{link_val}"
                        st.link_button("🌐", final_url, use_container_width=True)
                    else:
                        # הוספתי key ייחודי גם לכפתור המבוטל!
                        st.button("🔗", disabled=True, key=f"no_link_{i}", use_container_width=True)

                # כפתור מחיקה
                with b3:
                    if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                        df = df.drop(i)
                        save_df = df.drop(columns=["amount_calc"], errors="ignore")
                        conn.update(worksheet="Sheet1", data=save_df.reset_index(drop=True))
                        st.rerun()
        
