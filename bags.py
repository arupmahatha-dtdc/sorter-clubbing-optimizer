# bags_app.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

# ---------- Helpers ----------
def find_elbow(x, y):
    """Find elbow (knee) using max perpendicular distance from line connecting first and last points."""
    if len(x) < 2:
        return 0
    p1, p2 = np.array([x[0], y[0]]), np.array([x[-1], y[-1]])
    line_vec = p2 - p1
    line_vec = line_vec / np.linalg.norm(line_vec)
    distances = []
    for i in range(len(x)):
        p = np.array([x[i], y[i]])
        proj_len = np.dot(p - p1, line_vec)
        proj_point = p1 + proj_len * line_vec
        dist = np.linalg.norm(p - proj_point)
        distances.append(dist)
    return int(np.argmax(distances))


# ---------- Load Data ----------
df_abs = pd.read_csv("all_data.csv")
df_pct = pd.read_csv("all_data_percentage.csv")
df_office = pd.read_csv("office_location.csv")

# Import flow analysis functions from processing
from processing import (
    load_flow_analysis_data, 
    get_region_flow_summary, 
    get_region_receiving_summary, 
    get_all_india_flow_summary
)

# ---------- Dynamic Flow Analysis Functions ----------
def calculate_dynamic_flow_analysis(df_abs, df_optimal, type_name):
    """Calculate flow analysis dynamically based on current optimal branches"""
    
    # Create region mapping from branch codes to regions
    region_mapping = {
        'A': 'AMD', 'B': 'BLR', 'C': 'CHE', 'E': 'CJB', 'H': 'HYD', 
        'I': 'IDR', 'J': 'HHPT', 'K': 'CCU', 'M': 'MUM', 'N': 'DDL',
        'O': 'COK', 'P': 'PNQ', 'Q': 'JAI', 'R': 'NGP', 'T': 'PAT',
        'U': 'UPT', 'V': 'VJA', 'W': 'BBI', 'X': 'GAU'
    }
    
    # Get all unique regions
    regions = df_abs['Region'].unique()
    
    # Create a dictionary to store optimal branches for each combination
    optimal_branches_dict = {}
    for _, row in df_optimal.iterrows():
        key = (row['Region'], row['Service_Type'], row['Type'])
        branches = [b.strip() for b in str(row['Branches']).split(',') if b.strip()]
        optimal_branches_dict[key] = set(branches)
    
    # Initialize flow matrices
    flow_matrix = pd.DataFrame(0, index=regions, columns=regions)
    optimal_matrix = pd.DataFrame(0, index=regions, columns=regions)
    non_optimal_matrix = pd.DataFrame(0, index=regions, columns=regions)
    
    # Process each row (origin region)
    for _, row in df_abs.iterrows():
        if row['Type'] != type_name:
            continue
            
        origin_region = row['Region']
        service_type = row['Service_Type']
        
        # Get optimal branches for this combination
        key = (origin_region, service_type, type_name)
        optimal_branches = optimal_branches_dict.get(key, set())
        
        # Get branch columns (exclude Region, Type, Service_Type, Total)
        branch_cols = [col for col in df_abs.columns if col not in ['Region', 'Type', 'Service_Type', 'Total']]
        
        for branch in branch_cols:
            flow_value = row[branch]
            if pd.isna(flow_value) or flow_value == 0:
                continue
                
            # Determine destination region from branch code
            dest_region = None
            if branch and len(branch) > 0:
                first_letter = branch[0]
                dest_region = region_mapping.get(first_letter)
            
            if dest_region and dest_region in regions:
                # Add to total flow matrix
                flow_matrix.loc[origin_region, dest_region] += flow_value
                
                # Determine if this is optimal or non-optimal based on optimal_branches
                if branch in optimal_branches:
                    optimal_matrix.loc[origin_region, dest_region] += flow_value
                else:
                    non_optimal_matrix.loc[origin_region, dest_region] += flow_value
    
    # Calculate percentages correctly (optimal/total * 100 for each origin-destination pair)
    optimal_pct_matrix = pd.DataFrame(0.0, index=regions, columns=regions)
    non_optimal_pct_matrix = pd.DataFrame(0.0, index=regions, columns=regions)
    
    for origin in regions:
        for dest in regions:
            total_flow = flow_matrix.loc[origin, dest]
            if total_flow > 0:
                optimal_pct_matrix.loc[origin, dest] = (optimal_matrix.loc[origin, dest] / total_flow * 100).round(2)
                non_optimal_pct_matrix.loc[origin, dest] = (non_optimal_matrix.loc[origin, dest] / total_flow * 100).round(2)
    
    return flow_matrix, optimal_matrix, non_optimal_matrix, optimal_pct_matrix, non_optimal_pct_matrix


