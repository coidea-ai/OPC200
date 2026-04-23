# 网关配置流程

网关配置与验证阶段，基于 `Configure-Gateway`。

## 5.1 停止旧网关

- 执行 `gateway stop`
- 等 5 秒
- 端口 Listen 门：18789 没人 Listen → 直接认定已停止
- 否则用 `Test-GatewayRpcOk` 再探一次
  - 仍在运行 → 再 `gateway stop` + 再等 5 秒

## 5.2 写入 config

- `gateway.mode = local`
- `gateway.tls.enabled = false`

## 5.3 端口查杀

- 检测 18789 是否被占用
- 被占用 → 尝试 `openclaw gateway stop`、停计划任务、`Stop-Process` 杀 Listen 进程（最多 4 轮）
- 释放失败仅打 `[WARN]`，不阻塞

## 5.4 gateway install

- `gateway install --force --port 18789`
- 失败则再试不带 `--force`
- 两次都失败仅打 `[WARN]`

## 5.4.a 首轮启动探测（3 分钟墙钟）

每轮：端口 Listen 门 → RPC 探测（`--require-rpc --timeout 5000`，单次最多 15s）→ HTTP 探测（6 URL × 5s）→ sleep 5s

- 探测通过 → **直接结束整个第 5 步**

## 5.4.b 端口占用分流

- 端口**未被占用** → gateway 根本没起 → `gateway start`（fire-and-forget）→ sleep 6s → 进入 5.5
- 端口**被占用**（疑似启动中）→ 再探测 2 分钟墙钟
  - 通过 → **直接结束整个第 5 步**
  - 超时 → `Kill-PortOccupier` 强制释放端口 → `gateway restart` → sleep 6s → 进入 5.5

## 5.5 探测 RPC/HTTP（8 分钟墙钟）

- 通过 → 第 5 步完成
- 未通过 → 进入 5.6

## 5.6 doctor 自修复

- `openclaw doctor --non-interactive`（默认最长 30 分钟，可设 `OPENCLAW_INSTALLER_SKIP_DOCTOR=1` 跳过）

## 5.7 重新安装网关

- `Stop-GatewayAndConfirm`（同 5.1）
- `Kill-PortOccupier`（同 5.3）
- `Install-GatewayWithFallback`（同 5.4）

## 5.8 再次探测 RPC/HTTP（8 分钟墙钟）

- 通过 → 第 5 步完成
- 仍失败 → `Fail` 整个脚本退出

---

## 关键硬边界

- **单次 RPC 探测** ≤ 15s（`Invoke-OpenClawWithRedirect -MaxWaitSec 15` + `--timeout 5000`）
- **单次 HTTP 探测** ≤ 30s（6 个 URL × 5s）
- **每轮墙钟检查** 在循环开头，超时直接 `return $false`
- **端口 Listen 前置门**
  - `Wait-GatewayRpcReady`：端口没人 Listen 就跳过本轮探测，避免 RPC/HTTP 假通过
  - `Stop-GatewayAndConfirm`：端口没人 Listen 就直接认定已停止，不再做 RPC 二次确认
