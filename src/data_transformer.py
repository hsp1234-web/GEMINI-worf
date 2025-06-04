import pandas as pd
import numpy as np
import logging # Keep for type hinting if needed

from src import utils

# Initialize logger
logger = utils.setup_logger(__name__)

# --- OHLCV to Text Summary ---
def summarize_ohlcv_for_llm(df_ohlcv: pd.DataFrame, period_desc: str = "this period") -> str:
    """
    Generates a textual summary of OHLCV data for a given period.

    Args:
        df_ohlcv: DataFrame with 'date', 'open', 'high', 'low', 'close', 'volume'.
                  Should be sorted by date.
        period_desc: A string describing the period (e.g., "this week", "January 2023").

    Returns:
        A string summarizing the OHLCV data.
    """
    if df_ohlcv.empty:
        return f"No OHLCV data available for {period_desc} to summarize."

    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df_ohlcv.columns]
    if missing_cols:
        logger.error(f"OHLCV DataFrame for summary is missing required columns: {missing_cols}")
        return f"Incomplete OHLCV data for {period_desc}. Missing: {', '.join(missing_cols)}."

    # Ensure data types are correct for calculations
    try:
        df_ohlcv['date'] = pd.to_datetime(df_ohlcv['date'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_ohlcv[col] = pd.to_numeric(df_ohlcv[col], errors='coerce')
    except Exception as e:
        logger.error(f"Error converting OHLCV data types for summary: {e}", exc_info=True)
        return f"Error processing data types for {period_desc} summary."

    df_ohlcv = df_ohlcv.sort_values(by='date').dropna(subset=['open', 'high', 'low', 'close', 'volume'])
    if df_ohlcv.empty:
        return f"OHLCV data for {period_desc} is empty after removing NaNs."

    start_date = df_ohlcv['date'].iloc[0].strftime('%Y-%m-%d')
    end_date = df_ohlcv['date'].iloc[-1].strftime('%Y-%m-%d')

    first_open = df_ohlcv['open'].iloc[0]
    last_close = df_ohlcv['close'].iloc[-1]

    overall_return = (last_close - first_open) / first_open if first_open != 0 else 0.0

    highest_high = df_ohlcv['high'].max()
    lowest_low = df_ohlcv['low'].min()

    avg_volume = df_ohlcv['volume'].mean()

    # Volatility: (High - Low) / Open over the period (simplified)
    period_open_avg = df_ohlcv['open'].mean() # Could also use first_open
    volatility_range_over_open = (highest_high - lowest_low) / period_open_avg if period_open_avg != 0 else 0.0

    # Trend description (simple logic)
    if overall_return > 0.02: # Example threshold for uptrend
        trend_desc = "uptrend"
    elif overall_return < -0.02: # Example threshold for downtrend
        trend_desc = "downtrend"
    else:
        trend_desc = "sideways movement"

    peak_price_date = df_ohlcv.loc[df_ohlcv['high'].idxmax(), 'date'].strftime('%Y-%m-%d')
    bottom_price_date = df_ohlcv.loc[df_ohlcv['low'].idxmin(), 'date'].strftime('%Y-%m-%d')

    summary = (
        f"Summary for {period_desc} ({start_date} to {end_date}):\n"
        f"- Overall return: {overall_return:.2%}.\n"
        f"- Price range: Low {lowest_low:.2f} to High {highest_high:.2f}.\n"
        f"- Average daily volume: {avg_volume:,.0f}.\n"
        f"- Volatility (period range / avg open): {volatility_range_over_open:.2%}.\n"
        f"- General trend: {trend_desc}.\n"
        f"- Key price points: Started at {first_open:.2f} (on {start_date}), ended at {last_close:.2f} (on {end_date}).\n"
        f"- Period peak high: {highest_high:.2f} (on {peak_price_date}), period bottom low: {lowest_low:.2f} (on {bottom_price_date})."
    )
    return summary

# --- Macro Indicator to Text Summary ---
def summarize_macro_indicator_for_llm(series_macro: pd.Series,
                                      indicator_name: str,
                                      period_desc: str = "this period") -> str:
    """
    Generates a textual summary of a macro indicator series.

    Args:
        series_macro: Pandas Series with DatetimeIndex and indicator values. Should be sorted.
        indicator_name: Name of the macro indicator (e.g., "GDP Growth Rate").
        period_desc: A string describing the period.

    Returns:
        A string summarizing the macro indicator data.
    """
    if not isinstance(series_macro, pd.Series):
        logger.error("Input 'series_macro' must be a pandas Series.")
        return f"Invalid data type for {indicator_name} summary."

    if series_macro.empty:
        return f"No data available for macro indicator '{indicator_name}' for {period_desc}."

    # Ensure Series is numeric and index is datetime
    try:
        series_macro = pd.to_numeric(series_macro, errors='coerce')
        if not isinstance(series_macro.index, pd.DatetimeIndex):
            series_macro.index = pd.to_datetime(series_macro.index, errors='coerce')
    except Exception as e:
        logger.error(f"Error converting macro series data types for summary: {e}", exc_info=True)
        return f"Error processing data types for {indicator_name} summary."

    series_macro = series_macro.sort_index().dropna()
    if series_macro.empty:
        return f"Data for macro indicator '{indicator_name}' for {period_desc} is empty after removing NaNs."

    start_date = series_macro.index[0].strftime('%Y-%m-%d')
    end_date = series_macro.index[-1].strftime('%Y-%m-%d')

    latest_date = series_macro.index[-1]
    latest_value = series_macro.iloc[-1]

    prev_date_str = "N/A"
    prev_value_str = "N/A"
    change_str = "N/A"
    pct_change_str = "N/A"

    if len(series_macro) >= 2:
        prev_date = series_macro.index[-2]
        prev_value = series_macro.iloc[-2]
        change = latest_value - prev_value
        pct_change = (change / prev_value) if prev_value != 0 else 0.0

        prev_date_str = prev_date.strftime('%Y-%m-%d')
        prev_value_str = f"{prev_value:.2f}"
        change_str = f"{change:.2f}"
        pct_change_str = f"{pct_change:.2%}"

    min_val = series_macro.min()
    max_val = series_macro.max()

    summary = (
        f"Macro Indicator Summary for '{indicator_name}' ({period_desc}, data from {start_date} to {end_date}):\n"
        f"- Latest value ({latest_date.strftime('%Y-%m-%d')}): {latest_value:.2f}.\n"
        f"- Previous value ({prev_date_str}): {prev_value_str}.\n"
        f"- Change from previous: {change_str} ({pct_change_str}).\n"
        f"- Range in period: Min {min_val:.2f} to Max {max_val:.2f}."
    )
    return summary

# --- Basic Financial Calculations ---
def calculate_returns(price_series: pd.Series, period: int = 1) -> pd.Series:
    """Calculates percentage change returns for a given period."""
    if not isinstance(price_series, pd.Series):
        raise TypeError("Input must be a pandas Series.")
    if price_series.empty:
        return pd.Series(dtype=float)
    return price_series.pct_change(periods=period)

def calculate_rolling_volatility_std_dev(returns_series: pd.Series, window: int = 20) -> pd.Series:
    """
    Calculates rolling standard deviation of returns as a measure of volatility.
    Note: Annualization factor (e.g. * np.sqrt(252)) is often applied depending on context
          and return frequency. This function returns the direct rolling std dev of the input returns.
    """
    if not isinstance(returns_series, pd.Series):
        raise TypeError("Input must be a pandas Series.")
    if returns_series.empty or len(returns_series) < window :
        logger.warning(f"Returns series is too short for window {window}. Returning NaNs or empty series.")
        return pd.Series([np.nan] * len(returns_series), index=returns_series.index, dtype=float)

    return returns_series.rolling(window=window).std()


if __name__ == '__main__':
    logger.info("--- Running data_transformer.py direct execution tests ---")

    # Sample OHLCV Data
    ohlcv_data_dict = {
        'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']),
        'open': [100, 102, 101, 105, 103],
        'high': [103, 104, 106, 107, 105],
        'low': [99, 101, 100, 103, 102],
        'close': [102, 101, 105, 103, 104],
        'volume': [10000, 12000, 11000, 15000, 13000]
    }
    ohlcv_df_sample = pd.DataFrame(ohlcv_data_dict)

    logger.info(f"Sample OHLCV DataFrame:\n{ohlcv_df_sample}")
    ohlcv_summary = summarize_ohlcv_for_llm(ohlcv_df_sample.copy(), period_desc="first week of Jan 2023")
    logger.info(f"OHLCV Summary:\n{ohlcv_summary}")
    assert "Overall return" in ohlcv_summary
    assert "Average daily volume" in ohlcv_summary

    # Test with empty OHLCV df
    empty_ohlcv_summary = summarize_ohlcv_for_llm(pd.DataFrame(columns=ohlcv_df_sample.columns), period_desc="empty period")
    logger.info(f"Empty OHLCV Summary:\n{empty_ohlcv_summary}")
    assert "No OHLCV data available" in empty_ohlcv_summary


    # Sample Macro Data
    macro_dates = pd.to_datetime(['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01'])
    macro_values = [3.0, 3.2, 3.1, 3.3]
    macro_series_sample = pd.Series(macro_values, index=macro_dates, name="Unemployment Rate")

    logger.info(f"Sample Macro Series:\n{macro_series_sample}")
    macro_summary = summarize_macro_indicator_for_llm(macro_series_sample.copy(),
                                                      indicator_name="Unemployment Rate",
                                                      period_desc="Q1 2023")
    logger.info(f"Macro Summary:\n{macro_summary}")
    assert "Latest value" in macro_summary
    assert "Range in period" in macro_summary

    # Test with single value macro series
    single_value_macro = pd.Series([5.0], index=[pd.to_datetime('2023-05-01')])
    single_macro_summary = summarize_macro_indicator_for_llm(single_value_macro, "CPI", "May 2023")
    logger.info(f"Single Value Macro Summary:\n{single_macro_summary}")
    assert "Previous value (N/A)" in single_macro_summary


    # Financial Calculations
    price_s = pd.Series([100, 102, 101, 105, 103])
    returns_s = calculate_returns(price_s)
    logger.info(f"Price Series: {price_s.values}")
    logger.info(f"Returns Series: {returns_s.values}")
    expected_returns = np.array([np.nan, 0.02, -0.00980392,  0.03960396, -0.01904762])
    pd.testing.assert_series_equal(returns_s, pd.Series(expected_returns), check_dtype=False, atol=1e-5)


    volatility_s = calculate_rolling_volatility_std_dev(returns_s.dropna(), window=2) # Use dropna for clean returns
    logger.info(f"Volatility (rolling std dev of returns, window=2):\n{volatility_s}")
    # Manual check for rolling std of [0.02, -0.00980392, 0.03960396, -0.01904762] with window 2
    # For [0.02, -0.00980392], std is np.std([0.02, -0.00980392], ddof=0) if using population std in rolling. Pandas uses ddof=1 by default.
    # np.std([0.02, -0.00980392], ddof=1) approx 0.02107
    # np.std([-0.00980392, 0.03960396], ddof=1) approx 0.035
    # np.std([0.03960396, -0.01904762], ddof=1) approx 0.041
    assert volatility_s.isnull().sum() == 1 # First entry is NaN due to window
    assert not volatility_s.dropna().empty

    logger.info("--- data_transformer.py direct execution tests completed ---")
