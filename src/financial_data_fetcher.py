import os
import json
import time
import pandas as pd
import requests # For FinMind and News API placeholders
import hashlib # For _get_mock_data_path
from urllib.parse import urlencode # For _get_mock_data_path

import logging # Keep for type hinting if needed
from src import utils
from src import config

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pybreaker

# Initialize logger
logger = utils.setup_logger(__name__)

# --- Circuit Breakers ---
# These breakers will be applied to the respective API fetching functions.
# If a function fails config.CIRCUIT_BREAKER_FAIL_MAX times, the breaker opens
# and subsequent calls will fail immediately for config.CIRCUIT_BREAKER_RESET_TIMEOUT seconds.

fred_breaker = pybreaker.CircuitBreaker(
    fail_max=config.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=config.CIRCUIT_BREAKER_RESET_TIMEOUT,
    name="FRED_API"
)
yf_breaker = pybreaker.CircuitBreaker(
    fail_max=config.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=config.CIRCUIT_BREAKER_RESET_TIMEOUT,
    name="YFinance_API"
)
finmind_breaker = pybreaker.CircuitBreaker(
    fail_max=config.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=config.CIRCUIT_BREAKER_RESET_TIMEOUT,
    name="FinMind_API"
)
news_breaker = pybreaker.CircuitBreaker(
    fail_max=config.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=config.CIRCUIT_BREAKER_RESET_TIMEOUT,
    name="News_API"
)

# --- Tenacity Retry Configuration ---
# Common retry decorator for API calls
# Retry on general request exceptions, specific API errors that indicate server-side issues (5xx),
# or custom RateLimitError.
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.RequestException, # Includes ConnectionError, Timeout, etc.
    utils.APIError, # Base for specific API errors
    # utils.RateLimitError, # If RateLimitError should always be retried (careful with strict limits)
    # Add other exceptions if needed, e.g. specific library errors that are transient
)

def retry_if_api_error_is_server_side_or_rate_limit(exception):
    """Retries only if APIError has a 5xx status code or is a RateLimitError."""
    if isinstance(exception, utils.RateLimitError):
        logger.warning(f"Rate limit hit, retrying: {exception}")
        return True # Retry on rate limits
    if isinstance(exception, utils.APIError):
        if exception.status_code and 500 <= exception.status_code <= 599:
            logger.warning(f"Server-side API error ({exception.status_code}), retrying: {exception}")
            return True # Retry on 5xx errors
    if isinstance(exception, requests.exceptions.RequestException):
        logger.warning(f"Request exception, retrying: {exception}")
        return True # Retry on general request exceptions
    return False


common_retry_decorator = retry(
    stop=stop_after_attempt(config.RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=config.RETRY_DELAY_SECONDS, max=config.RETRY_DELAY_SECONDS * 4), # Exponential backoff
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS) # Initial broad retry
    # For more fine-grained control, use retry_if_api_error_is_server_side_or_rate_limit:
    # retry=retry_if_api_error_is_server_side_or_rate_limit
)


# --- API Key Simulation Helper ---
def _get_mock_data_path(api_name: str, endpoint_name: str, params: dict) -> str:
    """
    Creates a unique, sorted, and hashed filename for mock data
    based on API, endpoint, and parameters.
    """
    if not config.MOCK_DATA_DIR:
        logger.error("MOCK_DATA_DIR is not configured.")
        raise utils.ConfigError("MOCK_DATA_DIR is not configured.")

    # Sort params by key to ensure consistent filenames
    sorted_params = sorted(params.items())
    # Create a string representation that is filename-friendly
    # Use urlencode for a robust representation, then hash for brevity if too long
    param_string = urlencode(sorted_params)

    # Hash the param_string if it's too long to be a convenient filename part
    if len(param_string) > 100: # Arbitrary length limit
        param_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest()
        filename_base = f"{api_name}_{endpoint_name}_{param_hash}"
    else:
        # Replace characters that are problematic in filenames
        safe_param_string = re.sub(r'[=&<>:"/\\|?*]+', '_', param_string)
        filename_base = f"{api_name}_{endpoint_name}_{safe_param_string}"

    # Ensure filename doesn't get excessively long
    max_len = 150 # Max length for the base part of filename
    filename_base = filename_base[:max_len]

    return os.path.join(config.MOCK_DATA_DIR, f"{filename_base}.mock")

