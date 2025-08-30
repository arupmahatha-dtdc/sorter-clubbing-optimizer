import pandas as pd

def filter_and_sum(
    org_zone=None, org_region=None, org_city=None, org_branch=None, org_product=None,
    type_=None, des_zone=None, des_region=None, des_city=None, des_branch=None,
    csv_path="data.csv"
):
    """
    Filters the data.csv file based on the provided parameters and returns the sum of the filtered values.
    Parameters can be None to indicate no filtering on that field.
    The data starts from row 7 (index 6) and column 6 (index 5).
    Column headers are in rows 0-5 (indexes 0-5).
    """
    # Read the CSV file with low_memory=False to handle mixed data types
    df = pd.read_csv(csv_path, header=None, low_memory=False)
    
    # The first 6 rows (0-5) are column headers for the data columns
    # The first 5 columns (0-4) are row headers for the data rows
    # Data starts from row 7 (index 6) and column 6 (index 5)
    
    # Build MultiIndex for columns (destination) - include row 5 for branch names
    col_header_rows = df.iloc[0:6, 5:]  # Rows 0-5 (indexes 0-5)
    col_tuples = list(zip(*[col_header_rows.iloc[i].values for i in range(6)]))
    col_index = pd.MultiIndex.from_tuples(col_tuples, names=['ignored', 'type', 'des_zone', 'des_region', 'des_city', 'des_branch'])
    
    # Build MultiIndex for rows (origin)
    row_header_cols = df.iloc[6:, 0:5]  # Start from row 7 (index 6)
    row_tuples = [tuple(row_header_cols.iloc[i].values) for i in range(row_header_cols.shape[0])]
    row_index = pd.MultiIndex.from_tuples(row_tuples, names=['org_zone', 'org_region', 'org_city', 'org_branch', 'org_product'])
    
    # Extract the data values and convert to numeric immediately
    data_values = df.iloc[6:, 5:]  # Start from row 7 (index 6)
    # Convert all data to numeric before proceeding
    data_values = data_values.apply(pd.to_numeric, errors='coerce')
    data_values.index = row_index
    data_values.columns = col_index
    
    # Apply filters for rows
    row_filters = [org_zone, org_region, org_city, org_branch, org_product]
    row_index_names = ['org_zone', 'org_region', 'org_city', 'org_branch', 'org_product']
    if any(val is not None for val in row_filters):
        row_mask = pd.Series([True] * data_values.shape[0], index=data_values.index)
        for i, val in enumerate(row_filters):
            if val is not None:
                row_mask &= (data_values.index.get_level_values(row_index_names[i]) == val)
        data_values = data_values[row_mask]
    
    # Apply filters for columns
    col_filters = [type_, des_zone, des_region, des_city, des_branch]
    col_index_names = ['ignored', 'type', 'des_zone', 'des_region', 'des_city', 'des_branch']
    if any(val is not None for val in col_filters):
        col_mask = pd.Series([True] * data_values.shape[1], index=data_values.columns)
        for i, val in enumerate(col_filters):
            if val is not None:
                col_mask &= (data_values.columns.get_level_values(col_index_names[i+1]) == val)  # +1 to skip ignored level
        data_values = data_values.loc[:, col_mask]
    
    # Sum the numeric values (already converted)
    return data_values.values.sum()