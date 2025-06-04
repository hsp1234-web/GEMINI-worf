# coding: utf-8
"""
This script parses community posts from a text file, extracts relevant information,
and groups them by month.
"""
import re
import json
from datetime import datetime

def parse_post_date(date_str):
    """
    Parses a date string (YYYY-MM-DD or YYYY/MM/DD) into a datetime object.
    Handles potential errors during parsing.
    """
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    print(f"Warning: Could not parse date string: {date_str} with known formats.")
    return None

def extract_post_info(post_block):
    """
    Extracts title, date, content, and comments from a single post block.
    """
    lines = post_block.strip().split('\n')
    title = None
    date_obj = None
    post_content_list = []
    comments_list = []

    # Regex for date
    date_pattern_line = re.compile(r"^(?:Date:\s*)?(\d{4}[-/]\d{2}[-/]\d{2})", re.IGNORECASE)
    # Regex for separator line itself, to extract potential title part
    separator_title_pattern = re.compile(r"^=== 檔案 \d+/\d+:\s*(.*)", re.IGNORECASE)

    # Check first line for title (separator case)
    first_line_match = separator_title_pattern.match(lines[0])
    if first_line_match:
        title = first_line_match.group(1).strip()
        lines.pop(0) # Remove the separator line from further processing

    in_comments_section = False

    # Iterate through lines to find date, title (if not found yet), content, and comments
    for i, line in enumerate(lines):
        # Date extraction
        date_match = date_pattern_line.search(line)
        if date_match and not date_obj: #Only parse date if not already found
            date_str = date_match.group(1)
            date_obj = parse_post_date(date_str)

            # If title is not yet found from separator, try to get it from lines around date
            if not title:
                if "Date:" in line and len(line.split("Date:")) > 1 and line.split("Date:")[0].strip() : # Title on the same line before "Date:"
                     title_candidate = line.split("Date:")[0].strip()
                     if title_candidate and not separator_title_pattern.match(title_candidate) and title_candidate.lower() != "comments:":
                         title = title_candidate
                elif i > 0 and lines[i-1].strip() and not date_pattern_line.search(lines[i-1]): # Title on the line above date
                    title_candidate = lines[i-1].strip()
                    if title_candidate and not separator_title_pattern.match(title_candidate) and title_candidate.lower() != "comments:":
                        title = title_candidate
                        # remove from content list if it was added prematurely
                        if title_candidate in post_content_list:
                            post_content_list.remove(title_candidate)

            # Avoid adding the date line itself to content if it also contained the title
            if title and title in line:
                line_content_after_title_and_date = line.replace(title, "").replace(f"Date: {date_str}", "").replace(date_str, "").strip()
                if line_content_after_title_and_date:
                    post_content_list.append(line_content_after_title_and_date)
                continue # Move to next line
            elif date_match.group(0) == line.strip(): # If the whole line is just the date
                continue


        if line.strip().lower() == "comments:":
            in_comments_section = True
            # remove "Comments:" line if it was added to content
            if line.strip() in post_content_list:
                post_content_list.remove(line.strip())
            continue

        if in_comments_section:
            comments_list.append(line)
        else:
            # Add to content, but avoid adding lines that might be title if title is not yet found
            if title or (not title and i > 0): # Add if title is found, or if it's not the very first line (potential title)
                 post_content_list.append(line)


    # If title still not found (e.g. for "---" separator cases)
    if not title and lines:
        # Try to take the first non-empty, non-date line as title
        for line_idx, line_content in enumerate(lines):
            line_stripped = line_content.strip()
            if line_stripped and not date_pattern_line.search(line_stripped) and line_stripped.lower() != "comments:":
                title = line_stripped
                # If this title was added to post_content_list, remove it
                if title in post_content_list:
                    post_content_list.remove(title)
                # If date is on the next line, this is a good candidate for title
                if (line_idx + 1 < len(lines)) and date_pattern_line.search(lines[line_idx+1]):
                     pass # Good title
                # If date was on the same line as this auto-title (less likely due to previous checks)
                elif date_pattern_line.search(title):
                     title = title.split(date_pattern_line.search(title).group(1))[0].strip() # take part before date

                break # Found a candidate for title

    # Consolidate post content
    post_content = "\n".join(post_content_list).strip()
    # Clean title: if content starts with title, remove title from content
    if title and post_content.startswith(title):
        post_content = post_content[len(title):].lstrip()

    return {
        "title": title,
        "date": date_obj.strftime("%Y-%m-%d") if date_obj else None,
        "post_content": post_content,
        "comments": "\n".join(comments_list).strip()
    }

