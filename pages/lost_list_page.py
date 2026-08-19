"""LostListPage：失物信息列表页 Page Object（Day16）。

列表页是首页「发布失物信息」/「浏览失物信息」入口的落点（URL `/lost`），
承载搜索筛选与发布入口。元素定位依据 2026-08-19 对真实列表页实测：

- 标题搜索框 placeholder「请输入标题关键词」；**过滤只在点击"搜索"按钮后生效**
  （实测结论：输入 + 回车只更新 URL 不触发过滤；URL 参数 search/title/keyword
  直达也不过滤；点"搜索"按钮后 .el-card 变为匹配结果——zzzz 不存在关键词 → 0 张）；
- 「重置」按钮实测点击后列表变空（前端缺陷候选），用例不依赖重置；
- 页面另有 2 个 .el-select（分类/状态筛选）与分页 btn-prev/btn-next；
- 「发布失物信息」按钮进入发布页 /lost/publish（首页入口按钮的同类按钮）。

用法（用例内）：
    lost_list_page.go(base_url)
    lost_list_page.search("学生证")     # 输入关键词并点"搜索"按钮
    assert lost_list_page.get_item_count() > 0
"""

import allure

from pages.base_page import BasePage

# 列表页路径
LOST_LIST_PATH = "/lost"


class LostListPage(BasePage):
    # 元素定位器（集中管理；与探测结果一一对应）
    TITLE_SEARCH_INPUT = "input[placeholder*='标题']"
    SEARCH_BUTTON = "button:has-text('搜索')"
    RESET_BUTTON = "button:has-text('重置')"
    PUBLISH_BUTTON = "button:has-text('发布失物信息')"
    ITEM_CARDS = ".el-card"

    def go(self, base_url: str):
        """打开列表页。"""
        self.navigate(f"{base_url}{LOST_LIST_PATH}")

    @allure.step("按标题搜索: {keyword}")
    def search(self, keyword: str):
        """输入标题关键词并点击「搜索」按钮（过滤唯一生效路径，实测确认）。

        两个实测卡点（Day16 第 1~2 轮踩过，均已内置）：
        1) 标题输入框与路由 search 参数绑定，fill 会触发前端重渲染
           （输入框/按钮被替换），需等待重渲染稳定后再点搜索按钮；
        2) 点击「搜索」后 Vue 异步队列才发出查询请求——click 返回瞬间
           networkidle 会误判空闲（请求还没发出），断言将跑在请求完成前。
           解决：expect_response 精确等待 /api/lost-item/page 查询请求返回
           （有结果/无结果都会发同一请求，两种情况均适用）。
        """
        self.fill(self.TITLE_SEARCH_INPUT, keyword)
        self.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(600)  # 等 Vue 重渲染稳定（路由参数同步）
        with self.page.expect_response(
            lambda r: "/api/lost-item/page" in r.url and "title=" in r.url,
            timeout=10_000,
        ):
            self.click(self.SEARCH_BUTTON)
        self.page.wait_for_timeout(300)  # 响应返回后等 DOM 渲染完成

    def get_item_count(self) -> int:
        """当前列表物品卡片数量（搜索过滤后即结果数）。"""
        return self.page.locator(self.ITEM_CARDS).count()

    def get_card_texts(self) -> list[str]:
        """所有物品卡片的文本（用于断言搜索结果包含关键词）。"""
        return [c.inner_text() for c in self.page.locator(self.ITEM_CARDS).all()]

    def go_to_publish(self):
        """点击「发布失物信息」按钮进入发布页 /lost/publish。"""
        with allure.step("点击发布失物信息（列表页入口）"):
            self.click(self.PUBLISH_BUTTON)
            self.wait_for_url("**/lost/publish", timeout=10_000)
