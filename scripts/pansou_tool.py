#!/usr/bin/env python3
"""
PanSou 网盘资源搜索工具
直接被 Hermes 作为 tool 调用，输出纯文本结果供对话使用
"""

import json
import urllib.request
import urllib.error


def search_pansou(keyword: str, limit_per_type: int = 3) -> str:
    """
    搜索影视网盘资源

    参数:
        keyword: 搜索关键词（影视名称）
        limit_per_type: 每种网盘最多返回条数

    返回:
        格式化后的文本搜索结果
    """
    base_url = "http://192.168.1.50:9530"

    payload = {
        "kw": keyword,
        "res": "merge",
        "filter": {
            "include": ["4K", "HDR", "蓝光", "高码", "原盘"],
            "exclude": ["预告", "抢先", "枪版", "生肉", "字幕组", "采样"]
        }
    }

    req = urllib.request.Request(
        f"{base_url}/api/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return f"❌ 请求失败: {e}"

    if data.get("code") != 0:
        return f"❌ API错误: {data.get('message', 'unknown')}"

    content = data.get("data", {})
    total = content.get("total", 0)
    merged = content.get("merged_by_type", {})

    if not merged:
        return f"🔍 未找到「{keyword}」的相关资源"

    type_labels = {
        "aliyun": "阿里云盘",
        "quark": "夸克网盘",
        "baidu": "百度网盘",
        "115": "115网盘",
        "xunlei": "迅雷云盘",
        "mobile": "139云",
        "tianyi": "天翼云盘",
        "magnet": "磁力链接",
    }

    lines = [f"🔍 **「{keyword}」网盘资源**（共{total}条，过滤后精选高质量版本）\n"]

    for cloud_type, items in merged.items():
        label = type_labels.get(cloud_type, cloud_type)
        if not items:
            continue
        lines.append(f"**【{label}】**（共{len(items)}个）")
        for item in items[:limit_per_type]:
            pwd = item.get("password") or "无"
            note = item.get("note", "（无描述）")
            url = item.get("url", "")
            source = item.get("source", "")
            if source.startswith("tg:"):
                source = f"来源📢{source[3:]}"
            elif source.startswith("plugin:"):
                source = f"来源🔌{source[7:]}"

            lines.append(f"• **{note}**")
            lines.append(f"  🔗 {url}")
            if pwd and pwd != "无":
                lines.append(f"  🔑 密码: `{pwd}`")
            lines.append(f"  📡 {source}")
        lines.append("")

    return "\n".join(lines).strip()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 pansou_tool.py <搜索关键词>")
        sys.exit(1)
    result = search_pansou(sys.argv[1])
    print(result)