def calculate_dynamic_receiving_analysis(df_abs, df_optimal, type_name):
    """Calculate receiving analysis dynamically based on current optimal branches"""
    
    # Create region mapping from branch codes to regions
    region_mapping = {
        'A': 'AMD', 'B': 'BLR', 'C': 'CHE', 'E': 'CJB', 'H': 'HYD', 
        'I': 'IDR', 'J': 'HHPT', 'K': 'CCU', 'M': 'MUM', 'N': 'DDL',
        'O': 'COK', 'P': 'PNQ', 'Q': 'JAI', 'R': 'NGP', 'T': 'PAT',
        'U': 'UPT', 'V': 'VJA', 'W': 'BBI', 'X': 'GAU'
    }
    
    # Get all unique regions
    regions = df_abs['Region'].unique()
    
    # Create a dictionary to store optimal branches for each combination
    optimal_branches_dict = {}
    for _, row in df_optimal.iterrows():
        key = (row['Region'], row['Service_Type'], row['Type'])
        branches = [b.strip() for b in str(row['Branches']).split(',') if b.strip()]
        optimal_branches_dict[key] = set(branches)
    
    # Initialize receiving matrices
    total_receiving = pd.Series(0, index=regions)
    optimal_receiving = pd.Series(0, index=regions)
    non_optimal_receiving = pd.Series(0, index=regions)
    
    # Process each row (origin region)
    for _, row in df_abs.iterrows():
        if row['Type'] != type_name:
            continue
            
        origin_region = row['Region']
        service_type = row['Service_Type']
        
        # Get optimal branches for this origin region combination
        key = (origin_region, service_type, type_name)
        optimal_branches = optimal_branches_dict.get(key, set())
        
        # Get branch columns (exclude Region, Type, Service_Type, Total)
        branch_cols = [col for col in df_abs.columns if col not in ['Region', 'Type', 'Service_Type', 'Total']]
        
        for branch in branch_cols:
            flow_value = row[branch]
            if pd.isna(flow_value) or flow_value == 0:
                continue
                
            # Determine destination region from branch code
            dest_region = None
            if branch and len(branch) > 0:
                first_letter = branch[0]
                dest_region = region_mapping.get(first_letter)
            
            if dest_region and dest_region in regions:
                # Add to total receiving
                total_receiving[dest_region] += flow_value
                
                # Determine if this is optimal or non-optimal based on optimal_branches
                if branch in optimal_branches:
                    optimal_receiving[dest_region] += flow_value
                else:
                    non_optimal_receiving[dest_region] += flow_value
    
    # Calculate percentages correctly (optimal/total * 100 for each region)
    optimal_pct = pd.Series(0.0, index=regions)
    non_optimal_pct = pd.Series(0.0, index=regions)
    
    for region in regions:
        if total_receiving[region] > 0:
            optimal_pct[region] = (optimal_receiving[region] / total_receiving[region] * 100).round(2)
            non_optimal_pct[region] = (non_optimal_receiving[region] / total_receiving[region] * 100).round(2)
    
    return total_receiving, optimal_receiving, non_optimal_receiving, optimal_pct, non_optimal_pct

# Melt wide → long
df_abs_long = df_abs.melt(
    id_vars=["Region", "Type", "Service_Type", "Total"],
    var_name="Branch",
    value_name="Value"
)
df_pct_long = df_pct.melt(
    id_vars=["Region", "Type", "Service_Type"],
    var_name="Branch",
    value_name="Percentage"
)

df_merge = pd.merge(
    df_abs_long,
    df_pct_long,
    on=["Region", "Type", "Service_Type", "Branch"],
    how="inner"
)

# Mapping file
with open("des_mappings.json", "r") as f:
    mapping = json.load(f)

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
df_region_counts = df_mapping.groupby("Region").size().reset_index(name="Self_Branches")

# Create branch code to name mapping from office_location.csv
branch_name_mapping = dict(zip(df_office['office'], df_office['name']))

def get_branch_names(branch_codes_str):
    """Convert branch codes string to branch names string"""
    if not isinstance(branch_codes_str, str) or branch_codes_str.strip() == "":
        return ""
    branch_codes = [b.strip() for b in branch_codes_str.split(",") if b.strip()]
    branch_names = []
    for code in branch_codes:
        name = branch_name_mapping.get(code, code)  # Use code if name not found
        branch_names.append(f"{code} - {name}")
    return ", ".join(branch_names)


# ---------- Streamlit UI ----------
st.set_page_config(layout="wide", page_title="Optimal Bagging Dashboard")
st.title("📦 Optimal Bagging Dashboard")

