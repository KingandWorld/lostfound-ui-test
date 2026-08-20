"""全局 fixture：base_url / browser / page / login_page / logged_in_page / user_credentials
+ 失败自动截图 / 认领数据 API（Day15~17）。

设计说明（与 week3_day15.md / week3_day16.md / week3_day17.md 计划对应）：
- browser 为 session 级：整个测试会话共用一个浏览器进程（启动快、开销小）；
- page 为 function 级：每个用例独立 context（1920x1080 + zh-CN），登录态互相隔离；
- logged_in_page 为 Day16 新增：依赖 page + login_page 复用真实登录流程，
  供发布/搜索等需要登录态的用例使用（每次用例独立登录，登录态不跨用例）；
- 各页面类 fixture（home_page / lost_list_page / publish_page / register_page /
  item_detail_page）为 Day16~17 新增，用例按需注入；
- HEADLESS 环境变量控制有头/无头：默认 headless（与服务器/CI 场景一致），
  本地调试用 `HEADLESS=false pytest ...` 打开有界面浏览器观察；
- 失败自动截图 hook Day17 完善：失败时附页面 URL + 控制台 error/warning 日志
  + 视口/全页截图两张（原 Day15 版仅一张全页截图）；
- api_headers 为 Day17 新增：认领用例的数据前置校验与 teardown 清理用
  （真实登录接口拿 token，仅只读校验与清理，不参与 UI 断言）；
- 配置统一从项目根目录 .env 读取（与接口自动化项目同一约定，同一测试账号）。

用法：
    pytest                            # headless 全量（含 1 次超时重试，见 pytest.ini）
    HEADLESS=false pytest             # 有头模式调试（本地观察）
    pytest -m ui                      # 按标记筛选
"""

import os
from pathlib import Path

import allure
import pytest
import requests
from dotenv import load_dotenv
from playwright.sync_api import Browser, Page, sync_playwright

from pages.home_page import HomePage
from pages.item_detail_page import ItemDetailPage
from pages.login_page import LoginPage
from pages.lost_list_page import LostListPage
from pages.publish_page import PublishPage
from pages.register_page import RegisterPage


def _strip_env_bom():
    """去掉 .env 文件头的 UTF-8 BOM（2026-08-20 实测卡点，见 Day17 手册卡点表）。

    Windows 编辑器保存 .env 时可能带 BOM，python-dotenv 会把 BOM 拼进第一个
    键名（如 \\ufeffBASE_URL），导致读不到该配置、BASE_URL 静默回退 localhost。
    加载前先修正文件本身，避免每次手动改。仅剥离 BOM 头，不触碰其他内容。
    """
    env_path = Path(".env")
    if env_path.exists():
        raw = env_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            env_path.write_bytes(raw[3:])


_strip_env_bom()
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
# 测试账号邮箱（2026-08-18 探测确认：/api/user/current 返回 email 字段，登录支持邮箱）；
# 未配置时邮箱登录用例跳过
TEST_EMAIL = os.getenv("TEST_EMAIL")

# 失败现场信息：用例执行中把当前 page / 控制台日志暂存在 node 上，makereport 失败时取出
_PAGE_KEY = pytest.StashKey[Page]()
_CONSOLE_KEY = pytest.StashKey[list[str]]()


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
    # Day17：收集页面控制台 error/warning，失败时随截图一起附进 Allure（前端 JS 异常排查）
    console_errors: list[str] = []
    request.node.stash[_CONSOLE_KEY] = console_errors
    page.on(
        "console",
        lambda msg: console_errors.append(f"[{msg.type}] {msg.text}")
        if msg.type in ("error", "warning")
        else None,
    )
    yield page
    context.close()


@pytest.fixture(scope="session")
def base_url():
    """被测系统根地址（.env BASE_URL，只读环境变量，session 级供 api_headers 复用）。"""
    return BASE_URL


