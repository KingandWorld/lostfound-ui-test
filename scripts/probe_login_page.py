"""登录页行为探测脚本（Day15 开发用）：确认真实元素与行为，结果回填到用例与手册。

用途（探测结果已写入 testcases/test_login_ui.py 与 week3_day15 手册）：
    - 登录页 URL、输入框 placeholder、按钮/链接文本；
    - 正确账号登录后的跳转目标（管理员 /back/dashboard vs 普通用户 /）；
    - localStorage 是否写入 token；/api/user/current 是否返回 email 字段（邮箱登录用）；
    - 错误密码的提示文案（含"还剩 N 次尝试机会"）；
    - 空表单的前端校验提示（.el-form-item__error）。

用法：
    .venv\\Scripts\\python.exe scripts\\probe_login_page.py

注意：错误密码探测会给真实账号的失败计数 +1（连续 5 次触发 15 分钟锁定），
    本脚本探测一次即收手；锁定不影响宽断言（见测试用例注释）。
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
USERNAME = os.getenv("TEST_USERNAME")
PASSWORD = os.getenv("TEST_PASSWORD")

LOGIN_URL = f"{BASE_URL}/login"


def _dump(page, tag: str):
    """打印页面输入框/按钮/链接清单，确认选择器。"""
    print(f"\n=== [{tag}] ===")
    for i, el in enumerate(page.locator("input").all()):
        print(f"input[{i}]: type={el.get_attribute('type')} "
              f"placeholder={el.get_attribute('placeholder')!r} visible={el.is_visible()}")
    for i, el in enumerate(page.locator("button").all()):
        print(f"button[{i}]: text={el.inner_text()!r} visible={el.is_visible()}")
    for i, el in enumerate(page.locator("a").all()):
        print(f"a[{i}]: text={el.inner_text()!r} href={el.get_attribute('href')}")


def main() -> int:
    with sync_playwright() as p:
        # --proxy-server=direct://：本机系统代理（127.0.0.1:7890）未启动时会
        # net::ERR_PROXY_CONNECTION_FAILED（--no-proxy-server 实测无效，direct 有效）；
        # 目标站点为公网服务器可直接访问
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])

        # 1. 登录页结构
        page = browser.new_page(locale="zh-CN")
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30_000)
        print(f"[1] 登录页 URL: {page.url}")
        _dump(page, "登录页元素")

        # 2. 正确账号登录 → 跳转目标 + token + 用户信息（含 email 字段）
        page.fill("input[placeholder='请输入用户名或邮箱']", USERNAME)
        page.fill("input[placeholder='请输入密码']", PASSWORD)
        page.click("button:has-text('登录')")
        try:
            page.wait_for_url("**/login", wait_until="load", timeout=8_000) is not None
        except Exception:
            pass
        page.wait_for_timeout(2_500)
        print(f"\n[2] 登录后 URL: {page.url}")
        token = page.evaluate("localStorage.getItem('token')")
        print(f"[2] localStorage token 非空: {bool(token)}")
        if token:
            data = page.evaluate(
                """async (token) => {
                    const resp = await fetch('/api/user/current', {headers: {'token': token}});
                    return await resp.json();
                }""",
                token,
            )
            print(f"[2] /api/user/current: {json.dumps(data, ensure_ascii=False)[:600]}")
        # 登录页截图（有头模式运行截图归档用）
        page.screenshot(path="screenshots/probe_login_success.png", full_page=True)

        # 3. 错误密码 → 提示文案（真实账号失败计数 +1，探测一次即收手）
        page2 = browser.new_page(locale="zh-CN")
        page2.goto(LOGIN_URL, wait_until="networkidle", timeout=30_000)
        page2.fill("input[placeholder='请输入用户名或邮箱']", USERNAME)
        page2.fill("input[placeholder='请输入密码']", "WrongPass_Probe_999")
        page2.click("button:has-text('登录')")
        page2.wait_for_timeout(1_500)
        errs = page2.locator(".el-message--error").all()
        print(f"\n[3] 错误密码提示条数: {len(errs)}")
        for e in errs:
            print(f"[3] 提示内容: {e.inner_text()!r}")
        print(f"[3] 验证码区域 .captcha-row 数量: {page2.locator('.captcha-row').count()}")

        # 4. 空表单 → 前端校验提示
        page3 = browser.new_page(locale="zh-CN")
        page3.goto(LOGIN_URL, wait_until="networkidle", timeout=30_000)
        page3.click("button:has-text('登录')")
        page3.wait_for_timeout(1_200)
        items = page3.locator(".el-form-item__error").all()
        print(f"\n[4] 空表单校验提示条数: {len(items)}")
        for it in items:
            print(f"[4] 提示内容: {it.inner_text()!r}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
