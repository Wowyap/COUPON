
import streamlit as st
import pandas as pd
import re
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection
from streamlit_oauth import OAuth2Component

# ===============================
# 1. הגדרות דף
# ===============================
st.set_page_config(page_title="ארנק קופונים חכם", page_icon="🎫", layout="wide", initial_sidebar_state="collapsed")

# ===============================
# 2. עיצוב CSS (RTL + Light Mode)
# ===============================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #ffffff; color: #000000; }
    .stMarkdown, .stButton, .stTextInput, .stDateInput, .stSelectbox, .stTextArea { direction: rtl; text-align: right; }
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
    .stRadio > div { display: flex; justify-content: center; background-color: #f8f9fa; padding: 10px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e0e0e0; }
    div[role="radiogroup"] > label { background-color: white; padding: 8px 16px; border-radius: 20px; border: 1px solid #ddd; margin: 0 5px; flex: 1; text-align: center; }
    div[role="radiogroup"] > label[data-checked="true"] { background-color: #e3f2fd !important; border-color: #2196f3 !important; color: #0d47a1 !important; font-weight: bold; }
    .coupon-card { padding: 15px; border-radius: 12px; background-color: #ffffff; border: 1px solid #e0e0e0; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); direction: rtl; }
    .code-container { direction: ltr !important; text-align: left !important; background: #f1f3f5; color: #333; padding: 12px; border-radius: 8px; font-family: monospace; font-weight: bold; border: 1px dashed #ced4da; }
</style>
""", unsafe_allow_html=True)

# ===============================
# 3. אימות גוגל (Login)
# ===============================
CLIENT_ID = st.secrets["google_client_id"]
CLIENT_SECRET = st.secrets["google_client_secret"]
REDIRECT_URI = "https://coupon-urtpmar277awmwda4z3vdw.streamlit.app"

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/revoke")

if "user_email" not in st.session_state:
    if "auth_token" in st.query_params:
        token = st.query_params["auth_token"]
        try:
            resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                user_data = resp.json()
                st.session_state.update({"user_email": user_data["email"], "user_name": user_data["name"], "user_picture": user_data["picture"]})
            else: st.query_params.clear()
        except: pass

if "user_email" not in st.session_state:
    st.markdown("<br><h3 style='text-align:center;'>🔐 כניסה לארנק</h3>", unsafe_allow_html=True)
    result = oauth2.authorize_button("התחבר עם Google", icon="https://www.google.com/favicon.ico", redirect_uri=REDIRECT_URI, scope="openid email profile", key="google_auth")
    if result:
        token = result.get("token", {}).get("access_token") or result.get("access_token")
        if token: st.query_params["auth_token"] = token; st.rerun()
    st.stop()

# ===============================
# 4. חיבור לנתונים ועזרים
# ===============================
ALLOWED_USERS = ["eyalicohen@gmail.com", "rachelcohen144@gmail.com"]
if st.session_state.get("user_email") not in ALLOWED_USERS: st.error("⛔ אין גישה."); st.stop()

def parse_amount(val):
    nums = re.findall(r"\d+\.?\d*", str(val))
    return float(nums[0]) if nums else 0.0

def parse_expiry(val):
    if not val or str(val).strip() == "": return None
    val_str = str(val).split(" ")[0]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(val_str, fmt).date()
        except: continue
    return None

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Sheet1", ttl=0)
df.columns = [col.strip().lower() for col in df.columns]
df = df.rename(columns={'notes': 'note', 'status': 'sstatus'})
for col in ["network", "value", "code_or_link", "expiry", "cvv", "note", "sstatus", "last_alert_date"]:
    if col not in df.columns: df[col] = ""

def save_to_sheets(target_df):
    final_df = target_df.drop(columns=["amount_calc"], errors="ignore").reset_index(drop=True)
    conn.update(worksheet="Sheet1", data=final_df)
    st.cache_data.clear()

# ===============================
# 5. מנגנון שליחת אימייל
# ===============================
def send_email_alert(subject, body):
    # שליפת הגדרות מה-UI (נשמרות ב-st.secrets או ב-state זמני - עדיפות ל-Sheet להגדרות)
    # לצורך הפשטות בשלב זה, נשתמש ב-Sidebar להגדרות או Sheet נפרד
    try:
        settings_df = conn.read(worksheet="Settings", ttl=0)
        s = settings_df.iloc[0]
        sender = s['sender_email']
        password = s['app_password']
        receiver = s['receiver_email']
        
        msg = MIMEMultipart()
        msg['From'] = f"ארנק קופונים <{sender}>"
        msg['To'] = receiver
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"שגיאה בשליחת מייל: {e}")
        return False

# בדיקה אוטומטית של קופונים שתוקפם פג
def run_auto_alerts(data_df):
    today = date.today()
    updates_made = False
    alerts_sent = []
    
    for i, row in data_df.iterrows():
        if row['sstatus'] != "פעיל": continue
        exp = parse_expiry(row['expiry'])
        if not exp: continue
        
        days_left = (exp - today).days
        last_alert = str(row['last_alert_date'])
        
        # התראה ב-14, 7 או יום לפני (ורק אם עוד לא נשלח היום)
        if days_left in [14, 7, 1] and last_alert != str(today):
            subject = f"🎫 התראת תוקף: קופון {row['network']} יפוג בעוד {days_left} ימים!"
            body = f"היי,\nהקופון של {row['network']} על סך {row['value']} עומד לפוג בתאריך {row['expiry']}.\nקוד קופון: {row['code_or_link']}\n\nאל תשכחו לנצל!"
            
            if send_email_alert(subject, body):
                data_df.at[i, 'last_alert_date'] = str(today)
                updates_made = True
                alerts_sent.append(f"{row['network']} ({days_left} ימים)")

    if updates_made:
        save_to_sheets(data_df)
    return alerts_sent

# הרצת בדיקת התראות שקטה בכניסה
if "alerts_checked" not in st.session_state:
    sent_list = run_auto_alerts(df)
    if sent_list:
        st.toast(f"נשלחו התראות מייל עבור: {', '.join(sent_list)}", icon="📧")
    st.session_state["alerts_checked"] = True

# ===============================
# 6. ניווט ותצוגה
# ===============================
col_h1, col_h2, col_h3 = st.columns([1, 4, 1])
with col_h1:
    if "user_picture" in st.session_state: st.image(st.session_state["user_picture"], width=45)
with col_h2: st.markdown(f"**שלום, {st.session_state.get('user_name').split()[0]}**")
with col_h3:
    if st.button("🚪"): st.query_params.clear(); st.session_state.clear(); st.rerun()

selected_page = st.radio("ניווט", ["📂 ארנק", "➕ הוספה", "📁 ארכיון", "⚙️ הגדרות"], horizontal=True, label_visibility="collapsed")
st.write("---")

# ===============================
# 7. דפי האפליקציה
# ===============================

if selected_page == "⚙️ הגדרות":
    st.header("⚙️ הגדרות אימייל והתראות")
    st.info("כאן מגדירים מאיפה ולאן יישלחו התראות התוקף.")
    
    try:
        settings_df = conn.read(worksheet="Settings", ttl=0)
        curr_settings = settings_df.iloc[0]
    except:
        curr_settings = {'sender_email': '', 'app_password': '', 'receiver_email': ''}

    with st.form("settings_form"):
        s_email = st.text_input("אימייל השולח (Gmail)", value=curr_settings['sender_email'])
        s_pass = st.text_input("סיסמת אפליקציה (16 תווים)", value=curr_settings['app_password'], type="password")
        r_email = st.text_input("אימייל הנמען (מי יקבל את ההתראה)", value=curr_settings['receiver_email'])
        
        if st.form_submit_button("💾 שמור הגדרות"):
            new_settings = pd.DataFrame([{'sender_email': s_email, 'app_password': s_pass, 'receiver_email': r_email}])
            conn.update(worksheet="Settings", data=new_settings)
            st.success("ההגדרות נשמרו בגיליון Settings!")
    
    if st.button("📧 שלח מייל בדיקה עכשיו"):
        if send_email_alert("מייל בדיקה - ארנק קופונים", "היי! אם קיבלת את המייל הזה, מערכת ההתראות שלך מוגדרת היטב."):
            st.success("מייל בדיקה נשלח בהצלחה!")

elif selected_page == "➕ הוספה":
    st.header("הוספת קופון חדש")
    existing_nets = sorted([n for n in df["network"].unique() if n])
    with st.form("add_form", clear_on_submit=True):
        sel_net = st.selectbox("רשת", options=["➕ רשת חדשה..."] + existing_nets)
        new_net = st.text_input("שם רשת חדשה") if sel_net == "➕ רשת חדשה..." else ""
        col1, col2 = st.columns(2)
        val = col1.text_input("ערך")
        exp_d = col2.date_input("תוקף", min_value=date.today())
        col3, col4 = st.columns(2)
        cvv = col3.text_input("CVV")
        link = col4.text_input("קוד/לינק")
        note = st.text_area("הערות")
        if st.form_submit_button("💾 שמור"):
            final_net = new_net if sel_net == "➕ רשת חדשה..." else sel_net
            if final_net and val:
                new_row = pd.DataFrame([{"network": final_net, "value": val, "expiry": exp_d.strftime("%d/%m/%Y"), "code_or_link": link, "cvv": cvv, "note": note, "sstatus": "פעיל", "last_alert_date": ""}])
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheets(df); st.rerun()

else:
    # דף ארנק / ארכיון (זהה לקוד הקודם עם סיכומי קבוצות)
    is_archive = (selected_page == "📁 ארכיון")
    target_status = "נוצל" if is_archive else "פעיל"
    
    c1, c2 = st.columns([3, 1])
    search = c1.text_input("🔍 חיפוש...")
    if "exp" not in st.session_state: st.session_state.exp = False
    if c2.button("📂" if not st.session_state.exp else "📁"): st.session_state.exp = not st.session_state.exp; st.rerun()

    df["amount_calc"] = df["value"].apply(parse_amount)
    display_df = df[df["sstatus"].str.strip() == target_status].copy()
    if search: display_df = display_df[display_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]

    st.info(f"💰 סה\"כ: ₪ {display_df['amount_calc'].sum():,.0f} | קופונים: {len(display_df)}")

    for net in sorted(display_df["network"].unique()):
        net_df = display_df[display_df["network"] == net]
        group_total = net_df['amount_calc'].sum()
        with st.expander(f"📦 {net} ({len(net_df)}) | ₪ {group_total:,.0f}", expanded=st.session_state.exp or search!=""):
            for i, row in net_df.iterrows():
                exp_dt = parse_expiry(row["expiry"])
                color = "#28a745"
                if target_status == "פעיל" and exp_dt:
                    days = (exp_dt - date.today()).days
                    if days < 0: color = "#ff4b4b"
                    elif days <= 14: color = "#ffa500"

                st.markdown(f"""
                <div class="coupon-card" style="border-right: 6px solid {color};">
                    <div style="display:flex; justify-content:space-between; font-weight:bold;">
                        <span>💎 {row['value']} {f'| 🔒 {row["cvv"]}' if row["cvv"] else ""}</span>
                        <span style="font-size:0.85em; background:#f1f3f5; padding:3px 8px; border-radius:10px;">📅 {row['expiry']}</span>
                    </div>
                    <div class="code-container" onclick="navigator.clipboard.writeText('{row['code_or_link']}'); alert('הועתק!')">{row['code_or_link']}</div>
                    {f'<div style="margin-top:5px; color:#666; font-size:0.9em; border-top:1px solid #eee; padding-top:4px;">📝 {row["note"]}</div>' if row["note"] else ""}
                </div>
                """, unsafe_allow_html=True)

                b1, b2, b3 = st.columns([1.2, 1, 0.8])
                if b1.button("⏪" if is_archive else "✅", key=f"s{i}"):
                    df.at[i, "sstatus"] = "פעיל" if is_archive else "נוצל"
                    save_to_sheets(df); st.rerun()
                with b2.popover("✏️"):
                    uv = st.text_input("סכום", row['value'], key=f"e{i}")
                    if st.button("💾", key=f"bu{i}"):
                        df.at[i, "value"] = uv; save_to_sheets(df); st.rerun()
                if b3.button("🗑️", key=f"d{i}"):
                    df = df.drop(i); save_to_sheets(df); st.rerun()
    
