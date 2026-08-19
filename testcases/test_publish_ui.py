"""失物发布流程 UI 自动化用例（Day16，4 条）。

设计说明（与 week3_day16.md 任务二对应；行为依据 2026-08-19 实测）：
- 发布页 /lost/publish 必填 4 项：标题 / 丢失地点 / 丢失时间 / 描述（+分类下拉），
  实测空表单提交校验提示 4 条同时出现；
- 发布成功标志：.el-message--success「发布成功」（实测文案）；
- test_publish_item_success 会向真实后端写入 1 条物品（标题带时间戳标记，
  与接口自动化项目同款"测试数据残留"策略，列表页可辨识为测试数据）；
- test_publish_without_login：未登录访问发布页会重定向登录页
  （实测 URL：/login?redirect=/lost/publish，redirect 参数保留回跳目标）。
"""

import time

import allure
import pytest

# 时间戳：保证发布标题唯一（多次运行互不冲突）
_STAMP = str(int(time.time() * 1000))

# 已知分类（2026-08-19 实测发布页下拉选项：证件类/电子产品/现金/卡类/生活用品/书籍资料/衣物饰品/其他）
CATEGORY = "电子产品"

# 搜索用已知存在的物品标题（2026-08-19 实测首页/列表页存在该数据）
KNOWN_ITEM_TITLE = "学生证"

# 必填校验提示（实测空表单提交的 4 条文案）
REQUIRED_ERRORS = {"请输入物品标题", "请输入丢失地点", "请选择丢失时间", "请输入物品描述"}


@allure.feature("失物发布流程 UI 自动化")
class TestPublishUI:

    @allure.story("正常发布")
    @allure.title("登录后完整发布失物信息，提示发布成功且列表页出现该物品")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_publish_item_success(self, base_url, logged_in_page, publish_page, lost_list_page):
        title = f"UI自动化发布物品_{_STAMP}"
        publish_page.go(base_url)
        publish_page.publish_item(
            title=title,
            category=CATEGORY,
            location="UI测试-图书馆大厅",
            description="UI 自动化测试发布的物品，用于验证发布流程，可忽略。",
            contact_name="测试联系人",
            contact_phone="13800138000",
        )
        # 成功提示（Element Plus 消息约 3 秒消失，内部显式等待）
        message = publish_page.get_success_message()
        assert "发布成功" in message, f"发布成功提示文案不符: {message}"
        publish_page.screenshot("publish_success")
        # 列表页搜索验证新物品出现（复用列表页过滤：输入标题关键词 + 点搜索）
        lost_list_page.go(base_url)
        lost_list_page.search(title)
        assert lost_list_page.get_item_count() > 0, "列表页搜索应出现新发布的物品"
        assert any(title in t for t in lost_list_page.get_card_texts()), \
            f"搜索结果应包含发布标题: {title}"

    @allure.story("异常发布")
    @allure.title("空表单提交发布，显示 4 条必填校验提示")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_publish_empty_required(self, base_url, logged_in_page, publish_page):
        publish_page.go(base_url)
        publish_page.submit()
        errors = set(publish_page.get_form_errors())
        assert REQUIRED_ERRORS.issubset(errors), \
            f"必填校验提示缺失: {REQUIRED_ERRORS - errors}（实际: {errors}）"
        publish_page.screenshot("publish_empty_required")

    @allure.story("异常发布")
    @allure.title("未登录访问发布页，重定向到登录页（带 redirect 回跳参数）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_publish_without_login(self, base_url, page, publish_page):
        publish_page.go(base_url)
        # 实测：未登录访问 /lost/publish → 重定向 /login?redirect=/lost/publish
        publish_page.wait_for_url("**/login**", timeout=10_000)
        assert "/login" in page.url, f"应跳转登录页: {page.url}"
        assert "redirect=/lost/publish" in page.url, f"应携带 redirect 回跳参数: {page.url}"
        # 登录页有登录表单（用户名/密码输入框），证明已回到登录页
        assert page.locator("input[placeholder='请输入用户名或邮箱']").is_visible(), \
            "跳转后的页面应显示登录表单"
        publish_page.screenshot("publish_without_login")

    @allure.story("表单交互")
    @allure.title("分类下拉框可选择目标分类（Element Plus 下拉组件）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_publish_category_select(self, base_url, logged_in_page, publish_page):
        publish_page.go(base_url)
        publish_page.select_category(CATEGORY)
        # 选中后下拉框应显示所选分类（.el-select__selected-item 存在 2 个元素
        # 触发 strict mode，改用 .el-select__wrapper 整体文本断言——实测踩过）
        selected = publish_page.page.locator(".el-select__wrapper").inner_text()
        assert CATEGORY in selected, f"分类选中值不符: {selected}"
        publish_page.screenshot("publish_category_select")
