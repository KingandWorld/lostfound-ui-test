"""登录流程 UI 自动化用例（Day15，5 条）。

设计说明（与 week3_day15.md 任务四对应；行为依据 2026-08-18 探测实测）：
- 数据来自 .env（TEST_USERNAME/TEST_PASSWORD/TEST_EMAIL），与接口自动化项目
  共用同一测试账号，实现"同一账号、接口层与 UI 层双重验证"；
- 登录成功：URL 跳转根路径 /（测试账号 roleCode=USER 普通用户；管理员跳
  /back/dashboard），token 写入 localStorage['token']——与接口层"自定义 Header token"呼应；
- 错误密码用例放在最后：连续 5 次失败触发 15 分钟账号锁定（接口层实测契约，
  成功登录重置计数）；本用例在成功用例之后执行，每次运行净增 1 次失败；
  断言采用"出现错误提示即通过"的宽断言，即使命中锁定提示也不误报；
- 邮箱登录用例使用 .env 的 TEST_EMAIL（探测确认 /api/user/current 返回 email 字段、
  登录表单支持邮箱输入）；未配置邮箱时跳过。
"""

import allure
import pytest

# 错误密码：与接口层同一值（test_login.py wrong_password），保证"计数型失败"行为一致
WRONG_PASSWORD = "WrongPass123"

# 成功登录后的首页 URL glob（普通用户跳根路径 /；管理员跳 /back/dashboard）
HOME_URL_GLOB = "**/"


@allure.feature("登录流程 UI 自动化")
class TestLoginUI:

    @allure.story("正常登录")
    @allure.title("使用正确的用户名密码登录，跳转到首页且 token 写入 localStorage")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_login_success(self, base_url, login_page, user_credentials):
        login_page.go(base_url)
        login_page.login(user_credentials["username"], user_credentials["password"])
        # 等待登录成功标志：URL 离开 /login 跳转首页（自动等待，不盲等）
        login_page.wait_for_url(HOME_URL_GLOB, timeout=15_000)
        login_page.wait_for_load_state()
        assert login_page.page.url.rstrip("/").endswith(base_url.rstrip("/")), \
            f"应跳转首页: {login_page.page.url}"
        assert login_page.page.evaluate(
            "localStorage.getItem('token')"
        ), "登录成功后 localStorage 应写入 token"
        login_page.screenshot("login_success")

    @allure.story("正常登录")
    @allure.title("使用邮箱登录，同样登录成功")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_with_email(self, base_url, login_page, user_credentials):
        email = user_credentials["email"]
        if not email:
            pytest.skip("未配置 TEST_EMAIL，邮箱登录用例跳过（表单已支持用户名或邮箱输入）")
        login_page.go(base_url)
        # 邮箱输入框与用户名输入框是同一个（placeholder「请输入用户名或邮箱」）
        login_page.login(email, user_credentials["password"])
        login_page.wait_for_url(HOME_URL_GLOB, timeout=15_000)
        assert login_page.page.evaluate(
            "localStorage.getItem('token')"
        ), "邮箱登录成功后应写入 token"
        login_page.screenshot("login_with_email")

    @allure.story("异常登录")
    @allure.title("错误密码登录，页面显示错误提示（不跳转、不写 token）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_wrong_password(self, base_url, login_page, user_credentials):
        login_page.go(base_url)
        login_page.login(user_credentials["username"], WRONG_PASSWORD)
        # Element Plus 错误消息约 3 秒自动消失，get_error_message 内部显式等待后立即读取；
        # 实测文案「用户名或密码错误，还剩 N 次尝试机会」——只断言固定前缀，兼容剩余次数
        message = login_page.get_error_message()
        assert "用户名或密码错误" in message, f"错误提示文案不符: {message}"
        # 仍停留在登录页，未写入 token
        assert "/login" in login_page.page.url, f"失败后不应跳转: {login_page.page.url}"
        assert not login_page.page.evaluate(
            "localStorage.getItem('token')"
        ), "登录失败不应写入 token"
        login_page.screenshot("login_wrong_password")

    @allure.story("异常登录")
    @allure.title("空表单提交，显示前端必填校验提示")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_empty_form(self, base_url, login_page):
        login_page.go(base_url)
        login_page.click_login()
        # Element Plus 表单校验提示（.el-form-item__error）在输入框下方，实测文案：
        # 「请输入用户名或邮箱」「请输入密码」；两个提示同时出现，.first 避开 strict mode
        login_page.page.locator(".el-form-item__error").first.wait_for(
            state="visible", timeout=5_000
        )
        errors = login_page.page.locator(".el-form-item__error").all()
        assert errors, "空表单提交应显示必填校验提示"
        texts = [e.inner_text() for e in errors]
        assert any("用户名或邮箱" in t for t in texts), f"应提示用户名/邮箱必填: {texts}"
        assert any("密码" in t for t in texts), f"应提示密码必填: {texts}"
        login_page.screenshot("login_empty_form")

    @allure.story("页面跳转")
    @allure.title("点击注册链接，跳转到注册页")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_redirect_to_register(self, base_url, login_page):
        login_page.go(base_url)
        login_page.go_to_register()
        login_page.wait_for_url("**/register", timeout=10_000)
        assert "register" in login_page.page.url, f"应跳转到注册页: {login_page.page.url}"
        login_page.screenshot("login_to_register")
