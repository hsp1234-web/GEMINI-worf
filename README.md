# Project Title (To be filled)

## 中文說明

### 1. Colab 首次設定與檔案上傳
這是在 Colab 中首次設定專案的步驟。它將指導您上傳包含專案文件的 ZIP 檔案。

```python
# 匯入必要的庫
# Import necessary libraries
from google.colab import files
import zipfile
import os

# 定義解壓縮 ZIP 檔案並執行後續步驟的函數
# Define a function to unzip the file and perform subsequent steps
def unzip_and_proceed():
    zip_file_name = '/content/uploaded_project.zip'  # 指定 ZIP 檔案的名稱 (Specify the name of the ZIP file)
    extract_path = '/content/extracted_code'  # 指定解壓縮的目標路徑 (Specify the target path for extraction)

    # 確保解壓縮路徑存在
    # Ensure the extraction path exists
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)
        print(f"Created directory: {extract_path} (已建立目錄：{extract_path})")

    try:
        # 解壓縮 ZIP 檔案
        # Unzip the ZIP file
        with zipfile.ZipFile(zip_file_name, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"Successfully unzipped '{zip_file_name}' to '{extract_path}' (成功將 '{zip_file_name}' 解壓縮到 '{extract_path}')")
        # 在這裡可以添加解壓縮成功後的其他操作，例如列出解壓縮的檔案
        # You can add other operations here after successful unzipping, e.g., listing the extracted files
        print(f"Files extracted to: {os.listdir(extract_path)} (檔案解壓縮至：{os.listdir(extract_path)})")
    except zipfile.BadZipFile:
        print(f"Error: The uploaded file is not a valid ZIP file or is corrupted. (錯誤：上傳的檔案不是有效的 ZIP 檔案或已損壞。)")
    except FileNotFoundError:
        print(f"Error: The ZIP file was not found at '{zip_file_name}'. Please ensure a ZIP file was uploaded. (錯誤：在 '{zip_file_name}'找不到 ZIP 檔案。請確保已上傳 ZIP 檔案。)")
    except Exception as e:
        print(f"An unexpected error occurred during unzipping: {e} (解壓縮過程中發生意外錯誤：{e})")

# 上傳檔案
# Upload files
print("Please upload your project ZIP file. (請上傳您的專案 ZIP 檔案。)")
uploaded = files.upload()

uploaded_zip_found = False
for fn in uploaded.keys():
    if fn.endswith('.zip'):
        # 將上傳的 ZIP 檔案儲存到指定路徑
        # Save the uploaded ZIP file to the specified path
        with open('/content/uploaded_project.zip', 'wb') as f:
            f.write(uploaded[fn])
        print(f"Uploaded file '{fn}' saved as '/content/uploaded_project.zip' (已上傳檔案 '{fn}' 並儲存為 '/content/uploaded_project.zip')")
        uploaded_zip_found = True
        unzip_and_proceed() # 呼叫解壓縮函數 (Call the unzipping function)
        break

if not uploaded_zip_found:
    print("No ZIP file was uploaded. Please run the cell again and select a .zip file. (沒有上傳 ZIP 檔案。請重新執行此儲存格並選擇一個 .zip 檔案。)")
```
這個儲存格用於首次設定，它會提示您上傳一個 ZIP 檔案。上傳後，程式碼會將其解壓縮到 `/content/extracted_code` 目錄，以便在 Colab 環境中使用專案檔案。

### 2. Google Drive 整合與持續儲存
此部分將引導您設定 Google Drive，以便在 Colab 會話之間永久儲存您的專案檔案和執行檔。這確保您不必在每次執行時都重新上傳檔案。

注意：如果您的專案需要 `GOOGLE_API_KEY`，請確保在執行此儲存格之前，已在 Colab 的「密鑰」(Secrets) 分頁中新增了名為 `GOOGLE_API_KEY` 的密鑰及其值。下方的程式碼區塊會嘗試讀取該密鑰。
```python
# --- (新增) 讀取 GOOGLE_API_KEY ---
# --- (New) Load GOOGLE_API_KEY ---
print("\n--- Loading GOOGLE_API_KEY ---")
print("中文: 正在嘗試從 Colab Secrets 中讀取 GOOGLE_API_KEY。")
print("English: Attempting to load GOOGLE_API_KEY from Colab Secrets.")
try:
    from google.colab import userdata
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        print("GOOGLE_API_KEY successfully loaded from Colab Secrets. (已成功從 Colab Secrets 讀取 GOOGLE_API_KEY。)")
    else:
        print("GOOGLE_API_KEY not found in Colab Secrets (is it set?). (在 Colab Secrets 中找不到 GOOGLE_API_KEY（是否已設定？）。)")
        print("中文: 程式碼將繼續執行，但如果您的專案需要此金鑰，後續步驟可能會失敗。")
        print("English: The code will continue, but subsequent steps might fail if your project requires this key.")
except ImportError:
    print("Error: `google.colab.userdata` could not be imported. This code is intended to run in a Google Colab environment. (錯誤：無法匯入 `google.colab.userdata`。此程式碼應在 Google Colab 環境中執行。)")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
except Exception as e:
    print(f"An unexpected error occurred while trying to load GOOGLE_API_KEY: {e} (嘗試讀取 GOOGLE_API_KEY 時發生意外錯誤：{e})")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
print("--- Finished loading GOOGLE_API_KEY ---\n")
# --- END (新增) 讀取 GOOGLE_API_KEY ---
```

