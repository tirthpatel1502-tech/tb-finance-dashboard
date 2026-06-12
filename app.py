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
        df = df.dropna(axis=1, how='all')
        return df
    except Exception as e:
        st.error(f"Failed to load data. Error: {e}")
        return pd.DataFrame()

def safe_sum(series):
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
            # Clean junk rows
            df = df[~df.iloc[:, 0].astype(str).isin(['None', 'nan', 'SR. NO.'])].copy()
            
            df = apply_sidebar_filters(df, ['ASHA/TRANSPORTER NAME', 'TU/PHI', 'TYPE OF PAYMENT'])
            
            # Monthly filters
            month_keywords = ['DEC', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV']
            month_cols = [c for c in df.columns if any(m in str(c).upper() for m in month_keywords) and 'AMOUNT' not in str(c).upper()]
            
            if month_cols:
                st.sidebar.markdown("### 📅 Select Months")
                selected_months = st.sidebar.multiselect("Months to View", month_cols, default=month_cols)
                cols_to_drop = [c for c in month_cols if c not in selected_months]
                df = df.drop(columns=cols_to_drop, errors='ignore')

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
            df = df[~df.iloc[:, 0].astype(str).isin(['None', 'nan', 'Sr. No.'])].copy()
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            kpi_col = 'Total'
            st.metric(label="Total POL Expenditure", value=format_inr(safe_sum(df[kpi_col]) if kpi_col in df.columns else 0))
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "DRUG TRAN.":
        df = load_data(SHEETS[selection], skiprows=1)
        if not df.empty:
            df = df[~df.iloc[:, 0].astype(str).isin(['None', 'nan', 'Sr. No.'])].copy()
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            
            # Monthly filters
            actual_month_cols = [c for c in df.columns if c.upper() in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUNE', 'JULY', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC']]
            if actual_month_cols:
                st.sidebar.markdown("### 📅 Select Months")
                selected_months = st.sidebar.multiselect("Months to View", actual_month_cols, default=actual_month_cols)
                cols_to_drop = [c for c in actual_month_cols if c not in selected_months]
                df = df.drop(columns=cols_to_drop, errors='ignore')

            kpi_col = 'TOTAL'
            st.metric(label="Total Drug Trans. Expense", value=format_inr(safe_sum(df[kpi_col]) if kpi_col in df.columns else 0))
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "X-RAY":
        base_url = PUBLISHED_LINK.split('/pub')[0] 
        csv_url = f"{base_url}/pub?gid={SHEETS[selection]}&single=true&output=csv"
        df = pd.read_csv(csv_url, skiprows=1)
        
        # 1. Clean Unnamed Columns dynamically
        new_cols = []
        current_month = ""
        for col in df.columns:
            col_str = str(col).strip()
            if 'Unnamed' not in col_str and col_str != '':
                if '26' in col_str or '25' in col_str or 'TOTAL' in col_str.upper():
                    current_month = col_str
                    new_cols.append(f"{current_month} (GROSS)")
                else:
                    new_cols.append(col_str)
            else:
                if len(new_cols) > 0 and '(GROSS)' in new_cols[-1]:
                    new_cols.append(f"{current_month} (TDS)")
                elif len(new_cols) > 0 and '(TDS)' in new_cols[-1]:
                    new_cols.append(f"{current_month} (PAID)")
                else:
                    new_cols.append(col_str)
        df.columns = new_cols
        
        # Drop junk rows
        df = df[~df.iloc[:, 1].astype(str).isin(['None', 'B', 'nan', 'X-RAY FACILITY NAME'])].copy()
        
        # Convert numeric columns safely
        numeric_cols = [c for c in df.columns if '(GROSS)' in c or '(TDS)' in c or '(PAID)' in c]
        for c in numeric_cols:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            
        # 2. Add Total Number of X-RAY Column for EVERY month
        for c in list(numeric_cols):
            if '(GROSS)' in c:
                prefix = c.split(' (')[0]
                count_col = f"{prefix} (X-RAY COUNT)"
                df[count_col] = (df[c] / 200).astype(int)
                numeric_cols.append(count_col)
                
        # Reorder columns to group them nicely
        final_cols = [c for c in df.columns if c not in numeric_cols]
        prefixes = []
        for c in numeric_cols:
            prefix = c.split(' (')[0]
            if prefix not in prefixes: prefixes.append(prefix)
            
        for prefix in prefixes:
            if f"{prefix} (GROSS)" in numeric_cols: final_cols.append(f"{prefix} (GROSS)")
            if f"{prefix} (TDS)" in numeric_cols: final_cols.append(f"{prefix} (TDS)")
            if f"{prefix} (PAID)" in numeric_cols: final_cols.append(f"{prefix} (PAID)")
            if f"{prefix} (X-RAY COUNT)" in numeric_cols: final_cols.append(f"{prefix} (X-RAY COUNT)")
        df = df[final_cols]
        
        df = apply_sidebar_filters(df, ['X-RAY FACILITY NAME', 'TB UNITS'])
        
        # Monthly Filters
        st.sidebar.markdown("### 📅 Select Months")
        selected_months = st.sidebar.multiselect("Months to View", prefixes, default=prefixes)
        
        cols_to_drop = []
        for c in numeric_cols:
            prefix = c.split(' (')[0]
            if prefix not in selected_months:
                cols_to_drop.append(c)
        df = df.drop(columns=cols_to_drop, errors='ignore')
        
        # 3. Facility Wise vs Branch Wise Merge
        st.markdown("### View Options")
        view_type = st.radio("Display Format:", ["All Branches (Detailed)", "Facility Wise (Merged Totals)"], horizontal=True)
        
        if view_type == "Facility Wise (Merged Totals)":
            agg_funcs = {c: 'sum' for c in df.columns if c in numeric_cols and c not in cols_to_drop}
            if 'Bank Account No.' in df.columns: agg_funcs['Bank Account No.'] = 'first'
            if 'IFSC Code' in df.columns: agg_funcs['IFSC Code'] = 'first'
            df = df.groupby('X-RAY FACILITY NAME').agg(agg_funcs).reset_index()
            
        # Metric
        paid_cols = [c for c in df.columns if '(PAID)' in c and 'TOTAL' in c.upper()]
        final_paid_col = paid_cols[-1] if paid_cols else None
        total_val = df[final_paid_col].sum() if final_paid_col else 0
        st.metric(label="Total Net Paid (Filtered)", value=format_inr(total_val))
        
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif selection == "OTHER EXP.":
        df = load_data(SHEETS[selection], skiprows=0)
        if not df.empty:
            df = df[~df.iloc[:, 0].astype(str).isin(['None', 'nan', 'NO'])].copy()
            df = apply_sidebar_filters(df, ['ZONE', 'TYPE OF EXPENSE', 'MONTH', 'BUDGET HEAD'])
            kpi_col = 'AMOUNT'
            st.metric(label="Total Other Expenditures", value=format_inr(safe_sum(df[kpi_col]) if kpi_col in df.columns else 0))
            st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("A critical error occurred while rendering the dashboard layout.")
    st.exception(e)
