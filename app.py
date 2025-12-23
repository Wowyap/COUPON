import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection
from streamlit_google_auth import Authenticate

# ===============================
# 1. אימות משתמש (Google Login)
# ===============================
# ניסיון טעינת המפתחות מה-Secrets עם הגנה מפני קריסה
try:
    authenticator = Authenticate(
        secret_key=st.secrets.get("secret_key"),
        cookie_name='coupon_wallet_cookie',
        cookie_expiry_days=30,
        client_id=st.secrets.get("google_client_id"),
        client_secret=st.secrets.get("google_client_secret"),
        redirect_uri="https://coupon-urtpmar277awmwda4z3vdw.streamlit.app",
    )
except Exception as e:
    st.error("שגיאה קריטית: המפתחות ב-Secrets לא מוגדרים נכון או חסרים.")
    st.stop()

# בדיקת מצב התחברות (קוקיז)
authenticator.check_authenticator()

# הצגת מסך התחברות אם המשתמש לא מחובר
if not st.session_state.get('connected'):
    st.markdown("<h2 style='text-align:center; direction:rtl;'>מערכת ארנק קופונים - נא להתחבר</h2>", unsafe_allow_html=True)
    authenticator.login()
    st.stop()

# אבטחה: וידוא שהמייל המחובר מורשה לגשת
ALLOWED_USERS = ["eyalicohen@gmail.com"]  # <--- שנה למייל שלך כאן!
user_info = st.session_state.get('user_info', {})

if user_info.get('email') not in ALLOWED_USERS:
    st.error(f"למשתמש {user_info.get('email')} אין הרשאת גישה.")
    if st.button("התנתק"):
        authenticator.logout()
    st.stop()

# ===============================
# 2. הגדרות דף ו-CSS (RTL)
# ===============================
st.set_page_config(page_title="ארנק קופונים חכם", page_icon="🎫", layout="wide")

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
# 3. פונקציות עזר (Helpers)
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

# ===============================
# 4. טעינת נתונים מ-Google Sheets
# ===============================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    
    # נירמול עמודות
    df.columns = [col.strip().lower() for col in df.columns]
    column_mapping = {'notes': 'note', 'status': 'sstatus'}
    df = df.rename(columns=column_mapping)
    
    # הבטחת עמודות חובה
    required = ["network", "value", "code_or_link", "expiry", "cvv", "note", "sstatus"]
    for col in required:
        if col not in df.columns: df[col] = ""
            
    df["sstatus"] = df["sstatus"].replace("", "פעיל").fillna("פעיל")
    df = df.fillna("")
            
except Exception as e:
    st.error(f"שגיאה בחיבור ל-Google Sheets: {e}")
    st.stop()

def save_to_sheets(target_df):
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)

# ===============================
# 5. תפריט צד (Sidebar)
# ===============================
with st.sidebar:
    if user_info.get('picture'):
        st.image(user_info.get('picture'), width=70)
    st.write(f"שלום, **{user_info.get('name')}**")
    
    page = st.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])
    
    st.write("---")
    if st.button("🚪 התנתק"):
        authenticator.logout()
        st.rerun()

# ===============================
# 6. דף: הוספת קופון
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        network = col1.text_input("רשת / חנות")
        value = col2.text_input("ערך (לדוגמה: 100)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        cvv = st.text_input("CVV")
        link = st.text_input("קוד או קישור")
        note = st.text_area("הערות")
        
        if st.form_submit_button("שמור בארנק"):
            if network and value:
                new_row = pd.DataFrame([{"network": network, "value": value, "expiry": expiry_date.strftime("%d/%m/%Y"),
                                         "code_or_link": link, "cvv": cvv, "note": note, "sstatus": "פעיל"}])
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheets(df)
                st.success("הקופון נשמר בהצלחה!")
                st.rerun()

# ===============================
# 7. דף: ארנק וארכיון
# ===============================
else:
    is_archive = (page == "📁 ארכיון (נוצלו)")
    target_status = "נוצל" if is_archive else "פעיל"
    
    st.header("🎫 הארנק שלי" if not is_archive else "📁 ארכיון קופונים")
    
    # מצב תצוגה
    if "expand_all" not in st.session_state:
        st.session_state.expand_all = True

    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("↔️ הרחב הכל"):
        st.session_state.expand_all = True
        st.rerun()
    if col_btn2.button("↕️ כווץ הכל"):
        st.session_state.expand_all = False
        st.rerun()

    # עיבוד נתונים לתצוגה
    df["amount_calc"] = df["value"].apply(parse_amount)
    display_df = df[df["sstatus"].str.strip() == target_status].copy()
    
    st.info(f"💰 **סה\"כ:** ₪ {display_df['amount_calc'].sum():,.0f} | {len(display_df)} קופונים")

    search = st.text_input("🔍 חיפוש לפי שם רשת...")
    if search:
        display_df = display_df[display_df['network'].str.contains(search, case=False, na=False)]

    networks = sorted(display_df["network"].unique())
    
    for net in networks:
        net_df = display_df[display_df["network"] == net]
        with st.expander(f"📦 {net} ({len(net_df)})", expanded=st.session_state.expand_all):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" if target_status == "פעיל" else "#6c757d"
                
                # התראה על תוקף
                if target_status == "פעיל" and exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b" # פג תוקף
                    elif days <= 14: color = "#ffa500" # עומד לפוג

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

                # כפתורי פעולה
                b1, b2, b3 = st.columns([1, 1, 1])
                with b1:
                    btn_label = "⏪ החזר" if is_archive else "✅ מומש"
                    if st.button(btn_label, key=f"stat_{i}"):
                        df.at[i, "sstatus"] = "פעיל" if is_archive else "נוצל"
                        save_to_sheets(df)
                        st.rerun()
                with b2:
                    with st.popover("✏️"):
                        u_val = st.text_input("עדכן ערך", value=row['value'], key=f"u_v_{i}")
                        if st.button("אישור", key=f"upd_{i}"):
                            df.at[i, "value"] = u_val
                            save_to_sheets(df)
                            st.rerun()
                with b3:
                    if st.button("🗑️", key=f"del_{i}"):
                        df = df.drop(i)
                        save_to_sheets(df)
                        st.rerun()
