@echo off
echo ====================================================
echo Setting up LOCAL Windows Test Environment (Python 3.8)
echo ====================================================

:: Check if mamba or conda is installed and available in PATH
where mamba >nul 2>nul
if %errorlevel% equ 0 (
    set CONDA_CMD=mamba
    echo Found 'mamba' package manager. Using it for faster setup!
) else (
    where conda >nul 2>nul
    if %errorlevel% equ 0 (
        set CONDA_CMD=conda
        echo Using standard 'conda' package manager.
    ) else (
        echo [ERROR] Neither 'mamba' nor 'conda' commands were found.
        echo Please make sure Miniforge is installed and registered in your PATH,
        echo or run this script from the "Miniforge Prompt" / "Anaconda Prompt".
        echo.
        echo You can download Miniforge for Windows from:
        echo https://github.com/conda-forge/miniforge#miniforge3
        pause
        exit /b 1
    )
)

echo.
echo [1/3] Checking if Conda environment 'smart_cafeteria' already exists...
call %CONDA_CMD% info --envs | findstr /I "smart_cafeteria" >nul
if %errorlevel% equ 0 (
    echo Environment 'smart_cafeteria' already exists. Skipping environment creation.
) else (
    echo Creating environment 'smart_cafeteria' with Python 3.8 using %CONDA_CMD%...
    call %CONDA_CMD% create -y -n smart_cafeteria python=3.8
)

echo.
echo [2/3] Installing required libraries from requirements.txt in environment...
:: Using '%CONDA_CMD% run' executes the command inside the environment without needing to activate it in this script.
call %CONDA_CMD% run -n smart_cafeteria pip install -r requirements.txt

echo.
echo [3/3] Verifying the environment with local simulation...
call %CONDA_CMD% run -n smart_cafeteria python smart_cafeteria\nodes\llm_test_publisher.py --local

echo ====================================================
echo Local test environment setup completed successfully!
echo To activate this environment in your terminal, run:
echo     %CONDA_CMD% activate smart_cafeteria
echo ====================================================
pause
