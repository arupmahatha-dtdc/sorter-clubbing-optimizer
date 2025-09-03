import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# -------------------- Data Loading --------------------
def load_data():
    """Load all required data files"""
    try:
        branches_df = pd.read_csv('branch_locations.csv')
        org_summary = pd.read_csv('org_summary.csv')
        des_summary = pd.read_csv('des_summary.csv')
        return branches_df, org_summary, des_summary
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None

# -------------------- Branch Search --------------------
def find_branch_coordinates(branches_df, branch_code):
    """Find coordinates for a given branch code"""
    branch_data = branches_df[branches_df['office'] == branch_code]
    if not branch_data.empty:
        try:
            lat = float(branch_data.iloc[0]['lat'])
            lon = float(branch_data.iloc[0]['lon'])
            if pd.notna(lat) and pd.notna(lon):
                return lat, lon
        except (KeyError, ValueError, TypeError):
            pass
    return None

# -------------------- Map Creation --------------------
def create_interactive_map(branches_df, org_summary, des_summary, data_type=None, service_type=None, selected_branch=None):
    """Create an interactive map with branch locations and clickable markers"""
    
    # Determine map center based on selected branch or default to India center
    if selected_branch:
        branch_coords = find_branch_coordinates(branches_df, selected_branch)
        if branch_coords:
            center_lat, center_lon = branch_coords
            zoom_level = 10  # Closer zoom for specific branch
        else:
            center_lat, center_lon = 23.5937, 78.9629  # Center of India
            zoom_level = 5
    else:
        center_lat, center_lon = 23.5937, 78.9629  # Center of India
        zoom_level = 5
    
    # Create map with determined center
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles='OpenStreetMap',
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True,
        doubleClickZoom=True
    )

    # Marker color by zone
    zone_colors = {
        'NORTH': 'red',
        'SOUTH': 'blue',
        'EAST': 'green',
        'WEST': 'orange'
    }

    # Add branch markers
    for idx, row in branches_df.iterrows():
        try:
            lat = float(row['lat'])
            lon = float(row['lon'])
        except (KeyError, ValueError, TypeError):
            continue

        if pd.notna(lat) and pd.notna(lon):
            # Filter summary data for this branch with optional type/service filters
            org_filter = (org_summary['org_branch_code'] == row['office'])
            if data_type is not None:
                org_filter = org_filter & (org_summary['type'] == data_type)
            if service_type is not None:
                org_filter = org_filter & (org_summary['service_type'] == service_type)
            org_data = org_summary[org_filter]

            des_filter = (des_summary['des_branch_code'] == row['office'])
            if data_type is not None:
                des_filter = des_filter & (des_summary['type'] == data_type)
            if service_type is not None:
                des_filter = des_filter & (des_summary['service_type'] == service_type)
            des_data = des_summary[des_filter]

            org_sum = org_data['sum'].sum() if not org_data.empty else 0
            des_sum = des_data['sum'].sum() if not des_data.empty else 0

            # Popup content
            type_label = data_type if data_type is not None else "All Types"
            service_label = service_type if service_type is not None else "All Services"
            popup_content = f"""
            <div style="font-family: Arial, sans-serif; min-width: 250px;">
                <h3 style="color: #1f77b4; margin: 0 0 10px 0;">{row.get('name', '')}</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                    <tr><td><strong>Branch Code:</strong></td><td>{row.get('office', '')}</td></tr>
                    <tr><td><strong>City:</strong></td><td>{row.get('city', '')}</td></tr>
                    <tr><td><strong>Region:</strong></td><td>{row.get('region', '')}</td></tr>
                    <tr><td><strong>Zone:</strong></td><td>{row.get('zone', '')}</td></tr>
                </table>
                <hr style="margin: 10px 0;">
                <h4 style="color: #ff7f0e; margin: 10px 0;">Summary Data ({type_label} - {service_label})</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: #f0f0f0;">
                        <td><strong>Origin:</strong></td>
                        <td style="text-align: right; font-weight: bold;">{org_sum:,.0f}</td>
                    </tr>
                    <tr style="background-color: #f0f0f0;">
                        <td><strong>Destination:</strong></td>
                        <td style="text-align: right; font-weight: bold;">{des_sum:,.0f}</td>
                    </tr>
                    <tr style="background-color: #e0e0e0;">
                        <td><strong>Total:</strong></td>
                        <td style="text-align: right; font-weight: bold; color: #1f77b4;">{org_sum + des_sum:,.0f}</td>
                    </tr>
                </table>
            </div>
            """

            color = zone_colors.get(str(row.get('zone', '')).upper(), 'gray')
            
            # Make selected branch marker larger and highlighted
            is_selected = selected_branch and row['office'] == selected_branch
            marker_radius = 12 if is_selected else 6
            marker_color = 'purple' if is_selected else color
            marker_weight = 3 if is_selected else 1

            # Add CircleMarker
            folium.CircleMarker(
                location=[lat, lon],
                radius=marker_radius,
                color=marker_color,
                weight=marker_weight,
                fill=True,
                fill_color=marker_color,
                fill_opacity=0.8,
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{row.get('name', '')} ({row.get('office', '')}) - {row.get('city', '')}"
            ).add_to(m)

    # Add optional tile layers
    folium.TileLayer('CartoDB positron', name='Light Theme').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Theme').add_to(m)

    folium.LayerControl().add_to(m)

    return m

