# lostfound-ui-test — 失物招领系统 UI 自动化测试项目

> **技术栈**：Playwright（Python sync_api）+ pytest + allure-pytest + Page Object 模式
> **开始日期**：2026-08-18（第3周 Day15）
> **运行策略（方案C）**：UI 测试**本地运行**，Allure 报告手动合并——接口测试跑服务器
> Jenkins CI（见 `../lostfound-api-test-示例/`），UI 测试本地跑（4G 服务器 headless
> Chromium 有 OOM 风险，决策记录见 week2_day14 手册第 4 步）。
> **配套文档**：`../../示例/week3_day15_示例-UI自动化框架选型与第一个脚本开发手册.md`

## 目录结构

```
lostfound-ui-test/
├── .env                     # 环境变量（BASE_URL / 测试账号；gitignore 排除，不入库）
├── conftest.py              # 全局 fixture：browser / page / 页面类 / 失败现场信息 / api_headers
├── pytest.ini               # pytest 配置（testpaths / alluredir / rerunfailures 重试）
├── pages/                   # Page Object 页面类
│   ├── base_page.py         # 基类：navigate/click/fill/等待/截图 + 校验提示轮询读取
│   ├── login_page.py        # 登录页（Day15）
│   ├── home_page.py         # 首页（Day16）
│   ├── lost_list_page.py    # 列表页：搜索过滤/点卡片进详情（Day16~17）
│   ├── publish_page.py      # 发布页：publish_item() 组合流程（Day16）
│   ├── register_page.py     # 注册页：字段校验用例（Day16）
│   └── item_detail_page.py  # 详情页：认领流程（申请归还弹窗）（Day17）
├── testcases/               # 用例模块（21 条：登录5/发布4/搜索2/注册5/认领5）
│   ├── test_login_ui.py     # 登录流程（Day15）
│   ├── test_publish_ui.py   # 发布流程（Day16）
│   ├── test_search_ui.py    # 搜索流程（Day16）
│   ├── test_register_ui.py  # 注册流程（Day16，含 1 条缺陷阻断 skip）
│   └── test_claim_ui.py     # 认领流程（Day17，含 1 条认领池依赖 skip）
├── utils/
│   └── screenshot_utils.py  # 截图附件工具
├── scripts/                 # 页面探测/运行输出脚本（开发用；*.txt 不入库）
├── screenshots/             # 截图产物（gitignore 排除）
└── allure-results/          # Allure 原始结果（gitignore 排除）
```

## 测试覆盖（Day15~17，21 条）

| 模块 | 用例数 | 覆盖点 | 状态 |
|------|:---:|--------|:---:|
| 登录（Day15） | 5 | 成功/邮箱/错误密码/空表单/注册跳转 | ✅ |
| 发布（Day16） | 4 | 完整发布/必填校验/未登录保护/分类下拉 | ✅ |
| 搜索（Day16） | 2 | 已知关键词有结果/不存在关键词空结果 | ✅ |
| 注册（Day16） | 5 | 字段校验 4 + 成功 1（协议弹窗缺陷阻断，skip） | 4✅ 1⛔ |
| 认领（Day17） | 5 | 弹窗结构/空说明校验/重复申请拒绝/自认领拦截/成功（认领池耗尽，skip） | 4✅ 1⛔ |

**认领池说明（2026-08-20 实测）**：系统缺陷——物品一旦被认领（即使已取消）永久不可
再次认领；当前本账号历史认领单已覆盖全部他人物品，`test_claim_success` 按接口项目同款
策略 skip（后台重置种子数据后自动恢复，见 test_claim_ui.py 注释）。

## 快速开始

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv

# 2. 安装依赖（国内可用阿里云镜像加速；清华镜像 2026-08 起对本机 HTTP 403）
.venv\Scripts\pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 3. 下载 Chromium 内核（下载慢时设国内镜像源）
.venv\Scripts\playwright install chromium
#    set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/

# 4. 配置环境变量：复制 .env.example 为 .env，填写 BASE_URL / 测试账号
#    （与接口自动化项目同一测试账号，接口层与 UI 层双重验证）

# 5. 运行测试并生成 Allure 报告
.venv\Scripts\python.exe -m pytest -v                 # headless 全量
.venv\Scripts\python.exe -m pytest --alluredir=./allure-results --clean-alluredir
.venv\Scripts\allure.exe serve ./allure-results       # 查看报告

# 有头模式调试（本地观察页面操作）
$env:HEADLESS="false"; .venv\Scripts\python.exe -m pytest testcases/test_login_ui.py -v
```

## 与接口自动化项目的关系（面试可讲）

- **双项目同一测试账号**：UI 层与接口层共用 .env 的 TEST_USERNAME/PASSWORD，
  实现对同一功能的"协议层 + 表现层"双重验证；
- **方案C 分工**：接口测试（轻量、快）跑服务器 Jenkins CI 全自动；UI 测试（依赖
  Chromium 150MB + 内存需求）本地运行，Allure 报告手动合并——面试讲"资源约束下的
  架构取舍"，决策记录见 week2_day14 手册；
- **错误密码用例的设计默契**：接口层实测"连续 5 次失败锁定 15 分钟、成功登录重置"，
  UI 层沿用同一契约（错误密码用例放最后 + 宽断言），两层行为一致。

## 敏感信息说明

- `.env` 含真实 `BASE_URL` 与测试账号密码，**已 gitignore，绝不入库**；
- 代码注释/docstring 中一律用占位符（`<服务器IP>` / `<目标站点>`），示例 URL 不写真实域名；
- 错误密码、账号锁定机制等契约信息来自真实系统实测，属于测试知识，不涉及凭据。
