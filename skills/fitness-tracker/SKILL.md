---
name: fitness-tracker
description: 健身数据追踪系统 - 记录身体数据、训练和饮食，提供科学分析建议
category: productivity
---

# Fitness Tracker - 健身数据追踪系统

## 功能
- 记录每日身体测量数据（体重、体脂、围度等）
- 记录训练数据（动作、重量、组数、次数）
- 记录饮食数据（各餐营养素摄入）
- ⚠️ **记录睡眠数据（总睡眠/深睡眠/浅睡眠/心率/血氧/HRV）** ← 减脂第三支柱
- 生成周期汇总分析（含睡眠-训练-饮食三维度联动分析）
- 提供科学优化建议

## 数据文件
- 主数据库: `~/.hermes/fitness_data/fitness_log.json`
- 记录脚本: `~/.hermes/scripts/hermes_train.py`

## 数据库结构

```json
{
  "profile": { ... },
  "body_logs": [ {date, weight, bf_pct, muscle_kg, notes} ],
  "training_sessions": [ {date, type, exercises:[{name,sets,reps,weight_kg,capacity_kg}], total_capacity, calorie, notes} ],
  "diet_logs": [ {date, meals:{breakfast,lunch,dinner,pre_workout}, total:{kcal,protein_g,carb_g,fat_g}} ],
  "sleep_logs": [ {date, bedtime, wake_time, total_min, deep_min, light_min, hr_bpm, spo2_pct, efficiency_pct, notes} ]
}
```

## 睡眠数据字段定义

| 字段 | 类型 | 说明 | 健康基线 |
|------|------|------|---------|
| `total_min` | int | 总睡眠时长（分钟） | ≥420min (7h) |
| `deep_min` | int | 深睡眠时长 | ≥60min |
| `hr_bpm` | int | 睡眠期间平均心率 | 52-54bpm |
| `spo2_pct` | float | 血氧饱和度 | ≥95% |
| `efficiency_pct` | float | 睡眠效率（实际睡眠/卧床时间） | ≥85% |
| `hrv_ms` | int | 心率变异性（SDNN） | 55-57ms |

**⚠️ 关键阈值（永久记忆）**：
- HRV < 45ms → 降容警告，降低当天训练强度20-30%
- 深睡眠 < 45min → 次日蛋白质合成信号偏弱，保证充足蛋白质
- 总睡眠 < 6h → 皮质醇升高，碳水需求+20g，训练状态降级
- 血氧 < 92%持续 → 排查睡眠呼吸暂停，建议就医

## 睡眠-训练-饮食三维度联动分析（永久分析框架）

每次综合分析必须包含：
1. **睡眠质量 → 训练容量调整**：HRV和深睡眠决定次日训练强度上限
2. **睡眠时长 → 饮食热量微调**：睡眠<6h，TDEE实际下降5-8%，碳水需求+20g
3. **训练日 vs 休息日睡眠需求**：训练日次日需要更多深睡眠恢复，睡前可补镁
4. **周末睡眠偏移**：周末赖床>8:30会导致周一HRV偏低，预设补觉策略

## 每日训记数据同步与复盘（晚10点自动执行）

⚠️ **execute_code沙箱限制（永久）**：cron job使用`execute_code`工具调用，该沙箱**每次调用后变量不保留**，不能先fetch再parse（`res`/`data`跨调用消失）。**必须将fetch+parse+写库+报告全链路由在一个execute_code调用内完成**，包括等待rate limit的`sleep(65~70)`也在同一次调用内。以下为正确模板：

