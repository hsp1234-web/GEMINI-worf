import os
import re
from datetime import datetime
import logging # Keep for type hinting if needed

from src import utils

# Initialize logger
logger = utils.setup_logger(__name__)

# --- Helper function for date parsing ---
def _parse_date(date_str: str) -> str | None:
    """
    Tries to parse a date string using common formats.
    Returns date as YYYY-MM-DD string or None if parsing fails.
    """
    if not date_str:
        return None

    # Extended list of common date formats
    common_formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d",
        "%m/%d/%Y", # US format, handle with care for ambiguity
        "%d/%m/%Y", # European format
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%Y. %m. %d.", "%Y. %m. %d",
        # Add formats that might appear in filenames or less structured metadata
        "%Y%m%d%H%M%S"
    ]

    # Attempt to extract date from potentially longer strings
    # Regex to find date-like patterns, can be refined
    # This example looks for YYYY-MM-DD or YYYYMMDD like patterns
    match = re.search(r'(\d{4}[-/]?\d{2}[-/]?\d{2})', date_str)
    if not match:
        match = re.search(r'(\d{8})', date_str) # For YYYYMMDD

    parsed_dt = None

    if match:
        potential_date_part = match.group(1)
        for fmt in common_formats:
            try:
                # Try parsing the extracted part first
                parsed_dt = datetime.strptime(potential_date_part, fmt)
                break
            except ValueError:
                continue

    # If no match from regex or regex parsing failed, try parsing the whole string
    if not parsed_dt:
        for fmt in common_formats:
            try:
                parsed_dt = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                continue

    if parsed_dt:
        return parsed_dt.strftime("%Y-%m-%d")
    else:
        logger.warning(f"Failed to parse date string: '{date_str}' with known formats.")
        return None


