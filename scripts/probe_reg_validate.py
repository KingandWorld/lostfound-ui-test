"""Day16 注册页字段校验 + 未登录发布页行为探测（开发用，不入库）。"""

import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")


def fill_and_submit(page, **fields):
    for ph, val in fields.items():
        page.locator(f"input[placeholder='{ph}']").fill(val)
    page.locator("button:has-text('注册')").click()
    page.wait_for_timeout(800)
    errors = [e.inner_text() for e in page.locator(".el-form-item__error").all()]
    msgs = [m.inner_text() for m in page.locator(".el-message").all()]
    return errors, msgs


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = ctx.new_page()

        def goto_register():
            page.goto(f"{BASE_URL}/register", wait_until="networkidle")
            page.locator(".el-form-item__error").count()  # 触发重渲染稳定

        # 1) 空表单提交
        goto_register()
        print("===== 空表单 =====")
        page.locator("button:has-text('注册')").click()
        page.wait_for_timeout(800)
        print(f"  校验: {[e.inner_text() for e in page.locator('.el-form-item__error').all()]}")

        # 2) 缺真实姓名（其余合法）
        goto_register()
        print("===== 缺真实姓名 =====")
        errs, msgs = fill_and_submit(page, **{
            "用户名": "validate_test_1", "邮箱地址": "validate1@example.com",
            "设置密码": "Test123456", "确认密码": "Test123456",
        })
        print(f"  校验: {errs}  messages: {msgs}")

        # 3) 邮箱格式错误
        goto_register()
        print("===== 邮箱格式错误 =====")
        errs, msgs = fill_and_submit(page, **{
            "用户名": "validate_test_2", "真实姓名": "校验用户", "邮箱地址": "not-an-email",
            "设置密码": "Test123456", "确认密码": "Test123456",
        })
        print(f"  校验: {errs}  messages: {msgs}")

        # 4) 两次密码不一致
        goto_register()
        print("===== 密码不一致 =====")
        errs, msgs = fill_and_submit(page, **{
            "用户名": "validate_test_3", "真实姓名": "校验用户三", "邮箱地址": "validate3@example.com",
            "设置密码": "Test123456", "确认密码": "Different999",
        })
        print(f"  校验: {errs}  messages: {msgs}")

        # 5) 未登录访问发布页
        print("===== 未登录访问 /lost/publish =====")
        ctx2 = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page2 = ctx2.new_page()
        page2.goto(f"{BASE_URL}/lost/publish", wait_until="networkidle")
        print(f"  未登录访问 URL: {page2.url}")
        print(f"  是否有登录框: {page2.locator("input[placeholder*='用户名']").count()}")
        ctx2.close()

        browser.close()
    print("\n探测完成")


if __name__ == "__main__":
    main()