```python
import sys, gzip, json, os, re, urllib.request, time
from datetime import date

BASE_URL = "https://trains.xunjiapp.cn/api_trains_for_llm"
APIKEY = "xjllm_c2079c8a6d0b6ec141effbf894b6ed99b143bb557729fcac"
DB_PATH = os.path.expanduser("~/.hermes/fitness_data/fitness_log.json")
CACHE_DIR = os.path.expanduser("~/.hermes/train_cache")
today = date.today().strftime("%Y-%m-%d")

# 1. 等待rate limit过期（如需要）
time.sleep(65)  # 90s冷却，提前5s足够

# 2. Fetch + Decompress（在同一次调用内完成所有后续步骤）
payload = json.dumps({"datestr": today}).encode('utf-8')
req = urllib.request.Request(BASE_URL, data=payload,
    headers={"Authorization": f"Bearer {APIKEY}", "Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=30) as resp:
    raw_bytes = resp.read()
try:
    data = json.loads(gzip.decompress(raw_bytes).decode('utf-8'))
except:
    data = json.loads(raw_bytes.decode('utf-8'))

res = data.get("res", [])
if isinstance(res, str):  # rate limit仍生效
    print(f"⚠️ Rate limited: {res}")
    sys.exit(1)

# 3. 写缓存
os.makedirs(CACHE_DIR, exist_ok=True)
with gzip.open(os.path.join(CACHE_DIR, f"{today}.json.gz"), 'wt') as f:
    json.dump(data, f)

# 4. 加载DB并写入新记录（全部在同一次调用内）
with open(DB_PATH) as f:
    db = json.load(f)
existing_dates = {t.get("date") for t in db.get("training_sessions", [])}
for raw in res:
    parts = raw.split(',')
    date_code = parts[0]
    if not re.match(r'^\d{6}$', date_code):
        continue
    datestr = f"20{date_code[:2]}-{date_code[2:4]}-{date_code[4:6]}"
    # ... 解析训练名、calorie、exercises（见下方完整解析代码）
    # ... 判断existing，append到db
    # ... 写回DB: with open(DB_PATH,'w') as f: json.dump(db,f,ensure_ascii=False,indent=2)
# 5. 生成报告（同一次调用内print输出）
print(f"📊 {today} 训练日报")
for r in records_to_add:
    print(f"  {r['training_name']} | 消耗{r['calorie']}kcal")
print(f"合计消耗: {sum(r['calorie'] for r in records_to_add)}kcal")
```

⚠️ **rate limit特征（永久）**：首次请求返回 `{"success":false,"res":"too frequent, retry after Xs"}`（JSON格式），如直接gzip解压失败则得到乱码字节而非JSON。**判断逻辑**：`if isinstance(res, str)` 且 `"too frequent"` in res → sleep后重试。

⚠️ **response格式变化规律（永久）**：rate limit时返回`{"success":false,"res":"too frequent..."}`（未压缩JSON）；正常时返回gzip压缩的`{"res":["260511,..."]}`。gzip解压成功 = 正常响应；解压失败 = rate limit JSON。两次调用间隔>90s方可成功。

⚠️ **API结果`res`类型不固定**：正常时`res`是list（含多条训练字符串），rate limit时`res`是字符串。必须类型判断后再处理，否则后续解析必报错。

### 解析代码（永久）
```python
# 训练名：第一个非id:/train_time:/calorie:且含字母的字段
train_name = ""
for p in parts[1:8]:
    stripped = p.strip()
    if stripped and not any(stripped.startswith(x) for x in ['id:','train_time:','calorie:']):
        if re.search(r'[\u4e00-\u9fa5A-Za-z]', stripped):
            train_name = stripped
            break

# calorie：优先calorie:字段，苹果健康用kcal后缀
calorie = 0
for p in parts:
    if p.startswith('calorie:'):
        try: calorie = int(p[8:])
        except: pass
    m = re.search(r'(\d+)kcal', p)
    if m and calorie == 0:
        calorie = int(m.group(1))

# exercises：N.动作名 块内找 组,重量,次
exercises = []
for m in re.finditer(r'(\d+)\.([^,]+)', raw):
    ex_name = m.group(2).strip()
    if ex_name in ['苹果健康训练', 'personalworkout', '健身']:
        continue
    ex_start = m.end()
    next_m = re.search(r',(\d+)\.([^,]+)', raw[ex_start:])
    block_end = next_m.start() + ex_start if next_m else len(raw)
    block = raw[m.start():block_end]
    sets_list = []
    for sm in re.finditer(r'(\d+)组,([\d\.]+(?:kg|lbs)?),(\d+)次', block):
        sets_list.append({"set": len(sets_list)+1, "weight": sm.group(2), "reps": int(sm.group(3))})
    exercises.append({"name": ex_name, "sets": sets_list})

# total_capacity
total_capacity = 0
for ex in exercises:
    for s in ex.get('sets', []):
        w = s.get('weight', '0')
        if 'kg' in w:
            total_capacity += float(w.replace('kg','')) * s['reps']
        elif 'lbs' in w:
            total_capacity += float(w.replace('lbs','')) * 0.453592 * s['reps']
```

