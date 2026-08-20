"""探测认领弹窗与我的认领入口（Day17 第 2 轮，2026-08-20）。

只观察不提交：点开「申请归还」后仅检查弹窗结构，不点确认按钮；
输出到 scripts/probe_claim_dialog_out.txt（gitignore，不入库）。
"""

import os
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def probe():
    print(f"== 认领弹窗/我的认领 探测 == 时间戳: {int(time.time() * 1000)}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()

        # 记录认领相关请求（只观察不发）
        def on_request(req):
            if "/api/claim" in req.url:
                print(f"  [request] {req.method} {req.url}")
        page.on("request", on_request)

        print("\n[1] 登录")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", TEST_USERNAME)
        page.fill("input[placeholder='请输入密码']", TEST_PASSWORD)
        page.locator("button:has-text('登录')").click()
        page.wait_for_url("**/", timeout=15_000)
        print("登录成功, token:", bool(page.evaluate("localStorage.getItem('token')")))

        print("\n[2] 详情页 /lost/detail/3（列表第一张卡片，待认领）")
        page.goto(f"{BASE_URL}/lost/detail/3", wait_until="networkidle")
        print("URL:", page.url)
        print("页面标题:", page.title())
        # 详情页正文结构
        body = page.locator("body").inner_text()
        print("正文（前 400 字）:")
        for line in body.splitlines():
            if line.strip():
                print(f"  {line.strip()}")

        print("\n[3] 点「申请归还」→ 检查弹窗结构")
        apply_btn = page.locator("text=申请归还")
        print("申请归还元素:", apply_btn.count(), "可见:", apply_btn.first.is_visible() if apply_btn.count() else "-")
        apply_btn.first.click()
        page.wait_for_timeout(1500)
        dialogs = page.locator(".el-dialog")
        print(".el-dialog 数量:", dialogs.count())
        for i in range(dialogs.count()):
            d = dialogs.nth(i)
            if d.is_visible():
                print(f"  可见弹窗 [{i}] 标题区: {d.locator('.el-dialog__header').inner_text()!r}")
                print(f"  内容区: {d.locator('.el-dialog__body').inner_text()[:300]!r}")
                btns = d.locator(".el-dialog__footer button")
                print(f"  footer 按钮 {btns.count()} 个: {[b.inner_text() for b in btns.all()]}")
                # 弹窗内的输入框/文本域
                for inp in d.locator("input, textarea").all():
                    ph = inp.get_attribute("placeholder") or ""
                    print(f"  输入元素: <{inp.evaluate('e=>e.tagName')}> placeholder={ph!r}")

        print("\n[4] 关闭弹窗（Esc），确认未提交认领")
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
        print("弹窗仍可见:", page.locator(".el-dialog:visible").count() > 0)

        print("\n[5] 个人中心 /profile 找「我的认领」入口")
        page.goto(f"{BASE_URL}/profile", wait_until="networkidle")
        body = page.locator("body").inner_text()
        for kw in ("认领", "归还", "我的发布", "记录"):
            hits = [l.strip() for l in body.splitlines() if kw in l and l.strip()]
            if hits:
                print(f"  含'{kw}': {hits[:6]}")

        browser.close()
    print("\n== 探测完成 ==")


if __name__ == "__main__":
    probe()
