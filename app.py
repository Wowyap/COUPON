import re
from datetime import datetime, timedelta

# --- 1. הגדרות דף ---
# --- 1. הגדרות עיצוב גלובליות ---
PASSWORD = "1"
GLOBAL_FONT_SIZE = "20px"  # <--- שנה כאן את גודל הפונט לכל המלל (למשל "18px", "22px" וכו')

# מילון לוגואים - הוסף כאן שמות רשתות וקישורים ללוגו (URL)
LOGOS = {
    "רמי לוי": "https://upload.wikimedia.org/wikipedia/he/thumb/6/6a/Rami_Levy_logo.svg/250px-Rami_Levy_logo.svg.png",
    "שופרסל": "https://upload.wikimedia.org/wikipedia/he/thumb/3/30/Shufersal_logo.svg/250px-Shufersal_logo.svg.png",
    "ויקטורי": "https://upload.wikimedia.org/wikipedia/he/c/c9/Victory_Supermarket_Chain_Logo.png",
    # ניתן להוסיף עוד רשתות...
}
DEFAULT_LOGO = "https://cdn-icons-png.flaticon.com/512/726/726476.png" # אייקון קופון גנרי

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

# --- 2. פונקציות עזר ועיבוד נתונים ---
# --- הזרקת CSS לשליטה גלובלית בגודל הפונט ---
st.markdown(f"""
    <style>
    html, body, [class*="st-"], p, div, span, input, label, button {{
        font-size: {GLOBAL_FONT_SIZE} !important;
    }}
    /* התאמה ספציפית לקוד כדי שלא יהיה קטן מדי */
    code {{
        font-size: {GLOBAL_FONT_SIZE} !important;
    }}
    /* הגדלת כותרות ה-Expander */
    .st-emotion-cache-p3m962 {{ 
        font-size: {GLOBAL_FONT_SIZE} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר ---
def clean_data(df):
    """ניקוי .0 וערכים ריקים"""
for col in df.columns:
df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
return df

def parse_expiry(date_str):
    """ניסיון להמיר מחרוזת תאריך לאובייקט datetime לצורך מיון"""
if not date_str or date_str == "" or date_str == "None":
return datetime.max
    
formats = ["%d/%m/%Y", "%d/%m/%y", "%m/%y", "%m/%Y", "%Y-%m-%d"]
for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
        try: return datetime.strptime(date_str, fmt)
        except: continue
return datetime.max

def parse_amount(val):
@@ -36,25 +59,22 @@ def parse_amount(val):
return float(parts[0]) * float(parts[1])
numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
return float(numbers[0]) if numbers else 0.0
    except:
        return 0.0
    except: return 0.0

# --- 3. חלון עריכה צף (עם שמות מודגשים) ---
# --- 3. חלון עריכה ---
@st.dialog("ערוך קופון ✏️")
def edit_coupon_dialog(index, row_data, df, conn):
with st.form("edit_form"):
        # הדגשת שם הרשת בכותרת העריכה
        st.markdown(f"### עריכת קופון עבור: **{row_data['network']}**")
        st.markdown(f"### עריכה: **{row_data['network']}**")
new_net = st.text_input("שם הרשת", value=row_data['network'])
        new_val = st.text_input("ערך/סכום", value=row_data['value'])
        new_val = st.text_input("ערך", value=row_data['value'])
new_type = st.selectbox("סוג", ["Link", "Code", "Credit Card"], 
index=["Link", "Code", "Credit Card"].index(row_data['type']) if row_data['type'] in ["Link", "Code", "Credit Card"] else 0)
        new_code = st.text_input("קוד או קישור", value=row_data['code_or_link'])
        new_exp = st.text_input("תוקף (DD/MM/YYYY)", value=row_data['expiry'])
        new_code = st.text_input("קוד/קישור", value=row_data['code_or_link'])
        new_exp = st.text_input("תוקף", value=row_data['expiry'])
new_cvv = st.text_input("CVV", value=row_data['cvv'])
new_notes = st.text_area("הערות", value=row_data['notes'])
        
        if st.form_submit_button("💾 שמור שינויים", use_container_width=True):
        if st.form_submit_button("💾 שמור"):
df.at[index, 'network'] = new_net
df.at[index, 'value'] = new_val
df.at[index, 'type'] = new_type
@@ -63,142 +83,112 @@ def edit_coupon_dialog(index, row_data, df, conn):
df.at[index, 'cvv'] = new_cvv
df.at[index, 'notes'] = new_notes
conn.update(worksheet="Sheet1", data=df)
            st.success("הקופון עודכן!")
st.rerun()

# --- 4. מערכת כניסה ---
# --- 4. כניסה ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
st.title("🔒 Login")
pwd = st.text_input("Password:", type="password")
if st.button("Enter"):
if pwd == PASSWORD:
st.session_state.authenticated = True
st.rerun()
            else:
                st.error("Wrong password")
            else: st.error("Wrong password")
return False
return True

# --- 5. לוגיקה מרכזית ---
if check_password():
conn = st.connection("gsheets", type=GSheetsConnection)
    
try:
df = conn.read(worksheet="Sheet1", ttl="0")
df = clean_data(df)
except Exception as e:
        st.error(f"שגיאת חיבור: {e}")
        st.stop()
        st.error(f"שגיאת חיבור: {e}"); st.stop()

st.title("🎫 My Coupon Wallet")

    # --- סיכום מדדים מעוצב ---
    # --- מדדים ---
if not df.empty:
total_value = df['value'].apply(parse_amount).sum()
c1, c2, c3 = st.columns(3)
        with c1:
            st.container(border=True).metric("💰 שווי כולל", f"{total_value:,.2f} ₪")
        with c2:
            st.container(border=True).metric("🎟️ קופונים", len(df))
        with c3:
            # חישוב קופונים שפגים ב-7 הימים הקרובים
            near_expiry = len([x for x in df['expiry'] if parse_expiry(x) < datetime.now() + timedelta(days=7)])
            st.container(border=True).metric("📅 פגי תוקף בקרוב", near_expiry)
        c1.metric("💰 שווי כולל", f"{total_value:,.2f} ₪")
        c2.metric("🎟️ קופונים", len(df))
        near_expiry = len([x for x in df['expiry'] if parse_expiry(x) < datetime.now() + timedelta(days=7)])
        c3.metric("📅 פגי תוקף בקרוב", near_expiry)

st.sidebar.header("🕹️ תפריט")
action = st.sidebar.radio("עבור אל:", ["הארנק שלי", "הוספה ידנית", "טעינה מרוכזת"])

if action == "הוספה ידנית":
        st.subheader("➕ הוספת קופון חדש")
with st.form("add_form", clear_on_submit=True):
col1, col2 = st.columns(2)
net = col1.text_input("רשת")
val_input = col2.text_input("ערך")
type_input = col1.selectbox("סוג", ["Link", "Code", "Credit Card"])
            exp_input = col2.text_input("תוקף (DD/MM/YYYY)")
            exp_input = col2.text_input("תוקף (DD/MM/YY)")
code_input = st.text_input("קוד או קישור")
cvv_input = st.text_input("CVV")
notes_input = st.text_area("הערות")
            if st.form_submit_button("🚀 שמור בארנק", use_container_width=True):
            if st.form_submit_button("🚀 שמור"):
new_row = pd.DataFrame([{"network": net, "type": type_input, "value": val_input, 
"code_or_link": code_input, "expiry": exp_input, 
"cvv": cvv_input, "notes": notes_input}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("נשמר!")
                st.rerun()
                conn.update(worksheet="Sheet1", data=pd.concat([df, new_row], ignore_index=True))
                st.success("נשמר!"); st.rerun()

elif action == "הארנק שלי":
        search = st.text_input("🔍 חיפוש רשת...", placeholder="הקלד שם רשת לסינון מהיר")
        
        # מיון לפי תאריך תפוגה
        search = st.text_input("🔍 חיפוש רשת...")
df['temp_date'] = df['expiry'].apply(parse_expiry)
display_df = df.sort_values(by='temp_date', ascending=True)
        
if search:
display_df = display_df[display_df['network'].str.contains(search, case=False, na=False)]

if display_df.empty:
            st.info("אין קופונים להצגה.")
            st.info("אין קופונים.")
else:
            # שמות הרשתות יישלפו מה-df המסונן והממוין
networks = display_df['network'].unique()
            
for net in networks:
net_coupons = display_df[display_df['network'] == net]
                # --- שימוש ב-Markdown להדגשת שם הרשת בכותרת ה-Expander ---
                
                # בחירת לוגו
                logo_url = LOGOS.get(net, DEFAULT_LOGO)
                
                # כותרת אקספנדר עם לוגו קטן ושם מודגש
with st.expander(f"🏢 **{net.upper()}** — ({len(net_coupons)} פריטים)", expanded=True):
                    # הצגת לוגו הרשת בראש הרשימה
                    st.image(logo_url, width=80)
                    
for i, row in net_coupons.iterrows():
expiry_date = parse_expiry(row['expiry'])
                        now = datetime.now()
                        
                        bg_color = "#F8F9FA"
status_msg = ""
                        bg_color = "#F8F9FA" # צבע ברירת מחדל
                        
                        if expiry_date < now:
                            status_msg = "❌ פג תוקף"
                            bg_color = "#FFEBEE"
                        elif expiry_date < now + timedelta(days=7):
                            status_msg = "⚠️ פג בקרוב!"
                            bg_color = "#FFF3E0"
                        if expiry_date < datetime.now():
                            status_msg = "❌ פג תוקף"; bg_color = "#FFEBEE"
                        elif expiry_date < datetime.now() + timedelta(days=7):
                            status_msg = "⚠️ פג בקרוב!"; bg_color = "#FFF3E0"

with st.container(border=True):
                            # יצירת רקע צבעוני לפי דחיפות
                            st.markdown(f"""<div style="background-color:{bg_color}; padding:12px; border-radius:8px; border: 1px solid #ddd;">""", unsafe_allow_html=True)
                            
                            st.markdown(f'<div style="background-color:{bg_color}; padding:15px; border-radius:10px;">', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, 2, 0.5])
                            
with c1:
                                st.markdown(f"## {row['value']} ₪")
                                if status_msg: st.markdown(f"**{status_msg}**")
                                st.caption(f"📅 תוקף: {row['expiry']}")
                                if row['cvv']: st.markdown(f"**CVV:** `{row['cvv']}`")
                            
                                st.markdown(f"**ערך: {row['value']} ₪**")
                                if status_msg: st.markdown(f"*{status_msg}*")
                                st.write(f"תוקף: {row['expiry']}")
                                if row['cvv']: st.write(f"CVV: {row['cvv']}")
with c2:
                                link_val = str(row['code_or_link']).strip()
                                if link_val.startswith("http"):
                                    st.link_button("🌐 פתח קופון", link_val, use_container_width=True)
                                else:
                                    st.code(link_val, language="text")
                                if row['notes']: st.info(f"💡 {row['notes']}")
                            
                                val = str(row['code_or_link']).strip()
                                if val.startswith("http"): st.link_button("🌐 פתח קישור", val, use_container_width=True)
                                else: st.code(val, language="text")
                                if row['notes']: st.caption(f"💡 {row['notes']}")
with c3:
                                # כפתורי פעולה
                                if st.button("✏️", key=f"edit_{i}", use_container_width=True, help="ערוך"):
                                    edit_coupon_dialog(i, row, df, conn)
                                if st.button("🗑️", key=f"del_{i}", use_container_width=True, help="מחק"):
                                    full_df = conn.read(worksheet="Sheet1", ttl="0")
                                    full_df = full_df.drop(i).reset_index(drop=True)
                                    conn.update(worksheet="Sheet1", data=full_df)
                                if st.button("✏️", key=f"edit_{i}"): edit_coupon_dialog(i, row, df, conn)
                                if st.button("🗑️", key=f"del_{i}"):
                                    conn.update(worksheet="Sheet1", data=df.drop(i).reset_index(drop=True))
st.rerun()
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout", use_container_width=True):
    if st.sidebar.button("🔓 Logout"):
st.session_state.authenticated = False
st.rerun()