```python
# 匯入必要的庫
# Import necessary libraries
from google.colab import drive
import os
import zipfile
import shutil

# 掛載 Google Drive
# Mount Google Drive
try:
    drive.mount('/content/drive')
    print("Google Drive mounted successfully. (Google Drive 已成功掛載。)")
except Exception as e:
    print(f"Error mounting Google Drive: {e} (掛載 Google Drive 時發生錯誤：{e})")
    # 如果掛載失敗，則停止執行後續的 Drive 操作
    # If mounting fails, stop further Drive operations
    raise SystemExit("Google Drive mount failed. Cannot proceed.")

# --- 路徑定義 ---
# --- Path Definitions ---
drive_base_path = '/content/drive/MyDrive/GEMINI-worf'  # Google Drive 中的基礎路徑 (Base path in Google Drive)
drive_zip_path_dir = os.path.join(drive_base_path, 'compressed') # Drive 中存放壓縮檔的目錄 (Directory for compressed files in Drive)
drive_executable_path = os.path.join(drive_base_path, 'executable') # Drive 中存放可執行程式碼的目錄 (Directory for executable code in Drive)

colab_executable_path = '/content/executable_code' # Colab 本地存放可執行程式碼的路徑 (Local Colab path for executable code)
colab_temp_zip_file = '/content/temp_project.zip' # Colab 本地臨時 ZIP 檔案路徑 (Local Colab temporary ZIP file path)

# --- 建立 Google Drive 和 Colab 中的目錄 (如果它們不存在) ---
# --- Create directories in Google Drive and Colab if they don't exist ---
try:
    if not os.path.exists(drive_base_path):
        os.makedirs(drive_base_path)
        print(f"Created Google Drive directory: {drive_base_path} (已建立 Google Drive 目錄：{drive_base_path})")
    if not os.path.exists(drive_zip_path_dir):
        os.makedirs(drive_zip_path_dir)
        print(f"Created Google Drive directory: {drive_zip_path_dir} (已建立 Google Drive 目錄：{drive_zip_path_dir})")
    if not os.path.exists(drive_executable_path):
        os.makedirs(drive_executable_path)
        print(f"Created Google Drive directory: {drive_executable_path} (已建立 Google Drive 目錄：{drive_executable_path})")

    if not os.path.exists(colab_executable_path):
        os.makedirs(colab_executable_path)
        print(f"Created Colab directory: {colab_executable_path} (已建立 Colab 目錄：{colab_executable_path})")
except OSError as e:
    print(f"Error creating directories: {e}. Please check permissions or path validity. (建立目錄時發生錯誤：{e}。請檢查權限或路徑有效性。)")
    raise SystemExit("Directory creation failed. Cannot proceed.")

# --- 同步邏輯 ---
# --- Synchronization Logic ---
print("\nStarting synchronization process... (開始同步過程...)")

# 檢查 Colab 中的可執行程式碼路徑是否為空
# Check if the executable code path in Colab is empty
if not os.listdir(colab_executable_path):
    print(f"Colab executable folder '{colab_executable_path}' is empty. Attempting to sync from Google Drive. (Colab 執行資料夾 '{colab_executable_path}' 是空的。正在嘗試從 Google Drive 同步。)")

    # 檢查 Drive 中的可執行程式碼路徑是否包含檔案
    # Check if the executable code path in Drive contains files
    if os.path.exists(drive_executable_path) and os.listdir(drive_executable_path):
        print(f"Found code in Google Drive executable folder ('{drive_executable_path}'). Syncing to Colab... (在 Google Drive 執行資料夾 ('{drive_executable_path}') 中找到程式碼。正在同步到 Colab...)")
        try:
            # 如果 Colab 目錄已存在且包含內容，先刪除它以避免 copytree 錯誤
            # If Colab directory exists and has content, remove it first to avoid copytree error
            if os.path.exists(colab_executable_path):
                shutil.rmtree(colab_executable_path)
                print(f"Removed existing Colab directory: {colab_executable_path} (已移除現有的 Colab 目錄：{colab_executable_path})")
            shutil.copytree(drive_executable_path, colab_executable_path)
            print(f"Sync from Drive executable folder to '{colab_executable_path}' complete. (從 Drive 執行資料夾同步到 '{colab_executable_path}' 完成。)")
        except Exception as e:
            print(f"Error syncing from Drive executable folder: {e} (從 Drive 執行資料夾同步時發生錯誤：{e})")
            print("Please ensure the Drive executable folder is accessible and contains valid files. (請確保 Drive 執行資料夾可訪問且包含有效檔案。)")
    else:
        print(f"Google Drive executable folder ('{drive_executable_path}') is empty. Checking for ZIP file in Drive compressed folder ('{drive_zip_path_dir}')... (Google Drive 執行資料夾 ('{drive_executable_path}') 是空的。正在檢查 Drive 壓縮資料夾 ('{drive_zip_path_dir}') 中的 ZIP 檔案...)")

        zip_file_found_in_drive = None
        if os.path.exists(drive_zip_path_dir) and os.listdir(drive_zip_path_dir):
            for f_name in os.listdir(drive_zip_path_dir):
                if f_name.endswith('.zip'):
                    zip_file_found_in_drive = os.path.join(drive_zip_path_dir, f_name)
                    break

        if zip_file_found_in_drive:
            print(f"Found ZIP file '{zip_file_found_in_drive}' in Google Drive. Copying to Colab, unzipping, and backing up to Drive executable folder. (在 Google Drive 中找到 ZIP 檔案 '{zip_file_found_in_drive}'。正在複製到 Colab，解壓縮，並備份到 Drive 執行資料夾。)")
            try:
                # 1. 複製 ZIP 檔案到 Colab 臨時位置
                # 1. Copy ZIP file to Colab temporary location
                shutil.copy2(zip_file_found_in_drive, colab_temp_zip_file)
                print(f"Copied '{zip_file_found_in_drive}' to '{colab_temp_zip_file}'. (已將 '{zip_file_found_in_drive}' 複製到 '{colab_temp_zip_file}'。)")

                # 2. 解壓縮到 Colab 可執行程式碼路徑
                # 2. Unzip to Colab executable path
                if os.path.exists(colab_executable_path): # 清理舊內容 (Clear old content)
                    shutil.rmtree(colab_executable_path)
                os.makedirs(colab_executable_path) # 重新建立目錄 (Recreate directory)

                with zipfile.ZipFile(colab_temp_zip_file, 'r') as zip_ref:
                    zip_ref.extractall(colab_executable_path)
                print(f"Successfully unzipped '{colab_temp_zip_file}' to '{colab_executable_path}'. (成功將 '{colab_temp_zip_file}' 解壓縮到 '{colab_executable_path}'。)")

                # 3. 將解壓縮的內容備份/複製到 Drive 可執行程式碼路徑
                # 3. Backup/Copy unzipped content to Drive executable path
                if os.path.exists(drive_executable_path): # 清理 Drive 中的舊內容 (Clear old content in Drive)
                     shutil.rmtree(drive_executable_path)
                shutil.copytree(colab_executable_path, drive_executable_path)
                print(f"Successfully backed up unzipped code from '{colab_executable_path}' to '{drive_executable_path}'. (已成功將解壓縮的程式碼從 '{colab_executable_path}' 備份到 '{drive_executable_path}'。)")

                # 4. 清理 Colab 中的臨時 ZIP 檔案
                # 4. Clean up temporary ZIP file in Colab
                os.remove(colab_temp_zip_file)
                print(f"Removed temporary ZIP file: {colab_temp_zip_file}. (已移除臨時 ZIP 檔案：{colab_temp_zip_file}。)")
                print("Unzip from Drive and backup to Drive executable folder complete. (從 Drive 解壓縮並備份到 Drive 執行資料夾完成。)")

            except FileNotFoundError:
                print(f"Error: The ZIP file '{zip_file_found_in_drive}' was not found during copy. This shouldn't happen if listed. (錯誤：複製過程中找不到 ZIP 檔案 '{zip_file_found_in_drive}'。如果已列出，則不應發生這種情況。)")
            except zipfile.BadZipFile:
                print(f"Error: The file '{zip_file_found_in_drive}' is not a valid ZIP file or is corrupted. (錯誤：檔案 '{zip_file_found_in_drive}' 不是有效的 ZIP 檔案或已損壞。)")
            except Exception as e:
                print(f"An error occurred during ZIP processing or backup to Drive: {e} (處理 ZIP 或備份到 Drive 時發生錯誤：{e})")
        else:
            print(f"No ZIP file found in Google Drive compressed folder ('{drive_zip_path_dir}'). (在 Google Drive 壓縮資料夾 ('{drive_zip_path_dir}') 中找不到 ZIP 檔案。)")
            print("Please ensure your project ZIP file is uploaded to Google Drive at 'MyDrive/GEMINI-worf/compressed/' for future use, or use the 'Initial Colab Setup' cell if this is the first time. (請確保您的專案 ZIP 檔案已上傳到 Google Drive 的 'MyDrive/GEMINI-worf/compressed/' 以供將來使用，或者如果這是第一次，請使用「Colab 首次設定」儲存格。)")
else:
    print(f"Executable code already found in Colab environment ('{colab_executable_path}'). (在 Colab 環境 ('{colab_executable_path}') 中已找到可執行程式碼。)")
    print("Assuming it's up-to-date or was handled by a previous step. No synchronization from Drive performed. (假設它是最新的或已由先前的步驟處理。未執行來自 Drive 的同步。)")

print("\nSynchronization process finished. (同步過程結束。)")
# 現在，'/content/executable_code' 中應該有可執行的程式碼
# Now, '/content/executable_code' should contain the executable code.
# 您可以在此儲存格的後續部分或下一個儲存格中繼續執行主要腳本
# You can proceed with running your main script in the latter part of this cell or in the next cell.
# 例如： %run /content/executable_code/main_script.py
# Example: %run /content/executable_code/main_script.py
```
這個儲存格的目的是將您的 Google Drive 與 Colab 環境連接起來。它會嘗試從 Google Drive 的 `GEMINI-worf/executable` 目錄中同步現有的可執行程式碼。如果該目錄為空，它會查找 `GEMINI-worf/compressed` 中的最新 ZIP 檔案，將其解壓縮到 Colab 的 `/content/executable_code`，然後將此解壓縮版本備份回 Drive 的 `GEMINI-worf/executable` 以供將來更快地存取。如果 Colab 中已存在程式碼，則跳過同步。

