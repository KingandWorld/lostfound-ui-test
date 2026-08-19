"""Day16 流程探测脚本：实测 搜索过滤 / 发布成功 / 注册成功 的真实行为（开发用，不入库）。

用法（项目根目录）:
    .venv\\Scripts\\python.exe scripts/probe_flows_day16.py

注意：本脚本会向真实后端写入数据（发布 1 条物品、注册 1 个测试用户），
标题/用户名带时间戳标记，与接口自动化项目同款"测试数据残留"策略。
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
USERNAME = os.getenv("TEST_USERNAME")
PASSWORD = os.getenv("TEST_PASSWORD")


def login(page):
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.fill("input[placeholder='请输入用户名或邮箱']", USERNAME)
    page.fill("input[placeholder='请输入密码']", PASSWORD)
    page.click("button:has-text('登录')")
    page.wait_for_url("**/", timeout=15_000)
    page.wait_for_load_state("networkidle")


def main():
    stamp = str(int(time.time() * 1000))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()
        login(page)
        print(f"登录成功: {page.url}")

        # ---- 1) 列表页搜索按钮是否过滤 ----
        print("\n===== 列表页点搜索按钮 =====")
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        print(f"初始 .el-card: {page.locator('.el-card').count()}")
        title_input = page.locator("input[placeholder*='标题']").first
        title_input.fill("zzzz绝对不存在的关键词zzzz")
        page.wait_for_timeout(800)  # 等输入触发的前端重渲染稳定
        page.locator("button:has-text('搜索')").first.click()
        page.wait_for_load_state("networkidle")
        print(f"点搜索后 URL: {page.url}")
        print(f"点搜索后 .el-card: {page.locator('.el-card').count()}")
        empty = page.locator(".el-empty").count()
        print(f".el-empty 数量: {empty}")
        if empty:
            print(f"  .el-empty 文案: '{page.locator('.el-empty').first.inner_text()[:80]}'")
        # 重置
        page.locator("button:has-text('重置')").first.click()
        page.wait_for_load_state("networkidle")
        print(f"重置后 .el-card: {page.locator('.el-card').count()}  URL: {page.url}")

        # ---- 2) 发布成功流程 ----
        print("\n===== 发布物品（真实提交）=====")
        page.goto(f"{BASE_URL}/lost/publish", wait_until="networkidle")
        title = f"UI测试发布物品_{stamp}"
        page.locator("input[placeholder='请输入物品标题']").fill(title)
        # 分类下拉：点开选择"电子产品"（选项: 证件类/电子产品/现金/卡类/生活用品/书籍资料/衣物饰品/其他）
        select = page.locator(".el-select").first
        select.click()
        page.wait_for_timeout(500)
        options = page.locator(".el-select-dropdown__item").all()
        print(f"分类选项: {[o.inner_text().strip() for o in options]}")
        page.locator(".el-select-dropdown__item").nth(1).click()
        page.locator("input[placeholder='请输入丢失地点']").fill("UI测试-图书馆大厅")
        # 丢失时间：点击输入框打开日期面板 → 点"此刻"快捷按钮
        page.locator("input[placeholder='请选择丢失时间']").click()
        page.wait_for_timeout(600)
        now_btn = page.locator("button:has-text('此刻')")
        print(f"日期面板'此刻'按钮数量: {now_btn.count()}")
        if now_btn.count():
            now_btn.first.click()
            page.wait_for_timeout(300)
            page.keyboard.press("Enter")  # 确认日期
        page.locator("textarea[placeholder*='描述']").fill("UI自动化测试发布的物品，用于验证发布流程，可忽略。")
        page.locator("input[placeholder='请输入联系人姓名']").fill("测试联系人")
        page.locator("input[placeholder='请输入联系电话']").fill("13800138000")
        page.locator("button:has-text('发布')").click()
        page.wait_for_timeout(1500)
        success_msg = page.locator(".el-message--success")
        print(f"成功提示 .el-message--success 数量: {success_msg.count()}")
        if success_msg.count():
            print(f"  文案: '{success_msg.first.inner_text()}'")
        print(f"发布后 URL: {page.url}")
        page.wait_for_load_state("networkidle")
        print(f"发布后页面标题区域: {page.title()}")
        # 到列表页验证新物品出现
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        found = [c.inner_text() for c in page.locator(".el-card").all() if title in c.inner_text()]
        print(f"列表页出现新物品: {len(found) > 0}")

        # ---- 3) 发布空标题校验 ----
        print("\n===== 发布空标题校验 =====")
        page.goto(f"{BASE_URL}/lost/publish", wait_until="networkidle")
        page.locator("button:has-text('发布')").click()
        page.wait_for_timeout(800)
        errors = page.locator(".el-form-item__error").all()
        print(f"校验提示数量: {len(errors)}  文案: {[e.inner_text() for e in errors]}")

        # ---- 4) 注册成功流程 ----
        print("\n===== 注册（真实提交唯一用户名）=====")
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")
        uname = f"uitest_{stamp}"
        page.locator("input[placeholder='用户名']").fill(uname)
        page.locator("input[placeholder='真实姓名']").fill("UI测试用户")
        page.locator("input[placeholder='邮箱地址']").fill(f"uitest_{stamp}@example.com")
        page.locator("input[placeholder='设置密码']").fill("Test123456")
        page.locator("input[placeholder='确认密码']").fill("Test123456")
        # 勾选协议：点 checkbox 方块（.el-checkbox__inner），不要点整个 .el-checkbox——
        # 实测点整个 label 区域可能触发《用户协议》链接打开协议 dialog 拦截注册按钮
        page.locator(".el-checkbox__inner").click()
        page.wait_for_timeout(500)
        protocol_dialog = page.locator(".el-overlay-dialog")
        print(f"协议 dialog 是否弹出: {protocol_dialog.count()}")
        if protocol_dialog.count():
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            print("已按 Esc 关闭协议 dialog")
        page.locator("button:has-text('注册')").click()
        page.wait_for_timeout(2500)
        print(f"注册后 URL: {page.url}")
        print(f"成功覆盖层 [class*='success']: {page.locator('[class*=\"success\"]').count()}")
        print(f".el-message 数量: {page.locator('.el-message').count()}")
        for m in page.locator(".el-message").all():
            print(f"  message: '{m.inner_text()}'")
        print(f"页面正文前 300 字: {page.locator('body').inner_text()[:300].replace(chr(10), ' | ')}")

        # ---- 5) 注册重复用户名校验 ----
        print("\n===== 注册重复用户名 =====")
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")
        page.locator("input[placeholder='用户名']").fill(uname)  # 刚注册过的用户名
        page.locator("input[placeholder='真实姓名']").fill("重复用户")
        page.locator("input[placeholder='邮箱地址']").fill(f"dup_{stamp}@example.com")
        page.locator("input[placeholder='设置密码']").fill("Test123456")
        page.locator("input[placeholder='确认密码']").fill("Test123456")
        page.locator(".el-checkbox__inner").click()
        page.wait_for_timeout(500)
        if page.locator(".el-overlay-dialog").count():
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        page.locator("button:has-text('注册')").click()
        page.wait_for_timeout(1500)
        msgs = page.locator(".el-message").all()
        print(f".el-message 数量: {len(msgs)}  文案: {[m.inner_text() for m in msgs]}")
        errors = page.locator(".el-form-item__error").all()
        print(f"表单校验提示: {[e.inner_text() for e in errors]}")
        print(f"重复注册后 URL: {page.url}")

        browser.close()
    print("\n流程探测完成，写入数据: 1 条物品 + 1 个注册用户（含用户名标记 uitest_）")


if __name__ == "__main__":
    main()
