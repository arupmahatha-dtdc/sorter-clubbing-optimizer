import pandas as pd

def filter_and_sum(
    type_=None, mode=None,   # <-- First type, then mode
    org_zone=None, org_region=None, org_city=None, org_branch=None, org_product=None,
    des_zone=None, des_region=None, des_city=None, des_branch=None,
    csv_path="data.csv"
):
    """
    Filters the data.csv file based on the provided parameters and returns the sum of the filtered values.
    Parameters can be None to indicate no filtering on that field.
    The data starts from row 7 (index 6) and column 6 (index 5).
    Column headers are in rows 0-5 (indexes 0-5).
    
    - type_ : Column "type" filter
    - mode : Derived from org_product (Air = {EP,BP}, Ground = {ES,BS,GP})
    - org_* : Filters for origin
    - des_* : Filters for destination
    """
    # Read CSV
    df = pd.read_csv(csv_path, header=None, low_memory=False)

    # Column headers (destination side)
    col_header_rows = df.iloc[0:6, 5:]
    col_tuples = list(zip(*[col_header_rows.iloc[i].values for i in range(6)]))
    col_index = pd.MultiIndex.from_tuples(
        col_tuples,
        names=['ignored', 'type', 'des_zone', 'des_region', 'des_city', 'des_branch']
    )

    # Row headers (origin side)
    row_header_cols = df.iloc[6:, 0:5]
    row_tuples = [tuple(row_header_cols.iloc[i].values) for i in range(row_header_cols.shape[0])]

    # MultiIndex for rows
    row_index = pd.MultiIndex.from_tuples(
        row_tuples,
        names=['org_zone', 'org_region', 'org_city', 'org_branch', 'org_product']
    )

    # Add derived "mode"
    product_to_mode = {
        "EP": "Air", "BP": "Air",
        "ES": "Ground", "BS": "Ground", "GP": "Ground"
    }
    modes = [product_to_mode.get(prod, "Unknown") for prod in row_index.get_level_values("org_product")]
    row_index = pd.MultiIndex.from_arrays(
        [
            row_index.get_level_values("org_zone"),
            row_index.get_level_values("org_region"),
            row_index.get_level_values("org_city"),
            row_index.get_level_values("org_branch"),
            row_index.get_level_values("org_product"),
            modes
        ],
        names=['org_zone', 'org_region', 'org_city', 'org_branch', 'org_product', 'mode']
    )

    # Extract numeric data
    data_values = df.iloc[6:, 5:]
    data_values = data_values.apply(pd.to_numeric, errors='coerce')
    data_values.index = row_index
    data_values.columns = col_index

    # Apply row filters
    row_filters = [org_zone, org_region, org_city, org_branch, org_product, mode]
    row_index_names = ['org_zone', 'org_region', 'org_city', 'org_branch', 'org_product', 'mode']
    if any(val is not None for val in row_filters):
        row_mask = pd.Series(True, index=data_values.index)
        for i, val in enumerate(row_filters):
            if val is not None:
                row_mask &= (data_values.index.get_level_values(row_index_names[i]) == val)
        data_values = data_values[row_mask]

    # Apply column filters
    col_filters = [type_, des_zone, des_region, des_city, des_branch]
    col_index_names = ['ignored', 'type', 'des_zone', 'des_region', 'des_city', 'des_branch']
    if any(val is not None for val in col_filters):
        col_mask = pd.Series(True, index=data_values.columns)
        for i, val in enumerate(col_filters):
            if val is not None:
                col_mask &= (data_values.columns.get_level_values(col_index_names[i+1]) == val)  # +1 skips "ignored"
        data_values = data_values.loc[:, col_mask]

    # Return sum
    return data_values.values.sum()