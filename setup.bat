@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════╗
echo ║   HR花名册智能匹配系统 - 环境配置         ║
echo ╚════════════════════════════════════════════╝
echo.

:: Step 1: Check Python
echo [□□□□] [1/4] 检测 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo         未检测到 Python，尝试从内置安装包安装...
    :: Try built-in installer first
    if exist "tools\python-3.11.9-amd64.exe" (
        echo         找到内置安装包，正在安装...
        tools\python-3.11.9-amd64.exe /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
        if %errorlevel% neq 0 (
            echo  !! 安装失败，请手动双击 tools\python-3.11.9-amd64.exe 安装
            pause
            exit /b 1
        )
        echo         Python 安装完成，请关闭此窗口并重新运行 setup.bat
        pause
        exit /b 0
    )
    :: No built-in installer, try winget
    echo         未找到内置安装包，尝试在线安装...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  !! 自动安装失败，请手动下载 Python 安装包:
        echo     国内镜像: https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-amd64.exe
        echo     官方地址: https://www.python.org/downloads/
        echo.
        echo     方式一：下载后放入本项目 tools\ 文件夹，重新运行 setup.bat
        echo     方式二：直接双击安装包安装（请勾选 Add Python to PATH）
        echo.
        pause
        exit /b 1
    )
    echo         Python 安装完成，请关闭此窗口并重新运行 setup.bat
    pause
    exit /b 0
)
for /f "tokens=*" %%i in ('python --version') do echo [■□□□] [1/4] %%i 已安装 ✓

:: Step 2: Create virtual environment
echo.
echo [■□□□] [2/4] 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo [■■□□] [2/4] 虚拟环境已创建 ✓
) else (
    echo [■■□□] [2/4] 虚拟环境已存在 ✓
)

:: Step 3: Install dependencies (using China mirror)
echo.
echo [■■□□] [3/4] 安装项目依赖（使用国内镜像源）...
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --progress-bar on -q
if %errorlevel% neq 0 (
    echo         国内镜像失败，尝试默认源...
    pip install -r requirements.txt --progress-bar on -q
    if %errorlevel% neq 0 (
        echo  !! 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)
echo [■■■□] [3/4] 依赖安装完成 ✓

:: Step 4: Ensure data directory exists
echo.
echo [■■■□] [4/4] 准备数据目录...
if not exist "data" mkdir data
echo [■■■■] [4/4] data\ 目录已就绪 ✓

echo.
echo ╔════════════════════════════════════════════╗
echo ║              配置完成！                    ║
echo ╠════════════════════════════════════════════╣
echo ║                                            ║
echo ║  使用步骤:                                 ║
echo ║  1. 将花名册文件放入 data\ 文件夹          ║
echo ║     支持: .xlsx .xls .et(WPS) .csv         ║
echo ║  2. 双击 start.bat 启动应用                ║
echo ║  3. 首次使用在网页输入 API Key（自动保存） ║
echo ║     获取: https://openrouter.ai/keys       ║
echo ║                                            ║
echo ╚════════════════════════════════════════════╝
pause
