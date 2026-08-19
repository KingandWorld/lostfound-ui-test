"""RegisterPage：失物招领系统注册页 Page Object（Day16）。

元素定位依据 2026-08-19 对真实注册页（/register）实测：
- 字段 placeholder 与计划文档一致：用户名 / 真实姓名 / 邮箱地址 /
  手机号码（选填）/ 设置密码 / 确认密码；
- 必填校验实测文案：请输入用户名 / 请输入真实姓名 / 请输入邮箱地址 /
  请输入密码 / 请再次输入密码；邮箱格式错 →「邮箱格式不正确」；
  两次密码不一致 →「两次输入密码不一致!」；
- 不勾选协议点注册 → .el-message「请阅读并同意用户协议」（协议校验在后端提交前拦截）；
- ⚠️ 前端缺陷（2026-08-19 实测，已记入卡点排查表）：勾选协议会弹出「用户协议」
  弹窗，弹窗内容渲染不稳定（常为空壳），且 footer「关闭」/ header X / Esc /
  遮罩点击均无法关闭 → 注册成功流程被阻断（一直报"请阅读并同意用户协议"）。
  因此本页 register() 组合操作不包含勾协议步骤，注册成功类用例需在缺陷修复后启用；
- 注册成功需要管理员审核后方可登录（计划文档契约），且注册页不自动登录。

用法（用例内）：
    register_page.go(base_url)
    register_page.register(username=..., name=..., email=..., password=...)  # 不含勾协议
"""

import allure

from pages.base_page import BasePage

# 注册页路径
REGISTER_PATH = "/register"


class RegisterPage(BasePage):
    # 元素定位器（集中管理；与探测结果一一对应）
    USERNAME_INPUT = "input[placeholder='用户名']"
    NAME_INPUT = "input[placeholder='真实姓名']"
    EMAIL_INPUT = "input[placeholder='邮箱地址']"
    PHONE_INPUT = "input[placeholder='手机号码（选填）']"
    PASSWORD_INPUT = "input[placeholder='设置密码']"
    CONFIRM_PASSWORD_INPUT = "input[placeholder='确认密码']"
    AGREEMENT_CHECKBOX = ".el-checkbox"
    REGISTER_BUTTON = "button:has-text('注册')"
    FORM_ERRORS = ".el-form-item__error"
    MESSAGE = ".el-message"

    def go(self, base_url: str):
        """打开注册页。"""
        self.navigate(f"{base_url}{REGISTER_PATH}")

    @allure.step("填写注册表单: {username}")
    def fill_form(
        self,
        username: str,
        name: str,
        email: str,
        password: str,
        confirm_password: str = None,
        phone: str = "",
    ):
        """填写注册表单字段（不含勾选协议与提交）。"""
        self.fill(self.USERNAME_INPUT, username)
        self.fill(self.NAME_INPUT, name)
        self.fill(self.EMAIL_INPUT, email)
        if phone:
            self.fill(self.PHONE_INPUT, phone)
        self.fill(self.PASSWORD_INPUT, password)
        self.fill(self.CONFIRM_PASSWORD_INPUT, confirm_password or password)

    def register(
        self,
        username: str,
        name: str,
        email: str,
        password: str,
        confirm_password: str = None,
        phone: str = "",
    ):
        """组合注册流程：填表单 + 点注册。

        注意：不含勾选协议步骤——实测勾选协议会弹出无法关闭的「用户协议」
        弹窗（前端缺陷，见类注释），注册成功类用例受阻断。
        """
        self.fill_form(username, name, email, password, confirm_password, phone)
        self.submit()

    def submit(self):
        """点击注册按钮。"""
        with allure.step("点击注册"):
            self.click(self.REGISTER_BUTTON)

    def get_form_errors(self) -> list[str]:
        """获取表单字段校验提示文案（提交后异步渲染，先轮询等待再读取）。"""
        errors_locator = self.page.locator(self.FORM_ERRORS)
        for _ in range(10):  # 最长等待 ~2s
            if errors_locator.count() > 0:
                break
            self.page.wait_for_timeout(200)
        return [e.inner_text() for e in errors_locator.all()]

    def get_messages(self) -> list[str]:
        """获取全局消息（.el-message，如"请阅读并同意用户协议"；约 3 秒自动消失）。"""
        messages_locator = self.page.locator(self.MESSAGE)
        for _ in range(10):  # 最长等待 ~2s
            if messages_locator.count() > 0:
                break
            self.page.wait_for_timeout(200)
        return [m.inner_text() for m in messages_locator.all()]