# --- Main Parsing Function ---
def parse_post_file(file_path: str) -> dict | None:
    """
    Parses a single community post file (text or markdown).

    Args:
        file_path: Path to the post file.

    Returns:
        A dictionary with parsed data {"file_path", "title", "date", "post_content", "comments"}
        or None if essential parts are missing or file cannot be read.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise utils.FileIOError(f"File not found: {file_path}")
    except IOError as e:
        logger.error(f"IOError reading file {file_path}: {e}")
        raise utils.FileIOError(f"IOError reading file {file_path}: {e}")

    title = None
    date_str_from_content = None # Date string found in content

    post_content_lines = []
    comments_lines = []

    # Regex for metadata
    # Allow variations in spacing and colon types (full-width/half-width)
    title_regex = re.compile(r"^(?:title|標題)\s*[:：]\s*(.+)", re.IGNORECASE)
    date_regex = re.compile(r"^(?:date|日期)\s*[:：]\s*(.+)", re.IGNORECASE)
    comments_marker_regex = re.compile(r"^(?:comments|留言)\s*[:：]\s*(.*)?", re.IGNORECASE)

    parsing_stage = "metadata" # metadata, content, comments

    # Try to get date from filename (simple pattern: YYYY-MM-DD or YYYYMMDD in filename)
    # This is a basic attempt and might need refinement.
    filename_date_str = None
    filename_match_iso = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(file_path))
    if filename_match_iso:
        filename_date_str = filename_match_iso.group(1)
    else:
        filename_match_basic = re.search(r"(\d{8})", os.path.basename(file_path))
        if filename_match_basic:
            filename_date_str = filename_match_basic.group(1)

    parsed_date_from_filename = _parse_date(filename_date_str) if filename_date_str else None


    for i, line_text in enumerate(lines):
        line = line_text.strip()

        if parsing_stage == "metadata":
            title_match = title_regex.match(line)
            if title_match:
                title = title_match.group(1).strip()
                continue

            date_match = date_regex.match(line)
            if date_match:
                date_str_from_content = date_match.group(1).strip()
                continue

            # If a line is '---' and it's early, could be a separator.
            # We are not strictly enforcing metadata blocks, so this is mostly ignored for now.
            # If we've checked a few lines for metadata and haven't found a comments marker,
            # switch to content. This threshold can be adjusted.
            if line == "---" and i < 5: # Arbitrary: separator in first 5 lines
                continue

            # Heuristic: if it's not metadata and not a comments marker, it's content.
            # Or, if we've scanned a few lines (e.g., 5) without finding metadata, assume content starts.
            # This part is tricky. A simpler rule: if it's not a comment marker, and we are past initial metadata lines.

            comments_match = comments_marker_regex.match(line)
            if comments_match:
                parsing_stage = "comments"
                # The text after "comments:" on the same line could be a comment or "無"
                first_comment_part = comments_match.group(1).strip()
                if first_comment_part and first_comment_part.lower() not in ["無", "none", ""]:
                    comments_lines.append(first_comment_part)
                continue # Move to next line for more comments

            # If no metadata found on this line, and not a comment marker, it's content
            # This means metadata must appear before any main content if using these markers.
            # For files without markers, all lines will initially be treated as content.
            post_content_lines.append(line_text) # Keep original line ending for now
            parsing_stage = "content" # Switch to content stage

        elif parsing_stage == "content":
            comments_match = comments_marker_regex.match(line)
            if comments_match:
                parsing_stage = "comments"
                first_comment_part = comments_match.group(1).strip()
                if first_comment_part and first_comment_part.lower() not in ["無", "none", ""]:
                    comments_lines.append(first_comment_part)
            else:
                post_content_lines.append(line_text) # Keep original line ending

        elif parsing_stage == "comments":
            comments_lines.append(line_text) # Keep original line ending

    # Post-processing
    parsed_date_from_content = _parse_date(date_str_from_content) if date_str_from_content else None

    final_parsed_date = parsed_date_from_content or parsed_date_from_filename # Content date takes precedence

    if not final_parsed_date:
        logger.warning(f"Could not determine date for file: {file_path}. Tried content and filename.")

    if not title:
        # Basic title extraction from filename if not found in content (remove date and extension)
        base_name = os.path.basename(file_path)
        name_part = os.path.splitext(base_name)[0]
        if parsed_date_from_filename: # Remove date part if it was used for filename parsing
            name_part = name_part.replace(filename_date_str, "", 1) # Remove only first occurrence
        title = name_part.replace("_", " ").strip() # Replace underscores, strip
        if not title: title = "[無標題]"
        logger.info(f"Title not found in content for {file_path}, derived from filename: '{title}'")

    final_post_content = "".join(post_content_lines).strip()

    # Join comment lines, then strip. If result is "無" or empty, set to empty string.
    raw_comments_text = "".join(comments_lines).strip()
    if raw_comments_text.lower() in ["無", "none"]:
        final_comments = ""
    else:
        final_comments = raw_comments_text

    # Basic validation: require post content and a date. Title can be default.
    if not final_post_content:
        logger.warning(f"No post content found for file: {file_path}. Skipping file.")
        return None
    if not final_parsed_date:
        logger.warning(f"No valid date found for file: {file_path} after checking content and filename. Skipping file.")
        return None


    return {
        "file_path": file_path,
        "title": title,
        "date": final_parsed_date, # YYYY-MM-DD string or None
        "post_content": final_post_content,
        "comments": final_comments
    }

# --- Directory Parsing Function ---
def parse_posts_from_directory(directory_path: str) -> list[dict]:
    """
    Parses all .md and .txt post files in a given directory.

    Args:
        directory_path: Path to the directory containing post files.

    Returns:
        A list of dictionaries, where each dictionary is the result of parse_post_file().
    """
    parsed_posts = []
    if not os.path.isdir(directory_path):
        logger.error(f"Directory not found: {directory_path}")
        raise utils.FileIOError(f"Directory not found: {directory_path}")

    logger.info(f"Starting to parse posts from directory: {directory_path}")
    for filename in os.listdir(directory_path):
        if filename.endswith((".md", ".txt")):
            file_path = os.path.join(directory_path, filename)
            try:
                logger.debug(f"Attempting to parse file: {file_path}")
                parsed_data = parse_post_file(file_path)
                if parsed_data:
                    parsed_posts.append(parsed_data)
                    logger.info(f"Successfully parsed file: {filename}")
                else:
                    logger.warning(f"Skipped file (parse_post_file returned None): {filename}")
            except utils.FileIOError as e: # Catch errors from parse_post_file's file reading
                logger.error(f"FileIOError while processing {filename}: {e}")
            except Exception as e: # Catch any other unexpected errors during parsing a single file
                logger.error(f"Unexpected error parsing file {filename}: {e}", exc_info=True)
        else:
            logger.debug(f"Skipping non-matching file: {filename}")

    logger.info(f"Finished parsing directory. Found {len(parsed_posts)} valid posts.")
    return parsed_posts


if __name__ == '__main__':
    # --- Test Section ---
    # Create dummy files and directory for testing based on examples

    # Ensure a base directory for tests exists (e.g., in relation to this script)
    # For a real test suite, this would be more robust (e.g., using tempfile module)
    test_dir_name = "test_posts_data"
    # Assuming this script is in src/, create test_posts_data at project root/test_posts_data
    project_root = os.path.dirname(os.path.abspath(__file__)) # src
    project_root = os.path.dirname(project_root) # project root
    test_dir_path = os.path.join(project_root, test_dir_name)

    if not os.path.exists(test_dir_path):
        os.makedirs(test_dir_path)
        logger.info(f"Created test directory: {test_dir_path}")

    # Test file contents
    example1_content = """title: 亮哥分享