def load_simulated_data(api_name: str, endpoint_name: str, params: dict,
                        expected_format: str = "json_df_records") -> pd.DataFrame | list | None:
    """
    Loads data from a mock file if SIMULATION_MODE is True.

    Args:
        api_name: Name of the API (e.g., "fred").
        endpoint_name: Name of the endpoint or series type (e.g., "series_GDPC1").
        params: Dictionary of parameters used in the API call for filename generation.
        expected_format: "json_df_records" (DataFrame from JSON records),
                         "csv" (DataFrame from CSV),
                         "json_list_dict" (list of dictionaries from JSON).

    Returns:
        Loaded data (DataFrame or list) or None if file not found or error.
    """
    if not config.SIMULATION_MODE:
        return None # Should not be called if not in simulation mode

    # Determine file extension based on expected_format for clarity in mock folder
    if expected_format == "json_df_records" or expected_format == "json_list_dict":
        ext = ".json"
    elif expected_format == "csv":
        ext = ".csv"
    else:
        ext = ".mock" # Generic extension

    # Construct mock file path using a simplified version of _get_mock_data_path for this example
    # A more robust approach would be to ensure _get_mock_data_path produces the base and then add ext

    # Create a string from params for filename uniqueness
    param_str_parts = []
    for k, v in sorted(params.items()): # Sort for consistency
        param_str_parts.append(f"{k}={v}")
    param_filename_part = "_".join(param_str_parts)
    # Sanitize param_filename_part for file systems
    param_filename_part = re.sub(r'[^\w\-_\.]', '_', param_filename_part)

    mock_filename_base = f"{api_name}_{endpoint_name}_{param_filename_part}"
    mock_file_path_with_ext = os.path.join(config.MOCK_DATA_DIR, f"{mock_filename_base}{ext}")

    # Fallback to generic .mock extension if specific extension file not found
    generic_mock_file_path = os.path.join(config.MOCK_DATA_DIR, f"{mock_filename_base}.mock")

    actual_path_to_load = None
    if os.path.exists(mock_file_path_with_ext):
        actual_path_to_load = mock_file_path_with_ext
    elif os.path.exists(generic_mock_file_path): # Try .mock if specific ext not found
        actual_path_to_load = generic_mock_file_path
        logger.info(f"Found generic mock file: {actual_path_to_load} after specific extension not found.")
    else:
        logger.warning(f"Mock data file not found for {api_name}/{endpoint_name} with params {params}. "
                       f"Checked: {mock_file_path_with_ext} and {generic_mock_file_path}")
        return None

    try:
        logger.info(f"SIMULATION: Loading data from mock file: {actual_path_to_load}")
        if expected_format == "json_df_records":
            # Ensure dates are parsed if they are common index/column names
            df = pd.read_json(actual_path_to_load, orient='records')
            if 'date' in df.columns: df['date'] = pd.to_datetime(df['date'])
            if 'Date' in df.columns: df['Date'] = pd.to_datetime(df['Date'])
            return df
        elif expected_format == "csv":
            # Try to infer date columns, common ones are 'date', 'Date', 'Datetime'
            df = pd.read_csv(actual_path_to_load)
            for col in ['date', 'Date', 'Datetime', 'timestamp', 'Timestamp']:
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col])
                        logger.info(f"Parsed column '{col}' as datetime for CSV mock.")
                    except Exception as e:
                        logger.warning(f"Could not parse column '{col}' as datetime: {e}")
            if 'Date' in df.columns and df.index.name != 'Date': # common yfinance structure
                 if not pd.api.types.is_datetime64_any_dtype(df['Date']):
                     df['Date'] = pd.to_datetime(df['Date'])
                 df = df.set_index('Date')
            return df
        elif expected_format == "json_list_dict":
            with open(actual_path_to_load, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.error(f"Unsupported mock data format: {expected_format}")
            return None
    except Exception as e:
        logger.error(f"Error loading or parsing mock data from {actual_path_to_load}: {e}", exc_info=True)
        raise utils.FileIOError(f"Failed to load mock data {actual_path_to_load}: {e}")


# --- FRED API Fetcher ---
@fred_breaker
@common_retry_decorator
def get_fred_data(series_id: str, start_date: str, end_date: str,
                  api_key: str | None = None, **kwargs) -> pd.DataFrame | None:
    """
    Fetches economic data series from FRED (Federal Reserve Economic Data).

    Args:
        series_id: The ID of the data series (e.g., "GDPC1").
        start_date: Start date in "YYYY-MM-DD" format.
        end_date: End date in "YYYY-MM-DD" format.
        api_key: FRED API key. Uses config.FRED_API_KEY if None.
        **kwargs: Additional arguments for fredapi.get_series().

    Returns:
        DataFrame with 'date' and 'value' columns, or None if error.
    """
    endpoint_name = f"series_{series_id}"
    mock_params = {"series_id": series_id, "start_date": start_date, "end_date": end_date}

    if config.SIMULATION_MODE:
        sim_data = load_simulated_data("fred", endpoint_name, mock_params, expected_format="json_df_records")
        # Ensure DataFrame has 'date' and 'value' columns as expected from real call
        if sim_data is not None and isinstance(sim_data, pd.DataFrame):
            if 'date' not in sim_data.columns or 'value' not in sim_data.columns:
                logger.warning(f"FRED mock data for {series_id} is missing 'date' or 'value' columns. Adapting.")
                # This is a basic adaptation. Real mock data should match schema.
                if 'DATE' in sim_data.columns and 'date' not in sim_data.columns: sim_data = sim_data.rename(columns={'DATE':'date'})
                if series_id in sim_data.columns and 'value' not in sim_data.columns: sim_data = sim_data.rename(columns={series_id:'value'})
                if 'date' in sim_data.columns: sim_data['date'] = pd.to_datetime(sim_data['date'])
            return sim_data
        return None # load_simulated_data returns None if file not found

    # Real API call
    key_to_use = api_key if api_key is not None else config.FRED_API_KEY
    if not key_to_use:
        logger.error("FRED API key not available in config or arguments.")
        raise utils.ConfigError("FRED API key not available.") # Raise error, don't just return None

    try:
        from fredapi import Fred
        fred = Fred(api_key=key_to_use)
        logger.info(f"Fetching FRED data for series: {series_id} from {start_date} to {end_date}")

        series_data = fred.get_series(series_id,
                                      observation_start=start_date,
                                      observation_end=end_date,
                                      **kwargs)

        if series_data.empty:
            logger.warning(f"No data returned for FRED series {series_id} for the given period.")
            return pd.DataFrame({'date': [], 'value': []}) # Return empty DF consistent with schema

        df = series_data.reset_index()
        df.columns = ['date', 'value']
        df['date'] = pd.to_datetime(df['date'])
        logger.info(f"Successfully fetched {len(df)} data points for FRED series {series_id}.")
        return df

    except requests.exceptions.HTTPError as e: # fredapi raises this for API errors
        status_code = e.response.status_code
        error_message = f"FRED API HTTP error for series {series_id}: {status_code} - {e.response.text}"
        logger.error(error_message, exc_info=True)
        if status_code == 401:
            raise utils.FredAPIError(error_message, status_code=status_code) # Unauthorized
        elif status_code == 429:
            raise utils.RateLimitError(f"FRED API rate limit hit for series {series_id}.", status_code=status_code)
        elif 400 <= status_code < 500: # Other client errors
            raise utils.FredAPIError(error_message, status_code=status_code)
        else: # Server errors or other HTTP errors
            raise utils.APIError(error_message, status_code=status_code) # Generic API error for retry

    except Exception as e: # Catch other fredapi or unexpected errors
        error_message = f"Unexpected error fetching FRED series {series_id}: {e}"
        logger.error(error_message, exc_info=True)
        # Don't know status code, so raise a generic one that might be retried by common_retry_decorator
        raise utils.FredAPIError(error_message)


# --- yfinance Fetcher ---
@yf_breaker
@common_retry_decorator # yfinance can raise various exceptions, some network-related
def get_yfinance_data(ticker: str, start_date: str, end_date: str,
                      interval: str = "1d", **kwargs) -> pd.DataFrame | None:
    """
    Fetches historical market data using yfinance.

    Args:
        ticker: Stock ticker symbol (e.g., "SPY", "MSFT").
        start_date: Start date "YYYY-MM-DD".
        end_date: End date "YYYY-MM-DD".
        interval: Data interval ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h",
                  "1d", "5d", "1wk", "1mo", "3mo").
        **kwargs: Additional arguments for yf.Ticker().history().

    Returns:
        DataFrame with OHLCV data, or None if error.
    """
    endpoint_name = f"ticker_{ticker}"
    mock_params = {"ticker": ticker, "start_date": start_date, "end_date": end_date, "interval": interval}

    if config.SIMULATION_MODE:
        df = load_simulated_data("yfinance", endpoint_name, mock_params, expected_format="csv")
        if df is not None and isinstance(df, pd.DataFrame):
            # Standardize columns for simulated data
            df = df.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close',
                'Volume': 'volume', 'Dividends': 'dividends', 'Stock Splits': 'stock_splits'
            })
            if df.index.name is not None: # If index has a name (likely 'Date' or 'Datetime')
                df = df.reset_index() # Make it a column for consistency before returning
            # Ensure date column is datetime
            date_col_names = ['Date', 'Datetime', 'date', 'datetime']
            for col_name in date_col_names:
                if col_name in df.columns:
                    df[col_name] = pd.to_datetime(df[col_name])
                    break
            return df
        return None


    # Real API call
    try:
        import yfinance as yf
        logger.info(f"Fetching yfinance data for ticker: {ticker}, interval: {interval}, from {start_date} to {end_date}")

        tick = yf.Ticker(ticker)
        # auto_adjust=True adjusts OHLC for splits/dividends, sets 'Volume'
        # repair=True can be slow but attempts to fix data issues
        data = tick.history(start=start_date, end=end_date, interval=interval,
                            auto_adjust=True, repair=False, **kwargs)

        if data.empty:
            logger.warning(f"No yfinance data returned for ticker {ticker} for the given period/interval.")
            # Return empty DF with expected schema
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

        # Standardize: yfinance returns index as Datetime, columns 'Open', 'High', etc.
        data = data.reset_index() # Moves 'Date' or 'Datetime' from index to column

        # Rename columns to lowercase and common names
        # Handle both 'Date' (for daily) and 'Datetime' (for intraday)
        if 'Datetime' in data.columns:
            data = data.rename(columns={'Datetime': 'date'})
        elif 'Date' in data.columns:
            data = data.rename(columns={'Date': 'date'})

        data = data.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        })

        # Select and reorder common columns, ensure date is present
        final_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        # Add any other columns that might have been returned and are useful (e.g. dividends, stock splits if auto_adjust=False)
        for col in data.columns:
            if col not in final_cols:
                final_cols.append(col)

        data = data[final_cols]
        data['date'] = pd.to_datetime(data['date'])

        logger.info(f"Successfully fetched {len(data)} data points for yfinance ticker {ticker}.")
        return data

    except Exception as e: # yfinance can raise a variety of errors
        # Check for common yfinance string errors that indicate specific issues
        err_str = str(e).lower()
        if "no data found" in err_str or "failed to decrypt" in err_str or "symbol may be delisted" in err_str:
            logger.warning(f"yfinance specific error for {ticker}: {e}")
            # This is not necessarily an API error to retry, but a data availability issue.
            # Return None or empty DataFrame as appropriate for "no data".
            return None # Or pd.DataFrame() if an empty DF is preferred for "no data"

        error_message = f"Error fetching yfinance data for {ticker}: {e}"
        logger.error(error_message, exc_info=True)
        # Wrap in a custom error that can be caught by retry logic if it's potentially transient
        raise utils.YFinanceError(error_message)


