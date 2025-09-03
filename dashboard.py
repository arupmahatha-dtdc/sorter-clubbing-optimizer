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
        df = pd.read_csv(csv_path, header=None, low_memory=False, skiprows=1)  # Skip first row
        # Extract row header data (origin hierarchy) - now 7 levels: zone, region, city, branch_code, branch_name, service_type, product
        row_headers = df.iloc[6:, 0:7].copy()  # Skip 6 header rows, get first 7 columns
        row_headers.columns = [
            'org_zone', 'org_region', 'org_city', 
            'org_branch_code', 'org_branch_name', 
            'service_type', 'org_product'
        ]

        # Extract column header data (destination hierarchy) - now 6 levels: type, zone, region, city, branch_code, branch_name
        col_headers = df.iloc[0:6, 7:].copy()  # Get 6 header rows, start from column 7 (after product column)
        col_headers.index = ['type', 'des_zone', 'des_region', 'des_city', 'des_branch_code', 'des_branch_name']
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
# TYPE & SERVICE TYPE
# =========================
colA, colB = st.columns(2)

with colA:
    type_values = sorted(col_headers['type'].dropna().unique())
    type_ = st.selectbox("Type", options=[""] + type_values)

with colB:
    service_type_values = sorted(row_headers['service_type'].dropna().unique())
    service_type = st.selectbox("Service Type", options=[""] + service_type_values)

# =========================
# ORIGIN PARAMETERS
# =========================
st.markdown("**Origin Parameters**")
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1.5, 1.5])

with col1:
    zone_options = sorted(row_headers['org_zone'].dropna().unique())
    org_zone = st.selectbox("Origin Zone", options=[""] + zone_options)

with col2:
    def get_regions_for_zone():
        filtered_df = row_headers.copy()
        if org_zone:
            filtered_df = filtered_df[filtered_df['org_zone'] == org_zone]
        regions = filtered_df['org_region'].dropna().unique()
        return sorted([r for r in regions if r])
    
    region_options = get_regions_for_zone()
    org_region = st.selectbox("Origin Region", options=[""] + region_options)

with col3:
    def get_cities_for_selection():
        filtered_df = row_headers.copy()
        if org_zone:
            filtered_df = filtered_df[filtered_df['org_zone'] == org_zone]
        if org_region:
            filtered_df = filtered_df[filtered_df['org_region'] == org_region]
        cities = filtered_df['org_city'].dropna().unique()
        return sorted([c for c in cities if c])
    
    city_options = get_cities_for_selection()
    org_city = st.selectbox("Origin City", options=[""] + city_options)

with col4:
    def get_branch_codes_for_selection():
        filtered_df = row_headers.copy()
        if org_zone:
            filtered_df = filtered_df[filtered_df['org_zone'] == org_zone]
        if org_region:
            filtered_df = filtered_df[filtered_df['org_region'] == org_region]
        if org_city:
            filtered_df = filtered_df[filtered_df['org_city'] == org_city]
        
        branch_data = filtered_df[['org_branch_code', 'org_branch_name']].dropna().drop_duplicates()
        display_options = []
        code_mapping = {}
        for _, row in branch_data.iterrows():
            code = row['org_branch_code']
            name = row['org_branch_name']
            display_text = f"{code} - {name}"
            display_options.append(display_text)
            code_mapping[display_text] = code
        
        return sorted(display_options), code_mapping
    
    branch_display_options, branch_code_mapping = get_branch_codes_for_selection()
    org_branch_display = st.selectbox("Origin Branch", options=[""] + branch_display_options, key="org_branch_display")
    org_branch_code = branch_code_mapping.get(org_branch_display) if org_branch_display else None

with col5:
    def get_products_for_selection():
        filtered_df = row_headers.copy()
        
        if service_type:
            filtered_df = filtered_df[filtered_df['service_type'] == service_type]
        if org_zone:
            filtered_df = filtered_df[filtered_df['org_zone'] == org_zone]
        if org_region:
            filtered_df = filtered_df[filtered_df['org_region'] == org_region]
        if org_city:
            filtered_df = filtered_df[filtered_df['org_city'] == org_city]
        if org_branch_code:
            filtered_df = filtered_df[filtered_df['org_branch_code'] == org_branch_code]
        
        products = filtered_df['org_product'].dropna().unique()
        return sorted([p for p in products if p])
    
    product_options = get_products_for_selection()
    org_product = st.selectbox("Origin Product", options=[""] + product_options)

# =========================
# DESTINATION PARAMETERS
# =========================
st.markdown("**Destination Parameters**")
col6, col7, col8, col9 = st.columns([1, 1, 1, 1.5])

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
    def get_des_branch_codes_for_selection():
        filtered_df = col_headers.copy()
        if des_zone:
            filtered_df = filtered_df[filtered_df['des_zone'] == des_zone]
        if des_region:
            filtered_df = filtered_df[filtered_df['des_region'] == des_region]
        if des_city:
            filtered_df = filtered_df[filtered_df['des_city'] == des_city]
        
        branch_data = filtered_df[['des_branch_code', 'des_branch_name']].dropna().drop_duplicates()
        display_options = []
        code_mapping = {}
        for _, row in branch_data.iterrows():
            code = row['des_branch_code']
            name = row['des_branch_name']
            display_text = f"{code} - {name}"
            display_options.append(display_text)
            code_mapping[display_text] = code
        
        return sorted(display_options), code_mapping
    
    des_branch_display_options, des_branch_code_mapping = get_des_branch_codes_for_selection()
    des_branch_display = st.selectbox("Destination Branch", options=[""] + des_branch_display_options, key="des_branch_display")
    des_branch_code = des_branch_code_mapping.get(des_branch_display) if des_branch_display else None

# =========================
# COMPUTE BUTTON
# =========================
if st.button("Compute Sum"):
    def none_if_empty(s):
        return s if s and s.strip() else None

    result = filter_and_sum(
        type_=none_if_empty(type_),
        service_type=none_if_empty(service_type),
        org_zone=none_if_empty(org_zone),
        org_region=none_if_empty(org_region),
        org_city=none_if_empty(org_city),
        org_branch_code=none_if_empty(org_branch_code),
        org_product=none_if_empty(org_product),
        des_zone=none_if_empty(des_zone),
        des_region=none_if_empty(des_region),
        des_city=none_if_empty(des_city),
        des_branch_code=none_if_empty(des_branch_code),
        csv_path=csv_path
    )
    st.markdown("### Result")
    st.success(f"Sum of filtered values: {result}")