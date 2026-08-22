# lostfound-ui-test — 失物招领系统 UI 自动化测试项目

> **技术栈**：Playwright（Python sync_api）+ pytest + allure-pytest + Page Object 模式
> **开始日期**：2026-08-18（第3周 Day15）
> **运行策略（方案C，Day18 决策落地）**：UI 测试**本地一键运行**，Allure 报告手动合并——
> 接口测试跑服务器 Jenkins CI（见 `../lostfound-api-test-示例/`），UI 测试本地跑。
> 决策依据（2026-08-21 服务器内存实测：空闲可用仅 ~758MiB，低于 headless Chromium
> 单实例需求）：`docs/UI自动化CI集成方案决策文档.md`；决策历程见 week2_day14 手册第 4 步。
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
├── run_ui_tests.bat         # 方案C 本地一键运行（Windows；Day18）
├── run_ui_tests.sh          # 方案C 本地一键运行（Linux/macOS/Git-Bash；Day18）
├── docs/
│   ├── UI自动化CI集成方案决策文档.md  # CI 集成方案决策与面试话术（Day18）
│   └── report_index.html     # COS 报告索引页模板（域名占位符，替换后传桶根；Day19）
├── scripts/
│   ├── upload_to_cos.py      # Allure 报告上传腾讯云 COS（Day19）
│   ├── cleanup_cos_reports.py# 清理 COS 历史报告 build-*（保留最近 N 个；Day19）
│   └── ...                   # 页面探测/运行输出脚本（开发用；*.txt 不入库）
├── screenshots/             # 截图产物（gitignore 排除）
└── allure-results/          # Allure 原始结果（gitignore 排除）
```

## 测试覆盖（Day15~17，21 条）

| 模块 | 用例数 | 覆盖点 | 状态 |
|------|:---:|--------|:---:|
| 登录（Day15） | 5 | 成功/邮箱/错误密码/空表单/注册跳转 | ✅ |
| 发布（Day16） | 4 | 完整发布/必填校验/未登录保护/分类下拉 | ✅ |
| 搜索（Day16） | 2 | 已知关键词有结果/不存在关键词空结果 | ✅ |
| 注册（Day16） | 5 | 字段校验 4 + 成功 1（注册前端缺陷阻断，skip） | 4✅ 1⛔ |
| 认领（Day17） | 5 | 弹窗结构/空说明校验/重复申请拒绝/自认领拦截/成功（认领池耗尽，skip） | 4✅ 1⛔ |

**认领池说明（2026-08-20 实测）**：系统缺陷——物品一旦被认领（即使已取消）永久不可
再次认领；当前本账号历史认领单已覆盖全部他人物品，`test_claim_success` 按接口项目同款
策略 skip（后台重置种子数据后自动恢复，见 test_claim_ui.py 注释）。

**注册缺陷说明（2026-08-20 复测定论）**：注册提交 payload 不含后端必填的
`agreementAccepted` 字段（前端剥离 agreement 且字段名与后端契约不一致）→ 后端始终
返回「请阅读并同意用户协议」，UI 注册对任何用户都无法走通（协议层带
`agreementAccepted=true` 可注册成功）；`test_register_success` 显式 skip 注明，
前端修复 payload 后取消 skip 即可启用。Day16 曾误报"协议弹窗无法关闭"，已勘误（见
Day17 测试运行报告 8.2 节）。

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

# 6. （Day18 方案C）一键运行：测试 -> Allure 报告 -> 保留趋势 -> 打开报告
.\run_ui_tests.bat          # Windows
./run_ui_tests.sh           # Linux / macOS / Git-Bash
```

## 与接口自动化项目的关系（面试可讲）

- **双项目同一测试账号**：UI 层与接口层共用 .env 的 TEST_USERNAME/PASSWORD，
  实现对同一功能的"协议层 + 表现层"双重验证；
- **方案C 分工（Day18 实测落地）**：接口测试（轻量、快）跑服务器 Jenkins CI 全自动；
  UI 测试（依赖 Chromium 150MB + 内存需求）本地一键运行，Allure 报告手动合并——
  面试讲"资源约束下的架构取舍"，决策数据与话术见 `docs/UI自动化CI集成方案决策文档.md`；
