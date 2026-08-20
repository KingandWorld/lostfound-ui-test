"""认领流程 UI 自动化用例（Day17，5 条）。

设计说明（与 week3_day17.md 任务一对应；行为依据 2026-08-20 实测）：
- 认领入口在详情页 /lost/detail/{id}（列表页点卡片进入，直连也有效）；
  其他用户发布且「待认领」的物品显示「申请归还」按钮，点击弹出「申请归还」
  弹窗：申请说明 textarea + 取消/提交申请；
- 空说明提交 → 表单校验「请输入申请说明」（弹窗不关闭）；
- 已认领过的物品再次提交 → .el-message「您已申请过该物品，请勿重复申请」
  （UI 文案与 API 层"该物品已被认领，请勿重复认领"不同，实测确认）；
- 自己发布的物品详情页无「申请归还」按钮，显示「不可归还自己的物品」
  （UI 层前置拦截，对应 API 契约"不能认领自己发布的物品"）；
- ⚠️ 认领池现状（2026-08-20 实测）：本账号 13 条历史认领单已覆盖所有他人物品
  （含已取消——系统缺陷：物品一旦被认领即永久不可再次认领），
  test_claim_success 依赖认领池，池空时按接口项目同款策略 skip（后台重置后可跑）；
- 数据策略：test_claim_success 成功认领会消耗认领池（1 条/轮），teardown 用
  API PUT /api/claim/cancel/{id} 取消认领单（保持认领列表整洁；已取消仍耗池）；
  拒绝路径（空说明/重复申请/自己物品）不产生数据，无需清理。
"""

import time

import allure
import pytest
import requests

# 时间戳：保证发布的物品标题唯一（多次运行互不冲突）
_STAMP = str(int(time.time() * 1000))

# 本账号发布物的标题前缀（2026-08-20 实测枚举列表页/接口列表：
# 本账号发布/创建的物品标题均带测试前缀，扫描候选卡片时排除）
OWN_TITLE_PREFIXES = (
    "UI自动化发布物品_", "UI测试发布物品_",
    "端到端发布物品_", "端到端招领发布物品_",
    "Postman测试失物_", "自动化搜索物品_",
)

# 已知被本账号认领过的种子物品（2026-08-20 实测：id=3「学生证丢了」在历史认领单中，
# 详情页仍显示「待认领」且可打开认领弹窗，提交即被拒「您已申请过该物品」——
# 用作重复申请拒绝路径的确定性锚点；若后台重置数据后该物品可认领，用例会 skip）
KNOWN_CLAIMED_ITEM_ID = 3

# 认领说明（与接口自动化项目 test_claims.py 同款风格）
CLAIM_DESCRIPTION = "这是我的证件，姓名与照片完全吻合，请求归还（UI 自动化测试数据）。"


def _my_claimed_item_ids(base_url: str, headers: dict) -> set[int]:
    """本账号已认领过的全部物品 ID（API 只读；含已取消——系统对曾认领物品永久拒绝再次认领）。"""
    claimed: set[int] = set()
    for page in range(1, 6):
        resp = requests.get(f"{base_url}/api/claim/my",
                            params={"currentPage": page, "size": 50},
                            headers=headers, timeout=10)
        records = (resp.json().get("data") or {}).get("records") or []
        for rec in records:
            claimed.add(rec.get("itemId"))
        if len(records) < 50:
            break
    return claimed


def _cancel_claims_on(base_url: str, headers: dict, item_id: int):
    """取消对指定物品发起的全部认领单（teardown 清理，保持认领列表整洁）。"""
    resp = requests.get(f"{base_url}/api/claim/my",
                        params={"currentPage": 1, "size": 50},
                        headers=headers, timeout=10)
    records = (resp.json().get("data") or {}).get("records") or []
    for rec in records:
        if rec.get("itemId") == item_id:
            requests.put(f"{base_url}/api/claim/cancel/{rec['id']}",
                         headers=headers, timeout=10)


def _pick_claim_card_index(card_texts: list[str]) -> int | None:
    """列表页找可发起认领的卡片：状态「待认领」且标题非本账号测试前缀。

    注意：卡片文本不含发布者，本账号发布物靠标题前缀排除（实测枚举）；
    已认领过的物品状态仍显示「待认领」（系统缺陷），是否可认领需
    test_claim_success 里经详情页按钮可见性 + API 认领单双重复核。
    """
    for i, text in enumerate(card_texts):
        if "待认领" in text and not any(p in text for p in OWN_TITLE_PREFIXES):
            return i
    return None