# -------------------- Main App --------------------
def main():
    st.set_page_config(
        page_title="Branch Location Map Dashboard",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar controls
    st.sidebar.title("🛠️ Controls")

    # Load data
    branches_df, org_summary, des_summary = load_data()
    if branches_df is None or org_summary is None or des_summary is None:
        st.error("Failed to load data. Please check your data files.")
        return

    # Build filter options
    type_values = pd.unique(pd.concat([
        org_summary['type'].dropna(),
        des_summary['type'].dropna()
    ]))
    type_options = ["All Types"] + sorted(map(str, type_values))
    data_type = st.sidebar.selectbox("Data Type:", type_options, index=0)
    if data_type == "All Types":
        data_type = None

    service_values = pd.unique(pd.concat([
        org_summary['service_type'].dropna(),
        des_summary['service_type'].dropna()
    ]))
    service_options = ["All Services"] + sorted(map(str, service_values))
    service_type = st.sidebar.selectbox("Service Type:", service_options, index=0)
    if service_type == "All Services":
        service_type = None
    
    # Branch search dropdown
    branch_options = ["All Branches"] + branches_df['office'].tolist()
    selected_branch = st.sidebar.selectbox(
        "Select Branch to Center Map:",
        options=branch_options,
        index=0,
        help="Choose 'All Branches' to view the entire map, or select a specific branch to center and zoom on it"
    )
    if selected_branch == "All Branches":
        selected_branch = None

    # Sidebar instructions
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🗺️ Map Controls:**")
    st.sidebar.markdown("""
    - **Zoom:** Mouse wheel or +/- buttons  
    - **Pan:** Click and drag  
    - **Double-click:** Zoom in
    """)

    st.sidebar.markdown("**📍 Branch Markers:**")
    st.sidebar.markdown("""
    - **Red:** North Zone  
    - **Blue:** South Zone  
    - **Green:** East Zone  
    - **Orange:** West Zone  
    - **Purple:** Selected Branch (larger marker)
    """)

    st.sidebar.markdown("**📊 Data Display:**")
    st.sidebar.markdown("""
    - Click any marker to see branch details  
    - Summary data updates with type/service selection  
    - Origin vs Destination comparison  
    - Use search to quickly navigate to specific branches
    """)

    # Main page title
    st.title("🗺️ Branch Map Dashboard")
    st.markdown("---")

    # Create and display interactive map
    map_obj = create_interactive_map(branches_df, org_summary, des_summary, data_type, service_type, selected_branch)
    folium_static(map_obj, width=1200, height=700)

# -------------------- Run App --------------------
if __name__ == "__main__":
    main()