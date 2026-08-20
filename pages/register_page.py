"""RegisterPage：失物招领系统注册页 Page Object（Day16，缺陷描述 Day17 复测修正）。

元素定位依据 2026-08-19 对真实注册页（/register）实测：
- 字段 placeholder 与计划文档一致：用户名 / 真实姓名 / 邮箱地址 /
  手机号码（选填）/ 设置密码 / 确认密码；
- 必填校验实测文案：请输入用户名 / 请输入真实姓名 / 请输入邮箱地址 /
  请输入密码 / 请再次输入密码；邮箱格式错 →「邮箱格式不正确」；
  两次密码不一致 →「两次输入密码不一致!」；
- 不勾选协议点注册 → .el-message「请阅读并同意用户协议」（协议校验先于提交）；
- ⚠️ 前端缺陷（2026-08-20 复测定论，修正 Day16 结论）：**勾选协议小框（协议文字
  左侧的 .el-checkbox__inner）是正常可用的**——原生 input.checked 变 true、
  is-checked 生效、不弹窗；点协议文本链接才弹「用户协议」弹窗，且弹窗内容渲染
  正常、footer「关闭」按钮有效。**真实缺陷**：注册提交 payload 不含后端必填的
  agreementAccepted 字段（前端把 agreement 字段解构剥离、字段名与后端契约不一致）
  → 后端始终返回「请阅读并同意用户协议」→ UI 注册流程对任何用户都无法走通。
  Day16 曾误报"弹窗无法关闭"，已证伪（复测记录见 Day17 测试运行报告勘误节）。
  因此本页 register() 组合操作不包含勾协议步骤，注册成功类用例需在前端修复后启用；
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
    # FORM_ERRORS / MESSAGE / get_form_errors / get_messages 已提升至 BasePage（Day17 重构）

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

    # get_form_errors / get_messages 由 BasePage 统一提供（Day17 重构，行为不变）
