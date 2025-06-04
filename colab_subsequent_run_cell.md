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