# --- FinMind API Fetcher Framework ---
@finmind_breaker
@common_retry_decorator
def get_finmind_data(dataset: str, stock_id: str, start_date: str, end_date: str,
                     api_token: str | None = None, **kwargs) -> pd.DataFrame | None:
    """
    Fetches data from FinMind API (Taiwan market data). Framework function.

    Args:
        dataset: FinMind dataset name (e.g., "TaiwanStockPrice").
        stock_id: Stock ID (e.g., "2330").
        start_date: "YYYY-MM-DD".
        end_date: "YYYY-MM-DD".
        api_token: FinMind API token. Uses config.FINMIND_API_KEY if None.
        **kwargs: Additional parameters for the API request.

    Returns:
        DataFrame with data, or None.
    """
    endpoint_name = f"dataset_{dataset}_stock_{stock_id}"
    mock_params = {"dataset": dataset, "stock_id": stock_id, "start_date": start_date, "end_date": end_date}

    if config.SIMULATION_MODE:
        df = load_simulated_data("finmind", endpoint_name, mock_params, expected_format="json_df_records")
        # TODO: Add schema standardization for FinMind mock data if needed
        return df

    # Real API call
    token_to_use = api_token if api_token is not None else config.FINMIND_API_KEY
    if not token_to_use:
        logger.error("FinMind API key not available in config or arguments.")
        raise utils.ConfigError("FinMind API key not available.")

    base_url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        'dataset': dataset,
        'data_id': stock_id,
        'start_date': start_date,
        'end_date': end_date,
        'token': token_to_use,
        **kwargs
    }

    logger.info(f"Fetching FinMind data for {dataset} / {stock_id} from {start_date} to {end_date}")

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() # Raises HTTPError for 4XX/5XX status codes

        data_json = response.json()
        if data_json.get('msg') != 'success':
            logger.error(f"FinMind API call not successful for {dataset}/{stock_id}: {data_json.get('msg')}")
            raise utils.FinMindAPIError(f"FinMind API error: {data_json.get('msg')}", status_code=response.status_code) # Use actual status code

        df = pd.DataFrame(data_json.get('data', []))
        if df.empty:
            logger.warning(f"No data returned by FinMind for {dataset}/{stock_id} for the period.")
        else:
            logger.info(f"Successfully fetched {len(df)} records from FinMind for {dataset}/{stock_id}.")
            if 'date' in df.columns: df['date'] = pd.to_datetime(df['date']) # Common transformation
        return df

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_message = f"FinMind API HTTP error for {dataset}/{stock_id}: {status_code} - {e.response.text}"
        logger.error(error_message, exc_info=True)
        if status_code == 401: # Unauthorized
            raise utils.FinMindAPIError(error_message, status_code=status_code)
        elif status_code == 402: # Token usage limit
             raise utils.RateLimitError(f"FinMind API usage limit hit for {dataset}/{stock_id}.", status_code=status_code)
        elif 400 <= status_code < 500: # Other client errors
            raise utils.FinMindAPIError(error_message, status_code=status_code)
        else: # Server errors or other HTTP errors
            raise utils.APIError(error_message, status_code=status_code) # Generic API error for retry

    except Exception as e:
        error_message = f"Unexpected error fetching FinMind data for {dataset}/{stock_id}: {e}"
        logger.error(error_message, exc_info=True)
        raise utils.FinMindAPIError(error_message) # Custom error for this API


