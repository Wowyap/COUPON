import streamlit as st
from st_google_auth import Authenticate
import pandas as pd
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# ===============================
# 1. אימות גוגל (Google Login)
# ===============================
authenticator = Authenticate(
    secret_names="google_auth",
    cookie_name="google_auth_cookie",
    key="google_auth_key",
    cookie_expiry_days=30,
)

authenticator.check_authenticator()

if not st.session_state.get('connected'):
    st.set_page_config(page_title="כניסה לארנק", page_icon="🔒")
    st.title("🎫 ארנק הקופונים החכם")
    st.write("אנא התחבר עם חשבון הגוגל שלך כדי להמשיך.")
    authenticator.login()
    st.stop()

# רשימת מורשים - שנה למייל שלך
ALLOWED_USERS = ["eyalicohen@gmail.com"] 
user_info = st.session_state.get('user_info', {})
if user_info.get('email') not in ALLOWED_USERS:
    st.error(f"גישה נדחתה למשתמש {user_info.get('email')}")
    if st.button("התנתק"): authenticator.logout()
    st.stop()

# ===============================
# 2. הגדרות דף ועיצוב RTL
# ===============================
st.set_page_config(page_title="הארנק שלי", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { direction: rtl; text-align: right; }
    .coupon-card {
        padding: 15px; border-radius: 12px; background: white;
        border: 1px solid #e0e0e0; margin-bottom: 10px;
    }
    .code-container { 
        direction: ltr !important; text-align: left; background: #f8f9fa; 
        padding: 8px; border-radius: 5px; font-family: monospace; border: 1px dashed #ccc;
    }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. טעינת נתונים ונירמול עמודות
# ===============================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    
    # ניקוי שמות עמודות (הפיכה לאותיות קטנות והסרת רווחים)
    df.columns = [col.strip().lower() for col in df.columns]
    
    # מיפוי שמות עמודות גמיש (פותר KeyError: 'note')
    mapping = {'notes': 'note', 'status': 'sstatus'}
    df = df.rename(columns=mapping)
    
    # וידוא עמודות חובה
    required_cols = ["network", "value", "code_or_link", "expiry", "cvv", "note", "sstatus"]
    for c in required_cols:
        if c not in df.columns: df[c] = ""
    
    # הגדרת ברירת מחדל לסטטוס (ריק = פעיל)
    df["sstatus"] = df["sstatus"].replace("", "פעיל").fillna("פעיל")
    df = df.fillna("")
except Exception as e:
    st.error(f"שגיאה בטעינת הנתונים: {e}")
    st.stop()

def save_changes(target_df):
    final = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final)

# ===============================
# 4. ניהול מצב "הרחב/כווץ"
# ===============================
if "is_expanded" not in st.session_state:
    st.session_state.is_expanded = True

# ===============================
# 5. תפריט צד
# ===============================
with st.sidebar:
    if user_info.get('picture'):
        st.image(user_info.get('picture'), width=60)
    st.write(f"שלום, {user_info.get('name')}")
    page = st.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])
    st.divider()
    if st.button("התנתק"):
        authenticator.logout()
        st.rerun()

# ===============================
# 6. דף התצוגה (ארנק וארכיון)
# ===============================
if page != "➕ הוספת קופון":
    is_archive = (page == "📁 ארכיון (נוצלו)")
    target_status = "נוצל" if is_archive else "פעיל"
    
    st.header("🎫 הארנק שלי" if not is_archive else "📁 קופונים שנוצלו")
    
    # כפתורי שליטה גלובליים להרחבה וכיווץ
    col_e1, col_e2 = st.columns(2)
    if col_e1.button("↔️ הרחב הכל"): 
        st.session_state.is_expanded = True
        st.rerun()
    if col_e2.button("↕️ כווץ הכל"): 
        st.session_state.is_expanded = False
        st.rerun()

    # חישוב שווי וסינון
    df["amount_calc"] = df["value"].apply(lambda x: float(re.findall(r"\d+", str(x))[0]) if re.findall(r"\d+", str(x)) else 0)
    display_df = df[df["sstatus"].str.strip() == target_status].copy()
    
    st.info(f"💰 **סה\"כ:** ₪ {display_df['amount_calc'].sum():,.0f} | {len(display_df)} קופונים")

    search = st.text_input("🔍 חיפוש קופון...")
    if search:
        display_df = display_df[display_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    # הצגת הקופונים בקבוצות לפי רשת
    for net in sorted(display_df["network"].unique()):
        net_df = display_df[display_df["network"] == net]
        with st.expander(f"📦 {net} ({len(net_df)})", expanded=st.session_state.is_expanded):
            for i, row in net_df.iterrows():
                color = "#28a745" if target_status == "פעיל" else "#6c757d"
                
                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between; font-weight:bold;">
                        <div>{row['value']} {f"| CVV: {row['cvv']}" if row['cvv'] else ""}</div>
                        <div style="font-size:0.8rem; color:gray;">תוקף: {row['expiry']}</div>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                    {f"<div style='font-size:0.8rem; color:#555;'>📝 {row['note']}</div>" if row['note'] else ""}
                </div>
                """, unsafe_allow_html=True)
                
                b1, b2 = st.columns(2)
                if b1.button("✅ מומש" if not is_archive else "⏪ החזר", key=f"b1_{i}"):
                    df.at[i, "sstatus"] = "נוצל" if not is_archive else "פעיל"
                    save_changes(df)
                    st.rerun()
                if b2.button("🗑️ מחק", key=f"b2_{i}"):
                    df = df.drop(i)
                    save_changes(df)
                    st.rerun()
else:
    # דף הוספת קופון
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        f_net = st.text_input("רשת")
        f_val = st.text_input("ערך")
        f_exp = st.date_input("תוקף", min_value=date.today())
        f_code = st.text_input("קוד/קישור")
        f_cvv = st.text_input("CVV")
        f_note = st.text_area("הערות")
        if st.form_submit_button("שמור בארנק"):
            new_row = pd.DataFrame([{
                "network": f_net, "value": f_val, "expiry": f_exp.strftime("%d/%m/%Y"),
                "code_or_link": f_code, "cvv": f_cvv, "note": f_note, "sstatus": "פעיל"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_changes(df)
            st.success("נשמר בהצלחה!")
