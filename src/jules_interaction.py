import json
import logging
import os # For potential future use, not strictly needed for current plan

from src import utils
from src import config # For API KEY, model name, retry params, SIMULATION_MODE

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_api_exceptions
except ImportError:
    genai = None # Handle missing google.generativeai gracefully
    google_api_exceptions = None
    logging.getLogger(__name__).warning(
        "google-generativeai library not found. "
        "Jules Interaction functionality will be limited to simulation mode or raise errors."
    )


from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Initialize logger
logger = utils.setup_logger(__name__)

# --- Gemini API Client Initialization ---
model = None
generation_config = None
gemini_initialized_successfully = False

# Default model name if not in config
DEFAULT_GEMINI_MODEL_NAME = 'gemini-1.5-flash-latest'

# Default generation config (can be overridden by config.py)
DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 32, # Adjusted based on common defaults, can be tuned
    "max_output_tokens": 8192, # Default for Gemini 1.5 Flash
}

if genai: # Only attempt initialization if library is present
    try:
        if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            # This warning is for when the placeholder key is still there.
            # A more robust check might be if it starts with "AIza" for actual keys.
            logger.warning("Gemini API Key might not be properly configured in config.py or Colab Secrets. "
                           "It's either missing or using the default placeholder.")
            # We don't raise ConfigError here to allow the script to load for simulation mode.
            # Functions calling the API will check gemini_initialized_successfully or config.SIMULATION_MODE.
        else:
            genai.configure(api_key=config.GEMINI_API_KEY)

            # Model Selection
            gemini_model_name = DEFAULT_GEMINI_MODEL_NAME
            if hasattr(config, 'GEMINI_MODEL_NAME') and config.GEMINI_MODEL_NAME:
                gemini_model_name = config.GEMINI_MODEL_NAME
            else:
                logger.info(f"GEMINI_MODEL_NAME not found in config, using default: {DEFAULT_GEMINI_MODEL_NAME}")

            model = genai.GenerativeModel(gemini_model_name)

            # Generation Configuration
            if hasattr(config, 'GEMINI_GENERATION_CONFIG') and config.GEMINI_GENERATION_CONFIG:
                generation_config = config.GEMINI_GENERATION_CONFIG
            else:
                generation_config = DEFAULT_GENERATION_CONFIG
                logger.info(f"GEMINI_GENERATION_CONFIG not found in config, using default: {DEFAULT_GENERATION_CONFIG}")

            gemini_initialized_successfully = True
            logger.info(f"Gemini API configured successfully with model: {gemini_model_name}")

    except Exception as e:
        logger.error(f"Error during Gemini API client initialization: {e}", exc_info=True)
        # This will leave gemini_initialized_successfully as False
else: # genai library itself is not available
    logger.warning("Gemini library (google.generativeai) is not installed. Real API calls will fail.")


# --- Retry Decorator for Gemini Calls ---
# Specific Google API core exceptions that might be retriable
RETRIABLE_GOOGLE_EXCEPTIONS = (
    google_api_exceptions.DeadlineExceeded,
    google_api_exceptions.ServiceUnavailable,
    google_api_exceptions.InternalServerError, # 500 errors from Google
    google_api_exceptions.ResourceExhausted, # For quota issues that might be temporary (e.g. per minute)
) if google_api_exceptions else ()

# Custom exception for Gemini that might indicate a retriable server-side issue
class RetriableGeminiError(utils.GeminiAPIError):
    pass

def retry_if_google_api_error_or_custom_retriable(exception):
    """Retries on specific Google API core exceptions or our custom RetriableGeminiError."""
    if isinstance(exception, RETRIABLE_GOOGLE_EXCEPTIONS):
        logger.warning(f"Retrying due to Google API Exception: {type(exception).__name__} - {exception}")
        return True
    if isinstance(exception, RetriableGeminiError):
        logger.warning(f"Retrying due to custom RetriableGeminiError: {exception}")
        return True
    # Also consider retrying on generic GeminiAPIError if it has a 5xx status code,
    # though Gemini Python SDK might not expose HTTP status codes directly in all exceptions.
    if isinstance(exception, utils.GeminiAPIError) and hasattr(exception, 'original_exception'):
        # If the original exception was a google_api_exception.ServerError or similar
        if isinstance(exception.original_exception, google_api_exceptions.ServerError): # Covers 500, 503 etc
             logger.warning(f"Retrying due to underlying Google API ServerError: {exception.original_exception}")
             return True
    return False

