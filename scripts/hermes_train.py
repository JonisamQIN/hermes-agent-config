"""
训记（Xunji）训练数据读取模块
API: POST https://trains.xunjiapp.cn/api_trains_for_llm
缓存目录: ~/.hermes/train_cache/

用法示例:
    from hermes_train import fetch_trains, get_trains

    # 查单日（自动缓存）
    data = fetch_trains("2026-05-06")

    # 强制刷新
    data = fetch_trains("2026-05-06", force_refresh=True)

    # 获取最近7天全部记录
    records = get_trains(days=7)
"""

import json
import gzip
import os
from datetime import date, timedelta
import urllib.request
import urllib.error

BASE_URL = "https://trains.xunjiapp.cn/api_trains_for_llm"
APIKEY = "xjllm_c2079c8a6d0b6ec141effbf894b6ed99b143bb557729fcac"
CACHE_DIR = os.path.expanduser("~/.hermes/train_cache")


def get_cache_path(datestr: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{datestr}.json.gz")


def load_from_cache(datestr: str):
    path = get_cache_path(datestr)
    if os.path.exists(path):
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                return json.load(f), path
        except Exception:
            pass
    return None, path


def save_to_cache(data, cache_path: str):
    with gzip.open(cache_path, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_trains(datestr: str, use_cache: bool = True, force_refresh: bool = False) -> dict:
    """
    获取训记训练数据，自动缓存到 ~/.hermes/train_cache/

    参数:
        datestr: str, 格式 YYYY-MM-DD
        use_cache: bool, 优先读缓存（默认True）
        force_refresh: bool, 强制跳过缓存重新请求（默认False）

    返回:
        dict, API原始响应（包含 res 数组）
    """
    cache_path = get_cache_path(datestr)

    if not force_refresh and use_cache:
        data, _ = load_from_cache(datestr)
        if data is not None:
            return data

    payload = json.dumps({"datestr": datestr}).encode('utf-8')
    req = urllib.request.Request(
        BASE_URL, data=payload,
        headers={
            "Authorization": f"Bearer {APIKEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            try:
                data = json.loads(gzip.decompress(raw).decode('utf-8'))
            except Exception:
                data = json.loads(raw.decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        raise Exception(f"HTTP {e.code}: {body}")

    save_to_cache(data, cache_path)
    return data


def get_trains(datestr: str = None, days: int = 7, force_refresh: bool = False) -> list:
    """
    便捷封装：获取指定日期或最近N天全部训练记录

    参数:
        datestr: str, 格式 YYYY-MM-DD；为None时返回最近days天
        days: int, 向前查询天数（默认7）
        force_refresh: bool, 是否跳过缓存强制刷新

    返回:
        list of dict, 每条记录含 _datestr, id, train_time, items 等字段
    """
    if datestr:
        result = fetch_trains(datestr, force_refresh=force_refresh)
        res = result.get("res", [])
        for item in res:
            item["_datestr"] = datestr
        return res

    today = date.today()
    all_records = []
    for i in range(days):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        result = fetch_trains(d, force_refresh=force_refresh)
        res = result.get("res", [])
        for item in res:
            item["_datestr"] = d
        all_records.extend(res)
    return all_records
