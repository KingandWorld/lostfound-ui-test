"""全局 fixture：base_url / browser / page / login_page / user_credentials + 失败自动截图（Day15）。

设计说明（与 week3_day15.md 计划对应）：
- browser 为 session 级：整个测试会话共用一个浏览器进程（启动快、开销小）；
- page 为 function 级：每个用例独立 context（1920x1080 + zh-CN），登录态互相隔离；
- HEADLESS 环境变量控制有头/无头：默认 headless（与服务器/CI 场景一致），
  本地调试用 `HEADLESS=false pytest ...` 打开有界面浏览器观察；
- 失败自动截图 hook 为 Day15 预留版（Day17 完善）：call 阶段失败时，
  把当前页面截图（全页）作为 PNG 附件附进 Allure 报告；
- 配置统一从项目根目录 .env 读取（与接口自动化项目同一约定，同一测试账号）。

用法：
    pytest                            # headless 全量
    HEADLESS=false pytest             # 有头模式调试（本地观察）
    pytest -m ui                      # 按标记筛选
"""

import os

import allure
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, Page, sync_playwright

from pages.login_page import LoginPage

# 默认读取项目根目录 .env（pytest 在项目根目录运行即可生效）
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
# 测试账号邮箱（2026-08-18 探测确认：/api/user/current 返回 email 字段，登录支持邮箱）；
# 未配置时邮箱登录用例跳过
TEST_EMAIL = os.getenv("TEST_EMAIL")

# 失败自动截图：用例执行中把当前 page 暂存在 node 上，makereport 失败时取出
_PAGE_KEY = pytest.StashKey[Page]()


@pytest.fixture(scope="session")
def browser():
    """创建浏览器实例（整个测试会话共享一个浏览器进程）。"""
    with sync_playwright() as p:
        headless = os.getenv("HEADLESS", "True").strip().lower() == "true"
        # --proxy-server=direct://：本机系统代理（127.0.0.1:7890）未启动时，
        # Chromium 会 net::ERR_PROXY_CONNECTION_FAILED（2026-08-18 实测，见手册卡点表）；
        # 目标站点为公网服务器，可直连，故强制直连。若需走代理请移除该参数。
        browser = p.chromium.launch(
            headless=headless,
            args=["--proxy-server=direct://"],
        )
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, request):
    """每个测试用例独立的页面上下文（视口 1920x1080，语言 zh-CN）。"""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
    )
    page = context.new_page()
    request.node.stash[_PAGE_KEY] = page
    yield page
    context.close()


@pytest.fixture
def base_url():
    """被测系统根地址（.env BASE_URL）。"""
    return BASE_URL


@pytest.fixture
def login_page(page):
    """登录页 Page Object 实例。"""
    return LoginPage(page)


@pytest.fixture
def user_credentials():
    """登录测试数据（与接口自动化项目共用同一测试账号，来自 .env）。"""
    return {"username": TEST_USERNAME, "password": TEST_PASSWORD, "email": TEST_EMAIL}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """失败自动截图（Day15 预留版，Day17 完善）：call 阶段失败时把页面截图附进 Allure。

    注意：截图失败只记录不抛错，避免掩盖原始用例失败信息。
    """
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = item.stash.get(_PAGE_KEY, None)
        if page is not None:
            try:
                screenshot = page.screenshot(full_page=True)
                allure.attach(
                    screenshot,
                    name="失败截图",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:  # 截图失败不应掩盖原始失败
                pass
