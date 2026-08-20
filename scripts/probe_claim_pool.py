"""枚举真实认领池（Day17，2026-08-20）：API 只读探测，不写数据。

逻辑与接口自动化项目 test_claims.py 的 _find_claimable_others_item 相同：
失物/招领列表中 status=0 且发布者不是本账号且本账号从未认领过的物品。
输出到 scripts/probe_claim_pool_out.txt（gitignore，不入库）。
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def main():
    # 登录拿 token
    resp = requests.post(f"{BASE_URL}/api/user/login",
                         json={"username": TEST_USERNAME, "password": TEST_PASSWORD}, timeout=10)
    token = resp.json()["data"]["token"]
    headers = {"token": token}
    print("登录成功, token 非空:", bool(token))

    # 本账号已认领过的物品（含已取消——系统永久拒绝再次认领）
    claimed = set()
    for page in range(1, 6):
        r = requests.get(f"{BASE_URL}/api/claim/my", params={"currentPage": page, "size": 50},
                         headers=headers, timeout=10)
        records = (r.json().get("data") or {}).get("records") or []
        for rec in records:
            claimed.add(rec.get("itemId"))
        if len(records) < 50:
            break
    print(f"本账号已认领过的物品数（含已取消）: {len(claimed)}: {sorted(claimed)[:20]}")

    # 枚举失物/招领列表，找可认领候选
    print("\n可认领候选（status=0 且发布者非本账号且从未认领）:")
    total_claimable = []
    for endpoint in ("lost-item", "found-item"):
        for page in range(1, 4):
            r = requests.get(f"{BASE_URL}/api/{endpoint}/page",
                             params={"currentPage": page, "size": 50}, headers=headers, timeout=10)
            records = (r.json().get("data") or {}).get("records") or []
            for rec in records:
                flag = ""
                if rec.get("username") != TEST_USERNAME and rec.get("status") == 0 and rec.get("id") not in claimed:
                    flag = "  <<< 可认领"
                    total_claimable.append((endpoint, rec["id"], rec.get("title", "")[:30],
                                            rec.get("username", ""), rec.get("status")))
                print(f"  {endpoint} id={rec.get('id')} status={rec.get('status')} "
                      f"user={rec.get('username')} title={rec.get('title', '')[:24]!r}{flag}")
            if len(records) < 50:
                break
    print(f"\n可认领候选总数: {len(total_claimable)}")
    for c in total_claimable[:15]:
        print("  ", c)


if __name__ == "__main__":
    main()
