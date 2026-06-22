import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# -----------------------------------------------------------------------------
# 1. GLOBAL CONFIGURATION & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NTEP Finance Dashboard",
    page_icon="🏥",
    layout="wide"
)

# Adaptive Power BI 3D CSS
st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1), 0 1px 3px rgba(0,0,0,0.08);
        border-top: 5px solid #E31837; /* NTEP Red */
        transition: transform 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.2);
    }
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

PUBLISHED_LINK = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT_ai_LwZQK-DFfgojQ4ZUJiXKt8ikzzGEcnoLQN8hcpKfHxNtzkFEqcPn5jJC07QGiXh8_kLuexZfo/pubhtml"
OTHER_EXP_LINK = "https://docs.google.com/spreadsheets/d/1vhQRXdUGfj4OL3y5heGQsGJeiukXhtBFX7lFzhHMaRE/export?format=csv&gid=0"

SHEETS = {
    "ALL SPUTUM": "0",
    "POL EXP.": "57196367",
    "DRUG TRAN.": "1226029008",  
    "X-RAY": "721930106",
    "OTHER EXP.": "NEW_LINK",
    "FILE TRACKER": "1062217994" 
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
    clean_series = series.astype(str).str.replace(r'[^\d.-]', '', regex=True)
    return pd.to_numeric(clean_series, errors='coerce').fillna(0).sum()

def apply_sidebar_filters(df, filter_columns):
    st.sidebar.markdown("### 🔍 Filter Data")
    for col in filter_columns:
        if col in df.columns:
            options = [str(x) for x in df[col].unique() if str(x).strip() not in ['None', 'nan', '', 'NaN', '<NA>']]
            options.sort()
            selected = st.sidebar.multiselect(f"Select {col}", options)
            if selected:
                df = df[df[col].astype(str).isin(selected)]
    return df

def clean_dataframe_for_display(df):
    cleaned = df.copy()
    cleaned = cleaned.fillna("") 
    for col in cleaned.columns:
        # Check if column contains floats ending in .0 and format to int, otherwise pure string
        if cleaned[col].dtype == float:
            cleaned[col] = cleaned[col].apply(lambda x: f"{int(x)}" if x.is_integer() else f"{x}")
        cleaned[col] = cleaned[col].astype(str).replace(["nan", "NaN", "None", "<NA>", "NaT", "0.0"], "")
    return cleaned

def clean_column_names(columns):
    cleaned_cols = []
    for i, col in enumerate(columns):
        col_str = str(col).strip()
        if col_str.lower() in ['nan', 'none', '<na>', 'nat', '']:
            cleaned_cols.append(f"Blank_Col_{i}")
        else:
            cleaned_cols.append(col_str)
    return cleaned_cols

@st.cache_data(ttl=120) 
def load_smart_data(gid, module_name):
    if module_name == "OTHER EXP.":
        csv_url = OTHER_EXP_LINK
    else:
        base_url = PUBLISHED_LINK.split('/pub')[0] 
        csv_url = f"{base_url}/pub?gid={gid}&single=true&output=csv"
    
    try:
        raw_df = pd.read_csv(csv_url, header=None)
        
        if module_name == "X-RAY":
            gross_idx = raw_df[raw_df.apply(lambda r: r.astype(str).str.contains('GROSS', case=False).any(), axis=1)].index
            if len(gross_idx) > 0:
                header_row_idx = gross_idx[0]
                month_row = raw_df.iloc[header_row_idx - 1].replace({'None': np.nan, '': np.nan, pd.NA: np.nan}).ffill().fillna('')
                sub_row = raw_df.iloc[header_row_idx].fillna('')
                
                new_cols = []
                for m, s in zip(month_row, sub_row):
                    m_str, s_str = str(m).strip(), str(s).strip()
                    if m_str and s_str and m_str != s_str and s_str.upper() in ['GROSS', 'TDS', 'PAID']:
                        new_cols.append(f"{m_str} ({s_str})")
                    else:
                        new_cols.append(s_str if s_str else m_str)
                
                raw_df.columns = clean_column_names(new_cols)
                df = raw_df.iloc[header_row_idx + 1:].copy()
                if df.iloc[0].astype(str).str.strip().isin(['A', 'B', 'C']).any():
                    df = df.iloc[1:].copy()
                
                df = df.dropna(how='all')
                return df.reset_index(drop=True)
                
        else:
            header_idx = raw_df[raw_df.apply(lambda r: r.astype(str).str.contains('(?i)SR\.? NO\.?|TB UNIT|ZONE|Name of Employee|INWARD NO|FILE NAME', regex=True).any(), axis=1)].index
            if len(header_idx) > 0:
                idx = header_idx[0]
                raw_columns = raw_df.iloc[idx].values
                raw_df.columns = clean_column_names(raw_columns)
                df = raw_df.iloc[idx + 1:].copy()
                
                if df.iloc[0].astype(str).str.strip().isin(['A', 'B', 'C', '1', '2', '3']).sum() > 3:
                     df = df.iloc[1:].copy()
                
                df = df.dropna(how='all')
                return df.reset_index(drop=True)

        return raw_df 
    except Exception as e:
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_column_width=True)

