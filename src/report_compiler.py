import os
import base64
import io
import pandas as pd
import markdown # For Markdown to HTML conversion

# Configure Matplotlib backend (optional, Agg is good for non-GUI environments)
import matplotlib
# matplotlib.use('Agg') # Uncomment if running in a strictly non-GUI environment and encountering issues
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker # Optional, for plot formatting

import logging
from src import utils
from src import config

# Initialize logger
logger = utils.setup_logger(__name__)

# --- Basic HTML Template and CSS ---
# Using .format() method for compatibility, not f-string for the main template
# to avoid issues with CSS curly braces.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; line-height: 1.6; background-color: #f9f9f9; color: #333; }}
        .container {{ max-width: 1200px; margin: auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #3498db; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px;}}
        h3 {{ color: #2980b9; margin-top: 25px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ddd; padding: 10px 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #e9ecef; }}
        .chart {{ text-align: center; margin: 30px 0; padding: 15px; background-color: #fdfdfd; border: 1px solid #eee; border-radius: 5px; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 4px; }}
        .content-section {{ margin-bottom: 40px; padding: 20px; background-color: #fff; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }}
        .markdown-content p {{ margin-bottom: 1em; }}
        .markdown-content ul, .markdown-content ol {{ padding-left: 20px; }}
        .codehilite {{ background: #f8f8f8; border: 1px solid #ccc; padding: .1em .4em; border-radius: 4px; }} /* For fenced_code */
    </style>
</head>
<body>
    <div class="container">
        <h1>{report_title}</h1>
        {main_content}
    </div>
</body>
</html>
"""

# --- Helper Functions ---
def convert_markdown_to_html(md_text: str) -> str:
    """Converts Markdown text to HTML."""
    try:
        # Using extensions: tables (for pipe tables), fenced_code (for ``` style code blocks),
        # nl2br (for newlines to <br>), codehilite (for syntax highlighting with fenced_code)
        html = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br', 'codehilite'])
        return f"<div class='markdown-content'>{html}</div>"
    except Exception as e:
        logger.error(f"Error converting Markdown to HTML: {e}", exc_info=True)
        return "<p>Error displaying Markdown content.</p>"

def convert_df_to_html_table(df: pd.DataFrame, table_id: str | None = None,
                             classes: str | list[str] | None = None) -> str:
    """Converts a Pandas DataFrame to an HTML table string."""
    if df.empty:
        return "<p>No data available for this table.</p>"
    try:
        default_classes = "dataframe-table pure-table pure-table-striped" # Example classes
        if isinstance(classes, list):
            final_classes = " ".join(classes) if classes else default_classes
        elif isinstance(classes, str):
            final_classes = classes
        else:
            final_classes = default_classes

        html_table = df.to_html(index=False, escape=True, table_id=table_id, classes=final_classes)
        return html_table
    except Exception as e:
        logger.error(f"Error converting DataFrame to HTML table: {e}", exc_info=True)
        return "<p>Error displaying table data.</p>"

def generate_price_chart_base64(df_ohlcv: pd.DataFrame, title: str = "Price Chart") -> str | None:
    """
    Generates a line chart for 'close' price from OHLCV data and returns as base64 encoded string.
    """
    if not isinstance(df_ohlcv, pd.DataFrame) or df_ohlcv.empty or \
       'close' not in df_ohlcv.columns or df_ohlcv['close'].isnull().all():
        logger.warning(f"No valid data available for chart: '{title}'. DataFrame empty or 'close' column missing/all NaN.")
        return "<!-- No data available for chart -->"

    df_chart = df_ohlcv.copy()

    # Ensure 'date' column is suitable for index
    if 'date' in df_chart.columns:
        try:
            df_chart['date'] = pd.to_datetime(df_chart['date'])
            if df_chart['date'].is_unique:
                df_chart = df_chart.set_index('date')
            else: # If dates are not unique, use default numeric index and plot date on x-axis if possible
                 logger.warning("Dates are not unique, using default index for plotting. X-axis might be numeric.")
        except Exception as e:
            logger.error(f"Error processing date column for chart '{title}': {e}. Using default index.")
    elif not isinstance(df_chart.index, pd.DatetimeIndex):
        logger.warning(f"DataFrame for chart '{title}' does not have a DatetimeIndex or a 'date' column. X-axis may be numeric.")


    try:
        # plt.style.use('seaborn-v0_8-darkgrid') # A modern seaborn style
        plt.style.use('ggplot') # Another popular style

        fig, ax = plt.subplots(figsize=(10, 5)) # Slightly smaller default

        # Determine x-axis data
        x_data = df_chart.index if isinstance(df_chart.index, pd.DatetimeIndex) else df_chart.get('date', pd.Series(range(len(df_chart))))

        ax.plot(x_data, df_chart['close'], label='Close Price', color='dodgerblue', linewidth=1.5)

        # Optionally plot other OHLC data if available
        if 'high' in df_chart.columns and 'low' in df_chart.columns:
            ax.fill_between(x_data, df_chart['high'], df_chart['low'], color='lightgray', alpha=0.3, label='High/Low Range')

        ax.set_title(title, fontsize=15)
        ax.set_xlabel("Date" if isinstance(x_data, pd.DatetimeIndex) or x_data.name == 'date' else "Index", fontsize=10)
        ax.set_ylabel("Price", fontsize=10)

        ax.legend(fontsize='small')
        ax.grid(True, linestyle='--', alpha=0.6)

        if isinstance(x_data, pd.DatetimeIndex) or x_data.name == 'date' and not x_data.empty :
            fig.autofmt_xdate() # Improve date formatting

        # Format y-axis ticks to avoid scientific notation for typical price ranges
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

        plt.tight_layout(pad=1.5) # Add some padding

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        plt.close(fig) # Close the figure to free memory

        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')

        return f'<img src="data:image/png;base64,{img_base64}" alt="{title}" />'
    except Exception as e:
        logger.error(f"Error generating chart '{title}': {e}", exc_info=True)
        plt.close(fig) # Ensure figure is closed on error too
        return f"<!-- Error generating chart: {title} -->"


# --- Main Report Compilation Function ---
def compile_html_report(report_title: str, sections: list[dict],
                        output_filename: str = "financial_report.html",
                        output_dir: str | None = None) -> str | None:
    """
    Compiles a list of sections (markdown, tables, charts) into a single HTML report file.

    Args:
        report_title: The title of the HTML report.
        sections: A list of dictionaries, where each dict defines a section.
                  Example: [{'type': 'markdown', 'title': 'Section Title', 'content': 'md_text'},
                            {'type': 'table', 'title': 'Table Title', 'dataframe': pd.DataFrame()},
                            {'type': 'chart', 'title': 'Chart Title', 'data': pd.DataFrame(),
                             'chart_function': generate_price_chart_base64}]
        output_filename: Name of the output HTML file.
        output_dir: Directory to save the report. Uses config.OUTPUT_DIR if None.

    Returns:
        The full path to the generated HTML report, or None if an error occurs.
    """
    final_output_dir = output_dir if output_dir is not None else config.OUTPUT_DIR
    if final_output_dir is None: # If still None, means config.OUTPUT_DIR is also None
        logger.error("Output directory is not specified and config.OUTPUT_DIR is not set.")
        raise utils.ConfigError("Report output directory is not configured.")

    try:
        utils.ensure_directory_exists(final_output_dir)
    except utils.FileIOError as e: # Raised by ensure_directory_exists if it fails
        logger.error(f"Failed to ensure output directory {final_output_dir} exists: {e}", exc_info=True)
        raise # Re-raise the error as it's critical

    full_output_path = os.path.join(final_output_dir, output_filename)
    main_html_content = ""

    for i, section in enumerate(sections):
        section_title = section.get('title', f'Section {i+1}')
        main_html_content += f"<div class='content-section'>\n<h2>{section_title}</h2>\n"

        section_type = section.get('type')

        try:
            if section_type == 'markdown':
                content = section.get('content')
                if isinstance(content, str):
                    main_html_content += convert_markdown_to_html(content)
                else:
                    logger.warning(f"Markdown content for section '{section_title}' is not a string. Skipping.")
                    main_html_content += "<p>Content for this section is invalid (expected markdown string).</p>"

            elif section_type == 'table':
                dataframe = section.get('dataframe')
                if isinstance(dataframe, pd.DataFrame):
                    main_html_content += convert_df_to_html_table(dataframe)
                else:
                    logger.warning(f"DataFrame for section '{section_title}' is not a valid DataFrame. Skipping.")
                    main_html_content += "<p>Data for this table is invalid.</p>"

            elif section_type == 'chart':
                chart_data = section.get('data')
                chart_function = section.get('chart_function')
                chart_plot_title = section.get('chart_title', section_title) # Use section title for chart if specific not given

                if callable(chart_function) and isinstance(chart_data, pd.DataFrame):
                    chart_html = chart_function(chart_data, title=chart_plot_title)
                    if chart_html:
                        main_html_content += f"<div class='chart'>{chart_html}</div>"
                    else:
                        logger.warning(f"Chart generation returned None for section '{section_title}'.")
                        main_html_content += "<p>Chart could not be generated for this section.</p>"
                else:
                    logger.warning(f"Invalid chart data or function for section '{section_title}'. Skipping.")
                    main_html_content += "<p>Chart data or generation function is invalid.</p>"

            else:
                logger.warning(f"Unknown section type '{section_type}' for section '{section_title}'.")
                main_html_content += f"<p>Unknown content type: {section_type}</p>"
        except Exception as e:
            logger.error(f"Error processing section '{section_title}' (type: {section_type}): {e}", exc_info=True)
            main_html_content += f"<p>Error rendering this section: {e}</p>"

        main_html_content += "</div>\n"

    final_html = HTML_TEMPLATE.format(report_title=report_title, main_content=main_html_content)

    try:
        with open(full_output_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        logger.info(f"HTML report generated successfully: {full_output_path}")
        return full_output_path
    except IOError as e: # More specific for file writing issues
        logger.error(f"IOError writing HTML report to {full_output_path}: {e}", exc_info=True)
        raise utils.FileIOError(f"Failed to write HTML report: {e}", original_exception=e)
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error writing HTML report to {full_output_path}: {e}", exc_info=True)
        raise utils.AppBaseError(f"Unexpected error during report writing: {e}", original_exception=e)


if __name__ == '__main__':
    logger.info("--- Running report_compiler.py direct execution tests ---")

    # Ensure OUTPUT_DIR is set for testing, or use a temporary one
    if not config.OUTPUT_DIR:
        # Fallback to a default output directory in the project root for this test
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Assumes src is one level down
        config.OUTPUT_DIR = os.path.join(project_root, "test_reports_output")
        logger.warning(f"config.OUTPUT_DIR not set. Using temporary for test: {config.OUTPUT_DIR}")
    utils.ensure_directory_exists(config.OUTPUT_DIR) # Ensure it exists

    # Sample Markdown
    sample_md = """
### Introduction
This is a sample financial report. It includes text, tables, and charts.

- Point 1
- Point 2

```python
print("Hello, Report!")
```
    """

    # Sample DataFrame for Table
    sample_table_df = pd.DataFrame({
        'Metric': ['Total Revenue', 'Net Profit', 'EPS'],
        'Value': ['$1,000,000', '$200,000', '$2.50'],
        'Change YoY': ['+10%', '+15%', '+12%']
    })

    # Sample DataFrame for Chart
    date_rng = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                               '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10'])
    sample_chart_df = pd.DataFrame({
        'date': date_rng,
        'close': [100, 102, 101, 105, 103, 106, 108, 107, 110, 112],
        'high':  [102, 103, 103, 106, 105, 107, 109, 109, 111, 113],
        'low':   [99,  101, 100, 102, 101, 104, 106, 105, 108, 110]
    })
    # sample_chart_df = sample_chart_df.set_index('date') # Test with date as index

    # Define report sections
    report_sections = [
        {'type': 'markdown', 'title': 'Market Overview (Markdown)', 'content': sample_md},
        {'type': 'table', 'title': 'Key Financial Metrics (Table)', 'dataframe': sample_table_df},
        {'type': 'chart', 'title': 'Stock Price Performance (Chart)',
         'data': sample_chart_df, 'chart_function': generate_price_chart_base64,
         'chart_title': '10-Day Stock Price Trend'}, # Specific title for the chart plot
        {'type': 'markdown', 'title': 'Analysis & Outlook',
         'content': "The outlook is **positive** based on recent performance and market sentiment."},
        {'type': 'table', 'title': 'Empty Table Test', 'dataframe': pd.DataFrame()},
        {'type': 'chart', 'title': 'Empty Chart Test', 'data': pd.DataFrame(), 'chart_function': generate_price_chart_base64},
        {'type': 'invalid_section_type', 'title': 'Invalid Section', 'content': 'This should be handled gracefully.'}
    ]

    report_file_path = compile_html_report(
        report_title="Monthly Financial Analysis - January 2023",
        sections=report_sections,
        output_filename="test_financial_report.html"
        # output_dir will use config.OUTPUT_DIR by default
    )

    if report_file_path:
        logger.info(f"Test report generated: {report_file_path}")
        # Basic check: Does the file exist?
        assert os.path.exists(report_file_path), f"Report file was not created at {report_file_path}"
        # Further checks could involve reading the file and checking for specific content,
        # but visual inspection is often needed for HTML.
        with open(report_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            assert "Monthly Financial Analysis - January 2023" in html_content
            assert "Market Overview (Markdown)" in html_content
            assert "Key Financial Metrics (Table)" in html_content
            assert "Stock Price Performance (Chart)" in html_content
            assert "data:image/png;base64," in html_content # Check if chart image data is embedded
            assert "<!-- No data available for chart -->" in html_content # For empty chart test
            assert "<p>No data available for this table.</p>" in html_content # For empty table test
            assert "Unknown content type: invalid_section_type" in html_content

    else:
        logger.error("Test report generation FAILED.")
        assert False, "Report compilation returned None"

    # Test error for invalid output directory (conceptual)
    logger.info("\n--- Conceptual Test: Invalid Output Directory ---")
    invalid_output_dir = "/non_existent_path_hopefully/reports"
    # This path should ideally not be writable or creatable without sudo.
    # On some systems, this might still pass if parent exists and user has rights.
    # A more robust test would be to mock os.makedirs to raise an error.
    try:
        compile_html_report(
            report_title="Error Test Report",
            sections=[{'type': 'markdown', 'title': 'Content', 'content': 'Test'}],
            output_filename="error_report.html",
            output_dir=invalid_output_dir
        )
        # If it didn't raise an exception where expected, it might be an issue or permissions allowed it.
        # logger.warning(f"Compile_html_report did not raise an error for invalid output_dir '{invalid_output_dir}'. This might be due to permissions or test setup.")
    except utils.FileIOError as e:
        logger.info(f"Caught expected FileIOError for invalid output directory: {e}")
        assert "Failed to write HTML report" in str(e) or "Failed to ensure output directory" in str(e) # Based on where it might fail
    except utils.ConfigError as e: # If config.OUTPUT_DIR was None and no output_dir passed
        logger.info(f"Caught expected ConfigError: {e}")
    except Exception as e: # Catch any other unexpected error
        logger.error(f"Unexpected error during invalid output directory test: {e}", exc_info=True)
        # assert False, f"Unexpected error for invalid output dir: {e}"


    logger.info("--- report_compiler.py direct execution tests completed ---")
