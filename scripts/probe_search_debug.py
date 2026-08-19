"""Day16 列表页搜索失败根因探测：监控点搜索按钮后的网络请求（开发用，不入库）。"""

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

        # 登录
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", USERNAME)
        page.fill("input[placeholder='请输入密码']", PASSWORD)
        page.click("button:has-text('登录')")
        page.wait_for_url("**/", timeout=15_000)

        # 场景 1: 列表页加载
        requests.clear()
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        print(f"场景1 列表加载: .el-card={page.locator('.el-card').count()}")
        for r in requests:
            print(f"  REQ {r}")
        requests.clear()

        # 场景 2: 输入"学生证"后点搜索
        page.locator("input[placeholder*='标题']").fill("学生证")
        page.wait_for_timeout(800)
        print(f"\n场景2 fill 后 URL: {page.url}")
        page.locator("button:has-text('搜索')").first.click()
        page.wait_for_timeout(1500)
        print(f"点搜索后 URL: {page.url}  .el-card={page.locator('.el-card').count()}")
        for r in requests:
            print(f"  REQ {r}")
        requests.clear()

        # 场景 3: 重置按钮
        page.locator("button:has-text('重置')").first.click()
        page.wait_for_timeout(1500)
        print(f"\n场景3 重置后 URL: {page.url}  .el-card={page.locator('.el-card').count()}")
        for r in requests:
            print(f"  REQ {r}")

        # 场景 4: 重新导航列表页（验证数据仍在）
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        print(f"\n场景4 重新导航后 .el-card={page.locator('.el-card').count()}")
        cards = [c.inner_text()[:40].replace("\n", "|") for c in page.locator(".el-card").all()[:3]]
        print(f"  前 3 张卡片: {cards}")

        browser.close()
    print("\n探测完成")


if __name__ == "__main__":
    main()