- **错误密码用例的设计默契**：接口层实测"连续 5 次失败锁定 15 分钟、成功登录重置"，
  UI 层沿用同一契约（错误密码用例放最后 + 宽断言），两层行为一致。

## CI 集成（Day18）

| 项 | 内容 |
|----|------|
| 接口测试 | 服务器 Jenkins `lostfound-api-test` 全自动（Poll SCM 30 分钟；CI 模式守卫见接口项目 README） |
| UI 测试 | **本地一键脚本** `run_ui_tests.bat` / `run_ui_tests.sh`（测试 → Allure 报告 → history 趋势保留 → 本地 HTTP 打开） |
| 决策文档 | `docs/UI自动化CI集成方案决策文档.md`（2026-08-21 服务器内存实测数据 + 三方案对比 + 面试话术） |
| 演进路径 | UI 仓库建远程后可选 Jenkins 手动触发参数（`UI_TESTS=true/false`）；服务器扩容 ≥8G 后升级方案A 全自动 |

## Allure 报告发布到 COS（Day19）

**思路（方案C 延续）**：UI 测试本地跑，报告上传腾讯云 COS 提供外网链接——
"本地跑 + 线上看报告"闭环；Jenkins 构建后上传步骤已在手册存档（UI 仓库建远程、
接口项目 Jenkins 落地时按 `示例/week3_day19_示例-*` 两篇文档执行）。

**配置**：复制 `.env.example` 的 `COS_*` 段到 `.env`（与接口项目 Day14 配置同款，可复用），
桶名含账号 APPID 后缀，**公网仓库一律 `<COS桶名>` 占位符**。

```bash
# 1. 上传最新报告（默认传 reports/latest，覆盖式更新）
.venv\Scripts\python.exe scripts\upload_to_cos.py allure-report reports/latest --verify

# 2. 上传历史构建报告（按构建号归档，供清理脚本管理）
.venv\Scripts\python.exe scripts\upload_to_cos.py allure-report reports/build-123 --no-version

# 3. 索引页（docs/report_index.html 替换占位符为真实域名后传桶根）
.venv\Scripts\python.exe scripts\upload_to_cos.py --index docs/report_index.html

# 4. 清理历史（只删 reports/build-*，保留最近 10 个；先 --dry-run 演练）
.venv\Scripts\python.exe scripts\cleanup_cos_reports.py --dry-run --keep 10
```

**存储策略**：`reports/latest/` 最新报告（每次覆盖）+ `reports/build-{N}/` 历史
（保留最近 10 次）+ `reports/archive/` 按月归档（可选）；COS 控制台可加生命周期
规则自动删除 30 天前历史。

**安全约定**：凭据只走 `.env` 环境变量；两个脚本日志对桶名脱敏（只留前缀 3 字符）；
`version.json` 仅在配置 `COS_CDN_DOMAIN` 时写 `report_url`，避免真实域名落桶。

**Day19 实测结论**（2026-08-22）：上传 73 个文件到 `reports/latest/` 全程 18.7s，
SDK 复核桶内 74 个对象（73 + version.json）数量一致；清理脚本实测保留/删除逻辑正确；
清华源缺 `cos-python-sdk-v5`（走官方 PyPI 安装，需 `NO_PROXY=*`）；
COS SDK 分页坑已修（`IsTruncated` 是字符串，翻页 marker 为 None 会导致
`SignatureDoesNotMatch`，见 upload_to_cos.py 注释）；外链浏览器访问待用户截图确认
（本次未配置 CDN 域名）。

## 敏感信息说明

- `.env` 含真实 `BASE_URL` 与测试账号密码，**已 gitignore，绝不入库**；
- 代码注释/docstring 中一律用占位符（`<服务器IP>` / `<目标站点>`），示例 URL 不写真实域名；
- 错误密码、账号锁定机制等契约信息来自真实系统实测，属于测试知识，不涉及凭据。
