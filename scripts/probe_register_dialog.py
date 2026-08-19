"""Day16 注册协议 dialog 最后探测 v7：header X 关闭路径（开发用，不入库）。"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = ctx.new_page()
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")

        # 链路 A：checkbox → 等 dialog → header X 关闭 → 注册
        print("===== 链路 A: checkbox → header X 关闭 → 注册 =====")
        page.locator(".el-checkbox__inner").click()
        page.wait_for_timeout(1500)
        close_x = page.locator(".el-overlay-dialog .el-dialog__headerbtn")
        print(f"header X 数量: {close_x.count()}")
        if close_x.count():
            close_x.first.click()
            page.wait_for_timeout(1000)
        print(f"关闭后 dialog: {page.locator('.el-overlay-dialog').count()}")
        checked = page.locator(".el-checkbox").first.evaluate(
            "el => el.classList.contains('is-checked')")
        print(f"关闭后 checked: {checked}")
        if checked and page.locator(".el-overlay-dialog").count() == 0:
            stamp = str(int(time.time() * 1000))
            page.locator("input[placeholder='用户名']").fill(f"uitest7a_{stamp}")
            page.locator("input[placeholder='真实姓名']").fill("X关闭用户")
            page.locator("input[placeholder='邮箱地址']").fill(f"uitest7a_{stamp}@example.com")
            page.locator("input[placeholder='设置密码']").fill("Test123456")
            page.locator("input[placeholder='确认密码']").fill("Test123456")
            page.locator("button:has-text('注册')").click()
            page.wait_for_timeout(3000)
            print(f"注册: url={page.url} msgs={[m.inner_text() for m in page.locator('.el-message').all()]}")
            print(f"[class*='success']: {page.locator('[class*=\"success\"]').count()}")
            print(f"正文前 250 字: {page.locator('body').inner_text()[:250].replace(chr(10), ' | ')}")
        else:
            print("X 关闭后状态不满足（checked 或 dialog），跳过注册")

        # 链路 B：链接打开 → header X 关闭 → 注册（不勾选）
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")
        print("\n===== 链路 B: 链接 → header X 关闭（不勾选）→ 注册 =====")
        page.locator("a.agreement-link").first.click()
        page.wait_for_timeout(1500)
        close_x = page.locator(".el-dialog__headerbtn")
        print(f"header X 数量: {close_x.count()}")
        if close_x.count():
            close_x.first.click()
            page.wait_for_timeout(1000)
        print(f"关闭后 dialog: {page.locator('.el-overlay-dialog').count()}")
        print(f"关闭后 checked: {page.locator('.el-checkbox').first.evaluate('el => el.classList.contains(\"is-checked\")')}")

        browser.close()
    print("\n探测完成")


if __name__ == "__main__":
    main()
