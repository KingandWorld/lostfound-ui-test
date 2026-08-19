"""失物搜索流程 UI 自动化用例（Day16，2 条）。

设计说明（与 week3_day16.md 任务二对应；行为依据 2026-08-19 实测）：
- 搜索过滤只在列表页 /lost 点「搜索」按钮后生效（实测：输入 + 回车只更新
  URL 不过滤；URL 参数直达不过滤；点搜索按钮后 .el-card 变为匹配结果）；
- 已知存在的物品：标题含「学生证」（实测首页/列表页第一条卡片即"学生证丢了"，
  与接口自动化项目测试数据同源）；
- 无结果关键词：zzzz 开头随机串（数据库不存在 → 卡片 0 张，实测无 .el-empty
  空状态组件，直接断言卡片数）；
- 搜索用例需要登录（列表页未登录会跳登录页）。
"""

import allure

# 已知存在的物品标题关键词（2026-08-19 实测列表页存在该数据）
KNOWN_KEYWORD = "学生证"

# 不存在的关键词（实测点搜索后 .el-card = 0）
NONE_KEYWORD = "zzzz不存在的关键词zzzz"


@allure.feature("失物搜索流程 UI 自动化")
class TestSearchUI:

    @allure.story("正常搜索")
    @allure.title("搜索已知存在的物品关键词，结果列表包含该物品")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_existing_item(self, base_url, logged_in_page, lost_list_page):
        lost_list_page.go(base_url)
        lost_list_page.search(KNOWN_KEYWORD)
        assert lost_list_page.get_item_count() > 0, "搜索已知物品应返回结果"
        texts = lost_list_page.get_card_texts()
        assert any(KNOWN_KEYWORD in t for t in texts), \
            f"搜索结果应包含关键词 '{KNOWN_KEYWORD}': {texts[:2]}"
        lost_list_page.screenshot("search_existing_item")

    @allure.story("异常搜索")
    @allure.title("搜索不存在的关键词，结果列表为空")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_no_result(self, base_url, logged_in_page, lost_list_page):
        lost_list_page.go(base_url)
        lost_list_page.search(NONE_KEYWORD)
        assert lost_list_page.get_item_count() == 0, \
            "搜索不存在关键词应返回空结果（实测无 .el-empty 提示，直接为 0 张卡片）"
        lost_list_page.screenshot("search_no_result")