### 3. 後續執行
在您首次完成「Colab 首次設定與檔案上傳」和「Google Drive 整合與持續儲存」之後，您可以使用此儲存格來執行您的專案。此儲存格假設您的程式碼已經同步到 Google Drive 的 `GEMINI-worf/executable` 目錄中。

注意：如果您的專案需要 `GOOGLE_API_KEY`，請確保在執行此儲存格之前，已在 Colab 的「密鑰」(Secrets) 分頁中新增了名為 `GOOGLE_API_KEY` 的密鑰及其值。下方的程式碼區塊會嘗試讀取該密鑰。
```python
# --- (新增) 讀取 GOOGLE_API_KEY ---
# --- (New) Load GOOGLE_API_KEY ---
print("\n--- Loading GOOGLE_API_KEY ---")
print("中文: 正在嘗試從 Colab Secrets 中讀取 GOOGLE_API_KEY。")
print("English: Attempting to load GOOGLE_API_KEY from Colab Secrets.")
try:
    from google.colab import userdata
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        print("GOOGLE_API_KEY successfully loaded from Colab Secrets. (已成功從 Colab Secrets 讀取 GOOGLE_API_KEY。)")
    else:
        print("GOOGLE_API_KEY not found in Colab Secrets (is it set?). (在 Colab Secrets 中找不到 GOOGLE_API_KEY（是否已設定？）。)")
        print("中文: 程式碼將繼續執行，但如果您的專案需要此金鑰，後續步驟可能會失敗。")
        print("English: The code will continue, but subsequent steps might fail if your project requires this key.")
except ImportError:
    print("Error: `google.colab.userdata` could not be imported. This code is intended to run in a Google Colab environment. (錯誤：無法匯入 `google.colab.userdata`。此程式碼應在 Google Colab 環境中執行。)")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
except Exception as e:
    print(f"An unexpected error occurred while trying to load GOOGLE_API_KEY: {e} (嘗試讀取 GOOGLE_API_KEY 時發生意外錯誤：{e})")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
print("--- Finished loading GOOGLE_API_KEY ---\n")
# --- END (新增) 讀取 GOOGLE_API_KEY ---
```

