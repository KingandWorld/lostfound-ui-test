"""探测认领拒绝路径（Day17 第 4 轮，2026-08-20）。

目标物品：id=3「学生证丢了」（其他用户发布，本账号已认领过 → 系统拒绝再次认领，
实测为"重复认领"路径）。只提交不成功 → 不产生新认领单，无数据污染。
输出到 scripts/probe_claim_reject_out.txt（gitignore，不入库）。
"""

import os

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

DESCRIPTION = "这是我的证件，姓名与照片完全吻合，请求归还（拒绝路径探测）。"


def main():
    print("== 认领拒绝路径探测 == id=3 学生证丢了")
    # API 登录（用于核对认领单数量前后变化）
    resp = requests.post(f"{BASE_URL}/api/user/login",
                         json={"username": TEST_USERNAME, "password": TEST_PASSWORD}, timeout=10)
    token = resp.json()["data"]["token"]
    headers = {"token": token}
    r = requests.get(f"{BASE_URL}/api/claim/my", params={"currentPage": 1, "size": 50},
                     headers=headers, timeout=10)
    before = len((r.json().get("data") or {}).get("records") or [])
    print(f"提交前 claim/my 记录数: {before}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--proxy-server=direct://"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = context.new_page()

        print("\n[1] 登录并打开详情页 id=3")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.fill("input[placeholder='请输入用户名或邮箱']", TEST_USERNAME)
        page.fill("input[placeholder='请输入密码']", TEST_PASSWORD)
        page.locator("button:has-text('登录')").click()
        page.wait_for_url("**/", timeout=15_000)
        page.goto(f"{BASE_URL}/lost/detail/3", wait_until="networkidle")

        print("\n[2] 点申请归还 → 空说明提交")
        page.locator("text=申请归还").first.click()
        page.wait_for_timeout(1000)
        dlg = page.locator(".el-dialog:visible")
        print("弹窗可见:", dlg.count() > 0)
        dlg.locator("button:has-text('提交申请')").click()
        page.wait_for_timeout(1500)
        errs = [e.inner_text() for e in page.locator(".el-form-item__error, .el-message").all()]
        print("空提交提示:", errs)
        # 弹窗是否还开着
        print("弹窗仍可见:", page.locator(".el-dialog:visible").count() > 0)

        print("\n[3] 填写说明提交 → 观察拒绝提示")
        dlg = page.locator(".el-dialog:visible")
        dlg.locator("textarea").fill(DESCRIPTION)
        dlg.locator("button:has-text('提交申请')").click()
        page.wait_for_timeout(2000)
        msgs = [m.inner_text() for m in page.locator(".el-message").all()]
        print("提交后 .el-message:", msgs)
        print("弹窗是否关闭:", page.locator(".el-dialog:visible").count() == 0)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        print("\n[4] 自己发布的物品详情（id=490）→ 申请归还按钮是否存在")
        page.goto(f"{BASE_URL}/lost/detail/490", wait_until="networkidle")
        n = page.locator("text=申请归还").count()
        print("申请归还 数量:", n)
        detail_btns = [b.inner_text() for b in page.locator("button, .el-button, span").all()
                       if b.inner_text().strip()][:15]
        print("详情页按钮/文本:", detail_btns)

        browser.close()

    r = requests.get(f"{BASE_URL}/api/claim/my", params={"currentPage": 1, "size": 50},
                     headers=headers, timeout=10)
    after = len((r.json().get("data") or {}).get("records") or [])
    print(f"\n提交后 claim/my 记录数: {after}（应等于 {before}，未产生新认领单）")
    print("== 完成 ==")


if __name__ == "__main__":
    main()
