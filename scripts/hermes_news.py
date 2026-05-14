#!/usr/bin/env python3
"""
每日早安资讯脚本
获取天气 + 新闻 + 影视资讯，输出格式化日报
"""

import json
import subprocess
import sys
from datetime import datetime

TMDB_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI4Y2Y1MmM0NWZmNWJjZDNkNTg3Yjk5YTU5MWI2M2FiOSIsIm5iZiI6MTY2MTA2ODI4NC40MTkwMDAxLCJzdWIiOiI2MzAxZTNmYzk2ZTMwYjAwOTExZmRiZWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.rp5q1bUoxhfwnAtJy3ntLM2RaYY6wjgHgxWF1CYoOJA"
PROXY = "socks5://127.0.0.1:20170"

def get_weather():
    """获取上海天气"""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", "10", "wttr.in/Shanghai?format=j1"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        current = data["current_condition"][0]
        weather_desc = current["weatherDesc"][0]["value"]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        windspeed = current["windspeedKmph"]
        visibility = current["visibility"]
        
        # 逐时预报（取3个整点）
        hourly = []
        hours_seen = set()
        for h in data["weather"][0]["hourly"]:
            hour = int(h["time"]) // 100  # 000 → 0, 300 → 3, 600 → 6
            if hour in hours_seen:
                continue
            hours_seen.add(hour)
            desc = h["weatherDesc"][0]["value"]
            t = h["tempC"]
            rain = h["chanceofrain"]
            hourly.append(f"{hour:02d}:00 → {desc}/{t}°C/雨量{rain}%")
            if len(hourly) >= 3:
                break
        
        # 对比昨天
        yesterday = data["weather"][1]["mintempC"]
        today_min = data["weather"][0]["mintempC"]
        diff = int(temp) - int(yesterday)
        comparison = f"比昨天{'凉' if diff < 0 else '热'}了{abs(diff)}度"
        
        # 贴心提示
        if "雨" in weather_desc or int(rain) > 50:
            tip = "出门带伞，防滑防湿！"
        elif int(feels) < 10:
            tip = "降温明显，注意保暖添衣。"
        elif int(temp) > 30:
            tip = "高温天气，注意防暑降温。"
        else:
            tip = "天气宜人，适合户外活动。"
        
        return {
            "desc": weather_desc,
            "temp": temp,
            "feels": feels,
            "humidity": humidity,
            "windspeed": windspeed,
            "visibility": visibility,
            "hourly": hourly,
            "comparison": comparison,
            "tip": tip
        }
    except Exception as e:
        return None

def get_tmdb_movies():
    """获取TMDB趋势电影"""
    try:
        result = subprocess.run(
            [
                "curl", "-sL", "--max-time", "15",
                "-x", PROXY,
                "https://api.themoviedb.org/3/trending/movie/day?language=zh-CN",
                "-H", f"Authorization: Bearer {TMDB_TOKEN}"
            ],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return [], []
        data = json.loads(result.stdout)
        movies = []
        for m in data.get("results", [])[:5]:
            movies.append({
                "title": m.get("title", ""),
                "rating": m.get("vote_average", 0),
                "date": m.get("release_date", ""),
                "overview": m.get("overview", "")[:80]
            })
        
        # 剧集
        result2 = subprocess.run(
            [
                "curl", "-sL", "--max-time", "15",
                "-x", PROXY,
                "https://api.themoviedb.org/3/trending/tv/day?language=zh-CN",
                "-H", f"Authorization: Bearer {TMDB_TOKEN}"
            ],
            capture_output=True, text=True, timeout=20
        )
        tvs = []
        if result2.returncode == 0:
            data2 = json.loads(result2.stdout)
            for t in data2.get("results", [])[:3]:
                tvs.append({
                    "title": t.get("name", ""),
                    "rating": t.get("vote_average", 0),
                    "date": t.get("first_air_date", ""),
                    "overview": t.get("overview", "")[:80]
                })
        return movies, tvs
    except Exception as e:
        return [], []

def get_news():
    """搜索当日新闻"""
    try:
        from hermes_tools import web_search
        results = web_search(
            query="今日重大新闻 2026年5月 中国",
            limit=5
        )
        news = []
        if results and "data" in results:
            for item in results["data"].get("web", [])[:5]:
                title = item.get("title", "")
                desc = item.get("description", "")
                if title and desc and "error" not in title.lower():
                    news.append(f"• {title}：{desc[:60]}")
        return news
    except Exception as e:
        return []

def format_date():
    """格式化日期"""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return now.strftime(f"%m月%d日 {weekdays[now.weekday()]}")

def main():
    weather = get_weather()
    movies, tvs = get_tmdb_movies()
    
    lines = []
    lines.append(f"📅 {format_date()}\n")
    
    # 天气
    if weather:
        lines.append("🌤️ 今日天气")
        lines.append(f"  当前：{weather['desc']} {weather['temp']}°C（体感{weather['feels']}°C）")
        lines.append(f"  湿度{weather['humidity']}% | 风速{weather['windspeed']}km/h | 能见度{weather['visibility']}km")
        lines.append(f"  逐时：{' | '.join(weather['hourly'][:3])}")
        lines.append(f"  {weather['comparison']}，{weather['tip']}")
    else:
        lines.append("🌤️ 天气数据获取失败，跳过。")
    
    lines.append("")
    
    # 资讯早茶 - 新闻
    lines.append("📰 资讯早茶")
    news = get_news()
    if news:
        for n in news[:4]:
            lines.append(f"  {n}")
    else:
        lines.append("  暂无资讯。")
    
    lines.append("")
    
    # 文娱快报
    lines.append("🎬 文娱快报")
    if movies:
        lines.append("  【电影趋势】")
        for i, m in enumerate(movies[:3], 1):
            year = m["date"][:4] if m["date"] else ""
            lines.append(f"  {i}.《{m['title']}》{m['rating']:.1f}分 {year}")
            if m["overview"]:
                lines.append(f"     {m['overview']}...")
    
    if tvs:
        lines.append("  【剧集趋势】")
        for i, t in enumerate(tvs[:2], 1):
            year = t["date"][:4] if t["date"] else ""
            lines.append(f"  {i}.《{t['title']}》{t['rating']:.1f}分 {year}")
            if t["overview"]:
                lines.append(f"     {t['overview']}...")
    
    lines.append("")
    lines.append("祝你今天心情愉快！☀️")
    
    print("\n".join(lines))

if __name__ == "__main__":
    main()
