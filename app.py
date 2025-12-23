import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection
from streamlit_oauth import OAuth2Component

# ===============================
# 1. הגדרות Google OAuth
# ===============================
CLIENT_ID = st.secrets["google_client_id"]
CLIENT_SECRET = st.secrets["google_client_secret"]
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_TOKEN_URL = "https://oauth2.googleapis.com/revoke"
REDIRECT_URI = "https://coupon-urtpmar277awmwda4z3vdw.streamlit.app"
SCOPE = "openid email profile"

# יצירת רכיב האימות
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

if "auth" not in st.session_state:
    # הצגת כפתור התחברות
    result = oauth2.authorize_button(
        name="התחבר עם Google",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        key="google_auth",
    )
    if result:
        st.session_state["auth"] = result
        st.rerun()
    st.stop()

# שליפת נתוני המשתמש מגוגל
if "user_email" not in st.session_state:
    import requests
    token = st.session_state["auth"]["access_token"]
    resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", 
                        headers={"Authorization": f"Bearer {token}"})
    user_info = resp.json()
    st.session_state["user_email"] = user_info.get("email")
    st.session_state["user_name"] = user_info.get("name")

# אבטחה: רק המייל שלך מורשה
ALLOWED_USERS = ["eyalicohen@gmail.com"] # <--- שנה למייל שלך!
if st.session_state["user_email"] not in ALLOWED_USERS:
    st.error(f"הגישה למשתמש {st.session_state['user_email']} חסומה.")
    if st.button("התנתק"):
        del st.session_state["auth"]
        st.rerun()
    st.stop()

# ===============================
# 2. הגדרות דף ו-CSS (RTL)
# ===============================
st.set_page_config(page_title="ארנק קופונים חכם", page_icon="🎫", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: rtl; text-align: right;
    }
    .coupon-card {
        padding: 15px; border-radius: 12px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); width: 100%; box-sizing: border-box;
    }
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f8f9fa; padding: 10px; border-radius: 6px;
        font-family: monospace; word-break: break-all; margin-top: 10px;
        border: 1px dashed #adb5bd;
    }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. פונקציות עזר וטעינת נתונים
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

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.rename(columns={'notes': 'note', 'status': 'sstatus'})
    for col in ["network", "value", "code_or_link", "expiry", "cvv", "note", "sstatus"]:
        if col not in df.columns: df[col] = ""
    df["sstatus"] = df["sstatus"].replace("", "פעיל").fillna("פעיל")
    df = df.fillna("")
except Exception as e:
    st.error(f"שגיאה בחיבור: {e}")
    st.stop()

def save_to_sheets(target_df):
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)

# ===============================
# 4. ניווט
# ===============================
with st.sidebar:
    st.write(f"שלום, **{st.session_state['user_name']}**")
    page = st.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])
    if st.button("🚪 התנתק"):
        del st.session_state["auth"]
        st.rerun()

# ===============================
# 5. דפי האפליקציה (הוספה/ארנק)
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        network = col1.text_input("רשת / חנות")
        value = col2.text_input("ערך")
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
                st.success("נשמר!")
                st.rerun()
else:
    is_archive = (page == "📁 ארכיון (נוצלו)")
    target_status = "נוצל" if is_archive else "פעיל"
    st.header("🎫 הארנק שלי" if not is_archive else "📁 ארכיון")
    
    if "expand_all" not in st.session_state: st.session_state.expand_all = True
    c1, c2 = st.columns(2)
    if c1.button("↔️ הרחב הכל"): st.session_state.expand_all = True; st.rerun()
    if c2.button("↕️ כווץ הכל"): st.session_state.expand_all = False; st.rerun()

    df["amount_calc"] = df["value"].apply(parse_amount)
    display_df = df[df["sstatus"].str.strip() == target_status].copy()
    st.info(f"💰 **סה\"כ:** ₪ {display_df['amount_calc'].sum():,.0f} | {len(display_df)} קופונים")

    search = st.text_input("🔍 חיפוש מהיר...")
    if search: display_df = display_df[display_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    for net in sorted(display_df["network"].unique()):
        net_df = display_df[display_df["network"] == net]
        with st.expander(f"📦 {net} ({len(net_df)})", expanded=st.session_state.expand_all):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" if target_status == "פעיל" else "#6c757d"
                if target_status == "פעיל" and exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"
                    elif days <= 14: color = "#ffa500"

                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between;">
                        <div style="font-weight:bold;">{row['value']}{f" | CVV: {row['cvv']}" if row['cvv'] else ""}</div>
                        <div style="font-size:0.85rem; color:#666;">תוקף: {row['expiry']}</div>
                    </div>
                    <div class="code-container">{row['code_or_link']}</div>
                    {f"<div style='font-size:0.85rem; color:#555; margin-top:5px;'>📝 {row['note']}</div>" if row['note'] else ""}
                </div>
                """, unsafe_allow_html=True)

                b1, b2, b3 = st.columns([1, 1, 1])
                with b1:
                    if st.button("⏪ החזר" if is_archive else "✅ מומש", key=f"stat_{i}"):
                        df.at[i, "sstatus"] = "פעיל" if is_archive else "נוצל"
                        save_to_sheets(df); st.rerun()
                with b2:
                    with st.popover("✏️"):
                        u_val = st.text_input("ערך", value=row['value'], key=f"u_v_{i}")
                        if st.button("עדכן", key=f"upd_{i}"):
                            df.at[i, "value"] = u_val
                            save_to_sheets(df); st.rerun()
                with b3:
                    if st.button("🗑️", key=f"del_{i}"):
                        df = df.drop(i); save_to_sheets(df); st.rerun()
