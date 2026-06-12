import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------------------------------------------------------
# 1. GLOBAL CONFIGURATION & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="TB Finance Master Dashboard",
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

def safe_sum(series):
    # Strictly extracts numbers and sums them safely
    clean_series = series.astype(str).str.replace(r'[^\d.]', '', regex=True)
    return pd.to_numeric(clean_series, errors='coerce').fillna(0).sum()

def apply_sidebar_filters(df, filter_columns):
    st.sidebar.markdown("### 🔍 Filter Data")
    for col in filter_columns:
        if col in df.columns:
            # Clean options
            options = [str(x) for x in df[col].unique() if str(x).strip() not in ['None', 'nan', '']]
            options.sort()
            selected = st.sidebar.multiselect(f"Select {col}", options)
            if selected:
                df = df[df[col].astype(str).isin(selected)]
    return df

@st.cache_data(ttl=120) 
def load_smart_data(gid, module_name):
    """Intelligently scans the sheet to find headers, regardless of merged cells or blank rows."""
    base_url = PUBLISHED_LINK.split('/pub')[0] 
    csv_url = f"{base_url}/pub?gid={gid}&single=true&output=csv"
    
    try:
        # Read raw without headers
        raw_df = pd.read_csv(csv_url, header=None)
        
        if module_name == "X-RAY":
            # 1. SMART SCAN FOR X-RAY
            # Find the row containing 'GROSS'
            gross_idx = raw_df[raw_df.apply(lambda r: r.astype(str).str.contains('GROSS', case=False).any(), axis=1)].index
            
            if len(gross_idx) > 0:
                header_row_idx = gross_idx[0]
                
                # Extract the row above it (The Months) and forward fill to fix merged cells
                month_row = raw_df.iloc[header_row_idx - 1].replace({'None': np.nan, '': np.nan, pd.NA: np.nan}).ffill().fillna('')
                
                # Extract the Sub-Headers (GROSS, TDS, PAID)
                sub_row = raw_df.iloc[header_row_idx].fillna('')
                
                # Combine them intelligently
                new_cols = []
                for m, s in zip(month_row, sub_row):
                    m_str, s_str = str(m).strip(), str(s).strip()
                    if m_str and s_str and m_str != s_str and s_str.upper() in ['GROSS', 'TDS', 'PAID']:
                        new_cols.append(f"{m_str} ({s_str})")
                    else:
                        new_cols.append(s_str if s_str else m_str)
                
                raw_df.columns = new_cols
                
                # Slice the dataframe to keep only data below headers
                df = raw_df.iloc[header_row_idx + 1:].copy()
                
                # Destroy the alphabet row (A, B, C...) if it exists
                if df.iloc[0].astype(str).str.strip().isin(['A', 'B', 'C']).any():
                    df = df.iloc[1:].copy()
                    
                df = df.reset_index(drop=True)
                return df
                
        else:
            # 2. SMART SCAN FOR OTHER MODULES
            # Scan for standard header keywords
            header_idx = raw_df[raw_df.apply(lambda r: r.astype(str).str.contains('(?i)SR\.? NO\.?|TB UNIT|ZONE|Name of Employee', regex=True).any(), axis=1)].index
            
            if len(header_idx) > 0:
                idx = header_idx[0]
                raw_df.columns = raw_df.iloc[idx].astype(str).str.strip()
                df = raw_df.iloc[idx + 1:].copy()
                
                # Destroy Alphabet row if exists
                if df.iloc[0].astype(str).str.strip().isin(['A', 'B', 'C', '1', '2', '3']).sum() > 3:
                     df = df.iloc[1:].copy()
                     
                df = df.reset_index(drop=True)
                return df

        return raw_df # Fallback
        
    except Exception as e:
        st.error(f"Failed to load data. Error: {e}")
        return pd.DataFrame()

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
    df = load_smart_data(SHEETS[selection], selection)
    
    if not df.empty:
        # Clean global junk rows
        if df.columns[0] != 'Unnamed: 0':
            df = df[~df.iloc[:, 0].astype(str).str.strip().isin(['None', 'nan', ''])].copy()

        if selection == "ALL SPUTUM":
            df = apply_sidebar_filters(df, ['ASHA/TRANSPORTER NAME', 'TU/PHI', 'TYPE OF PAYMENT'])
            
            # Monthly filters
            month_cols = [c for c in df.columns if any(m in str(c).upper() for m in ['DEC', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN']) and 'AMOUNT' not in str(c).upper()]
            if month_cols:
                st.sidebar.markdown("### 📅 Select Months")
                selected_months = st.sidebar.multiselect("Months to View", month_cols, default=month_cols)
                df = df.drop(columns=[c for c in month_cols if c not in selected_months], errors='ignore')

            kpi_col = 'AMOUNT Rs.' if 'AMOUNT Rs.' in df.columns else ('AMOUNT Rs' if 'AMOUNT Rs' in df.columns else None)
            total_val = safe_sum(df[kpi_col]) if kpi_col else 0
            aasha_val = safe_sum(df[df['TYPE OF PAYMENT'].astype(str).str.upper().str.contains('AASHA', na=False)][kpi_col]) if kpi_col and 'TYPE OF PAYMENT' in df.columns else 0
            dmc_val = safe_sum(df[df['TYPE OF PAYMENT'].astype(str).str.upper().str.contains('DMC', na=False)][kpi_col]) if kpi_col and 'TYPE OF PAYMENT' in df.columns else 0

            c1, c2, c3 = st.columns(3)
            c1.metric(label="Grand Total (Rs.)", value=format_inr(total_val))
            c2.metric(label="Total AASHA Expenses", value=format_inr(aasha_val))
            c3.metric(label="Total DMC Expenses", value=format_inr(dmc_val))
            st.dataframe(df, use_container_width=True, hide_index=True)

        elif selection == "POL EXP.":
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            kpi_col = 'Total'
            st.metric(label="Total POL Expenditure", value=format_inr(safe_sum(df[kpi_col]) if kpi_col in df.columns else 0))
            st.dataframe(df, use_container_width=True, hide_index=True)

        elif selection == "DRUG TRAN.":
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            
            actual_month_cols = [c for c in df.columns if c.upper() in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUNE', 'JULY', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC']]
            if actual_month_cols:
                st.sidebar.markdown("### 📅 Select Months")
                selected_months = st.sidebar.multiselect("Months to View", actual_month_cols, default=actual_month_cols)
                df = df.drop(columns=[c for c in actual_month_cols if c not in selected_months], errors='ignore')

            kpi_col = 'TOTAL'
            st.metric(label="Total Drug Trans. Expense", value=format_inr(safe_sum(df[kpi_col]) if kpi_col in df.columns else 0))
            st.dataframe(df, use_container_width=True, hide_index=True)

        elif selection == "X-RAY":
            # Identify numeric money columns and convert them
            numeric_cols = [c for c in df.columns if '(GROSS)' in c or '(TDS)' in c or '(PAID)' in c]
            for c in numeric_cols:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                
            # Add X-RAY COUNT calculation dynamically for all months
            generated_cols = []
            for c in list(numeric_cols):
                if '(GROSS)' in c:
                    prefix = c.split(' (')[0]
                    count_col = f"{prefix} (X-RAY COUNT)"
                    df[count_col] = (df[c] / 200).astype(int)
                    generated_cols.append(count_col)
            
            numeric_cols.extend(generated_cols)
            
            # Reorder columns neatly
            static_cols = [c for c in df.columns if c not in numeric_cols]
            prefixes = list(dict.fromkeys([c.split(' (')[0] for c in numeric_cols]))
            
            ordered_cols = static_cols.copy()
            for prefix in prefixes:
                if f"{prefix} (GROSS)" in numeric_cols: ordered_cols.append(f"{prefix} (GROSS)")
                if f"{prefix} (TDS)" in numeric_cols: ordered_cols.append(f"{prefix} (TDS)")
                if f"{prefix} (PAID)" in numeric_cols: ordered_cols.append(f"{prefix} (PAID)")
                if f"{prefix} (X-RAY COUNT)" in numeric_cols: ordered_cols.append(f"{prefix} (X-RAY COUNT)")
            df = df[ordered_cols]

            df = apply_sidebar_filters(df, ['X-RAY FACILITY NAME', 'TB UNITS'])
            
            # Month Filters
            st.sidebar.markdown("### 📅 Select Months")
            selected_months = st.sidebar.multiselect("Months to View", prefixes, default=prefixes)
            cols_to_drop = [c for c in numeric_cols if c.split(' (')[0] not in selected_months]
            df = df.drop(columns=cols_to_drop, errors='ignore')
            
            # Merge Logic
            st.markdown("### ⚙️ View Options")
            view_type = st.radio("Display Format:", ["All Branches (Detailed)", "Facility Wise (Merged Totals)"], horizontal=True)
            
            if view_type == "Facility Wise (Merged Totals)" and 'X-RAY FACILITY NAME' in df.columns:
                agg_funcs = {c: 'sum' for c in df.columns if c in numeric_cols and c not in cols_to_drop}
                for c in ['Bank Account No.', 'IFSC Code']:
                    if c in df.columns: agg_funcs[c] = 'first'
                df = df.groupby('X-RAY FACILITY NAME', as_index=False).agg(agg_funcs)
                
            # Net Paid Total
            paid_cols = [c for c in df.columns if '(PAID)' in c and 'TOTAL' in c.upper()]
            final_paid_col = paid_cols[-1] if paid_cols else None
            st.metric(label="Total Net Paid (Filtered)", value=format_inr(df[final_paid_col].sum() if final_paid_col else 0))
            
            st.dataframe(df, use_container_width=True, hide_index=True)

        elif selection == "OTHER EXP.":
            df = apply_sidebar_filters(df, ['ZONE', 'TYPE OF EXPENSE', 'MONTH', 'BUDGET HEAD'])
            kpi_col = 'AMOUNT'
            st.metric(label="Total Other Expenditures", value=format_inr(safe_sum(df[kpi_col]) if kpi_col in df.columns else 0))
            st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("A critical error occurred while parsing the data structure.")
    st.exception(e)
