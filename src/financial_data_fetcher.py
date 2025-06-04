# coding: utf-8
"""
This script fetches financial data based on keywords found in monthly posts,
textualizes the data, and integrates it back into the post data.
"""
import json
import os
import re
from datetime import datetime, timedelta
from calendar import monthrange
import yfinance as yf
import pandas_datareader.data as pdr
import pandas as pd

# Configuration
INPUT_JSON_FILE = "monthly_posts_raw.json" # Should be in the root project directory for this task
OUTPUT_JSON_FILE = "monthly_posts_with_financial_data.json" # Will be created in the root
FRED_API_KEY = os.getenv("FRED_API_KEY")
# Default test key, will be used if FRED_API_KEY env var is not set.
# It's better to require it to be set explicitly for FRED data.
DEFAULT_TEST_FRED_KEY = "c85a224a0e0d72a7bccb471c0021eb7b"


FINANCIAL_KEYWORDS = {
    "恐慌指數": {"id": "^VIX", "type": "yfinance"},
    "VIX": {"id": "^VIX", "type": "yfinance"},
    "債券": {"id": "AGG", "type": "yfinance"}, # General bond ETF
    "公債": {"id": "IEF", "type": "yfinance"}, # US 7-10 Year Treasury Bond ETF
    "美國10年期公債殖利率": {"id": "DGS10", "type": "fred"},
    "台指": {"id": "^TWII", "type": "yfinance"},
    "TSLA": {"id": "TSLA", "type": "yfinance"},
    "AAPL": {"id": "AAPL", "type": "yfinance"},
    "NASDAQ": {"id": "^IXIC", "type": "yfinance"},
    "S&P 500": {"id": "^GSPC", "type": "yfinance"},
    "美元指數": {"id": "DX-Y.NYB", "type": "yfinance"},
    # Example FRED series (ensure it's findable and public)
    # "原油": {"id": "DCOILWTICO", "type": "fred"}, # WTI Crude Oil Price at Cushing
    # "失業率": {"id": "UNRATE", "type": "fred"}, # Civilian Unemployment Rate
}

