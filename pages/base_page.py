"""Page Object 基类：封装 Playwright 通用页面操作（Day15）。

设计说明（与 week3_day15.md 任务二对应）：
- 所有定位/操作都吃 Playwright 自动等待（auto-waiting），不写死 sleep；
- 每个关键动作用 allure.step 包裹，Allure 报告里可看到"打开页面/点击/输入"步骤树；
- screenshot() 把截图保存到 screenshots/ 并作为 PNG 附件进 Allure 报告；
- 等待方法（wait_for_element / wait_for_url / wait_for_load_state）供断言前
  显式等待关键元素/跳转，避免"断言跑在页面状态到达之前"。

用法：
    class LoginPage(BasePage):
        def login(self, ...):
            self.fill(...)
"""

from pathlib import Path

import allure
from playwright.sync_api import Page


class BasePage:
    """通用页面基类：构造时注入 Playwright Page。"""

    def __init__(self, page: Page):
        self.page = page

    # ---------- 导航 ----------

    def navigate(self, url: str):
        """导航到指定 URL，等待页面加载至网络空闲。"""
        with allure.step(f"打开页面: {url}"):
            self.page.goto(url, wait_until="networkidle")

    def wait_for_url(self, url_pattern: str, timeout: int = 10_000):
        """等待 URL 匹配（支持 Playwright glob，如 '**/back/dashboard'）。"""
        with allure.step(f"等待 URL 匹配: {url_pattern}"):
            self.page.wait_for_url(url_pattern, timeout=timeout)

    def wait_for_load_state(self, state: str = "networkidle", timeout: int = 10_000):
        """等待页面加载状态（load / domcontentloaded / networkidle）。"""
        self.page.wait_for_load_state(state, timeout=timeout)

    # ---------- 元素操作 ----------

    def click(self, selector: str):
        """点击元素（Playwright 自动等待元素可见、可操作）。"""
        with allure.step(f"点击: {selector}"):
            self.page.locator(selector).click()

    def fill(self, selector: str, text: str):
        """输入文本（自动先清空再输入）。"""
        with allure.step(f"输入 '{text[:20]}' 到 {selector}"):
            self.page.locator(selector).fill(text)

    def get_text(self, selector: str) -> str:
        """获取元素文本。"""
        with allure.step(f"获取文本: {selector}"):
            return self.page.locator(selector).inner_text()

    def is_visible(self, selector: str) -> bool:
        """检查元素当前是否可见。"""
        return self.page.locator(selector).is_visible()

    def wait_for_element(self, selector: str, timeout: int = 10_000):
        """显式等待元素可见（关键操作/断言前用，替代盲等）。"""
        with allure.step(f"等待元素可见: {selector}"):
            self.page.locator(selector).wait_for(state="visible", timeout=timeout)

    # ---------- 截图留证 ----------

    def screenshot(self, name: str):
        """截图保存到 screenshots/{name}.png，并附加到 Allure 报告。"""
        with allure.step(f"截图: {name}"):
            path = Path("screenshots") / f"{name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(path), full_page=True)
            allure.attach.file(str(path), name, allure.attachment_type.PNG)