st.sidebar.title("NTEP Navigation")
st.sidebar.markdown("---")
selection = st.sidebar.radio("Select Module:", list(SHEETS.keys()))

# -----------------------------------------------------------------------------
# 4. MAIN HEADER 
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 10])
with col1:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=80)
with col2:
    st.title("NTEP Finance Dashboard")
    st.subheader(f"📂 {selection} Module")
st.markdown("---")

# -----------------------------------------------------------------------------
# 5. TAB LOGIC & RENDERING
# -----------------------------------------------------------------------------
try:
    df = load_smart_data(SHEETS[selection], selection)
    
    if not df.empty:
        # CLEANUP
        if len(df.columns) > 0 and df.columns[0] != 'Unnamed: 0':
            identifier_col = None
            if selection == "ALL SPUTUM": identifier_col = 'ASHA/TRANSPORTER NAME'
            elif selection in ["POL EXP.", "DRUG TRAN."]: identifier_col = 'Name of Employee'
            elif selection == "X-RAY": identifier_col = 'X-RAY FACILITY NAME'
            elif selection == "OTHER EXP.": identifier_col = 'TYPE OF EXPENSE'
            elif selection == "FILE TRACKER": identifier_col = 'FILE NAME'

            if identifier_col and identifier_col in df.columns:
                df[identifier_col] = df[identifier_col].astype(str).replace(r'^\s*$', np.nan, regex=True).replace(['None', 'nan', 'NaN', '<NA>'], np.nan)
                df = df.dropna(subset=[identifier_col])

            for col in df.columns[:5]:
                df = df[~df[col].astype(str).str.strip().str.upper().isin(['TOTAL', 'GRAND TOTAL'])]
            df = df.loc[:, ~df.columns.str.startswith('Blank_Col_')]

        # --- ALL SPUTUM TAB ---
        if selection == "ALL SPUTUM":
            df = apply_sidebar_filters(df, ['ASHA/TRANSPORTER NAME', 'TU/PHI', 'TYPE OF PAYMENT'])
            
            month_cols = [c for c in df.columns if any(m in str(c).upper() for m in ['DEC', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN']) and 'AMOUNT' not in str(c).upper()]
            if month_cols:
                st.sidebar.markdown("### 📅 Select Months")
                selected_months = st.sidebar.multiselect("Months to View", month_cols, default=month_cols)
                
                # --- DYNAMIC MATH ENGINE ---
                kpi_col = 'AMOUNT Rs.' if 'AMOUNT Rs.' in df.columns else ('AMOUNT Rs' if 'AMOUNT Rs' in df.columns else None)
                tot_col = 'TOTAL' if 'TOTAL' in df.columns else None

                if kpi_col and tot_col:
                    # 1. Clean data for calculation
                    for c in month_cols:
                        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
                    temp_tot = pd.to_numeric(df[tot_col].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
                    temp_amt = pd.to_numeric(df[kpi_col].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)

                    # 2. Derive specific multiplier rates (Amount / Total)
                    rates = np.where(temp_tot != 0, temp_amt / temp_tot, 0)

                    # 3. Recalculate based ONLY on user's selected months
                    new_counts = df[selected_months].sum(axis=1) if selected_months else 0
                    df[tot_col] = new_counts
                    df[kpi_col] = new_counts * rates

                # 4. Hide unselected months
                df = df.drop(columns=[c for c in month_cols if c not in selected_months], errors='ignore')

            # Render KPI
            kpi_col_name = 'AMOUNT Rs.' if 'AMOUNT Rs.' in df.columns else ('AMOUNT Rs' if 'AMOUNT Rs' in df.columns else None)
            total_val = safe_sum(df[kpi_col_name]) if kpi_col_name else 0
            aasha_val = safe_sum(df[df['TYPE OF PAYMENT'].astype(str).str.upper().str.contains('AASHA', na=False)][kpi_col_name]) if kpi_col_name and 'TYPE OF PAYMENT' in df.columns else 0
            dmc_val = safe_sum(df[df['TYPE OF PAYMENT'].astype(str).str.upper().str.contains('DMC', na=False)][kpi_col_name]) if kpi_col_name and 'TYPE OF PAYMENT' in df.columns else 0

            c1, c2, c3 = st.columns(3)
            c1.metric(label="Grand Total (Rs.)", value=format_inr(total_val))
            c2.metric(label="Total AASHA", value=format_inr(aasha_val))
            c3.metric(label="Total DMC", value=format_inr(dmc_val))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if aasha_val > 0 or dmc_val > 0:
                fig = px.pie(values=[aasha_val, dmc_val], names=['AASHA', 'DMC'], hole=0.5, 
                             color_discrete_sequence=['#E31837', '#FFC72C'], title="Expense Distribution")
                st.plotly_chart(fig, use_container_width=True, theme="streamlit")
            
            st.dataframe(clean_dataframe_for_display(df), use_container_width=True, hide_index=True)

        # --- POL EXP TAB ---
        elif selection == "POL EXP.":
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            
            kpi_col = 'Total' if 'Total' in df.columns else [c for c in df.columns if 'TOTAL' in str(c).upper()][-1]
            st.metric(label="Total POL Expenditure (Selected Month)", value=format_inr(safe_sum(df[kpi_col])))
            
            base_cols = [c for c in df.columns if c in ['Sr. No.', 'Name of Employee', 'Bank  A/c No.', 'IFSC Code', 'Designation', 'Vehicle No.', kpi_col]]
            detail_cols = [c for c in df.columns if c not in base_cols and 'Unnamed' not in str(c)]
            
            st.dataframe(clean_dataframe_for_display(df[base_cols]), use_container_width=True, hide_index=True)
            
            with st.expander("➕ View Detailed Expense Breakdown (VP, VM, Mis, Training...)"):
                st.dataframe(clean_dataframe_for_display(df[['Name of Employee'] + detail_cols]), use_container_width=True, hide_index=True)

        # --- DRUG TRAN TAB ---
        elif selection == "DRUG TRAN.":
            df = apply_sidebar_filters(df, ['Name of Employee', 'Designation'])
            
            actual_month_cols = [c for c in df.columns if c.upper() in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUNE', 'JULY', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC']]
            if actual_month_cols:
                st.sidebar.markdown("### 📅 Select Months")
                selected_months = st.sidebar.multiselect("Months to View", actual_month_cols, default=actual_month_cols)
                
                # Dynamic Math for DRUG TRAN
                kpi_col = 'TOTAL' if 'TOTAL' in df.columns else None
                if kpi_col:
                    for c in actual_month_cols:
                        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
                    df[kpi_col] = df[selected_months].sum(axis=1) if selected_months else 0

                df = df.drop(columns=[c for c in actual_month_cols if c not in selected_months], errors='ignore')

            kpi_col_name = 'TOTAL' if 'TOTAL' in df.columns else None
            st.metric(label="Total Drug Trans. Expense", value=format_inr(safe_sum(df[kpi_col_name]) if kpi_col_name in df.columns else 0))
            st.dataframe(clean_dataframe_for_display(df), use_container_width=True, hide_index=True)

        # --- X-RAY TAB ---
        elif selection == "X-RAY":
            numeric_cols = [c for c in df.columns if '(GROSS)' in c or '(TDS)' in c or '(PAID)' in c]
            for c in numeric_cols:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                
            generated_cols = []
            for c in list(numeric_cols):
                if '(GROSS)' in c:
                    prefix = c.split(' (')[0]
                    count_col = f"{prefix} (X-RAY COUNT)"
                    df[count_col] = (df[c] / 200).astype(int)
                    generated_cols.append(count_col)
            numeric_cols.extend(generated_cols)

            df = apply_sidebar_filters(df, ['X-RAY FACILITY NAME', 'TB UNITS'])
            
            prefixes = list(dict.fromkeys([c.split(' (')[0] for c in numeric_cols]))
            st.sidebar.markdown("### 📅 Select Months")
            selected_months = st.sidebar.multiselect("Months to View", prefixes, default=prefixes)
            cols_to_drop = [c for c in numeric_cols if c.split(' (')[0] not in selected_months]
            df = df.drop(columns=cols_to_drop, errors='ignore')
            
            view_type = st.radio("Display Format:", ["All Branches (Detailed)", "Facility Wise (Merged Totals)"], horizontal=True)
            
            if view_type == "Facility Wise (Merged Totals)" and 'X-RAY FACILITY NAME' in df.columns:
                agg_funcs = {c: 'sum' for c in df.columns if c in numeric_cols and c not in cols_to_drop}
                for c in ['Bank Account No.', 'IFSC Code']:
                    if c in df.columns: agg_funcs[c] = 'first'
                df = df.groupby('X-RAY FACILITY NAME', as_index=False).agg(agg_funcs)
                
            # Dynamic Totaling for X-RAY View Table
            gross_cols = [c for c in df.columns if '(GROSS)' in c and 'TOTAL' not in c.upper()]
            tds_cols = [c for c in df.columns if '(TDS)' in c and 'TOTAL' not in c.upper()]
            paid_cols = [c for c in df.columns if '(PAID)' in c and 'TOTAL' not in c.upper()]
            count_cols = [c for c in df.columns if '(X-RAY COUNT)' in c and 'TOTAL' not in c.upper()]
            
            if 'TOTAL (GROSS)' in df.columns: df['TOTAL (GROSS)'] = df[gross_cols].sum(axis=1) if gross_cols else 0
            if 'TOTAL (TDS)' in df.columns: df['TOTAL (TDS)'] = df[tds_cols].sum(axis=1) if tds_cols else 0
            if 'TOTAL (PAID)' in df.columns: df['TOTAL (PAID)'] = df[paid_cols].sum(axis=1) if paid_cols else 0
            if 'TOTAL (X-RAY COUNT)' in df.columns: df['TOTAL (X-RAY COUNT)'] = df[count_cols].sum(axis=1) if count_cols else 0

            static_cols = [c for c in df.columns if c not in numeric_cols]
            count_only_cols = [c for c in df.columns if '(X-RAY COUNT)' in c and 'TOTAL' not in c.upper()]
            
            tot_count = df[count_only_cols].sum().sum() if count_only_cols else 0
            st.metric(label="Total X-Rays Performed", value=int(tot_count))
            
            simplified_view_cols = static_cols + count_only_cols
            st.dataframe(clean_dataframe_for_display(df[simplified_view_cols]), use_container_width=True, hide_index=True)

        # --- OTHER EXP TAB ---
        elif selection == "OTHER EXP.":
            df = apply_sidebar_filters(df, ['ZONE', 'TB UNIT', 'MONTH OF EXPENSE', 'TYPE OF EXPENSE', 'BUDGET HEAD', 'FILE STATUS'])
            
            kpi_col = 'AMOUNT' if 'AMOUNT' in df.columns else None
            total_val = safe_sum(df[kpi_col]) if kpi_col else 0
            total_claims = len(df[df['AMOUNT'].notna() & (df['AMOUNT'].astype(str).str.strip() != '') & (df['AMOUNT'].astype(str).str.strip() != 'nan')]) if kpi_col else 0
            
            c1, c2 = st.columns(2)
            c1.metric(label="Total Other Expenditures", value=format_inr(total_val))
            c2.metric(label="Total Number of Claims", value=total_claims)
            
            st.dataframe(clean_dataframe_for_display(df), use_container_width=True, hide_index=True)

        # --- FILE TRACKER ---
        elif selection == "FILE TRACKER":
            if 'FILE NAME' in df.columns:
                df['FILE NAME'] = df['FILE NAME'].astype(str).replace(r'^\s*$', np.nan, regex=True).replace(['None', 'nan', 'NaN', '<NA>'], np.nan)
                df = df.dropna(subset=['FILE NAME'])

            df = apply_sidebar_filters(df, ['FILE NAME', 'STATUS'])
            
            total_files = len(df)
            submitted_files = len(df[df['STATUS'].astype(str).str.upper().str.contains("SUBMITTED", na=False)])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Files TRACKED", total_files)
            c2.metric("Files SUBMITTED", submitted_files)
            c3.metric("Pending / Processing", total_files - submitted_files)
            
            st.dataframe(clean_dataframe_for_display(df), use_container_width=True, hide_index=True)

except Exception as e:
    st.error("A critical error occurred while parsing the data structure.")
    st.exception(e)
