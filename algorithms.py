import pandas as pd

def filter_and_sum(
    type_=None,
    mode=None,
    org_zone=None, org_region=None, org_city=None, org_branch_code=None, org_product=None,
    des_zone=None, des_region=None, des_city=None, des_branch_code=None,
    csv_path="data.csv"
):
    # --- Read CSV with multi-index and multi-columns ---
    df = pd.read_csv(
        csv_path,
        skiprows=1,
        header=[0, 1, 2, 3, 4],
        index_col=[0, 1, 2, 3, 5, 6]
    )

    # Name the index and columns for clarity
    df.index.set_names(
        ["org_zone", "org_region", "org_city", "org_branch_code", "mode", "org_product"],
        inplace=True
    )
    df.columns.set_names(
        ["type", "des_zone", "des_region", "des_city", "des_branch_code"],
        inplace=True
    )

    # --- Convert entire dataframe to numeric ---
    df = df.apply(pd.to_numeric, errors="coerce")

    # --- Apply row filters ---
    row_filters = [org_zone, org_region, org_city, org_branch_code, mode, org_product]
    if any(val is not None for val in row_filters):
        row_mask = pd.Series(True, index=df.index)
        for level_name, value in zip(df.index.names, row_filters):
            if value is not None:
                row_mask &= df.index.get_level_values(level_name) == value
        df = df[row_mask]

    # --- Apply column filters ---
    col_filters = [type_, des_zone, des_region, des_city, des_branch_code]
    if any(val is not None for val in col_filters):
        col_mask = pd.Series(True, index=df.columns)
        for level_name, value in zip(df.columns.names, col_filters):
            if value is not None:
                col_mask &= df.columns.get_level_values(level_name) == value
        df = df.loc[:, col_mask]

    # --- Return numeric sum ---
    return df.to_numpy().sum()