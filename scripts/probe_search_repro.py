"""Day16 搜索失败精确复现：按 lost_list_page.search() 完全相同的步骤逐步打印状态（开发用，不入库）。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
USERNAME = os.getenv("TEST_USERNAME")
PASSWORD = os.getenv("TEST_PASSWORD")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = ctx.new_page()

        requests = []
        page.on("request", lambda r: requests.append(f"{r.method} {r.url}"))

        # 与 logged_in_page fixture 完全一致：登录
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", USERNAME)
        page.fill("input[placeholder='请输入密码']", PASSWORD)
        page.click("button:has-text('登录')")
        page.wait_for_url("**/", timeout=15_000)
        page.wait_for_load_state()
        print(f"登录后 URL: {page.url}  token: {bool(page.evaluate('localStorage.getItem(\"token\")'))}")

        # 与 lost_list_page.go() 一致
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        print(f"navigate 后 URL: {page.url}  .el-card={page.locator('.el-card').count()}")
        requests.clear()

        # 与 search() 一致
        keyword = "学生证"
        page.locator("input[placeholder*='标题']").fill(keyword)
        print(f"fill 后 URL: {page.url}")
        input_value = page.locator("input[placeholder*='标题']").input_value()
        print(f"fill 后输入框值: '{input_value}'")
        page.wait_for_load_state("networkidle")
        print(f"fill 后 networkidle 返回, URL: {page.url}")
        page.wait_for_timeout(600)
        title_input = page.locator("input[placeholder*='标题']").first
        print(f"600ms 后输入框值: '{title_input.input_value()}'")
        page.locator("button:has-text('搜索')").first.click()
        print(f"点击搜索后 URL: {page.url}")
        page.wait_for_load_state("networkidle")
        print(f"点击后 networkidle 返回, .el-card={page.locator('.el-card').count()}")
        for r in requests:
            print(f"  REQ {r}")
        print(f"列表文本: {[c.inner_text()[:60].replace(chr(10), '|') for c in page.locator('.el-card').all()[:3]]}")

        browser.close()
    print("\n复现完成")


if __name__ == "__main__":
    main()
