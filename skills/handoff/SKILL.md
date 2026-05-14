---
name: handoff
description: 跨Bot转交技能 — WeChat Bot检测到转交指令时执行上下文写入；Feishu Bot启动时检测并读取转交内容
category: productivity
triggers:
  - WeChat Bot检测到"转交专业助理"等指令时调用
  - Feishu Bot收到消息时优先检查pending状态
---

# Handoff — 跨Bot转交通道

## 触发条件

**在 WeChat Bot 中，当用户说出以下任意指令时，立即调用本技能：**
- 转交专业助理 / 转给专业助理 / 交给飞书
- 请专业助理处理 / 升级到专业助理
- 这个问题让飞书处理 / 转交

**在 Feishu Bot 中，每次收到消息时优先执行本技能的自检逻辑。**

---

## WeChat Bot 执行步骤（当检测到转交指令）

### Step 1：立即停止当前对话处理
不要回答用户的原问题，不要继续任何其他操作。直接进入转交流程。

### Step 2：写入 pending.json
使用 `write_file` 工具，将以下内容写入 `/root/.hermes/handoff/pending.json`：

```json
{
  "pending": true,
  "source_channel": "weixin",
  "created_at": "2026-05-14TXX:XX:XX+08:00（当前时间）",
  "user_id": "o9cq80yxQit9lAwgEWuPNi4I2CR8@im.wechat",
  "conversation_summary": "【一句话描述用户遇到了什么问题】",
  "issue_description": "【用户的具体问题或需求描述】",
  "raw_context": "【最后2-3轮对话原文，用于精确还原】",
  "status": "pending"
}
```

**注意：** `conversation_summary` 和 `issue_description` 从当前对话上下文中提取。如果上下文不足（例如用户只说了"转交专业助理"），则 `summary` = "用户触发转交，未提供具体问题描述"，`issue_description` = "需在飞书进一步询问"。

### Step 3：输出确认消息
直接回复以下内容，不要添加其他文字：

```
✅ 已收到你的转交请求。

你描述的问题是：
【从对话中提取的问题摘要】

已转交给专业助理（Feishu Bot）处理。请切换到飞书继续，我会接力完成后续工作。
```

---

## Feishu Bot 执行步骤（当检测到 pending.json 存在）

### Step 1：读取 pending.json
使用 `read_file` 工具读取 `/root/.hermes/handoff/pending.json`。

### Step 2：判断是否需要处理
```
if pending == true AND status == "pending":
    → 进入转交接收流程
else:
    → 不做任何转交通知，正常处理用户消息
```

### Step 3：输出转交通知并更新状态
先读取文件内容，然后使用 `write_file` 将 status 改为 "delivered"，再输出通知：

**通知内容：**
```
📥 检测到来自 WeChat Bot 的转交请求

你遇到的问题是：
【conversation_summary 中的内容】

我来接管后续处理。请详细描述一下具体遇到了什么情况？
```

**更新 pending.json（立即执行）：**
将 `status` 字段从 `"pending"` 改为 `"delivered"`，保留其他所有字段不变。

---

## 文件路径

```
~/.hermes/handoff/pending.json
```

## 状态说明

| status | 含义 |
|--------|------|
| `pending` | WeChat Bot 已写入，等待 Feishu Bot 读取 |
| `delivered` | Feishu Bot 已读取并处理完毕 |
| `none` | 无转交请求 |

## 重要约束

- Feishu Bot 只在 status == "pending" 时提示一次
- 修改 status 为 "delivered" 后，当前会话不再重复提示
- pending.json 不删除（保留审计记录），只改 status