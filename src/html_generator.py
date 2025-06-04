# coding: utf-8
"""
This script generates monthly HTML reports by combining analysis from TXT reports,
financial data (for charts), and HTML structure/further insights from the Gemini API.
"""
import json
import os
import logging
import glob
import re
import pandas as pd # Import pandas
from datetime import datetime # Import datetime

# Attempt to import Gemini; set a flag if unavailable
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Attempt to import Plotly and Kaleido for chart generation
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Warning: Plotly library not found. Chart generation will be skipped.")

# Configuration
TXT_REPORTS_DIR = "reports/txt"
JSON_DATA_FILE = "monthly_posts_with_financial_data.json" # From subtask 2
CHARTS_OUTPUT_DIR = "reports/charts"
HTML_OUTPUT_DIR = "reports/html"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Mock/Skip API Call Configuration ---
SKIP_GEMINI_HTML_CALL_GLOBAL = False # Set to True for local testing
MOCK_GEMINI_HTML_RESPONSE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>月度金融市場深度分析報告 - {YYYY_MM}</title>
    <!-- GOOGLE_API_KEY is read from environment variables server-side, not exposed here. -->
    <style>
        :root {{
            --primary-color: #4a90e2; /* Gemini Blue */
            --secondary-color: #f5a623; /* Gemini Orange */
            --text-color: #333;
            --bg-color: #fff;
            --accent-color: #d0021b; /* Gemini Red */
            --neutral-color: #7f8c8d; /* Gemini Grey */
            --border-color: #e0e0e0;
        }}
        body.dark-mode {{
            --text-color: #eee;
            --bg-color: #2c2c2c;
            --border-color: #444;
        }}
        /* Add more styles here based on Gemini visual style */
        body {{ font-family: sans-serif; margin: 0; padding: 20px; background-color: var(--bg-color); color: var(--text-color); }}
        header {{ background-color: var(--primary-color); color: white; padding: 1em; text-align: center; }}
        h1, h2, h3 {{ color: var(--primary-color); }}
        body.dark-mode h1, body.dark-mode h2, body.dark_mode h3 {{ color: var(--secondary-color); }}
        .chart-container {{ margin: 20px 0; text-align: center; }}
        .chart-container img {{ max-width: 100%; height: auto; border: 1px solid var(--border-color); }}
        .chart-caption {{ font-style: italic; color: var(--neutral-color); margin-top: 5px; }}
    </style>
</head>
<body>
    <header><h1>{YYYY_MM} 金融市場深度分析報告</h1></header>
    <section id="overview"><h2>I. 當月概覽</h2><p>(Mocked: Overview for {YYYY_MM})</p></section>
    <section id="event-interpretation"><h2>II. 金融事件解讀</h2><p>(Mocked: Financial event interpretation for {YYYY_MM})</p><div>{TXT_REPORT_SECTION_3_CONTENT}</div></section>
    <section id="trading-logic"><h2>III. 交易邏輯分析</h2><p>(Mocked: Trading logic analysis for {YYYY_MM})</p></section>
    <section id="takeaways"><h2>IV. 成功交易啟示</h2><p>(Mocked: Trading takeaways for {YYYY_MM})</p></section>
    <section id="charts">
        <h2>V. 視覺化市場數據</h2>
        <div class="chart-container">
            <img src='charts/{YYYY_MM}_VIX_OCHLV_chart.png' alt='VIX OCHLV Chart for {YYYY_MM}'>
            <p class="chart-caption">VIX 指數月度 OCHLV 走勢圖。</p>
        </div>
        <div class="chart-container">
            <img src='charts/{YYYY_MM}_TSLA_OCHLV_chart.png' alt='TSLA OCHLV Chart for {YYYY_MM}'>
            <p class="chart-caption">TSLA 月度 OCHLV 走勢圖。</p>
        </div>
    </section>
    <footer><p>報告生成時間: {GENERATION_TIME}</p></footer>
</body>
</html>
"""

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_json_data(filepath):
    """Loads data from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: JSON data file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        return None