date: 2024-12-09
昨天甲狼股友分享一檔股票代號，我看了之後覺得不錯，今天開盤買進。
他的基本面、技術面、籌碼面都很好，而且還有一些利多消息。
我認為這檔股票有機會上漲到100元，甚至更高。
因此會考慮出場。
comments:
"""
    example2_content = """---
title: 閱讀能力很重要
date: 2025-02-01
---
#善甲狼a機智生活
今天看到一張圖，差點笑死我。
這張圖是在講說，如果你看不懂這張圖，
那你可能要加強你的閱讀能力。
#閱讀能力很重要
comments:
- xoilmk017888: 你的雙眼....
  天啊，這張圖已經超越人類的理解能力啦
  XDD
  這張圖有2500多個讚
  留言又怕
  講話都變慢
  沒法講
  怎麼
- apital_designs3jp: GOOGLE大神快來解說解釋。哈
- ry3068306: 以被打臉，哭死ㄌ傻全款。傻全車
- 張秀琴: 留言區..
- 吳立萍 Austin: 這次是一張... 😂😭
"""
    example3_content = """標題: 加州大火先機
日期: 2025-01-12
文章內容:
關於這次的加州大火，其實可以看到一些先機。
例如，相關的防火、救災概念股，股價都有上漲。
另外，災後重建的需求，也會帶動相關產業的發展。
| 公司名稱 | 股票代號 | 備註 |
|---|---|---|
| ABC公司 | 1234 | 防火材料 |
| XYZ公司 | 5678 | 救災設備 |
![image](https://example.com/fire.jpg)
#天佑加州
留言: 無
"""
    example4_content_no_meta_date_in_filename = """
This is a post with no explicit metadata.
The content starts directly.
We expect the date to be parsed from the filename.
And title to be derived from filename.
"""
    example5_content_only_content = """
Just content here. No metadata, no comments section.
"""


    # Create dummy files
    files_to_create = {
        "FB亮哥分享_2024-12-09.txt": example1_content,
        "FB閱讀能力很重要_2025-02-01.txt": example2_content,
        "FB加州大火先機_2025-01-12.md": example3_content,
        "Post With Date 20230101 In Name.txt": example4_content_no_meta_date_in_filename,
        "Just_Content_File_2023-03-15.md": example5_content_only_content,
        "NoDateInFilenameOrContent.txt": "Content but no date.",
        "EmptyFile.txt": ""
    }

    for filename, content in files_to_create.items():
        file_path = os.path.join(test_dir_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created test file: {file_path}")

    logger.info(f"--- Testing _parse_date ---")
    assert _parse_date("2023-10-05") == "2023-10-05"
    assert _parse_date("2023/10/05") == "2023-10-05"
    assert _parse_date("20231005") == "2023-10-05"
    assert _parse_date("10/05/2023") == "2023-10-05" # Ambiguous but common
    assert _parse_date("Date: 2023-10-05") == "2023-10-05" # Extracts from string
    assert _parse_date("File_20231005_data.txt") == "2023-10-05"
    assert _parse_date("Invalid Date String") is None
    assert _parse_date("") is None
    logger.info("_parse_date tests passed.")

    logger.info(f"--- Testing parse_post_file for Example 1 ---")
    parsed1 = parse_post_file(os.path.join(test_dir_path, "FB亮哥分享_2024-12-09.txt"))
    if parsed1:
        assert parsed1["title"] == "亮哥分享"
        assert parsed1["date"] == "2024-12-09"
        assert "昨天甲狼股友分享一檔股票代號" in parsed1["post_content"]
        assert parsed1["comments"] == "" # comments: followed by nothing
        logger.info("Example 1 parsed as expected.")
    else:
        logger.error("Example 1 parsing failed.")

    logger.info(f"--- Testing parse_post_file for Example 2 ---")
    parsed2 = parse_post_file(os.path.join(test_dir_path, "FB閱讀能力很重要_2025-02-01.txt"))
    if parsed2:
        assert parsed2["title"] == "閱讀能力很重要"
        assert parsed2["date"] == "2025-02-01"
        assert "#善甲狼a機智生活" in parsed2["post_content"]
        assert "- xoilmk017888: 你的雙眼...." in parsed2["comments"]
        assert "吳立萍 Austin: 這次是一張... 😂😭" in parsed2["comments"]
        logger.info("Example 2 parsed as expected.")
    else:
        logger.error("Example 2 parsing failed.")

    logger.info(f"--- Testing parse_post_file for Example 3 ---")
    parsed3 = parse_post_file(os.path.join(test_dir_path, "FB加州大火先機_2025-01-12.md"))
    if parsed3:
        assert parsed3["title"] == "加州大火先機"
        assert parsed3["date"] == "2025-01-12"
        assert "關於這次的加州大火" in parsed3["post_content"]
        assert "| ABC公司 | 1234 |" in parsed3["post_content"] # Markdown table
        assert parsed3["comments"] == "" #留言: 無
        logger.info("Example 3 parsed as expected.")
    else:
        logger.error("Example 3 parsing failed.")

    logger.info(f"--- Testing parse_post_file for Example 4 (date from filename) ---")
    parsed4 = parse_post_file(os.path.join(test_dir_path, "Post With Date 20230101 In Name.txt"))
    if parsed4:
        assert parsed4["title"] == "Post With Date In Name" # Date part removed
        assert parsed4["date"] == "2023-01-01"
        assert "This is a post with no explicit metadata." in parsed4["post_content"]
        logger.info("Example 4 parsed as expected (date from filename).")
    else:
        logger.error("Example 4 parsing failed.")

    logger.info(f"--- Testing parse_post_file for Example 5 (only content, date from filename) ---")
    parsed5 = parse_post_file(os.path.join(test_dir_path, "Just_Content_File_2023-03-15.md"))
    if parsed5:
        assert parsed5["title"] == "Just Content File" # Date part removed and underscores to spaces
        assert parsed5["date"] == "2023-03-15"
        assert "Just content here." in parsed5["post_content"]
        assert parsed5["comments"] == ""
        logger.info("Example 5 parsed as expected.")
    else:
        logger.error("Example 5 parsing failed.")

    logger.info(f"--- Testing parse_post_file for No Date ---")
    parsed_no_date = parse_post_file(os.path.join(test_dir_path, "NoDateInFilenameOrContent.txt"))
    assert parsed_no_date is None, "File with no date should return None"
    logger.info("No Date file handled as expected (returned None).")

    logger.info(f"--- Testing parse_post_file for Empty File ---")
    parsed_empty = parse_post_file(os.path.join(test_dir_path, "EmptyFile.txt"))
    assert parsed_empty is None, "Empty file should return None"
    logger.info("Empty file handled as expected (returned None).")


    logger.info(f"--- Testing parse_posts_from_directory ---")
    all_parsed_posts = parse_posts_from_directory(test_dir_path)
    # Expected count: Ex1, Ex2, Ex3, Ex4, Ex5. "NoDate..." and "EmptyFile..." should be skipped.
    expected_successful_parses = 5
    assert len(all_parsed_posts) == expected_successful_parses, \
        f"Expected {expected_successful_parses} successfully parsed posts, got {len(all_parsed_posts)}"
    logger.info(f"parse_posts_from_directory returned {len(all_parsed_posts)} posts as expected.")

    # Optional: Clean up test directory and files
    # for filename in files_to_create:
    #     try:
    #         os.remove(os.path.join(test_dir_path, filename))
    #     except OSError:
    #         pass
    # try:
    #     os.rmdir(test_dir_path)
    #     logger.info(f"Cleaned up test directory: {test_dir_path}")
    # except OSError:
    #     logger.warning(f"Could not remove test directory {test_dir_path}. It might not be empty or lacks permissions.")

    logger.info("--- post_parser.py direct execution tests completed ---")
