"""探测认领提交全流程（Day17 第 3 轮，2026-08-20）。

本轮会真实提交 1 次认领（验证成功提示/状态变化/重复认领提示），
结束后用 API（自定义 Header token）取消该认领单清理数据。
输出到 scripts/probe_claim_submit_out.txt（gitignore，不入库）。
"""

import os
import time

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

CLAIM_DESCRIPTION = "这是我的证件，姓名与照片完全吻合，请求归还（UI 自动化探测数据）。"


def api_cleanup(token: str):
    """查询 claim/my 并取消本账号全部认领单（清理本轮探测数据）。"""
    headers = {"token": token}
    resp = requests.get(f"{BASE_URL}/api/claim/my",
                        params={"currentPage": 1, "size": 50}, headers=headers, timeout=10)
    records = (resp.json().get("data") or {}).get("records") or []
    canceled = 0
    for rec in records:
        r = requests.put(f"{BASE_URL}/api/claim/cancel/{rec['id']}", headers=headers, timeout=10)
        canceled += 1
        print(f"  [清理] 取消认领单 id={rec['id']} itemId={rec.get('itemId')} "
              f"status={rec.get('status')} -> {r.status_code}")
    if not canceled:
        print("  [清理] 无可取消的认领单")
    return canceled


def probe():
    print(f"== 认领提交全流程探测 == 时间戳: {int(time.time() * 1000)}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()

        print("\n[1] 登录")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", TEST_USERNAME)
        page.fill("input[placeholder='请输入密码']", TEST_PASSWORD)
        page.locator("button:has-text('登录')").click()
        page.wait_for_url("**/", timeout=15_000)
        token = page.evaluate("localStorage.getItem('token')")
        print("token 非空:", bool(token))

        print("\n[2] 选一张「待认领」且非固件/非本账号发布物的卡片")
        # 排除规则（实测）：卡片文本不含发布者；
        # 本账号发布物标题带测试前缀（UI自动化发布物品_ / 端到端发布物品_），
        # 自己的物品详情页无「申请归还」按钮（实测：不能认领自己发布的物品）
        OWN_PATTERNS = ("UI自动化发布物品_", "端到端发布物品_")
        page.goto(f"{BASE_URL}/lost", wait_until="networkidle")
        cards = page.locator(".el-card")
        target = None
        for i in range(cards.count()):
            t = cards.nth(i).inner_text()
            if "待认领" in t and "学生证" not in t and not any(p in t for p in OWN_PATTERNS):
                target = t
                target_index = i
                break
        print("目标卡片:", target[:80].replace("\n", "|") if target else "未找到")
        assert target, "探测失败：找不到可认领的目标卡片"
        # 点卡片进详情
        cards.nth(target_index).click()
        page.wait_for_url("**/lost/detail/**", timeout=10_000)
        detail_url = page.url
        print("详情 URL:", detail_url)

        print("\n[3] 空申请说明提交 → 观察校验提示")
        page.locator("text=申请归还").first.click()
        page.wait_for_timeout(1000)
        dlg = page.locator(".el-dialog:visible")
        print("弹窗可见:", dlg.count() > 0)
        dlg.locator("button:has-text('提交申请')").click()
        page.wait_for_timeout(1200)
        errors = [e.inner_text() for e in page.locator(".el-form-item__error, .el-message").all()]
        print("空提交提示:", errors)

        print("\n[4] 填写说明并提交 → 观察成功提示/弹窗/状态")
        dlg.locator("textarea").fill(CLAIM_DESCRIPTION)
        dlg.locator("button:has-text('提交申请')").click()
        page.wait_for_timeout(2000)
        msgs = [m.inner_text() for m in page.locator(".el-message").all()]
        print("提交后 .el-message:", msgs)
        print("弹窗是否已关闭:", page.locator(".el-dialog:visible").count() == 0)
        # 详情页状态标签
        status_el = page.locator(".el-tag, .status, [class*='status']")
        texts = [t.inner_text() for t in status_el.all()][:5]
        print("详情页状态类元素文本:", texts)

        print("\n[5] 同一物品再次申请归还 → 观察重复提示")
        page.locator("text=申请归还").first.click()
        page.wait_for_timeout(1000)
        dlg2 = page.locator(".el-dialog:visible")
        dlg2.locator("textarea").fill(CLAIM_DESCRIPTION)
        dlg2.locator("button:has-text('提交申请')").click()
        page.wait_for_timeout(2000)
        msgs2 = [m.inner_text() for m in page.locator(".el-message").all()]
        print("重复提交 .el-message:", msgs2)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        print("\n[6] API 清理：取消本轮认领单")
        api_cleanup(token)

        browser.close()
    print("\n== 探测完成 ==")


if __name__ == "__main__":
    probe()