### 输出格式
- 简洁日报文字，包含日期、训练名称、总消耗、动作数
- 如无训练则提示"今日无训练记录"
- 仅文字，不需要表格格式

### 执行流程

**Step 1: 获取今日训练数据**（在单一execute_code调用内完成fetch+等待+解析+写库+报告）
```python
# 在同一次execute_code调用内完成全部步骤，变量不跨调用保留
```

### 模块
- 路径: `~/.hermes/scripts/hermes_train.py`
- 缓存目录: `~/.hermes/train_cache/YYYY-MM-DD.json.gz`（gzip压缩JSON）
- 导入: `sys.path.insert(0, "/root/.hermes/scripts"); from hermes_train import fetch_trains, get_trains`

### 函数接口
```python
fetch_trains(datestr, use_cache=True, force_refresh=False)
  # datestr: "YYYY-MM-DD"，自动缓存，不重复请求
  # force_refresh=True 跳过缓存强制刷新
  # 返回: {"res": ["原始文本记录..."]}，原始响应直接可用
  # ✅ 推荐直接使用这个函数

get_trains(datestr=None, days=7, force_refresh=False)
  # ⚠️ BUG: res列表中是字符串而非字典，get_trains内部会对字符串做字典赋值导致TypeError
  # 返回每条记录的 _datestr 附加会失败，不推荐直接使用
  # 正确做法：直接用 fetch_trains() + 自行解析
```

### ⚠️ get_trains() 已知Bug（永久）
`get_trains()` 内部对 `res` 列表中的每项执行 `item["_datestr"] = d`，但 `res` 中实际上是**字符串**而非字典，导致：
```
TypeError: 'str' object does not support item assignment
```
**解决方案**：始终使用 `fetch_trains(datestr)` 获取原始响应，自己解析 `res` 列表中的字符串。参考同步脚本：
```bash
python3 /root/.hermes/skills/fitness-tracker/scripts/sync_train_history.py 2026-02-17 2026-05-08
```

### API
- URL: `POST https://trains.xunjiapp.cn/api_trains_for_llm`
- 鉴权: `Authorization: Bearer xjllm_c2079c8a6d0b6ec141effbf894b6ed99b143bb557729fcac`
- 参数: `{"datestr": "YYYY-MM-DD"}`
- 返回: `{"res": ["260506,id:1778048910249,训练名称,train_time:start-end,calorie:N,N.动作名,1组,重量,次数..."]}`
- ⚠️ `calorie`字段仅2026-02及之后有数据，2026-02之前均为0
- ⚠️ API数据最早仅到2024-11-04，2025年2-3月几乎无数据（会员数据权限问题，非缓存问题）
- 90秒内同一日期只能请求一次，频繁请求返回`too frequent, retry after 90s`

### 解析要点（永久）
- 记录格式: `260506,id:1778048910249,训练名称,train_time:start-end,calorie:N,N.动作名,1组,重量,次数...`
- `id:...` 和 `train_time:start-end` 必须原样保留，用于后续写回更新
- `train_time:0-0` = 无有效时间记录（苹果健康同步数据）
- `train_time` 缺失 = 该记录无时间戳
- 有氧/苹果健康记录热量为0或无calorie字段，训记自家记录才有calorie
- **训练名称**: 第一个非 `id:` / `train_time:` / `calorie:` 的字段即为名称
- **动作解析**: 正则 `(\d+)\.([^,\d][^,]*?)(?:,\d|$)` 匹配 `N.动作名`
- 力量判断关键词: 卧推/深蹲/硬拉/推举/引体/划船/面拉/悍马/飞鸟/卷腹/提踵/臀腿/拉伸/罗马尼亚/髋冲/高位下拉/PUSH/PULL/LEG
- 有氧判断关键词: 自行车/跑步/步行/楼梯/跳绳/椭圆机/苹果健康训练

