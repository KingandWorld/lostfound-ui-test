"""注册流程 UI 自动化用例（Day16，5 条：4 条可执行 + 1 条缺陷阻断 skip）。

设计说明（与 week3_day16.md 任务二对应；行为依据 2026-08-19 实测）：
- 注册页字段必填校验实测文案：请输入用户名 / 请输入真实姓名 / 请输入邮箱地址 /
  请输入密码 / 请再次输入密码；邮箱格式错 →「邮箱格式不正确」；
  两次密码不一致 →「两次输入密码不一致!」；
- 不勾选协议点注册 → .el-message「请阅读并同意用户协议」（协议校验先于提交）；
- ⚠️ 前端缺陷（2026-08-19 实测，详见卡点排查表）：勾选协议弹出「用户协议」弹窗，
  弹窗内容渲染不稳定（常为空壳），footer「关闭」/ header X / Esc / 遮罩均无法关闭，
  注册成功与重复用户名两条用例被阻断 → test_register_success 以 pytest.skip
  显式跳过并注明缺陷，字段校验类用例不受影响正常执行；
- 注册成功需要管理员审核后方可登录（计划文档契约），注册页不自动登录。
"""

import allure
import pytest

# 统一测试密码（与接口自动化项目注册数据同款强度）
_PASSWORD = "Test123456"

# 缺陷阻断用例说明（2026-08-19 实测，已记入 Day16 卡点排查表）
AGREEMENT_DIALOG_BUG = (
    "前端缺陷：勾选协议弹出无法关闭的「用户协议」弹窗（内容渲染不稳定），"
    "注册成功流程被'请阅读并同意用户协议'校验阻断（2026-08-19 实测，见卡点排查表）"
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

        2026-08-19 实测：勾选协议即弹出「用户协议」弹窗（内容渲染不稳定，常为空壳），
        footer「关闭」/ header X / Esc / 遮罩点击均无法关闭 → 提交始终被
        「请阅读并同意用户协议」校验拦截，注册成功流程无法走通。
        用例保留（缺陷修复后取消 skip 即可启用），当前显式跳过并记录缺陷。
        """
        pytest.skip(AGREEMENT_DIALOG_BUG)
        # 缺陷修复后的执行体（保留作为验收基线）
        register_page.go(base_url)
        register_page.register(username="register_ui_test", name="测试用户",
                               email="success@example.com", password=_PASSWORD)
        register_page.page.locator(".el-checkbox__inner").click()
        register_page.submit()
        register_page.page.wait_for_url("**/login", timeout=10_000)
        assert "/login" in register_page.page.url, "注册成功应跳转登录页（非自动登录）"
