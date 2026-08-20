"""ItemDetailPage：物品详情页 Page Object（Day17 认领流程）。

元素定位依据 2026-08-20 对真实详情页（/lost/detail/{id}）实测：
- 列表页点击物品卡片进入详情页（URL 形态 /lost/detail/{id}，直连也有效）；
- 其他用户发布且状态「待认领」的物品：显示「申请归还」按钮 → 点击弹出
  「申请归还」弹窗：申请说明 textarea（placeholder 要求描述物品特征/遗失场景，
  以证明是合法所有者）+ footer 按钮 取消 / 提交申请；
- 空说明提交 → 表单校验「请输入申请说明」（.el-form-item__error），弹窗不关闭；
- 已认领过的物品再次提交 → .el-message「您已申请过该物品，请勿重复申请」，
  弹窗不关闭（UI 文案与 API 层"该物品已被认领，请勿重复认领"不同，实测确认）；
- 自己发布的物品：无「申请归还」按钮，页面显示「不可归还自己的物品」
  （UI 层前置拦截，对应 API 契约"不能认领自己发布的物品"）；
- 认领成功后物品状态变「已认领」（2026-08-20 认领池耗尽未实测成功路径，
  断言基线待池恢复后回填——见 test_claim_ui.py 说明）。

用法（用例内）：
    item_detail_page.go(base_url, item_id)   # 直连详情页
    item_detail_page.click_apply_claim()     # 点「申请归还」打开弹窗
    item_detail_page.submit_claim("说明...") # 填说明并提交
"""

import re

import allure

from pages.base_page import BasePage

# 详情页路径（/lost/detail/{id}）
DETAIL_PATH = "/lost/detail"


class ItemDetailPage(BasePage):
    # 元素定位器（集中管理；与 2026-08-20 探测结果一一对应）
    APPLY_CLAIM_BUTTON = "text=申请归还"
    OWN_ITEM_HINT = "text=不可归还自己的物品"
    CLAIM_DIALOG = ".el-dialog"
    CLAIM_DESCRIPTION_INPUT = "textarea[placeholder*='详细描述']"
    DIALOG_CANCEL_BUTTON = "button:has-text('取消')"
    DIALOG_SUBMIT_BUTTON = "button:has-text('提交申请')"
    SUCCESS_MESSAGE = ".el-message--success"

    def go(self, base_url: str, item_id: int):
        """直连物品详情页（需登录，未登录会跳登录页）。"""
        self.navigate(f"{base_url}{DETAIL_PATH}/{item_id}")

    def get_item_id(self) -> int:
        """从当前 URL 解析物品 id（/lost/detail/{id}）。"""
        m = re.search(r"/lost/detail/(\d+)", self.page.url)
        assert m, f"当前 URL 不是详情页: {self.page.url}"
        return int(m.group(1))

    # ---------- 认领弹窗 ----------

    @allure.step("点击申请归还（打开认领弹窗）")
    def click_apply_claim(self):
        """点击「申请归还」，等待认领弹窗出现（仅他人物品且待认领时可见）。"""
        self.click(self.APPLY_CLAIM_BUTTON)
        self.page.locator(self.CLAIM_DIALOG).locator("visible=true").first.wait_for(
            state="visible", timeout=5_000
        )

    def get_claim_dialog(self):
        """当前可见的认领弹窗（Playwright Locator）。"""
        return self.page.locator(f"{self.CLAIM_DIALOG}:visible").first

    def fill_claim_description(self, text: str):
        """在认领弹窗填写申请说明。"""
        with allure.step("填写申请说明"):
            self.page.locator(self.CLAIM_DESCRIPTION_INPUT).fill(text)

    @allure.step("点击提交申请")
    def submit_claim(self):
        """点击认领弹窗「提交申请」按钮。"""
        self.get_claim_dialog().locator(self.DIALOG_SUBMIT_BUTTON).click()

    @allure.step("点击取消（关闭认领弹窗）")
    def cancel_claim(self):
        """点击认领弹窗「取消」按钮关闭弹窗。"""
        self.get_claim_dialog().locator(self.DIALOG_CANCEL_BUTTON).click()

    def is_claim_dialog_closed(self, timeout_ms: int = 2_000) -> bool:
        """认领弹窗是否已关闭（提交成功后应自动关闭）。"""
        dialog = self.page.locator(f"{self.CLAIM_DIALOG}:visible")
        for _ in range(timeout_ms // 200):
            if dialog.count() == 0:
                return True
            self.page.wait_for_timeout(200)
        return False

    def get_success_message(self) -> str:
        """获取认领成功提示文案（.el-message--success，Element Plus 消息约 3 秒消失）。"""
        self.wait_for_element(self.SUCCESS_MESSAGE, timeout=5_000)
        return self.get_text(self.SUCCESS_MESSAGE)

    # ---------- 状态/入口检查 ----------

    def _wait_claim_area_ready(self, timeout_ms: int = 5_000):
        """等待详情页认领区渲染完成：「申请归还」或「不可归还自己的物品」任一出现。

        2026-08-20 实测踩坑：open_card_detail 等 URL 跳转后 Vue 详情页仍在渲染，
        立即 is_visible() 会误判 False——先轮询等待两个互斥状态之一出现再判断。
        """
        claim_btn = self.page.locator(self.APPLY_CLAIM_BUTTON)
        own_hint = self.page.locator(self.OWN_ITEM_HINT)
        for _ in range(timeout_ms // 200):
            if claim_btn.count() > 0 or own_hint.count() > 0:
                return
            self.page.wait_for_timeout(200)

    def is_apply_claim_visible(self, timeout_ms: int = 5_000) -> bool:
        """「申请归还」按钮是否可见（他人物品且待认领时为 True；自己发布时为 False）。"""
        self._wait_claim_area_ready(timeout_ms)
        return self.is_visible(self.APPLY_CLAIM_BUTTON)

    def is_own_item_hint_visible(self, timeout_ms: int = 5_000) -> bool:
        """「不可归还自己的物品」提示是否可见（自己发布的物品详情页）。"""
        self._wait_claim_area_ready(timeout_ms)
        return self.is_visible(self.OWN_ITEM_HINT)
