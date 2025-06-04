import pandas as pd
import numpy as np
import logging # Keep for type hinting if needed

from src import utils

# Initialize logger
logger = utils.setup_logger(__name__)

# --- Missing Value Handlers ---
def handle_missing_ohlcv(df: pd.DataFrame,
                         price_ffill: bool = True,
                         volume_fill_zero: bool = True,
                         adj_close_ffill: bool = True) -> pd.DataFrame:
    """
    Handles missing values in OHLCV DataFrame.
    Ensures 'date' column is datetime and sorts by it.
    """
    if df.empty:
        logger.info("OHLCV DataFrame is empty. No missing values to handle.")
        return df

    if 'date' not in df.columns:
        logger.error("OHLCV DataFrame must contain a 'date' column.")
        raise utils.DataProcessingError("OHLCV DataFrame missing 'date' column.")

    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        logger.error(f"Error converting 'date' column to datetime: {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to convert 'date' column to datetime: {e}")

    df = df.sort_values(by='date').copy() # Use .copy() to avoid SettingWithCopyWarning

    price_cols = ['open', 'high', 'low', 'close']
    existing_price_cols = [col for col in price_cols if col in df.columns]

    if price_ffill and existing_price_cols:
        df[existing_price_cols] = df[existing_price_cols].ffill()
        logger.info(f"Forward-filled missing values for price columns: {existing_price_cols}")

    if adj_close_ffill and 'adj_close' in df.columns:
        df['adj_close'] = df['adj_close'].ffill()
        logger.info("Forward-filled missing values for 'adj_close' column.")

    if volume_fill_zero and 'volume' in df.columns:
        df['volume'] = df['volume'].fillna(0)
        logger.info("Filled missing values in 'volume' column with 0.")

    return df

def handle_missing_macro(df: pd.DataFrame,
                         value_ffill: bool = True,
                         value_interpolate: bool = False) -> pd.DataFrame:
    """
    Handles missing values in macro indicator DataFrame.
    Ensures 'date' column is datetime and sorts by it.
    """
    if df.empty:
        logger.info("Macro indicator DataFrame is empty. No missing values to handle.")
        return df

    if 'date' not in df.columns or 'value' not in df.columns:
        logger.error("Macro DataFrame must contain 'date' and 'value' columns.")
        raise utils.DataProcessingError("Macro DataFrame missing 'date' or 'value' columns.")

    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        logger.error(f"Error converting 'date' column to datetime: {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to convert 'date' column to datetime: {e}")

    df = df.sort_values(by='date').copy()

    if value_ffill:
        df['value'] = df['value'].ffill()
        logger.info("Forward-filled missing values for 'value' column in macro data.")
    elif value_interpolate: # Ensure this is mutually exclusive with ffill or applied after
        df['value'] = df['value'].interpolate(method='linear')
        logger.info("Linearly interpolated missing values for 'value' column in macro data.")

    return df

# --- Outlier Detection/Handling (Basic) ---
def detect_outliers_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    """
    Detects outliers in a Series using the IQR method.
    Returns a boolean Series where True indicates an outlier.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input must be a pandas Series.")
    if series.empty or series.isnull().all():
        logger.warning("Cannot detect outliers in an empty or all-NaN series.")
        return pd.Series([False] * len(series), index=series.index)

    # Ensure series is numeric
    numeric_series = pd.to_numeric(series, errors='coerce')
    # Calculate Q1, Q3, IQR on non-NaN values
    Q1 = numeric_series.quantile(0.25)
    Q3 = numeric_series.quantile(0.75)

    # If Q1 or Q3 is NaN (e.g. too many NaNs in series), cannot compute IQR
    if pd.isna(Q1) or pd.isna(Q3):
        logger.warning("Could not compute Q1/Q3 for outlier detection (possibly too many NaNs).")
        return pd.Series([False] * len(series), index=series.index)

    IQR = Q3 - Q1
    lower_bound = Q1 - k * IQR
    upper_bound = Q3 + k * IQR

    outliers = (numeric_series < lower_bound) | (numeric_series > upper_bound)
    # Ensure the result has the same index as the input series
    return outliers.reindex(series.index, fill_value=False)


def handle_outliers_percentage_change(df: pd.DataFrame, column: str, threshold: float = 0.5) -> pd.DataFrame:
    """
    Identifies and logs rows where the daily percentage change of 'column' exceeds 'threshold'.
    Current implementation only logs.
    """
    if column not in df.columns:
        logger.error(f"Column '{column}' not found for outlier detection.")
        return df
    if df.empty:
        return df

    # Ensure column is numeric
    numeric_col = pd.to_numeric(df[column], errors='coerce')
    if numeric_col.isnull().all():
        logger.warning(f"Column '{column}' is all NaN after numeric conversion. Skipping outlier detection.")
        return df

    pct_change = numeric_col.pct_change().abs()
    outlier_mask = pct_change > threshold

    outlier_indices = df.index[outlier_mask] # Get actual index labels
    if not outlier_indices.empty:
        logger.warning(f"Potential outliers detected in column '{column}' based on daily % change > {threshold*100}% "
                       f"at indices: {outlier_indices.tolist()}")
        # Future: df.loc[outlier_indices, column] = np.nan # or apply winsorization etc.
    else:
        logger.info(f"No significant outliers detected in '{column}' based on % change threshold {threshold*100}%.")

    return df


# --- Data Type Validation/Conversion ---
def ensure_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Converts specified columns to numeric, coercing errors to NaN."""
    df_copy = df.copy()
    for col in columns:
        if col in df_copy.columns:
            original_nan_count = df_copy[col].isnull().sum()
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
            new_nan_count = df_copy[col].isnull().sum()
            if new_nan_count > original_nan_count:
                logger.warning(f"Coerced NaNs introduced in column '{col}' during numeric conversion. "
                               f"Original NaNs: {original_nan_count}, New NaNs: {new_nan_count}.")
        else:
            logger.warning(f"Column '{col}' not found for numeric conversion.")
    return df_copy

