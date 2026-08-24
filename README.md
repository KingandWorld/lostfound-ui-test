# 失物招领系统 — 全栈自动化测试项目

> 一个面向**真实 Web 应用**的完整测试实践项目：功能测试（禅道）+ 接口自动化（pytest+requests）+ UI 自动化（Playwright）+ CI/CD（Jenkins Pipeline → Allure 报告 → 腾讯云 COS）。
> 本仓库为 **UI 自动化测试**仓库（`lostfound-ui-test-示例`），同时作为项目的 **CI/CD 中枢**（Jenkinsfile / COS 脚本 / 配置文档）与**项目门面 README**（Day21 升级）。

## 📋 项目概述

- **功能测试**：60+ 条用例，覆盖核心业务流程，禅道全生命周期管理（第1周）
- **接口自动化**：55 条 pytest 用例，Jenkins CI 集成（第2周；仓库见「相关文档」）
- **UI 自动化**：21 条 Playwright 用例，Page Object 模式（第3周；本仓库）
- **CI/CD**：Jenkins Pipeline → Allure 报告 → 腾讯云 COS 自动部署（夜间定时）

## 🌐 在线访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 被测系统 | `http://<服务器IP>:<端口>` | 失物招领 Web 应用 |
| 禅道 | `http://<服务器IP>:8081` | 测试管理平台（用例 + Bug） |
| Allure 报告 | `https://<报告访问域名>/reports/latest/` | 自动化测试报告（Jenkins 定时发布） |

> ⚠️ **公网仓库安全红线**：真实域名 / 服务器 IP / COS 桶名一律使用占位符（规则见文末「敏感信息说明」）；真实值仅存在于个人笔记与 `.env`。

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| 接口自动化 | pytest + requests + allure-pytest + pymysql（数据库校验，SSH 隧道连真实库） |
| UI 自动化 | Playwright（Python sync API）+ pytest + allure-pytest + Page Object 模式 |
| CI/CD | Jenkins Declarative Pipeline（Jenkinsfile 版本化）+ 腾讯云 COS + CDN + Docker |
| 测试管理 | 禅道（用例管理 + 缺陷跟踪） |

## 📊 测试成果（数字可溯源，来源见 `docs/第四周素材清单.md`）

| 指标 | 数据 | 来源 |
|------|------|------|
| 功能测试用例 | 60+ 条（禅道管理） | 第1周功能测试 |
| 接口自动化用例 | 55 条（认证12/物品20/搜索10/认领5/数据库4/端到端4） | API 仓库 README（Day12 验收版） |
| UI 自动化用例 | 21 条（登录5/发布4/搜索2/注册5/认领5），基线 19 passed + 2 skipped | 本仓库「测试覆盖」+ Day20 测试运行报告 |
| 发现缺陷 | 15+ 个（含 1 个 XSS 安全漏洞 + 2 个业务逻辑缺陷：注册 payload 缺 `agreementAccepted` / 认领池永久不可再认领） | 功能测试报告 + Day6/17 实测记录 |
| 代码规模 | ~5,400 行（API 2,136 + UI 3,235） | 2026-08-24 `wc` 实测 |
| CI 端到端 | 服务器全链路 ≈ 30s（冒烟 18.64s + 报告 2s + 上传 4.1s，build #4） | Day20 测试运行报告 |

## 📁 项目结构（双仓库，方案C）

```
lostfound-testing/                    # 概念总目录：实际为两个独立 git 仓库
├── lostfound-api-test-示例/          # 接口自动化仓库（第2周；标签 v1.0~v1.2）
│   ├── testcases/                    # 55 条用例（认证/物品/搜索/认领/数据库/端到端）
│   ├── config/  utils/  scripts/     # 数据驱动 / 数据库校验工具 / Jenkins 构建脚本
│   └── Jenkins 任务：lostfound-api-test（Poll SCM 30 分钟，CI 模式守卫）
└── lostfound-ui-test-示例/           # UI 自动化仓库（第3周；本仓库；CI/CD 中枢）
    ├── Jenkinsfile                   # 声明式 Pipeline（Day20；参数/触发器/通知版本化）
    ├── pages/  testcases/            # Page Object 页面类（7 个）+ 21 条用例
    ├── conftest.py                   # browser/page fixture + 失败现场信息 hook
    ├── run_ui_tests.bat/.sh          # 方案C 本地一键运行（Day18）
    ├── scripts/                      # COS 上传/清理脚本（Day19~20，--prune 加固）
    ├── docs/                         # 决策文档 / Jenkins 配置 / 第四周素材清单
    └── 远程：gitee + github 双远程（Day19 建）
```