def read_txt_report(filepath):
    """Reads content from a TXT report file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Error: TXT report file not found at {filepath}")
        return None
    except IOError as e:
        logging.error(f"Error reading TXT report file {filepath}: {e}")
        return None

def configure_gemini_for_html(): # Renamed to avoid conflict if used in same context
    """Configures the Gemini API with the provided key."""
    if not GEMINI_AVAILABLE:
        logging.warning("Gemini library (google.generativeai) not available. Skipping Gemini configuration.")
        return False
    if not GOOGLE_API_KEY:
        logging.error("GOOGLE_API_KEY environment variable not set. Cannot use Gemini API unless calls are skipped.")
        return False
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        logging.info("Gemini API configured successfully for HTML generation.")
        return True
    except Exception as e:
        logging.error(f"Error configuring Gemini API: {e}")
        return False

def get_ohlcv_data_for_month(all_financial_data, year_month_str, keyword_map):
    """
    Extracts OCHLV data for specified keywords for a given month.
    This function needs to parse financial_data_summary to find relevant data,
    or ideally, access structured OCHLV if available from monthly_posts_with_financial_data.json.
    For now, this is a placeholder as the JSON doesn't store raw OCHLV.
    It should ideally load raw data that financial_data_fetcher might have saved (if it did).

    Let's assume financial_data_fetcher.py would need to be modified to save raw yfinance data
    if we want to plot it here. For this subtask, we might need to re-fetch or use dummy data for plotting.

    For now, we'll simulate this by re-fetching minimal data for known yfinance tickers
    found in the financial_summary for that month. This is inefficient but demonstrates plotting.
    A better approach: financial_data_fetcher saves raw data.
    """
    if not PLOTLY_AVAILABLE:
        logging.warning("Plotly not available, skipping OCHLV data fetching for charts.")
        return {}

    month_data = all_financial_data.get(year_month_str)
    if not month_data or "financial_data_summary" not in month_data:
        return {}

    # Extract yfinance tickers from summary
    # Example: "TSLA (TSLA): ..." -> "TSLA"
    # Example: "VIX (^VIX): ..." -> "^VIX"
    tickers_to_plot = {} # Store as {name_for_filename: ticker_id}
    pattern = re.compile(r'([^(]+)\s*\(([^)]+)\):')
    for summary_item in month_data["financial_data_summary"]:
        match = pattern.search(summary_item)
        if match:
            name_part = match.group(1).strip().replace(" ", "_").replace("/", "_") # Sanitize for filename
            id_part = match.group(2).strip()
            # Check if it's likely a yfinance ticker (not FRED ID like DGS10)
            # This is a heuristic; ideally, the JSON would specify type or source.
            if not any(fred_char in id_part for fred_char in ['DGS', 'UNRATE', 'DCOIL']): # Basic filter
                tickers_to_plot[name_part] = id_part

    if not tickers_to_plot:
        return {}

    # Re-fetch data (simplified from financial_data_fetcher.py)
    # This is inefficient. Ideally, fetcher saves raw data.
    from datetime import datetime, timedelta
    from calendar import monthrange
    import yfinance as yf

    year, month_int = map(int, year_month_str.split('-'))
    start_date_dt = datetime(year, month_int, 1)
    _, last_day = monthrange(year, month_int)
    end_date_dt = datetime(year, month_int, last_day)

    fetched_ohlcv_data = {}
    for name, ticker_id in tickers_to_plot.items():
        try:
            logging.info(f"Fetching chart data for {name} ({ticker_id}) for {year_month_str}...")
            # Fetch slightly wider for ATR calculations if needed, then trim
            data_df = yf.download(ticker_id,
                                  start=(start_date_dt - timedelta(days=30)).strftime("%Y-%m-%d"), # previous 30 days for ATR
                                  end=(end_date_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                                  progress=False, auto_adjust=False) # auto_adjust=False is simpler for OHLCV
            if not data_df.empty:
                # Calculate ATR (Average True Range) - example for a technical indicator
                high_low = data_df['High'] - data_df['Low']
                high_close = (data_df['High'] - data_df['Close'].shift()).abs()
                low_close = (data_df['Low'] - data_df['Close'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                data_df['ATR'] = true_range.rolling(window=14).mean() # 14-day ATR

                # Filter data to the actual month for plotting
                data_df = data_df[(data_df.index >= start_date_dt) & (data_df.index <= end_date_dt)]
                if not data_df.empty:
                     fetched_ohlcv_data[name] = data_df
        except Exception as e:
            logging.error(f"Failed to fetch/process chart data for {ticker_id}: {e}")

    return fetched_ohlcv_data


def generate_and_save_charts(year_month_str, ohlcv_data_map):
    """Generates and saves charts for the given data."""
    if not PLOTLY_AVAILABLE:
        logging.warning("Plotly not available. Skipping chart generation.")
        return []
    if not ohlcv_data_map:
        logging.info(f"No OCHLV data provided for {year_month_str} to generate charts.")
        return []

    if not os.path.exists(CHARTS_OUTPUT_DIR):
        os.makedirs(CHARTS_OUTPUT_DIR)
        logging.info(f"Created charts directory: {CHARTS_OUTPUT_DIR}")

    chart_filenames = []

    for item_name, df in ohlcv_data_map.items():
        if df.empty:
            continue

        # 1. OCHLV Candlestick Chart
        try:
            fig_ohlcv = go.Figure(data=[go.Candlestick(x=df.index,
                                                   open=df['Open'], high=df['High'],
                                                   low=df['Low'], close=df['Close'])])
            fig_ohlcv.update_layout(title=f'{item_name} OCHLV ({year_month_str})', xaxis_rangeslider_visible=False)
            filename_ohlcv = f"{year_month_str}_{item_name}_OCHLV_chart.png"
            filepath_ohlcv = os.path.join(CHARTS_OUTPUT_DIR, filename_ohlcv)
            fig_ohlcv.write_image(filepath_ohlcv, scale=2) # Increased scale for better resolution
            chart_filenames.append(filename_ohlcv)
            logging.info(f"Generated OCHLV chart: {filepath_ohlcv}")
        except Exception as e:
            logging.error(f"Failed to generate OCHLV chart for {item_name}: {e}")

        # 2. Volume Chart
        try:
            # Try squeezing the Series to ensure it's 1D for Plotly Express
            fig_vol = px.bar(x=df.index, y=df['Volume'].squeeze(), title=f'{item_name} Volume ({year_month_str})')
            filename_vol = f"{year_month_str}_{item_name}_Volume_chart.png"
            filepath_vol = os.path.join(CHARTS_OUTPUT_DIR, filename_vol)
            fig_vol.write_image(filepath_vol, scale=2)
            chart_filenames.append(filename_vol)
            logging.info(f"Generated Volume chart: {filepath_vol}")
        except Exception as e:
            logging.error(f"Failed to generate Volume chart for {item_name}: {e}")

        # 3. ATR (Volatility Indicator) Chart
        if 'ATR' in df.columns and not df['ATR'].isnull().all():
            try:
                fig_atr = px.line(x=df.index, y=df['ATR'], title=f'{item_name} ATR (14-day) ({year_month_str})')
                filename_atr = f"{year_month_str}_{item_name}_ATR_chart.png"
                filepath_atr = os.path.join(CHARTS_OUTPUT_DIR, filename_atr)
                fig_atr.write_image(filepath_atr, scale=2)
                chart_filenames.append(filename_atr)
                logging.info(f"Generated ATR chart: {filepath_atr}")
            except Exception as e:
                logging.error(f"Failed to generate ATR chart for {item_name}: {e}")

    return chart_filenames # Relative paths for HTML

def construct_gemini_html_prompt(txt_report_content, year_month_str, chart_relative_paths):
    """Constructs the prompt for Gemini to generate HTML report."""

    chart_placeholders_html = ""
    if chart_relative_paths:
        for chart_path in chart_relative_paths:
            # Extract item name from filename like "YYYY_MM_ItemName_Type_chart.png"
            try:
                parts = os.path.basename(chart_path).split('_')
                item_name_in_chart = parts[2] if len(parts) > 3 else "Chart"
                chart_type = parts[3] if len(parts) > 4 else "Analysis"
                alt_text = f"{item_name_in_chart} {chart_type} for {year_month_str}"
                caption = f"{item_name_in_chart} {chart_type.replace('_', ' ')}圖表 ({year_month_str})。" # Make caption more readable
            except IndexError:
                alt_text = f"金融圖表 ({year_month_str})"
                caption = f"金融數據圖表 ({year_month_str})。"

            chart_placeholders_html += f"""
