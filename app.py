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
    page_title="ארנק קופונים", 
    page_icon="🎫", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===============================
# 2. עיצוב CSS (ניווט עליון + התאמה למובייל)
# ===============================
st.markdown("""
<style>
    /* === עיצוב כללי === */
    [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #000000; }
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0.95); }
    
    /* === יישור לימין (RTL) === */
    .stMarkdown, .stButton, .stTextInput, .stDateInput, .stSelectbox, .stTextArea {
        direction: rtl; 
        text-align: right;
    }
    
    /* הסתרת התפריט הצדדי לחלוטין - אנחנו עוברים לניווט עליון */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }
    
    /* === עיצוב סרגל הניווט העליון === */
    .stRadio > div {
        display: flex;
        justify-content: center;
        width: 100%;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        direction: rtl;
    }
    
    /* עיצוב כפתורי הרדיו שיראו כמו כרטיסיות */
    div[role="radiogroup"] > label {
        background-color: white;
        padding: 8px 16px;
        border-radius: 20px;
        border: 1px solid #ddd;
        margin: 0 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s;
        flex: 1; /* פורס את הכפתורים לרוחב מלא */
        text-align: center;
        justify-content: center;
    }
    
    /* מצב נבחר */
    div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #e3f2fd !important;
        border-color: #2196f3 !important;
        color: #0d47a1 !important;
        font-weight: bold;
    }

    /* === עיצוב כרטיס קופון === */
    .coupon-card {
        padding: 15px; border-radius: 12px; background-color: #ffffff;
        border: 1px solid #e0e0e0; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        direction: rtl;
    }
    
    .code-container {
        direction: ltr !important; text-align: left !important;
        background: #f1f3f5; color: #333; padding: 12px;
        border-radius: 8px; font-family: monospace; font-weight: bold;
        word-break: break-all; margin-top: 10px; border: 1px dashed #ced4da;
    }
    
    .stButton button { width: 100%; }
    
    /* הסתרת כפתור "מסך מלא" */
    [data-testid="stToolbar"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. אימות משתמש + מנגנון זיכרון (Persistence)
# ===============================
CLIENT_ID = st.secrets["google_client_id"]
CLIENT_SECRET = st.secrets["google_client_secret"]
REDIRECT_URI = "https://coupon-urtpmar277awmwda4z3vdw.streamlit.app"

oauth2 = OAuth2Component(
    CLIENT_ID, CLIENT_SECRET, 
    "https://accounts.google.com/o/oauth2/v2/auth", 
    "https://oauth2.googleapis.com/token", 
    "https://oauth2.googleapis.com/token", 
    "https://oauth2.googleapis.com/revoke"
)

# פונקציה לבדיקת טוקן שנשמר ב-URL (כדי לא להתנתק ברענון)
def check_cached_login():
    if "auth_token" in st.query_params:
        token = st.query_params["auth_token"]
        try:
            # בדיקה שהטוקן עדיין חי מול גוגל
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(user_info_url, headers=headers)
            
            if resp.status_code == 200:
                user_data = resp.json()
                st.session_state["user_email"] = user_data.get("email")
                st.session_state["user_name"] = user_data.get("name")
                st.session_state["user_picture"] = user_data.get("picture")
                return True
        except:
            pass
    return False

# לוגיקת כניסה ראשית
if "user_email" not in st.session_state:
    # שלב 1: האם יש לנו טוקן שמור מהרענון הקודם?
    if check_cached_login():
        st.success("חוברת מחדש בהצלחה!")
    else:
        # שלב 2: אם לא, מציגים כפתור התחברות
        st.markdown("<br><h3 style='text-align:center;'>🔐 כניסה לארנק</h3>", unsafe_allow_html=True)
        result = oauth2.authorize_button(
            name="התחבר עם Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
            key="google_auth",
        )
        
        if result:
            try:
                if "token" in result: token = result["token"]["access_token"]
                elif "access_token" in result: token = result["access_token"]
                else: st.error("שגיאה בטוקן"); st.stop()
                
                # שמירת הטוקן ב-URL לעתיד (לרענון הבא)
                st.query_params["auth_token"] = token
                st.rerun() # רענון כדי להפעיל את check_cached_login
                
            except Exception as e:
                st.error("תקלה בהתחברות, נסה שוב.")
                st.stop()
        st.stop()

# ===============================
# 4. בדיקת הרשאות
# ===============================
ALLOWED_USERS = ["eyalicohen@gmail.com", "rachelcohen144@gmail.com"]

if st.session_state.get("user_email") not in ALLOWED_USERS:
    st.error("⛔ אין גישה.")
    if st.button("יציאה"):
        st.query_params.clear()
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
    st.error(f"תקלת תקשורת: {e}")
    st.stop()

def save_to_sheets(target_df):
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)
    st.cache_data.clear()

# ===============================
# 6. ניווט עליון (במקום Sidebar)
# ===============================
# כותרת עם תמונה ושם
col_h1, col_h2, col_h3 = st.columns([1, 4, 1])
with col_h1:
    if "user_picture" in st.session_state:
        st.image(st.session_state["user_picture"], width=45)
with col_h2:
    st.markdown(f"**שלום, {st.session_state.get('user_name').split()[0]}**")
with col_h3:
    if st.button("🚪", help="התנתק"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

# תפריט ניווט ראשי (רדיו אופקי)
selected_page = st.radio(
    "ניווט", 
    ["📂 הארנק שלי", "➕ הוספה", "📁 ארכיון"], 
    horizontal=True,
    label_visibility="collapsed"
)

st.write("---")

# ===============================
# 7. תוכן הדפים
# ===============================

if selected_page == "➕ הוספה":
    st.header("הוספת קופון חדש")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        network = col1.text_input("שם הרשת / חנות")
        value = col2.text_input("ערך (לדוגמה: 200)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        cvv = st.text_input("CVV (אם יש)")
        link = st.text_input("קוד קופון או קישור")
        note = st.text_area("הערות")
        
        if st.form_submit_button("💾 שמור קופון"):
            if network and value:
                new_row = pd.DataFrame([{
                    "network": network, "value": value, 
                    "expiry": expiry_date.strftime("%d/%m/%Y"),
                    "code_or_link": link, "cvv": cvv, "note": note, "sstatus": "פעיל"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheets(df)
                st.toast("הקופון נשמר!", icon="✅")
                st.rerun()
            else:
                st.warning("נא למלא שם רשת וערך")

else:
    # תצוגת הארנק או הארכיון
    is_archive = (selected_page == "📁 ארכיון")
    target_status = "נוצל" if is_archive else "פעיל"
    
    # פילטרים וכפתורים
    c1, c2 = st.columns([3, 1])
    search = c1.text_input("🔍 חיפוש...", placeholder="רשת, סכום...")
    if "expand_all" not in st.session_state: st.session_state.expand_all = False
    
    if c2.button("📂 פתח הכל" if not st.session_state.expand_all else "📁 סגור הכל"):
        st.session_state.expand_all = not st.session_state.expand_all
        st.rerun()

    # עיבוד נתונים
    df["amount_calc"] = df["value"].apply(parse_amount)
    display_df = df[df["sstatus"].str.strip() == target_status].copy()
    
    if search: 
        display_df = display_df[display_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    # סיכום כללי
    total_val = display_df['amount_calc'].sum()
    st.info(f"💰 **סה\"כ:** ₪ {total_val:,.0f} | **כמות:** {len(display_df)}")

    networks = sorted(display_df["network"].unique())
    if not networks: st.warning("לא נמצאו קופונים.")

    for net in networks:
        net_df = display_df[display_df["network"] == net]
        group_total = net_df['amount_calc'].sum()
        
        # כותרת קבוצה משודרגת
        header_text = f"📦 {net} ({len(net_df)}) | ₪ {group_total:,.0f}"
        
        # האם לפתוח את הקבוצה?
        is_open = st.session_state.expand_all or (search != "")
        
        with st.expander(header_text, expanded=is_open):
            for i, row in net_df.iterrows():
                # לוגיקת צבעים
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745" # ירוק
                txt_exp = row['expiry']
                
                if target_status == "פעיל" and exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"; txt_exp += " (פג!)"
                    elif days <= 14: color = "#ffa500"

                cvv_txt = f" | 🔒 {row['cvv']}" if row['cvv'] else ""
                note_html = f"<div style='margin-top:5px; color:#666; font-size:0.9em; border-top:1px solid #eee; padding-top:4px;'>📝 {row['note']}</div>" if row['note'] else ""
                
                # כרטיס הקופון
                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between; font-weight:bold; align-items:center;">
                        <span style="font-size:1.1em;">💎 {row['value']} {cvv_txt}</span>
                        <span style="font-size:0.85em; background:#f1f3f5; padding:3px 8px; border-radius:10px;">📅 {txt_exp}</span>
                    </div>
                    <div class="code-container" onclick="navigator.clipboard.writeText('{row['code_or_link']}'); alert('הועתק!')">{row['code_or_link']}</div>
                    {note_html}
                </div>
                """, unsafe_allow_html=True)

                # כפתורי פעולה
                b1, b2, b3 = st.columns([1.2, 1, 0.8])
                
                label = "⏪ החזר" if is_archive else "✅ מומש"
                if b1.button(label, key=f"s{i}"):
                    df.at[i, "sstatus"] = "פעיל" if is_archive else "נוצל"
                    save_to_sheets(df); st.toast("סטטוס עודכן"); st.rerun()
                
                with b2.popover("✏️ ערוך"):
                    uv = st.text_input("סכום מעודכן", row['value'], key=f"e{i}")
                    if st.button("שמור", key=f"bu{i}"):
                        df.at[i, "value"] = uv; save_to_sheets(df); st.rerun()
                
                if b3.button("🗑️", key=f"d{i}"):
                    df = df.drop(i); save_to_sheets(df); st.toast("נמחק"); st.rerun()
