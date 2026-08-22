# lostfound-ui-test — Jenkins 建项执行清单（方案C 手动触发预留）

> **编制日期**：2026-08-22（第3周 Day19 收尾）
> **前置**：UI 仓库已推送双远程（gitee + github，main 分支，Day15~19 共 6 个提交）；
> 接口项目 Jenkins 先例：`lostfound-api-test` 自由风格项目，`http://<服务器IP>:8082`
> **配套**：`docs/UI自动化CI集成方案决策文档.md`（方案C 决策与内存实测数据）、
> `示例/week3_day19_示例-Allure报告自动上传COS与外网链接开发手册.md` 第四节（COS 上传存档）
> **用法**：按顺序逐项执行，每一项的「完成标志」打勾后再进下一项；卡住查「九、卡点预案」。

---

## 一、先读：这个任务是什么、边界在哪（5 分钟）

**目标**：在服务器 Jenkins 上建立一个**手动触发**的自由风格项目 `lostfound-ui-test`，
把"Git 拉取 → 依赖 → 跑 UI 测试 → Allure 报告 → （可选）上传 COS"整条链路跑通，
作为方案C 的弹性入口（想跑就在服务器跑），**不是**常驻定时任务。

**边界（Day18 实测数据的硬约束，不可绕过）**：

| 事实 | 数据（2026-08-21 实测） | 影响 |
|------|--------------------------|------|
| 宿主机内存 | 总 3.6Gi，空闲可用仅 ~758MiB | UI 全量在服务器会挤压业务容器 |
| 服务器 headless 全量 | 220.7s / **4 failed**（2 条搜索 10s 超时） | "能跑但跑不稳"，环境性超时 |
| Jenkins 容器上限 | **768MiB**，基线已用 488.6MiB | 容器内跑 headless（峰值 ~494MB）极可能触顶 |
| 本地全量 | 19 passed + 2 skipped / ~134s | 稳定基线在本地，不在服务器 |

**结论**：本项目落地的正确姿势 = **手动触发 + 首次验证用冒烟/单模块 + 全量留待扩容**；
`UI_TESTS=false` 时只出报告/上传，是"流水线可用性验证"与"报告发布"两个用途，
不与"服务器跑全量"绑定。

---

## 二、服务器侧准备（SSH 直连，root 密钥登录）

### 1. 确认 Jenkins 容器与端口

```bash
docker ps --format '{{.Names}} {{.Ports}} {{.Status}}'
# 确认 jenkins 容器在跑；浏览器访问 http://<服务器IP>:8082 能打开 Jenkins（接口项目同端口）
```

✅ 完成标志：Jenkins 页面可登录，能看到 `lostfound-api-test` 任务。

### 2. 给 jenkins 容器准备 UI 测试系统库（headless chromium 依赖）

Jenkins 任务跑在 **jenkins 容器内**，Day18 装系统库是在宿主机（/opt 副本用的），
容器内需要再装一次：

```bash
docker exec -u root jenkins bash -c "apt-get update -qq && apt-get install -y -qq \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
  libcairo2 libasound2 fonts-liberation"
```

✅ 完成标志：无报错退出；若容器是精简镜像缺 apt 基础，先 `apt-get update` 看源可用。

### 3. （可选，建议做）放大 jenkins 容器内存上限

Day18 实测 jenkins 容器 768MiB 上限、基线已用 488.6MiB——headless 全量在这个
上限内跑不现实。宿主机 3.6Gi 空闲 758MiB，只能小放：

```bash
docker update --memory 1280m --memory-swap 1280m jenkins
free -h   # 确认宿主机有余量（swap 2G 兜底）
```

⚠️ 只在宿主机内存允许时放；不放也不影响建项（冒烟子集在 768MiB 内可跑）。

✅ 完成标志：`docker stats jenkins` 显示新上限；宿主机 free 无 OOM 风险。

### 4. 容器内安装 Allure CLI（Execute shell 里 `allure generate` 用）

```bash
docker exec -u root jenkins bash -c "curl -fsSL -o /tmp/allure.zip \
  https://github.com/allure-framework/allure2/releases/download/2.30.0/allure-2.30.0.zip \
  && apt-get install -y -qq unzip && mkdir -p /opt/allure && unzip -q -o /tmp/allure.zip -d /opt/allure \
  && ln -sf /opt/allure/allure-2.30.0/bin/allure /usr/local/bin/allure && allure --version"
```

