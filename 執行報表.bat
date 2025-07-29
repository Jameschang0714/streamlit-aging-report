REM 將當前目錄切換到批次檔所在的目錄
cd /d %~dp0

echo =====================================================
echo. 
echo      正在啟動租賃案件帳齡追蹤報表...
echo. 
echo      請稍候，瀏覽器將會自動開啟報表頁面。
echo. 
echo      (您可以隨時關閉此視窗來停止報表伺服器)
echo. 
echo =====================================================

echo 準備執行 Streamlit 應用程式...

REM 使用系統PATH中的Python來啟動Streamlit應用
start "" python -m streamlit run dashboard.py > NUL 2>&1

echo Streamlit 應用程式執行完畢或發生錯誤。

pause