```python
# 匯入必要的庫
# Import necessary libraries
from google.colab import drive
import os
import shutil

# 掛載 Google Drive (強制重新掛載以確保是最新的)
# Mount Google Drive (force remount to ensure it's current)
try:
    drive.mount('/content/drive', force_remount=True)
    print("Google Drive mounted successfully. (Google Drive 已成功掛載。)")
except Exception as e:
    print(f"Error mounting Google Drive: {e} (掛載 Google Drive 時發生錯誤：{e})")
    # 如果掛載失敗，則停止執行後續的 Drive 操作
    # If mounting fails, stop further Drive operations
    raise SystemExit("Google Drive mount failed. Cannot proceed.")

# --- 路徑定義 (與第 2 部分一致) ---
# --- Path Definitions (consistent with Section 2) ---
drive_executable_path = '/content/drive/MyDrive/GEMINI-worf/executable' # Drive 中存放可執行程式碼的目錄 (Directory for executable code in Drive)
colab_executable_path = '/content/executable_code' # Colab 本地存放可執行程式碼的路徑 (Local Colab path for executable code)

# --- 確保 Colab 環境準備就緒 ---
# --- Ensuring Colab environment is ready for execution ---
print("\nEnsuring Colab environment is ready for execution... (確保 Colab 環境準備就緒...)")

# 建立 Colab 中的可執行程式碼路徑 (如果它不存在)
# Create Colab executable path if it doesn't exist
if not os.path.exists(colab_executable_path):
    os.makedirs(colab_executable_path)
    print(f"Created Colab directory: {colab_executable_path} (已建立 Colab 目錄：{colab_executable_path})")

# 檢查 Colab 中的可執行程式碼路徑是否為空，或者我們想要確保它是從 Drive 過來的最新版本
# Check if Colab executable path is empty, or if we want to ensure it's the latest from Drive
force_sync_from_drive = True # 設定為 True 以始終從 Drive 同步，設定為 False 以僅在 Colab 為空時同步
                             # Set to True to always sync from Drive, False to sync only if Colab is empty.
                             # 對於「後續執行」，通常建議 True 以獲取最新程式碼。
                             # For "Subsequent Runs", True is generally recommended to get the latest code.


if force_sync_from_drive or not os.listdir(colab_executable_path):
    if force_sync_from_drive:
        print(f"Force sync is enabled. Refreshing code from Google Drive executable folder ('{drive_executable_path}')... (強制同步已啟用。正在從 Google Drive 執行資料夾 ('{drive_executable_path}') 更新程式碼...)")
    else:
        print(f"Colab executable folder ('{colab_executable_path}') is empty. Attempting to sync from Google Drive. (Colab 執行資料夾 ('{colab_executable_path}') 是空的。正在嘗試從 Google Drive 同步。)")

    if os.path.exists(drive_executable_path) and os.listdir(drive_executable_path):
        print(f"Syncing latest code from Google Drive executable folder ('{drive_executable_path}') to Colab... (正在將最新程式碼從 Google Drive 執行資料夾 ('{drive_executable_path}') 同步到 Colab...)")
        try:
            if os.path.exists(colab_executable_path):
                shutil.rmtree(colab_executable_path) # 移除舊的 Colab 程式碼 (Remove old Colab code)
                print(f"Removed existing Colab directory: {colab_executable_path} (已移除現有的 Colab 目錄：{colab_executable_path})")
            os.makedirs(colab_executable_path) # 確保在 copytree 之前目錄存在 (Ensure directory exists before copytree)
            shutil.copytree(drive_executable_path, colab_executable_path, dirs_exist_ok=True) # dirs_exist_ok=True 避免了如果內部有子目錄時的問題
            print(f"Sync complete. Code is ready in '{colab_executable_path}'. (同步完成。程式碼已準備就緒於 '{colab_executable_path}'。)")
        except Exception as e:
            print(f"Error syncing from Drive executable folder: {e} (從 Drive 執行資料夾同步時發生錯誤：{e})")
            print(f"Please ensure the Drive executable folder ('{drive_executable_path}') is accessible and contains valid files. (請確保 Drive 執行資料夾 ('{drive_executable_path}') 可訪問且包含有效檔案。)")
            raise SystemExit("Code sync failed. Cannot proceed.")
    else:
        print(f"Error: Google Drive executable folder ('{drive_executable_path}') is empty or not found. (錯誤：Google Drive 執行資料夾 ('{drive_executable_path}') 為空或找不到。)")
        print("Please ensure setup was completed using Sections 1 and 2, and that code exists in the Drive executable path. (請確保已使用第 1 和第 2 部分完成設定，並且程式碼存在於 Drive 執行路徑中。)")
        raise SystemExit("Drive executable folder is not ready. Cannot proceed.")
else:
    print(f"Code already present in Colab ('{colab_executable_path}'). Assuming it's ready. (程式碼已存在於 Colab ('{colab_executable_path}')。假設已準備就緒。)")

# --- 執行您的主要腳本 ---
# --- Execute your main script ---
print("\n--- Project Execution ---")
print("中文: 请在此处取消注释并修改以下行来执行您的代码。 (例如，更改 'your_main_script.py' 为您的实际脚本名称和路径)")
print("English: Please uncomment and modify the following lines to execute your code here. (e.g., change 'your_main_script.py' to your actual script name and path)")

# 中文: 在下方加入您專案的主要執行命令 (例如: %run /content/executable_code/main.py 或 !python /content/executable_code/main.py)
# English: Add your project's main execution command below (e.g., %run /content/executable_code/main.py or !python /content/executable_code/main.py)

# 示例 (Example):
# %cd /content/executable_code
# !python your_main_script.py

# 如果您的專案需要特定的 Python 版本或依賴項，請確保在此之前已設定好
# If your project requires specific Python versions or dependencies, ensure they are set up before this point.
```
此儲存格用於在初始設定後執行您的專案。它會首先確保 Colab 環境中的 `/content/executable_code` 目錄與您在 Google Drive 上 `GEMINI-worf/executable` 中的最新程式碼同步。然後，您需要取消註釋並修改儲存格末尾的命令以實際執行您的主要腳本。

### 一般使用說明
- 此設定旨在簡化在 Google Colab 中執行 GitHub 專案的流程。
- 首次執行時，您需要使用「Colab 首次設定與檔案上傳」儲存格來上傳您的 .zip 壓縮檔。
- 完成首次設定後，您的程式碼將會備份到您的 Google Drive (`GEMINI-worf/executable` 資料夾)。
- 後續執行時，您可以使用「Google Drive 整合與持續儲存」儲存格（如果需要確保與雲端同步）或直接使用「後續執行」儲存格來載入並執行您的程式碼。
- 所有程式碼和上傳的檔案都將儲存在您的 Google Drive 中，以避免在 Colab 工作階段結束時遺失。

#### 關於 API 金鑰的錯誤處理
*   - **檢查密鑰名稱**：確保您在程式碼中使用的密鑰名稱（例如 `userdata.get('YOUR_KEY_NAME')`）與您在 Colab「密鑰」分頁中設定的名稱完全相符（區分大小寫）。
*   - **驗證金鑰值**：再次檢查您輸入的金鑰值是否正確、未過期且具有存取所需服務的必要權限。
*   - **特定服務錯誤**：大多數 API 服務在金鑰驗證失敗時會提供特定的錯誤訊息。請仔細閱讀這些訊息，它們通常會指出問題所在（例如，無效的金鑰、超出配額等）。
*   - **GOOGLE_API_KEY 特別說明**：對於 `GOOGLE_API_KEY`，上述相關儲存格已包含讀取邏輯。如果提示找不到，請務必在 Colab 的「密鑰」中設定名為 `GOOGLE_API_KEY` 的密鑰。