# --- News API Fetcher Framework ---
@news_breaker
@common_retry_decorator
def fetch_market_news(query: str, start_date: str, end_date: str,
                      api_key: str | None = None, source: str = "default_news_api",
                      **kwargs) -> list[dict] | None:
    """
    Fetches market news from a configured news API. Framework function.

    Args:
        query: Search query for news (e.g., "AAPL", "market sentiment").
        start_date: "YYYY-MM-DD".
        end_date: "YYYY-MM-DD".
        api_key: API key for the news source. Specific config keys might be used.
        source: Identifier for the news source (e.g., "newsapi.org", "finnhub").
        **kwargs: Additional parameters for the news API.

    Returns:
        List of news articles (dicts), or None.
    """
    endpoint_name = f"query_{query}_source_{source}"
    mock_params = {"query": query, "start_date": start_date, "end_date": end_date, "source": source}

    if config.SIMULATION_MODE:
        return load_simulated_data("news", endpoint_name, mock_params, expected_format="json_list_dict")

    # Real API call - Placeholder
    logger.warning(f"Real News API call for source '{source}' not yet fully implemented. This is placeholder logic.")

    # Example: Determine key based on source
    key_to_use = api_key
    if not key_to_use:
        if source == "GEMINI_NEWS" and config.GEMINI_API_KEY: # Example if Gemini has news
             key_to_use = config.GEMINI_API_KEY
        # Add elif for other news sources and their respective config keys
        # elif source == "NEWSAPI_ORG" and config.NEWSAPI_ORG_KEY:
        # key_to_use = config.NEWSAPI_ORG_KEY
        else:
            logger.error(f"News API key for source '{source}' not available in config or arguments.")
            raise utils.ConfigError(f"News API key for source '{source}' not available.")

    # --- Placeholder for actual API call logic ---
    # This section would be replaced with actual requests to a news API.
    # Example structure:
    # url = "..."
    # params = {"q": query, "from": start_date, "to": end_date, "apiKey": key_to_use, **kwargs}
    # try:
    #     response = requests.get(url, params=params)
    #     response.raise_for_status()
    #     news_data = response.json().get('articles', []) # Example for NewsAPI.org structure
    #     # Transform news_data to a standard list of dicts:
    #     # [{'date': ..., 'headline': ..., 'summary': ..., 'source': ..., 'url': ...}]
    #     processed_news = []
    #     for article in news_data:
    #         processed_news.append({
    #             'date': article.get('publishedAt'),
    #             'headline': article.get('title'),
    #             'summary': article.get('description'),
    #             'source': article.get('source', {}).get('name'),
    #             'url': article.get('url')
    #         })
    #     logger.info(f"Fetched {len(processed_news)} news articles for query '{query}' from {source}.")
    #     return processed_news
    # except requests.exceptions.HTTPError as e:
    #     # Handle HTTP errors similar to FinMind: 401, 429, etc.
    #     # Raise utils.NewsAPIError(..., status_code=e.response.status_code)
    #     pass
    # except Exception as e:
    #     # Handle other errors
    #     # Raise utils.NewsAPIError(...)
    #     pass
    # --- End Placeholder ---

    logger.info(f"Placeholder: Would fetch news for '{query}' from {source} between {start_date} and {end_date}.")
    # Return an empty list for now as it's a placeholder
    return []