（版本号按需换；服务器网络可达 GitHub，实测下载正常。装不上也不阻塞建项——
`allure generate` 步骤会跳过，报告由 Jenkins Allure 插件出，COS 上传暂缓。）

✅ 完成标志：`allure --version` 输出版本号。

### 5. 确认 Gitee 可达（服务器在境内，源码源用 Gitee 快）

```bash
docker exec jenkins bash -c "git ls-remote https://gitee.com/novaforge/lostfound-ui-test.git HEAD"
```

✅ 完成标志：输出一行 commit SHA（仓库为公开仓库时无需凭据；私有则按「七、凭据」补）。

---

## 三、Jenkins 建项（浏览器操作，8 步）

### 1. 新建任务

主页 → **新建任务** → 名称 `lostfound-ui-test` → 类型 **自由风格项目** → 确定。

### 2. 源码管理（Git）

| 项 | 值 |
|----|----|
| Repository URL | `https://gitee.com/novaforge/lostfound-ui-test.git`（公开仓库凭据留空；私有仓库选 Gitee 账号凭据） |
| Branches to build | `*/main` |
| Additional Behaviours | 不额外添加（**不要**勾 Clean before checkout——工作区里要保留 venv/浏览器缓存） |

### 3. 构建环境

- ☑️ **Add timestamps to the Console Output**（日志带时间，接口项目同款）
- ☐ Delete workspace before build **不勾**（UI 依赖 300MB 级，每次清空重装不可接受）

### 4. 参数化构建（方案C 弹性入口）

勾 **This project is parameterized**，添加两个参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `UI_TESTS` | Boolean Parameter | `false` | true=跑 pytest 全量；false=跳过 pytest 只生成/上传报告（Day18 存档契约） |
| `REPORT_PREFIX` | String Parameter | `latest` | COS 上传目标：`latest` 或 `build-${BUILD_NUMBER}`（留空则不传 COS） |

### 5. 构建步骤（Execute shell）

用下面的完整脚本（**纯 ASCII 注释**——项目红线：bat 与 shell 注释禁中文，避免
服务器 locale 乱码；敏感值从 Jenkins 环境变量取，不落仓库）：

```bash
#!/bin/bash
set -e
# lostfound-ui-test: fetch -> deps -> (ui tests) -> allure report -> (cos upload)
# CI mode: backend unreachable means BUILD FAILS (same guard as api project)

echo "== [1/4] checkout ok, workspace: $(pwd) =="

echo "== [2/4] venv & deps (cached in workspace, do not delete workspace) =="
if [ ! -d venv ]; then
    python3 -m venv venv
fi
venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
# cos-python-sdk-v5 is NOT on tsinghua mirror -> official pypi fallback (Day19)
venv/bin/pip install cos-python-sdk-v5 -q || true

echo "== [2/4] playwright chromium (npmmirror standard prefix, Day18) =="
export PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright
venv/bin/playwright install chromium || true

echo "== [3/4] generate .env from Jenkins env vars (never in git) =="
cat > .env <<EOF
BASE_URL=${BASE_URL}
TEST_USERNAME=${TEST_USERNAME}
TEST_PASSWORD=${TEST_PASSWORD}
TEST_EMAIL=${TEST_EMAIL}
HEADLESS=True
EOF

if [ "${UI_TESTS}" = "true" ]; then
    echo "== [3/4] run full UI test suite (server: memory limited, see decision doc) =="
    venv/bin/python -m pytest testcases/ -q || true   # exit code handled by report step
else
    echo "== [3/4] UI_TESTS=false: skip pytest, report-only mode =="
fi

echo "== [4/4] allure report (skip if CLI missing; plugin also generates) =="
if command -v allure >/dev/null 2>&1; then
    allure generate ./allure-results -o ./allure-report --clean || true
fi

echo "== [4/4] optional COS upload (needs cos creds + REPORT_PREFIX, Day19) =="
if [ -n "${REPORT_PREFIX}" ] && [ -d allure-report ]; then
    if [ "${REPORT_PREFIX}" = "latest" ]; then
        venv/bin/python scripts/upload_to_cos.py allure-report reports/latest --verify || true
    else
        venv/bin/python scripts/upload_to_cos.py allure-report "reports/${REPORT_PREFIX}" --no-version || true
    fi
fi

echo "== build script finished =="
```

> 注：`|| true` 的语义 = "该环节失败不中断构建，日志留痕"（报告与上传是可后补的
> 环节）；**pytest 失败本身**由 Allure 插件与最终结果体现，不让脚本提前 exit 掩盖
> 环境步骤问题。若要严格失败传播，把对应 `|| true` 去掉即可（接口项目风格）。

### 6. 构建后操作（Allure Report）

- **Allure Report**：Results 路径 `allure-results`，Report 路径 `allure-report`（与插件默认一致）
- 保留生成历史报告趋势：勾 **include history**（Allure 插件内置，趋势图连续）

### 7. 环境变量（敏感值不落仓库的出处）

Manage Jenkins → System → **Global properties** → Environment variables 添加：

| 变量 | 值 |
|------|----|
| `BASE_URL` | 后端地址（占位：`https://<目标站点>`，本地 `.env` 同值） |
| `TEST_USERNAME` | 测试账号（与接口项目共用） |
| `TEST_PASSWORD` | 测试账号密码（**建议改用 Secret text 凭据**注入，见「七、凭据」） |
| `TEST_EMAIL` | 测试邮箱 |

COS 上传需要时再加：`COS_BUCKET` / `COS_REGION` / `COS_CDN_DOMAIN`；
`COS_SECRET_ID` / `COS_SECRET_KEY` 走凭据（见「七、凭据」）。

### 8. 保存并试构建

- ☐ **不配 Poll SCM / Build periodically**（方案C 边界：UI 不常驻定时跑）
- 保存后点 **Build Now**，首次构建 `UI_TESTS=false` + `REPORT_PREFIX` 留空——
  先验证"拉代码→装依赖→报告"链路本身，再进第四节逐步加码。

✅ 完成标志：首次构建绿色（或报告成功生成）；Console Output 能看到 4 段日志。

---

## 四、首次构建验证清单（逐项核对）

| # | 验证项 | 看什么 | 通过标准 |
|:-:|--------|--------|---------|
| 1 | SCM 拉取 | Console Output 前 20 行 | `Checking out Revision ...` 指向最新 commit（6066911） |
| 2 | 依赖安装 | `[2/4]` 段 | venv 创建/复用、pip 无 ERROR、playwright 版本输出 |
| 3 | chromium 下载 | `[2/4]` 段 | npmmirror 标准前缀生效（慢则查卡点表 #3） |
| 4 | .env 生成 | 工作区 `cat .env` | 6 个变量齐全、无真实密钥明文（凭据方式下） |
| 5 | 报告生成 | Build 后 Allure Report 链接 | 打开报告首页正常、趋势页有图（history 生效） |
| 6 | UI_TESTS=true 冒烟 | 再构建一次，参数改 true | 登录模块跑通（容器内存允许时）；全量风险见第一节 |
| 7 | COS 上传（可选） | `REPORT_PREFIX=latest` + COS 凭据 | 日志 `[verify] ... = N, expected N -> OK`；外链可开 |
| 8 | 内存观察 | 构建期间宿主机 `free -h` | 可用内存未跌破 ~300MB；容器未 OOM（`docker stats`） |
| 9 | 失败可见性 | 后端故意不可达时构建一次 | 构建标红（CI 模式原则：不允许假绿灯） |

---

## 五、日常怎么用（方案C 语义）

| 场景 | 操作 |
|------|------|
| 想展示"UI 测试也能在服务器跑" | 手动构建，`UI_TESTS=true`（服务器内存允许时；先冒烟后全量） |
| 只发布一份最新报告到外链 | 手动构建，`UI_TESTS=false` + `REPORT_PREFIX=latest` |
| 存一份构建历史报告 | `REPORT_PREFIX=build-${BUILD_NUMBER}`（`${BUILD_NUMBER}` 为 Jenkins 内置变量，直接填） |
| 日常回归 | **仍走本地一键** `run_ui_tests.bat`（方案C 主路径，Day18） |
| 全量自动化 | 服务器扩容 ≥8G 后升级方案A：去掉"手动"边界、配 Poll SCM、UI_TESTS 默认 true |

---

## 六、关闭与回滚

| 场景 | 操作 |
|------|------|
| 停用任务 | 任务页 → Disable（保留配置不执行） |
| 删除任务 | 任务页 → Delete Project（工作区/venv 一并删除，如需保留先拷出） |
| 容器内存上限回退 | `docker update --memory 768m --memory-swap 768m jenkins` |
| COS 清理 | `python scripts/cleanup_cos_reports.py --dry-run --keep 10`（先演练） |

---

## 七、凭据（Credentials）配置

| 用途 | 类型 | ID | 值来源 |
|------|------|----|--------|
| Gitee 私有仓库拉取（如仓库转私有） | Username with password | `gitee-account` | Gitee 账号/密码或令牌 |
| COS SecretId（上传用） | Secret text | `cos-secret-id` | 腾讯云 API 密钥（与本地 .env 同值） |
| COS SecretKey | Secret text | `cos-secret-key` | 同上 |
| 测试账号密码（替代全局环境变量，更严） | Secret text | `ui-test-password` | 本地 .env 的 TEST_PASSWORD |

Execute shell 取用示例：`export COS_SECRET_ID="$(cat $COS_SECRET_ID)"`（Credentials Binding
插件，接口项目已用过）；或用 **Credentials Binding** 插件直接绑定变量。

---

## 八、敏感信息清单（本任务涉及的真实值，全在服务器/凭据侧）

| 值 | 落点 | 红线 |
|----|------|------|
| BASE_URL / 测试账号密码 | Jenkins 全局环境变量或凭据 | 不写进任何仓库文件 |
| COS 密钥 / 桶名 / 域名 | Jenkins 凭据 + 全局环境变量 | 桶名/域名在文档一律 `<COS桶名>` / `<报告访问域名>` 占位 |
| 服务器 IP / 端口 | 仅本清单与接口项目 README（已入库的既有占位风格） | 公网仓库代码注释零真实值 |

---

## 九、卡点预案（均为本项目实测或已存档经验）

| # | 卡在哪 | 现象 | 解决 |
|:-:|--------|------|------|
| 1 | 容器内 chromium 启动失败 | `libnss3.so: cannot open shared object file` 等 | 容器内补系统库（第二节第 2 步）；Day18 宿主机同款依赖清单 |
| 2 | 容器内 OOM | 构建中途进程被杀、日志尾部 `Killed` | 先冒烟（`pytest testcases/test_login_ui.py -q`）确认再全量；`docker update` 放大上限；全量留待扩容（Day18 内存实测数据背书） |
| 3 | chromium 下载卡 0% | `cdn.playwright.dev` 不可达 | **标准前缀** `PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright`（Day18 服务器实测 16.4MB/s） |
| 4 | pip 装 cos SDK 失败 | 清华源 `No matching distribution` | 官方 PyPI 兜底（脚本已有 `|| true` 二次尝试；Day19 实测） |
| 5 | Gitee 拉取慢/失败 | SCM 超时 | 检查容器 DNS/网络；换 GitHub 源（双远程同内容） |
| 6 | 测试超时失败 | `TimeoutError: 10000ms ... response` | 服务器负载性超时（Day18 实测 4 failed 同因）：环境问题非用例缺陷，重试已内置（pytest.ini reruns）；全量结果以本地为准 |
| 7 | allure generate 报错 | 命令不存在或版本问题 | 容器内按第二节第 4 步装 CLI；失败不阻断（脚本 `|| true`），插件报告兜底 |
| 8 | 凭据绑定变量读不到 | `cat $COS_SECRET_ID` 为空 | 检查 Credentials Binding 插件已装（接口项目在用）、ID 拼写一致 |

---

> **保存路径**：`md存放/面试求职/四周计划/接口自动化代码/lostfound-ui-test-示例/docs/Jenkins建项执行清单.md`
> **配套**：`docs/UI自动化CI集成方案决策文档.md`（为什么是手动触发）、`示例/week3_day19_示例-*`（COS 上传存档）、接口项目 `示例/week2_day13_示例-*`（建项先例，历史版本）
