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
├── conftest.py              # 全局 fixture：browser / page / login_page / 失败自动截图
├── pytest.ini               # pytest 配置（testpaths / alluredir）
├── pages/                   # Page Object 页面类
│   ├── base_page.py         # 基类：navigate/click/fill/等待/截图（通用操作封装）
│   └── login_page.py        # 登录页：定位器集中管理 + login() 组合操作
├── testcases/
│   └── test_login_ui.py     # 登录流程 5 条用例（成功/邮箱/错误密码/空表单/注册跳转）
├── utils/
│   └── screenshot_utils.py  # 截图附件工具（失败自动截图复用）
├── scripts/
│   └── probe_login_page.py  # 登录页行为探测脚本（开发用，实测结果已回填用例）
├── screenshots/             # 截图产物（gitignore 排除）
└── allure-results/          # Allure 原始结果（gitignore 排除）
```

## 测试覆盖（Day15，5 条用例）

| 用例 | 场景 | 断言 |
|------|------|------|
| test_login_success | 正确用户名密码登录 | URL 离开 /login 跳转首页 + localStorage token 非空 |
| test_login_with_email | 邮箱登录 | 同上（真实账号邮箱实测确认；账号未配邮箱时跳过） |
| test_login_wrong_password | 错误密码 | 错误提示含"用户名或密码错误" + 不跳转 + 无 token |
| test_login_empty_form | 空表单提交 | 前端必填校验提示（.el-form-item__error） |
| test_login_redirect_to_register | 点击注册链接 | URL 跳转 */register |

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
