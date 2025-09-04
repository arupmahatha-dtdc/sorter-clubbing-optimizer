import streamlit as st
import pandas as pd
import os
import json

# ---------- Page setup ----------
st.set_page_config(layout="wide", page_title="Optimal Bagging Dashboard")

# ---------- Load data ----------
df_optimal = pd.read_csv("optimal_branches.csv")
df_bag = pd.read_csv("bag_summary.csv")
df_fd = pd.read_csv("final_sorting_location.csv")
all_data = pd.read_csv("all_data.csv")

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
st.title("📦 Optimal Bagging Dashboard")

# Top filters
col1, col2 = st.columns([1, 2])
with col1:
    type_choice = st.selectbox("Select Type", all_data["Type"].unique(), key="type_filter")
with col2:
    region_choice = st.selectbox("Select Region", all_data["Region"].unique(), key="region_filter")

st.markdown("---")

# ---------- Sorting Location Requirement ----------
st.subheader("🏭 Sorting Location Requirement")
df_sort = df_fd[(df_fd["Region"] == region_choice) & (df_fd["Type"] == type_choice)]
if df_sort.empty:
    st.info("No sorting location data for this Region × Type")
else:
    st.dataframe(df_sort, use_container_width=True)

st.markdown("---")

# ---------- Determine the column to use for total process ----------
# You may have a mapping of Type -> column name
type_total_column_map = {
    "Volume": "Volume",           # example: change if actual column names differ
    "Billed_Wt": "Billed_Wt",    # add more Type -> column mappings if needed
    # Add more mappings here
}
total_col = type_total_column_map.get(type_choice, "Total")  # fallback to 'Total'

# ---------- Filter data for Region × Type ----------
df_all = all_data[(all_data["Region"] == region_choice) & (all_data["Type"] == type_choice)]
df_bag_filtered = df_bag[(df_bag["Region"] == region_choice) & (df_bag["Type"] == type_choice)]
df_opt_filtered = df_optimal[(df_optimal["Region"] == region_choice) & (df_optimal["Type"] == type_choice)]

# Region × Type totals
sum_total_process = df_all[total_col].sum()
sum_optimal_process = 0  # accumulator for overall optimal

service_types = df_all["Service_Type"].unique()
cols = st.columns(len(service_types))

for i, stype in enumerate(service_types):
    with cols[i]:
        row_all = df_all[df_all["Service_Type"] == stype].iloc[0]
        row_bag = df_bag_filtered[df_bag_filtered["Service_Type"] == stype].iloc[0]
        row_opt = df_opt_filtered[df_opt_filtered["Service_Type"] == stype].iloc[0]

        total_process = row_all[total_col]
        branches_above_threshold = row_bag["Num_Branches"]
        cum_pct_above_threshold = row_bag["Cumulative_Percentage"]
        total_process_above_threshold = total_process * cum_pct_above_threshold / 100

        optimal_branches = row_opt["Optimal_Num_Branches"]
        optimal_cum_pct = row_opt["Optimal_Cumulative_Percentage"]
        optimal_total_process = total_process * optimal_cum_pct / 100

        sum_optimal_process += optimal_total_process

        # Map branch codes to names for display
        branch_codes = row_bag.get("Branches", "").split(",") if pd.notna(row_bag.get("Branches")) else []
        df_br_names = df_mapping[df_mapping["BranchCode"].isin([b.strip() for b in branch_codes])]
        branch_display = df_br_names[["BranchCode", "BranchName"]]

        # Display header + plot
        st.markdown(f"### {stype}")
        plot_filename = f"{region_choice}_{stype.replace(' ', '_')}_{type_choice.replace(' ', '_')}.png"
        plot_path = os.path.join("elbow_plots", plot_filename)
        if os.path.exists(plot_path):
            st.image(plot_path, caption=f"{stype} | {region_choice} | {type_choice}", use_column_width=True)
        else:
            st.warning(f"No saved plot found for {stype} ({plot_filename})")

        # Display metrics
        st.markdown(f"""
        - **Total {total_col}:** `{total_process}`  
        - **Branches Passing Threshold:** `{branches_above_threshold}`  
        - **Cumulative % Above Threshold:** `{cum_pct_above_threshold:.2f}%`  
        - **Total Process Above Threshold:** `{total_process_above_threshold:.2f}`  
        - **Optimal Branches:** `{optimal_branches}`  
        - **Optimal Cumulative %:** `{optimal_cum_pct:.2f}%`  
        - **Optimal Total Process:** `{optimal_total_process:.2f}`  
        """)

        # Collapsible branch list
        with st.expander("Show Branches Above Threshold"):
            st.dataframe(branch_display, use_container_width=True)

# ---------- Region × Type Overall ----------
overall_optimal_pct = (sum_optimal_process / sum_total_process * 100) if sum_total_process > 0 else 0

st.markdown("---")
st.markdown(f"### Overall {region_choice} | {type_choice} Summary")
st.markdown(f"""
- **Total {total_col}:** `{sum_total_process}`  
- **Total Process Handled by Optimal Branches:** `{sum_optimal_process:.2f}`  
- **Overall % of Volume Handled by Optimal Branches:** `{overall_optimal_pct:.2f}%`  
""")