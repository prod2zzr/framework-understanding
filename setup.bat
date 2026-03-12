@echo off
chcp 65001 >nul
echo ============================================
echo   HR花名册智能匹配系统 - 环境配置
echo ============================================
echo.

:: Step 1: Check Python
echo [1/4] 检测 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       未检测到 Python，尝试自动安装...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  !! 自动安装失败，请手动安装 Python:
        echo     下载地址: https://www.python.org/downloads/
        echo     安装时请勾选 "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
    echo       Python 安装完成，请关闭此窗口并重新运行 setup.bat
    pause
    exit /b 0
)
for /f "tokens=*" %%i in ('python --version') do echo       %%i 已安装

:: Step 2: Create virtual environment
echo.
echo [2/4] 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo       虚拟环境已创建
) else (
    echo       虚拟环境已存在，跳过
)

:: Step 3: Install dependencies
echo.
echo [3/4] 安装项目依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo  !! 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo       依赖安装完成

:: Step 4: Configure .env
echo.
echo [4/4] 配置 API Key...
if not exist ".env" (
    copy .env.example .env >nul
    echo       已创建 .env 配置文件
    echo.
    echo  !! 重要：请用记事本打开 .env 文件，填入你的 OpenRouter API Key
    echo     获取地址: https://openrouter.ai/keys
    echo.
    notepad .env
) else (
    echo       .env 配置文件已存在，跳过
)

echo.
echo ============================================
echo   配置完成！双击 start.bat 启动应用
echo ============================================
pause
