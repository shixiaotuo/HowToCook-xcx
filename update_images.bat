@echo off
chcp 65001 >nul
REM ============================================================
REM  一键更新菜谱图片（绕开 GitHub LFS 额度限制）
REM  用法：直接双击运行；或拖入/传入本地仓库的 dishes 目录
REM    例：update_images.bat "D:\tmp\111\HowToCook\dishes"
REM  不传参则自动探测常见路径。
REM ============================================================
setlocal
cd /d "%~dp0"

REM 选 Python 解释器
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )
if not defined PY ( where python3 >nul 2>&1 && set "PY=python3" )
if not defined PY (
  echo [!] 未找到 Python。请先安装 Python 3.9+ 并勾选 "Add to PATH"。
  pause
  exit /b 1
)
echo [*] 使用 Python：%PY%

REM 运行更新脚本（传入 dishes 目录参数，若拖入则 %1 非空）
if "%~1"=="" (
  %PY% scripts/update_images.py
) else (
  %PY% scripts/update_images.py "%~1"
)

echo.
echo [*] 完成。按任意键关闭。
pause >nul
endlocal
