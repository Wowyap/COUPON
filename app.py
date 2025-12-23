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
# 2. כפיית מצב מואר (Light Mode) + תיקוני מובייל
# ===============================
st.markdown("""
<style>
    /* === כפיית מצב מואר (Light Mode) === */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    p, h1, h2, h3, div, span, label {
        color: #000000 !important;
    }
    
    /* === הגדרות RTL ועיצוב === */
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
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        width: 100%;
        box-sizing: border-box;
    }
    
    .code-container {
        direction: ltr !important;
        text-align: left !important;
        background: #f1f3f5;
        color: #333 !important;
        padding: 12px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-weight: bold;
        word-break: break-all;
        margin-top: 10px;
        border: 1px dashed #ced4da;
    }
    
    .stButton button { width: 100%; }

    /* === תיקון אגרסיבי למובייל === */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            top: 0; 
            height: 100vh;
            z-index: 999999;
            width: 300px !important; /* רוחב קבוע לתפריט */
            box-shadow: -5px 0 15px rgba(0,0,0,0.2);
        }
        div[data-testid="stSidebarCollapsedControl"] {
            display: block;
            color: #000 !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. הגדרות Google OAuth
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

# בדיקה אם יש טוקן שמור ב-Session או ב-Query Params (לשמירה ברענון)
if "auth_token" not in st.session_state:
    if "code" in st.query_params:
        # אם חזרנו מגוגל, הקוד יטופל בהמשך
        pass
    else:
        st.markdown("<h3 style='text-align:center;'>התחברות לארנק קופונים 🔐</h3>", unsafe_allow_html=True)
        result = oauth2.authorize_button(
            name="התחבר עם Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            key="google_auth",
        )
        
        if result:
            try:
                if "token" in result:
                    access_token = result["token"]["access_token"]
                elif "access_token" in result:
                    access_token = result["access_token"]
                else:
                    st.error("שגיאה בקבלת הטוקן")
                    st.stop()
                
                # שמירת הטוקן
                st.session_state["auth_token"] = access_token
                
                # שליפת פרטים
                user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                resp = requests.get(user_info_url, headers=headers)
                resp.raise_for_status()
                user_data = resp.json()
                
                st.session_state["user_email"] = user_data.get("email")
                st.session_state["user_name"] = user_data.get("name")
                st.session_state["user_picture"] = user_data.get("picture")
                st.rerun()

            except Exception as e:
                st.error(f"תקלה בהתחברות: {e}")
                if st.button("נסה שוב"):
                    st.query_params.clear()
                    st.rerun()
                st.stop()
        st.stop()

# ===============================
# 4. אבטחה והרשאות
# ===============================
ALLOWED_USERS = ["eyalicohen@gmail.com", "rachelcohen144@gmail.com"]

current_email = st.session_state.get("user_email")
if current_email not in ALLOWED_USERS:
    st.error(f"הגישה למשתמש {current_email} אינה מורשית.")
    if st.button("התנתק"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# ===============================
# 5. חיבור לנתונים ופונקציות
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

# טעינת נתונים עם TTL=0 כדי להבטיח רענון
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
    """שמירה וניקוי מטמון כדי להבטיח עדכון מיידי"""
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)
    st.cache_data.clear() # ניקוי זיכרון כדי שהרענון הבא יביא מידע חדש

# ===============================
# 6. תפריט צד (Sidebar)
# ===============================
with st.sidebar:
    if "user_picture" in st.session_state:
        st.image(st.session_state["user_picture"], width=60)
    st.markdown(f"### שלום, {st.session_state.get('user_name')}")
    
    page = st.radio("בחר פעולה:", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])
    
    st.write("---")
    if st.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

# ===============================
# 7. לוגיקת האפליקציה
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        network = col1.text_input("רשת / חנות")
        value = col2.text_input("ערך (לדוגמה: 100)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        cvv = st.text_input("CVV (אופציונלי)")
        link = st.text_input("קוד קופון או קישור")
        note = st.text_area("הערות")
        
        submitted = st.form_submit_button("💾 שמור בארנק")
        if submitted:
            if network and value:
                new_row = pd.DataFrame([{
                    "network": network, 
                    "value": value, 
                    "expiry": expiry_date.strftime("%d/%m/%Y"),
                    "code_or_link": link, 
                    "cvv": cvv, 
                    "note": note, 
                    "sstatus": "פעיל"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheets(df)
                st.toast("✅ הקופון נוסף בהצלחה!", icon="🎉")
                st.rerun()
            else:
                st.warning("⚠️ חובה למלא שם רשת וערך")

else:
    # מצב תצוגה
    is_archive = (page == "📁 ארכיון (נוצלו)")
    target_status = "נוצל" if is_archive else "פעיל"