## English Instructions

### 1. Initial Colab Setup & File Upload
This section guides you through the initial setup of the project in Colab. It involves uploading a ZIP file containing the project documents.

```python
# 匯入必要的庫
# Import necessary libraries
from google.colab import files
import zipfile
import os

# 定義解壓縮 ZIP 檔案並執行後續步驟的函數
# Define a function to unzip the file and perform subsequent steps
def unzip_and_proceed():
    zip_file_name = '/content/uploaded_project.zip'  # 指定 ZIP 檔案的名稱 (Specify the name of the ZIP file)
    extract_path = '/content/extracted_code'  # 指定解壓縮的目標路徑 (Specify the target path for extraction)

    # 確保解壓縮路徑存在
    # Ensure the extraction path exists
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)
        print(f"Created directory: {extract_path} (已建立目錄：{extract_path})")

    try:
        # 解壓縮 ZIP 檔案
        # Unzip the ZIP file
        with zipfile.ZipFile(zip_file_name, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"Successfully unzipped '{zip_file_name}' to '{extract_path}' (成功將 '{zip_file_name}' 解壓縮到 '{extract_path}')")
        # 在這裡可以添加解壓縮成功後的其他操作，例如列出解壓縮的檔案
        # You can add other operations here after successful unzipping, e.g., listing the extracted files
        print(f"Files extracted to: {os.listdir(extract_path)} (檔案解壓縮至：{os.listdir(extract_path)})")
    except zipfile.BadZipFile:
        print(f"Error: The uploaded file is not a valid ZIP file or is corrupted. (錯誤：上傳的檔案不是有效的 ZIP 檔案或已損壞。)")
    except FileNotFoundError:
        print(f"Error: The ZIP file was not found at '{zip_file_name}'. Please ensure a ZIP file was uploaded. (錯誤：在 '{zip_file_name}'找不到 ZIP 檔案。請確保已上傳 ZIP 檔案。)")
    except Exception as e:
        print(f"An unexpected error occurred during unzipping: {e} (解壓縮過程中發生意外錯誤：{e})")

# 上傳檔案
# Upload files
print("Please upload your project ZIP file. (請上傳您的專案 ZIP 檔案。)")
uploaded = files.upload()

uploaded_zip_found = False
for fn in uploaded.keys():
    if fn.endswith('.zip'):
        # 將上傳的 ZIP 檔案儲存到指定路徑
        # Save the uploaded ZIP file to the specified path
        with open('/content/uploaded_project.zip', 'wb') as f:
            f.write(uploaded[fn])
        print(f"Uploaded file '{fn}' saved as '/content/uploaded_project.zip' (已上傳檔案 '{fn}' 並儲存為 '/content/uploaded_project.zip')")
        uploaded_zip_found = True
        unzip_and_proceed() # 呼叫解壓縮函數 (Call the unzipping function)
        break

if not uploaded_zip_found:
    print("No ZIP file was uploaded. Please run the cell again and select a .zip file. (沒有上傳 ZIP 檔案。請重新執行此儲存格並選擇一個 .zip 檔案。)")
```
This cell is for the first-time setup. It will prompt you to upload a ZIP file. Once uploaded, the code will unzip it to the `/content/extracted_code` directory, making the project files available for use in the Colab environment.

### 2. Google Drive Integration & Persistent Storage
This section guides you through setting up Google Drive for persistent storage of your project files and executables across Colab sessions. This ensures you don't have to re-upload files every time.

Note: If your project requires a `GOOGLE_API_KEY`, please ensure you have added a secret named `GOOGLE_API_KEY` with its value in Colab's 'Secrets' tab before running this cell. The code block below will attempt to load it.
```python
# --- (新增) 讀取 GOOGLE_API_KEY ---
# --- (New) Load GOOGLE_API_KEY ---
print("\n--- Loading GOOGLE_API_KEY ---")
print("中文: 正在嘗試從 Colab Secrets 中讀取 GOOGLE_API_KEY。")
print("English: Attempting to load GOOGLE_API_KEY from Colab Secrets.")
try:
    from google.colab import userdata
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        print("GOOGLE_API_KEY successfully loaded from Colab Secrets. (已成功從 Colab Secrets 讀取 GOOGLE_API_KEY。)")
    else:
        print("GOOGLE_API_KEY not found in Colab Secrets (is it set?). (在 Colab Secrets 中找不到 GOOGLE_API_KEY（是否已設定？）。)")
        print("中文: 程式碼將繼續執行，但如果您的專案需要此金鑰，後續步驟可能會失敗。")
        print("English: The code will continue, but subsequent steps might fail if your project requires this key.")
except ImportError:
    print("Error: `google.colab.userdata` could not be imported. This code is intended to run in a Google Colab environment. (錯誤：無法匯入 `google.colab.userdata`。此程式碼應在 Google Colab 環境中執行。)")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
except Exception as e:
    print(f"An unexpected error occurred while trying to load GOOGLE_API_KEY: {e} (嘗試讀取 GOOGLE_API_KEY 時發生意外錯誤：{e})")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
print("--- Finished loading GOOGLE_API_KEY ---\n")
# --- END (新增) 讀取 GOOGLE_API_KEY ---
```

