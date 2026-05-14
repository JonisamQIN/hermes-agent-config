---
name: memory-setup
description: Hermes Agent Mem0记忆系统配置指南 — 确保所有技能自动接入记忆库，避免重复踩坑
category: productivity
triggers:
  - 安装新技能时验证Mem0接入
  - 新增Cron Job需要读写记忆时
  - 发现记忆库访问问题时排查
  - 每次新增skill后检查记忆集成
---

# Hermes Agent Mem0 记忆系统 — 正确接入规范

## 架构原理（必须理解）

```
Hermes Agent 内置 memory 工具
         ↓
    mem0_conclude / mem0_search / mem0_profile
         ↓
    通过 config.yaml 中 memory.provider=mem0
         ↓
    调用 Mem0 Cloud API（无需pip安装mem0ai包）
```

**核心原则：永远不要在 skill 的 Python 脚本里 `import mem0ai` 或 `from mem0 import Mem0`。**

Mem0 是 Hermes Agent 的**内置能力**，不是需要单独安装的库。所有 skills 通过 Hermes Agent 提供的 `mem0_conclude`、`mem0_search`、`mem0_profile` 工具与 Mem0 交互——这些工具在所有 skills 加载时**自动可用**，无需任何额外配置。

---

## 两种接入场景

### 场景A：Skill 纯 prompt/SKILL.md（不写Python）

如果 skill 只需要在 prompt 里引用记忆，**无需任何额外操作**。

Agent 的内置工具 `mem0_search` / `mem0_conclude` 直接在 prompt 指令中调用即可：

```
# 在 SKILL.md 的 prompt 指令中直接使用：
→ 查记忆：用 mem0_search（结果作为上下文注入）
→ 存事实：用 mem0_conclude（触发 Hermes 写入选民存储）
```

**示例（SKILL.md 中正确写法）：**
```markdown
每次回答前，先用 mem0_search 搜索用户相关记忆。
如果用户明确纠正了某件事，用 mem0_conclude 存储新事实。
```

这是**推荐方式**——大多数 skills 用这种方式即可。

---

### 场景B：Skill 有 Python 脚本（execute_code / 独立脚本）

如果 skill 包含需要**主动查询记忆并用于决策**的 Python 代码，不能直接 import mem0。需要通过 subprocess 调用 hermes 工具，或者用文件作为中转。

**推荐方案：文件中介模式**

```
Python 脚本
    ↓ 写入查询请求
~/.hermes/memory/pending_query.json
    ↓
在 SKILL.md prompt 中用 mem0_search 查询
    ↓ 写入结果
~/.hermes/memory/pending_result.json
    ↓
Python 脚本读取结果文件
    ↓ 用于后续决策
```

**示例结构：**
```python
# Python 脚本中：写入查询请求
query_request = {
    "action": "search",
    "query": "用户最近的训练计划偏好",
    "output_file": "/root/.hermes/memory/pending_result.json"
}
with open("/root/.hermes/memory/pending_query.json", "w") as f:
    json.dump(query_request, f)
```

然后在 SKILL.md 的 prompt 步骤中：
```
Step 1: 检查 ~/.hermes/memory/pending_query.json
Step 2: 如果有查询请求，执行 mem0_search
Step 3: 将结果写入 pending_result.json
Step 4: Python 脚本读取结果继续执行
```

**绝对禁止：**
```python
# ❌ 绝对不要这样做
from mem0 import Mem0
client = Mem0(...)
results = client.search(...)
```

---

## 新增 Skill 的 Mem0 接入检查清单

每次新增 skill 后，按以下清单检查：

```
□ 1. 这个 skill 的 SKILL.md 是否需要查记忆？
   → 是：用 mem0_search 指令
   → 否：跳过

□ 2. 这个 skill 是否需要主动写入记忆？
   → 是：用 mem0_conclude 指令

□ 3. 这个 skill 是否包含 Python 脚本？
   → 是：确保脚本不 import mem0ai，改用文件中介模式

□ 4. 如果 skill 面向 WeChat Bot：
   → 需要在飞书 Bot 和微信 Bot 两侧都可用
   → 飞书配置完 → 立即检查微信 Bot 是否同步
```

---

## 已知限制

| 限制 | 说明 | 解决方案 |
|------|------|---------|
| Mem0 Search API 需有效 key | `mem0ai` Python包未安装不影响工具使用 | 使用内置 `mem0_search` 工具 |
| mem0_search 需 rerank=true | 简单查询可能返回空结果 | 设置 `rerank=true` 提高精度 |
| 记忆同步有时间差 | 写入后不能立即查到 | 依赖 Hermes 内置 flush 机制 |

---

## 文件路径

```
~/.hermes/handoff/          # 跨Bot转交通道
~/.hermes/memory/           # 记忆查询中转目录（需创建）
~/.hermes/fitness_data/     # 健身数据主库
~/.hermes/skills/           # 所有技能目录
```

---

## 快速参考：内置记忆工具

| 工具 | 用途 | 在 SKILL.md 中写法 |
|------|------|-------------------|
| `mem0_search` | 按语义查询记忆 | `→ mem0_search(query="用户偏好")` |
| `mem0_conclude` | 存储新事实 | `→ mem0_conclude(conclusion="用户喜欢XX")` |
| `mem0_profile` | 获取用户全量记忆 | `→ mem0_profile()` |

所有工具**自动注入到 Agent 上下文**，skill 无需声明或导入。

---

## 规范制定日期
2026-05-14

## 历史踩坑记录

**2026-05-14：** 直接在 Python 中 `import mem0ai` 报错 `ModuleNotFoundError: No module named 'mem0'`。原因是 Mem0 是通过 Hermes Agent 的 memory provider 接入的，不是一个可独立导入的 Python 包。解决方案：使用内置 `mem0_*` 工具，或通过文件中介模式。