# Threshold sliders
col1, col2 = st.columns(2)
with col1:
    vol_thresh = st.slider("Volume Threshold", 0, 100, 25, step=1)
with col2:
    wt_thresh = st.slider("Billed Wt Threshold", 0, 100, 35, step=1)

thresholds = {"Volume": vol_thresh, "Billed Wt": wt_thresh}

# Type + Region filters
col1, col2 = st.columns(2)
with col1:
    type_sel = st.selectbox("Select Type", df_abs["Type"].unique())
with col2:
    regions = ["All India"] + sorted(df_abs["Region"].unique())
    region_sel = st.selectbox("Select Region", regions)



# ---------- Compute Bag Summary ----------
results = []
for (region, stype, type_), group in df_merge.groupby(["Region", "Service_Type", "Type"]):
    thresh = thresholds.get(type_, 0)
    filtered = group[group["Value"] >= thresh]
    num_branches = len(filtered)
    cum_pct = filtered["Percentage"].sum()
    branch_list = filtered["Branch"].tolist()
    results.append({
        "Region": region,
        "Service_Type": stype,
        "Type": type_,
        "Num_Branches": num_branches,
        "Cumulative_Percentage": cum_pct,
        "Branches": ", ".join(branch_list) if branch_list else "",
        "Branch_Names": get_branch_names(", ".join(branch_list)) if branch_list else ""
    })
df_summary = pd.DataFrame(results)

# ---------- Compute Optimal Branches ----------
optimal_results = []
for _, row in df_summary.iterrows():
    branches_str = row["Branches"]
    if not isinstance(branches_str, str) or branches_str.strip() == "":
        continue
    branches = [b.strip() for b in branches_str.split(",") if b.strip()]
    subset = df_pct_long[
        (df_pct_long["Region"] == row["Region"]) &
        (df_pct_long["Service_Type"] == row["Service_Type"]) &
        (df_pct_long["Type"] == row["Type"]) &
        (df_pct_long["Branch"].isin(branches))
    ].copy()
    if subset.empty:
        continue
    subset = subset.sort_values("Percentage", ascending=False).reset_index(drop=True)
    subset["Cumulative_Percentage"] = subset["Percentage"].cumsum()
    x = np.arange(1, len(subset) + 1)
    y = subset["Cumulative_Percentage"].values
    elbow_idx = find_elbow(x, y)
    opt_num_branches = x[elbow_idx]
    opt_cum_pct = y[elbow_idx]
    opt_branches = subset.loc[:elbow_idx, "Branch"].tolist()
    optimal_results.append({
        "Region": row["Region"],
        "Service_Type": row["Service_Type"],
        "Type": row["Type"],
        "Optimal_Num_Branches": opt_num_branches,
        "Optimal_Cumulative_Percentage": opt_cum_pct,
        "Branches": ", ".join(opt_branches),
        "Branch_Names": get_branch_names(", ".join(opt_branches))
    })
df_optimal = pd.DataFrame(optimal_results)

# ---------- Sorting Location Requirement ----------
df_sum_opt = df_optimal.groupby(["Region", "Type"])["Optimal_Num_Branches"].sum().reset_index()
df_sum_opt = df_sum_opt.rename(columns={"Optimal_Num_Branches": "Sorting_Locations_for_Optimal_Branches"})
df_fd = pd.merge(df_sum_opt, df_region_counts, on="Region", how="left")
df_fd["Sorting_Location_Needed"] = (
    df_fd["Sorting_Locations_for_Optimal_Branches"] + 60 + 2 * df_fd["Self_Branches"]
)

# ---------- All India Summary Box (Before Sorting) ----------
if region_sel == "All India" and not df_optimal.empty:
    st.subheader("🇮🇳 All India Summary")
    
    # Calculate total units - sum of all service types across all regions for selected type
    total_units_all = df_abs[df_abs["Type"] == type_sel]["Total"].sum()
    
    # Calculate total units through optimal branches for the selected type only
    total_units_through_optimal = 0
    for _, row in df_optimal[df_optimal["Type"] == type_sel].iterrows():
        # Get total units for this service type
        total_process = df_abs[
            (df_abs["Region"] == row["Region"]) &
            (df_abs["Type"] == row["Type"]) &
            (df_abs["Service_Type"] == row["Service_Type"])
        ]["Total"].iloc[0]
        
        total_units_through_optimal += total_process * row["Optimal_Cumulative_Percentage"] / 100
    
    # Calculate percentage
    pct_through_optimal_all = (total_units_through_optimal / total_units_all * 100) if total_units_all > 0 else 0
    units_not_through_optimal = total_units_all - total_units_through_optimal
    pct_not_through_optimal = 100 - pct_through_optimal_all
    
    # Create summary data with only the 3 requested metrics
    india_summary = {
        "Metric": [
            "Total Units (All Regions)",
            "Units Through Optimal",
            "% Through Optimal",
            "Units Not Through Optimal",
            "% Not Through Optimal",
        ],
        "Value": [
            f"{total_units_all:,.2f}",
            f"{total_units_through_optimal:,.2f}",
            f"{pct_through_optimal_all:.2f}%",
            f"{units_not_through_optimal:,.2f}",
            f"{pct_not_through_optimal:.2f}%",
        ]
    }
    
    df_india_summary = pd.DataFrame(india_summary)
    st.dataframe(df_india_summary, use_container_width=True)