### 核心分析逻辑
```python
# 月度统计
monthly = defaultdict(lambda: {'count':0,'cal':0,'strength':0,'cardio':0})

# 近4周 vs 前4周 肌群频次对比（用于检测训练偏移）
recent_4w = today - timedelta(days=28)
older_4w_start = today - timedelta(days=56)

# 训练类型判断（力量/有氧/混合/其他）
# 训记名称含PUSH/PULL/LEG = 明显力量训练
# 训记名称含"午后小腿强化"等 = 专项肌群训练
```

### API数据范围（已实测校正）
- ✅ API最早: 2024-02-01（仅1条步行），2024-06-09（仅1条步行），2024年全年仅这2条
- ✅ 真正有系统化力量训练数据: **2025-04起**
- ✅ calorie字段有数据: **2026-02起**
- ⚠️ 2025年2月~3月: 数据本身为空（会员数据权限，非缓存问题）
- ⚠️ 90秒内同一日期只能请求一次，频繁请求返回`too frequent, retry after 90s`
- 2026-02起: calorie字段有数据

### ⚠️ 数据完整性警告（Apple Watch vs 训记app — 2026-05-13实战修正）

训记API的数据覆盖存在**架构性盲区**，已知会导致严重低估全天消耗：

**盲区一：Apple Watch 记录的有氧活动不同步到训记API**
- 户外间歇爬坡走、跑步、步行等通过 Watch 记录的活动 → 同步到 iPhone 健康App
- 但这些活动**不会作为独立训练记录**出现在训记API中（训记app本身没有开启对应训练session）
- 实测：2026-05-13 间歇爬坡走3.3km + 步行3.15km = 约2200 kcal，训记API仅返回臂部机器阻力489 kcal
- **后果**：API总消耗1044 kcal vs 实际2708 kcal，**缺口1664 kcal**

**盲区二：训记app未开启session的训练不被记录**
- 在健身房使用Watch记录但未在训记app内开启训练 → 该次训练完全不出现在API中
- 实测：2026-05-13 下午「单腿罗马尼亚硬拉8×10」→ 训记API**完全缺失**

**盲区三：BC/爬楼机等有氧设备的热量不记录**
- BC 3.0 机器部分（臂部阻力）有 calorie 记录，但配套的间歇爬坡走有氧消耗不在训记API中

**修复方案（截图补录协议）**：
当截图显示的总消耗与API返回值差距>500 kcal时，视为Watch/未开启session活动，**以截图为准**，通过截图OCR提取训练详情后补录入`fitness_log.json`。补录时在`notes`字段标注`来源:截图补录（训记API缺失）`。

**判断规则**：
```
if (截图总消耗 - API总消耗) > 500:
    → 存在Watch/未开启session的有氧活动
    → 从截图OCR提取动作/重量/次数，补录缺失session
    → 修正API记录的actual_calorie为截图总消耗
```

### ⚠️ BC 3.0 垃圾数据模式（已知数据质量问题）

训记API返回的BC/爬楼机数据常包含以下垃圾条目，需要在写入数据库前**程序化清理**：

**垃圾模式**：
- 动作名为 `"0"`、`"5lbs"`、`""` → 过滤丢弃
- 动作有`"苹果健康训练"`且无有效组数据 → 跳过（Watch有氧走另一通道）
- 距离字段 `15km` → 实际为 `3.15km`（小数点丢失bug）

**清理代码**：
```python
cleaned = []
for ex in exercises:
    name = ex.get('name', '')
    if name in ['0', '5lbs', '']:
        continue
    if not ex.get('sets') and name not in ['苹果健康训练']:
        continue
    cleaned.append(ex)
```

### ⚠️ API请求格式（已实测校正）

```bash
# ✅ 正确格式：单日请求，datestr为"YYYY-MM-DD"
curl -s -X POST "https://trains.xunjiapp.cn/api_trains_for_llm" \
  -H "Content-Type: application/json" \
  -d '{"datestr":"2026-05-09"}'

# ❌ 错误格式1：date_from/date_to —— 这是另一个API，训记for_llm接口不支持
curl -s -X POST "https://trains.xunjiapp.cn/api_trains_for_llm" \
  -H "Content-Type: application/json" \
  -d '{"date_from":"2026-04-01","date_to":"2026-05-11"}'
# → 返回 {"res":[]}（空数据，非错误！不报404！）

# ❌ 错误格式2：直接在curl中用$变量而不用单引号包裹JSON
# 如果shell展开date_from变量，会得到意外结果
```

