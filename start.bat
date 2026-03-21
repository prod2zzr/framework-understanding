@echo off
chcp 65001 >nul
echo ============================================
echo   HR花名册智能匹配系统 - 启动中...
echo ============================================
echo.

:: Check venv exists
if not exist "venv\Scripts\activate.bat" (
    echo  !! 未找到虚拟环境，请先运行 setup.bat
    pause
    exit /b 1
)

:: Activate venv
call venv\Scripts\activate.bat

:: Start Streamlit
echo  启动应用，浏览器将自动打开...
echo  关闭此窗口可停止应用
echo.
streamlit run hr_matching/app.py
