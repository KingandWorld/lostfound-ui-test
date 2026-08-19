"""HomePage：失物招领系统首页 Page Object（Day16）。

元素定位依据 2026-08-19 对真实首页实测（与 week3_day16.md 任务一一致）：
- 首页搜索框 placeholder「搜索你遗失的物品...」，输入 + 回车会跳转列表页
  `/lost?search=关键词`（实测跳转生效，但列表过滤只有点"搜索"按钮才生效，
  见 lost_list_page.py 的说明——首页搜索只做"入口"角色）；
- 首页主要入口是按钮而非链接（实测）：浏览失物信息 / 发布失物信息 / 查看全部；
- 物品卡片是 .el-card（首页默认 8 张），卡片文本结构：
  分类 | 📌 | 标题 | 地点 | 日期 | 状态；
- 用户头像 .user-avatar 存在（登录后可见，可作为"已登录"标志）。

用法（用例内）：
    home_page.go(base_url)
    home_page.search("学生证")     # 输入关键词并回车，跳转列表页
    home_page.go_to_publish()      # 点击「发布失物信息」进入列表页
"""

import allure

from pages.base_page import BasePage

# 首页路径
HOME_PATH = "/"


class HomePage(BasePage):
    # 元素定位器（集中管理；与探测结果一一对应）
    SEARCH_INPUT = "input[placeholder*='搜索']"
    BROWSE_BUTTON = "button:has-text('浏览失物信息')"
    PUBLISH_BUTTON = "button:has-text('发布失物信息')"
    VIEW_ALL_BUTTON = "button:has-text('查看全部')"
    ITEM_CARDS = ".el-card"
    USER_AVATAR = ".user-avatar"

    def go(self, base_url: str):
        """打开首页。"""
        self.navigate(f"{base_url}{HOME_PATH}")

    @allure.step("首页搜索: {keyword}")
    def search(self, keyword: str):
        """输入关键词并回车，跳转列表页 /lost?search=...。

        实测：首页搜索回车会跳转 /lost 并携带 search 参数，但列表页过滤
        需在列表页点"搜索"按钮才生效——搜索断言请使用 LostListPage.search()。
        """
        self.fill(self.SEARCH_INPUT, keyword)
        self.page.keyboard.press("Enter")
        self.wait_for_load_state("networkidle")

    def go_to_publish(self):
        """点击「发布失物信息」按钮（实测为按钮而非链接），进入列表页 /lost。"""
        with allure.step("点击发布失物信息（首页入口）"):
            self.click(self.PUBLISH_BUTTON)

    def get_item_count(self) -> int:
        """首页物品卡片数量。"""
        return self.page.locator(self.ITEM_CARDS).count()

    def is_logged_in(self) -> bool:
        """用户头像是否可见（登录后的标志）。"""
        return self.is_visible(self.USER_AVATAR)
