"""注册流程 UI 自动化用例（Day16，5 条：4 条可执行 + 1 条缺陷阻断 skip）。

设计说明（与 week3_day16.md 任务二对应；行为依据 2026-08-19 实测 + 2026-08-20 复测修正）：
- 注册页字段必填校验实测文案：请输入用户名 / 请输入真实姓名 / 请输入邮箱地址 /
  请输入密码 / 请再次输入密码；邮箱格式错 →「邮箱格式不正确」；
  两次密码不一致 →「两次输入密码不一致!」；
- 不勾选协议点注册 → .el-message「请阅读并同意用户协议」（协议校验先于提交）；
- ⚠️ 前端缺陷（2026-08-19 初报描述有误，2026-08-20 复测定论，见 REGISTER_FLOW_BUG）：
  Day16 曾结论"勾选协议弹无法关闭的弹窗"——**已证伪**：点协议左侧小框正常勾选
  （原生 input.checked=True、is-checked=True、不弹窗）；点协议文本才弹「用户协议」
  弹窗，且弹窗内容渲染正常、footer「关闭」按钮有效。**真实缺陷**：注册提交
  payload 不含后端必填的 agreementAccepted 字段（前端把 agreement 字段剥离、
  字段名与后端契约不一致）→ 后端始终返回「请阅读并同意用户协议」→
  **UI 注册流程对任何用户都无法走通**；协议层（API）带 agreementAccepted=true
  可注册成功（接口项目 Day8 实测，2026-08-20 复验一致）。
  test_register_success 以 pytest.skip 显式跳过并注明缺陷，字段校验类用例不受影响；
- 注册成功需要管理员审核后方可登录（计划文档契约），注册页不自动登录。
"""

import allure
import pytest

# 统一测试密码（与接口自动化项目注册数据同款强度）
_PASSWORD = "Test123456"

# 缺陷阻断用例说明（2026-08-19 初报 → 2026-08-20 复测定论）
REGISTER_FLOW_BUG = (
    "前端缺陷（2026-08-20 定论）：注册提交 payload 不含后端必填的 agreementAccepted "
    "字段——前端表单模型字段名为 agreement 且提交时被解构剥离，后端契约（接口项目 "
    "Day8 实测）要求 agreementAccepted=true → 后端始终返回'请阅读并同意用户协议'，"
    "UI 注册流程对任何用户都无法走通。Day16 曾误报为'协议弹窗无法关闭'，已证伪："
    "勾选小框正常、弹窗可正常关闭（2026-08-20 实测，见 Day17 报告勘误）"
)


@allure.feature("注册流程 UI 自动化")
class TestRegisterUI:

    @allure.story("表单校验")
    @allure.title("真实姓名留空提交，显示必填校验提示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_missing_name(self, base_url, register_page):
        register_page.go(base_url)
        register_page.register(username="register_ui_test", name="", email="reg@example.com",
                               password=_PASSWORD)
        errors = register_page.get_form_errors()
        assert any("请输入真实姓名" in e for e in errors), f"应提示真实姓名必填: {errors}"
        register_page.screenshot("register_missing_name")

    @allure.story("表单校验")
    @allure.title("邮箱格式错误提交，显示邮箱格式校验提示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_invalid_email(self, base_url, register_page):
        register_page.go(base_url)
        register_page.register(username="register_ui_test", name="测试用户",
                               email="not-an-email", password=_PASSWORD)
        errors = register_page.get_form_errors()
        assert any("邮箱格式不正确" in e for e in errors), f"应提示邮箱格式错误: {errors}"
        register_page.screenshot("register_invalid_email")

    @allure.story("表单校验")
    @allure.title("两次输入的密码不一致，显示一致性校验提示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_password_mismatch(self, base_url, register_page):
        register_page.go(base_url)
        register_page.register(username="register_ui_test", name="测试用户",
                               email="mismatch@example.com", password=_PASSWORD,
                               confirm_password="Different999")
        errors = register_page.get_form_errors()
        assert any("两次输入密码不一致" in e for e in errors), f"应提示密码不一致: {errors}"
        register_page.screenshot("register_password_mismatch")

    @allure.story("协议校验")
    @allure.title("不勾选用户协议提交，提示请阅读并同意用户协议")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_agreement_not_checked(self, base_url, register_page):
        register_page.go(base_url)
        register_page.register(username="register_ui_test", name="测试用户",
                               email="agreement@example.com", password=_PASSWORD)
        messages = register_page.get_messages()
        assert any("请阅读并同意用户协议" in m for m in messages), \
            f"应提示阅读并同意用户协议: {messages}"
        register_page.screenshot("register_agreement_not_checked")

    @allure.story("正常注册")
    @allure.title("完整信息注册成功（受前端缺陷阻断，跳过并注明）")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_register_success(self, base_url, register_page):
        """注册成功用例。

        2026-08-20 复测定论（修正 Day16 结论）：勾选协议小框正常（原生 input
        checked、is-checked、不弹窗），「用户协议」弹窗可正常关闭；真实缺陷是
        提交 payload 缺后端必填的 agreementAccepted 字段（前端剥离 agreement、
        字段名与后端契约不一致）→ 后端始终返回「请阅读并同意用户协议」，
        注册成功流程对任何用户都无法走通（协议层带 agreementAccepted=true
        可注册成功，接口项目 Day8 已实测）。
        用例保留（缺陷修复后取消 skip 即可启用），当前显式跳过并记录缺陷。
        """
        pytest.skip(REGISTER_FLOW_BUG)
        # 缺陷修复后的执行体（保留作为验收基线；username 需唯一，修复后改为时间戳）
        register_page.go(base_url)
        register_page.register(username="register_ui_test", name="测试用户",
                               email="success@example.com", password=_PASSWORD)
        register_page.page.locator(".el-checkbox__inner").click()
        register_page.submit()
        register_page.page.wait_for_url("**/login", timeout=10_000)
        assert "/login" in register_page.page.url, "注册成功应跳转登录页（非自动登录）"
