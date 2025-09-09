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
                            # Create a DataFrame with both codes and names
                            branch_codes = [b.strip() for b in branch_codes_str.split(",") if b.strip()]
                            branch_data = []
                            for code in branch_codes:
                                name = branch_name_mapping.get(code, "Name not found")
                                branch_data.append({"Branch Code": code, "Branch Name": name})
                            st.table(pd.DataFrame(branch_data))
                        else:
                            st.write("No optimal branches found")
