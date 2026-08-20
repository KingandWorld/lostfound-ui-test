"""PublishPage：失物信息发布页 Page Object（Day16）。

元素定位依据 2026-08-19 对真实发布页（/lost/publish）实测：
- 表单必填 4 项（实测空表单提交校验提示）：物品标题 / 丢失地点 / 丢失时间 / 物品描述；
- 分类为 Element Plus 下拉（.el-select），选项实测：
  证件类/电子产品/现金/卡类/生活用品/书籍资料/衣物饰品/其他；
- 丢失时间需点开日期面板选「此刻」（面板内 el-picker-panel 的快捷按钮）再回车确认；
- 物品图片上传 .el-upload + input[type='file']（最多 5 张、每张 2MB，用例未做上传）；
- 联系人/联系电话/联系邮箱/备注为选填；
- 提交按钮文本「发布」——页面同时存在「发布失物信息」导航按钮，
  has-text('发布') 会命中两个元素，故限定在表单内定位（.el-form button）；
- 发布成功标志：.el-message--success「发布成功」（实测文案）。

用法（用例内）：
    publish_page.go(base_url)
    publish_page.publish_item(title=..., category="电子产品", location=...)
"""

import allure

from pages.base_page import BasePage

# 发布页路径
PUBLISH_PATH = "/lost/publish"


class PublishPage(BasePage):
    # 元素定位器（集中管理；与探测结果一一对应）
    TITLE_INPUT = "input[placeholder='请输入物品标题']"
    CATEGORY_SELECT = ".el-select"
    CATEGORY_OPTION = ".el-select-dropdown__item"
    LOCATION_INPUT = "input[placeholder='请输入丢失地点']"
    LOST_TIME_INPUT = "input[placeholder='请选择丢失时间']"
    DESCRIPTION_TEXTAREA = "textarea[placeholder*='描述']"
    IMAGE_INPUT = "input[type='file']"
    CONTACT_NAME_INPUT = "input[placeholder='请输入联系人姓名']"
    CONTACT_PHONE_INPUT = "input[placeholder='请输入联系电话']"
    CONTACT_EMAIL_INPUT = "input[placeholder='请输入联系邮箱']"
    SUBMIT_BUTTON = ".el-form button:has-text('发布')"  # 避开"发布失物信息"导航按钮
    SUCCESS_MESSAGE = ".el-message--success"
    # FORM_ERRORS / get_form_errors 已提升至 BasePage（Day17 重构）

    def go(self, base_url: str):
        """打开发布页（需登录，未登录会跳登录页并带 redirect 参数）。"""
        self.navigate(f"{base_url}{PUBLISH_PATH}")

    @allure.step("选择分类: {category_name}")
    def select_category(self, category_name: str):
        """Element Plus 下拉：点开 → 等选项列表 → 点目标选项（实测选项见类注释）。"""
        self.click(self.CATEGORY_SELECT)
        self.page.locator(self.CATEGORY_OPTION).first.wait_for(
            state="visible", timeout=5_000
        )
        self.page.locator(f"{self.CATEGORY_OPTION}:has-text('{category_name}')").click()

    @allure.step("选择丢失时间为此刻")
    def pick_lost_time_now(self):
        """丢失时间：点开日期面板 → 点「此刻」快捷按钮 → 回车确认（实测可行）。"""
        self.click(self.LOST_TIME_INPUT)
        self.page.locator("button:has-text('此刻')").first.wait_for(
            state="visible", timeout=5_000
        )
        self.page.locator("button:has-text('此刻')").first.click()
        self.wait_for_load_state("domcontentloaded")
        self.page.keyboard.press("Enter")

    def publish_item(
        self,
        title: str,
        category: str,
        location: str,
        description: str,
        contact_name: str = "",
        contact_phone: str = "",
    ):
        """组合发布流程：标题 + 分类 + 地点 + 时间 + 描述（必填 4 项 + 分类）。

        时间统一取"此刻"；联系方式选填（不传则不填）。不处理图片上传。
        """
        self.fill(self.TITLE_INPUT, title)
        self.select_category(category)
        self.fill(self.LOCATION_INPUT, location)
        self.pick_lost_time_now()
        self.fill(self.DESCRIPTION_TEXTAREA, description)
        if contact_name:
            self.fill(self.CONTACT_NAME_INPUT, contact_name)
        if contact_phone:
            self.fill(self.CONTACT_PHONE_INPUT, contact_phone)
        self.submit()

    def submit(self):
        """点击「发布」提交按钮。"""
        with allure.step("点击发布（提交表单）"):
            self.click(self.SUBMIT_BUTTON)

    def get_success_message(self) -> str:
        """获取发布成功提示文案（.el-message--success，Element Plus 消息约 3 秒消失）。"""
        self.wait_for_element(self.SUCCESS_MESSAGE, timeout=5_000)
        return self.get_text(self.SUCCESS_MESSAGE)

    # get_form_errors 由 BasePage 统一提供（Day17 重构，行为不变）
