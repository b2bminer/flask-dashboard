@echo off
setlocal enabledelayedexpansion

echo > git_error_log.txt

echo Starting test add...
echo.

for %%f in (templates\*) do (
    echo Trying: %%f
    git add "%%f" 2>>git_error_log.txt
    if errorlevel 1 (
        echo ERROR adding %%f >> git_error_log.txt
    )
)

echo.
echo Done.

echo --------------------------------------
echo Files that caused errors:
type git_error_log.txt
echo --------------------------------------

echo Finished.
pause
