# Office Location & Summary Dashboard

An interactive dashboard that displays office locations on a map and provides summary data analysis for logistics operations.

## Features

- 🗺️ **Interactive Map**: View all office locations across India with color-coded zones
- 📊 **Data Selection**: Choose between Volume or Billed Weight data
- 🚚 **Transport Mode**: Select Air or Ground transport data
- 📍 **Office Selection**: Pick specific offices to view detailed summary data
- 📈 **Visual Analytics**: Charts and metrics showing origin vs destination data
- 🎨 **Zone Color Coding**: Different colors for North, South, East, and West zones

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit application:
```bash
streamlit run geoplot.py
```

2. Open your web browser and navigate to the URL shown in the terminal (usually http://localhost:8501)

3. Use the sidebar controls to:
   - Select data type (Volume or Billed Wt)
   - Choose transport mode (Air or Ground)
   - Pick an office code to analyze

4. Interact with the map:
   - Click on markers to see office details
   - Hover over markers for quick office information
   - View color-coded zones (Red=North, Blue=South, Green=East, Orange=West)

## Data Files Required

The application requires these CSV files in the same directory:
- `office_location.csv` - Office locations with coordinates
- `org_summary.csv` - Origin summary data
- `des_summary.csv` - Destination summary data

## Features

- **Real-time Data Filtering**: Instantly see data changes when selecting different options
- **Responsive Design**: Works on different screen sizes
- **Interactive Elements**: Clickable map markers with detailed popups
- **Data Visualization**: Bar charts and metrics for easy data interpretation
- **Error Handling**: Graceful handling of missing or invalid data

## Technical Details

- Built with Streamlit for the web interface
- Uses Folium for interactive mapping
- Plotly for data visualization
- Pandas for data manipulation
- Responsive layout with sidebar controls and main content area
