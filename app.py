import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# --- Security Settings ---
PASSWORD = "שנה_לסיסמה_שלך"

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

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

# Helper to sum amounts for the dashboard
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
        # Read from Google Sheets
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = df.fillna("")
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    st.title("🎫 My Coupon Wallet")

    # --- Dashboard Summary ---
    if not df.empty:
        total_value = df['value'].apply(parse_amount).sum()
        col1, col2 = st.columns(2)
        col1.metric("Total Value", f"{total_value:,.2f} ₪")
        col2.metric("Active Coupons", len(df))
        st.markdown("---")

    # --- Sidebar Actions ---
    st.sidebar.header("Management")
    action = st.sidebar.radio("Navigation:", ["My Wallet", "Add Manually", "Bulk Upload"])

    if action == "Add Manually":
        st.subheader("➕ Add New Coupon")
        with st.form("add_form"):
            net = st.text_input("Network")
            v = st.text_input("Value (e.g. 100 or 50x5)")
            t = st.selectbox("Type", ["Link", "Code", "Credit Card"])
            code = st.text_input("Code or URL")
            exp = st.text_input("Expiry (DD-MM-YYYY)")
            cvv = st.text_input("CVV")
            n = st.text_area("Notes")
            if st.form_submit_button("Save"):
                new_row = pd.DataFrame([{"network": net, "type": t, "value": v, 
                                          "code_or_link": code, "expiry": exp, "cvv": cvv, "notes": n}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Successfully saved to Google Sheets!")
                st.rerun()

    elif action == "Bulk Upload":
        st.subheader("📥 Upload CSV/Excel")
        file = st.file_uploader("Select file", type=['xlsx', 'csv'])
        if file:
            new_df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file, encoding='utf-8-sig')
            if st.button("Upload to Cloud"):
                updated_df = pd.concat([df, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Data merged successfully!")
                st.rerun()

    else: # My Wallet View
        search = st.text_input("🔍 Search network:")
        display_df = df[df['network'].str.contains(search, case=False, na=False)] if search else df

        if display_df.empty:
            st.info("No coupons found.")
        else:
            # Grouping by network name
            networks = sorted(display_df['network'].unique())
            
            for net in networks:
                net_coupons = display_df[display_df['network'] == net]
                with st.expander(f"➕ {net} ({len(net_coupons)} items)"):
                    for i, row in net_coupons.iterrows():
                        c1, c2, c3, c4 = st.columns([1, 2.5, 1, 0.5])
                        
                        with c1:
                            st.write(f"**{row['value']}**")
                            if row['expiry']: st.caption(f"Exp: {row['expiry']}")
                        
                        with c2:
                            val = str(row['code_or_link']).strip()
                            if val.startswith("http"):
                                # הצגת לחצן פתיחה
                                st.link_button("Open Link 🔗", val)
                                # הצגת הלינק עצמו כטקסט
                                st.caption(f"URL: {val}")
                            else:
                                st.code(val, language="text")
                        
                        with c3:
                            if row['cvv']: st.write(f"CVV: {row['cvv']}")
                            if row['notes']: st.info(row['notes'])
                            
                        with c4:
                            if st.button("🗑️", key=f"del_{i}"):
                                # Re-read data to ensure we delete the correct row
                                full_df = conn.read(worksheet="Sheet1", ttl="0")
                                full_df = full_df.drop(i).reset_index(drop=True)
                                conn.update(worksheet="Sheet1", data=full_df)
                                st.rerun()
                        st.markdown("---")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
