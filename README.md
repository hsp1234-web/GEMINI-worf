# 在 Google Colab 中運行您的專案

本文件旨在引導您如何在 Google Colaboratory (Colab) 環境中輕鬆設定並執行您的專案。透過以下提供的兩個 Colab 儲存格，您可以快速將專案部署到 Colab，並選擇是否將其與您的 Google Drive 同步以實現持久化儲存。

## 整體結構

本指南包含兩個主要的 Colab 儲存格，請依序執行：

1.  **首次運行設定 (上傳專案並初始化)**：此儲存格負責處理專案的初次上傳和設定。您可以選擇將專案檔案儲存到 Google Drive，方便日後快速取用。
2.  **後續運行 (載入專案並執行)**：在完成首次設定後，此儲存格用於重新載入您的專案 (無論是從 Google Drive 還是重新上傳) 並執行您的主要程式碼。

---

### 1. 首次運行設定 (上傳專案並初始化)

此儲存格將引導您完成專案的首次設定。它會執行以下操作：
1.  提示您上傳包含專案所有檔案的 ZIP 壓縮檔。
2.  詢問您是否希望將專案檔案儲存到您的 Google Drive。
    *   **建議掛載 Google Drive**：這樣您的專案檔案將會被儲存起來，方便未來直接透過「後續運行」儲存格載入，無需重複上傳和解壓縮。
    *   **不掛載 Google Drive**：如果您選擇不掛載，專案檔案將僅存在於本次 Colab 工作階段中。關閉分頁後，下次需要重新上傳 ZIP 檔案。
3.  根據您的選擇，處理檔案的解壓縮和儲存。
4.  嘗試讀取 `GOOGLE_API_KEY` (如果您的專案需要)。請確保已在 Colab 的「密鑰」(Secrets) 中設定。

