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
