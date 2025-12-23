import streamlit as st
import pandas as pd
import re
import requests
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection
from streamlit_oauth import OAuth2Component

# ===============================
# 1. הגדרות דף (חייב להיות ראשון)
# ===============================
st.set_page_config(
    page_title="ארנק קופונים חכם", 
    page_icon="🎫", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ===============================
# 2. עיצוב (Light Mode + Mobile Fix)
# ===============================
st.markdown("""
<style>
    /* כפיית מצב מואר */
    [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #000000; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0.95); }
    
    /* כיוון RTL */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: rtl; 
        text-align: right;
    }
    
    .coupon-card {
        padding: 15px; border-radius: 12px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f1f3f5; color: #333; padding: 12px;
        border-radius: 8px; font-family: monospace; font-weight: bold;
        word-break: break-all; margin-top: 10px; border: 1px dashed #ced4da;
    }
    
    .stButton button { width: 100%; }

    /* תיקון למובייל */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            top: 0; height: 100vh; z-index: 999999;
            width: 80% !important; max-width: 300px;
        }
        div[data-testid="stSidebarCollapsedControl"] { display: block; color: #000; }
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. אימות מול גוגל (הלוגיקה המתוקנת)
# ===============================
CLIENT_ID = st.secrets["google_client_id"]
CLIENT_SECRET = st.secrets["google_client_secret"]
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REFRESH_TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_TOKEN_URL = "https://oauth2.googleapis.com/revoke"
REDIRECT_URI = "https://coupon-urtpmar277awmwda4z3vdw.streamlit.app"
SCOPE = "openid email profile"

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

# בדיקה אם אנחנו כבר מחוברים ב-Session
if "user_email" not in st.session_state:
    
    # הצגת כותרת
    st.markdown("<h3 style='text-align:center;'>התחברות לארנק קופונים 🔐</h3>", unsafe_allow_html=True)
    
    # === התיקון: הרכיב חייב לרוץ תמיד כדי לתפוס את הקוד מגוגל ===
    result = oauth2.authorize_button(
        name="התחבר עם Google",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        key="google_auth",
    )
    
    if result:
        try:
            # חילוץ הטוקן
            if "token" in result:
                access_token = result["token"]["access_token"]
            elif "access_token" in result:
                access_token = result["access_token"]
            else:
                st.error("שגיאה: לא התקבל טוקן תקין.")
                st.stop()
            
            # שליפת פרטי משתמש
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = requests.get(user_info_url, headers=headers)
            resp.raise_for_status()
            
            user_data = resp.json()
            st.session_state["user_email"] = user_data.get("email")
            st.session_state["user_name"] = user_data.get("name")
            st.session_state["user_picture"] = user_data.get("picture")
            
            # רענון כדי להכנס למערכת
            st.rerun()
            
        except Exception as e:
            st.error(f"שגיאה בהתחברות: {e}")
            if st.button("נסה שוב"):
                st.rerun()
            st.stop()
            
    # אם לא מחוברים ולא חזרנו עם תוצאה - עוצרים כאן
    st.stop()

# ===============================
# 4. בדיקת הרשאות
# ===============================
ALLOWED_USERS = ["eyalicohen@gmail.com", "rachelcohen144@gmail.com"]

if st.session_state.get("user_email") not in ALLOWED_USERS:
    st.error("⛔ אין לך הרשאה לגשת לאפליקציה זו.")
    if st.button("התנתק"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# ===============================
# 5. חיבור לנתונים
# ===============================
def parse_amount(val):
    try:
        nums = re.findall(r"\d+\.?\d*", str(val))
        return float(nums[0]) if nums else 0.0
    except: return 0.0

def parse_expiry(val):
    if not val or str(val).strip() == "": return None
    try:
        val_str = str(val).split(" ")[0]
        return datetime.strptime(val_str, "%d/%m/%Y").date()
    except ValueError:
        try: return datetime.strptime(val_str, "%Y-%m-%d").date()
        except: return None

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.rename(columns={'notes': 'note', 'status': 'sstatus'})
    required = ["network", "value", "code_or_link", "expiry", "cvv", "note", "sstatus"]
    for col in required:
        if col not in df.columns: df[col] = ""
    df["sstatus"] = df["sstatus"].replace("", "פעיל").fillna("פעיל")
    df = df.fillna("")
except Exception as e:
    st.error(f"שגיאה בטעינת נתונים: {e}")
    st.stop()

def save_to_sheets(target_df):
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)
    st.cache_data.clear()

# ===============================
# 6. תפריט צד
# ===============================
with st.sidebar:
    if "user_picture" in st.session_state:
        st.image(