<div class="chart-container">
    <img src='{chart_path}' alt='{alt_text}'>
    <p class="chart-caption">{caption}</p>
</div>
"""
    else:
        chart_placeholders_html = "<p>本月無可用圖表。</p>"

    # Extract Section 3 (AI summary) from TXT report to embed it properly
    section_3_content = ""
    match = re.search(r"## 3\. 當月金融大事件與小事件彙整 \(Gemini AI 彙整\)(.*)", txt_report_content, re.DOTALL)
    if match:
        section_3_content = match.group(1).strip()


    prompt = f"""你是一位頂尖的資深量化分析師、金融教育家，同時也是一位具備卓越內容組織和網頁排版能力的專家。你的任務是根據提供的詳細月度金融分析報告內容，創建一份精美、專業且具備高度教學價值的 HTML 報告。這份報告不僅要呈現事實，更要深入推理交易邏輯，並提供實用教學。

以下是 {year_month_str} 月份的詳細金融分析報告文字稿：
---
{txt_report_content}
---

任務要求：
請將以上文字報告內容轉換為一份完整的 HTML 報告。
1.  **整體風格**：請採用類似 Google Gemini 的視覺風格。使用 CSS `:root` 變量定義亮色和暗色模式的基礎顏色。提供一個簡單的切換按鈕或機制（可選，若複雜可省略）。
    *   亮色模式 (預設): 背景白、文字深灰、主色調藍 (Gemini Blue)、輔色調橘 (Gemini Orange)。
    *   暗色模式: 背景深灰、文字淺灰、主色調亮藍、輔色調亮橘。
