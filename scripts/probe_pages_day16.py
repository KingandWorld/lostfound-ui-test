"""Day16 页面探测脚本：登录后实测 首页 / 发布页 / 注册页 的 DOM 结构（开发用，不入库）。

用法（项目根目录）:
    .venv\\Scripts\\python.exe scripts/probe_pages_day16.py

输出内容（与 week3_day16 手册对应）:
    1) 登录后首页（/）: 导航链接、搜索框、按钮、物品卡片结构；
    2) 发布页: 表单 input/textarea/select/上传按钮结构（找到其 URL）；
    3) 注册页（/register）: 表单字段结构。

选择器结论将被回填到 pages/home_page.py / publish_page.py / register_page.py，
与 Day15 探测登录页的做法一致：先实测、后写定位器。
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# pytest 在项目根目录运行，脚本手动加载 .env
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
USERNAME = os.getenv("TEST_USERNAME")
PASSWORD = os.getenv("TEST_PASSWORD")


def dump_inputs(page, label):
    print(f"\n===== [{label}] inputs =====")
    for i, el in enumerate(page.locator("input").all()):
        info = el.evaluate(
            "el => JSON.stringify({type: el.type, placeholder: el.placeholder, "
            "name: el.name, cls: el.className})"
        )
        print(f"  input[{i}]: {info}")


def dump_buttons(page, label, limit=30):
    print(f"\n===== [{label}] buttons =====")
    for i, el in enumerate(page.locator("button").all()):
        if i >= limit:
            print("  ... (truncated)")
            break
        print(f"  button[{i}]: text='{el.inner_text().strip()}' cls='{el.get_attribute('class')}'")


def dump_textareas(page, label):
    print(f"\n===== [{label}] textareas =====")
    for i, el in enumerate(page.locator("textarea").all()):
        print(f"  textarea[{i}]: placeholder='{el.get_attribute('placeholder')}'")


def dump_links(page, label, limit=30):
    print(f"\n===== [{label}] links =====")
    for i, el in enumerate(page.locator("a").all()):
        if i >= limit:
            print("  ... (truncated)")
            break
        txt = el.inner_text().strip().replace("\n", " ")
        href = el.get_attribute("href")
        if txt or href:
            print(f"  a[{i}]: text='{txt[:40]}' href={href}")


def dump_container(page, selector, label):
    print(f"\n===== [{label}] container: {selector} =====")
    count = page.locator(selector).count()
    print(f"  count={count}")
    if count > 0 and count <= 5:
        html = page.locator(selector).first.inner_html()[:800]
        print(f"  first inner_html (truncated): {html}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--proxy-server=direct://"],  # 本机卡点：系统代理未启动时强制直连
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()

        # 1) 登录（复用真实流程）
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", USERNAME)
        page.fill("input[placeholder='请输入密码']", PASSWORD)
        page.click("button:has-text('登录')")
        page.wait_for_url("**/", timeout=15_000)
        page.wait_for_load_state("networkidle")
        print(f"登录成功，当前 URL: {page.url}")

        # 2) 首页结构
        print("\n########## 首页 / ##########")
        dump_links(page, "首页导航链接")
        dump_inputs(page, "首页")
        dump_buttons(page, "首页")
        dump_container(page, ".el-card", "物品卡片候选: .el-card")
        dump_container(page, "[class*='item']", "物品卡片候选: [class*='item']")
        dump_container(page, ".user-avatar", "用户头像候选: .user-avatar")

        # 3) 首页卡片结构（物品卡片 .el-card 内部字段，供搜索断言用）
        dump_container(page, ".el-card", "首页物品卡片")

        # 3b) 搜索行为：首页搜索框输入 + 回车，观察 URL 变化与结果
        search_input = page.locator("input[placeholder*='搜索']").first
        print(f"\n===== 搜索行为探测 =====")
        print(f"搜索框 placeholder: '{search_input.get_attribute('placeholder')}'")
        search_input.fill("水杯")
        search_input.press("Enter")
        page.wait_for_load_state("networkidle")
        print(f"搜索后 URL: {page.url}")
        print(f"搜索后 .el-card 数量: {page.locator('.el-card').count()}")
        cards = page.locator(".el-card").all()
        for i, c in enumerate(cards[:2]):
            print(f"  card[{i}] inner_text (truncated): {c.inner_text()[:150].replace(chr(10), ' | ')}")
        # 无结果搜索
        search_input.fill("zzzz不存在的关键词zzzz")
        search_input.press("Enter")
        page.wait_for_load_state("networkidle")
        print(f"无结果搜索后 .el-card 数量: {page.locator('.el-card').count()}")
        empty_hint = page.locator(".el-empty")
        print(f"空结果提示 .el-empty 数量: {empty_hint.count()}")
        if empty_hint.count():
            print(f"  .el-empty 文案: '{empty_hint.first.inner_text()[:80]}'")

        # 4) 发布入口是按钮（不是链接，实测）——点击"发布失物信息"进入列表页 /lost
        publish_btn = page.locator("button:has-text('发布失物信息')").first
        print(f"\n发布按钮可见: {publish_btn.is_visible()}")
        publish_btn.click()
        page.wait_for_load_state("networkidle")
        print(f"########## 列表页 URL: {page.url} ##########")
        dump_inputs(page, "列表页")
        dump_buttons(page, "列表页", limit=8)
        dump_container(page, ".el-select", "列表页下拉框候选: .el-select")
        # 列表页搜索行为：输入标题关键词 + 回车（fill 会触发路由重渲染，按钮可能脱离，用回车更稳）
        title_input = page.locator("input[placeholder*='标题']").first
        print(f"\n===== 列表页搜索行为探测 =====")
        print(f"标题搜索框 placeholder: '{title_input.get_attribute('placeholder')}'")
        title_input.fill("学生证")
        title_input.press("Enter")
        page.wait_for_load_state("networkidle")
        print(f"搜索后 URL: {page.url}")
        print(f"搜索后 .el-card 数量: {page.locator('.el-card').count()}")
        cards = page.locator(".el-card").all()
        for i, c in enumerate(cards[:3]):
            print(f"  card[{i}] inner_text: {c.inner_text()[:120].replace(chr(10), ' | ')}")
        # 重置，再验证 URL 参数直达：/lost?search=学生证
        page.locator("button:has-text('重置')").first.click()
        page.wait_for_load_state("networkidle")
        page.goto(f"{BASE_URL}/lost?search=学生证", wait_until="networkidle")
        print(f"\nURL 参数直达 /lost?search=学生证 后 .el-card 数量: {page.locator('.el-card').count()}")
        for i, c in enumerate(page.locator(".el-card").all()[:3]):
            print(f"  card[{i}] inner_text: {c.inner_text()[:120].replace(chr(10), ' | ')}")

        # 5) 再点一次"发布失物信息"→ 真正的发布表单页
        print("\n===== 发布表单页探测 =====")
        try:
            page.locator("button:has-text('发布失物信息')").first.click()
            page.wait_for_timeout(2500)  # 等路由动画/弹窗渲染
            print(f"########## 点击后 URL: {page.url} ##########")
            print(f"点击后 .el-dialog 数量: {page.locator('.el-dialog').count()}")
            print(f"点击后 .el-form 数量: {page.locator('.el-form').count()}")
            print(f"点击后 form 标签数量: {page.locator('form').count()}")
            print(f"页面正文前 400 字: {page.locator('body').inner_text()[:400].replace(chr(10), ' | ')}")
            dump_inputs(page, "点击发布后")
            dump_textareas(page, "点击发布后")
            dump_buttons(page, "点击发布后", limit=10)
            dump_container(page, ".el-select", "点击发布后下拉框: .el-select")
            dump_container(page, ".el-upload", "点击发布后上传组件: .el-upload")
            dump_container(page, "input[type='file']", "点击发布后文件上传 input")
            dump_container(page, ".el-dialog", "点击发布后弹窗: .el-dialog")
            dump_container(page, ".el-form", "点击发布后 .el-form")
            # 如果有 dialog 且有表单，dump dialog 内的 input
            if page.locator(".el-dialog").count() > 0:
                print("\n===== dialog 内 inputs =====")
                for i, el in enumerate(page.locator(".el-dialog input").all()):
                    print(f"  dialog input[{i}]: {el.evaluate('el => JSON.stringify({type: el.type, placeholder: el.placeholder})')}")
                print("\n===== dialog 内 textareas =====")
                for i, el in enumerate(page.locator(".el-dialog textarea").all()):
                    print(f"  dialog textarea[{i}]: placeholder='{el.get_attribute('placeholder')}'")
                print("\n===== dialog 内 buttons =====")
                for i, el in enumerate(page.locator(".el-dialog button").all()):
                    print(f"  dialog button[{i}]: text='{el.inner_text().strip()}'")
        except Exception as exc:
            print(f"[表单页探测失败] {type(exc).__name__}: {exc}")

        # 5b) URL 参数名实测：title= / search= / 首页搜索框行为
        print("\n===== URL 参数名实测 =====")
        for param in ("title", "keyword", "search"):
            try:
                page.goto(f"{BASE_URL}/lost?{param}=学生证", wait_until="networkidle")
                count = page.locator(".el-card").count()
                first_title = ""
                if count:
                    first_title = page.locator(".el-card").first.inner_text()[:60].replace(chr(10), " | ")
                print(f"/lost?{param}=学生证 → .el-card={count}  first: {first_title}")
            except Exception as exc:
                print(f"/lost?{param}=学生证 → 失败: {type(exc).__name__}")
        # 首页搜索框：输入后点击（找图标按钮），观察 URL
        try:
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            search_input = page.locator("input[placeholder*='搜索']").first
            search_input.fill("学生证")
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            print(f"首页搜索回车后 URL: {page.url}")
            print(f"首页搜索回车后 .el-card: {page.locator('.el-card').count()}")
        except Exception as exc:
            print(f"首页搜索探测失败: {type(exc).__name__}: {exc}")

        # 6) 注册页结构
        print("\n########## 注册页 /register ##########")
        page.goto(f"{BASE_URL}/register", wait_until="networkidle")
        dump_inputs(page, "注册页")
        dump_buttons(page, "注册页")
        dump_container(page, ".el-checkbox", "协议勾选候选: .el-checkbox")
        dump_container(page, "[class*='success']", "成功覆盖层候选: [class*='success']")

        browser.close()
    print("\n探测完成")


if __name__ == "__main__":
    main()