def load_monthly_posts(filepath):
    """Loads the monthly posts data from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return None

def get_month_date_range(year_month_str):
    """
    Calculates the first and last day of a given month string (YYYY-MM).
    Returns (start_date, end_date) as datetime objects.
    """
    year, month = map(int, year_month_str.split('-'))
    start_date = datetime(year, month, 1)
    _, last_day_of_month = monthrange(year, month)
    # For yfinance, end_date in download is exclusive, so data up to end_date - 1 day.
    # For FRED, it's inclusive.
    # We'll handle this in the fetch functions.
    end_date = datetime(year, month, last_day_of_month)
    return start_date, end_date

def fetch_yfinance_data(ticker, start_date, end_date):
    """Fetches OCHLV data from Yahoo Finance for a given ticker and date range."""
    try:
        # yfinance end_date is exclusive, add one day to include the month's last day.
        # Try with auto_adjust=False to see if it changes VIX data structure
        data = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"), end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"), progress=False, auto_adjust=False)
        if data.empty:
            print(f"Warning: No yfinance data found for {ticker} from {start_date.date()} to {end_date.date()}")
            return None
        # Forward fill, then back fill for any leading NaNs after ffill (e.g. if first day was holiday)
        data.ffill(inplace=True)
        data.bfill(inplace=True)
        return data
    except Exception as e:
        print(f"Error fetching yfinance data for {ticker}: {e}")
        return None

def fetch_fred_data(series_id, start_date, end_date, api_key_to_use):
    """Fetches data from FRED for a given series ID and date range."""
    if not api_key_to_use: # Check if an API key is provided to this function
        print(f"Error: FRED_API_KEY not available. Cannot fetch FRED data for {series_id}.")
        return None
    try:
        # pandas_datareader end_date is inclusive for FRED
        data = pdr.DataReader(series_id, 'fred', start_date, end_date, api_key=api_key_to_use)
        if data.empty:
            print(f"Warning: No FRED data found for {series_id} from {start_date.date()} to {end_date.date()}")
            return None
        data.ffill(inplace=True)
        data.bfill(inplace=True)
        return data
    except Exception as e:
        print(f"Error fetching FRED data for {series_id}: {e}")
        return None

def textualize_yfinance_data(keyword_name, ticker_symbol, data_df, month_start_date, month_end_date):
    """Converts yfinance OCHLV data to a textual summary."""
    if data_df is None or data_df.empty:
        return f"{keyword_name} ({ticker_symbol}): 本月無數據。"

    # Filter data strictly within the month to avoid issues with ffill/bfill from outside
    data_df = data_df[(data_df.index >= month_start_date) & (data_df.index <= month_end_date)]
    if data_df.empty:
        return f"{keyword_name} ({ticker_symbol}): 本月無數據 (過濾後)。"

    # Assuming yfinance data might have MultiIndex columns like (ticker_symbol, 'Open')
    # Access the correct Series first. ticker_symbol is data_id passed to this function.
    try:
        open_series = data_df[(ticker_symbol, 'Open')]
        close_series = data_df[(ticker_symbol, 'Close')]
        high_series = data_df[(ticker_symbol, 'High')]
        low_series = data_df[(ticker_symbol, 'Low')]
        volume_series = data_df[(ticker_symbol, 'Volume')]
    except KeyError:
        # Fallback for simple column names if the above failed
        print(f"Warning: MultiIndex column access failed for {ticker_symbol}. Trying simple column names.")

        # If data_df['Open'] (etc.) is a DataFrame (e.g., single column), take its first column as the Series.
        # Otherwise, assume it's already the Series.
        open_col_selection = data_df['Open']
        open_series = open_col_selection.iloc[:, 0] if isinstance(open_col_selection, pd.DataFrame) else open_col_selection

        close_col_selection = data_df['Close']
        close_series = close_col_selection.iloc[:, 0] if isinstance(close_col_selection, pd.DataFrame) else close_col_selection

        high_col_selection = data_df['High']
        high_series = high_col_selection.iloc[:, 0] if isinstance(high_col_selection, pd.DataFrame) else high_col_selection

        low_col_selection = data_df['Low']
        low_series = low_col_selection.iloc[:, 0] if isinstance(low_col_selection, pd.DataFrame) else low_col_selection

        volume_col_selection = data_df['Volume']
        volume_series = volume_col_selection.iloc[:, 0] if isinstance(volume_col_selection, pd.DataFrame) else volume_col_selection

    # Now open_series (etc.) should truly be pd.Series objects.
    open_val = open_series.iloc[0]
    close_val = close_series.iloc[-1]
    high_val = high_series.max() # .max() on a Series returns a scalar
    low_val = low_series.min()   # .min() on a Series returns a scalar
    volume_val = volume_series.mean() # .mean() on a Series returns a scalar

    # Now open_val, close_val etc. should be scalars from these Series operations.
    month_open = float(open_val) if pd.notna(open_val) else None
    month_close = float(close_val) if pd.notna(close_val) else None
    month_high = float(high_val) if pd.notna(high_val) else None
    month_low = float(low_val) if pd.notna(low_val) else None
    month_avg_volume = float(volume_val) if pd.notna(volume_val) else None

    if month_open is None:
        percentage_change = 'N/A'
    elif month_open == 0:
        percentage_change = 0.0 if month_close is not None else 'N/A'
    elif month_close is None:
        percentage_change = 'N/A'
    else:
        percentage_change = ((month_close - month_open) / month_open) * 100

    daily_closes = close_series.round(2).tolist() # Use the extracted close_series

    # Helper for formatting, to avoid :.2f on None
    fmt_val = lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else ('0.00' if v == 0 else 'N/A')


    summary = (
        f"{keyword_name} ({ticker_symbol}): "
        f"本月開盤 {fmt_val(month_open)}, 收盤 {fmt_val(month_close)}, "
        f"最高 {fmt_val(month_high)}, 最低 {fmt_val(month_low)}. "
        f"月漲跌幅 {fmt_val(percentage_change)}%" if isinstance(percentage_change, (float, int)) else f"月漲跌幅 {percentage_change}. "
        f"日均成交量 {month_avg_volume:,.0f}" if isinstance(month_avg_volume, (int,float)) else f"日均成交量 N/A. " # Keep comma for large numbers
        f"每日收盤價 (頭3尾3): {daily_closes[:3]}...{daily_closes[-3:]} (共 {len(daily_closes)} 天交易日)."
    )
    return summary

def textualize_fred_data(keyword_name, series_id, data_df, month_start_date, month_end_date):
    """Converts FRED macroeconomic data to a textual summary."""
    if data_df is None or data_df.empty or data_df.iloc[:, 0].isnull().all():
        return f"{keyword_name} ({series_id}): 本月無數據。"

    # Filter data strictly within the month
    series_data = data_df[(data_df.index >= month_start_date) & (data_df.index <= month_end_date)].iloc[:, 0]
    if series_data.empty or series_data.isnull().all():
        return f"{keyword_name} ({series_id}): 本月無數據 (過濾後)。"

    month_start_val = series_data.dropna().iloc[0] if not series_data.dropna().empty else 'N/A'
    month_end_val = series_data.dropna().iloc[-1] if not series_data.dropna().empty else 'N/A'
    month_avg_val = series_data.mean() if pd.api.types.is_numeric_dtype(series_data.dropna()) else 'N/A' #dropna before mean

    change = 'N/A'
    if pd.api.types.is_numeric_dtype(series_data.dropna()) and month_start_val != 'N/A' and month_end_val != 'N/A':
        change = month_end_val - month_start_val

    unit = "%" if "yield" in keyword_name.lower() or "利率" in keyword_name.lower() or series_id in ["DGS10"] else ""

    val_format = lambda x: f"{x:.2f}{unit}" if isinstance(x, (int, float)) else x

    summary = (
        f"{keyword_name} ({series_id}): "
        f"月初值 {val_format(month_start_val)}, "
        f"月末值 {val_format(month_end_val)}. "
        f"月平均值 {val_format(month_avg_val)}. "
    )
    if isinstance(change, (int, float)):
         summary += f"月變化 {change:.2f}{unit}."
    else:
        summary += "月變化 N/A."
    return summary

def save_to_json(data, output_filepath):
    """Saves the given data to a JSON file."""
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved data to {output_filepath}")
    except Exception as e:
        print(f"Error saving data to JSON file {output_filepath}: {e}")

def main():
    """Main function to orchestrate the financial data fetching and integration."""

    # Determine FRED API key to use
    active_fred_api_key = FRED_API_KEY
    if not active_fred_api_key:
        print("INFO: FRED_API_KEY environment variable not set. Falling back to default test key for FRED data.")
        active_fred_api_key = DEFAULT_TEST_FRED_KEY

    if active_fred_api_key == DEFAULT_TEST_FRED_KEY:
         print(f"WARNING: Using the default/test FRED API key ({DEFAULT_TEST_FRED_KEY}). This key is for testing purposes and may be rate-limited or disabled. For reliable access, set your own FRED_API_KEY environment variable.")


    monthly_posts_data = load_monthly_posts(INPUT_JSON_FILE)
    if not monthly_posts_data:
        return

    updated_monthly_posts_data_structure = {}

    for month_str, posts_in_month_list in monthly_posts_data.items():
        print(f"\nProcessing month: {month_str}...")
        start_date, end_date = get_month_date_range(month_str) # These are for the actual month boundaries

        all_text_for_month = ""
        for post in posts_in_month_list: # Iterate directly over the list of posts
            all_text_for_month += post.get("post_content", "") + " "
            all_text_for_month += post.get("comments", "") + " "

        identified_keywords_for_month = set()
        for keyword, details in FINANCIAL_KEYWORDS.items():
            # Using word boundaries for more precise matching
            if re.search(r'\b' + re.escape(keyword) + r'\b', all_text_for_month, re.IGNORECASE):
                identified_keywords_for_month.add(keyword)

        print(f"Identified keywords for {month_str}: {identified_keywords_for_month if identified_keywords_for_month else 'None'}")

        financial_data_summary_list = []
        processed_ids = set() # To avoid duplicate fetches for same ID (e.g. VIX and 恐慌指數)

        for keyword_name in identified_keywords_for_month:
            details = FINANCIAL_KEYWORDS[keyword_name]
            data_id = details["id"]
            data_type = details["type"]

            if data_id in processed_ids:
                print(f"Skipping already processed ID: {data_id} (for keyword: {keyword_name})")
                # Find the summary already generated for this ID and reuse it if needed, or just ensure it's fetched once.
                # For simplicity, we fetch once and if multiple keywords point to it, the first one's name is used in summary.
                # This could be enhanced to list all keywords that pointed to this data.
                continue

            processed_ids.add(data_id)
            print(f"Fetching data for {keyword_name} ({data_id})...")
            textual_summary = f"{keyword_name} ({data_id}): Data processing error or type mismatch."

            if data_type == "yfinance":
                # Fetch data for a slightly wider range to allow ffill/bfill to work, then filter strictly
                fetch_start = start_date - timedelta(days=5)
                fetch_end = end_date + timedelta(days=5)
                data_df = fetch_yfinance_data(data_id, fetch_start, fetch_end)
                if data_df is not None:
                    textual_summary = textualize_yfinance_data(keyword_name, data_id, data_df, start_date, end_date)
                else:
                    textual_summary = f"{keyword_name} ({data_id}): 無法獲取 yfinance 數據。"
            elif data_type == "fred":
                if not active_fred_api_key: # Should have been caught by the initial check, but as a safeguard
                    textual_summary = f"{keyword_name} ({data_id}): FRED API 金鑰不可用。"
                else:
                    fetch_start = start_date - timedelta(days=5) # FRED data can be sparse
                    fetch_end = end_date + timedelta(days=5)
                    data_df = fetch_fred_data(data_id, fetch_start, fetch_end, active_fred_api_key)
                    if data_df is not None:
                        textual_summary = textualize_fred_data(keyword_name, data_id, data_df, start_date, end_date)
                    else:
                        textual_summary = f"{keyword_name} ({data_id}): 無法獲取 FRED 數據。"

            financial_data_summary_list.append(textual_summary)

        # New structure for each month: a dictionary containing posts and financial summary
        updated_monthly_posts_data_structure[month_str] = {
            "posts": posts_in_month_list, # Original list of posts
            "financial_data_summary": financial_data_summary_list
        }

    save_to_json(updated_monthly_posts_data_structure, OUTPUT_JSON_FILE)

if __name__ == "__main__":
    print("Starting financial data fetching process...")

    # Ensure a dummy 'monthly_posts_raw.json' exists if the real one isn't there.
    # This uses the output of the previous script.
    if not os.path.exists(INPUT_JSON_FILE):
        print(f"Warning: {INPUT_JSON_FILE} not found. Creating a dummy version for testing.")
        dummy_posts_raw_content = {
            "2023-01": [ # Original structure: list of posts
                {
                    "title": "Post One Title", "date": "2023-01-15",
                    "post_content": "Discussion about VIX and S&P 500 performance.",
                    "comments": "What about TSLA and also Apple (AAPL)?"
                }
            ],
            "2023-02": [ # Original structure: list of posts
                {
                    "title": "Post Two Title", "date": "2023-02-10",
                    "post_content": "Thinking about US 10-year bond yields (美國10年期公債殖利率).",
                    "comments": "Any news on NASDAQ?"
                }
            ]
        }
        with open(INPUT_JSON_FILE, 'w', encoding='utf-8') as f_dummy:
            json.dump(dummy_posts_raw_content, f_dummy, ensure_ascii=False, indent=4)
        print(f"Dummy {INPUT_JSON_FILE} created.")

    main()
    print("Financial data fetching process completed.")