# ---------- Display Sorting Requirement ----------
st.subheader("🏭 Sorting Location Requirement")

if region_sel == "All India":
    df_display = df_fd[df_fd["Type"] == type_sel].copy()
    
    # Get total units for regions that exist in df_display
    region_totals = df_abs[df_abs["Type"] == type_sel].groupby("Region")["Total"].sum()
    df_display["Total_Units"] = df_display["Region"].map(region_totals).fillna(0)

    # Compute Optimal Units per region for the selected type
    region_opt_units = {}
    for _, row in df_optimal[df_optimal["Type"] == type_sel].iterrows():
        total_process = df_abs[
            (df_abs["Region"] == row["Region"]) &
            (df_abs["Type"] == row["Type"]) &
            (df_abs["Service_Type"] == row["Service_Type"])
        ]["Total"].iloc[0]
        region_opt_units[row["Region"]] = region_opt_units.get(row["Region"], 0) + (
            total_process * row["Optimal_Cumulative_Percentage"] / 100
        )

    df_display["Optimal_Units"] = df_display["Region"].map(region_opt_units).fillna(0)
    df_display["Optimal_%"] = np.where(
        df_display["Total_Units"] > 0,
        df_display["Optimal_Units"] / df_display["Total_Units"] * 100,
        0,
    )
    # Add not-through-optimal metrics
    df_display["Units_Not_Through_Optimal"] = df_display["Total_Units"] - df_display["Optimal_Units"]
    df_display["Pct_Not_Through_Optimal"] = 100 - df_display["Optimal_%"]
    
    # Remove Type column since it's already selected
    df_display = df_display.drop(columns=["Type"])
    # Round numeric columns to 2 decimals for display
    numeric_cols = df_display.select_dtypes(include=[np.number]).columns
    df_display[numeric_cols] = df_display[numeric_cols].astype(float).round(2)
    st.dataframe(df_display, use_container_width=True)
else:
    df_display = df_fd[(df_fd["Region"] == region_sel) & (df_fd["Type"] == type_sel)].copy()
    if not df_display.empty:
        total_units = df_abs[(df_abs["Region"] == region_sel) & (df_abs["Type"] == type_sel)]["Total"].sum()
        opt_units = 0
        for _, row in df_optimal[(df_optimal["Region"] == region_sel) & (df_optimal["Type"] == type_sel)].iterrows():
            total_process = df_abs[
                (df_abs["Region"] == row["Region"]) &
                (df_abs["Type"] == row["Type"]) &
                (df_abs["Service_Type"] == row["Service_Type"])
            ]["Total"].iloc[0]
            opt_units += total_process * row["Optimal_Cumulative_Percentage"] / 100
        overall_pct = (opt_units / total_units * 100) if total_units > 0 else 0
        df_display["Total_Units"] = total_units
        df_display["Optimal_Units"] = opt_units
        df_display["Optimal_%"] = overall_pct
        # Add not-through-optimal metrics
        df_display["Units_Not_Through_Optimal"] = df_display["Total_Units"] - df_display["Optimal_Units"]
        df_display["Pct_Not_Through_Optimal"] = 100 - df_display["Optimal_%"]
        # Remove Type column since it's already selected
        df_display = df_display.drop(columns=["Type"])
        # Round numeric columns to 2 decimals for display
        numeric_cols = df_display.select_dtypes(include=[np.number]).columns
        df_display[numeric_cols] = df_display[numeric_cols].astype(float).round(2)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No sorting data for this Region × Type")

# ---------- Comprehensive Service Type Summary ----------
st.subheader("📈 Comprehensive Service Type Summary")

