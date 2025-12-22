import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# --- Security Settings ---
PASSWORD = "1"

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

# פונקציה לניקוי ה-.0 המציק מכל העמודות הרלוונטיות
def clean_decimal_strings(df):
    for col in df.columns:
        # הופך לטקסט ומסיר .0 בסוף המחרוזת
        df[col] = df[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')
    return df

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

def parse_amount(val):
    try:
        val = str(val).lower().replace('₪', '').strip()
        if 'x' in val:
            parts = val.split('x')
            return float(parts[0]) * float(parts[1])
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
        return float(numbers[0]) if numbers else 0.0
    except:
        return 0.0

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        df = conn.read(worksheet="Sheet1", ttl="0")
        # --- כאן קורה הקסם של הניקוי ---
        df = clean_decimal_strings(df)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

    st.title("🎫 My Coupon Wallet")

    # --- Dashboard Summary Section ---
    if not df.empty:
        # חישוב הסכום (צריך להמיר זמנית למספר לצורך החישוב)
        total_value = df['value'].apply(parse_amount).sum()
        
        # עיצוב מטריקות בתוך קונטיינר
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Total Value", f"{total_value:,.2f} ₪")
            col2.metric("🎟️ Active Coupons", len(df))
            col3.write("") # מקום ריק לאיזון
    
    st.markdown("---")

    # --- Sidebar Management ---
    st.sidebar.header("🕹️ Menu")
    action = st.sidebar.radio("Go to:", ["My Wallet", "Add Manually", "Bulk Upload"])

    if action == "Add Manually":
        st.subheader("➕ Add New Coupon")
        with st.form("add_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            net = col_a.text_input("Network (e.g., Rami Levy)")
            v = col_b.text_input("Value (e.g., 50 or 50x5)")
            t = col_a.selectbox("Type", ["Link", "Code", "Credit Card"])
            exp = col_b.text_input("Expiry (MM/YYYY)")
            code = st.text_input("Code or URL")
            cvv = st.text_input("CVV")
            n = st.text_area("Notes")
            
            if st.form_submit_button("🚀 Save to Wallet"):
                new_row = pd.DataFrame([{"network": net, "type": t, "value": v, 
                                          "code_or_link": code, "expiry": exp, "cvv": cvv, "notes": n}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Saved successfully!")
                st.rerun()

    elif action == "Bulk Upload":
        st.subheader("📥 Bulk Upload")
        file = st.file_uploader("Upload CSV/Excel", type=['xlsx', 'csv'])
        if file:
            new_df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file, encoding='utf-8-sig')
            if st.button("Merge and Upload"):
                updated_df = pd.concat([df, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Bulk update complete!")
                st.rerun()

    else: # My Wallet
        search = st.text_input("🔍 Search network...", placeholder="Start typing to filter...")
        display_df = df[df['network'].str.contains(search, case=False, na=False)] if search else df

        if display_df.empty:
            st.info("Your wallet is empty or no results found.")
        else:
            networks = sorted(display_df['network'].unique())
            
            for net in networks:
                net_coupons = display_df[display_df['network'] == net]
                # עיצוב כותרת הרשת
                with st.expander(f"🏢 {net.upper()} — {len(net_coupons)} items"):
                    for i, row in net_coupons.iterrows():
                        # יצירת "כרטיס" לכל קופון
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([1, 2, 0.5])
                            
                            with c1:
                                st.markdown(f"### {row['value']} ₪")
                                if row['expiry']: 
                                    st.caption(f"📅 Expires: {row['expiry']}")
                                if row['cvv']:
                                    st.markdown(f"**CVV:** `{row['cvv']}`")
                            
                            with c2:
                                val = str(row['code_or_link']).strip()
                                if val.startswith("http"):
                                    st.link_button("🌐 Open Coupon Link", val, use_container_width=True)
                                else:
                                    st.code(val, language="text")
                                
                                if row['notes']:
                                    st.caption(f"📝 {row['notes']}")
                            
                            with c3:
                                # כפתור מחיקה מעוצב
                                if st.button("🗑️", key=f"del_{i}", help="Delete this coupon"):
                                    # קריאה מחדש כדי לוודא שמוחקים מהגרסה הכי עדכנית
                                    full_df = conn.read(worksheet="Sheet1", ttl="0")
                                    full_df = full_df.drop(i).reset_index(drop=True)
                                    conn.update(worksheet="Sheet1", data=full_df)
                                    st.rerun()

    # Sidebar Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