> 分工（方案C，Day18 实测决策）：接口测试（轻量）跑服务器 Jenkins CI 全自动；UI 测试（依赖 Chromium + 内存）本地一键运行；Jenkins Pipeline 提供服务器手动触发与夜间报告发布入口。

## 🚀 快速开始（项目级）

```bash
# 1. 克隆两个仓库
git clone https://gitee.com/<用户名>/lostfound-api-test-示例.git
git clone https://gitee.com/<用户名>/lostfound-ui-test-示例.git

# 2. 各自创建虚拟环境并安装依赖（UI 仓库）
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
.venv\Scripts\playwright install chromium

# 3. 配置环境变量：复制 .env.example 为 .env，填写 BASE_URL / 测试账号（两仓库同一测试账号）

# 4. 运行测试并查看报告
.venv\Scripts\python.exe -m pytest -v                          # UI 全量（21 条）
.\run_ui_tests.bat                                             # 一键：测试→报告→打开
# 接口测试：cd ../lostfound-api-test-示例 && pytest -v --alluredir=./allure-results
```

详细命令（含 headless 调试、COS 上传、Jenkins 触发）见下文「本仓库详解」。

## 🔗 相关文档

- 测试计划 / 功能测试报告 / API 文档：见 `docs/` 与 `示例/`（Day1~14 各日手册）
- 接口自动化项目：`../lostfound-api-test-示例/README.md`（55 条用例 + 接口契约实测）
- CI/CD 决策文档：`docs/UI自动化CI集成方案决策文档.md`（Day18，三方案对比 + 面试话术）
- Jenkins 流水线配置：`docs/Jenkins流水线定时构建与通知配置文档.md`（Day20）
- **简历素材一页速查：`docs/第四周素材清单.md`（Day21 新增：关键数字/截图清单/简历 bullet 初稿/三链接）**

---

# 本仓库详解：UI 自动化测试（lostfound-ui-test）

> **技术栈**：Playwright（Python sync_api）+ pytest + allure-pytest + Page Object 模式
> **开始日期**：2026-08-18（第3周 Day15）
> **运行策略（方案C，Day18 决策落地）**：UI 测试**本地一键运行**，Allure 报告手动合并——
> 接口测试跑服务器 Jenkins CI（见 `../lostfound-api-test-示例/`），UI 测试本地跑；
> Jenkins Pipeline 提供服务器手动触发与夜间报告发布入口（Day20，见下）。
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
├── Jenkinsfile              # Jenkins 声明式流水线（拉取→依赖→测试→报告→上传；Day20）
├── docs/
│   ├── UI自动化CI集成方案决策文档.md  # CI 集成方案决策与面试话术（Day18）
│   ├── Jenkins建项执行清单.md        # Jenkins 手动触发建项步骤（自由风格版；Day19）
│   ├── Jenkins流水线定时构建与通知配置文档.md  # Pipeline 建项/定时/邮件通知（Day20）
│   ├── 第四周素材清单.md             # 简历/面试素材一页速查（Day21）
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

## 快速开始（本仓库，详细版）

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
| 演进路径 | UI 仓库已建远程（2026-08-22，gitee/github 双远程）；Jenkins 声明式流水线（Day20）见下节，完整建项/卡点见 `docs/Jenkins流水线定时构建与通知配置文档.md`；Day19 自由风格手动版清单见 `docs/Jenkins建项执行清单.md`；服务器扩容 ≥8G 后升级方案A 全自动 |

## Jenkins 流水线与定时构建（Day20）

**升级路径**：Day19 的「自由风格手动任务（存档）」升级为**声明式 Pipeline**——
`Jenkinsfile` 随仓库版本化（参数/触发器/通知全在代码里），方案C 边界不变
（UI 全量仍本地跑；实测背书：768MiB 容器内跑浏览器必 OOM，见下方卡点 #11）。

- **Jenkinsfile**：Checkout → Env Guard（fail-fast 校验必填变量）→ Setup（venv 缓存 +
  依赖 + chromium）→ UI Tests（参数化可选）→ Generate Report（容器内 Allure CLI）→
  Upload to COS（`--prune --verify` 复核）；post：失败自动邮件（email-ext）；
