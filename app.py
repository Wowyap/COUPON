import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# --- 1. הגדרות דף אבטחה ---
PASSWORD = "1"
st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

# --- 2. פונקציות עזר (ניקוי נתונים) ---
def clean_data(df):
    """מסיר .0 ממספרים שהפכו ל-Float ומנקה ערכים ריקים"""
    for col in df.columns:
        df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
    return df

def parse_amount(val):
    """מחשב ערך כספי לסיכום המדדים"""
    try:
        val = str(val).lower().replace('₪', '').strip()
        if 'x' in val:
            parts = val.split('x')
            return float(parts[0]) * float(parts[1])
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
        return float(numbers[0]) if numbers else 0.0
    except:
        return 0.0

# --- 3. חלון עריכה צף (Edit Dialog) ---
@st.dialog("ערוך קופון ✏️")
def edit_coupon_dialog(index, row_data, df, conn):
    with st.form("edit_form"):
        st.markdown(f"### עריכת קופון: {row_data['network']}")
        new_net = st.text_input("רשת", value=row_data['network'])
        new_val = st.text_input("ערך/סכום", value=row_data['value'])
        new_type = st.selectbox("סוג", ["Link", "Code", "Credit Card"], 
                               index=["Link", "Code", "Credit Card"].index(row_data['type']) if row_data['type'] in ["Link", "Code", "Credit Card"] else 0)
        new_code = st.text_input("קוד או קישור", value=row_data['code_or_link'])
        new_exp = st.text_input("תוקף (MM/YY)", value=row_data['expiry'])
        new_cvv = st.text_input("CVV", value=row_data['cvv'])
        new_notes = st.text_area("הערות", value=row_data['notes'])
        
        if st.form_submit_button("שמור שינויים", use_container_width=True):
            # עדכון השורה בזיכרון
            df.at[index, 'network'] = new_net
            df.at[index, 'value'] = new_val
            df.at[index, 'type'] = new_type
            df.at[index, 'code_or_link'] = new_code
            df.at[index, 'expiry'] = new_exp
            df.at[index, 'cvv'] = new_cvv
            df.at[index, 'notes'] = new_notes
            
            # עדכון גוגל שיטס
            conn.update(worksheet="Sheet1", data=df)
            st.success("הקופון עודכן!")
            st.rerun()

# --- 4. מערכת כניסה ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Login")
        pwd = st.text_input("Password:", type="password")
        if st.button("Enter"):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Wrong password")
        return False
    return True

# --- 5. לוגיקה מרכזית ---
if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        # קריאת נתונים וניקוי
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = clean_data(df)
    except Exception as e:
        st.error(f"שגיאת חיבור: {e}")
        st.stop()

    st.title("🎫 My Coupon Wallet")

    # --- סיכום מדדים (Dashboard) ---
    if not df.empty:
        total_value = df['value'].apply(parse_amount).sum()
        with st.container(border=True):
            c1, c2 = st.columns(2)
            c1.metric("💰 שווי כולל", f"{total_value:,.2f} ₪")
            c2.metric("🎟️ קופונים פעילים", len(df))

    # --- תפריט צד ---
    st.sidebar.header("🕹️ תפריט")
    action = st.sidebar.radio("עבור אל:", ["הארנק שלי", "הוספה ידנית", "טעינה מרוכזת"])

    if action == "הוספה ידנית":
        st.subheader("➕ הוספת קופון חדש")
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            net = col1.text_input("רשת")
            val_input = col2.text_input("ערך")
            type_input = col1.selectbox("סוג", ["Link", "Code", "Credit Card"])
            exp_input = col2.text_input("תוקף")
            code_input = st.text_input("קוד או קישור")
            cvv_input = st.text_input("CVV")
            notes_input = st.text_area("הערות")
            
            if st.form_submit_button("שמור בארנק"):
                new_row = pd.DataFrame([{"network": net, "type": type_input, "value": val_input, 
                                         "code_or_link": code_input, "expiry": exp_input, 
                                         "cvv": cvv_input, "notes": notes_input}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("נשמר בהצלחה!")
                st.rerun()

    elif action == "טעינה מרוכזת":
        st.subheader("📥 העלאת קבצים")
        file = st.file_uploader("בחר קובץ CSV או Excel", type=['xlsx', 'csv'])
        if file:
            new_df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file)
            if st.button("מזג ועדכן"):
                updated_df = pd.concat([df, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("הנתונים הועלו!")
                st.rerun()

    else: # הארנק שלי
        search = st.text_input("🔍 חיפוש...", placeholder="הקלד שם רשת...")
        display_df = df[df['network'].str.contains(search, case=False, na=False)] if search else df

        if display_df.empty:
            st.info("אין נתונים להצגה.")
        else:
            networks = sorted(display_df['network'].unique())
            for net in networks:
                net_coupons = display_df[display_df['network'] == net]
                with st.expander(f"🏢 {net.upper()} — ({len(net_coupons)} פריטים)"):
                    for i, row in net_coupons.iterrows():
                        with st.container(border=True):
                            col_text, col_action, col_buttons = st.columns([1.5, 2, 0.5])
                            
                            with col_text:
                                st.markdown(f"### {row['value']} ₪")
                                if row['expiry']: st.caption(f"📅 תוקף: {row['expiry']}")
                                if row['cvv']: st.markdown(f"**CVV:** `{row['cvv']}`")
                            
                            with col_action:
                                link_val = str(row['code_or_link']).strip()
                                if link_val.startswith("http"):
                                    st.link_button("🌐 פתח קישור", link_val, use_container_width=True)
                                else:
                                    st.code(link_val, language="text")
                                if row['notes']: st.caption(f"📝 {row['notes']}")
                            
                            with col_buttons:
                                # כפתור עריכה
                                if st.button("✏️", key=f"edit_{i}", use_container_width=True):
                                    edit_coupon_dialog(i, row, df, conn)
                                
                                # כפתור מחיקה
                                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                                    full_df = conn.read(worksheet="Sheet1", ttl="0")
                                    full_df = full_df.drop(i).reset_index(drop=True)
                                    conn.update(worksheet="Sheet1", data=full_df)
                                    st.rerun()

    # Logout
    if st.sidebar.button("🔓 Logout"):
        st.session_state.authenticated = False
        st.rerun()
