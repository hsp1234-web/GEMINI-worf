import sqlite3
import pandas as pd
import os
import logging # Keep this for type hinting if needed, though utils.setup_logger is primary

from src import utils
from src import config

# Initialize logger
logger = utils.setup_logger(__name__)

# --- Database Constants (Consider moving to config if they become more complex) ---
# Define table schemas here for clarity or fetch from a dedicated schema definition module later
OHLCV_TABLE_SCHEMA = {
    "symbol": "TEXT",
    "date": "TEXT", # ISO 8601 format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
    "open": "REAL",
    "high": "REAL",
    "low": "REAL",
    "close": "REAL",
    "volume": "INTEGER",
    "source_api": "TEXT", # e.g., 'gemini', 'finnhub', 'yfinance_daily', 'yfinance_intraday'
    "data_type": "TEXT", # e.g., 'crypto', 'stock', 'forex', 'commodity'
    "timeframe": "TEXT" # e.g., '1D', '1H', '5min'
}
OHLCV_PRIMARY_KEYS = ["symbol", "date", "source_api", "timeframe"] # Composite primary key

MACRO_INDICATORS_TABLE_SCHEMA = {
    "indicator_name": "TEXT", # e.g., 'GDP_USA', 'UNEMPLOYMENT_RATE_USA'
    "date": "TEXT", # Date of the indicator value
    "value": "REAL",
    "source_api": "TEXT", # e.g., 'fred', 'worldbank'
    "frequency": "TEXT" # e.g., 'Quarterly', 'Monthly', 'Annual'
}
MACRO_INDICATORS_PRIMARY_KEYS = ["indicator_name", "date", "source_api"]

FINANCIAL_EVENTS_TABLE_SCHEMA = {
    "event_id": "TEXT", # Unique ID for the event, could be hash of key components if no natural one
    "event_type": "TEXT", # e.g., 'earnings_report', 'ipo', 'stock_split', 'fed_meeting'
    "date": "TEXT", # Date of the event
    "symbol": "TEXT", # Associated symbol (if any, e.g., for earnings)
    "details_json": "TEXT", # JSON string for additional event-specific details
    "source_api": "TEXT"
}
FINANCIAL_EVENTS_PRIMARY_KEYS = ["event_id"] # Or a composite like ['event_type', 'date', 'symbol', 'source_api'] if event_id is not guaranteed unique across sources


