import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# -------------------- Data Loading --------------------
def load_data():
    """Load all required data files"""
    try:
        offices_df = pd.read_csv('office_location.csv')
        org_summary = pd.read_csv('org_summary.csv')
        des_summary = pd.read_csv('des_summary.csv')
        return offices_df, org_summary, des_summary
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None

# -------------------- Map Creation --------------------
def create_interactive_map(offices_df, org_summary, des_summary, data_type, mode):
    """Create an interactive map with office locations and clickable markers"""
    m = folium.Map(
        location=[23.5937, 78.9629],  # Center of India
        zoom_start=5,
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

    # Add office markers
    for idx, row in offices_df.iterrows():
        try:
            lat = float(row['lat'])
            lon = float(row['lon'])
        except (KeyError, ValueError, TypeError):
            continue
        if pd.notna(lat) and pd.notna(lon):
            # Filter summary data for this office
            org_data = org_summary[
                (org_summary['org_branch_code'] == row['office']) &
                (org_summary['type'] == data_type) &
                (org_summary['mode'] == mode)
            ]
            des_data = des_summary[
                (des_summary['des_branch_code'] == row['office']) &
                (des_summary['type'] == data_type) &
                (des_summary['mode'] == mode)
            ]

            org_sum = org_data['sum'].sum() if not org_data.empty else 0
            des_sum = des_data['sum'].sum() if not des_data.empty else 0

            # Popup content
            popup_content = f"""
            <div style="font-family: Arial, sans-serif; min-width: 250px;">
                <h3 style="color: #1f77b4; margin: 0 0 10px 0;">{row.get('name', '')}</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                    <tr><td><strong>Office Code:</strong></td><td>{row.get('office', '')}</td></tr>
                    <tr><td><strong>City:</strong></td><td>{row.get('city', '')}</td></tr>
                    <tr><td><strong>Region:</strong></td><td>{row.get('region', '')}</td></tr>
                    <tr><td><strong>Zone:</strong></td><td>{row.get('zone', '')}</td></tr>
                </table>
                <hr style="margin: 10px 0;">
                <h4 style="color: #ff7f0e; margin: 10px 0;">Summary Data ({data_type} - {mode})</h4>
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

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{row.get('name', '')} ({row.get('office', '')}) - {row.get('city', '')}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)

    # Extra tile layers for theme switching
    folium.TileLayer('CartoDB positron', name='Light Theme').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Theme').add_to(m)

    # Layer control
    folium.LayerControl().add_to(m)

    return m

# -------------------- Main App --------------------
def main():
    st.set_page_config(
        page_title="Office Location Map Dashboard",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar controls
    st.sidebar.title("🛠️ Controls")

    data_type = st.sidebar.selectbox(
        "Data Type:",
        ["Volume", "Billed Wt"],
        index=0
    )

    mode = st.sidebar.selectbox(
        "Mode:",
        ["Air", "Ground"],
        index=0
    )

    # Sidebar instructions
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🗺️ Map Controls:**")
    st.sidebar.markdown("""
    - **Zoom:** Mouse wheel or +/- buttons  
    - **Pan:** Click and drag  
    - **Double-click:** Zoom in
    """)

    st.sidebar.markdown("**📍 Office Markers:**")
    st.sidebar.markdown("""
    - **Red:** North Zone  
    - **Blue:** South Zone  
    - **Green:** East Zone  
    - **Orange:** West Zone
    """)

    st.sidebar.markdown("**📊 Data Display:**")
    st.sidebar.markdown("""
    - Click any marker to see office details  
    - Summary data updates with type/mode selection  
    - Origin vs Destination comparison
    """)

    # Main page title
    st.title("🗺️ Office Map Dashboard")
    st.markdown("---")

    # Load data
    offices_df, org_summary, des_summary = load_data()
    if offices_df is None or org_summary is None or des_summary is None:
        st.error("Failed to load data. Please check your data files.")
        return

    # Create and display the interactive map
    map_obj = create_interactive_map(offices_df, org_summary, des_summary, data_type, mode)
    folium_static(map_obj, width=1200, height=700)

# -------------------- Run App --------------------
if __name__ == "__main__":
    main()