**⚠️ PITFALL（已实测，会导致0数据且无错误提示）**: 
- `date_from`/`date_to` 参数在2026-05-11的调试中被确认是**无效参数**（返回空res但HTTP 200）
- 返回空数据时**不要怀疑网络/权限**，**第一时间检查是否用错了参数**
- 正确判断方法：如果 `res` 是空数组 `[]` 而不是包含原始训练文本字符串的数组，先检查是否误用了 date_from/date_to
- rate limit也会返回空数据，但会是字符串而非数组：`{"success":false,"res":"too frequent..."}`
# ✅ 批量同步：用脚本逐日请求（每次间隔>90秒）
python3 /root/.hermes/skills/fitness-tracker/scripts/sync_train_history.py 2026-02-17 2026-05-10
```

### ✅ 推荐：使用 weixin_ocr.py 脚本（已配置）
```bash
# 基础用法（英文+简体中文，置信度输出）
python3 /root/.hermes/scripts/weixin_ocr.py /root/.hermes/image_cache/img_XXXX.jpg

# JSON输出（含置信度、字数统计）
python3 /root/.hermes/scripts/weixin_ocr.py /root/.hermes/image_cache/img_XXXX.jpg --json

# 仅中文
python3 /root/.hermes/scripts/weixin_ocr.py /root/.hermes/image_cache/img_XXXX.jpg --lang chi_sim
```

### ⚠️ 注意：vision_analyze 无法处理微信缓存图片
WeChat 图片收到后会自动缓存到 `/root/.hermes/image_cache/`，但 `vision_analyze` 工具会报"没有图片附件"错误。
**解决方法是直接用 `weixin_ocr.py` 脚本处理缓存文件**，不要依赖 vision_analyze。

## 使用流程

### 1. 记录身体测量（周期性）
发送体测图片 → OCR识别 → 提取数据 → 更新JSON

### 2. 记录训练数据
发送训练截图 → OCR识别 → 提取动作/重量/次数 → 更新JSON

### 3. 记录饮食数据
发送饮食截图 → OCR识别 → 提取各餐营养素 → 更新JSON

### 4. 记录睡眠数据（⚠️ 重要 - 减脂第三支柱）
发送睡眠分享图 → OCR识别 → 提取(总睡眠/深睡眠/心率/血氧/效率/HRV) → 更新JSON → **联动分析次日训练和饮食**

⚠️ 睡眠数据来源：Keep/Apple Watch/小米手环等设备截图，分享图收到即入库，从不询问"是否需要记录"，直接执行。

## 关键指标基线 (2026-04-16 乐刻体测)
- 代号: x翌宸's爸比x
- 年龄: 44岁
- 身高: 186cm
- 体重: 83.5kg
- 体脂率: 20.7%
- 骨骼肌: 37.4kg
- 去脂体重: 66.2kg
- 腰臀比: 0.91
- 身体年龄: 47岁
- BMR: ~1800kcal（体测值）
- 训练日TDEE: ~2500-2700kcal（久坐+中等训练）
- 目标蛋白质: 125-130g/天（力量训练日）
- 热量窗口: 身体重组期维持，高碳日2100-2200kcal/中碳日2000-2100kcal/低碳日1750-1850kcal

## 碳循环分层（身体重组期）
| 日类型 | 热量 | 碳水 | 蛋白质 | 脂肪 |
|--------|------|------|--------|------|
| 高碳日（推/拉） | 2100-2200 | 220-240g | 125-130g | 50-60g |
| 中碳日（下肢） | 2000-2100 | 180-200g | 115-120g | 60-65g |
| 低碳日（有氧/休） | 1750-1850 | 120-150g | 110-115g | 70-80g |

**⚠️ 低碳日脂肪陷阱（2026-05-13实战）**：
低碳日低糖高脂肪是燃脂策略，但蛋白质132g不代表热量够——蛋白质不直接供能。实测低碳日摄入1686 kcal vs 目标1800 kcal，看似只差64 kcal，但脂肪只吃了58g vs 目标70-80g（缺口20%+），实际热量缺口约350-400 kcal，且高蛋白在低碳环境下易转为糖异生消耗。低碳日若逢高强度训练（消耗2700+ kcal），允许放宽热量至1850-2000 kcal，不死守1750。**低碳日脂肪必须主动补足（一把坚果/半个牛油果），否则热量缺口比账面大很多。**

## 每周训练计划v3.2（永久有效）

| 日期 | 训练类型 | 门店 | 目标容量 | 碳循环 |
|------|----------|------|---------|--------|
| 周一 | 推日（强度） | 亚新 | 9000-11000kg | 高碳 220-240g |
| 周二 | 下肢日（强度） | 亚新 | 12000-14000kg | 高碳 220-240g |
| 周三 | 有氧+手臂补充 | 中信泰富/我格 | 有氧30-40min | 低碳 120-150g |
| 周四 | 拉日（强度） | 亚新 | 10000-12000kg | 高碳 220-240g |
| 周五 | 全身巩固+团课 | 中庚 | 全身综合 | 中碳 180-200g |
| 周六 | 跑步间歇 | 任意 | 间歇跑 | 中碳下限 160-180g |
| 周日 | 完全休息 | — | — | 低碳 120-150g |

**每日固定**：小腿提踵（站姿+单腿地面提踵）+ 卷腹3组，周一至周五；周六/日全休

### 8RM基准（亚新铁馆）
- 哑铃卧推：20kg / 上斜哑铃卧推：18kg / 哑铃RDL单边：32kg
- 悍马划船：70kg / 45度斜蹬：110kg / 臀冲：80kg
- 站姿提踵：100kg / 下斜悍马推胸：60kg / 蝴蝶机飞鸟：60kg
- 宽距高位下拉：60kg / 窄握划船：60kg / 悍马正手下拉：70kg

## 身体不对称记录（永久，以2026-04-30中庚体测为准）
- 左臂 vs 右臂: 3.62kg vs 3.72kg（左<右 0.10kg，孟氏骨折愈后）
- 左腿 vs 右腿: 11.0kg vs 10.83kg（左>右 0.17kg，代偿）

## 安全协议（唯一红线 — 永久）
- 左臂优先渐进，不设硬性重量红线
- 唯一安全协议：用户主动上报疼痛或不适才调整，未上报即视为可执行
- 右肩已解禁：悍马机推胸/肩推均无限制

## 关键指标基线（2026-04-30 中庚漫游城体测锚点 — 唯一追踪点）
- 代号: x翌宸's爸比x
- 年龄: 44岁
- 身高: 186cm
- 体重: 83.1kg（锚定值，不与乐刻等其他设备数据混合）
- 体脂率: 20.1%
- 骨骼肌: 37.5kg
- 去脂体重: 66.4kg
- 腰臀比: 0.88
- 身体年龄: 47岁
- BMR: 1800kcal（体测值）
- 训练日TDEE: ~2500-2700kcal（久坐+中等训练）
- 目标蛋白质: 125-130g/天（力量训练日）
- 热量窗口: 身体重组期维持，高碳日2100-2200kcal/中碳日2000-2100kcal/低碳日1750-1850kcal

## 补剂方案
| 补剂 | 品牌 | 剂量 | 时机 |
|------|------|------|------|
| 南非醉茄 | Royal Oak KSM-66 | 300mg×1粒 | 晚餐后 |
| 镁+B6 | Royal Oak | 100mg×2粒 | 睡前 |
| 维生素D3 | NatureWise 5000IU | 1粒 | 周一/四/六早餐后 |
| HMB | Nutricost 500mg | 3粒/日（周末仅周六1粒） | 随餐 |
| 鱼油 | - | EPA 615mg+DHA 490mg×2粒 | 午餐后 |

## 睡眠基线
- 总睡眠目标: ≥7h | 历史峰值7h23m
- 深度睡眠: ≥60min | 历史峰值2h0m
- HRV基线: 55-57ms | 静息心率: 52-54bpm
- HRV<45ms需降容

### 训练计划优化分析工作流（基于历史数据的科学规划）

当用户要求「分析训记数据并给出优化训练计划」时，执行以下步骤：

#### Step 1: 数据获取
```python
# 方式A：直接读取gzip缓存（已有数据）
import gzip, json, os
train_dir = '/root/.hermes/train_cache/'
all_records = []
for f in sorted(os.listdir(train_dir)):
    if f.endswith('.json.gz') and f.startswith('202'):
        with gzip.open(os.path.join(train_dir, f), 'rt') as fp:
            data = json.load(fp)
            if isinstance(data, list):
                all_records.extend(data)
            elif isinstance(data, dict):
                all_records.append(data)