# Create comprehensive summary table
comprehensive_results = []
for (region, stype, type_), group in df_merge.groupby(["Region", "Service_Type", "Type"]):
    if region_sel != "All India" and region != region_sel:
        continue
    if type_ != type_sel:
        continue
    
    # Get total units for this service type
    total_units = group["Value"].sum()
    
    # Get threshold and filtered data
    thresh = thresholds.get(type_, 0)
    filtered = group[group["Value"] >= thresh]
    num_branches_threshold = len(filtered)
    pct_through_threshold = filtered["Percentage"].sum() if not filtered.empty else 0
    units_through_threshold = filtered["Value"].sum() if not filtered.empty else 0
    
    # Get optimal branches data
    opt_row = df_optimal[(df_optimal["Region"] == region) & 
                        (df_optimal["Service_Type"] == stype) & 
                        (df_optimal["Type"] == type_)]
    if not opt_row.empty:
        opt_num_branches = opt_row.iloc[0]["Optimal_Num_Branches"]
        opt_pct = opt_row.iloc[0]["Optimal_Cumulative_Percentage"]
        opt_units = total_units * opt_pct / 100
    else:
        opt_num_branches = 0
        opt_pct = 0
        opt_units = 0
    
    comprehensive_results.append({
        "Region": region,
        "Service_Type": stype,
        "Total_Units": total_units,
        "Threshold_Branches": num_branches_threshold,
        "Pct_Through_Threshold": round(pct_through_threshold, 2),
        "Units_Through_Threshold": round(units_through_threshold, 0),
        "Optimal_Branches": opt_num_branches,
        "Pct_Through_Optimal": round(opt_pct, 2),
        "Units_Through_Optimal": round(opt_units, 0)
    })

df_comprehensive = pd.DataFrame(comprehensive_results)

if not df_comprehensive.empty:
    # Format the display
    display_cols = ["Service_Type", "Total_Units", "Threshold_Branches", "Pct_Through_Threshold", 
                   "Units_Through_Threshold", "Optimal_Branches", "Pct_Through_Optimal", "Units_Through_Optimal"]
    
    if region_sel == "All India":
        display_cols = ["Region"] + display_cols
    
    df_comp_view = df_comprehensive[display_cols].copy()
    comp_numeric_cols = df_comp_view.select_dtypes(include=[np.number]).columns
    df_comp_view[comp_numeric_cols] = df_comp_view[comp_numeric_cols].astype(float).round(2)
    st.dataframe(df_comp_view, use_container_width=True)
    
    # Add download button for the comprehensive table
    csv = df_comprehensive[display_cols].to_csv(index=False)
    st.download_button(
        label="📥 Download Comprehensive Summary as CSV",
        data=csv,
        file_name=f"comprehensive_summary_{type_sel}_{region_sel.replace(' ', '_')}.csv",
        mime="text/csv"
    )
else:
    st.info("No data available for the selected filters")


# ---------- Threshold Branch Summary with Names ----------
st.subheader("🏢 Threshold Branch Summary with Names")

if region_sel == "All India":
    summary_display = df_summary[df_summary["Type"] == type_sel][["Region", "Service_Type", "Num_Branches", "Cumulative_Percentage", "Branch_Names"]].copy()
else:
    summary_display = df_summary[(df_summary["Region"] == region_sel) & (df_summary["Type"] == type_sel)][["Service_Type", "Num_Branches", "Cumulative_Percentage", "Branch_Names"]].copy()

if not summary_display.empty:
    sum_view = summary_display.copy()
    sum_numeric_cols = sum_view.select_dtypes(include=[np.number]).columns
    sum_view[sum_numeric_cols] = sum_view[sum_numeric_cols].astype(float).round(2)
    st.dataframe(sum_view, use_container_width=True)
else:
    st.info("No branch data available for the selected filters")

# ---------- Optimal Branches Summary with Names ----------
st.subheader("🎯 Optimal Branches Summary with Names")

if region_sel == "All India":
    optimal_display = df_optimal[df_optimal["Type"] == type_sel][["Region", "Service_Type", "Optimal_Num_Branches", "Optimal_Cumulative_Percentage", "Branch_Names"]].copy()
else:
    optimal_display = df_optimal[(df_optimal["Region"] == region_sel) & (df_optimal["Type"] == type_sel)][["Service_Type", "Optimal_Num_Branches", "Optimal_Cumulative_Percentage", "Branch_Names"]].copy()

if not optimal_display.empty:
    opt_view_tbl = optimal_display.copy()
    opt_numeric_cols = opt_view_tbl.select_dtypes(include=[np.number]).columns
    opt_view_tbl[opt_numeric_cols] = opt_view_tbl[opt_numeric_cols].astype(float).round(2)
    st.dataframe(opt_view_tbl, use_container_width=True)
else:
    st.info("No optimal branch data available for the selected filters")

# ---------- Service Type Analysis ----------
st.subheader("📊 Service Type Analysis")

