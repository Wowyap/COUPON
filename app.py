import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection
from streamlit_google_auth import Authenticate

# ===============================
# אבחון שגיאות Secrets (זמני)
# ===============================
st.write("### בודק הגדרות אבטחה...")

# רשימת המפתחות שאנחנו חייבים
required = ["google_client_id", "google_client_secret", "secret_key"]
found_keys = list(st.secrets.keys())

# בדיקה אם המפתחות נמצאים בתוך gsheets בטעות
in_gsheets = []
if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
    in_gsheets = [k for k in required if k in st.secrets["connections"]["gsheets"]]

missing = [k for k in required if k not in st.secrets]

if missing:
    st.error(f"❌ חסרים מפתחות ב-Secrets: {missing}")
    if in_gsheets:
        st.warning(f"⚠️ המפתחות {in_gsheets} נמצאים בתוך [connections.gsheets]. תעביר אותם לראש הקובץ!")
    st.stop()
else:
    st.success("✅ כל המפתחות נמצאו!")

# ניסיון הפעלת האימות עם שמות המשתנים המעודכנים
try:
    authenticator = Authenticate(
        client_id=st.secrets["google_client_id"],
        client_secret=st.secrets["google_client_secret"],
        redirect_uri="https://coupon-urtpmar277awmwda4z3vdw.streamlit.app",
        cookie_password=st.secrets["secret_key"], # כאן השתנה השם מ-secret_key ל-cookie_password
        cookie_name='coupon_wallet_cookie',
        cookie_expiry_days=30,
    )
except Exception as e:
    st.error(f"שגיאה בהפעלת האימות: {e}")
    st.stop()

# בדיקת מצב התחברות
authenticator.check_authenticator()

if not st.session_state.get('connected'):
    authenticator.login()
    st.stop()

# המשך הקוד המקורי שלך (ALLOWED_USERS וכו')...
