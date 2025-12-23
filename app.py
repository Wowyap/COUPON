import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection
from streamlit_google_auth import Authenticate

# ===============================
# 1. אימות משתמש (Google Login)
# ===============================
# מנגנון גמיש למניעת TypeError - שולח גם secret_key וגם cookie_password
auth_kwargs = {
    "client_id": st.secrets["google_client_id"],
    "client_secret": st.secrets["google_client_secret"],
    "redirect_uri": "https://coupon-urtpmar277awmwda4z3vdw.streamlit.app",
    "cookie_name": "coupon_wallet_cookie",
    "cookie_expiry_days": 30,
    # שולחים את שניהם כדי שהספרייה תבחר מה שמתאים לה
    "secret_key": st.secrets["secret_key"],
    "cookie_password": st.secrets["secret_key"] 
}

try:
    # ניסיון ראשון: המבנה החדש ביותר
    authenticator = Authenticate(**auth_kwargs)
except TypeError:
    # ניסיון שני: אם המבנה הקודם נכשל, מנסים בלי הפרמטרים העודפים
    from inspect import signature
    sig = signature(Authenticate.__init__)
    valid_params = [p for p in sig.parameters if p in auth_kwargs]
    filtered_kwargs = {k: auth_kwargs[k] for k in valid_params}
    authenticator = Authenticate(**filtered_kwargs)

# בדיקת מצב התחברות
authenticator.check_authenticator()

if not st.session_state.get('connected'):
    st.markdown("<h2 style='text-align:center; direction:rtl;'>כניסה לארנק קופונים</h2>", unsafe_allow_html=True)
    authenticator.login()
    st.stop()

# אבטחה: רק המייל שלך מורשה
ALLOWED_USERS = ["your-email@gmail.com"] # <--- כאן שים את המייל שלך!
user_info = st.session_state.get('user_info', {})
if user_info.get('email') not in ALLOWED_USERS:
    st.error(f"הגישה למשתמש {user_info.get('email')} חסומה.")
    if st.button("התנתק"):
        authenticator.logout()
    st.stop()

# ===============================
# 2. הגדרות דף ו-CSS
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
# 4. טעינת נתונים
# ===============================
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
# 5. ניווט
# ===============================
with st.sidebar:
    if user_info.get('picture'): st.image(user_info.get('picture'), width=70)
    st.write(f"שלום, **{user_info.get('name')}**")
    page = st.radio("ניווט", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])
    if st.button("🚪 התנתק"):
        authenticator.logout()
        st.rerun()

# ===============================
# 6. דפי האפליקציה
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

    search = st.text_input("🔍 חיפוש...")
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
                    <div style="display