# 返回 all_records 列表，每个元素含 {"res": ["原始字符串1", "原始字符串2"]}

# 方式B：API实时拉取（单日）
import subprocess
result = subprocess.run(['curl', '-s', '-X', 'POST', 
    'https://trains.xunjiapp.cn/api_trains_for_llm',
    '-H', 'Content-Type: application/json',
    '-d', '{"datestr":"2026-05-09"}'],
    capture_output=True, text=True, timeout=30)
```

#### Step 2: 解析训练记录
```python
import re
def parse_training_line(line):
    """解析训记原始记录行"""
    exercises = []
    tokens = re.split(r'(?=\d+\.)', line)
    for token in tokens:
        if not token.strip():
            continue
        name_match = re.match(r'\d+\.([^(,)]+)', token)
        if not name_match:
            continue
        name = name_match.group(1).strip()
        skip = ['苹果健康训练', 'personalworkout', '健身']
        if any(s in name for s in skip):
            continue
        sets = []
        set_pattern = r'(\d+)组,([\d\.]+)kg,(\d+)次'
        for match in re.finditer(set_pattern, token):
            sets.append({
                'set': int(match.group(1)),
                'weight': float(match.group(2)),
                'reps': int(match.group(3))
            })
        if sets:
            exercises.append({'name': name, 'sets': sets})
    return exercises