```python
import os
import shutil
import zipfile
from google.colab import files, drive, userdata

# --- 配置路徑 ---
# Colab 中解壓縮和執行的路徑
COLAB_PROJECT_DIR = '/content/project_code'
# Colab 中臨時存放上傳 ZIP 的路徑
COLAB_TEMP_ZIP = '/content/uploaded_project.zip'
# 使用者 Drive 中的專案基礎路行 (可修改 MyProject 資料夾名稱)
DRIVE_PROJECT_BASE_DIR = '/content/drive/MyDrive/MyProject'
# Drive 中存放解壓縮後可執行程式碼的路徑
DRIVE_EXECUTABLE_DIR = os.path.join(DRIVE_PROJECT_BASE_DIR, 'executable_code')
# Drive 中存放原始壓縮檔的路徑
DRIVE_COMPRESSED_DIR = os.path.join(DRIVE_PROJECT_BASE_DIR, 'compressed_zips')

# --- GOOGLE_API_KEY 相關 ---
GOOGLE_API_KEY = None
try:
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        print("成功讀取 GOOGLE_API_KEY。")
    else:
        print("警告：未在 Colab 密鑰中找到 GOOGLE_API_KEY。如果您的專案需要，請設定它。")
except userdata.SecretNotFoundError:
    print("警告：未在 Colab 密鑰中找到名為 'GOOGLE_API_KEY' 的密鑰。如果您的專案需要，請設定它。")
except Exception as e:
    print(f"讀取 GOOGLE_API_KEY 時發生錯誤：{e}")

# --- 主邏輯 ---
def main():
    print("--- 專案首次運行設定 ---")

    # 1. 上傳 ZIP 檔案
    print("\n步驟 1: 上傳專案 ZIP 檔案")
    uploaded_files = files.upload()

    if not uploaded_files:
        print("錯誤：沒有上傳任何檔案。請重新運行儲存格並上傳您的專案 ZIP 檔案。")
        return

    zip_filename = None
    for fn in uploaded_files.keys():
        if fn.endswith('.zip'):
            zip_filename = fn
            break

    if not zip_filename:
        print("錯誤：上傳的檔案中沒有找到 .zip 檔案。請確保您上傳的是 ZIP 壓縮檔。")
        return

    # 將上傳的檔案移至固定路徑
    try:
        shutil.move(zip_filename, COLAB_TEMP_ZIP)
        print(f"成功將 '{zip_filename}' 儲存為 '{COLAB_TEMP_ZIP}'。")
    except Exception as e:
        print(f"移動上傳的 ZIP 檔案時發生錯誤：{e}")
        return

    # 2. 詢問是否掛載 Google Drive
    print("\n步驟 2: Google Drive 設定")
    while True:
        mount_drive_choice = input("是否要掛載 Google Drive 並儲存檔案？(y/n，建議 y): ").strip().lower()
        if mount_drive_choice in ['y', 'n']:
            break
        print("無效的輸入，請輸入 'y' 或 'n'。")

    # 4. 主要流程
    if mount_drive_choice == 'y':
        print("\n--- 處理：掛載 Google Drive 並儲存檔案 ---")
        try:
            drive.mount('/content/drive')
            print("Google Drive 掛載成功。")

            # 建立 Drive 上的目錄
            for dir_path in [DRIVE_PROJECT_BASE_DIR, DRIVE_EXECUTABLE_DIR, DRIVE_COMPRESSED_DIR]:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    print(f"已建立目錄：{dir_path}")

            # 將 ZIP 複製到 Drive
            drive_zip_path = os.path.join(DRIVE_COMPRESSED_DIR, os.path.basename(COLAB_TEMP_ZIP)) # 可改成 'latest_project.zip'
            shutil.copy(COLAB_TEMP_ZIP, drive_zip_path)
            print(f"已將 ZIP 檔案複製到 Google Drive：{drive_zip_path}")

            # 解壓縮到 COLAB_PROJECT_DIR
            if os.path.exists(COLAB_PROJECT_DIR):
                print(f"正在刪除已存在的 Colab 專案目錄：{COLAB_PROJECT_DIR}")
                shutil.rmtree(COLAB_PROJECT_DIR)
            os.makedirs(COLAB_PROJECT_DIR)
            print(f"正在將 '{COLAB_TEMP_ZIP}' 解壓縮到 '{COLAB_PROJECT_DIR}'...")
            with zipfile.ZipFile(COLAB_TEMP_ZIP, 'r') as zip_ref:
                zip_ref.extractall(COLAB_PROJECT_DIR)
            print("解壓縮完成。")

            # 將解壓縮後的內容複製到 DRIVE_EXECUTABLE_DIR
            if os.path.exists(DRIVE_EXECUTABLE_DIR):
                print(f"正在刪除已存在的 Drive 可執行程式碼目錄：{DRIVE_EXECUTABLE_DIR}")
                shutil.rmtree(DRIVE_EXECUTABLE_DIR)
            # shutil.copytree 需要目標目錄不存在，或者在 Python 3.8+ 中使用 dirs_exist_ok=True
            # 為了兼容性，我們先確保它不存在，然後再複製
            shutil.copytree(COLAB_PROJECT_DIR, DRIVE_EXECUTABLE_DIR)
            print(f"已將專案檔案複製到 Google Drive 的可執行目錄：{DRIVE_EXECUTABLE_DIR}")

            print("\n🎉 設定完成！您的專案檔案已成功儲存到 Google Drive。")
            print(f"  - 原始 ZIP 存放於：{drive_zip_path}")
            print(f"  - 可執行的程式碼存放於：{DRIVE_EXECUTABLE_DIR}")
            print("下次運行時，您可以直接使用「後續運行」儲存格從 Google Drive 載入專案。")
            print(f"目前專案也已解壓縮到 Colab 的 '{COLAB_PROJECT_DIR}'，您可以直接在此 Notebook 中執行。")

            # 可選清理 Colab 臨時檔案
            # print(f"正在清理臨時檔案 '{COLAB_TEMP_ZIP}'...")
            # os.remove(COLAB_TEMP_ZIP)
            # print(f"正在清理臨時 Colab 專案目錄 '{COLAB_PROJECT_DIR}'...")
            # shutil.rmtree(COLAB_PROJECT_DIR)
            # print("清理完成。")

        except Exception as e:
            print(f"處理 Google Drive 儲存時發生錯誤：{e}")
            print("請檢查錯誤訊息，並確保您已授權 Colab 存取 Google Drive。")
            print(f"如果問題持續，您可以嘗試選擇不掛載 Drive，或手動在 Drive 中建立 '{DRIVE_PROJECT_BASE_DIR}' 資料夾。")

    else: # 不掛載 Drive
        print("\n--- 處理：僅在本次 Colab 工作階段使用檔案 ---")
        try:
            if os.path.exists(COLAB_PROJECT_DIR):
                print(f"正在刪除已存在的 Colab 專案目錄：{COLAB_PROJECT_DIR}")
                shutil.rmtree(COLAB_PROJECT_DIR)
            os.makedirs(COLAB_PROJECT_DIR)

            print(f"正在將 '{COLAB_TEMP_ZIP}' 解壓縮到 '{COLAB_PROJECT_DIR}'...")
            with zipfile.ZipFile(COLAB_TEMP_ZIP, 'r') as zip_ref:
                zip_ref.extractall(COLAB_PROJECT_DIR)
            print("解壓縮完成。")

            print("\n✅ 設定完成！您的專案檔案已解壓縮到 Colab 的臨時儲存空間。")
            print(f"  - 專案路徑：{COLAB_PROJECT_DIR}")
            print("注意：這些檔案僅存在於本次 Colab 工作階段。如果關閉此 Colab Notebook，檔案將會遺失。")
            print("您可以在此儲存格下方加入執行指令，或在「後續運行」儲存格中選擇重新上傳 ZIP 檔案。")

            # 可選清理
            # print(f"正在清理臨時 ZIP 檔案 '{COLAB_TEMP_ZIP}'...")
            # os.remove(COLAB_TEMP_ZIP)
            # print("清理完成。")

        except Exception as e:
            print(f"解壓縮檔案到 Colab 時發生錯誤：{e}")

if __name__ == "__main__":
    main()
    # 提示：您可以在此處或下一個儲存格中更改工作目錄並執行您的專案
    # 例如：
    # %cd {COLAB_PROJECT_DIR}
    # !python your_main_script.py
```

