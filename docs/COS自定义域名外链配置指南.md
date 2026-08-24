# COS 自定义域名外链配置指南（Day21 三链接验证配套）

> **编制日期**：2026-08-24（第3周第21天）
> **背景**：Day21 三链接终极验证发现——计划文档中的报告域名在公网 DNS 不存在（NXDOMAIN），
> 而真实可用域名（`<被测系统域名>`）托管的是失物招领 Web 应用（Vue SPA，nginx fallback 会
> 吃掉所有未知路径）；COS 桶内报告对象存在（复核 74=74 OK）但 **`COS_CDN_DOMAIN` 未配置、
> 桶未绑定自定义域名 → 报告无外链**。本指南补齐这一环。
> **红线**：本指南一律占位符；真实域名/桶名只存在于个人笔记与 `.env`。

---

## 一、总体流程

```text
COS 控制台绑定自定义域名（开通 CDN）→ 域名服务商加 CNAME → 桶权限公共读 → SSL 证书
→ .env 配 COS_CDN_DOMAIN → 重跑上传（--prune --verify）→ version.json 写 report_url
→ 浏览器 + nslookup/curl 双重验证 → 截图归档
```

## 二、操作步骤（用户操作，腾讯云控制台 + 域名服务商）

### 1. COS 控制台绑定自定义域名

1. 腾讯云控制台 → 对象存储 COS → 存储桶列表 → 目标桶 → **域名管理**；
2. **自定义源站域名** → 绑定域名：`<报告访问域名>`（建议独立子域名，如 `reports` 前缀，
   与被测系统域名分开，互不干扰）；
3. 勾选**开通 CDN 加速** → 记录系统生成的 CNAME 目标（形如
   `<报告访问域名>.cdn.dnsv1.com`）。

### 2. 域名服务商添加 CNAME

| 项 | 值 |
|----|----|
| 记录类型 | CNAME |
| 主机记录 | `reports`（子域名前缀） |
| 记录值 | 第 1 步拿到的 CDN CNAME 目标 |

### 3. 权限与 HTTPS

- **桶权限**：公共读（存储桶策略 / ACL 允许 `GetObject`，教学项目简单可控）；
  或保持私有 + CDN 回源鉴权（更安全，需额外配置）；
- **HTTPS**：COS 域名管理上传 SSL 证书（腾讯云免费证书）；未配置时先用 `http://` 验证。

### 4. 生效等待

CNAME 生效一般 10 分钟~24 小时（多数分钟级）。验证命令：

```bash
nslookup <报告访问域名>            # 应返回 CNAME 链，最终到 CDN 节点
curl -skI https://<报告访问域名>/reports/latest/index.html   # 期望 200 + 内容长度几十 KB（Allure 首页）
```

### 5. .env 配置与重传

```bash
# .env 新增（UI 项目；与接口项目 Day14 配置同款）
COS_CDN_DOMAIN=https://<报告访问域名>

# 重跑上传（--prune 清孤儿 + --verify 复核；version.json 自动写 report_url）
.venv\Scripts\python.exe scripts\upload_to_cos.py allure-report reports/latest --prune --verify
# 期望: [prune] no orphan / [verify] COS objects under reports/latest/ = N, expected N -> OK
# 期望: version.json 含 "report_url": "https://<报告访问域名>/reports/latest/"
```

### 6. 三链接记录更新

| 服务 | 地址（个人笔记） | 状态 |
|------|----------------|:----:|
| 被测系统 | `https://<被测系统域名>/`（Vue 应用）或 `http://<服务器IP>:<端口>` | ✅ |
| 禅道 | `http://<服务器IP>:8081` | ✅ |
| Allure 报告 | `https://<报告访问域名>/reports/latest/index.html` | ⬜ 本指南配置后 ✅ |

截图归档：`screenshots/week3_day21/三个链接验证.png`（截图只存本地/被 gitignore 的 screenshots/，不入库文档）。

---

## 三、卡点排查表

| # | 现象 | 解决 |
|:-:|------|------|
| 1 | `nslookup` 查不到新子域名（NXDOMAIN） | CNAME 解析未生效或记录值填错——核对域名服务商记录 + COS 域名管理页的 CNAME 目标；个别解析器有缓存，换 `nslookup <域名> 223.6.6.6` 复测 |
| 2 | 访问报 `403 AccessDenied` | 桶权限未开放公共读——检查存储桶策略/ACL 是否允许 `GetObject`；或改用 CDN 回源鉴权配置 |
| 3 | 访问报 `404` | 路径不对——确认对象前缀 `reports/latest/index.html` 真实存在（`--verify` 复核数一致即可排除） |
| 4 | 页面打开但样式全丢（CSS 404） | CDN 缓存了 SPA fallback 或历史错误响应——CDN 控制台刷新缓存（目录刷新 `reports/latest/`）后重试 |
| 5 | 返回的是 Vue 应用首页 | 该域名被 nginx SPA fallback 接管（`try_files ... /index.html`）——确认访问的是 COS 自定义域名而非服务器域名；若确实走了服务器，检查 nginx 是否把该域名代理到了错误站点 |
| 6 | HTTPS 证书无效 | COS 域名管理上传证书（腾讯云免费证书）；或先用 `http://` 验证功能，再补证书 |

---

## 四、与现有设计的关系

- **version.json 的 `report_url` 字段是 Day19 预留的**：上传脚本仅在配置 `COS_CDN_DOMAIN` 时写入
  `report_url`（避免真实域名落桶）——本指南配置后该字段首次生效；
- **Jenkins 邮件/成功提示里的报告链接**同样走 `COS_CDN_DOMAIN` 变量（Jenkinsfile 未配置时显示兜底
  域名）——`.env` 配置后需同步在 Jenkins 全局环境变量更新该值；
- **报告双通道**（Day20）：COS 外链 + Jenkins 插件兜底，外链建立后主通道就是自定义域名。