@allure.feature("认领流程 UI 自动化")
class TestClaimUI:

    @allure.story("认领弹窗")
    @allure.title("详情页点击申请归还，弹出认领弹窗（说明输入框 + 取消/提交按钮）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_claim_dialog_opens(self, base_url, logged_in_page, lost_list_page, item_detail_page):
        """认领入口与弹窗结构（实测基线：2026-08-20）。"""
        lost_list_page.go(base_url)
        idx = _pick_claim_card_index(lost_list_page.get_card_texts())
        assert idx is not None, "列表页未找到「待认领」且非本账号测试前缀的物品卡片"
        lost_list_page.open_card_detail(idx)
        assert item_detail_page.is_apply_claim_visible(), "他人物品详情页应显示「申请归还」"
        item_detail_page.click_apply_claim()
        dialog = item_detail_page.get_claim_dialog()
        # 弹窗标题与说明输入框（placeholder 实测文案）
        header_text = dialog.locator(".el-dialog__header").inner_text()
        assert "申请归还" in header_text, f"弹窗标题不符: {header_text}"
        textarea = dialog.locator("textarea")
        assert "详细描述" in (textarea.get_attribute("placeholder") or ""), \
            "申请说明输入框 placeholder 应为描述物品特征/遗失场景"
        # footer 按钮
        buttons = [b.inner_text() for b in dialog.locator(".el-dialog__footer button").all()]
        assert "取消" in buttons and "提交申请" in buttons, f"弹窗按钮不符: {buttons}"
        item_detail_page.cancel_claim()
        item_detail_page.screenshot("claim_dialog_opens")

    @allure.story("表单校验")
    @allure.title("空申请说明提交，显示必填校验提示且弹窗不关闭")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_claim_empty_description(self, base_url, logged_in_page, lost_list_page, item_detail_page):
        """空说明提交被前端校验拦截（实测文案「请输入申请说明」）。"""
        lost_list_page.go(base_url)
        idx = _pick_claim_card_index(lost_list_page.get_card_texts())
        assert idx is not None, "列表页未找到「待认领」且非本账号测试前缀的物品卡片"
        lost_list_page.open_card_detail(idx)
        item_detail_page.click_apply_claim()
        item_detail_page.submit_claim()
        errors = item_detail_page.get_form_errors()
        assert any("请输入申请说明" in e for e in errors), f"应提示申请说明必填: {errors}"
        assert not item_detail_page.is_claim_dialog_closed(), \
            "校验失败后认领弹窗应保持打开"
        item_detail_page.cancel_claim()
        item_detail_page.screenshot("claim_empty_description")

    @allure.story("异常认领")
    @allure.title("对已认领过的物品再次申请，提示请勿重复申请")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_claim_duplicate_rejected(self, base_url, logged_in_page, item_detail_page, api_headers):
        """重复申请被拒绝（2026-08-20 实测 UI 文案「您已申请过该物品，请勿重复申请」）。

        数据前置：锚点物品（学生证丢了）须确在本账号历史认领单中——若后台重置
        了认领数据导致该物品可认领，本用例场景失效，skip 并提示人工确认。
        """
        claimed = _my_claimed_item_ids(base_url, api_headers)
        if KNOWN_CLAIMED_ITEM_ID not in claimed:
            pytest.skip("「学生证丢了」当前不在本账号历史认领单中（认领数据已重置？），"
                        "重复申请场景失效，请人工确认锚点数据")
        item_detail_page.go(base_url, KNOWN_CLAIMED_ITEM_ID)
        assert item_detail_page.is_apply_claim_visible(), "锚点物品应显示「申请归还」（状态为待认领）"
        item_detail_page.click_apply_claim()
        item_detail_page.fill_claim_description(CLAIM_DESCRIPTION)
        item_detail_page.submit_claim()
        messages = item_detail_page.get_messages()
        assert any("您已申请过该物品，请勿重复申请" in m for m in messages), \
            f"应提示重复申请被拒: {messages}"
        item_detail_page.screenshot("claim_duplicate_rejected")

    @allure.story("异常认领")
    @allure.title("自己发布的物品详情页无申请归还按钮（UI 层拦截自认领）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_claim_own_item_no_button(self, base_url, logged_in_page, publish_page,
                                      lost_list_page, item_detail_page):
        """自己发布物品不可认领（对应 API"不能认领自己发布的物品"，UI 层前置拦截）。

        流程：先发布一条自己的物品（标题带时间戳），再进详情页断言无认领入口。
        """
        title = f"UI认领测试物品_{_STAMP}"
        publish_page.go(base_url)
        publish_page.publish_item(
            title=title,
            category="证件类",
            location="UI测试-图书馆大厅",
            description="UI 自动化测试发布的物品（认领自拦截用例），可忽略。",
        )
        message = publish_page.get_success_message()
        assert "发布成功" in message, f"发布成功提示文案不符: {message}"
        # 列表页搜索自己的标题 → 点进详情
        lost_list_page.go(base_url)
        lost_list_page.search(title)
        assert lost_list_page.get_item_count() > 0, "列表页应搜到刚发布的物品"
        lost_list_page.open_card_detail(0)
        assert not item_detail_page.is_apply_claim_visible(), \
            "自己发布的物品不应显示「申请归还」按钮"
        assert item_detail_page.is_own_item_hint_visible(), \
            "自己发布的物品详情页应显示「不可归还自己的物品」"
        item_detail_page.screenshot("claim_own_item_no_button")

    @allure.story("正常认领")
    @allure.title("对他人待认领物品完整发起认领（依赖认领池，池空时跳过）")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_claim_success(self, base_url, logged_in_page, lost_list_page,
                           item_detail_page, api_headers, claimed_item_cleanup):
        """完整认领成功流程。

        ⚠️ 2026-08-20 实测：本账号 13 条历史认领单已覆盖所有他人物品（系统缺陷：
        物品一旦被认领即使取消也永久不可再认领），认领池耗尽 → 本用例 skip，
        与接口自动化项目 test_claims.py 的 others_item fixture 同款策略。
        后台重置种子数据后自动恢复执行。

        候选选择三重校验（UI + API 双重复核）：
        1) 列表页卡片：状态「待认领」且标题非本账号测试前缀；
        2) 详情页有「申请归还」按钮（非本账号发布）；
        3) API 认领单确认该物品未被本账号认领过。
        认领成功后 teardown 用 API 取消认领单（保持认领列表整洁）。
        """
        claimed = _my_claimed_item_ids(base_url, api_headers)
        lost_list_page.go(base_url)
        candidate_id = None
        for text in lost_list_page.get_card_texts():
            if "待认领" not in text or any(p in text for p in OWN_TITLE_PREFIXES):
                continue  # 状态非待认领 / 本账号测试前缀 → 跳过
            lost_list_page.open_card_detail(0)
            item_id = item_detail_page.get_item_id()
            if item_id in claimed or not item_detail_page.is_apply_claim_visible():
                lost_list_page.go(base_url)  # 已被认领过 / 是自己发布的 → 换下一张
                continue
            candidate_id = item_id
            break
        if candidate_id is None:
            pytest.skip("认领池已耗尽（本账号历史认领单覆盖全部他人物品），"
                        "请在系统后台重置种子数据后重跑")
        # 发起认领
        item_detail_page.click_apply_claim()
        item_detail_page.fill_claim_description(CLAIM_DESCRIPTION)
        item_detail_page.submit_claim()
        # 成功断言（认领池耗尽期间无法实测成功文案/状态标签，按最小可验证设计：
        # 成功提示出现 + 弹窗关闭；池恢复后回填实测文案与「已认领」状态断言）
        success_message = item_detail_page.get_success_message()
        assert success_message, "认领成功应出现 .el-message--success 提示"
        assert item_detail_page.is_claim_dialog_closed(), "认领成功后弹窗应自动关闭"
        item_detail_page.screenshot("claim_success")
        claimed_item_cleanup.append(candidate_id)


@pytest.fixture
def claimed_item_cleanup(base_url, api_headers):
    """test_claim_success 专用清理：teardown 取消本轮认领单（API），保持认领列表整洁。"""
    claimed_ids: list[int] = []
    yield claimed_ids
    for item_id in claimed_ids:
        _cancel_claims_on(base_url, api_headers, item_id)