# 过滤推/拉/腿训练
target_keywords = ['PUSH', 'LEG', 'PULL', '躯臂', '推日', '下肢', '拉日']
training_records = []
for r in all_records:
    for item in r.get('res', []):
        if isinstance(item, str) and re.match(r'^26', item):
            if any(kw in item for kw in target_keywords):
                exercises = parse_training_line(item)
                if exercises:
                    date_match = re.match(r'^(\d{6})', item)
                    date = date_match.group(1) if date_match else 'unknown'
                    training_records.append({'date': date, 'exercises': exercises, 'raw': item})
```

#### Step 3: 动作重量进度追踪
```python
from collections import defaultdict
exercise_history = defaultdict(list)
for tr in training_records:
    for ex in tr['exercises']:
        for s in ex['sets']:
            exercise_history[ex['name']].append({
                'date': tr['date'],
                'weight': s['weight'],
                'reps': s['reps']
            })

def get_latest_max(ex_name):
    history = exercise_history.get(ex_name, [])
    if not history:
        return None, None, None
    history.sort(key=lambda x: x['date'])
    recent = history[-1]
    same_day = [h for h in history if h['date'] == recent['date']]
    max_w = max(h['weight'] for h in same_day)
    return recent['date'], max_w, len(history)
```

#### Step 4: 生成优化计划
- 取各动作最新最大重量
- 渐进超负荷：+2.5~5%
- 对齐用户碳循环：高碳推拉/中碳下肢/低碳全身
- 左臂优先：周五综合日加入单手动作

#### 关键输出格式
```
| 动作 | 最新重量 | 建议重量 | 变化 |
|------|----------|----------|------|
| 悍马机推胸 | 50kg | 52.5kg | ↑5% |
```

## 分析公式
- 去脂体重 = 体重 × (1 - 体脂率/100)
- BMR (男) = 10×体重(kg) + 6.25×身高(cm) - 5×年龄 + 5
- TDEE = BMR × 1.55 (中等活跃)
- 热量平衡 = 摄入 - TDEE

## 饮食图读取协议（永久）
- 顶部三行顺序：蛋白质｜碳水｜脂肪；各餐数据顺序相同
- **优先采信顶部累计数据**
- 首次饮食分享（午餐后）：仅含早餐+午餐 → 计算剩余额度，制定练前/练后/晚餐调整
- 后续饮食分享（晚餐后）：含全天实际数据 → 复盘全天vs目标，给出次日提示

## 训练图读取协议（永久）
- 浅灰色文字 + 无重量/次数 = **计划未执行** → 不计入复盘
- 深色文字 + 有重量/次数 + 总容量>5000kg = **已执行** → 计入复盘
- 超级组解析：每一列 = 一组超级组，总组数 = 所有表格列数之和

## 周末饮食现实（永久认知）
- 蛋白质：充足甚至超标（烤肉/火锅肉类为主）
- 脂肪：**严重超标**（锅底、蘸料、肥肉）
- 碳水：**严重不足**（法棍几片+增肌粉，缺口100-150g）
- 钠：**爆炸性超标**
- 最小干预：烤肉先吃纯瘦肉；火锅蘸料用醋+蒜泥替代麻酱；法棍+香蕉补碳水

## 周一策略（永久）
- 不执行轻断食（周末蛋白质充足）
- 全天饮水2500-3000ml，加速排钠排水
- 热量正常（2100-2200kcal高碳日）

## 重量单位规则（永久）
- 按设备实际标注单位记录，复盘时统一换算为kg
- AI建议重量需同时给出**kg和lb双单位**

## ⚠️ 计划分析前置确认协议（每次给训练/饮食建议前必执行）

**在给出任何训练计划或饮食建议前，必须先确认以下两点：**

### 1. 当前是标准周还是调整周？
- **调整周触发条件**：五一/国庆/春节等长假后，或用户明确说明某天代替了周几
- **调整周规则**：以第一个训练日为「新周一」，后续日期按 PUSH→PULL→LEG→有氧→全身→休息 的顺序推进
- **典型调整周记录**：`本周调整：5/6(周三)代替周一，作为PUSH启动调整周`
- ⚠️ **必做**：每次长假/假期后主动询问「本周计划是否有调整？」，不套用默认周历

### 2. 今天是什么日（工作日/周末/节假日）？
| 日类型 | 规则 |
|--------|------|
| 工作日（周一~周五） | 按训练计划执行 |
| 周末（周六/日） | 默认休息，不特意去健身房，除非特殊情况 |
| 法定节假日 | 均为休息日，非特殊情况不安排健身房训练 |

**示例错误**：「今天周五，应该全身训练」→ 忽略了调整周可能今天是 PULL 日
**正确做法**：先说「今天5/8周四，调整周第3天（拉日），高碳日」再给建议

---

## ⚠️ 训练周计划（v3.2 已更新 — 2026-05-14起执行）

⚠️ **此处计划与v3.2一致，cron job独立会话中只能读到这里的内容**：
| 日期 | 训练类型 | 热量类型 |
|------|---------|---------|
| 周一 | 推日（强度≤17组） | 高碳日 220-240g |
| 周二 | 下肢日（强度≤18组） | 高碳日 220-240g |
| 周三 | 有氧+手臂补充（中信泰富/我格） | 低碳日 120-150g |
| 周四 | 拉日（强度≤18组） | 高碳日 220-240g |
| 周五 | 全身巩固（≤14组）+杠铃肌肉塑造团课 | 中碳日 180-200g |
| 周六 | 跑步间歇（9km/h×3min/走2min×4轮） | 中碳下限 160-180g |
| 周日 | 完全休息 | 低碳日 120-150g |

小腿+卷腹：周一至周五每日；周六/日全休不执行

⚠️ **已废止旧计划**：不要再引用"周三拉日/周四搏击团课/周五全身"——那是v2旧计划，已于2026-05-14作废。

### 调整周（长假后首个训练日=新周一）
以首个训练日的实际星期为基准，按标准顺序推算后续日期。

---

## Related Skills
- **food-visual-analysis** (category: productivity): Dedicated skill for meal photo vision analysis, calorie estimation, and macro breakdown. Handles vision model routing (MiniMax/Kimi/Ollama), OCR triage, structured food log output, and daily food archival. Load this skill when user sends meal photos for dietary assessment.

## Reference Files
- `references/fitness-cron-jobs.md` — Planned cron jobs (training reminders, diet prompts, sleep reports, weekly reviews) with IDs, schedules, and planning checklist