---

### 2. 後續運行 (載入專案並執行)

此儲存格用於在您完成「首次運行設定」後啟動和執行專案。
*   **如果您在首次設定時選擇了掛載 Google Drive**：此儲存格會嘗試重新掛載 Drive，並將您先前儲存的專案檔案從 Drive 同步到 Colab 環境中，然後您可以執行主要腳本。
*   **如果您在首次設定時選擇了不掛載 Google Drive (或掛載失敗)**：
    *   您可以選擇**重新掛載 Google Drive** (如果首次是因為其他原因失敗，或您改變了主意想使用 Drive)。
    *   或者，您可以選擇**直接在此處上傳專案的 ZIP 檔案**來執行 (檔案僅存在於本次 Colab 工作階段)。
*   此儲存格也會嘗試讀取 `GOOGLE_API_KEY` (如果您的專案需要)。

```python
import os
import shutil
import zipfile
from google.colab import drive, files, userdata

# --- 配置路徑 (與「首次運行」儲存格一致) ---
# Colab 中解壓縮和執行的路徑
COLAB_PROJECT_DIR = '/content/project_code'
# Colab 中臨時存放上傳 ZIP 的路徑 (用於重新上傳的情況)
COLAB_TEMP_ZIP = '/content/uploaded_project.zip'
# 使用者 Drive 中的專案基礎路行
DRIVE_PROJECT_BASE_DIR = '/content/drive/MyDrive/MyProject' # 請確保與首次運行設定一致
# Drive 中存放解壓縮後可執行程式碼的路徑
DRIVE_EXECUTABLE_DIR = os.path.join(DRIVE_PROJECT_BASE_DIR, 'executable_code')

# --- GOOGLE_API_KEY 相關 ---
GOOGLE_API_KEY = None
try:
    GOOGLE_API_KEY = userdata.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        print("成功讀取 GOOGLE_API_KEY。")
    else:
        print("警告：未在 Colab 密鑰中找到 GOOGLE_API_KEY。如果您的專案需要，請設定它。")
except userdata.SecretNotFoundError:
    print("警告：未在 Colab 密鑰中找到名為 'GOOGLE_API_KEY' 的密鑰。如果您的專案需要，請設定它。")
except Exception as e:
    print(f"讀取 GOOGLE_API_KEY 時發生錯誤：{e}")

# --- 主邏輯 ---
def main():
    print("--- 專案後續運行 ---")

    # 1. 詢問使用者操作模式
    print("\n步驟 1: 選擇專案載入方式")
    while True:
        load_choice = input("您希望如何載入專案？\n"
                            "  (1) 從 Google Drive 同步 (如果您在首次設定時已儲存到 Drive)\n"
                            "  (2) 重新上傳 ZIP 檔案 (若未使用 Drive 或 Drive 同步失敗)\n"
                            "請輸入選項 (1 或 2): ").strip()
        if load_choice in ['1', '2']:
            break
        print("無效的輸入，請輸入 '1' 或 '2'。")

    # 3. 主要流程
    project_ready_for_execution = False

    if load_choice == '1':
        print("\n--- 處理：從 Google Drive 同步 ---")
        try:
            print("正在嘗試掛載 Google Drive...")
            drive.mount('/content/drive', force_remount=True)
            print("Google Drive 掛載成功。")

            if os.path.exists(DRIVE_EXECUTABLE_DIR) and os.listdir(DRIVE_EXECUTABLE_DIR):
                print(f"在 Google Drive 中找到專案檔案：{DRIVE_EXECUTABLE_DIR}")

                if os.path.exists(COLAB_PROJECT_DIR):
                    print(f"正在刪除已存在的 Colab 專案目錄：{COLAB_PROJECT_DIR}")
                    shutil.rmtree(COLAB_PROJECT_DIR)
                # os.makedirs(COLAB_PROJECT_DIR) # copytree 會自動建立目標目錄

                print(f"正在將專案檔案從 Drive 的 '{DRIVE_EXECUTABLE_DIR}' 同步到 Colab 的 '{COLAB_PROJECT_DIR}'...")
                shutil.copytree(DRIVE_EXECUTABLE_DIR, COLAB_PROJECT_DIR)
                print("專案檔案同步完成。")
                project_ready_for_execution = True
            else:
                print(f"錯誤：在 Google Drive 的 '{DRIVE_EXECUTABLE_DIR}' 中找不到專案檔案或該目錄為空。")
                print("請確認您是否已成功執行「首次運行設定」並將檔案儲存到 Drive。")
                print("或者，您可以選擇「重新上傳 ZIP 檔案」的選項。")

        except Exception as e:
            print(f"從 Google Drive 同步時發生錯誤：{e}")
            print("請檢查錯誤訊息，並確保您已授權 Colab 存取 Google Drive。")
            print("如果問題持續，您可以嘗試選擇「重新上傳 ZIP 檔案」。")

    elif load_choice == '2':
        print("\n--- 處理：重新上傳 ZIP 檔案 ---")
        print("請上傳您的專案 ZIP 檔案。")
        uploaded_files = files.upload()

        if not uploaded_files:
            print("錯誤：沒有上傳任何檔案。請重新運行儲存格並上傳您的專案 ZIP 檔案。")
            return # 提早結束 main 函數

        zip_filename = None
        for fn in uploaded_files.keys():
            if fn.endswith('.zip'):
                zip_filename = fn
                break

        if not zip_filename:
            print("錯誤：上傳的檔案中沒有找到 .zip 檔案。請確保您上傳的是 ZIP 壓縮檔。")
            return # 提早結束 main 函數

        try:
            # 將上傳的檔案移至固定路徑
            if os.path.exists(COLAB_TEMP_ZIP):
                 os.remove(COLAB_TEMP_ZIP)
            shutil.move(zip_filename, COLAB_TEMP_ZIP)
            print(f"成功將 '{zip_filename}' 儲存為 '{COLAB_TEMP_ZIP}'。")

            if os.path.exists(COLAB_PROJECT_DIR):
                print(f"正在刪除已存在的 Colab 專案目錄：{COLAB_PROJECT_DIR}")
                shutil.rmtree(COLAB_PROJECT_DIR)
            os.makedirs(COLAB_PROJECT_DIR)

            print(f"正在將 '{COLAB_TEMP_ZIP}' 解壓縮到 '{COLAB_PROJECT_DIR}'...")
            with zipfile.ZipFile(COLAB_TEMP_ZIP, 'r') as zip_ref:
                zip_ref.extractall(COLAB_PROJECT_DIR)
            print("解壓縮完成。")

            print("\n✅ 專案檔案已解壓縮到 Colab 的臨時儲存空間。")
            print(f"  - 專案路徑：{COLAB_PROJECT_DIR}")
            print("注意：這些檔案僅存在於本次 Colab 工作階段。如果關閉此 Colab Notebook，檔案將會遺失。")
            project_ready_for_execution = True

            # 可選清理
            # print(f"正在清理臨時 ZIP 檔案 '{COLAB_TEMP_ZIP}'...")
            # os.remove(COLAB_TEMP_ZIP)
            # print("清理完成。")

        except Exception as e:
            print(f"處理上傳的 ZIP 檔案時發生錯誤：{e}")

    else: # 理論上不會執行到這裡，因為前面有檢查
        print("錯誤：無效的選擇。")

    # 4. 提供執行主要腳本的指示區塊
    if project_ready_for_execution:
        print(f"\n--- 執行專案 ---")
        print(f"專案檔案已準備就緒於：{COLAB_PROJECT_DIR}")
        print("您現在可以執行您的主要腳本。請取消註解並修改以下指令以符合您的專案：")
        print(f"# %cd {COLAB_PROJECT_DIR}")
        print("# !ls -l # 查看專案根目錄下的檔案")
        print("# !python your_main_script.py your_arguments")
        print("# 或者使用 %run your_main_script.py your_arguments")
        print("\n提示：如果您的專案有特定的 Python 虛擬環境或依賴項，請確保在此儲存格或後續儲存格中進行設定。")
    else:
        print("\n--- 專案未準備就緒 ---")
        print("由於上述錯誤，專案未能成功載入。請檢查錯誤訊息並重試。")

if __name__ == "__main__":
    main()
```

