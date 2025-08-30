import streamlit as st
import pandas as pd
from algorithms import filter_and_sum

st.title("Data Filter and Sum UI")

st.write("""
This app allows you to filter the data from `data.csv` using various parameters and computes the sum of the filtered values.
""")

# --- Helper to load and structure the CSV ---
@st.cache_data
def load_data(csv_path):
    try:
        df = pd.read_csv(csv_path, header=None, low_memory=False)
        # Extract row header data (origin hierarchy)
        row_headers = df.iloc[6:, 0:5].copy()
        row_headers.columns = ['org_zone', 'org_region', 'org_city', 'org_branch', 'org_product']

        # Extract column header data (destination hierarchy)
        col_headers = df.iloc[0:6, 5:].copy()
        col_headers.index = ['ignored', 'type', 'des_zone', 'des_region', 'des_city', 'des_branch']
        col_headers = col_headers.T.reset_index(drop=True)

        return row_headers, col_headers
    except Exception:
        return None, None

csv_path = st.text_input("CSV Path", value="data.csv")
row_headers, col_headers = load_data(csv_path)

if row_headers is None or col_headers is None:
    st.error("Could not load data. Check CSV path or format.")
    st.stop()

# --- Utility for cascading filter ---
def cascade_options(df, filters, column):
    """Filter DataFrame using given filters dict and return sorted unique values of column."""
    filtered_df = df.copy()
    for col, val in filters.items():
        if val:
            filtered_df = filtered_df[filtered_df[col] == val]
    return sorted(filtered_df[column].dropna().unique())

# =========================
# TYPE Selection
# =========================
type_values = sorted(col_headers['type'].dropna().unique())
type_ = st.selectbox(
    "Type", 
    options=[""] + type_values, 
    index=(type_values.index("volume")+1) if "volume" in type_values else 0
)

# =========================
# ORIGIN PARAMETERS
# =========================
st.markdown("**Origin Parameters**")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    org_zone = st.selectbox("Origin Zone", options=[""] + sorted(row_headers['org_zone'].dropna().unique()))
with col2:
    org_region = st.selectbox(
        "Origin Region",
        options=[""] + cascade_options(row_headers, {'org_zone': org_zone}, 'org_region')
    )
with col3:
    org_city = st.selectbox(
        "Origin City",
        options=[""] + cascade_options(row_headers, {'org_zone': org_zone, 'org_region': org_region}, 'org_city')
    )
with col4:
    org_branch = st.selectbox(
        "Origin Branch",
        options=[""] + cascade_options(
            row_headers, {'org_zone': org_zone, 'org_region': org_region, 'org_city': org_city}, 'org_branch'
        )
    )
with col5:
    org_product = st.selectbox(
        "Origin Product",
        options=[""] + cascade_options(
            row_headers, {
                'org_zone': org_zone, 
                'org_region': org_region, 
                'org_city': org_city, 
                'org_branch': org_branch
            }, 'org_product'
        )
    )

# =========================
# DESTINATION PARAMETERS
# =========================
st.markdown("**Destination Parameters**")
col6, col7, col8, col9 = st.columns(4)

with col6:
    des_zone = st.selectbox("Destination Zone", options=[""] + sorted(col_headers['des_zone'].dropna().unique()))
with col7:
    des_region = st.selectbox(
        "Destination Region",
        options=[""] + cascade_options(col_headers, {'des_zone': des_zone}, 'des_region')
    )
with col8:
    des_city = st.selectbox(
        "Destination City",
        options=[""] + cascade_options(col_headers, {'des_zone': des_zone, 'des_region': des_region}, 'des_city')
    )
with col9:
    des_branch = st.selectbox(
        "Destination Branch",
        options=[""] + cascade_options(
            col_headers, {'des_zone': des_zone, 'des_region': des_region, 'des_city': des_city}, 'des_branch'
        )
    )

# =========================
# COMPUTE BUTTON
# =========================
if st.button("Compute Sum"):
    def none_if_empty(s):
        return s if s and s.strip() else None

    result = filter_and_sum(
        org_zone=none_if_empty(org_zone),
        org_region=none_if_empty(org_region),
        org_city=none_if_empty(org_city),
        org_branch=none_if_empty(org_branch),
        org_product=none_if_empty(org_product),
        type_=none_if_empty(type_),
        des_zone=none_if_empty(des_zone),
        des_region=none_if_empty(des_region),
        des_city=none_if_empty(des_city),
        des_branch=none_if_empty(des_branch),
        csv_path=csv_path
    )
    st.markdown("### Result")
    st.success(f"Sum of filtered values: {result}")