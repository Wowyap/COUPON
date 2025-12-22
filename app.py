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
st.set_page_config(
    page_title="ארנק קופונים חכם",
    page_icon="🎫",
    layout="wide"
)

# ===============================
# CSS – תיקון מובייל ו-RTL מלא
# ===============================
st.markdown("""
<style>
    /* הגדרת כיווניות כללית */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        direction: rtl;
        text-align: right;
    }

    /* מניעת שבירת טקסט אנכית במובייל */
    div[data-testid="stVerticalBlock"] > div {
        width: 100% !important;
    }

    /* עיצוב כרטיסיית קופון */
    .coupon-card {
        padding: 1.2rem;
        border-radius: 12px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .coupon-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .coupon-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #31333F;
    }

    .coupon-value {
        font-size: 1.1rem;
        font-weight: bold;
        color: #ff4b4b;
    }

    /* תיקון לקישורים וקודים (שמאל לימין) */
    .code-container {
        direction: ltr !important;
        text-align: left !important;
        background: #f1f3f5;
        padding: 10px;
        border-radius: 6px;
        font-family: monospace;
        word-break: break-all;
        white-space: normal !important;
        margin: 10px 0;
        border: 1px dashed #ced4da;
    }

    /* התאמות לסרגל הצדי */
    section[data-testid="stSidebar"] {
        direction: rtl;
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
    except:
        return 0.0

def parse_expiry(val):
    try:
        return datetime.strptime(val, "%d/%m/%Y").date()
    except:
        return None

def send_mail(subject, body, to_email):
    try:
        msg = EmailMessage()
        msg["From"] = st.secrets["EMAIL_USER"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASSWORD"])
            server.send_message(msg)
        return True
    except:
        return False

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
# Page: Settings
# ===============================
if page == "⚙️ הגדרות":
    st.header("⚙️ הגדרות")
    notify_email = st.text_input("מייל לקבלת התראות", value="eyalicohen@gmail.com")
    if st.button("📧 שלח בדיקת מייל"):
        if send_mail("בדיקת מערכת קופונים", "המערכת מחוברת בהצלחה!", notify_email):
            st.success("מייל נשלח!")
        else:
            st.error("שגיאה בשליחת המייל. בדוק את ה-Secrets.")

# ===============================
# Page: Add Coupon
# ===============================
elif page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון")
    with st.form("add_coupon", clear_on_submit=True):
        network = st.text_input("רשת / חנות")
        value = st.text_input("ערך (לדוגמה: 100 שח)")
        expiry_date = st.date_input("תוקף", min_value=date.today())
        link = st.text_input("קוד או קישור (יוצג משמאל לימין)")
        
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
                st.success("הקופון נשמר!")
                st.rerun()

# ===============================
# Page: Wallet
# ===============================
else:
    st.header("🎫 הארנק שלי")

    # חיפוש וסינון
    search = st.text_input("🔍 חיפוש קופון...")
    if search:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    # שווי כולל
    df["amount_calc"] = df["value"].apply(parse_amount)
    st.metric("💰 שווי כולל", f"₪ {df['amount_calc'].sum():,.0f}")

    # הצגת הקופונים
    today = date.today()
    
    for i, row in df.iterrows():
        exp_dt = parse_expiry(row["expiry"])
        color = "#808080"
        status_text = "⚪ ללא תוקף"
        
        if exp_dt:
            days_left = (exp_dt - today).days
            if days_left < 0:
                color = "#ff4b4b"
                status_text = "🔴 פג תוקף"
            elif days_left <= 14:
                color = "#ffa500"
                status_text = f"🟠 יפוג בעוד {days_left} ימים"
            else:
                color = "#28a745"
                status_text = "🟢 בתוקף"

        # כרטיסיית קופון מעוצבת
        st.markdown(f"""
        <div class="coupon-card" style="border-right: 6px solid {color};">
            <div class="coupon-header">
                <span class="coupon-title">{row['network']}</span>
                <span class="coupon-value">{row['value']}</span>
            </div>
            <div style="font-size: 0.9rem; color: #666;">
                {status_text} | תוקף: {row['expiry']}
            </div>
            <div class="code-container">
                {row['code_or_link']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # כפתור מחיקה רחב ונוח למובייל
        if st.button(f"🗑️ מחק {row['network']}", key=f"del_{i}", use_container_width=True):
            df = df.drop(i)
            conn.update(worksheet="Sheet1", data=df.reset_index(drop=True))
            st.rerun()
        st.write("") # רווח קטן בין הקופונים
