import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta
import io
import smtplib
from email.mime.text import MIMEText

# ----------------- הגדרות כלליות -----------------
st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

GLOBAL_FONT_SIZE = "18px"

st.markdown(f"""
<style>
html, body, [class*="st-"] {{
    font-size: {GLOBAL_FONT_SIZE};
    direction: rtl;
    text-align: right;
}}
</style>
""", unsafe_allow_html=True)

# ----------------- פונקציות עזר -----------------
def clean_data(df):
    for col in df.columns:
        df[col] = df[col].astype(str).replace("nan", "")
    return df

def parse_expiry(val):
    if not val:
        return datetime.max
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%m/%Y", "%m/%y"):
        try:
            return datetime.strptime(val, fmt)
        except:
            pass
    return datetime.max

def parse_amount(val):
    try:
        nums = re.findall(r"\d+\.?\d*", str(val))
        return float(nums[0]) if nums else 0.0
    except:
        return 0.0

# ----------------- מייל -----------------
def send_expiry_email(df):
    if not st.session_state.email_enabled:
        return False

    today = datetime.today().date()
    alerts = []

    for _, row in df.iterrows():
        exp = parse_expiry(row["expiry"]).date()
        days_left = (exp - today).days

        if days_left in st.session_state.alert_days:
            alerts.append(
                f"- {row['network']} | {row['value']} | פג בעוד {days_left} ימים ({row['expiry']})"
            )

    if not alerts:
        return False

    body = "התראות תוקף לקופונים:\n\n" + "\n".join(alerts)

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = "⏰ התראת תוקף קופונים"
    msg["From"] = st.secrets["EMAIL_USER"]
    msg["To"] = st.session_state.email_recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASSWORD"]
        )
        server.send_message(msg)

    return True

# ----------------- חיבור ל־Google Sheets -----------------
conn = st.connection("gsheets", type=GSheetsConnection)
df = clean_data(conn.read(worksheet="Sheet1", ttl=0))

# ----------------- Sidebar -----------------
st.sidebar.title("⚙️ ניווט והגדרות")

page = st.sidebar.radio("עבור אל:", ["הארנק שלי", "הוספה ידנית"])

st.sidebar.markdown("### 🔎 חיפוש וסינון")
search_text = st.sidebar.text_input("חיפוש חופשי")
type_filter = st.sidebar.multiselect(
    "סוג קופון",
    options=df["type"].unique(),
    default=list(df["type"].unique())
)

st.sidebar.markdown("### 📧 הגדרות התראות מייל")

st.session_state.email_enabled = st.sidebar.checkbox(
    "הפעל התראות מייל", value=True
)

st.session_state.email_recipient = st.sidebar.text_input(
    "שלח התראות אל:",
    value="eyalicohen@gmail.com"
)

st.session_state.alert_days = st.sidebar.multiselect(
    "שלח התראה לפני:",
    options=[14, 7, 1],
    default=[14, 7, 1],
    format_func=lambda x: f"{x} ימים"
)

# ----------------- עמוד הוספה -----------------
if page == "הוספה ידנית":
    st.header("➕ הוספת קופון")

    with st.form("add_coupon"):
        net = st.text_input("רשת")
        val = st.text_input("ערך")
        typ = st.selectbox("סוג", ["Link", "Code", "Credit Card"])
        exp = st.text_input("תוקף")
        code = st.text_input("קוד / קישור")
        notes = st.text_area("הערות")

        if st.form_submit_button("💾 שמור"):
            new_row = pd.DataFrame([{
                "network": net,
                "value": val,
                "type": typ,
                "expiry": exp,
                "code_or_link": code,
                "notes": notes
            }])
            conn.update(
                worksheet="Sheet1",
                data=pd.concat([df, new_row], ignore_index=True)
            )
            st.success("הקופון נוסף")
            st.rerun()

# ----------------- הארנק -----------------
if page == "הארנק שלי":
    st.title("🎫 My Coupon Wallet")

    df["amount"] = df["value"].apply(parse_amount)
    st.metric("סה״כ שווי הקופונים", f"₪{df['amount'].sum():,.2f}")

    # פילטרים
    filtered_df = df.copy()

    if search_text:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda r: search_text.lower() in r.astype(str).str.lower().to_string(),
                axis=1
            )
        ]

    filtered_df = filtered_df[filtered_df["type"].isin(type_filter)]

    # התראות תוקף
    today = datetime.today()
    soon = (df["expiry"].apply(parse_expiry) <= today + timedelta(days=7)).sum()
    expired = (df["expiry"].apply(parse_expiry) < today).sum()

    st.info(f"🟠 {soon} קופונים פגים השבוע | 🔴 {expired} פגי תוקף")

    # כפתור שליחת מייל
    if st.button("📧 שלח התרעות מייל עכשיו"):
        if send_expiry_email(df):
            st.success("המייל נשלח בהצלחה")
        else:
            st.info("אין קופונים עם תוקף קרוב או שהתראות כבויות")

    # מחיקה מרובה
    st.markdown("### 🗑️ מחיקה מרובה")
    selected = st.multiselect(
        "בחר קופונים למחיקה",
        options=filtered_df.index,
        format_func=lambda i: f"{filtered_df.loc[i,'network']} | {filtered_df.loc[i,'value']}"
    )

    if st.button("🗑️ מחק נבחרים"):
        if selected:
            df = df.drop(selected)
            conn.update(worksheet="Sheet1", data=df.reset_index(drop=True))
            st.success(f"נמחקו {len(selected)} קופונים")
            st.rerun()
        else:
            st.warning("לא נבחרו קופונים")

    # הצגת קופונים
    for i, row in filtered_df.iterrows():
        with st.container(border=True):
            st.write(f"**{row['network']}** | {row['value']} | תוקף: {row['expiry']}")
            st.code(row["code_or_link"])
            if st.button("🗑️ מחק", key=f"del_{i}"):
                df = df.drop(i)
                conn.update(worksheet="Sheet1", data=df.reset_index(drop=True))
                st.rerun()