---

## 額外說明

### Google Drive 的重要性

強烈建議您在「首次運行設定」時選擇將專案儲存到 Google Drive。這樣做有以下好處：

*   **持久化儲存**：您的專案檔案（包括上傳的 ZIP 和解壓縮後的程式碼）將安全地儲存在您的 Google Drive 中，不會因為 Colab 工作階段結束而消失。
*   **避免重複上傳**：下次運行專案時，您可以直接從 Google Drive 同步檔案，無需再次上傳體積可能較大的 ZIP 檔案。
*   **版本控制（間接）**：您可以將不同版本的 ZIP 檔案儲存在 Drive 的 `compressed_zips` 資料夾中。
*   **方便性**：一旦設定完成，後續運行將更加便捷。

**路徑自訂**：
在 Python 程式碼中，Google Drive 的基礎路徑預設為 `/content/drive/MyDrive/MyProject`。您可以將 `MyProject` 修改為您偏好的任何資料夾名稱。
**重要**：如果您修改此路徑，請確保在「首次運行設定」和「後續運行」兩個儲存格的 Python 程式碼中都進行相同的修改，以確保路徑一致性。

### API 金鑰設定 (GOOGLE_API_KEY)

這兩個 Colab 儲存格中的程式碼都會嘗試讀取名為 `GOOGLE_API_KEY` 的密鑰。這是為了方便那些需要使用 Google API (例如 Gemini API, Google Cloud APIs 等) 的專案。