- **参数**：`UI_TESTS`（默认 false = report-only，方案C 弹性入口）、`TEST_PATH`
  （冒烟可限定 `testcases/test_login_ui.py`）、`REPORT_PREFIX`（latest / build-N）；
- **定时构建**：`cron('H 18 * * *')` = UTC 18:00 = **北京时间 02:00**（容器时区是
  UTC，见卡点 #12），夜间默认 report-only，冒烟/全量两档升级路径见配置文档；
- **凭据**：COS 密钥走 Jenkins Credentials（Secret text，日志自动掩码）；桶名/域名/账号
  走全局环境变量；Jenkinsfile 零硬编码、纯 ASCII 注释、零真实值；
- 完整建项步骤 / SMTP 邮件配置 / 验证清单 / 卡点预案：`docs/Jenkins流水线定时构建与通知配置文档.md`。

**服务器端到端实测（2026-08-24）**：build #1 骨架全绿（report-only 按条件跳过）→
build #3 冒烟 **5 passed in 18.64s**（容器内存放大至 1024MiB 后 OOM 解除）→
build #4 报告生成 + 上传复核 **44 = 44 -> OK**（43 文件 / 4.1s，`--prune` 清理 160 个
历史孤儿）——"拉码 → 依赖 → 测试 → 报告 → 上传 COS"全链路 ≈ **30s** 闭环。

**服务器实测卡点（2026-08-24，详见配置文档卡点表 #0 / #10~#14）**：

| # | 坑 | 一句话解决 |
|:-:|----|-----------|
| 0 | 声明式参数类型 | 字符串参数用 `string`，`stringParam` 是脚本式写法（编译直接报错） |
| 10 | post 块环境变量裸引用 | 报 `MissingPropertyException: No such property: ...`；必须 `env.` 前缀（`params.X` 裸引用正常） |
| 11 | 容器 OOM | 768MiB 内跑浏览器（哪怕单用例冒烟）会 cgroup 杀 java、容器重启；`docker update --memory 1024m` 放大后可跑冒烟 |
| 12 | 容器时区 UTC | `docker exec jenkins date` 是 UTC，cron 按容器时区跑；`H 18 * * *` = 北京 02:00 |
| 13 | 邮件 Not sent | SMTP 未配置（默认 localhost:25 连不上）；按文档第六节配 QQ 465/SSL/授权码 |
| 14 | 上传复核 MISMATCH | Allure 附件随机 UUID 文件名 + `put_object` 只增不删 → 孤儿堆积；Upload 带 `--prune` 一次清零 |

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

# 5. （Day20）--prune：删除目标前缀下孤儿对象（Allure 附件随机名残留，
#    长期会撑大复核计数；先 --dry-run 演练）。CI 中建议 latest 上传带 --prune
.venv\Scripts\python.exe scripts\upload_to_cos.py allure-report reports/latest --prune --verify
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

**Day20 实测结论**（2026-08-23）：复核首次发现 **MISMATCH（桶内 114 vs 预期 74）**——
`put_object` 只覆盖同名对象从不删除，而 Allure 附件是**随机 UUID 文件名**
（`data/attachments/<uuid>.png`），每次测试运行的附件集合都不同 → 旧版本报告
残留 40 个孤儿附件对象。修复：`upload_to_cos.py` 新增 `--prune`（删除目标前缀下
不在本地文件集中的对象，只操作传入前缀、空前缀拒绝执行、`--dry-run` 可演练），
实测真删 40 对象后复核 74=74 OK，幂等重跑 0 孤儿；期间另踩 **SDK 批量删除坑**：
`delete_objects` 参数键是 `Object`（单数），不是 AWS 风格的 `Objects`——写错报
`InvalidArgument`（400），注释已留档。

## 敏感信息说明

- `.env` 含真实 `BASE_URL` 与测试账号密码，**已 gitignore，绝不入库**；
- 代码注释/docstring 中一律用占位符（`<服务器IP>` / `<目标站点>` / `<报告访问域名>` / `<COS桶名>`），示例 URL 不写真实域名；
- 错误密码、账号锁定机制等契约信息来自真实系统实测，属于测试知识，不涉及凭据。
