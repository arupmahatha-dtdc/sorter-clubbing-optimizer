import pandas as pd
import numpy as np
import json

# =========================
# Load & Melt Data
# =========================
def load_data():
    df_abs = pd.read_csv("all_data.csv")
    df_pct = pd.read_csv("all_data_percentage.csv")

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
    return df_abs, df_pct, df_abs_long, df_pct_long, df_merge


# =========================
# Bag Summary (Above Threshold)
# =========================
def build_bag_summary(df_merge, thresholds):
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
            "Branches": ", ".join(branch_list) if branch_list else ""
        })

    return pd.DataFrame(results)


# =========================
# Elbow Finder
# =========================
def find_elbow(x, y):
    if len(x) < 2:   # not enough points
        return 0
    p1, p2 = np.array([x[0], y[0]]), np.array([x[-1], y[-1]])
    line_vec = (p2 - p1) / np.linalg.norm(p2 - p1)
    distances = []
    for i in range(len(x)):
        p = np.array([x[i], y[i]])
        proj_len = np.dot(p - p1, line_vec)
        proj_point = p1 + proj_len * line_vec
        distances.append(np.linalg.norm(p - proj_point))
    return int(np.argmax(distances))


# =========================
# Optimal Branches (Elbow Method)
# =========================
def build_optimal_branches(df_bag, df_pct_long):
    optimal_results = []
    for _, row in df_bag.iterrows():
        branches_str = row["Branches"]
        if not isinstance(branches_str, str) or not branches_str.strip():
            continue

        branches = [b.strip() for b in branches_str.split(",")]
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
            "Branches": ", ".join(opt_branches)
        })

    return pd.DataFrame(optimal_results)


# =========================
# Final Sorting Locations
# =========================
def build_final_sorting(df_optimal):
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

    df_sum_opt = df_optimal.groupby(["Region", "Type"])["Optimal_Num_Branches"].sum().reset_index()
    df_sum_opt = df_sum_opt.rename(columns={"Optimal_Num_Branches": "Sorting_Locations_for_Optimal_Branches"})

    df_fd = pd.merge(df_sum_opt, df_region_counts, on="Region", how="left")
    df_fd["Sorting_Location_Needed"] = (
        df_fd["Sorting_Locations_for_Optimal_Branches"] + 60 + 2 * df_fd["Self_Branches"]
    )
    return df_fd


# =========================
# Flow Analysis Functions
# =========================
def load_flow_analysis_data():
    """Load the flow analysis CSV files"""
    try:
        df_flow = pd.read_csv("region_to_region_flow_analysis.csv")
        df_receiving = pd.read_csv("region_receiving_analysis.csv")
        return df_flow, df_receiving
    except FileNotFoundError:
        print("Flow analysis CSV files not found. Please run the flow analysis code blocks first.")
        return None, None


def get_region_flow_summary(df_flow, region, type_name):
    """Get flow summary for a specific region and type"""
    if df_flow is None:
        return None, None
    
    # Filter data for the region and type
    region_data = df_flow[(df_flow['Origin_Region'] == region) & (df_flow['Type'] == type_name)]
    
    if region_data.empty:
        return None, None
    
    # Calculate sending summary
    sending_summary = {
        'Total_Units_Sent': region_data['Total_Flow_Units'].sum(),
        'Optimal_Units_Sent': region_data['Optimal_Flow_Units'].sum(),
        'Non_Optimal_Units_Sent': region_data['Non_Optimal_Flow_Units'].sum(),
        'Optimal_Percentage_Sent': (region_data['Optimal_Flow_Units'].sum() / region_data['Total_Flow_Units'].sum() * 100) if region_data['Total_Flow_Units'].sum() > 0 else 0,
        'Non_Optimal_Percentage_Sent': (region_data['Non_Optimal_Flow_Units'].sum() / region_data['Total_Flow_Units'].sum() * 100) if region_data['Total_Flow_Units'].sum() > 0 else 0
    }
    
    # Get detailed sending matrix (where it sends)
    sending_matrix = region_data[region_data['Total_Flow_Units'] > 0].copy()
    sending_matrix = sending_matrix.sort_values('Total_Flow_Units', ascending=False)
    
    return sending_summary, sending_matrix


def get_region_receiving_summary(df_receiving, region, type_name):
    """Get receiving summary for a specific region and type"""
    if df_receiving is None:
        return None
    
    # Filter data for the region and type
    region_data = df_receiving[(df_receiving['Region'] == region) & (df_receiving['Type'] == type_name)]
    
    if region_data.empty:
        return None
    
    return region_data.iloc[0].to_dict()


def get_all_india_flow_summary(df_flow, df_receiving, type_name):
    """Get flow summary for All India"""
    if df_flow is None or df_receiving is None:
        return None, None, None
    
    # Filter data for the type
    flow_data = df_flow[df_flow['Type'] == type_name]
    receiving_data = df_receiving[df_receiving['Type'] == type_name]
    
    if flow_data.empty or receiving_data.empty:
        return None, None, None
    
    # Calculate All India sending summary
    all_india_sending = {
        'Total_Units_Sent': flow_data['Total_Flow_Units'].sum(),
        'Optimal_Units_Sent': flow_data['Optimal_Flow_Units'].sum(),
        'Non_Optimal_Units_Sent': flow_data['Non_Optimal_Flow_Units'].sum(),
        'Optimal_Percentage_Sent': (flow_data['Optimal_Flow_Units'].sum() / flow_data['Total_Flow_Units'].sum() * 100) if flow_data['Total_Flow_Units'].sum() > 0 else 0,
        'Non_Optimal_Percentage_Sent': (flow_data['Non_Optimal_Flow_Units'].sum() / flow_data['Total_Flow_Units'].sum() * 100) if flow_data['Total_Flow_Units'].sum() > 0 else 0
    }
    
    # Calculate All India receiving summary
    all_india_receiving = {
        'Total_Units_Received': receiving_data['Total_Units_Received'].sum(),
        'Optimal_Units_Received': receiving_data['Optimal_Units_Received'].sum(),
        'Non_Optimal_Units_Received': receiving_data['Non_Optimal_Units_Received'].sum(),
        'Optimal_Percentage_Received': (receiving_data['Optimal_Units_Received'].sum() / receiving_data['Total_Units_Received'].sum() * 100) if receiving_data['Total_Units_Received'].sum() > 0 else 0,
        'Non_Optimal_Percentage_Received': (receiving_data['Non_Optimal_Units_Received'].sum() / receiving_data['Total_Units_Received'].sum() * 100) if receiving_data['Total_Units_Received'].sum() > 0 else 0
    }
    
    # Get top sending destinations
    top_destinations = flow_data.groupby('Destination_Region').agg({
        'Total_Flow_Units': 'sum',
        'Optimal_Flow_Units': 'sum',
        'Non_Optimal_Flow_Units': 'sum'
    }).reset_index()
    top_destinations['Optimal_Percentage'] = (top_destinations['Optimal_Flow_Units'] / top_destinations['Total_Flow_Units'] * 100).round(2)
    top_destinations = top_destinations.sort_values('Total_Flow_Units', ascending=False)
    
    return all_india_sending, all_india_receiving, top_destinations