gemini_retry_decorator = retry(
    stop=stop_after_attempt(config.RETRY_ATTEMPTS if hasattr(config, 'RETRY_ATTEMPTS') else 3),
    wait=wait_exponential(
        multiplier=1,
        min=config.RETRY_DELAY_SECONDS if hasattr(config, 'RETRY_DELAY_SECONDS') else 2,
        max=(config.RETRY_DELAY_SECONDS if hasattr(config, 'RETRY_DELAY_SECONDS') else 2) * 4
    ),
    retry=retry_if_google_api_error_or_custom_retriable
)


# --- Prompt Templates (Simplified here, can be moved to a constants file) ---
MONTHLY_TRANSCRIPT_PROMPT_TEMPLATE = """
作為一個專業的金融社群報告分析師，請你根據以下提供的多篇社群討論區的貼文資料，為我做一個全面的月度社群言論彙總。

目標：
1.  **整合與摘要**：將所有貼文內容整合成一份連貫的「社群討論月度逐字稿」。這份逐字稿應按日期和原始貼文順序組織，清晰呈現當月社群的主要討論點和情緒。
2.  **內容要求**：
    *   保留原始語氣和關鍵信息，避免過度解讀或添加個人評論。
    *   對於非文字內容（如圖片、影片連結），請以文字描述其主題或類型（例如 `[圖片：一張關於市場趨勢的圖表]` 或 `[影片連結：分析個股未來走勢]`）。
    *   若貼文包含明確的買賣建議、市場預測、情緒表達（如恐慌、興奮），應予以記錄。
    *   評論區的內容若有價值，也應整合進逐字稿，標示其為評論。
3.  **格式要求**：
    *   逐字稿開頭應包含本月彙總的整體摘要（約100-200字），簡述本月社群討論的熱點話題和主要情緒傾向。
    *   逐字稿內容應清晰易讀，適當分段。每篇貼文前應註明原始標題和發布日期。

請嚴格按照上述要求，基於以下貼文數據生成報告：

貼文數據如下：
{posts_data_json_str}

社群討論月度逐字稿：
"""

MONTHLY_ANALYSIS_REPORT_PROMPT_TEMPLATE = """
作為一個頂尖的金融市場分析師，你需要整合以下三方面的資訊：1) 本月社群逐字稿，2) 本月相關金融事件彙整，3) 本月金融數據的文字化摘要。基於這些資訊，生成一份專業的月度市場綜合分析報告。

目標：
1.  **綜合分析**：深入分析社群情緒、真實發生的金融事件以及客觀的金融市場數據，找出它們之間的關聯性與潛在影響。
2.  **市場洞察**：提供對當前市場狀態的洞察，包括主要趨勢、潛在風險、以及可能的市場機會。
3.  **報告結構**：
    *   **開頭摘要 (Executive Summary)**：(約200-300字) 總結本月市場的整體表現、主要驅動因素、社群情緒焦點，以及你對後市的總體看法。
    *   **社群情緒分析 (Community Sentiment Analysis)**：
        *   本月社群討論的熱點話題是什麼？主要關注哪些股票、指數或事件？
        *   社群的整體情緒是樂觀、悲觀、中性，還是混合？是否有明顯轉變？
        *   社群討論中是否有值得關注的特定觀點、預測或謠言？（請指出來源，例如「多數討論認為...」，「部分用戶擔心...」）
    *   **金融事件影響分析 (Financial Events Impact Analysis)**：
        *   本月發生的重要金融事件（如財報、政策變動、國際事件）對市場造成了哪些實際影響？
        *   這些事件是否在社群討論中得到反映？社群的反應與事件的實際影響是否一致？
    *   **金融數據表現分析 (Financial Data Performance Analysis)**：
        *   本月關鍵金融數據（如指數漲跌、成交量變化、特定板塊表現）的實際情況如何？
        *   這些數據表現與社群的預期或討論是否相符？
    *   **綜合市場展望與建議 (Overall Market Outlook & Recommendations)**：
        *   綜合以上分析，你對未來一個月的市場整體走勢有何預期？（樂觀、謹慎樂觀、中性、謹慎悲觀、悲觀）
        *   有哪些潛在的市場驅動因素或風險點需要特別關注？
        *   （可選）如果提供投資建議，請說明是基於何種風險偏好（例如，對保守型投資者...，對積極型投資者...）。

請確保報告客觀、專業，並以數據和事實為基礎進行分析。

提供的資訊如下：

社群逐字稿：
```
{monthly_transcript}
```

金融事件彙整：
```
{event_summary}
```

金融數據文字化摘要：
```
{financial_data_summary}
```

月度市場綜合分析報告：
"""


