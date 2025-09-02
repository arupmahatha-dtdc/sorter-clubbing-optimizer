import streamlit as st
import pandas as pd
import json
import os
from PIL import Image

# -----------------------------
# Configuration
# -----------------------------
BAGS_FOLDER = "bags"
TYPES = ["Volume", "Billed_Wt"]
MODES = ["Air", "Surface"]

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("Branch Elbow Analysis Viewer")

# Select Type and Mode
selected_type = st.selectbox("Select Type", TYPES)
selected_mode = st.selectbox("Select Mode", MODES)

# Construct CSV folder name
csv_filename = f"{selected_type}_{selected_mode}_percentage"
csv_folder = os.path.join(BAGS_FOLDER, csv_filename)

# Check if folder exists
if not os.path.exists(csv_folder):
    st.error(f"No data found for {csv_filename}")
else:
    # Load DataFrame and JSON
    df_csv = os.path.join(csv_folder, "optimal_branches.csv")
    df = pd.read_csv(df_csv)
    
    json_file = os.path.join(csv_folder, "optimal_branches.json")
    with open(json_file, "r") as f:
        branch_json = json.load(f)
    
    # Select Region
    regions = df["Region"].tolist()
    selected_region = st.selectbox("Select Region", regions)
    
    # Show row info
    row_info = df[df["Region"] == selected_region]
    st.subheader("Optimal Branches Info")
    st.write(row_info)
    
    # Show branch names
    st.subheader("Optimal Branch Names")
    region_branches = branch_json[selected_region]
    st.write(region_branches)
    
    # Show plot
    st.subheader("Elbow Plot")
    plot_file = os.path.join(csv_folder, f"{selected_region}_elbow.png")
    if os.path.exists(plot_file):
        img = Image.open(plot_file)
        st.image(img, caption=f"{selected_region} - {csv_filename}", use_column_width=True)
    else:
        st.warning("Plot not found for this region.")