# Filter data based on selected region and type
if region_sel == "All India":
    bag_view = df_summary[df_summary["Type"] == type_sel]
    opt_view = df_optimal[df_optimal["Type"] == type_sel]
else:
    bag_view = df_summary[(df_summary["Region"] == region_sel) & (df_summary["Type"] == type_sel)]
    opt_view = df_optimal[(df_optimal["Region"] == region_sel) & (df_optimal["Type"] == type_sel)]

service_types = bag_view["Service_Type"].unique()

if region_sel == "All India":
    st.info("Elbow plots and optimal branches are not available for All India view. Please select a specific region.")
else:
    # Create columns to show plots side by side (max 3 per row)
    max_cols = 3
    for i in range(0, len(service_types), max_cols):
        cols = st.columns(min(max_cols, len(service_types) - i))
        for j, stype in enumerate(service_types[i:i + max_cols]):
            col = cols[j]
            with col:
                subset = bag_view[bag_view["Service_Type"] == stype]
                opt_subset = opt_view[opt_view["Service_Type"] == stype]

                # Plot
                if not subset.empty and not opt_subset.empty:
                    branches = [b.strip() for b in subset.iloc[0]["Branches"].split(",") if b.strip()]
                    sub_pct = df_pct_long[
                        (df_pct_long["Region"] == region_sel) &
                        (df_pct_long["Service_Type"] == stype) &
                        (df_pct_long["Type"] == type_sel) &
                        (df_pct_long["Branch"].isin(branches))
                    ].copy()

                    if not sub_pct.empty:
                        sub_pct = sub_pct.sort_values("Percentage", ascending=False).reset_index(drop=True)
                        sub_pct["Cumulative_Percentage"] = sub_pct["Percentage"].cumsum()
                        x = np.arange(1, len(sub_pct) + 1)
                        y = sub_pct["Cumulative_Percentage"].values

                        if len(x) > 1:
                            elbow_idx = find_elbow(x, y)
                            opt_num_branches = x[elbow_idx]
                            opt_cum_pct = y[elbow_idx]

                            fig, ax = plt.subplots(figsize=(4, 3))
                            ax.plot(x, y, marker="o", label="Cumulative %")
                            ax.axvline(opt_num_branches, color="r", linestyle="--")
                            ax.axhline(opt_cum_pct, color="r", linestyle="--")
                            ax.scatter(opt_num_branches, opt_cum_pct, color="red", zorder=5, label="Elbow Point")
                            ax.text(opt_num_branches, opt_cum_pct,
                                    f"Opt = {opt_num_branches}\nCum% = {opt_cum_pct:.2f}",
                                    fontsize=8, ha="left", va="bottom", color="red")
                            ax.set_title(stype, fontsize=10)
                            ax.set_xlabel("Branches", fontsize=8)
                            ax.set_ylabel("Cum%", fontsize=8)
                            ax.tick_params(axis='both', labelsize=8)
                            ax.legend(fontsize=8)
                            st.pyplot(fig)

                # Optimal branches in expander
                if not opt_subset.empty:
                    with st.expander(f"Show Optimal Branches ({stype})"):
                        branch_codes_str = opt_subset.iloc[0]["Branches"]
                        branch_names_str = get_branch_names(branch_codes_str)
                        if branch_names_str:
                            # Create a DataFrame with code, name, and amount for selected type
                            branch_codes = [b.strip() for b in branch_codes_str.split(",") if b.strip()]
                            branch_data = []
                            # Get the source row for amounts for this Region × Service_Type × Type
                            src_rows = df_abs[
                                (df_abs["Region"] == region_sel) &
                                (df_abs["Service_Type"] == stype) &
                                (df_abs["Type"] == type_sel)
                            ]
                            src_row = src_rows.iloc[0] if not src_rows.empty else None
                            for code in branch_codes:
                                name = branch_name_mapping.get(code, "Name not found")
                                amount = 0.0
                                if src_row is not None and code in src_row.index:
                                    try:
                                        amount = float(src_row[code])
                                    except Exception:
                                        amount = 0.0
                                branch_data.append({
                                    "Branch Code": code,
                                    "Branch Name": name,
                                    f"{type_sel} Amount": round(amount, 2)
                                })
                            df_branch_table = pd.DataFrame(branch_data)
                            st.table(df_branch_table)
                        else:
                            st.write("No optimal branches found")


# ---------- Flow Analysis Section ----------
st.subheader("🔄 Flow Analysis")

# Calculate dynamic flow analysis based on current thresholds and optimal branches
flow_matrix, optimal_matrix, non_optimal_matrix, optimal_pct_matrix, non_optimal_pct_matrix = calculate_dynamic_flow_analysis(df_abs, df_optimal, type_sel)
total_receiving, optimal_receiving, non_optimal_receiving, optimal_pct, non_optimal_pct = calculate_dynamic_receiving_analysis(df_abs, df_optimal, type_sel)