```python
# Import necessary libraries
# 匯入必要的庫
from google.colab import drive
import os
import zipfile
import shutil

# Mount Google Drive
# 掛載 Google Drive
try:
    drive.mount('/content/drive')
    print("Google Drive mounted successfully. (Google Drive 已成功掛載。)")
except Exception as e:
    print(f"Error mounting Google Drive: {e} (掛載 Google Drive 時發生錯誤：{e})")
    # If mounting fails, stop further Drive operations
    # 如果掛載失敗，則停止執行後續的 Drive 操作
    raise SystemExit("Google Drive mount failed. Cannot proceed.")

# --- Path Definitions ---
# --- 路徑定義 ---
drive_base_path = '/content/drive/MyDrive/GEMINI-worf'  # Base path in Google Drive (Google Drive 中的基礎路徑)
drive_zip_path_dir = os.path.join(drive_base_path, 'compressed') # Directory for compressed files in Drive (Drive 中存放壓縮檔的目錄)
drive_executable_path = os.path.join(drive_base_path, 'executable') # Directory for executable code in Drive (Drive 中存放可執行程式碼的目錄)

colab_executable_path = '/content/executable_code' # Local Colab path for executable code (Colab 本地存放可執行程式碼的路徑)
colab_temp_zip_file = '/content/temp_project.zip' # Local Colab temporary ZIP file path (Colab 本地臨時 ZIP 檔案路徑)

# --- Create directories in Google Drive and Colab if they don't exist ---
# --- 建立 Google Drive 和 Colab 中的目錄 (如果它們不存在) ---
try:
    if not os.path.exists(drive_base_path):
        os.makedirs(drive_base_path)
        print(f"Created Google Drive directory: {drive_base_path} (已建立 Google Drive 目錄：{drive_base_path})")
    if not os.path.exists(drive_zip_path_dir):
        os.makedirs(drive_zip_path_dir)
        print(f"Created Google Drive directory: {drive_zip_path_dir} (已建立 Google Drive 目錄：{drive_zip_path_dir})")
    if not os.path.exists(drive_executable_path):
        os.makedirs(drive_executable_path)
        print(f"Created Google Drive directory: {drive_executable_path} (已建立 Google Drive 目錄：{drive_executable_path})")

    if not os.path.exists(colab_executable_path):
        os.makedirs(colab_executable_path)
        print(f"Created Colab directory: {colab_executable_path} (已建立 Colab 目錄：{colab_executable_path})")
except OSError as e:
    print(f"Error creating directories: {e}. Please check permissions or path validity. (建立目錄時發生錯誤：{e}。請檢查權限或路徑有效性。)")
    raise SystemExit("Directory creation failed. Cannot proceed.")

# --- Synchronization Logic ---
# --- 同步邏輯 ---
print("\nStarting synchronization process... (開始同步過程...)")

# Check if the executable code path in Colab is empty
# 檢查 Colab 中的可執行程式碼路徑是否為空
if not os.listdir(colab_executable_path):
    print(f"Colab executable folder '{colab_executable_path}' is empty. Attempting to sync from Google Drive. (Colab 執行資料夾 '{colab_executable_path}' 是空的。正在嘗試從 Google Drive 同步。)")

    # Check if the executable code path in Drive contains files
    # 檢查 Drive 中的可執行程式碼路徑是否包含檔案
    if os.path.exists(drive_executable_path) and os.listdir(drive_executable_path):
        print(f"Found code in Google Drive executable folder ('{drive_executable_path}'). Syncing to Colab... (在 Google Drive 執行資料夾 ('{drive_executable_path}') 中找到程式碼。正在同步到 Colab...)")
        try:
            # If Colab directory exists and has content, remove it first to avoid copytree error
            # 如果 Colab 目錄已存在且包含內容，先刪除它以避免 copytree 錯誤
            if os.path.exists(colab_executable_path):
                shutil.rmtree(colab_executable_path)
                print(f"Removed existing Colab directory: {colab_executable_path} (已移除現有的 Colab 目錄：{colab_executable_path})")
            shutil.copytree(drive_executable_path, colab_executable_path)
            print(f"Sync from Drive executable folder to '{colab_executable_path}' complete. (從 Drive 執行資料夾同步到 '{colab_executable_path}' 完成。)")
        except Exception as e:
            print(f"Error syncing from Drive executable folder: {e} (從 Drive 執行資料夾同步時發生錯誤：{e})")
            print("Please ensure the Drive executable folder is accessible and contains valid files. (請確保 Drive 執行資料夾可訪問且包含有效檔案。)")
    else:
        print(f"Google Drive executable folder ('{drive_executable_path}') is empty. Checking for ZIP file in Drive compressed folder ('{drive_zip_path_dir}')... (Google Drive 執行資料夾 ('{drive_executable_path}') 是空的。正在檢查 Drive 壓縮資料夾 ('{drive_zip_path_dir}') 中的 ZIP 檔案...)")

        zip_file_found_in_drive = None
        if os.path.exists(drive_zip_path_dir) and os.listdir(drive_zip_path_dir):
            for f_name in os.listdir(drive_zip_path_dir):
                if f_name.endswith('.zip'):
                    zip_file_found_in_drive = os.path.join(drive_zip_path_dir, f_name)
                    break

        if zip_file_found_in_drive:
            print(f"Found ZIP file '{zip_file_found_in_drive}' in Google Drive. Copying to Colab, unzipping, and backing up to Drive executable folder. (在 Google Drive 中找到 ZIP 檔案 '{zip_file_found_in_drive}'。正在複製到 Colab，解壓縮，並備份到 Drive 執行資料夾。)")
            try:
                # 1. Copy ZIP file to Colab temporary location
                # 1. 複製 ZIP 檔案到 Colab 臨時位置
                shutil.copy2(zip_file_found_in_drive, colab_temp_zip_file)
                print(f"Copied '{zip_file_found_in_drive}' to '{colab_temp_zip_file}'. (已將 '{zip_file_found_in_drive}' 複製到 '{colab_temp_zip_file}'。)")

                # 2. Unzip to Colab executable path
                # 2. 解壓縮到 Colab 可執行程式碼路徑
                if os.path.exists(colab_executable_path): # Clear old content (清理舊內容)
                    shutil.rmtree(colab_executable_path)
                os.makedirs(colab_executable_path) # Recreate directory (重新建立目錄)

                with zipfile.ZipFile(colab_temp_zip_file, 'r') as zip_ref:
                    zip_ref.extractall(colab_executable_path)
                print(f"Successfully unzipped '{colab_temp_zip_file}' to '{colab_executable_path}'. (成功將 '{colab_temp_zip_file}' 解壓縮到 '{colab_executable_path}'。)")

                # 3. Backup/Copy unzipped content to Drive executable path
                # 3. 將解壓縮的內容備份/複製到 Drive 可執行程式碼路徑
                if os.path.exists(drive_executable_path): # Clear old content in Drive (清理 Drive 中的舊內容)
                     shutil.rmtree(drive_executable_path)
                shutil.copytree(colab_executable_path, drive_executable_path)
                print(f"Successfully backed up unzipped code from '{colab_executable_path}' to '{drive_executable_path}'. (已成功將解壓縮的程式碼從 '{colab_executable_path}' 備份到 '{drive_executable_path}'。)")

                # 4. Clean up temporary ZIP file in Colab
                # 4. 清理 Colab 中的臨時 ZIP 檔案
                os.remove(colab_temp_zip_file)
                print(f"Removed temporary ZIP file: {colab_temp_zip_file}. (已移除臨時 ZIP 檔案：{colab_temp_zip_file}。)")
                print("Unzip from Drive and backup to Drive executable folder complete. (從 Drive 解壓縮並備份到 Drive 執行資料夾完成。)")

            except FileNotFoundError:
                print(f"Error: The ZIP file '{zip_file_found_in_drive}' was not found during copy. This shouldn't happen if listed. (錯誤：複製過程中找不到 ZIP 檔案 '{zip_file_found_in_drive}'。如果已列出，則不應發生這種情況。)")
            except zipfile.BadZipFile:
                print(f"Error: The file '{zip_file_found_in_drive}' is not a valid ZIP file or is corrupted. (錯誤：檔案 '{zip_file_found_in_drive}' 不是有效的 ZIP 檔案或已損壞。)")
            except Exception as e:
                print(f"An error occurred during ZIP processing or backup to Drive: {e} (處理 ZIP 或備份到 Drive 時發生錯誤：{e})")
        else:
            print(f"No ZIP file found in Google Drive compressed folder ('{drive_zip_path_dir}'). (在 Google Drive 壓縮資料夾 ('{drive_zip_path_dir}') 中找不到 ZIP 檔案。)")
            print("Please ensure your project ZIP file is uploaded to Google Drive at 'MyDrive/GEMINI-worf/compressed/' for future use, or use the 'Initial Colab Setup' cell if this is the first time. (請確保您的專案 ZIP 檔案已上傳到 Google Drive 的 'MyDrive/GEMINI-worf/compressed/' 以供將來使用，或者如果這是第一次，請使用「Colab 首次設定」儲存格。)")
else:
    print(f"Executable code already found in Colab environment ('{colab_executable_path}'). (在 Colab 環境 ('{colab_executable_path}') 中已找到可執行程式碼。)")
    print("Assuming it's up-to-date or was handled by a previous step. No synchronization from Drive performed. (假設它是最新的或已由先前的步驟處理。未執行來自 Drive 的同步。)")

print("\nSynchronization process finished. (同步過程結束。)")
# Now, '/content/executable_code' should contain the executable code.
# 現在，'/content/executable_code' 中應該有可執行的程式碼
# You can proceed with running your main script in the latter part of this cell or in the next cell.
# 您可以在此儲存格的後續部分或下一個儲存格中繼續執行主要腳本
# Example: %run /content/executable_code/main_script.py
# 例如： %run /content/executable_code/main_script.py
```
The purpose of this cell is to connect your Google Drive to the Colab environment. It attempts to sync existing executable code from the `GEMINI-worf/executable` directory in your Google Drive. If that's empty, it looks for the latest ZIP file in `GEMINI-worf/compressed`, unzips it to Colab's `/content/executable_code`, and then backs up this unzipped version to Drive's `GEMINI-worf/executable` for faster access in the future. If code already exists in Colab, synchronization is skipped.