2.  **HTML 結構**：
    *   `<head>`: 包含 UTF-8 meta, viewport, 報告月份標題, 以及 CSS 樣式（包含亮暗模式）。
    *   `<body>`:
        *   `<header>`: 報告主標題 (例如 "{year_month_str} 金融市場深度分析報告")。
        *   `<nav>` (可選): 快速導航至各區段。
        *   `<main>`: 包含以下主要區段：
            *   **I. 當月概覽 (Overview)**: (此部分內容請你根據整體報告自行總結，約150-250字，強調市場情緒和關鍵轉折)
            *   **II. 金融事件解讀 (Financial Event Interpretation)**: (此處整合文字報告中 "## 3. 當月金融大事件與小事件彙整 (Gemini AI 彙整)" 的內容: "{section_3_content}")
            *   **III. 交易邏輯分析 (Trading Logic Analysis)**: (此為核心，請你基於報告中的貼文內容、數據摘要、以及金融事件，深入分析至少2-3個具體的交易邏輯。例如，某事件如何影響特定商品價格，市場對此的預期反應，實際走勢是否符合，以及潛在的發散或收斂現象。請結合技術分析概念，如支撐、壓力、趨勢線、指標等進行推論，即使原始數據未提供所有指標，也請基於常見市場行為進行合理推斷和教學。例如，若提到VIX上升，可以解釋恐慌指數的意義和用法。)
            *   **IV. 成功交易啟示與學習 (Key Takeaways and Learnings)**: (提煉出2-3條具有普遍指導意義的交易原則、風險管理技巧或市場觀察方法，作為教學總結。)
            *   **V. 視覺化市場數據 (Visualized Market Data)**: (此處嵌入以下圖表佔位符。確保每個圖表下方有簡要解說。)
                {chart_placeholders_html}
        *   `<footer>`: 報告生成時間或版本。
3.  **內容呈現**：
    *   專業術語使用一致，必要時可提供簡短註解。
    *   排版清晰，易於閱讀。使用標題 (h1-h4), 段落 (p), 列表 (ul/ol), 表格 (table) 等元素。
    *   圖表下方應有簡要解說，說明圖表類型和主要觀察點。
4.  **輸出格式**：請僅輸出完整的 HTML 程式碼，不需要任何額外的解釋或引言。確保 HTML 結構完整且語法正確。
5.  **API 金鑰安全**：在 HTML 的 `<head>` 中加入一個註釋，說明 API 金鑰是伺服器端通過環境變數讀取的，不會暴露在客戶端：`<!-- GOOGLE_API_KEY is read from environment variables server-side, not exposed here. -->`

