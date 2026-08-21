#!/bin/bash
# ============================================================
# Day18 方案C：UI 测试本地一键运行脚本（Linux / macOS / Git-Bash）
# 用途：运行全量 UI 测试 -> 生成 Allure 报告 -> 保留历史趋势 -> 打开报告
# Windows 原生环境请用 run_ui_tests.bat
# ============================================================
set -u
cd "$(dirname "$0")"

# Python 可执行文件：Windows venv 为 Scripts，Linux/macOS 为 bin
PYBIN=".venv/bin/python"
[ -f ".venv/Scripts/python.exe" ] && PYBIN=".venv/Scripts/python.exe"

if [ ! -x "$PYBIN" ]; then
    echo "[错误] 未找到虚拟环境 $PYBIN，请先按 README 初始化"
    exit 1
fi
if [ ! -f ".env" ]; then
    echo "[错误] 未找到 .env（BASE_URL / 测试账号），请参照 .env.example 创建"
    exit 1
fi

echo "[1/4] 保留上一次报告的 history（Allure 趋势连续）"
if [ -d "allure-report/history" ]; then
    mkdir -p allure-results
    cp -r allure-report/history allure-results/
    echo "     已保留历史趋势数据"
else
    echo "     首次运行，无历史数据可保留"
fi

echo "[2/4] 运行全量 UI 测试（headless；偶发超时/网络波动自动重试 1 次，约 105s）"
"$PYBIN" -m pytest testcases/
PYTEST_EXIT=$?

echo "[3/4] 生成 Allure 报告（allure-results -> allure-report）"
if command -v allure >/dev/null 2>&1; then
    allure generate allure-results -o allure-report --clean
else
    echo "[警告] 未找到 allure CLI，跳过报告生成（测试结果仍保留在 allure-results/）"
fi

echo "[4/4] 打开报告（Allure 为 SPA，需本地 HTTP 服务；占用端口 8123）"
python3 -m http.server 8123 --directory allure-report >/dev/null 2>&1 &
SERVER_PID=$!
sleep 2
case "$(uname -s)" in
    Darwin) open "http://localhost:8123" ;;
    Linux)  xdg-open "http://localhost:8123" >/dev/null 2>&1 || true ;;
    *)      echo "     报告地址: http://localhost:8123" ;;
esac
echo "     （HTTP 服务 PID $SERVER_PID，停止: kill $SERVER_PID）"

echo
if [ "$PYTEST_EXIT" = "0" ]; then
    echo "============ 全量 UI 测试通过 ============"
else
    echo "============ 测试存在失败，详见上方输出与报告 ============"
fi
exit "$PYTEST_EXIT"
