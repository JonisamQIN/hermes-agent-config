# hermes-agent-config

> Hermes Agent 配置备份仓库 — skills索引 / 脚本 / cron配置 / 健身数据模板

## 📦 仓库内容

```
hermes-agent-config/
├── README.md              # 本文件
├── .gitignore            # 排除敏感文件
├── skills_index.md       # 93个Skills完整索引
├── awesome-resources.md  # GitHub Hermes生态资源汇总
├── scripts/              # 自定义脚本
│   ├── hermes_news.py    # 早安资讯脚本
│   ├── hermes_train.py   # 训练记录脚本
│   ├── pansou_search.py  # 盘搜网盘搜索
│   ├── pansou_tool.py   # 盘搜工具
│   └── weixin_ocr.py    # 微信图片OCR
├── cron/
│   └── jobs.json         # Cron任务配置
├── config/
│   └── mcp_servers.yaml  # MCP服务器配置（已脱敏）
└── fitness/
    ├── fitness_log.json  # 健身数据模板
    └── record_entry.py   # 记录录入脚本
```

## 🔢 本地Skills统计

- **总计**: 93个skills
- **分类**: apple, autonomous-ai-agents, creative, data-science, devops, email, fitness-tracker, gaming, github, hermes, leisure, mcp, media, mlops, note-taking, productivity, red-teaming, research, smart-home, social-media, software-development

## 🧩 MCP服务器配置

已安装的MCP服务器（见 `config/mcp_servers.yaml`）：
- Tavily Search (AI优化搜索)
- 盘搜网盘搜索 (pansou)
- 剪映视频生成 (jianying-video-gen)
- YouTube Watcher
- Yuanbao groups

## ⭐ 相关Hermes资源

详见 [awesome-resources.md](./awesome-resources.md)，包含：
- 官方资源 (NousResearch/hermes-agent)
- Web UI工具 (hermes-workspace, mission-control)
- Skills生态 (wondelai/skills 380+, agentskills.io)
- 插件 (hermes-plugins, hermes-spotify-skill)
- 部署方案 (Docker, Nix, Portainer)
- Skill发现平台 (hermeshub, skilldock.io)

## 🚀 快速恢复

```bash
# 克隆仓库
git clone https://github.com/JonisamQIN/hermes-agent-config.git

# 恢复scripts到 ~/.hermes/scripts/
cp scripts/* ~/.hermes/scripts/

# 恢复cron配置
cp cron/jobs.json ~/.hermes/cron/jobs.json

# 查看MCP配置
cat config/mcp_servers.yaml
```

## 📊 健身数据

`fitness/fitness_log.json` 包含健身记录模板字段：
- `date`, `gym`, `routine`, `exercises`
- `sets`, `reps`, `weight_kg`, `volume_kg`
- `hrv`, `sleep_hours`, `subjective_energy`

## 🔒 安全说明

`.gitignore` 已排除所有敏感文件：
- `.env` (API密钥)
- `auth.json` (认证文件)
- `*.db` (数据库)
- `cache/`, `logs/`, `sessions/` (运行时数据)

**如有API密钥变更，请手动更新相应配置文件。**

---

*Last updated: 2026-05-14*