### 3. Subsequent Runs
After you have completed the "Initial Colab Setup & File Upload" and "Google Drive Integration & Persistent Storage" for the first time, you can use this cell to run your project. This cell assumes your code has been synced to the `GEMINI-worf/executable` directory in your Google Drive.

Note: If your project requires a `GOOGLE_API_KEY`, please ensure you have added a secret named `GOOGLE_API_KEY` with its value in Colab's 'Secrets' tab before running this cell. The code block below will attempt to load it.
```python
# --- (新增) 讀取 GOOGLE_API_KEY ---
# --- (New) Load GOOGLE_API_KEY ---
print("\n--- Loading GOOGLE_API_KEY ---")
print("中文: 正在嘗試從 Colab Secrets 中讀取 GOOGLE_API_KEY。")
print("English: Attempting to load GOOGLE_API_KEY from Colab Secrets.")
try:
    from google.colab import userdata
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        print("GOOGLE_API_KEY successfully loaded from Colab Secrets. (已成功從 Colab Secrets 讀取 GOOGLE_API_KEY。)")
    else:
        print("GOOGLE_API_KEY not found in Colab Secrets (is it set?). (在 Colab Secrets 中找不到 GOOGLE_API_KEY（是否已設定？）。)")
        print("中文: 程式碼將繼續執行，但如果您的專案需要此金鑰，後續步驟可能會失敗。")
        print("English: The code will continue, but subsequent steps might fail if your project requires this key.")
except ImportError:
    print("Error: `google.colab.userdata` could not be imported. This code is intended to run in a Google Colab environment. (錯誤：無法匯入 `google.colab.userdata`。此程式碼應在 Google Colab 環境中執行。)")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
except Exception as e:
    print(f"An unexpected error occurred while trying to load GOOGLE_API_KEY: {e} (嘗試讀取 GOOGLE_API_KEY 時發生意外錯誤：{e})")
    GOOGLE_API_KEY = None # Ensure GOOGLE_API_KEY exists
print("--- Finished loading GOOGLE_API_KEY ---\n")
# --- END (新增) 讀取 GOOGLE_API_KEY ---
```