if region_sel == "All India":
    # All India Flow Analysis
    st.write("**All India Flow Summary**")
    
    # Calculate All India sending summary
    all_india_sending = {
        'Total_Units_Sent': flow_matrix.sum().sum(),
        'Optimal_Units_Sent': optimal_matrix.sum().sum(),
        'Non_Optimal_Units_Sent': non_optimal_matrix.sum().sum(),
        'Optimal_Percentage_Sent': (optimal_matrix.sum().sum() / flow_matrix.sum().sum() * 100) if flow_matrix.sum().sum() > 0 else 0,
        'Non_Optimal_Percentage_Sent': (non_optimal_matrix.sum().sum() / flow_matrix.sum().sum() * 100) if flow_matrix.sum().sum() > 0 else 0
    }
    
    # Calculate All India receiving summary
    all_india_receiving = {
        'Total_Units_Received': total_receiving.sum(),
        'Optimal_Units_Received': optimal_receiving.sum(),
        'Non_Optimal_Units_Received': non_optimal_receiving.sum(),
        'Optimal_Percentage_Received': (optimal_receiving.sum() / total_receiving.sum() * 100) if total_receiving.sum() > 0 else 0,
        'Non_Optimal_Percentage_Received': (non_optimal_receiving.sum() / total_receiving.sum() * 100) if total_receiving.sum() > 0 else 0
    }
    
    # Display sending summary
    col1, col2 = st.columns(2)
    with col1:
        st.write("**📤 Sending Summary**")
        sending_df = pd.DataFrame([
            {"Metric": "Total Units Sent", "Value": f"{all_india_sending['Total_Units_Sent']:,.2f}"},
            {"Metric": "Optimal Units Sent", "Value": f"{all_india_sending['Optimal_Units_Sent']:,.2f}"},
            {"Metric": "Non-Optimal Units Sent", "Value": f"{all_india_sending['Non_Optimal_Units_Sent']:,.2f}"},
            {"Metric": "Optimal % Sent", "Value": f"{all_india_sending['Optimal_Percentage_Sent']:.2f}%"},
            {"Metric": "Non-Optimal % Sent", "Value": f"{all_india_sending['Non_Optimal_Percentage_Sent']:.2f}%"}
        ])
        st.dataframe(sending_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.write("**📥 Receiving Summary**")
        receiving_df = pd.DataFrame([
            {"Metric": "Total Units Received", "Value": f"{all_india_receiving['Total_Units_Received']:,.2f}"},
            {"Metric": "Optimal Units Received", "Value": f"{all_india_receiving['Optimal_Units_Received']:,.2f}"},
            {"Metric": "Non-Optimal Units Received", "Value": f"{all_india_receiving['Non_Optimal_Units_Received']:,.2f}"},
            {"Metric": "Optimal % Received", "Value": f"{all_india_receiving['Optimal_Percentage_Received']:.2f}%"},
            {"Metric": "Non-Optimal % Received", "Value": f"{all_india_receiving['Non_Optimal_Percentage_Received']:.2f}%"}
        ])
        st.dataframe(receiving_df, use_container_width=True, hide_index=True)
    
    # Top destinations
    st.write("**🎯 Top Destinations (All India)**")
    top_destinations = flow_matrix.sum().sort_values(ascending=False).reset_index()
    top_destinations.columns = ['Destination Region', 'Total Units']
    top_destinations['Optimal Units'] = [optimal_matrix[region].sum() for region in top_destinations['Destination Region']]
    top_destinations['Non-Optimal Units'] = [non_optimal_matrix[region].sum() for region in top_destinations['Destination Region']]
    top_destinations['Optimal %'] = (top_destinations['Optimal Units'] / top_destinations['Total Units'] * 100).round(2)
    top_destinations['Non-Optimal %'] = (top_destinations['Non-Optimal Units'] / top_destinations['Total Units'] * 100).round(2)
    st.dataframe(top_destinations, use_container_width=True)

else:
    # Specific Region Flow Analysis
    st.write(f"**Flow Analysis for {region_sel}**")
    
    # Calculate sending summary for the selected region
    sending_summary = {
        'Total_Units_Sent': flow_matrix.loc[region_sel].sum(),
        'Optimal_Units_Sent': optimal_matrix.loc[region_sel].sum(),
        'Non_Optimal_Units_Sent': non_optimal_matrix.loc[region_sel].sum(),
        'Optimal_Percentage_Sent': (optimal_matrix.loc[region_sel].sum() / flow_matrix.loc[region_sel].sum() * 100) if flow_matrix.loc[region_sel].sum() > 0 else 0,
        'Non_Optimal_Percentage_Sent': (non_optimal_matrix.loc[region_sel].sum() / flow_matrix.loc[region_sel].sum() * 100) if flow_matrix.loc[region_sel].sum() > 0 else 0
    }
    
    # Get receiving summary for the selected region
    receiving_summary = {
        'Total_Units_Received': total_receiving[region_sel],
        'Optimal_Units_Received': optimal_receiving[region_sel],
        'Non_Optimal_Units_Received': non_optimal_receiving[region_sel],
        'Optimal_Percentage_Received': optimal_pct[region_sel],
        'Non_Optimal_Percentage_Received': non_optimal_pct[region_sel]
    }
    
    # Display sending summary
    col1, col2 = st.columns(2)
    with col1:
        st.write("**📤 Sending Summary**")
        sending_df = pd.DataFrame([
            {"Metric": "Total Units Sent", "Value": f"{sending_summary['Total_Units_Sent']:,.2f}"},
            {"Metric": "Optimal Units Sent", "Value": f"{sending_summary['Optimal_Units_Sent']:,.2f}"},
            {"Metric": "Non-Optimal Units Sent", "Value": f"{sending_summary['Non_Optimal_Units_Sent']:,.2f}"},
            {"Metric": "Optimal % Sent", "Value": f"{sending_summary['Optimal_Percentage_Sent']:.2f}%"},
            {"Metric": "Non-Optimal % Sent", "Value": f"{sending_summary['Non_Optimal_Percentage_Sent']:.2f}%"}
        ])
        st.dataframe(sending_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.write("**📥 Receiving Summary**")
        receiving_df = pd.DataFrame([
            {"Metric": "Total Units Received", "Value": f"{receiving_summary['Total_Units_Received']:,.2f}"},
            {"Metric": "Optimal Units Received", "Value": f"{receiving_summary['Optimal_Units_Received']:,.2f}"},
            {"Metric": "Non-Optimal Units Received", "Value": f"{receiving_summary['Non_Optimal_Units_Received']:,.2f}"},
            {"Metric": "Optimal % Received", "Value": f"{receiving_summary['Optimal_Percentage_Received']:.2f}%"},
            {"Metric": "Non-Optimal % Received", "Value": f"{receiving_summary['Non_Optimal_Percentage_Received']:.2f}%"}
        ])
        st.dataframe(receiving_df, use_container_width=True, hide_index=True)
    
    # Detailed sending matrix (where it sends)
    st.write("**🎯 Where It Sends (Top Destinations)**")
    sending_data = []
    for dest in flow_matrix.columns:
        total_flow = flow_matrix.loc[region_sel, dest]
        if total_flow > 0:
            optimal_flow = optimal_matrix.loc[region_sel, dest]
            non_optimal_flow = non_optimal_matrix.loc[region_sel, dest]
            optimal_pct = optimal_pct_matrix.loc[region_sel, dest]
            non_optimal_pct = non_optimal_pct_matrix.loc[region_sel, dest]
            
            sending_data.append({
                'Destination': dest,
                'Total Units': total_flow,
                'Optimal Units': optimal_flow,
                'Non-Optimal Units': non_optimal_flow,
                'Optimal %': optimal_pct,
                'Non-Optimal %': non_optimal_pct
            })
    
    sending_df = pd.DataFrame(sending_data)
    sending_df = sending_df.sort_values('Total Units', ascending=False)
    st.dataframe(sending_df, use_container_width=True)
    
    # Detailed receiving matrix (from where it gets)
    st.write("**📥 From Where It Receives**")
    incoming_data = []
    for origin in flow_matrix.index:
        total_flow = flow_matrix.loc[origin, region_sel]
        if total_flow > 0:
            optimal_flow = optimal_matrix.loc[origin, region_sel]
            non_optimal_flow = non_optimal_matrix.loc[origin, region_sel]
            optimal_pct = optimal_pct_matrix.loc[origin, region_sel]
            
            incoming_data.append({
                'Origin Region': origin,
                'Total Units': total_flow,
                'Optimal Units': optimal_flow,
                'Non-Optimal Units': non_optimal_flow,
                'Optimal %': optimal_pct,
                'Non-Optimal %': non_optimal_pct_matrix.loc[origin, region_sel]
            })
    
    if incoming_data:
        incoming_df = pd.DataFrame(incoming_data)
        incoming_df = incoming_df.sort_values('Total Units', ascending=False)
        st.dataframe(incoming_df, use_container_width=True)
    else:
        st.info("No incoming flow data available for this region.")