請開始生成 {year_month_str} 的 HTML 報告。
"""
    return prompt

def get_gemini_html_response(prompt, current_skip_html_call_flag):
    """Calls Gemini API for HTML generation."""
    if current_skip_html_call_flag:
        logging.info("Skipping actual Gemini API call for HTML. Using mock response.")
        # Replace placeholders in mock response
        # For simplicity, YYYY_MM is hardcoded in MOCK_GEMINI_HTML_RESPONSE for now
        # A more dynamic mock would parse YYYY_MM from prompt or arguments
        return MOCK_GEMINI_HTML_RESPONSE

    if not GEMINI_AVAILABLE or not genai.conf.api_key:
        logging.warning("Gemini API not available or key not configured for HTML. Skipping call.")
        return "<!-- Gemini API call skipped due to missing library or API key. -->"

    try:
        model = genai.GenerativeModel('gemini-pro') # Consider specific model for HTML
        response = model.generate_content(prompt)
        full_response_text = "".join(part.text for part in response.parts) if hasattr(response, 'parts') and response.parts else response.text
        if not full_response_text.strip() or not full_response_text.lower().startswith("<!doctype html"):
            logging.warning(f"Gemini API returned an empty or non-HTML response for HTML generation. Length: {len(full_response_text)}")
            return f"<!-- Gemini API returned unexpected content. Response was: {full_response_text[:200]}... -->"
        return full_response_text
    except Exception as e:
        logging.error(f"Error calling Gemini API for HTML: {e}")
        return f"<!-- Error generating HTML from Gemini API: {e} -->"

def save_html_report(year_month_str, html_content):
    """Saves the HTML content to a file."""
    if not os.path.exists(HTML_OUTPUT_DIR):
        os.makedirs(HTML_OUTPUT_DIR)
        logging.info(f"Created HTML output directory: {HTML_OUTPUT_DIR}")

    filename = f"final_report_{year_month_str.replace('-', '_')}.html"
    filepath = os.path.join(HTML_OUTPUT_DIR, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"Successfully saved HTML report: {filepath}")
    except IOError as e:
        logging.error(f"Error writing HTML file {filepath}: {e}")


def main():
    """Main function to orchestrate HTML report generation."""
    global SKIP_GEMINI_HTML_CALL_GLOBAL
    logging.info("Starting HTML report generation process...")

    # Configure Gemini (important to check if API key is actually set for this run)
    gemini_configured_ok = configure_gemini_for_html()

    current_run_skip_gemini_html = SKIP_GEMINI_HTML_CALL_GLOBAL or not GEMINI_AVAILABLE or not gemini_configured_ok

    if current_run_skip_gemini_html and not SKIP_GEMINI_HTML_CALL_GLOBAL :
         logging.warning("HTML Gemini calls will be skipped for this run due to missing library or API key issues, despite SKIP_GEMINI_HTML_CALL_GLOBAL=False.")
    elif SKIP_GEMINI_HTML_CALL_GLOBAL:
        logging.info("SKIP_GEMINI_HTML_CALL_GLOBAL is True. HTML Gemini calls will use mock data.")


    all_financial_data = load_json_data(JSON_DATA_FILE)
    if not all_financial_data:
        logging.error(f"Failed to load financial data from {JSON_DATA_FILE}. Charts cannot be generated accurately.")
        # Decide if to proceed. For now, proceed, charts might be empty or based on dummy.

    txt_report_files = glob.glob(os.path.join(TXT_REPORTS_DIR, "monthly_report_*.txt"))
    if not txt_report_files:
        logging.warning(f"No TXT report files found in {TXT_REPORTS_DIR}. Cannot generate HTML reports.")
        return

    for txt_filepath in sorted(txt_report_files):
        filename = os.path.basename(txt_filepath)
        match = re.match(r"monthly_report_(\d{4})_(\d{2})\.txt", filename)
        if not match:
            logging.warning(f"Skipping file with unexpected name format: {filename}")
            continue

        year, month = match.groups()
        year_month_str = f"{year}-{month}"
        logging.info(f"\nProcessing HTML report for month: {year_month_str} from {txt_filepath}")

        txt_report_content = read_txt_report(txt_filepath)
        if not txt_report_content:
            continue

        # Chart generation
        prompt_chart_paths = [] # Initialize prompt_chart_paths
        # chart_relative_paths = [] # This variable was unused, removing for clarity
        if PLOTLY_AVAILABLE and all_financial_data : # Ensure plotly is there and we have data
            ohlcv_data = get_ohlcv_data_for_month(all_financial_data, year_month_str, {}) # Keyword map not used yet in get_ohlcv
            if ohlcv_data:
                raw_chart_filenames = generate_and_save_charts(year_month_str, ohlcv_data)
                # Corrected paths for prompt, assuming HTML is in reports/html/
                # and charts are in reports/charts/. So path in HTML is ../charts/filename.png
                prompt_chart_paths = [f"../{CHARTS_OUTPUT_DIR.replace('reports/', '')}/{fname}".replace("\\","/") for fname in raw_chart_filenames]
            else:
                logging.info(f"No OCHLV data extracted for {year_month_str} to generate charts.")
        else:
            logging.info(f"Skipping chart generation for {year_month_str} (Plotly available: {PLOTLY_AVAILABLE}, Financial data available: {bool(all_financial_data)}).")

        gemini_html_prompt = construct_gemini_html_prompt(txt_report_content, year_month_str, prompt_chart_paths)
        logging.info(f"Constructed Gemini HTML prompt for {year_month_str} (length: {len(gemini_html_prompt)} chars).")

        html_content = get_gemini_html_response(gemini_html_prompt, current_run_skip_gemini_html)

        # Simple placeholder replacement if mock is used and contains them
        if current_run_skip_gemini_html:
            html_content = html_content.replace("{YYYY_MM}", year_month_str) # Basic replacement
            # More sophisticated replacement for chart paths if needed, but mock is simple for now.
            # Also for TXT_REPORT_SECTION_3_CONTENT
            section_3_content_mock = ""
            match_mock = re.search(r"## 3\. 當月金融大事件與小事件彙整 \(Gemini AI 彙整\)(.*)", txt_report_content, re.DOTALL)
            if match_mock: section_3_content_mock = match_mock.group(1).strip()
            html_content = html_content.replace("{TXT_REPORT_SECTION_3_CONTENT}", section_3_content_mock)
            html_content = html_content.replace("{GENERATION_TIME}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


        save_html_report(year_month_str, html_content)

    logging.info("HTML report generation process completed.")

if __name__ == "__main__":
    # This block helps manage test behavior regarding API calls.
    if not os.path.exists(JSON_DATA_FILE):
        logging.warning(f"{JSON_DATA_FILE} not found. Creating a dummy version for html_generator testing.")
        dummy_financial_data = {
            "2023-01": {
                "posts": [{"title": "Jan Post", "date": "2023-01-15", "post_content": "Content about VIX, TSLA.", "comments": ""}],
                "financial_data_summary": ["VIX (^VIX): VIX summary...", "TSLA (TSLA): TSLA summary..."]
            },
             "2023-02": {
                "posts": [{"title": "Feb Post", "date": "2023-02-15", "post_content": "Content about AAPL.", "comments": ""}],
                "financial_data_summary": ["AAPL (AAPL): AAPL summary..."]
            }
        }
        with open(JSON_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dummy_financial_data, f, ensure_ascii=False, indent=4)

    # Create dummy TXT reports if they don't exist (based on report_compiler's mock output structure)
    if not os.path.exists(TXT_REPORTS_DIR):
        os.makedirs(TXT_REPORTS_DIR)

    sample_txt_months = ["2023-01", "2023-02"]
    for ym_str in sample_txt_months:
        year, month = ym_str.split('-')
        txt_path = os.path.join(TXT_REPORTS_DIR, f"monthly_report_{year}_{month}.txt")
        if not os.path.exists(txt_path):
            logging.info(f"Creating dummy TXT report: {txt_path}")
            dummy_txt_content = f"""# {year} 年 {month} 月 金融市場深度分析報告