```python
# Import necessary libraries
# 匯入必要的庫
from google.colab import drive
import os
import shutil

# Mount Google Drive (force remount to ensure it's current)
# 掛載 Google Drive (強制重新掛載以確保是最新的)
try:
    drive.mount('/content/drive', force_remount=True)
    print("Google Drive mounted successfully. (Google Drive 已成功掛載。)")
except Exception as e:
    print(f"Error mounting Google Drive: {e} (掛載 Google Drive 時發生錯誤：{e})")
    # If mounting fails, stop further Drive operations
    # 如果掛載失敗，則停止執行後續的 Drive 操作
    raise SystemExit("Google Drive mount failed. Cannot proceed.")

# --- Path Definitions (consistent with Section 2) ---
# --- 路徑定義 (與第 2 部分一致) ---
drive_executable_path = '/content/drive/MyDrive/GEMINI-worf/executable' # Directory for executable code in Drive (Drive 中存放可執行程式碼的目錄)
colab_executable_path = '/content/executable_code' # Local Colab path for executable code (Colab 本地存放可執行程式碼的路徑)

# --- Ensuring Colab environment is ready for execution ---
# --- 確保 Colab 環境準備就緒 ---
print("\nEnsuring Colab environment is ready for execution... (確保 Colab 環境準備就緒...)")

# Create Colab executable path if it doesn't exist
# 建立 Colab 中的可執行程式碼路徑 (如果它不存在)
if not os.path.exists(colab_executable_path):
    os.makedirs(colab_executable_path)
    print(f"Created Colab directory: {colab_executable_path} (已建立 Colab 目錄：{colab_executable_path})")

# Check if Colab executable path is empty, or if we want to ensure it's the latest from Drive
# 檢查 Colab 中的可執行程式碼路徑是否為空，或者我們想要確保它是從 Drive 過來的最新版本
force_sync_from_drive = True # Set to True to always sync from Drive, False to sync only if Colab is empty.
                             # 設定為 True 以始終從 Drive 同步，設定為 False 以僅在 Colab 為空時同步
                             # For "Subsequent Runs", True is generally recommended to get the latest code.
                             # 對於「後續執行」，通常建議 True 以獲取最新程式碼。

if force_sync_from_drive or not os.listdir(colab_executable_path):
    if force_sync_from_drive:
        print(f"Force sync is enabled. Refreshing code from Google Drive executable folder ('{drive_executable_path}')... (強制同步已啟用。正在從 Google Drive 執行資料夾 ('{drive_executable_path}') 更新程式碼...)")
    else:
        print(f"Colab executable folder ('{colab_executable_path}') is empty. Attempting to sync from Google Drive. (Colab 執行資料夾 ('{colab_executable_path}') 是空的。正在嘗試從 Google Drive 同步。)")

    if os.path.exists(drive_executable_path) and os.listdir(drive_executable_path):
        print(f"Syncing latest code from Google Drive executable folder ('{drive_executable_path}') to Colab... (正在將最新程式碼從 Google Drive 執行資料夾 ('{drive_executable_path}') 同步到 Colab...)")
        try:
            if os.path.exists(colab_executable_path):
                shutil.rmtree(colab_executable_path) # Remove old Colab code (移除舊的 Colab 程式碼)
                print(f"Removed existing Colab directory: {colab_executable_path} (已移除現有的 Colab 目錄：{colab_executable_path})")
            os.makedirs(colab_executable_path) # Ensure directory exists before copytree (確保在 copytree 之前目錄存在)
            shutil.copytree(drive_executable_path, colab_executable_path, dirs_exist_ok=True) # dirs_exist_ok=True avoids issues if subdirectories exist
            print(f"Sync complete. Code is ready in '{colab_executable_path}'. (同步完成。程式碼已準備就緒於 '{colab_executable_path}'。)")
        except Exception as e:
            print(f"Error syncing from Drive executable folder: {e} (從 Drive 執行資料夾同步時發生錯誤：{e})")
            print(f"Please ensure the Drive executable folder ('{drive_executable_path}') is accessible and contains valid files. (請確保 Drive 執行資料夾 ('{drive_executable_path}') 可訪問且包含有效檔案。)")
            raise SystemExit("Code sync failed. Cannot proceed.")
    else:
        print(f"Error: Google Drive executable folder ('{drive_executable_path}') is empty or not found. (錯誤：Google Drive 執行資料夾 ('{drive_executable_path}') 為空或找不到。)")
        print("Please ensure setup was completed using Sections 1 and 2, and that code exists in the Drive executable path. (請確保已使用第 1 和第 2 部分完成設定，並且程式碼存在於 Drive 執行路徑中。)")
        raise SystemExit("Drive executable folder is not ready. Cannot proceed.")
else:
    print(f"Code already present in Colab ('{colab_executable_path}'). Assuming it's ready. (程式碼已存在於 Colab ('{colab_executable_path}')。假設已準備就緒。)")

# --- Execute your main script ---
# --- 執行您的主要腳本 ---
print("\n--- Project Execution ---")
print("中文: 请在此处取消注释并修改以下行来执行您的代码。 (例如，更改 'your_main_script.py' 为您的实际脚本名称和路径)")
print("English: Please uncomment and modify the following lines to execute your code here. (e.g., change 'your_main_script.py' to your actual script name and path)")

# 中文: 在下方加入您專案的主要執行命令 (例如: %run /content/executable_code/main.py 或 !python /content/executable_code/main.py)
# English: Add your project's main execution command below (e.g., %run /content/executable_code/main.py or !python /content/executable_code/main.py)

# 示例 (Example):
# %cd /content/executable_code
# !python your_main_script.py

# If your project requires specific Python versions or dependencies, ensure they are set up before this point.
# 如果您的專案需要特定的 Python 版本或依賴項，請確保在此之前已設定好
```
This cell is used to run your project after the initial setup. It will first ensure that the `/content/executable_code` directory in your Colab environment is synced with the latest code from `GEMINI-worf/executable` on your Google Drive. You will then need to uncomment and modify the commands at the end of the cell to actually execute your main script.

### General Usage Notes
- This setup is designed to simplify the process of running GitHub projects in Google Colab.
- On your first run, you will need to use the 'Initial Colab Setup & File Upload' cell to upload your .zip file.
- After the initial setup, your code will be backed up to your Google Drive (in the `GEMINI-worf/executable` folder).
- For subsequent runs, you can use the 'Google Drive Integration & Persistent Storage' cell (if you need to ensure synchronization with the cloud) or directly use the 'Subsequent Runs' cell to load and run your code.
- All code and uploaded files will be stored in your Google Drive to prevent loss when your Colab session ends.

#### API Key Error Handling
*   "- **Check Secret Names**: Ensure the secret name used in your code (e.g., `userdata.get('YOUR_KEY_NAME')`) exactly matches the name you set in Colab's 'Secrets' tab (it's case-sensitive)."
*   "- **Verify Key Value**: Double-check that the API key value you entered is correct, not expired, and has the necessary permissions for the service you're trying to access."
*   "- **Service-Specific Errors**: Most API services provide specific error messages when key authentication fails. Read these messages carefully, as they often indicate the problem (e.g., invalid key, quota exceeded, etc.)."
*   "- **Note on GOOGLE_API_KEY**: The relevant cells above include logic to load the `GOOGLE_API_KEY`. If it's reported as not found, ensure it's set as a secret named `GOOGLE_API_KEY` in Colab's 'Secrets'."
