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
# 2. עיצוב CSS (מתוקן למובייל - ללא חסימות)
# ===============================
st.markdown("""
<style>
    /* === כפיית מצב מואר === */
    [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #000000; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0.95); }
    
    /* === יישור לימין (RTL) לתוכן בלבד === */
    .stMarkdown, .stButton, .stTextInput, .stDateInput, .stSelectbox, .stTextArea, [data-testid="stSidebar"] {
        direction: rtl; 
        text-align: right;
    }
    
    /* יישור כותרות */
    h1, h2, h3, p, div {
        text-align: right;
    }

    /* עיצוב כרטיס קופון */
    .coupon-card {
        padding: 15px; border-radius: 12px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        direction: rtl;
    }
    
    /* קוד הקופון - תמיד משמאל לימין */
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f1f3f5; color: #333; padding: 12px;
        border-radius: 8px; font-family: monospace; font-weight: bold;
        word-break: break-all; margin-top: 10px; border: 1px dashed #ced4da;
    }
    
    .stButton button { width: 100%; }

    /* הסתרת כפתור "מסך מלא" שמפריע בנייד */
    [data-testid="stToolbar"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. אימות מול גוגל
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

if "user_email" not in st.session_state:
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
                st.error("שגיאה: לא התקבל טוקן תקין.")
                st.stop()
            
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
            st.error(f"שגיאה בהתחברות: {e}")
            if st.button("נסה שוב"):
                st.rerun()
            st.stop()
            
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
        st.image(st.session_state["user_picture"], width=60)
    
    st.markdown(f"### {st.session_state.get('user_name')}")
    
    page = st.radio("תפריט:", ["📂 הארנק שלי", "➕ הוספת קופון", "📁 ארכיון (נוצלו)"])
    
    st.write("---")
    if st.button("🚪 התנתק"):
        st.session_state.clear()
        st.rerun()

# ===============================
# 7. לוגיקה ותצוגה
# ===============================
if page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        network = col1.text_input("רשת / חנות")
        value = col2.text_input("ערך (לדוגמה: 100)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        cvv = st.text_input("CVV")
        link = st.text_input("קוד / לינק")
        note = st.text_area("הערות")
        
        if st.form_submit_button("💾 שמור"):
            if network and value:
                new_row = pd.DataFrame([{
                    "network": network, "value": value, 
                    "expiry": expiry_date.strftime("%d/%m/%Y"),
                    "code_or_link": link, "cvv": cvv, "note": note, "sstatus": "פעיל"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheets(df)
                st.toast("נשמר בהצלחה!", icon="✅")
                st.rerun()
            else:
                st.warning("חובה למלא רשת וערך")

else:
    is_archive = (page == "📁 ארכיון (נוצלו)")
    target_status = "נוצל" if is_archive else "פעיל"
    st.header("🎫 הארנק שלי" if not is_archive else "📁 ארכיון")
    
    # כפתורי שליטה (ברירת מחדל: מכווץ)
    c1, c2 = st.columns(2)
    if "expand_all" not in st.session_state: st.session_state.expand_all = False
    if c1.button("📂 הרחב הכל"): st.session_state.expand_all = True; st.rerun()
    if c2.button("📁 כווץ הכל"): st.session_state.expand_all = False; st.rerun()

    df["amount_calc"] = df["value"].apply(parse_amount)
    display_df = df[df["sstatus"].str.strip() == target_status].copy()
    
    st.info(f"💰 **סה\"כ:** ₪ {display_df['amount_calc'].sum():,.0f} ({len(display_df)} קופונים)")

    search = st.text_input("🔍 חיפוש...")
    if search: display_df = display_df[display_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    networks = sorted(display_df["network"].unique())
    if not networks: st.info("אין נתונים להצגה.")

    for net in networks:
        net_df = display_df[display_df["network"] == net]
        
        # === חישוב הסכום הכולל לקבוצה הנוכחית ===
        group_total = net_df['amount_calc'].sum()
        
        # נפתח רק אם ביקשנו הרחבה או שיש חיפוש
        opened = st.session_state.expand_all or (search != "")
        
        # כותרת שכוללת גם את שם הרשת, כמות הקופונים והסכום הכולל
        expander_title = f"📦 {net} ({len(net_df)}) | ₪ {group_total:,.0f}"
        
        with st.expander(expander_title, expanded=opened):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745"
                txt_exp = row['expiry']
                
                if target_status == "פעיל" and exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"; txt_exp += " (פג!)"
                    elif days <= 14: color = "#ffa500"

                cvv_txt = f" | 🔒 {row['cvv']}" if row['cvv'] else ""
                note_html = f"<div style='margin-top:5px; color:#666; font-size:0.9em;'>📝 {row['note']}</div>" if row['note'] else ""
                
                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between; font-weight:bold;">
                        <span>💎 {row['value']} {cvv_txt}</span>
                        <span style="font-size:0.85em; background:#f1f3f5; padding:2px 5px; border-radius:4px;">📅 {txt_exp}</span>
                    </div>
                    <div class="code-container" onclick="navigator.clipboard.writeText('{row['code_or_link']}'); alert('הועתק!')">{row['code_or_link']}</div>
                    {note_html}
                </div>
                """, unsafe_allow_html=True)

                b1, b2, b3 = st.columns([1,1,1])
                lbl = "⏪ החזר" if is_archive else "✅ מומש"
                if b1.button(lbl, key=f"s{i}"):
                    df.at[i, "sstatus"] = "פעיל" if is_archive else "נוצל"
                    save_to_sheets(df); st.toast("סטטוס עודכן"); st.rerun()
                
                with b2.popover("✏️"):
                    uv = st.text_input("ערך", row['value'], key=f"e{i}")
                    if st.button("שמור", key=f"bu{i}"):
                        df.at[i, "value"] = uv; save_to_sheets(df); st.rerun()
                
                if b3.button("🗑️", key=f"d{i}"):
                    df = df.drop(i); save_to_sheets(df); st.toast("נמחק"); st.rerun()
