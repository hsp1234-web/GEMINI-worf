#專案說明
本專案旨在分析社群媒體貼文和財務數據，以產生月度報告。

#下載與設定指南

## 1. 下載專案
您可以從 GitHub 下載本專案的 ZIP 檔案。

## 2. 在 Google Colab 中上傳與解壓縮
   - 將下載的 ZIP 檔案上傳到您的 Google Colab 環境。
   - 使用以下指令解壓縮檔案：
     ```bash
     !unzip 專案檔案名稱.zip
     ```

## 3. 設定 API 金鑰
   - 在 Google Colab 左側面板中找到「Secrets」分頁。
   - 設定 `GEMINI_API_KEY`。請注意，您需要自行取得此 API 金鑰。
   - 根據您需要使用的功能，可能還需要設定 `FRED_API_KEY` 和 `FINMIND_API_KEY`。如果使用到這些功能，請同樣在 Colab Secrets 中新增這些金鑰。這些金鑰也需要您自行取得。

## 4. 執行程式
   - 開啟 Colab 的終端機。
   - 使用以下指令執行程式：
     ```bash
     python src/jules_interaction.py
     ```

# 注意事項
- 請確保您已依照指示正確設定所有必要的 API 金鑰。
- 某些功能可能需要特定的 Python 套件，請依照錯誤訊息提示安裝相關依賴。

# Project Description
This project analyzes social media posts and financial data to generate monthly reports.

# Download and Setup Guide

## 1. Download the Project
You can download the project as a ZIP file from GitHub.

## 2. Upload and Unzip in Google Colab
   - Upload the downloaded ZIP file to your Google Colab environment.
   - Use the following command to unzip the file:
     ```bash
     !unzip project_filename.zip
     ```

## 3. Set API Keys
   - Find the "Secrets" tab in the left panel of Google Colab.
   - Set the `GEMINI_API_KEY`. Please note that you need to obtain this API key yourself.
   - Depending on the functionality you intend to use, you might also need to set `FRED_API_KEY` and `FINMIND_API_KEY`. If these features are used, please add these keys to Colab Secrets as well. You also need to obtain these keys yourself.

## 4. Run the Program
   - Open the Colab terminal.
   - Use the following command to run the program:
     ```bash
     python src/jules_interaction.py
     ```

# Notes
- Please ensure you have correctly set all necessary API keys as instructed.
- Some features may require specific Python packages. Please install any relevant dependencies based on error messages.
