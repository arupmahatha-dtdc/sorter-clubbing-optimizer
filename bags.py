import streamlit as st
import pandas as pd
import os
import json

# ---------- Page setup ----------
st.set_page_config(layout="wide", page_title="Branch Optimization Dashboard")

# ---------- Load saved results ----------
df_optimal = pd.read_csv("optimal_branches.csv")
df_fd = pd.read_csv("final_sorting_location.csv")

# Load mapping JSON
with open("des_mappings.json", "r") as f:
    mapping = json.load(f)

# Flatten branch mapping JSON
rows = []
for zone, regions in mapping.items():
    for region, cities in regions.items():
        for city, branches in cities.items():
            for branch_code, branch_name in branches.items():
                rows.append({
                    "Zone": zone,
                    "Region": region,
                    "City": city,
                    "BranchCode": branch_code,
                    "BranchName": branch_name
                })
df_mapping = pd.DataFrame(rows)

# ---------- Streamlit UI ----------
st.title("📦 Branch Optimization Dashboard")

# Top filters instead of sidebar
col1, col2 = st.columns([1, 2])
with col1:
    type_choice = st.selectbox("Select Type", df_optimal["Type"].unique(), key="type_filter")
with col2:
    region_choice = st.selectbox("Select Region", df_optimal["Region"].unique(), key="region_filter")

st.markdown("---")

# ---------- Sorting Location Requirement ----------
st.subheader("🏭 Sorting Location Requirement")
df_sort = df_fd[(df_fd["Region"] == region_choice) & (df_fd["Type"] == type_choice)]
st.dataframe(df_sort, use_container_width=True)

# ---------- Service Type Analysis ----------
st.subheader(f"📊 Analysis for {region_choice} | {type_choice}")

service_types = df_optimal[
    (df_optimal["Region"] == region_choice) &
    (df_optimal["Type"] == type_choice)
]["Service_Type"].unique()

# Create wider columns for service types
cols = st.columns(len(service_types))

for i, stype in enumerate(service_types):
    with cols[i]:
        row = df_optimal[
            (df_optimal["Region"] == region_choice) &
            (df_optimal["Type"] == type_choice) &
            (df_optimal["Service_Type"] == stype)
        ].iloc[0]

        opt_branches = row["Optimal_Num_Branches"]
        opt_cum_pct = row["Optimal_Cumulative_Percentage"]
        branch_codes = row["Branches"].split(",") if pd.notna(row["Branches"]) else []

        # Map branch codes → names
        df_br_names = df_mapping[df_mapping["BranchCode"].isin([b.strip() for b in branch_codes])]
        branch_display = df_br_names[["BranchCode", "BranchName"]]

        # Normalize filenames (spaces → underscores)
        stype_safe = stype.replace(" ", "_")
        type_safe = type_choice.replace(" ", "_")
        plot_filename = f"{region_choice}_{stype_safe}_{type_safe}.png"
        plot_path = os.path.join("elbow_plots", plot_filename)

        # Show header + plot
        st.markdown(f"### {stype}")
        if os.path.exists(plot_path):
            st.image(plot_path, caption=f"{stype} | {region_choice} | {type_choice}", use_column_width=True)
        else:
            st.warning(f"No saved plot found for {stype} ({plot_filename})")

        # Show results
        st.markdown(f"""
        - **Optimal Branches:** `{opt_branches}`  
        - **Optimal Cumulative %:** `{opt_cum_pct:.2f}`  
        """)

        # Collapsible branch list
        with st.expander("Show Branches"):
            st.dataframe(branch_display, use_container_width=True)
