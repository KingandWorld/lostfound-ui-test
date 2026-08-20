"""枚举列表页所有卡片与状态（Day17，2026-08-20）：统计可认领候选池。"""

import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def probe():
    print("== 列表页卡片枚举 ==")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", TEST_USERNAME)
        page.fill("input[placeholder='请输入密码']", TEST_PASSWORD)
        page.locator("button:has-text('登录')").click()
        page.wait_for_url("**/", timeout=15_000)

        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        cards = page.locator(".el-card")
        print(f"第 1 页卡片数: {cards.count()}")
        pending = 0
        for i in range(cards.count()):
            t = "|".join(x.strip() for x in cards.nth(i).inner_text().splitlines() if x.strip())
            print(f"  [{i}] {t}")
            if "待认领" in t:
                pending += 1
        print(f"待认领卡片数: {pending}")

        # 第 2 页
        next_btn = page.locator(".btn-next")
        if next_btn.is_enabled():
            next_btn.click()
            page.wait_for_timeout(1500)
            cards2 = page.locator(".el-card")
            print(f"第 2 页卡片数: {cards2.count()}")
            for i in range(cards2.count()):
                t = "|".join(x.strip() for x in cards2.nth(i).inner_text().splitlines() if x.strip())
                print(f"  [{i}] {t}")
        browser.close()
    print("== 完成 ==")


if __name__ == "__main__":
    probe()
