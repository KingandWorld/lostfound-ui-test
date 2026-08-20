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
    """通用页面基类：构造时注入 Playwright Page。

    Day17 重构：get_form_errors / get_messages 从 PublishPage / RegisterPage
    提升到基类（两处实现原为同款轮询逻辑），表单页统一复用；
    默认选择器 FORM_ERRORS / MESSAGE 为 Element Plus 通用结构，
    子类可按需覆写。
    """

    # Element Plus 通用结构（表单校验提示 / 全局消息；Day17 提升至基类）
    FORM_ERRORS = ".el-form-item__error"
    MESSAGE = ".el-message"

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

    # ---------- 表单校验提示 ----------

    def get_form_errors(self, timeout_ms: int = 2_000) -> list[str]:
        """获取表单字段校验提示文案（.el-form-item__error）。

        Element Plus 校验提示在提交后异步渲染（实测约 200~800ms），
        读取前轮询等待提示出现，避免"断言跑在提示渲染之前"。
        Day17 起由基类统一提供（PublishPage/RegisterPage/ItemDetailPage 复用）。
        """
        return self._poll_texts(self.page.locator(self.FORM_ERRORS), timeout_ms)

    def get_messages(self, timeout_ms: int = 2_000) -> list[str]:
        """获取全局消息（.el-message，如"请阅读并同意用户协议"；约 3 秒自动消失）。"""
        return self._poll_texts(self.page.locator(self.MESSAGE), timeout_ms)

    def _poll_texts(self, locator, timeout_ms: int) -> list[str]:
        """轮询等待 locator 出现元素后返回全部文本（每 200ms 一次，最长为 timeout_ms）。"""
        for _ in range(max(1, timeout_ms // 200)):
            if locator.count() > 0:
                break
            self.page.wait_for_timeout(200)
        return [el.inner_text() for el in locator.all()]

    # ---------- 截图留证 ----------

    def screenshot(self, name: str):
        """截图保存到 screenshots/{name}.png，并附加到 Allure 报告。"""
        with allure.step(f"截图: {name}"):
            path = Path("screenshots") / f"{name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(path), full_page=True)
            allure.attach.file(str(path), name, allure.attachment_type.PNG)
