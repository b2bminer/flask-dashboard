@echo off
setlocal enabledelayedexpansion

echo > git_error_log.txt

echo Starting one-by-one test add + commit...
echo.

for %%f in (templates\*) do (
    echo -----------------------------------------
    echo Trying: %%f

    git add "%%f" 2>>git_error_log.txt
    if errorlevel 1 (
        echo ERROR adding %%f >> git_error_log.txt
        echo Failed at add step. Skipping...
        git reset HEAD --hard >nul
        goto :continue
    )

    git commit -m "Add %%f" 2>>git_error_log.txt
    if errorlevel 1 (
        echo ERROR committing %%f >> git_error_log.txt
        echo Failed at commit step. Undoing...
        git reset HEAD --hard >nul
    )

    :continue
)

echo.
echo -----------------------------------------
echo Finished testing.
echo These files had problems:
type git_error_log.txt
echo -----------------------------------------

pause