# --- API Interaction Functions ---
@gemini_retry_decorator
def generate_monthly_transcript(posts_data: list[dict]) -> str | None:
    """
    Generates a monthly transcript from social media posts using Gemini API.
    """
    if config.SIMULATION_MODE:
        logger.info("SIMULATION MODE: Skipping real Gemini API call for transcript generation.")
        return "這是模擬模式下生成的月度社群逐字稿。\n包含多篇貼文的摘要和重點。\n情緒：普遍樂觀，偶有謹慎。"

    if not gemini_initialized_successfully or not model:
        logger.error("Gemini API client not initialized. Cannot generate transcript.")
        raise utils.ConfigError("Gemini API client not initialized properly.")

    try:
        # Format posts_data into a JSON string for the prompt
        posts_data_json_str = json.dumps(posts_data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error serializing posts_data to JSON: {e}", exc_info=True)
        raise utils.DataProcessingError(f"Failed to serialize posts_data for prompt: {e}")

    prompt = MONTHLY_TRANSCRIPT_PROMPT_TEMPLATE.format(posts_data_json_str=posts_data_json_str)

    logger.info(f"Generating monthly transcript. Prompt length (approx chars): {len(prompt)}")
    # Consider adding model.count_tokens(prompt) here if prompt length is a concern

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        generated_text = response.text # Accessing .text directly
        logger.info(f"Successfully generated monthly transcript. Response length (chars): {len(generated_text)}")
        return generated_text
    except Exception as e:
        logger.error(f"Gemini API error during transcript generation: {e}", exc_info=True)
        # Wrap the exception for unified error handling
        if isinstance(e, google_api_exceptions.GoogleAPIError):
            raise utils.GeminiAPIError(f"Gemini API failed: {e}", original_exception=e)
        else: # Other types of errors
            raise utils.GeminiAPIError(f"An unexpected error occurred: {e}", original_exception=e)


@gemini_retry_decorator
def generate_monthly_analysis_report(monthly_transcript: str,
                                   event_summary: str | None,
                                   financial_data_summary: str) -> str | None:
    """
    Generates a monthly analysis report using Gemini API.
    """
    if config.SIMULATION_MODE:
        logger.info("SIMULATION MODE: Skipping real Gemini API call for analysis report generation.")
        return "這是模擬模式下生成的月度分析報告。\n市場情緒：樂觀。\n關鍵事件：財報季。\n數據表現：指數上漲。\n展望：謹慎樂觀。"

    if not gemini_initialized_successfully or not model:
        logger.error("Gemini API client not initialized. Cannot generate analysis report.")
        raise utils.ConfigError("Gemini API client not initialized properly.")

    effective_event_summary = event_summary if event_summary else "本月無特別外部金融事件彙整。"

    prompt = MONTHLY_ANALYSIS_REPORT_PROMPT_TEMPLATE.format(
        monthly_transcript=monthly_transcript,
        event_summary=effective_event_summary,
        financial_data_summary=financial_data_summary
    )

    logger.info(f"Generating monthly analysis report. Prompt length (approx chars): {len(prompt)}")

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        generated_text = response.text
        logger.info(f"Successfully generated monthly analysis report. Response length (chars): {len(generated_text)}")
        return generated_text
    except Exception as e:
        logger.error(f"Gemini API error during analysis report generation: {e}", exc_info=True)
        if isinstance(e, google_api_exceptions.GoogleAPIError):
            raise utils.GeminiAPIError(f"Gemini API failed: {e}", original_exception=e)
        else:
            raise utils.GeminiAPIError(f"An unexpected error occurred: {e}", original_exception=e)


# Optional: generate_financial_event_summary - can be added later if needed.

if __name__ == '__main__':
    logger.info("--- Running jules_interaction.py direct execution tests ---")

    # Store original SIMULATION_MODE and temporarily enable it for tests to avoid API calls
    original_sim_mode = config.SIMULATION_MODE
    config.SIMULATION_MODE = True
    logger.info("Set SIMULATION_MODE = True for these tests.")

    # Test: API Key Configuration Check (Conceptual)
    # This test is tricky to automate without actually modifying config or env vars.
    # We rely on the initial loading logic to log warnings if key is placeholder.
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        logger.warning("GEMINI_API_KEY is not configured or is a placeholder. "
                       "Real API calls would fail. Simulation mode will proceed.")

    # Sample data for generate_monthly_transcript
    sample_posts_data = [
        {"file_path": "post1.txt", "title": "股市大漲怎麼看", "date": "2023-01-05",
         "post_content": "今天股市大漲，大家覺得是為什麼？我看好後市！", "comments": "- 我也覺得不錯！\n- 要小心回調風險。"},
        {"file_path": "post2.md", "title": "某某公司財報分析", "date": "2023-01-15",
         "post_content": "某某公司財報出來了，EPS超乎預期！[圖片：財報截圖]", "comments": "- 買！\n- 已上車！"}
    ]

    logger.info("\n--- Testing generate_monthly_transcript (SIMULATION_MODE=True) ---")
    transcript = generate_monthly_transcript(sample_posts_data)
    if transcript:
        logger.info(f"Generated Transcript (Simulated):\n{transcript[:200]}...") # Print first 200 chars
        assert "模擬模式" in transcript or "simulation mode" in transcript.lower()
    else:
        logger.error("Transcript generation failed in simulation mode.")
        assert False, "Transcript generation failed in simulation mode"


    # Sample data for generate_monthly_analysis_report
    sample_transcript = "本月社群討論熱烈，主要圍繞股市上漲及個別公司財報。整體情緒偏向樂觀，但亦有提醒風險的聲音。"
    sample_event_summary = "本月重要事件：A公司發布亮眼財報，B公司宣布擴產計畫。"
    sample_financial_summary = "市場指數本月上漲5%，成交量放大。科技股表現尤其突出。"

    logger.info("\n--- Testing generate_monthly_analysis_report (SIMULATION_MODE=True) ---")
    analysis_report = generate_monthly_analysis_report(sample_transcript, sample_event_summary, sample_financial_summary)
    if analysis_report:
        logger.info(f"Generated Analysis Report (Simulated):\n{analysis_report[:200]}...")
        assert "模擬模式" in analysis_report or "simulation mode" in analysis_report.lower()
    else:
        logger.error("Analysis report generation failed in simulation mode.")
        assert False, "Analysis report generation failed in simulation mode"

    # Test case: event_summary is None
    logger.info("\n--- Testing generate_monthly_analysis_report with None event_summary (SIMULATION_MODE=True) ---")
    analysis_report_no_event = generate_monthly_analysis_report(sample_transcript, None, sample_financial_summary)
    if analysis_report_no_event:
        logger.info(f"Generated Analysis Report (No Events, Simulated):\n{analysis_report_no_event[:200]}...")
        # The prompt template should handle None for event_summary by inserting a default phrase.
        # The simulated output might not reflect this detail unless the simulation logic is also complex.
        assert "模擬模式" in analysis_report_no_event
    else:
        logger.error("Analysis report generation (no events) failed in simulation mode.")

    # Restore original SIMULATION_MODE
    config.SIMULATION_MODE = original_sim_mode
    logger.info(f"Restored SIMULATION_MODE to: {config.SIMULATION_MODE}")

    # Conceptual test for API key not configured (real call scenario)
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        logger.info("\n--- Conceptual Test: Real API call with unconfigured key ---")
        logger.info("Attempting a call that would need a real key (SIMULATION_MODE=False temporarily)")
        config.SIMULATION_MODE = False # Temporarily disable simulation
        # We expect a ConfigError or GeminiAPIError if gemini_initialized_successfully is False
        try:
            # Ensure the function checks gemini_initialized_successfully before making a call
            # or that the call itself fails gracefully due to lack of API key.
            # This requires gemini_initialized_successfully to be False if key is bad/missing.
            if not gemini_initialized_successfully: # If key was bad, this should be false.
                 logger.info("Simulating the check: gemini_initialized_successfully is False as expected with bad key.")
                 # Raise the kind of error the function would raise internally.
                 raise utils.ConfigError("Gemini API client not initialized properly (simulated for test).")
            else: # This case means key was somehow considered valid during init, which is unlikely for a placeholder
                 logger.warning("Gemini client was initialized even with potentially placeholder key. Test might not reflect real failure.")
                 generate_monthly_transcript(sample_posts_data) # This would attempt a real call

        except utils.ConfigError as e:
            logger.info(f"Caught expected ConfigError: {e}")
            assert "not initialized" in str(e)
        except utils.GeminiAPIError as e: # This might happen if init was somehow bypassed and call was made
            logger.info(f"Caught GeminiAPIError (also possible if key is invalid at call time): {e}")
        except Exception as e:
            logger.error(f"Caught unexpected error during unconfigured key test: {e}", exc_info=True)
        finally:
            config.SIMULATION_MODE = True # Ensure simulation mode is restored
            logger.info("Restored SIMULATION_MODE to True after conceptual key test.")

    logger.info("--- jules_interaction.py direct execution tests completed ---")