# --- Database Connection ---
def get_db_connection(db_path: str = None, in_memory: bool = False) -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database.

    Args:
        db_path: Path to the database file. Uses config.DATABASE_PATH if None.
        in_memory: If True, creates an in-memory database.

    Returns:
        sqlite3.Connection object.

    Raises:
        DataProcessingError: If the database connection cannot be established.
    """
    if in_memory:
        db_path_to_use = ":memory:"
        logger.info("Connecting to in-memory SQLite database.")
    else:
        db_path_to_use = db_path if db_path is not None else config.DATABASE_PATH
        if db_path_to_use is None:
            raise utils.ConfigError("DATABASE_PATH is not set in config and no db_path provided.")

        # Ensure the directory for the database file exists
        db_dir = os.path.dirname(db_path_to_use)
        if db_dir: # Only if db_path_to_use includes a directory
            utils.ensure_directory_exists(db_dir)
        logger.info(f"Connecting to SQLite database at: {db_path_to_use}")

    try:
        conn = sqlite3.connect(db_path_to_use, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        # Enable foreign key support if needed, though not explicitly used in these schemas yet
        # conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database '{db_path_to_use}': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to connect to database '{db_path_to_use}': {e}")


# --- Table Creation Functions ---
def create_table_ohlcv(conn: sqlite3.Connection):
    """Creates the ohlcv_data table if it doesn't exist."""
    try:
        cols_with_types = [f'"{col_name}" {col_type}' for col_name, col_type in OHLCV_TABLE_SCHEMA.items()]
        # Primary key definition: making it composite
        pk_cols_str = ", ".join([f'"{pk}"' for pk in OHLCV_PRIMARY_KEYS])

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS ohlcv_data (
            {', '.join(cols_with_types)},
            PRIMARY KEY ({pk_cols_str})
        );
        """
        conn.execute(create_table_sql)

        # Example Indexes (add more as needed based on query patterns)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_date ON ohlcv_data (symbol, date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_source_api ON ohlcv_data (source_api);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_data_type ON ohlcv_data (data_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe ON ohlcv_data (timeframe);")

        conn.commit()
        logger.info("Table 'ohlcv_data' checked/created successfully with indexes.")
    except sqlite3.Error as e:
        logger.error(f"Error creating table 'ohlcv_data': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to create table 'ohlcv_data': {e}")

def create_table_macro_indicators(conn: sqlite3.Connection):
    """Creates the macro_indicators table if it doesn't exist."""
    try:
        cols_with_types = [f'"{col_name}" {col_type}' for col_name, col_type in MACRO_INDICATORS_TABLE_SCHEMA.items()]
        pk_cols_str = ", ".join([f'"{pk}"' for pk in MACRO_INDICATORS_PRIMARY_KEYS])

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS macro_indicators (
            {', '.join(cols_with_types)},
            PRIMARY KEY ({pk_cols_str})
        );
        """
        conn.execute(create_table_sql)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_macro_indicator_name_date ON macro_indicators (indicator_name, date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_macro_source_api ON macro_indicators (source_api);")

        conn.commit()
        logger.info("Table 'macro_indicators' checked/created successfully with indexes.")
    except sqlite3.Error as e:
        logger.error(f"Error creating table 'macro_indicators': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to create table 'macro_indicators': {e}")

def create_table_financial_events(conn: sqlite3.Connection):
    """Creates the financial_events table if it doesn't exist."""
    try:
        cols_with_types = [f'"{col_name}" {col_type}' for col_name, col_type in FINANCIAL_EVENTS_TABLE_SCHEMA.items()]
        pk_cols_str = ", ".join([f'"{pk}"' for pk in FINANCIAL_EVENTS_PRIMARY_KEYS])

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS financial_events (
            {', '.join(cols_with_types)},
            PRIMARY KEY ({pk_cols_str})
        );
        """
        conn.execute(create_table_sql)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_event_type_date ON financial_events (event_type, date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_event_symbol ON financial_events (symbol);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_event_source_api ON financial_events (source_api);")

        conn.commit()
        logger.info("Table 'financial_events' checked/created successfully with indexes.")
    except sqlite3.Error as e:
        logger.error(f"Error creating table 'financial_events': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to create table 'financial_events': {e}")

def initialize_database(conn: sqlite3.Connection):
    """Initializes all tables in the database."""
    logger.info("Initializing database schema...")
    create_table_ohlcv(conn)
    create_table_macro_indicators(conn)
    create_table_financial_events(conn)
    logger.info("Database schema initialization complete.")


# --- DataFrame to SQLite ---
def save_dataframe_to_db(df: pd.DataFrame, table_name: str, conn: sqlite3.Connection,
                         if_exists: str = "append", primary_keys: list[str] | None = None):
    """
    Saves a Pandas DataFrame to a specified SQLite table with an upsert mechanism.

    Args:
        df: DataFrame to save.
        table_name: Name of the table to save to.
        conn: SQLite connection object.
        if_exists: How to behave if the table already exists.
                   'append': Appends new rows. Uses INSERT OR REPLACE for rows with
                             conflicting primary keys if primary_keys are provided.
                   'replace': Drops the table before inserting new values.
                   'fail': Raises ValueError if table exists.
        primary_keys: List of column names that form the primary key.
                      Required for 'append' with upsert behavior.
                      If 'append' and primary_keys is None, it will be a simple append,
                      which might lead to duplicates or errors if PKs are violated.
    """
    if df.empty:
        logger.info(f"DataFrame for table '{table_name}' is empty. Nothing to save.")
        return

    try:
        if if_exists == "append" and primary_keys:
            # Using INSERT OR REPLACE for simplicity, assuming primary keys are defined in the table.
            # This will replace rows if their primary key already exists.
            cols = ', '.join([f'"{c}"' for c in df.columns])
            placeholders = ', '.join(['?'] * len(df.columns))
            sql_upsert = f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"

            # Convert Timestamp objects to ISO format strings if they are not already
            df_copy = df.copy()
            for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
                logger.debug(f"Converting column {col} to ISO 8601 string format for SQLite.")
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S') # Adjust format as needed

            conn.executemany(sql_upsert, df_copy.to_records(index=False).tolist())
            conn.commit()
            logger.info(f"{len(df)} rows upserted into table '{table_name}'.")
        else:
            # Standard pandas to_sql for 'replace', 'fail', or simple 'append'
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            logger.info(f"DataFrame saved to table '{table_name}' with if_exists='{if_exists}'.")

    except sqlite3.Error as e:
        logger.error(f"SQLite error saving DataFrame to table '{table_name}': {e}", exc_info=True)
        conn.rollback() # Rollback on error
        raise utils.DataProcessingError(f"Failed to save DataFrame to table '{table_name}': {e}")
    except Exception as e: # Catch other potential errors like issues with df.to_records
        logger.error(f"Unexpected error saving DataFrame to table '{table_name}': {e}", exc_info=True)
        if conn: conn.rollback()
        raise utils.DataProcessingError(f"Unexpected error saving DataFrame to table '{table_name}': {e}")


# --- SQLite to DataFrame ---
def read_dataframe_from_db(query: str, conn: sqlite3.Connection, params: tuple | None = None) -> pd.DataFrame:
    """
    Reads data from SQLite into a Pandas DataFrame using a SQL query.

    Args:
        query: SQL query string.
        conn: SQLite connection object.
        params: Optional tuple of parameters to bind to the query.

    Returns:
        Pandas DataFrame with query results.

    Raises:
        DataProcessingError: If data cannot be read.
    """
    try:
        df = pd.read_sql_query(query, conn, params=params)
        logger.info(f"Successfully executed query and fetched {len(df)} rows.")
        return df
    except sqlite3.Error as e:
        logger.error(f"Error reading DataFrame from database with query '{query[:100]}...': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to read DataFrame from database: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading DataFrame from database with query '{query[:100]}...': {e}", exc_info=True)
        raise utils.DataProcessingError(f"Unexpected error reading DataFrame from database: {e}")


# --- Get Latest Timestamp ---
def get_latest_timestamp(table_name: str, conn: sqlite3.Connection,
                         date_column: str = "date",
                         symbol: str | None = None,
                         source_api: str | None = None,
                         timeframe: str | None = None) -> pd.Timestamp | None:
    """
    Retrieves the latest timestamp from a specified table and date column,
    optionally filtered by symbol, source_api, and timeframe.

    Args:
        table_name: The name of the table.
        conn: SQLite connection object.
        date_column: The name of the column containing timestamps/dates.
        symbol: Optional. Filter by this symbol.
        source_api: Optional. Filter by this source_api.
        timeframe: Optional. Filter by this timeframe (for ohlcv_data).

    Returns:
        pd.Timestamp of the latest entry, or None if no data or error.
    """
    conditions = []
    params = []

    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if source_api:
        conditions.append("source_api = ?")
        params.append(source_api)
    if timeframe and table_name == "ohlcv_data": # timeframe is specific to ohlcv
        conditions.append("timeframe = ?")
        params.append(timeframe)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT MAX({date_column}) FROM {table_name} {where_clause}"

    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        result = cursor.fetchone()

        if result and result[0] is not None:
            # SQLite stores dates as TEXT, REAL, or INTEGER. Pandas can parse many string formats.
            # If stored as TEXT in ISO format, pd.to_datetime will handle it.
            # If stored as unix epoch (INTEGER or REAL), specify unit.
            # Assuming ISO string format for now as per OHLCV_TABLE_SCHEMA.
            latest_ts_str = result[0]
            latest_ts = pd.to_datetime(latest_ts_str)
            logger.info(f"Latest timestamp for {table_name} (filters: symbol={symbol}, source_api={source_api}, timeframe={timeframe}): {latest_ts}")
            return latest_ts
        else:
            logger.info(f"No timestamp found for {table_name} (filters: symbol={symbol}, source_api={source_api}, timeframe={timeframe}). Table might be empty or filters too restrictive.")
            return None
    except sqlite3.Error as e:
        logger.error(f"Error getting latest timestamp from '{table_name}': {e}", exc_info=True)
        # Not raising DataProcessingError here to allow flow to continue if this is optional
        return None
    except Exception as e: # Catch pandas parsing errors etc.
        logger.error(f"Unexpected error processing latest timestamp from '{table_name}': {e}", exc_info=True)
        return None


# --- Parquet Operations ---
def save_df_to_parquet(df: pd.DataFrame, file_name: str, parquet_dir: str = None, **kwargs):
    """
    Saves a DataFrame to a Parquet file.

    Args:
        df: DataFrame to save.
        file_name: Name of the file (e.g., 'my_data.parquet'). Extension will be checked.
        parquet_dir: Directory to save the Parquet file. Uses config.PARQUET_DATA_DIR if None.
        **kwargs: Additional arguments to pass to df.to_parquet().
    """
    if df.empty:
        logger.info(f"DataFrame for Parquet file '{file_name}' is empty. Nothing to save.")
        return

    target_dir = parquet_dir if parquet_dir is not None else config.PARQUET_DATA_DIR
    if target_dir is None:
        raise utils.ConfigError("PARQUET_DATA_DIR is not set in config and no parquet_dir provided.")

    utils.ensure_directory_exists(target_dir)

    if not file_name.endswith((".parquet", ".pq")):
        file_name += ".parquet"
        logger.info(f"Added .parquet extension to filename. New filename: {file_name}")

    file_path = os.path.join(target_dir, file_name)

    try:
        df.to_parquet(file_path, index=False, **kwargs)
        logger.info(f"DataFrame successfully saved to Parquet: {file_path}")
    except Exception as e: # Pandas errors or other OS errors
        logger.error(f"Error saving DataFrame to Parquet file '{file_path}': {e}", exc_info=True)
        raise utils.FileIOError(f"Failed to save DataFrame to Parquet file '{file_path}': {e}")

def read_df_from_parquet(file_name: str, parquet_dir: str = None,
                         columns: list[str] | None = None, **kwargs) -> pd.DataFrame:
    """
    Reads a DataFrame from a Parquet file.

    Args:
        file_name: Name of the Parquet file.
        parquet_dir: Directory where the Parquet file is located. Uses config.PARQUET_DATA_DIR if None.
        columns: List of columns to read. Reads all if None.
        **kwargs: Additional arguments to pass to pd.read_parquet().

    Returns:
        Pandas DataFrame.

    Raises:
        FileIOError: If the file cannot be read.
    """
    source_dir = parquet_dir if parquet_dir is not None else config.PARQUET_DATA_DIR
    if source_dir is None:
        raise utils.ConfigError("PARQUET_DATA_DIR is not set in config and no parquet_dir provided.")

    if not file_name.endswith((".parquet", ".pq")):
        # Try adding extension if user forgot, but be less aggressive than in save
        potential_file_path_pq = os.path.join(source_dir, file_name + ".parquet")
        potential_file_path_raw = os.path.join(source_dir, file_name)
        if os.path.exists(potential_file_path_pq):
            file_path = potential_file_path_pq
        elif os.path.exists(potential_file_path_raw):
             file_path = potential_file_path_raw
        else:
            # If neither exists, default to adding .parquet and let pd.read_parquet handle FileNotFoundError
            file_path = potential_file_path_pq
            logger.warning(f"File '{file_name}' not found directly. Assuming '.parquet' extension: {file_path}")

    else:
        file_path = os.path.join(source_dir, file_name)


    try:
        df = pd.read_parquet(file_path, columns=columns, **kwargs)
        logger.info(f"DataFrame successfully read from Parquet: {file_path} (read {len(df)} rows).")
        return df
    except FileNotFoundError:
        logger.error(f"Parquet file not found: {file_path}", exc_info=True)
        raise utils.FileIOError(f"Parquet file not found: {file_path}")
    except Exception as e: # Pandas errors or other OS errors
        logger.error(f"Error reading DataFrame from Parquet file '{file_path}': {e}", exc_info=True)
        raise utils.FileIOError(f"Failed to read DataFrame from Parquet file '{file_path}': {e}")


if __name__ == '__main__':
    # This section is for basic testing when the script is run directly.
    # It requires config.py to have DATABASE_PATH and PARQUET_DATA_DIR set.

    logger.info("--- Running database_manager.py direct execution tests ---")

    # Ensure essential config paths are set for testing
    if not config.DATABASE_PATH:
        # Create a temporary db path for testing if not defined in config
        config.DATABASE_PATH = os.path.join(config.SRC_DIR, "temp_test_db.sqlite")
        logger.warning(f"config.DATABASE_PATH not set. Using temporary: {config.DATABASE_PATH}")

    if not config.PARQUET_DATA_DIR:
        config.PARQUET_DATA_DIR = os.path.join(os.path.dirname(config.SRC_DIR), "temp_test_parquet_data")
        utils.ensure_directory_exists(config.PARQUET_DATA_DIR)
        logger.warning(f"config.PARQUET_DATA_DIR not set. Using temporary: {config.PARQUET_DATA_DIR}")


    # Test DB connection and table creation
    # test_db_path = os.path.join(os.path.dirname(config.SRC_DIR), "test_main_db.sqlite")
    # logger.info(f"Using test database: {test_db_path}")
    # if os.path.exists(test_db_path):
    #     os.remove(test_db_path) # Clean start for testing

    # conn = get_db_connection(db_path=test_db_path)
    conn = get_db_connection(in_memory=True) # Use in-memory for simpler testing

    logger.info("Initializing database...")
    initialize_database(conn)

    # Test OHLCV data saving and reading
    logger.info("--- Testing OHLCV Data ---")
    ohlcv_sample_data = [
        ('BTCUSD', '2023-01-01 00:00:00', 30000.0, 30100.0, 29900.0, 30050.0, 100, 'test_api', 'crypto', '1D'),
        ('BTCUSD', '2023-01-02 00:00:00', 30050.0, 30200.0, 30000.0, 30150.0, 150, 'test_api', 'crypto', '1D'),
        ('ETHUSD', '2023-01-01 00:00:00', 2000.0, 2010.0, 1990.0, 2005.0, 500, 'test_api', 'crypto', '1D'),
        # Duplicate for upsert test
        ('BTCUSD', '2023-01-01 00:00:00', 30001.0, 30101.0, 29901.0, 30051.0, 101, 'test_api', 'crypto', '1D'),
    ]
    ohlcv_df = pd.DataFrame(ohlcv_sample_data, columns=list(OHLCV_TABLE_SCHEMA.keys()))
    # Convert date column to datetime objects for proper handling by save_dataframe_to_db's conversion
    ohlcv_df['date'] = pd.to_datetime(ohlcv_df['date'])

    save_dataframe_to_db(ohlcv_df, "ohlcv_data", conn, if_exists="append", primary_keys=OHLCV_PRIMARY_KEYS)

    retrieved_ohlcv_df = read_dataframe_from_db("SELECT * FROM ohlcv_data WHERE symbol = 'BTCUSD'", conn)
    logger.info(f"Retrieved BTCUSD OHLCV data ({len(retrieved_ohlcv_df)} rows):\n{retrieved_ohlcv_df}")
    assert len(retrieved_ohlcv_df) == 2, "Upsert logic for OHLCV failed or data not inserted."
    assert retrieved_ohlcv_df[retrieved_ohlcv_df['date'] == '2023-01-01 00:00:00']['open'].iloc[0] == 30001.0, "Upsert did not update existing row."


    latest_btc_ts = get_latest_timestamp("ohlcv_data", conn, symbol="BTCUSD", source_api="test_api", timeframe="1D")
    logger.info(f"Latest BTCUSD timestamp: {latest_btc_ts}")
    assert latest_btc_ts == pd.Timestamp('2023-01-02 00:00:00'), "Latest timestamp for BTCUSD incorrect."

    latest_eth_ts = get_latest_timestamp("ohlcv_data", conn, symbol="ETHUSD", source_api="test_api")
    logger.info(f"Latest ETHUSD timestamp: {latest_eth_ts}") # Should be 2023-01-01
    assert latest_eth_ts == pd.Timestamp('2023-01-01 00:00:00'), "Latest timestamp for ETHUSD incorrect."

    # Test Macro Indicators data saving and reading
    logger.info("--- Testing Macro Indicators Data ---")
    macro_sample_data = [
        ('GDP_USA', '2023-01-01', 25000.5, 'test_fred', 'Quarterly'),
        ('GDP_USA', '2023-04-01', 25500.0, 'test_fred', 'Quarterly'),
        ('UNEMP_USA', '2023-01-01', 3.5, 'test_fred', 'Monthly'),
        ('GDP_USA', '2023-01-01', 25000.6, 'test_fred', 'Quarterly'), # Upsert test
    ]
    macro_df = pd.DataFrame(macro_sample_data, columns=list(MACRO_INDICATORS_TABLE_SCHEMA.keys()))
    macro_df['date'] = pd.to_datetime(macro_df['date'])

    save_dataframe_to_db(macro_df, "macro_indicators", conn, if_exists="append", primary_keys=MACRO_INDICATORS_PRIMARY_KEYS)
    retrieved_macro_df = read_dataframe_from_db("SELECT * FROM macro_indicators WHERE indicator_name = 'GDP_USA'", conn)
    logger.info(f"Retrieved GDP_USA Macro data ({len(retrieved_macro_df)} rows):\n{retrieved_macro_df}")
    assert len(retrieved_macro_df) == 2, "Upsert logic for Macro indicators failed."
    assert retrieved_macro_df[retrieved_macro_df['date'] == '2023-01-01']['value'].iloc[0] == 25000.6, "Upsert did not update existing macro row."

    # Test Financial Events data saving and reading
    logger.info("--- Testing Financial Events Data ---")
    events_sample_data = [
        ('evt1', 'earnings', '2023-01-15', 'AAPL', '{"eps": "1.50"}', 'test_source'),
        ('evt2', 'fed_meeting', '2023-01-20', None, '{}', 'test_source'),
        ('evt1', 'earnings', '2023-01-15', 'AAPL', '{"eps": "1.55"}', 'test_source'), # Upsert
    ]
    events_df = pd.DataFrame(events_sample_data, columns=list(FINANCIAL_EVENTS_TABLE_SCHEMA.keys()))
    events_df['date'] = pd.to_datetime(events_df['date'])

    save_dataframe_to_db(events_df, "financial_events", conn, if_exists="append", primary_keys=FINANCIAL_EVENTS_PRIMARY_KEYS)
    retrieved_events_df = read_dataframe_from_db("SELECT * FROM financial_events WHERE event_id = 'evt1'", conn)
    logger.info(f"Retrieved Financial Event evt1 ({len(retrieved_events_df)} rows):\n{retrieved_events_df}")
    assert len(retrieved_events_df) == 1, "Upsert logic for Financial Events failed."
    assert retrieved_events_df['details_json'].iloc[0] == '{"eps": "1.55"}', "Upsert did not update event."

    conn.close() # Close in-memory or file DB connection

    # Test Parquet operations
    logger.info("--- Testing Parquet Operations ---")
    # Use ohlcv_df from before for Parquet test
    parquet_file_name = "test_ohlcv_data.parquet"
    save_df_to_parquet(ohlcv_df, parquet_file_name) # Uses default PARQUET_DATA_DIR from config

    read_parquet_df = read_df_from_parquet(parquet_file_name)
    logger.info(f"Read {len(read_parquet_df)} rows from Parquet file '{parquet_file_name}'.")
    pd.testing.assert_frame_equal(ohlcv_df.reset_index(drop=True), read_parquet_df.reset_index(drop=True), check_dtype=False) # dtypes can be tricky with Parquet I/O
    logger.info("Parquet save and read test successful.")

    # Test Parquet with specific directory
    custom_parquet_dir = os.path.join(config.PARQUET_DATA_DIR, "custom_subdir")
    save_df_to_parquet(ohlcv_df, parquet_file_name, parquet_dir=custom_parquet_dir)
    read_parquet_custom_df = read_df_from_parquet(parquet_file_name, parquet_dir=custom_parquet_dir)
    pd.testing.assert_frame_equal(ohlcv_df.reset_index(drop=True), read_parquet_custom_df.reset_index(drop=True), check_dtype=False)
    logger.info(f"Parquet save and read test with custom directory '{custom_parquet_dir}' successful.")

    # Test reading non-existent parquet
    try:
        read_df_from_parquet("non_existent_file.parquet")
    except utils.FileIOError as e:
        logger.info(f"Successfully caught expected error for non-existent Parquet: {e}")

    logger.info("--- database_manager.py direct execution tests completed ---")
