---
name: guest-mode
description: 访客权限模式 — 检测用户tier并执行功能限制；owner跳过所有限制，guest/tier受限功能拦截
category: productivity
triggers:
  - 每次飞书消息进来时优先执行权限检测
  - 主用户发送权限提升指令时调用
  - 新增用户时调用
---

# Guest Mode — 权限分级与访客限制

## 核心概念

所有飞书用户按 `~/.hermes/permissions.json` 中的 `tier` 划分权限：

| Tier | 标识 | 可用功能 |
|------|------|---------|
| `owner` | 主人 | 全部功能，无任何限制 |
| `family` | 家人 | 生活服务/健身/饮食/影视搜索，无系统配置权限 |
| `guest` | 访客 | 仅：影视搜索(pansou) + 信息查询(tavily/multi-search) + 简单问答 |

## 文件路径

```
~/.hermes/permissions.json   # 权限配置（主用户修改）
~/.hermes/skills/guest-mode/ # 本skill目录
```

---

## 流程一：每次消息进来时（优先级：最高）

### Step 1：提取 sender open_id

从飞书消息事件中提取 `sender.open_id`（格式：`ou_xxx`）。

### Step 2：查权限配置

读取 `~/.hermes/permissions.json`，根据 `open_id` 查到对应 `tier`。

### Step 3：权限判断

```
tier == "owner"  → 直接放行，不做任何拦截，继续正常处理
tier == "family" → 功能限制：无系统配置权限，但生活服务全开
tier == "guest"  → 功能限制：仅允许以下功能，其余全部拦截
```

### Step 4：Guest 拦截规则

**允许的功能（直接放行）：**
- `pansou-search` skill → 影视/网盘资源搜索
- `tavily` / `multi-search-engine` skill → 简单信息查询
- 闲聊/日常问答（不限内容）
- 时间和日期查询

**拦截的功能（直接回复「仅限主用户使用」）：**
- 任何涉及「配置」「修改」「设置」「调试」的内容
- 任何涉及「技能」「skill」「Cron」「自动化」的询问
- 任何涉及「健身计划」「饮食建议」「身体数据」的内容
- 任何涉及「memory」「记忆」「Mem0」的查询
- 任何涉及「另一个用户」或「权限」的询问
- 调用 `delegate_task` / `execute_code` / 任何系统工具
- 任何看起来像在刺探系统架构的问题

**拦截回复示例：**
```
「抱歉，这个功能仅限主用户使用哦～」

「这个我暂时没法帮你处理，需要主用户的权限～」

「这个功能目前还没有开放给你的账号呢 😊」
```

---

## 流程二：权限提升指令（主用户触发）

**触发条件：** 主用户（owner）在飞书发送以下格式指令：
```
权限提升 {open_id} {tier}
```

**示例：**
- `权限提升 ou_63807fd414ce72ca3d49e4aabce8ac9c owner` → 将测试账号升级为owner
- `权限提升 ou_63807fd414ce72ca3d49e4aabce8ac9c family` → 设为family

### 执行步骤

1. 解析指令，提取 `open_id` 和 `tier`
2. 验证发送者是 owner（`ou_e6bf39d71fc508e4997184a7a1eed13d`）
3. 验证目标 `tier` 是合法值（owner/family/guest）
4. 读取 `permissions.json`，更新对应用户的 `tier`
5. 回复：「已将 {用户名} 权限提升为 {tier} ✅」

### 特殊处理

如果 `tier` 为 `owner`，输出额外提示：
```
「注意：{用户名} 现已升级为owner，拥有全部权限，包括系统配置。」
```

---

## 流程三：添加新用户

**触发条件：** 检测到新的飞书 `open_id`（不在 permissions.json 中）首次发消息。

### 执行步骤

1. 在 `permissions.json` 的 `users` 中新增条目
2. `tier` 默认设为 `guest`
3. `name` 设为 `新用户-{open_id前8位}`
4. `added_at` 设为当前日期
5. 输出：「检测到新用户，已将其设为访客权限。如需调整，请使用权限提升指令。」

---

## 安全规则

1. **权限文件不可删除** — 即使误操作也要保留审计追踪
2. **tier只降不升需要验证** — 降级操作也需要是owner触发
3. **所有权限变更记录到日志** — 包含时间戳、操作者、目标用户、变更前后tier
4. **guest拦截是硬拦截** — 不存在「临时开放」机制，一律直接回复限制提示

---

## 当前权限配置

| open_id | tier | 状态 |
|---------|------|------|
| ou_e6bf39d71fc508e4997184a7a1eed13d | owner | 主用户 |
| ou_63807fd414ce72ca3d49e4aabce8ac9c | guest | 测试账号（待升级owner） |

---

## 快速参考（每次执行时检查）

```
消息进来 → 查 permissions.json → tier=owner? → 直接处理
                                       tier=family? → 仅拦截系统配置
                                       tier=guest? → 仅允许影视搜索/信息查询
```

---

## 规范制定日期
2026-05-14