if __name__ == '__main__':
    logger.info("--- Running financial_data_fetcher.py direct execution tests ---")

    # Ensure MOCK_DATA_DIR exists for testing simulation mode
    if not config.MOCK_DATA_DIR:
        # Fallback to a default mock_data directory in the project root for this test
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Assumes src is one level down
        config.MOCK_DATA_DIR = os.path.join(project_root, "mock_data_fetcher_test")
        logger.warning(f"config.MOCK_DATA_DIR not set. Using temporary for test: {config.MOCK_DATA_DIR}")
    utils.ensure_directory_exists(config.MOCK_DATA_DIR)

    # --- Create Dummy Mock Files ---
    # FRED Mock (json_df_records)
    fred_mock_params = {"series_id": "GDPC1", "start_date": "2020-01-01", "end_date": "2020-12-31"}
    fred_mock_filename = f"fred_series_GDPC1_{urlencode(sorted(fred_mock_params.items()))[:50]}.json" # Simplified
    fred_mock_path = os.path.join(config.MOCK_DATA_DIR, fred_mock_filename)
    fred_sample_data = [{'date': '2020-01-01', 'value': 20000.0}, {'date': '2020-04-01', 'value': 19000.0}]
    with open(fred_mock_path, 'w') as f: json.dump(fred_sample_data, f)
    logger.info(f"Created FRED mock file: {fred_mock_path}")

    # yfinance Mock (csv)
    yf_mock_params = {"ticker": "TESTMSFT", "start_date": "2020-01-01", "end_date": "2020-01-05", "interval": "1d"}
    # yf_mock_filename = f"yfinance_ticker_TESTMSFT_{urlencode(sorted(yf_mock_params.items()))[:80]}.csv" # Simplified
    yf_mock_filename_base = f"yfinance_ticker_TESTMSFT_start_date=2020-01-01_end_date=2020-01-05_interval=1d" # matching load_simulated_data format
    yf_mock_path = os.path.join(config.MOCK_DATA_DIR, f"{yf_mock_filename_base}.csv")

    yf_sample_df = pd.DataFrame({
        'Date': pd.to_datetime(['2020-01-01', '2020-01-02', '2020-01-03']),
        'Open': [150.0, 151.0, 152.0], 'High': [155.0, 156.0, 157.0],
        'Low': [149.0, 150.0, 151.0], 'Close': [154.0, 155.0, 156.0],
        'Volume': [100000, 120000, 110000]
    })
    yf_sample_df.to_csv(yf_mock_path, index=False) # Save without index for this test file
    logger.info(f"Created yfinance mock file: {yf_mock_path}")

    # FinMind Mock (json_df_records)
    finmind_mock_params = {"dataset": "TestStockPrice", "stock_id": "0050", "start_date": "2020-01-01", "end_date": "2020-01-05"}
    finmind_mock_filename_base = f"finmind_dataset_TestStockPrice_stock_id=0050_start_date=2020-01-01_end_date=2020-01-05"
    finmind_mock_path = os.path.join(config.MOCK_DATA_DIR, f"{finmind_mock_filename_base}.json")
    finmind_sample_data = [{'date': '2020-01-02', 'stock_id': '0050', 'Trading_Volume': 1000, 'Close': 80.0},
                           {'date': '2020-01-03', 'stock_id': '0050', 'Trading_Volume': 1200, 'Close': 81.0}]
    with open(finmind_mock_path, 'w') as f: json.dump(finmind_sample_data, f)
    logger.info(f"Created FinMind mock file: {finmind_mock_path}")

    # News Mock (json_list_dict)
    news_mock_params = {"query": "test_query", "start_date": "2020-01-01", "end_date": "2020-01-02", "source": "test_news"}
    news_mock_filename_base = f"news_query_test_query_start_date=2020-01-01_end_date=2020-01-02_source_test_news"
    news_mock_path = os.path.join(config.MOCK_DATA_DIR, f"{news_mock_filename_base}.json")
    news_sample_data = [{'date': '2020-01-01T10:00:00Z', 'headline': 'Test News 1', 'summary': 'Summary 1', 'source': 'Test Source'},
                        {'date': '2020-01-01T12:00:00Z', 'headline': 'Test News 2', 'summary': 'Summary 2', 'source': 'Test Source'}]
    with open(news_mock_path, 'w') as f: json.dump(news_sample_data, f)
    logger.info(f"Created News mock file: {news_mock_path}")


    # --- Test Fetchers in SIMULATION_MODE ---
    original_sim_mode = config.SIMULATION_MODE
    config.SIMULATION_MODE = True
    logger.info("--- Testing in SIMULATION_MODE = True ---")

    # Test FRED
    fred_df_sim = get_fred_data(series_id="GDPC1", start_date="2020-01-01", end_date="2020-12-31")
    assert fred_df_sim is not None and not fred_df_sim.empty, "FRED simulation failed"
    assert 'value' in fred_df_sim.columns and 'date' in fred_df_sim.columns, "FRED sim columns incorrect"
    logger.info(f"FRED sim data (first 2 rows):\n{fred_df_sim.head(2)}")

    # Test yfinance
    yf_df_sim = get_yfinance_data(ticker="TESTMSFT", start_date="2020-01-01", end_date="2020-01-05", interval="1d")
    assert yf_df_sim is not None and not yf_df_sim.empty, "yfinance simulation failed"
    # Check for standardized columns (lowercase)
    assert 'open' in yf_df_sim.columns and 'volume' in yf_df_sim.columns, "yfinance sim columns incorrect"
    logger.info(f"yfinance sim data (first 2 rows):\n{yf_df_sim.head(2)}")

    # Test FinMind
    finmind_df_sim = get_finmind_data(dataset="TestStockPrice", stock_id="0050", start_date="2020-01-01", end_date="2020-01-05")
    assert finmind_df_sim is not None and not finmind_df_sim.empty, "FinMind simulation failed"
    logger.info(f"FinMind sim data (first 2 rows):\n{finmind_df_sim.head(2)}")

    # Test News
    news_list_sim = fetch_market_news(query="test_query", start_date="2020-01-01", end_date="2020-01-02", source="test_news")
    assert news_list_sim is not None and len(news_list_sim) > 0, "News simulation failed"
    logger.info(f"News sim data (first item):\n{news_list_sim[0] if news_list_sim else 'Empty'}")

    config.SIMULATION_MODE = original_sim_mode # Restore original mode

    # --- Test Real API Calls (if keys are available and not in CI/restricted env) ---
    # These tests will likely fail if API keys are not set in config or environment.
    # They also make actual network calls.
    # Consider adding a flag to skip these in automated test environments without keys/network.

    RUN_REAL_API_TESTS = os.getenv("RUN_REAL_API_TESTS", "false").lower() == "true"

    if RUN_REAL_API_TESTS:
        logger.info("--- Testing REAL API Calls (requires API keys and network) ---")

        # Test FRED (requires FRED_API_KEY)
        if config.FRED_API_KEY:
            logger.info("Testing real FRED API call...")
            try:
                fred_df_real = get_fred_data(series_id="GDPC1", start_date="2022-01-01", end_date="2022-06-30")
                if fred_df_real is not None and not fred_df_real.empty:
                    logger.info(f"Real FRED GDPC1 data (first 2 rows):\n{fred_df_real.head(2)}")
                    assert not fred_df_real.empty
                elif fred_df_real is not None and fred_df_real.empty: # API returned no data for period
                    logger.info("Real FRED GDPC1 data returned empty for period, which is valid.")
                else: # None was returned, indicating an error during fetch
                    logger.error("Real FRED GDPC1 data fetch returned None.")
            except Exception as e:
                logger.error(f"Real FRED API test failed: {e}", exc_info=True)
        else:
            logger.warning("Skipping real FRED API test: FRED_API_KEY not configured.")

        # Test yfinance (usually doesn't require API key)
        logger.info("Testing real yfinance API call...")
        try:
            yf_df_real = get_yfinance_data(ticker="MSFT", start_date="2023-01-01", end_date="2023-01-10", interval="1d")
            if yf_df_real is not None and not yf_df_real.empty:
                logger.info(f"Real yfinance MSFT data (first 2 rows):\n{yf_df_real.head(2)}")
                assert not yf_df_real.empty
            elif yf_df_real is not None and yf_df_real.empty:
                 logger.info("Real yfinance MSFT data returned empty for period, which is valid.")
            else:
                logger.error("Real yfinance MSFT data fetch returned None.")
        except Exception as e:
            logger.error(f"Real yfinance API test failed: {e}", exc_info=True)

        # Test FinMind (requires FINMIND_API_KEY)
        if config.FINMIND_API_KEY:
            logger.info("Testing real FinMind API call...")
            try:
                # Using a common dataset that is usually available
                finmind_df_real = get_finmind_data(dataset="TaiwanStockInfo", stock_id="", start_date="", end_date="") # Info doesn't need date/id
                if finmind_df_real is not None and not finmind_df_real.empty:
                    logger.info(f"Real FinMind TaiwanStockInfo data (first 2 rows):\n{finmind_df_real.head(2)}")
                    assert not finmind_df_real.empty
                elif finmind_df_real is not None and finmind_df_real.empty:
                    logger.info("Real FinMind TaiwanStockInfo returned empty, which might be valid or an issue.")
                else:
                    logger.error("Real FinMind TaiwanStockInfo data fetch returned None.")
            except Exception as e:
                logger.error(f"Real FinMind API test failed: {e}", exc_info=True)
        else:
            logger.warning("Skipping real FinMind API test: FINMIND_API_KEY not configured.")

        # News API is placeholder, so no real test here yet.

    else:
        logger.info("Skipping REAL API Calls tests (RUN_REAL_API_TESTS not true).")


    # Test retry and circuit breaker (conceptual - hard to test deterministically without mocks for server errors)
    logger.info("--- Conceptual test for retry and circuit breaker ---")
    # To truly test these, you'd mock the 'requests.get' or library calls to raise specific exceptions.
    # For example, to test fred_breaker:
    # with mock.patch('fredapi.Fred.get_series', side_effect=utils.APIError("Simulated server error", status_code=500)):
    #     for i in range(config.CIRCUIT_BREAKER_FAIL_MAX + 1):
    #         try:
    #             get_fred_data("FAIL_SERIES", "2023-01-01", "2023-01-02")
    #         except pybreaker.CircuitBreakerError:
    #             logger.info(f"Circuit breaker opened as expected on attempt {i+1}")
    #             assert True
    #             break
    #         except utils.APIError: # Expected due to tenacity retries exhausting
    #             logger.info(f"APIError caught on attempt {i+1}")
    #             if i == config.CIRCUIT_BREAKER_FAIL_MAX -1 : # After last successful retry before breaker opens
    #                 pass # Expected
    #     else: # If loop completes without breaker opening
    #         assert False, "Circuit breaker did not open"
    # This kind of test is more for a dedicated test suite.
    logger.info("Conceptual retry/breaker test points noted. Implement in formal test suite.")

    logger.info("--- financial_data_fetcher.py direct execution tests completed ---")
