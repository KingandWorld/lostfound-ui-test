"""LoginPage：失物招领系统登录页 Page Object（Day15）。

元素定位依据 2026-08-18 对真实登录页实测（与 week3_day15.md 任务三一致）：
- 登录支持用户名或邮箱（输入框 placeholder 为「请输入用户名或邮箱」）；
- 密码输入框 placeholder「请输入密码」，登录按钮按文本匹配「登录」；
- 登录接口 POST /api/user/login，JWT token 存 localStorage['token']，
  后续请求走自定义 Header `token`（非 Bearer），返回 code 为 String 类型 "200"；
- 错误提示是 Element Plus 的 .el-message--error（约 3 秒自动消失，断言要快）；
- 验证码区域 .captcha-row 为条件显示（连续失败可能触发），自动化策略见
  week3_day15 手册卡点排查表：字符验证码走万能码/评估 OCR，滑块不自动化。

用法（用例内）：
    login_page.go(base_url)
    login_page.login(username, password)
    assert login_page.is_login_success()   # 登录后跳转等，见测试用例
"""

import allure

from pages.base_page import BasePage

# 登录页路径（.env BASE_URL 后拼接）
LOGIN_PATH = "/login"


class LoginPage(BasePage):
    # 元素定位器（集中管理，方便维护；与计划文档 week3_day15.md 任务三一致）
    USERNAME_INPUT = "input[placeholder='请输入用户名或邮箱']"
    PASSWORD_INPUT = "input[placeholder='请输入密码']"
    LOGIN_BUTTON = "button:has-text('登录')"
    ERROR_MESSAGE = ".el-message--error"
    REGISTER_LINK = "a:has-text('注册')"
    REMEMBER_CHECKBOX = ".el-checkbox"  # "记住我"复选框
    CAPTCHA_ROW = ".captcha-row"  # 验证码区域（条件显示）

    def go(self, base_url: str):
        """打开登录页。"""
        self.navigate(f"{base_url}{LOGIN_PATH}")

    @allure.step("输入用户名或邮箱: {username}")
    def enter_username(self, username: str):
        """输入用户名或邮箱。"""
        self.fill(self.USERNAME_INPUT, username)

    @allure.step("输入密码")
    def enter_password(self, password: str):
        """输入密码。"""
        self.fill(self.PASSWORD_INPUT, password)

    @allure.step("点击登录按钮")
    def click_login(self):
        """点击登录按钮。"""
        self.click(self.LOGIN_BUTTON)

    def login(self, username: str, password: str):
        """组合登录操作：输入用户名/邮箱 + 密码 + 点击登录。"""
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

    def get_error_message(self) -> str:
        """获取错误提示文本（.el-message--error，Element Plus 消息约 3 秒自动消失）。"""
        self.wait_for_element(self.ERROR_MESSAGE, timeout=5_000)
        return self.get_text(self.ERROR_MESSAGE)

    def is_captcha_visible(self) -> bool:
        """验证码区域是否出现（条件显示，连续失败可能触发）。"""
        return self.is_visible(self.CAPTCHA_ROW)

    def go_to_register(self):
        """点击注册链接，进入注册页。"""
        self.click(self.REGISTER_LINK)
