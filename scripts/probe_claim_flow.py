"""探测认领流程 UI（Day17）：登录 → 列表页 → 点击物品卡片 → 找认领入口（2026-08-20）。

输出到 stdout（重定向到 scripts/probe_claim_out.txt 归档，不入库）。

要点（沿用 Day15/16 探测思路）：
- 真实登录（.env 测试账号），保证会话有效；
- 依次尝试：列表页点卡片 → 详情页结构 / 认领按钮；/lost/{id} 直连；个人中心我的认领页；
- 只探测不写数据（不点"确认认领"）。
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
    print(f"== 认领流程 UI 探测 == 时间戳: {int(time.time() * 1000)}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()

        # 1. 登录
        print("\n[1] 登录")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", TEST_USERNAME)
        page.fill("input[placeholder='请输入密码']", TEST_PASSWORD)
        page.locator("button:has-text('登录')").click()
        page.wait_for_url("**/", timeout=15_000)
        token = page.evaluate("localStorage.getItem('token')")
        print(f"token 非空: {bool(token)}")

        # 2. 列表页，点第一张卡片，观察跳转
        print("\n[2] 列表页 /lost 点击第一张卡片")
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        cards = page.locator(".el-card")
        print(f"卡片数: {cards.count()}")
        first_text = cards.first.inner_text() if cards.count() else "(无卡片)"
        print(f"第一张卡片文本: {first_text[:120]!r}")
        # 记录点击前的 URL，点击后对比
        before_url = page.url
        cards.first.click()
        page.wait_for_timeout(3000)  # 等跳转/弹窗
        after_url = page.url
        print(f"点击前 URL: {before_url}")
        print(f"点击后 URL: {after_url}")
        print(f"URL 是否变化: {before_url != after_url}")

        # 3. 找认领相关元素（按钮/链接，含文本"认领"）
        print("\n[3] 查找认领入口")
        page.wait_for_timeout(1500)
        claim_markers = page.locator("text=/认领|失主|归还/")
        n = claim_markers.count()
        print(f"文本含 认领/失主/归还 的元素数: {n}")
        for i in range(min(n, 8)):
            el = claim_markers.nth(i)
            tag = el.evaluate("e => e.tagName")
            txt = (el.inner_text() or "")[:60]
            vis = el.is_visible()
            print(f"  [{i}] <{tag}> visible={vis} text={txt!r}")
        # 弹窗元素
        dialogs = page.locator(".el-dialog")
        print(f".el-dialog 数量: {dialogs.count()}")
        for i in range(dialogs.count()):
            d = dialogs.nth(i)
            if d.is_visible():
                print(f"  弹窗可见 [{i}]: {d.inner_text()[:200]!r}")

        # 4. 尝试直连详情路由（常见形态：/lost/{id} /lost-item/{id} /detail/{id}）
        print("\n[4] 尝试直连详情路由")
        for path in ("/lost/1", "/lost-item/1", "/detail/1", "/lost/detail/1"):
            try:
                page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=10_000)
                page.wait_for_timeout(1200)
                title = page.title()
                print(f"  {path}: title={title!r} url={page.url}")
                if "login" in page.url:
                    print(f"    -> 重定向登录（未登录保护或路由不存在）")
                    continue
                body_text = page.locator("body").inner_text()[:100].replace("\n", " ")
                print(f"    body 开头: {body_text!r}")
            except Exception as exc:
                print(f"  {path}: 异常 {type(exc).__name__}: {exc}")

        # 5. 个人中心/我的认领页尝试
        print("\n[5] 尝试个人中心/我的认领路由")
        for path in ("/mine", "/my", "/my-claims", "/profile", "/user", "/claims"):
            try:
                page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=10_000)
                page.wait_for_timeout(1200)
                if "login" in page.url:
                    print(f"  {path}: -> 重定向登录")
                    continue
                body_text = page.locator("body").inner_text()[:120].replace("\n", " ")
                print(f"  {path}: title={page.title()!r} body={body_text!r}")
            except Exception as exc:
                print(f"  {path}: 异常 {type(exc).__name__}")

        browser.close()
    print("\n== 探测完成 ==")


if __name__ == "__main__":
    probe()