@pytest.fixture
def login_page(page):
    """登录页 Page Object 实例。"""
    return LoginPage(page)


@pytest.fixture
def logged_in_page(page, login_page, base_url, user_credentials):
    """已登录的页面实例（Day16）：复用真实登录流程，供发布/搜索等用例使用。

    设计说明：每个用例通过 page fixture 拿到独立 context，登录态互不污染；
    登录成功标准与 Day15 一致（跳转首页 + localStorage token 非空）。
    返回的是已登录的 page，后续用例可直接 goto 目标页面。
    """
    login_page.go(base_url)
    login_page.login(user_credentials["username"], user_credentials["password"])
    login_page.wait_for_url("**/", timeout=15_000)
    login_page.wait_for_load_state()
    assert login_page.page.evaluate(
        "localStorage.getItem('token')"
    ), "logged_in_page 登录失败：localStorage 无 token"
    return page


@pytest.fixture
def home_page(page):
    """首页 Page Object 实例。"""
    return HomePage(page)


@pytest.fixture
def lost_list_page(page):
    """失物列表页 Page Object 实例。"""
    return LostListPage(page)


@pytest.fixture
def publish_page(page):
    """发布页 Page Object 实例。"""
    return PublishPage(page)


@pytest.fixture
def register_page(page):
    """注册页 Page Object 实例。"""
    return RegisterPage(page)


@pytest.fixture
def item_detail_page(page):
    """物品详情页 Page Object 实例（Day17 认领流程）。"""
    return ItemDetailPage(page)


@pytest.fixture(scope="session")
def api_headers(base_url):
    """API 请求头（Day17 认领用例的数据前置校验与 teardown 清理用）。

    通过真实登录接口拿 token（与接口自动化项目同款自定义 Header `token`），
    session 级只登录一次。仅用于只读校验与数据清理，不参与 UI 断言。
    """
    resp = requests.post(
        f"{base_url}/api/user/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=10,
    )
    body = resp.json()
    assert body.get("code") == "200", f"api_headers 登录失败: {body}"
    return {"token": body["data"]["token"]}


@pytest.fixture
def user_credentials():
    """登录测试数据（与接口自动化项目共用同一测试账号，来自 .env）。"""
    return {"username": TEST_USERNAME, "password": TEST_PASSWORD, "email": TEST_EMAIL}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """失败自动截图（Day15 预留版 → Day17 完善版）。

    Day17 完善点（对应 week3_day17.md 任务三）：
    1) 附失败时的页面 URL（快速定位用例停在哪一步）；
    2) 附页面控制台 error/warning 日志（前端 JS 异常排查，最多取末 50 条）；
    3) 截图两张：视口截图（失败现场）+ 全页截图（长页面辅助定位）。

    注意：任何附加操作失败只记录不抛错，避免掩盖原始用例失败信息；
    与 pytest-rerunfailures 配合：重试前的失败也走本 hook，最终报告
    只保留最后一次尝试的现场（Allure 会合并重试结果）。
    """
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = item.stash.get(_PAGE_KEY, None)
        if page is not None:
            try:
                allure.attach(
                    page.url,
                    name="失败时页面 URL",
                    attachment_type=allure.attachment_type.TEXT,
                )
            except Exception:  # 附加信息失败不应掩盖原始失败
                pass
            try:
                console_errors = item.stash.get(_CONSOLE_KEY, [])
                if console_errors:
                    allure.attach(
                        "\n".join(console_errors[-50:]),
                        name=f"页面控制台错误/警告（共 {len(console_errors)} 条，取末 50 条）",
                        attachment_type=allure.attachment_type.TEXT,
                    )
            except Exception:
                pass
            try:
                allure.attach(
                    page.screenshot(full_page=False),
                    name="失败截图-视口",
                    attachment_type=allure.attachment_type.PNG,
                )
                allure.attach(
                    page.screenshot(full_page=True),
                    name="失败截图-全页",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass
