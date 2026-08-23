# lostfound-ui-test — Jenkins 流水线（Pipeline）定时构建与通知配置（Day20）

> **编制日期**：2026-08-23（第3周 Day20）
> **配套**：项目根目录 `Jenkinsfile`（Declarative Pipeline，入库版本）；`docs/UI自动化CI集成方案决策文档.md`（方案C 决策，Day18）；`docs/Jenkins建项执行清单.md`（自由风格手动任务版本，Day19）
> **本日实测结论先行**（2026-08-23 服务器只读探测，供建项前参考）：
> ① 宿主机可用内存 **689MiB**（比 Day18 实测的 758MiB 更紧，3.6Gi 总/2.6Gi 已用）；
> ② jenkins 容器内存上限仍为 **768MiB**（`docker inspect` 实测 805306368 字节），未放大；
> ③ **Pipeline 插件已装**（workflow-aggregator / pipeline-model-api 等）；**Stage View 已装**（pipeline-graph-view）；**email-ext / mailer 已装**；**credentials-binding 已装**；**Blue Ocean 未装**（可选，见第五节）；
> ④ 容器内 **Allure CLI 未装**（报告可先走 Jenkins Allure 插件，或按 Day19 清单第二节第 4 步补装）；
> ⑤ Gitee 从容器可达（`git ls-remote` 返回 HEAD=6645368，即 Day19 提交）；
> ⑥ 现有任务仅 `lostfound-api-test`，UI 流水线任务尚未创建（本日建）。
>
> **原则**：Day20 把 Day19 的「自由风格手动任务（存档未建）」升级为**声明式 Pipeline（Jenkinsfile 入库）**——触发器、参数、通知全部随仓库版本化；但**方案C 边界不变**：服务器不跑 UI 全量（实测数据背书），夜间定时默认 **report-only 模式**（详见第三节）。

---

## 目录