---
## 1. 原始貼文內容整理
### 貼文 1
標題: Dummy Post for {ym_str}
日期: {year}-{month}-15
內容: Dummy post content for {ym_str} mentioning VIX, TSLA, AAPL.
留言: Dummy comments.
---
## 2. 當月金融市場數據概覽
- VIX (^VIX): Dummy VIX summary for {ym_str}
- TSLA (TSLA): Dummy TSLA summary for {ym_str}
- AAPL (AAPL): Dummy AAPL summary for {ym_str}
---
## 3. 當月金融大事件與小事件彙整 (Gemini AI 彙整)
{MOCK_GEMINI_RESPONSE}
""" # Using the report_compiler's mock for consistency in test
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(dummy_txt_content)


    if not GOOGLE_API_KEY and not SKIP_GEMINI_HTML_CALL_GLOBAL:
        logging.warning("GOOGLE_API_KEY environment variable is not set. Forcing SKIP_GEMINI_HTML_CALL_GLOBAL = True for this test run.")
        SKIP_GEMINI_HTML_CALL_GLOBAL = True

    if not PLOTLY_AVAILABLE:
        logging.warning("Plotly is not available. Charts will not be generated.")

    main()

    logging.info(f"Script finished. HTML Reports should be in '{HTML_OUTPUT_DIR}', Charts in '{CHARTS_OUTPUT_DIR}'.")
    logging.info(f"Gemini Available (library): {GEMINI_AVAILABLE}, Plotly Available: {PLOTLY_AVAILABLE}")
    logging.info(f"Google API Key was Set: {bool(GOOGLE_API_KEY)}")
    logging.info(f"Gemini HTML Calls Skipped (this run): {SKIP_GEMINI_HTML_CALL_GLOBAL or not GEMINI_AVAILABLE or not genai.conf.api_key if GEMINI_AVAILABLE else 'N/A due to lib missing'}")

print("html_generator.py loaded.")
