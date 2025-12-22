import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from streamlit_gsheets import GSheetsConnection

# ===============================
# Page config
# ===============================
st.set_page_config(
    page_title="ארנק קופונים",
    layout="wide"
)

# ===============================
# CSS – RTL + תיקון מובייל
# ===============================
st.markdown("""
<style>
html, body, [class*="st-"] {
    direction: rtl;
    text-align: right;
    font-size: 18px;
}

code, pre, .stCodeBlock, a {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: bidi-override;
    white-space: nowrap !important;
    overflow-x: auto;
}

section[data-testid="stSidebar"] * {
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# Helpers
# ===============================
def parse_amount(val):
    try:
        nums = re.findall(r"\d+", str(val))
        return float(nums[0]) if nums else 0
    except:
        return 0.0

def parse_expiry(val):
    try:
        return datetime.strptime(val, "%d/%m/%Y")
    except:
        return None

def send_mail(subject, body, to_email):
    msg = EmailMessage()
    msg["From"] = st.secrets["EMAIL_USER"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASSWORD"]
        )
        server.send_message(msg)

# ===============================
# Load data
# ===============================
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=0)
df = df.fillna("")

# ===============================
# Sidebar – Navigation & Settings
# ===============================
page = st.sidebar.radio("עבור אל", ["📂 הארנק שלי", "➕ הוספת קופון", "⚙️ הגדרות"])

# ===============================
# Settings
# ===============================
if page == "⚙️ הגדרות":
    st.header("⚙️ הגדרות")

    notify_email = st.text_input(
        "מייל לקבלת התראות",
        value="eyalicohen@gmail.com"
    )

    days_14 = st.checkbox("התראה 14 יום לפני", True)
    days_7 = st.checkbox("התראה 7 ימים לפני", True)
    days_1 = st.checkbox("התראה יום לפני", True)

    if st.button("📧 שלח בדיקת מייל"):
        send_mail(
            "בדיקת מערכת קופונים",
            "המייל מחובר בהצלחה",
            notify_email
        )
        st.success("מייל נשלח")

# ===============================
# Add coupon
# ===============================
elif page == "➕ הוספת קופון":
    st.header("➕ הוספת קופון")

    with st.form("add_coupon"):
        network = st.text_input("רשת")
        value = st.text_input("ערך")
        expiry = st.text_input("תוקף (DD/MM/YYYY)")
        link = st.text_input("קוד / קישור")

        if st.form_submit_button("שמור"):
            new_row = pd.DataFrame([{
                "network": network,
                "value": value,
                "expiry": expiry,
                "code_or_link": link
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df)
            st.success("נשמר")

# ===============================
# Wallet
# ===============================
else:
    st.header("🎫 הארנק שלי")

    # Filters
    search = st.text_input("🔍 חיפוש")
    if search:
        df = df[df.apply(lambda r: search.lower() in r.astype(str).str.lower().to_string(), axis=1)]

    # Total value
    df["amount"] = df["value"].apply(parse_amount)
    st.metric("💰 סך שווי הקופונים", f"₪ {df['amount'].sum():,.0f}")

    # Expiry alerts
    today = datetime.today()
    soon = []
    for i, row in df.iterrows():
        exp = parse_expiry(row["expiry"])
        if not exp:
            continue
        days_left = (exp - today).days
        if (days_left == 14 and days_14) or (days_left == 7 and days_7) or (days_left == 1 and days_1):
            soon.append(row)

    if soon:
        st.warning(f"יש {len(soon)} קופונים עם תוקף קרוב")

    # Multi delete
    selected = st.multiselect(
        "🗑️ מחיקה מרובה",
        options=df.index,
        format_func=lambda i: f"{df.loc[i,'network']} | {df.loc[i,'value']}"
    )

    if st.button("🗑️ מחק נבחרים") and selected:
        df = df.drop(selected)
        conn.update(worksheet="Sheet1", data=df.reset_index(drop=True))
        st.experimental_rerun()

    # Display coupons
    for i, row in df.iterrows():
        exp = parse_expiry(row["expiry"])
        status = ""
        if exp:
            days = (exp - today).days
            if days < 0:
                status = "🔴 פג תוקף"
            elif days <= 7:
                status = "🟠 פג השבוע"
            else:
                status = "🟢 תקף"

        st.markdown(f"""
        **{row['network']}** | ₪ {row['value']} | תוקף: {row['expiry']} {status}
        """)
        st.markdown(
            f"<div style='direction:ltr; overflow-x:auto'>{row['code_or_link']}</div>",
            unsafe_allow_html=True
        )

        if st.button("🗑️ מחק", key=f"del_{i}"):
            df = df.drop(i)
            conn.update(worksheet="Sheet1", data=df.reset_index(drop=True))
            st.experimental_rerun()