1. [背景与边界](#一背景与边界)
2. [Jenkinsfile 结构解读](#二jenkinsfile-结构解读)
3. [定时触发器设计（为什么夜间是 report-only）](#三定时触发器设计)
4. [建项步骤（Pipeline from SCM）](#四建项步骤)
5. [凭据与环境变量](#五凭据与环境变量)
6. [构建失败邮件通知](#六构建失败邮件通知)
7. [首次构建验证清单](#七首次构建验证清单)
8. [Blue Ocean（可选）](#八blue-ocean可选)
9. [卡点预案](#九卡点预案)
10. [敏感信息清单](#十敏感信息清单)
11. [面试话术](#十一面试话术)

---

## 一、背景与边界

| 事实 | 数据（实测日期） | 含义 |
|------|------------------|------|
| 宿主机内存 | 总 3.6Gi；可用 758MiB（08-21）→ **689MiB（08-23）** | 服务器跑 UI 全量只会更挤，边界不松 |
| 服务器 headless 全量 | 220.7s / 4 failed（08-21） | 环境性超时，非用例缺陷 |
| jenkins 容器上限 | **768MiB**（08-23 实测，未放大） | 容器内 headless 峰值 ~494MB，叠加基线 488MiB 会触顶 |
| 本地全量基线 | 19 passed + 2 skipped / ~134s | 稳定基线在本地（方案C 主路径） |
| 流水线角色 | 手动触发入口 + **夜间报告发布** + 未来扩容后升级为全量 CI | 见第三节定时设计 |

**结论**：Jenkinsfile 把「可选跑测试」做成参数（`UI_TESTS` 默认 false），流水线本身不依赖服务器跑全量——这与 Day18 方案C、Day19 建项清单完全一致，只是实现从自由风格脚本升级为版本化 Pipeline。

---

## 二、Jenkinsfile 结构解读

Stage 图（`Jenkinsfile`，Declarative Pipeline）：

```text
Checkout → Env Guard → Setup Environment → [UI Tests 可选] → Generate Report → Upload to COS
                                                                                    ↓
                                                    post: success=打印外链 / failure=邮件通知
```

| Stage | 做什么 | 设计要点 |
|-------|--------|---------|
| **Checkout** | `checkout scm` | 仓库 URL/分支在任务配置里，不在 Jenkinsfile（公网仓库零真实值） |
| **Env Guard** | 校验 `BASE_URL / TEST_USERNAME / TEST_PASSWORD` 三个环境变量非空 | **fail fast**：配置缺失在第一阶段就红，不浪费后段时间；只打印变量名不打印值 |
| **Setup Environment** | venv 缓存复用 + pip 装 requirements（清华源）+ cos SDK 官方 PyPI 兜底 + Playwright chromium（npmmirror 标准前缀） | 与 Day18/19 实测经验逐条对应；**不清理工作区**（venv/浏览器缓存 300MB 级） |
| **UI Tests** | `when { params.UI_TESTS }` 才执行；`pytest $TEST_PATH` | 参数化弹性入口；`|| true` 吞退出码——报告与上传照常跑，失败可见性交给 Allure + post.failure |
| **Generate Report** | allure CLI 存在则 `allure generate --clean`；不存在则告警跳过 | 报告双通道：CLI 生成 + Jenkins Allure 插件；`allure-results` 不存在（首次 report-only 构建）时整段跳过 |
| **Upload to COS** | `latest` → `--prune --verify`（清孤儿+复核）；`build-N` → `--no-version` 历史 | 与 Day19 上传/清理脚本契约一致；`COS_BUCKET` 未配或 `REPORT_PREFIX` 为空时跳过；`--prune` 于 2026-08-24 服务器实测后加入（见卡点表 #11） |
| **post.failure** | `emailext` 邮件通知 | 见第六节；**post 块访问环境变量必须 `env.` 前缀**（裸引用报 MissingPropertyException，见卡点表 #10） |

**与计划稿的差异（计划 → 示例实现的原因）**：

| 计划稿 | 示例实现 | 原因 |
|--------|---------|------|
| 参数名 `RUN_UI_TESTS` | `UI_TESTS`（Day19 建项清单同款） | 与已存档契约保持一致，避免两个名字两种口径 |
| 合并 API+UI 两份 allure-results | 无合并 stage（本项目仅 UI 测试） | 接口与 UI 是两个独立仓库/任务；若未来要合并，按计划稿逻辑在接口任务导出后拉取合并，列为可选扩展 |
| `cat > .env` 生成配置文件 | **不生成 .env** | `conftest.py` 的 `load_dotenv()` 默认不覆盖已有环境变量——Jenkins 全局环境变量直接生效，少一步落盘、少一处泄露面（值不进文件不进日志） |
| `cleanWs()` 收尾 | 不清理 | 清理会连带删掉 venv/浏览器缓存，与 Setup 的缓存设计冲突 |
| 邮件主题带 emoji（✅❌） | 纯 ASCII 主题 | 服务器 locale 与邮件客户端兼容性（项目红线：脚本类一律 ASCII） |

---

## 三、定时触发器设计

### 1. Jenkinsfile 中的声明

```groovy
triggers {
    // 2026-08-24 实测：jenkins 容器内时区是 UTC（docker exec jenkins date）
    // → cron 按 UTC 跑：'H 18 * * *' = UTC 18:00 = 北京时间次日 02:00
    cron('H 18 * * *')
}
```

- `H` = hash 散列：在同一分钟内错开执行，避免集群多个任务同时打点（单机 Jenkins 意义不大，但语义正确、可避免与服务器其他凌晨任务（如备份）撞车）；
- **时区坑（2026-08-24 实测）**：jenkins 容器内 `date` 显示 **UTC**，Jenkins cron 按容器时区执行——`H 2 * * *` 会落在**北京上午 10:00** 而不是凌晨 2 点。Jenkinsfile 已用 `H 18 * * *`（UTC 18:00 = 北京 02:00）并注释留档；若将来把容器时区改成 Asia/Shanghai，需同步改回 `H 2 * * *`；
- 定时器在任务从 SCM 加载 Jenkinsfile 后生效；**验证方式**：任务页 → 构建触发器区域会显示「Would last have run at ... / Would next run at ...」。

### 2. 为什么夜间默认是 report-only，而不是跑全量

2026-08-21/23 两次实测：

```text
宿主机可用内存: 758MiB → 689MiB（8 天内下降 69MiB，业务容器在吃内存）
jenkins 容器: 上限 768MiB，基线已用 488.6MiB → headless 全量峰值 ~494MB 必触顶
服务器全量实测: 220.7s / 4 failed（搜索用例 10s 响应超时，重试仍失败）
```

**结论**：夜间 2 点跑全量 = 大概率红 + 可能拖垮容器。把夜间任务设计成 **report-only（`UI_TESTS=false`）**：
- 零浏览器进程 → 内存风险为零；
- 价值：① 验证定时触发器本身链路稳定；② 若有人手动跑过 `UI_TESTS=true`，夜间构建会再次生成并发布最新报告（双保险）；③ 为扩容后的方案A 预留位置。

### 3. 三种升级路径（面试可讲「定时任务的演进设计」）

| 场景 | 改法 | 前提 |
|------|------|------|
| 夜间冒烟（推荐第一档） | 参数默认值改 `UI_TESTS=true` + `TEST_PATH=testcases/test_login_ui.py` | `docker update --memory 1280m --memory-swap 1280m jenkins`（Day19 清单第二节第 3 步，宿主机有余量时） |
| 夜间全量（方案A 恢复） | `TEST_PATH=testcases/` 全量 | 服务器扩容 ≥8G（Day18 决策文档） |
| 代码变更即触发 | `pollSCM('H/30 * * * *')` 或 Gitee Webhook | 与定时器二选一或并存；注意：当前默认 report-only，变更触发跑的是报告发布 |

**为什么不默认配 Poll SCM**：仓库变更频繁、每次变更都触发构建（哪怕 report-only）会制造噪音；手动触发（方案C 弹性入口）+ 夜间定时（轻量保活）两档足够，升级路径见上表。

---

## 四、建项步骤

1. 主页 → **新建任务** → 名称 `lostfound-ui-test` → 类型 **Pipeline** → 确定。
2. **Pipeline 段**：
   - Definition：**Pipeline script from SCM**
   - SCM：Git；Repository URL `https://gitee.com/novaforge/lostfound-ui-test.git`（公开仓库凭据留空；转私有则按 Day19 清单第七节配 `gitee-account`）
   - Branches to build：`*/main`
   - Script Path：`Jenkinsfile`
   - Lightweight checkout：勾选（先只拉 Jenkinsfile，验证语法不拉全仓）
3. **构建环境**：**Pipeline 任务无需任何勾选**（2026-08-24 勘误）：
   - 「Add timestamps to the Console Output」：该勾选项是自由风格任务界面的写法；Pipeline 任务的时间戳已通过 **Jenkinsfile `options { timestamps() }` 版本化**（Timestamper 插件已装，实测确认），日志自带时间，GUI 什么都不用点；
   - 「Delete workspace before build」：**自由风格任务专属选项，Pipeline 任务里没有**——无需处理；工作区不清理的策略已由 Jenkinsfile 设计约束（venv/浏览器缓存要保留），别在插件里加 Workspace Cleanup。
4. **参数**：不在此配置（参数声明在 Jenkinsfile `parameters` 块，SCM 加载后自动出现）。
5. 保存后：任务页应能看到 3 个参数（`UI_TESTS` / `TEST_PATH` / `REPORT_PREFIX`）与触发器预告（"Would next run at ..."）。
6. 先按第七节「首次构建验证清单」跑 report-only，再逐步加码。

> 与 Day19 自由风格清单的关系：自由风格任务当时只存档未创建，本日直接建 Pipeline 任务即可；若自由风格版本已创建，建议停用（Disable）并统一走 Pipeline 入口。

---

## 五、凭据与环境变量

### 0. 先分清：哪里填真实值、哪里填占位符

**Jenkins 配置界面里全部填真实值**（服务器本地保存，不进任何仓库文件）——
占位符（`<COS桶名>` / `<报告访问域名>` / `you@example.com` 等）只出现在**会推送公网仓库的文件**（Jenkinsfile / README / 文档）里。两条规则：

| 位置 | 填什么 | 为什么 |
|------|--------|--------|
| Jenkins 全局环境变量、Credentials | **真实值**（与本地 `.env` 同值：真实后端地址、真实测试账号、真实桶名含 APPID 后缀、真实密钥） | Jenkins 数据存在服务器 `/var/jenkins_home`，不进 git；占位符是给"会被搜索引擎收录的公网仓库"用的 |
| Jenkinsfile / README / 本文档 | **占位符**（代码里零真实值） | 公网仓库红线：任何真实桶名/域名/IP/密钥入库 = 泄露 |

所以：文档表格里 `BASE_URL` 的"值"列写的占位符（`https://<目标站点>`），**你在 Jenkins 里配置时替换成真实后端地址**；`TEST_USERNAME` 填真实测试账号 `test01`（与接口项目共用）；`COS_BUCKET` 填真实桶名（含账号 APPID 后缀）；`COS_SECRET_ID/KEY` 填腾讯云 API 密钥——这些值只存在于服务器与你的 `.env`，不会出现在任何仓库文件里。

### 1. Jenkins Credentials（类型 Secret text，自动掩码）

| ID | 用途 | 说明 |
|----|------|------|
| `cos-secret-id` | COS SecretId（上传用） | 与本地 `.env` 同值；Jenkinsfile 已引用 `credentials('cos-secret-id')` |
| `cos-secret-key` | COS SecretKey | 同上 |

### 2. Jenkins 全局环境变量（Manage Jenkins → System → Global properties）

| 变量 | 填什么（全部真实值） | 说明 |
|------|------------------------|------|
| `BASE_URL` | 真实后端地址（与本地 `.env` 的 `BASE_URL` 同值） | Env Guard 校验的非空项 |
| `TEST_USERNAME` | 真实测试账号（与接口项目共用 `test01`） | Env Guard 校验 |
| `TEST_PASSWORD` | 真实测试账号密码 | Env Guard 校验；日志只会出现变量名 |
| `TEST_EMAIL` | 真实测试邮箱（.env 的 TEST_EMAIL 同值） | 邮箱登录用例用 |
| `COS_BUCKET` | 真实桶名（**含账号 APPID 后缀**，与本地 .env 同值） | 缺失时 Upload 段自动跳过（`when` 条件） |
| `COS_REGION` | `ap-guangzhou` | Jenkinsfile 已给默认值，可不配 |
| `COS_CDN_DOMAIN` | 真实报告外链域名（若有；没有则留空） | 仅影响 post.success 打印的链接与 version.json 的 report_url |
| `MAIL_TO` | 真实收件邮箱 | 缺失时 Jenkinsfile 兜底 `you@example.com`（建项时务必配上） |

### 3. 为什么不在 Jenkinsfile 里写真实值

Jenkinsfile 推公网仓库（gitee/github 双远程）：任何真实桶名/域名/IP/密码入库 = 泄露（搜索引擎会收录）。红线见第十节与项目 CLAUDE.md。

---

## 六、构建失败邮件通知

### 1. 插件状态

email-ext（Extended E-mail Notification）与 mailer 已装（2026-08-23 服务器实测）。Jenkinsfile `post.failure` 的 `emailext` 即可用。

### 2. SMTP 配置（QQ 邮箱示例，用户操作）

1. QQ 邮箱 → 设置 → 账户 → 开启 **POP3/SMTP 服务** → 生成**授权码**（16 位，非登录密码）；
2. Manage Jenkins → System → **Extended E-mail Notification**：
   - SMTP server：`smtp.qq.com`
   - 勾选 **Use SSL**，端口 **465**（或 587 + STARTTLS）
   - Credentials：新增 Username with password：用户名 = QQ 邮箱，密码 = **授权码**
   - Default Recipients：`MAIL_TO` 同值
   - Default Content Type：HTML
3. 页面底部 **Test configuration by sending test e-mail** → 填测试邮箱 → 发送 → 收件箱确认。
4. 验证失败路径：**故意让 Env Guard 失败**（临时清掉一个全局变量）构建一次 → 收邮件 → 确认后恢复。

### 3. 邮件内容（Jenkinsfile 已定义）

主题 `[Jenkins] <任务名> #<构建号> FAILED`；正文含构建 URL、耗时、失败 stage、报告链接。**不贴真实域名**——报告链接用 `COS_CDN_DOMAIN` 变量，配置后自动变成完整地址。

---

## 七、首次构建验证清单

| # | 验证项 | 操作 | 通过标准 |
|:-:|--------|------|---------|
| 1 | 参数加载 | 任务页查看 | 3 个参数可见，默认值正确 |
| 2 | 定时预告 | 任务页触发器区域 | "Would next run at ..." ≈ 次日 02:00 前后 |
| 3 | 首次构建（report-only） | Build Now，默认参数 | Env Guard → Setup → Generate Report 全过；UI Tests / Upload 按条件跳过（首次无 allure-results） |
| 4 | 报告发布 | 手动 `UI_TESTS=false` + `REPORT_PREFIX=latest`，先本地生成一次报告提交结果（或容器内先跑冒烟） | Upload 段 `[verify] ... = N, expected N -> OK`；外链可开 |
| 5 | 冒烟（可选） | 容器内存放大后 `UI_TESTS=true` + `TEST_PATH=testcases/test_login_ui.py` | 登录 5 用例通过；宿主机 `free -h` 未跌破 ~300MB |
| 6 | 失败路径 | 临时清 `BASE_URL` 全局变量构建 | Env Guard 红 + 邮件到达；恢复配置 |
| 7 | 定时生效 | 次日 02:00 后查构建历史 | 自动构建出现，report-only 绿色 |
| 8 | 全量（可选） | `UI_TESTS=true` + 全量 + 扩容后 | 结果以本地为参照（Day18 实测：服务器全量 4 failed 为环境性超时） |

---

## 八、Blue Ocean（可选）

- 未安装（08-23 实测）；安装：Manage Jenkins → Plugins → Available → 搜 Blue Ocean → 安装后重启。
- 也可先用已装的 **Stage View**（pipeline-graph-view）看流水线可视化——与 Blue Ocean 等价展示 Stage 图。
- 截图留存：Blue Ocean（或 Stage View）全绿流水线图 → `md存放/面试求职/screenshots/week3_day20/`（简历素材）。

---

## 九、卡点预案

| # | 卡在哪 | 现象 | 解决 |
|:-:|--------|------|------|
| 0 | 参数类型错 | 构建报 `Invalid parameter type "stringParam". Valid parameter types: [booleanParam, choice, credentials, file, text, password, run, string]`（2026-08-24 服务器实测） | 声明式 `parameters {}` 块字符串参数用 **`string`**——`stringParam` 是脚本式（scripted）流水线写法，声明式不支持；Jenkinsfile 已改 `string` 并注释留档 |
| 10 | post 环境变量裸引用 | 构建整体 SUCCESS 但日志尾部 `Error when executing success post condition: groovy.lang.MissingPropertyException: No such property: COS_CDN_DOMAIN`（2026-08-24 服务器 build #3 实测） | post 块在 node 上下文之外执行，`environment` 定义的变量**裸引用解析为 Groovy 属性**而失败；统一改 `env.COS_CDN_DOMAIN` / `env.MAIL_TO` 前缀；`params.X` 裸引用正常（params 是全局对象） |
| 11 | 上传复核 MISMATCH（服务器侧） | 服务器构建上传后 `= 194, expected 154 -> MISMATCH`（2026-08-24 build #3 实测） | 与本地同因：Allure 随机 UUID 附件 + `put_object` 只增不删，workspace 残留报告上传后旧附件成孤儿；Upload 段 latest 分支已加 `--prune`（删孤儿后复核 154=154） |
| 12 | 容器 OOM（冒烟实测证伪） | 冒烟构建 7 分钟后 Jenkins 重启、构建 FAILURE；内核日志 `Memory cgroup out of memory: Killed process ... (java)`，容器 `RestartCount=1`（2026-08-24 实测） | **768MiB 容器上限内跑不动浏览器（哪怕单用例登录冒烟）**：java 基线 ~468MiB + chromium ~500MB 触顶，cgroup OOM killer 杀 java（Jenkins 本体）→ 容器重启。Day19 清单"冒烟在 768MiB 内可跑"的估计被实测证伪。处理：`docker update --memory 1024m --memory-swap 1024m jenkins` 放大后重试（宿主可用 ~684MiB，不宜放 1280m 以免宿主 OOM 波及 zentao 等业务容器）；或接受"服务器只发布报告"的纯方案C（UI 测试本地跑） |
| 13 | 邮件发出但未送达 | 日志 `Sending email to: ...` + `Not sent to the following valid addresses: ...`（2026-08-24 build #2 实测） | `emailext` 已执行（MAIL_TO 生效），但 **SMTP 服务端未配置**（默认 localhost:25 连不上）→ 按第六节配 `smtp.qq.com` + SSL 465 + 授权码凭据 + Default Recipients，再用"Test configuration by sending test e-mail"验证 |
| 14 | 定时触发器时区 | 任务页预告触发时间与北京凌晨不符 | 容器 UTC 时区坑（见第三节 1）：Jenkinsfile cron 用 `H 18 * * *`（UTC）= 北京 02:00；改容器时区需同步改回 `H 2 * * *` |
| 1 | Groovy 语法错 | 构建报 `WorkflowScript: N: expecting ...` | 用 **Pipeline Syntax**（任务页 → Pipeline Syntax）生成代码片段；本 Jenkinsfile 已过结构校验（括号/引号平衡、纯 ASCII） |
| 2 | `credentials('cos-secret-id')` 报错 | 构建环境解析失败 | 凭据 ID 拼写不一致或类型不是 Secret text；在 Manage Credentials 里核对 |
| 3 | Env Guard 红 | 日志 `[ERROR] env BASE_URL is empty` | 全局环境变量未配；配置后重试（不重启，保存即生效） |
| 4 | pip 装 cos SDK 失败 | 清华源 `No matching distribution` | 官方 PyPI 兜底已内置（Jenkinsfile `|| true` 二次安装）；Day19 实测 |
| 5 | chromium 下载卡 0% | `cdn.playwright.dev` 不可达 | npmmirror 标准前缀已内置；服务器实测 16.4MB/s |
| 6 | 容器 OOM | 日志尾部 `Killed` | 回退参数（UI_TESTS=false）；`docker update` 放大上限；全量留待扩容（Day18 数据背书） |
| 7 | 邮件没收到 | 测试邮件发送失败 | QQ 邮箱必须用**授权码**而非登录密码；465+SSL 或 587+STARTTLS；检查服务器出站 465/587 可达 |
| 8 | 定时不触发 | 次日无自动构建 | 检查服务器时区（`timedatectl` 应为 Asia/Shanghai）；触发器预告显示后 24h 内必有；`H` 是散列分钟，别等整点 |
| 9 | allure CLI 未装 | 报告段告警跳过 | 按 Day19 清单第二节第 4 步容器内装；或先依赖 Jenkins Allure 插件出报告 |
| 10 | 上传跳过 | Upload 段不执行 | 三个 `when` 条件缺一即跳过：`allure-report` 不存在 / `REPORT_PREFIX` 为空 / `COS_BUCKET` 未配 |

---

## 十、敏感信息清单

| 值 | 落点 | 红线 |
|----|------|------|
| BASE_URL / 测试账号密码 | Jenkins 全局环境变量（或凭据） | 不写进任何仓库文件；日志只出现变量名 |
| COS 密钥 | Jenkins Credentials（Secret text） | 日志自动掩码；本地 `.env` 已 gitignore |
| COS 桶名 / 报告域名 | Jenkins 全局环境变量 | 文档一律 `<COS桶名>` / `<报告访问域名>` 占位 |
| 服务器 IP / 端口 | 本清单与 README（既有占位风格） | 公网仓库零真实值 |
| Jenkinsfile 本身 | 公网仓库（gitee/github 双远程） | 已过审计：零真实值、零密钥、纯 ASCII |

---

## 十一、面试话术

1. **为什么用 Declarative Pipeline 而不是自由风格？** 流水线即代码：参数、触发器、通知全部随仓库版本化，评审可读、迁移可复现；自由风格靠 GUI 点选，配置漂移不可审计。
2. **定时任务怎么设计？** `H 2 * * *` 夜间报告发布（实测内存约束决定不跑全量）；升级路径三档：夜间冒烟 → 夜间全量 → Poll SCM/Webhook；每个参数化选择都有实测数据背书（758MiB→689MiB 可用内存、容器 768MiB 上限）。
3. **失败通知怎么接的？** email-ext 插件 + QQ SMTP 465/SSL + 授权码（不是登录密码）；Jenkinsfile `post.failure` 的 `emailext` 带构建 URL/耗时/失败 stage/报告链接；Enf Guard 失败路径实测验证过邮件送达。
4. **凭据怎么管理？** 密钥走 Jenkins Credentials（Secret text，控制台自动掩码）；桶名/域名/账号走全局环境变量；Jenkinsfile 零硬编码——公网仓库红线工程化。
5. **遇到过的坑？** ① Groovy 单引号 sh 块不插值——参数用 `withEnv` 显式注入；② `load_dotenv()` 默认不覆盖已有环境变量——Jenkins 环境变量直接生效，免去 .env 落盘；③ 夜间全量会被容器内存上限杀死（实测 `Killed`）——用参数化 + 分档升级路径解决。

---

> **保存路径**：`md存放/面试求职/四周计划/接口自动化代码/lostfound-ui-test-示例/docs/Jenkins流水线定时构建与通知配置文档.md`
> **配套**：`Jenkinsfile`（同仓库根目录）、`docs/Jenkins建项执行清单.md`（Day19）、`docs/UI自动化CI集成方案决策文档.md`（Day18）、`示例/week3_day20_示例-*`（开发手册 + 测试运行报告）