def ensure_datetime_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Converts specified columns to datetime, coercing errors to NaT."""
    df_copy = df.copy()
    for col in columns:
        if col in df_copy.columns:
            original_nat_count = df_copy[col].isnull().sum()
            df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
            new_nat_count = df_copy[col].isnull().sum()
            if new_nat_count > original_nat_count:
                logger.warning(f"Coerced NaTs introduced in column '{col}' during datetime conversion. "
                               f"Original NaNs/NaTs: {original_nat_count}, New NaNs/NaTs: {new_nat_count}.")
        else:
            logger.warning(f"Column '{col}' not found for datetime conversion.")
    return df_copy

# --- Timezone and Frequency ---
def standardize_timezone_to_utc(df: pd.DataFrame, time_column: str = 'date') -> pd.DataFrame:
    """
    Standardizes the specified time column to UTC.
    If naive, assumes UTC. If aware, converts to UTC.
    """
    if time_column not in df.columns:
        logger.error(f"Time column '{time_column}' not found for timezone standardization.")
        return df
    if df.empty:
        return df

    df_copy = df.copy()
    time_col_series = df_copy[time_column]

    if not pd.api.types.is_datetime64_any_dtype(time_col_series):
        logger.warning(f"Column '{time_column}' is not datetime. Attempting conversion.")
        time_col_series = pd.to_datetime(time_col_series, errors='coerce')
        if time_col_series.isnull().all():
            logger.error(f"Failed to convert '{time_column}' to datetime. Cannot standardize timezone.")
            return df # Return original if conversion failed badly
        df_copy[time_column] = time_col_series


    if time_col_series.dt.tz is None: # Naive datetime
        logger.info(f"Time column '{time_column}' is timezone-naive. Assuming UTC and localizing.")
        df_copy[time_column] = time_col_series.dt.tz_localize('UTC')
    else: # Timezone-aware
        logger.info(f"Time column '{time_column}' is timezone-aware. Converting to UTC.")
        df_copy[time_column] = time_col_series.dt.tz_convert('UTC')

    return df_copy

def resample_data(df: pd.DataFrame, rule: str, time_column: str = 'date',
                  ohlc_agg: dict | None = None) -> pd.DataFrame:
    """
    Resamples time-series data to a specified frequency.

    Args:
        df: DataFrame with a time column.
        rule: The offset string or object representing target conversion (e.g., 'W', 'M', 'Q').
        time_column: Name of the datetime column to use as index.
        ohlc_agg: Aggregation dictionary for OHLCV data.
                  Example: {'open': 'first', 'high': 'max', 'low': 'min',
                            'close': 'last', 'volume': 'sum'}
                  If None, attempts a basic mean aggregation if other columns exist.

    Returns:
        Resampled DataFrame.
    """
    if time_column not in df.columns:
        logger.error(f"Time column '{time_column}' not found for resampling.")
        raise utils.DataProcessingError(f"Time column '{time_column}' not found.")
    if df.empty:
        return df

    df_copy = df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df_copy[time_column]):
        logger.info(f"Time column '{time_column}' is not datetime. Attempting conversion for resampling.")
        df_copy[time_column] = pd.to_datetime(df_copy[time_column], errors='coerce')
        if df_copy[time_column].isnull().all():
            logger.error(f"Failed to convert '{time_column}' to datetime. Cannot resample.")
            raise utils.DataProcessingError(f"Cannot resample due to invalid time column '{time_column}'.")

    # Set time_column as index for resampling
    try:
        df_copy = df_copy.set_index(time_column)
    except Exception as e:
        logger.error(f"Failed to set '{time_column}' as index for resampling: {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to set index for resampling: {e}")

    # Default aggregation if none provided and other numeric columns exist
    if ohlc_agg is None:
        numeric_cols = df_copy.select_dtypes(include=np.number).columns
        if not numeric_cols.empty:
            ohlc_agg = {col: 'mean' for col in numeric_cols} # Basic mean for other numeric columns
            logger.info(f"No ohlc_agg provided. Using default mean aggregation for numeric columns: {numeric_cols.tolist()}")
        else:
            logger.warning("No ohlc_agg and no other numeric columns to aggregate. Resampling might produce empty results beyond count.")
            # Resample will still count if no agg func and no numeric columns
            # Or we can raise an error if ohlc_agg is strictly required
            # return df_copy.resample(rule).size().to_frame(name='count') # Example of what happens

    try:
        if ohlc_agg: # If there's something to aggregate
            resampled_df = df_copy.resample(rule).agg(ohlc_agg)
        else: # If no numeric columns and no ohlc_agg, resample might just give counts or error
             # For robustness, let's provide a size if nothing else to aggregate
            logger.warning("Attempting to resample without specific aggregation for numeric columns.")
            resampled_df = df_copy.resample(rule).size().to_frame(name='count_in_period')


        logger.info(f"Data successfully resampled to rule '{rule}'.")
        return resampled_df.reset_index() # Return with time_column as a column again
    except Exception as e:
        logger.error(f"Error during resampling with rule '{rule}': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Resampling failed: {e}")


if __name__ == '__main__':
    logger.info("--- Running data_cleaner.py direct execution tests ---")

    # Sample OHLCV Data
    ohlcv_data = {
        'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']),
        'open': [10, 11, np.nan, 13, 14],
        'high': [12, 11.5, 12.5, np.nan, 14.5],
        'low': [9, 10.5, 11, 12, 13.5],
        'close': [11, np.nan, 12, 13.5, 14.2],
        'adj_close': [11, 10.8, 12, np.nan, 14.2],
        'volume': [1000, 1200, np.nan, 1500, 1300.0]
    }
    ohlcv_df = pd.DataFrame(ohlcv_data)
    ohlcv_df_original_nans = ohlcv_df.isnull().sum().sum()

    logger.info(f"Original OHLCV:\n{ohlcv_df}\nNaNs:\n{ohlcv_df.isnull().sum()}")
    cleaned_ohlcv = handle_missing_ohlcv(ohlcv_df.copy())
    logger.info(f"Cleaned OHLCV:\n{cleaned_ohlcv}\nNaNs:\n{cleaned_ohlcv.isnull().sum()}")
    assert cleaned_ohlcv.isnull().sum().sum() < ohlcv_df_original_nans
    assert cleaned_ohlcv['volume'].isnull().sum() == 0
    assert cleaned_ohlcv['open'].iloc[2] == 11 # Forward filled from 2023-01-02

    # Sample Macro Data
    macro_data = {
        'date': pd.to_datetime(['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01']),
        'indicator_name': ['GDP', 'GDP', 'GDP', 'GDP'],
        'value': [100, np.nan, 102, 103.5]
    }
    macro_df = pd.DataFrame(macro_data)
    logger.info(f"Original Macro:\n{macro_df}\nNaNs:\n{macro_df.isnull().sum()}")
    cleaned_macro = handle_missing_macro(macro_df.copy())
    logger.info(f"Cleaned Macro (ffill):\n{cleaned_macro}\nNaNs:\n{cleaned_macro.isnull().sum()}")
    assert cleaned_macro['value'].isnull().sum() == 0
    assert cleaned_macro['value'].iloc[1] == 100 # Forward filled

    # Outlier Detection
    outlier_series = pd.Series([10, 12, 11, 9, 15, 10, 12, 100, -50, 13, 11])
    outliers = detect_outliers_iqr(outlier_series)
    logger.info(f"Outlier series: {outlier_series.values}")
    logger.info(f"Detected outliers (IQR): {outlier_series[outliers].values}")
    assert outliers.iloc[7] == True # 100
    assert outliers.iloc[8] == True # -50

    # Percentage Change Outlier Logging
    ohlcv_df_for_pct = cleaned_ohlcv.copy()
    ohlcv_df_for_pct.loc[len(ohlcv_df_for_pct)] = ['2023-01-06', 14, 14.5, 13.5, 30.0, 30.0, 1300] # Introduce large jump in close
    ohlcv_df_for_pct['date'] = pd.to_datetime(ohlcv_df_for_pct['date'])
    logger.info(f"OHLCV for Pct Change Outlier Test:\n{ohlcv_df_for_pct}")
    handle_outliers_percentage_change(ohlcv_df_for_pct, 'close', threshold=0.5) # Expect log for 30.0

    # Data Type Conversion
    type_test_df = pd.DataFrame({
        'numeric_col': ['10.5', '20', 'abc', '30.0'],
        'datetime_col': ['2023-01-01', '2023/02/15', 'not-a-date', '2023-Mar-20'],
        'int_col': ['1','2','3','4.5'] # Will become float then int if desired
    })
    logger.info(f"Original types:\n{type_test_df.dtypes}")
    numeric_ensured_df = ensure_numeric_columns(type_test_df.copy(), ['numeric_col', 'int_col'])
    logger.info(f"Numeric ensured types:\n{numeric_ensured_df.dtypes}")
    logger.info(f"Numeric ensured df:\n{numeric_ensured_df}")
    assert pd.api.types.is_float_dtype(numeric_ensured_df['numeric_col'])
    assert numeric_ensured_df['numeric_col'].isnull().sum() == 1 # 'abc' became NaN

    datetime_ensured_df = ensure_datetime_columns(type_test_df.copy(), ['datetime_col'])
    logger.info(f"Datetime ensured types:\n{datetime_ensured_df.dtypes}")
    logger.info(f"Datetime ensured df:\n{datetime_ensured_df}")
    assert pd.api.types.is_datetime64_any_dtype(datetime_ensured_df['datetime_col'])
    assert datetime_ensured_df['datetime_col'].isnull().sum() == 1 # 'not-a-date' became NaT

    # Timezone Standardization
    tz_test_df = pd.DataFrame({'date': pd.to_datetime(['2023-01-01 10:00:00', '2023-01-02 12:00:00'])})
    tz_std_df = standardize_timezone_to_utc(tz_test_df.copy())
    logger.info(f"Timezone standardized (naive assumed UTC):\n{tz_std_df['date']}")
    assert tz_std_df['date'].dt.tz is not None
    assert str(tz_std_df['date'].dt.tz) == 'UTC'

    tz_aware_df = pd.DataFrame({'date': pd.to_datetime(['2023-01-01 10:00:00-05:00', '2023-01-02 12:00:00-05:00'])})
    tz_std_aware_df = standardize_timezone_to_utc(tz_aware_df.copy())
    logger.info(f"Timezone standardized (aware converted to UTC):\n{tz_std_aware_df['date']}")
    assert str(tz_std_aware_df['date'].dt.tz) == 'UTC'
    assert tz_std_aware_df['date'].iloc[0].hour == 15 # 10:00 EST is 15:00 UTC

    # Resampling
    # Use cleaned_ohlcv with its datetime 'date' column
    resample_test_df = cleaned_ohlcv[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
    resample_test_df['date'] = pd.to_datetime(resample_test_df['date']) # ensure datetime

    agg_rules = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    weekly_df = resample_data(resample_test_df, 'W', ohlc_agg=agg_rules)
    logger.info(f"Weekly resampled OHLCV:\n{weekly_df}")
    assert not weekly_df.empty
    assert 'open' in weekly_df.columns # Check if aggregation was applied

    # Test resampling with no agg_rules (should use mean for numeric or count)
    simple_resample_df = resample_test_df[['date', 'close']].copy() # Just date and close
    weekly_simple_df = resample_data(simple_resample_df, 'W')
    logger.info(f"Weekly resampled (default agg - mean for 'close'):\n{weekly_simple_df}")
    assert 'close' in weekly_simple_df.columns or 'count_in_period' in weekly_simple_df.columns

    logger.info("--- data_cleaner.py direct execution tests completed ---")