**如何設定 `GOOGLE_API_KEY`：**

1.  在 Colab Notebook 的介面中，點擊左側工具欄的「鑰匙」圖示（密鑰）。
2.  點擊「新增密鑰」。
3.  在「名稱」欄位中輸入 `GOOGLE_API_KEY`。
4.  在「值」欄位中貼上您的 API 金鑰。
5.  開啟「筆記本存取權」的切換按鈕，以允許此 Notebook 存取該密鑰。
6.  完成後關閉密鑰面板。

**如果您的專案不需要 API 金鑰**：
您可以安全地忽略程式碼輸出中關於 `GOOGLE_API_KEY` 的警告訊息。這些訊息僅為提示，不會影響不需要 API 金鑰的專案的正常運行。

### 如何執行主要腳本

在「後續運行」儲存格成功載入您的專案檔案後 (無論是從 Drive 同步還是重新上傳)，專案檔案將位於 Colab 環境的 `/content/project_code` 目錄下。

儲存格的末尾會提供類似以下的指示性註解：

```python
# %cd /content/project_code
# !ls -l # 查看專案根目錄下的檔案
# !python your_main_script.py your_arguments
# 或者使用 %run your_main_script.py your_arguments
```

您需要根據您的專案進行修改：

1.  **`%cd /content/project_code`**：這行指令會將 Colab 的目前工作目錄更改到您的專案根目錄。通常建議執行此操作。
2.  **`!ls -l`**：(可選) 這行指令可以列出專案根目錄下的檔案和資料夾，幫助您確認檔案結構是否正確。
3.  **`!python your_main_script.py your_arguments`**：
    *   將 `your_main_script.py` 替換為您專案中主要的 Python 執行腳本的實際名稱 (例如 `main.py`, `app.py` 等)。
    *   如果您的腳本需要命令列參數，請在腳本名稱後面加上這些參數 (例如 `!python train.py --epochs 10 --batch_size 32`)。
