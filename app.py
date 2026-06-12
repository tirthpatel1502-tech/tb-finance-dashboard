import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------------
# 1. GLOBAL CONFIGURATION & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="TB Finance Department Master Dashboard",
    page_icon="🏥",
    layout="wide"
)

PUBLISHED_LINK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT_ai_LwZQK-DFfgojQ4ZUJiXKt8ikzzGEcnoLQN8hcpKfHxNtzkFEqcPn5jJC07QGiXh8_kLuexZfo/pubhtml"

SHEETS = {
    "ALL SPUTUM": "0",
    "POL EXP.": "57196367",
    "DRUG TRAN.": "1226029008",  
    "X-RAY": "721930106",
    "OTHER EXP.": "1976797645"
}

# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def format_inr(number):
    try:
        s, *d = str(f"{float(number):.2f}").partition(".")
        r = ",".join([s[x-2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]]) if len(s) > 3 else s
        return f"₹{r}{d[0]}{d[1]}"
    except (ValueError, TypeError):
        return "₹0.00"

@st.cache_data(ttl=120) 
def load_data(gid, skiprows=0):
    base_url = PUBLISHED_LINK.split('/pub')[0] 
    csv_url = f"{base_url}/pub?gid={gid}&single=true&output=csv"
    
    try:
        df = pd.read_csv(csv_url, skiprows=skiprows)
        df.columns = df.columns.astype(str).str.strip()
        # I HAVE REMOVED the line that deleted "Unnamed" columns here.
        # This prevents the X-RAY 'PAID' columns from getting destroyed.
        df = df.dropna(axis=1, how='all')
        return df
    except Exception as e:
        st.error(f"Failed to load data. Error: {e}")
        return pd.DataFrame()

def safe_sum(series):
    # Cleans out text, symbols, and spaces, safely ignoring sub-headers like "PAID" or "A, B, C"
    clean_series = series.astype(str).str.replace(r'[^\d.]', '', regex=True)
    return pd.to_numeric(clean_series, errors='coerce').fillna(0).sum()

def apply_sidebar_filters(df, filter_columns):
    st.sidebar.markdown("### 🔍 Filter Data")
    
    for col in filter_columns:
        if col in df.columns:
            options = df[col].dropna().astype(str).unique().tolist()
            options.sort()
            
            selected = st.sidebar.multiselect(f"Select {col}", options)
            if selected:
                df = df[df[col].astype(str).isin(selected)]
    return df

# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.title("🏥 TB Finance Dashboard")
st.sidebar.markdown("---")
selection = st.sidebar.radio("Navigate to Module:", list(SHEETS.keys()))

st.title(f"{selection} Expense Data")
st.markdown("---")

# -----------------------------------------------------------------------------
# 4. TAB LOGIC & RENDERING
# -----------------------------------------------------------------------------
try:
    if selection == "ALL SPUTUM":
        df = load_data(SHEETS[selection], skiprows=0)
        
        if not df.empty:
            df = apply_sidebar_filters(df, ['ASHA/TRANSPORTER NAME', 'TU/PHI', 'TYPE OF PAYMENT'])
            
            kpi_col = 'AMOUNT Rs.' if 'AMOUNT Rs.' in df.columns else 'AMOUNT Rs'
            
            total_val = safe_sum(df[kpi_col]) if kpi_col in df.columns else 0
            aasha_val = 0
            dmc_val = 0
            
            if 'TYPE OF PAYMENT' in df.columns and kpi_col in df.columns:
                aasha_val = safe_sum(df[df['TYPE OF PAYMENT'].astype(str).str.upper().str.contains('AASHA', na=False)][kpi_col])
                dmc_val = safe_sum(df[df['TYPE OF PAYMENT'].astype(str).str.upper().str.contains('DMC', na=False)][kpi_col])

            col1, col2, col3 = st.columns(3)
            col1.metric(label="Grand Total (Rs.)", value=format_inr(total_val))
            col2.metric(label="Total AASHA Expenses", value=format_inr(aasha_val))
            col3.metric(label="Total DMC Expenses", value=format_inr(dmc_val))
            
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "POL EXP.":
        df = load_data(SHEETS[selection], skiprows=1)
        
        if not df.empty:
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            kpi_col = 'Total'
            total_val = safe_sum(df[kpi_col]) if kpi_col in df.columns else 0
            
            st.metric(label="Total POL Expenditure", value=format_inr(total_val))
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "DRUG TRAN.":
        df = load_data(SHEETS[selection], skiprows=1)
        
        if not df.empty:
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            kpi_col = 'TOTAL'
            total_val = safe_sum(df[kpi_col]) if kpi_col in df.columns else 0
            
            st.metric(label="Total Drug Trans. Expense", value=format_inr(total_val))
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "X-RAY":
        df = load_data(SHEETS[selection], skiprows=2)
        
        if not df.empty and len(df) > 1:
            df = apply_sidebar_filters(df, ['TB UNITS'])
            
            # Dynamically finds the final column that contains the word "PAID" in the first data row
            paid_columns = [col for col in df.columns if 'PAID' in str(df[col].iloc[0]).upper()]
            final_paid_col = paid_columns[-1] if paid_columns else None
            
            total_val = safe_sum(df[final_paid_col]) if final_paid_col else 0
            
            st.metric(label="Total Net Paid", value=format_inr(total_val))
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "OTHER EXP.":
        df = load_data(SHEETS[selection], skiprows=0)
        
        if not df.empty:
            df = apply_sidebar_filters(df, ['ZONE', 'TYPE OF EXPENSE'])
            kpi_col = 'AMOUNT'
            total_val = safe_sum(df[kpi_col]) if kpi_col in df.columns else 0
            
            st.metric(label="Total Other Expenditures", value=format_inr(total_val))
            st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("A critical error occurred while rendering the dashboard layout.")
    st.exception(e)