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
    # Round numeric columns in sorting location display
    df_sort_display = df_sort.copy()
    for col in df_sort_display.select_dtypes(include="number").columns:
        df_sort_display[col] = df_sort_display[col].round(2)
    st.dataframe(df_sort_display, use_container_width=True)

st.markdown("---")

# ---------- Determine the column to use for total process ----------
type_total_column_map = {
    "Volume": "Total",           # example: change if actual column names differ
    "Billed Wt": "Total",        # add more Type -> column mappings if needed
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

        # ---------- Show Optimal Branches ----------
        branch_codes = row_opt.get("Branches", "").split(",") if pd.notna(row_opt.get("Branches")) else []
        branch_codes = [b.strip() for b in branch_codes if b.strip()]

        df_br_names = df_mapping[df_mapping["BranchCode"].isin(branch_codes)]
        branch_display = df_br_names[["BranchCode", "BranchName"]]

        # Display header + plot
        st.markdown(f"### {stype}")
        plot_filename = f"{region_choice}_{stype.replace(' ', '_')}_{type_choice.replace(' ', '_')}.png"
        plot_path = os.path.join("elbow_plots", plot_filename)
        if os.path.exists(plot_path):
            st.image(plot_path, caption=f"{stype} | {region_choice} | {type_choice}", use_column_width=True)
        else:
            st.warning(f"No saved plot found for {stype} ({plot_filename})")

        # Display metrics (all rounded to 2 decimals)
        st.markdown(f"""
        - **Total Units to be Processed:** `{round(total_process, 2)}`  
        - **No. of Branches Passing Threshold:** `{branches_above_threshold}`  
        - **% of Units Processed by Branches Passing Threshold**: `{round(cum_pct_above_threshold, 2)}%`  
        - **Total Units Processed by Branches Passing Threshold:** `{round(total_process_above_threshold, 2)}`  
        - **No. of Optimal Branches:** `{optimal_branches}`  
        - **% of Units Processed by Optimal Branches:** `{round(optimal_cum_pct, 2)}%`  
        - **Total Units Processed by Optimal Branches:** `{round(optimal_total_process, 2)}`  
        """)

        # Collapsible branch list
        with st.expander("Show Optimal Branches"):
            if branch_display.empty:
                st.info("No optimal branches found for this service type")
            else:
                st.dataframe(branch_display, use_container_width=True)

# ---------- Region × Type Overall ----------
overall_optimal_pct = (sum_optimal_process / sum_total_process * 100) if sum_total_process > 0 else 0

st.markdown("---")
st.markdown(f"### Overall {region_choice} | {type_choice} Summary")
st.markdown(f"""
- **Total Units to be Processed:** `{round(sum_total_process, 2)}`  
- **Total Units Processed by Optimal Branches:** `{round(sum_optimal_process, 2)}`  
- **% of Units Processed by Optimal Branches:** `{round(overall_optimal_pct, 2)}%`  
""")