4.  **`%run your_main_script.py your_arguments`**：這是另一種執行 Python 腳本的方式，與 `!python` 類似。在某些情況下，`%run` 可能更適合 Colab 環境，例如當腳本中定義的變數需要在儲存格結束後仍然可被存取時。

選擇適合您專案的執行指令，取消註解並修改它。

### 疑難排解 / 注意事項

*   **ZIP 檔案格式**：請確保您上傳的是標準的 `.zip` 格式壓縮檔。其他壓縮格式 (如 `.rar`, `.7z`) 將無法被正確解壓縮。ZIP 檔案應包含您專案的所有必要檔案和資料夾。
*   **檔案上傳大小限制**：Colab 的 `files.upload()` 功能對於單一檔案上傳可能有大小限制 (通常在幾十 MB 到幾百 MB 之間，具體取決于當時的 Colab 資源狀況)。如果您的專案非常大，建議優先使用 Google Drive 進行同步。
*   **Google Drive 空間**：確保您的 Google Drive 有足夠的空間來儲存您的專案 ZIP 檔案和解壓縮後的程式碼。
*   **Colab 工作階段儲存**：任何不儲存到 Google Drive 的檔案 (例如選擇不掛載 Drive 時，或在 Colab 環境中手動建立的檔案) 都會在 Colab 工作階段結束後被清除。
*   **首次設定的重要性**：即使您打算主要透過重新上傳 ZIP 的方式運行，也建議至少完整執行一次「首次運行設定」並選擇一次掛載 Drive。這有助於在您的 Drive 中建立標準化的資料夾結構 (`MyProject/executable_code`, `MyProject/compressed_zips`)，方便未來管理。
*   **錯誤訊息**：請仔細閱讀儲存格輸出中的任何錯誤訊息。它們通常會提供解決問題的線索。

---

希望本指南能幫助您順利在 Colab 中運行您的專案！