def parse_posts_from_file(filepath):
    """
    Reads a file and parses all posts, grouping them by month.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return {}
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return {}

    # Regex to find separators "=== 檔案 x/y: ..." or "---"
    # This regex will find the start of each post.
    post_start_pattern = re.compile(r"(?:^=== 檔案 \d+/\d+:.*?$|^---$)", re.MULTILINE)

    posts_data = []
    # Find all start positions of separators
    separator_positions = [match.start() for match in post_start_pattern.finditer(content)]

    # If no separators found, treat the whole content as a single post (or handle as error)
    if not separator_positions:
        if content.strip(): # If there's any content
            posts_data.append(extract_post_info(content))
            # print("Warning: No post separators found. Treating entire file as a single post.")
        else:
            print("Warning: No post separators found and file is empty or whitespace only.")
            return {}
    else:
        # Create post blocks based on separator positions
        for i in range(len(separator_positions)):
            start_pos = separator_positions[i]
            end_pos = separator_positions[i+1] if i + 1 < len(separator_positions) else len(content)
            post_block = content[start_pos:end_pos].strip()
            if post_block:
                posts_data.append(extract_post_info(post_block))

    monthly_posts = {}
    for post_info in posts_data:
        if post_info.get("date"):
            try:
                # Date is already string "YYYY-MM-DD" from extract_post_info
                date_str = post_info["date"]
                # Re-parse to datetime object for month_year_key, though already validated in parse_post_date
                date_obj_for_grouping = datetime.strptime(date_str, "%Y-%m-%d")
                month_year_key = date_obj_for_grouping.strftime("%Y-%m")

                if month_year_key not in monthly_posts:
                    monthly_posts[month_year_key] = []
                monthly_posts[month_year_key].append(post_info)
            except ValueError as e: # Should ideally not happen if parse_post_date is robust
                print(f"Warning: Date '{post_info.get('date')}' for post titled '{post_info.get('title')}' caused an error during grouping. Error: {e}")
        else:
            print(f"Warning: Post titled '{post_info.get('title')}' is missing a valid date. Skipping grouping for this post.")

    return monthly_posts

def save_to_json(data, output_filepath):
    """
    Saves the given data to a JSON file.
    """
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved data to {output_filepath}")
    except Exception as e:
        print(f"Error saving data to JSON file {output_filepath}: {e}")

if __name__ == "__main__":
    # Define a test input filepath
    test_input_filename = "test_posts.md" # This will be created in the root of the repo
    output_filename = "monthly_posts_raw.json" # This will also be in the root

    # Create a dummy test_posts.md file for testing
    test_content = """=== 檔案 1/3: Post One Title
Date: 2023-01-15
This is the content of the first post.
It has multiple lines.

Comments:
UserA: Great post!
UserB: Thanks for sharing.

=== 檔案 2/3: Another Post
Date: 2023-01-20
Content for the second post.
No comments here.
---
Post Three Title (Alternative Separator and Date format)
2023/02/10
This is post three.
A bit different.
"""
    try:
        with open(test_input_filename, 'w', encoding='utf-8') as f:
            f.write(test_content)
        print(f"Created/Overwrote dummy file: {test_input_filename}")
    except IOError as e:
        print(f"Error creating dummy test file {test_input_filename}: {e}")
        # exit() # Exit if we can't create the test file

    # Parse the posts
    parsed_data = parse_posts_from_file(test_input_filename)

    if parsed_data:
        # Save the parsed data to JSON
        save_to_json(parsed_data, output_filename)

        # Optional: Print the parsed data to console for verification
        # print("\nParsed Data:")
        # print(json.dumps(parsed_data, ensure_ascii=False, indent=4))
    else:
        print("No data was parsed or an error occurred.")

    # Clean up the dummy file (optional, but good for testing)
    # import os
    # try:
    #     os.remove(test_input_filename)
    #     print(f"Cleaned up dummy file: {test_input_filename}")
    # except OSError as e:
    #     print(f"Error removing dummy test file {test_input_filename}: {e}")

print("post_parser.py loaded and potentially executed main block if run directly.")
