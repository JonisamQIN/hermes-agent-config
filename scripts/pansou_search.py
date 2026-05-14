#!/usr/bin/env python3
"""
PanSou 网盘资源搜索脚本
用法:
  python3 pansou_search.py "影视名称" [--include X] [--exclude Y] [--cloud-types A,B] [--limit N]
"""

import json
import sys
import argparse
import urllib.request
import urllib.error


def search_pansou(
    keyword: str,
    include: list[str] = None,
    exclude: list[str] = None,
    cloud_types: list[str] = None,
    limit: int = 5,
    base_url: str = "http://192.168.1.50:9530",
) -> dict:
    """调用 PanSou 搜索 API"""

    payload = {
        "kw": keyword,
        "res": "merge",
    }

    if cloud_types:
        payload["cloud_types"] = cloud_types

    if include or exclude:
        payload["filter"] = {
            "include": include or [],
            "exclude": exclude or [],
        }

    req = urllib.request.Request(
        f"{base_url}/api/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": str(e)}


def format_results(data: dict, limit_per_type: int = 5) -> str:
    """格式化搜索结果为可读文本"""

    if "error" in data:
        return f"❌ 请求失败: {data['error']}"

    if data.get("code") != 0:
        return f"❌ API错误: {data.get('message', 'unknown')}"

    content = data.get("data", {})
    total = content.get("total", 0)
    merged = content.get("merged_by_type", {})

    if not merged:
        return f"🔍 未找到「{data.get('data', {}).get('results', [{}])[0].get('title', '未知')}」的相关资源"

    lines = [f"🔍 共找到 **{total}** 条资源结果\n"]

    type_labels = {
        "aliyun": "�云的阿里云盘",
        "quark": "🔵 夸克网盘",
        "baidu": "🔴 百度网盘",
        "115": "🟣 115网盘",
        "xunlei": "⚡ 迅雷云盘",
        "mobile": "📱 139云",
        "tianyi": "☁️ 天翼云盘",
        "magnet": "🧲 磁力链接",
    }

    for cloud_type, items in merged.items():
        label = type_labels.get(cloud_type, cloud_type)
        if not items:
            continue
        lines.append(f"{label}（共{len(items)}个）:")
        for item in items[:limit_per_type]:
            pwd = item.get("password") or "无"
            note = item.get("note", "（无描述）")
            url = item.get("url", "")
            source = item.get("source", "")
            # 简化来源显示
            if source.startswith("tg:"):
                source = f"📢{source[3:]}"
            elif source.startswith("plugin:"):
                source = f"🔌{source[7:]}"

            lines.append(f"  • {note}")
            lines.append(f"    🔗 {url}")
            if pwd and pwd != "无":
                lines.append(f"    🔑 密码: `{pwd}`")
            lines.append(f"    📡 来源: {source}")
        lines.append("")

    return "\n".join(lines).strip()


def main():
    parser = argparse.ArgumentParser(description="PanSou 网盘资源搜索")
    parser.add_argument("keyword", help="搜索关键词（影视名称）")
    parser.add_argument("--include", default="4K,HDR,蓝光,高码,原盘",
                        help="必须包含的关键词（逗号分隔）")
    parser.add_argument("--exclude", default="预告,抢先,枪版,生肉,字幕组,采样",
                        help="排除的关键词（逗号分隔）")
    parser.add_argument("--cloud-types", default="aliyun,quark,baidu,115,xunlei,tianyi",
                        help="网盘类型（逗号分隔）")
    parser.add_argument("--limit", type=int, default=5, help="每类网盘最多显示条数")
    parser.add_argument("--no-filter", action="store_true", help="禁用过滤，直接返回所有结果")

    args = parser.parse_args()

    include = None if args.no_filter else [x.strip() for x in args.include.split(",") if x.strip()]
    exclude = None if args.no_filter else [x.strip() for x in args.exclude.split(",") if x.strip()]
    cloud_types = [x.strip() for x in args.cloud_types.split(",") if x.strip()]

    print(f"🎬 正在搜索: {args.keyword}", file=sys.stderr)
    if not args.no_filter:
        print(f"   过滤条件: 包含{include} / 排除{exclude}", file=sys.stderr)

    data = search_pansou(
        keyword=args.keyword,
        include=include,
        exclude=exclude,
        cloud_types=cloud_types,
        limit=args.limit,
    )

    result = format_results(data, limit_per_type=args.limit)
    print(result)


if __name__ == "__main__":
    main()
