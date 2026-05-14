#!/usr/bin/env python3
"""
健身数据记录脚本
用法: python record_entry.py --type body|training|diet --date YYYY-MM-DD --data JSON_STRING
"""

import json
import sys
import os
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.hermes/fitness_data/fitness_log.json")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"body_measurements": [], "training_sessions": [], "diet_logs": [], "weekly_summaries": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_body_measurement(data, date, weight=None, bodyfat=None, muscle=None, bmi=None, notes=None):
    entry = {
        "date": date,
        "weight_kg": weight,
        "bodyfat_pct": bodyfat,
        "muscle_kg": muscle,
        "bmi": bmi,
        "notes": notes
    }
    data["body_measurements"].append(entry)
    data["body_measurements"].sort(key=lambda x: x["date"])
    return entry

def add_training_session(data, date, duration_min, total_weight_kg, avg_heart_rate, exercises):
    entry = {
        "date": date,
        "duration_min": duration_min,
        "total_weight_kg": total_weight_kg,
        "avg_heart_rate": avg_heart_rate,
        "exercises": exercises
    }
    data["training_sessions"].append(entry)
    data["training_sessions"].sort(key=lambda x: x["date"])
    return entry

def add_diet_log(data, date, meals):
    entry = {
        "date": date,
        "meals": meals
    }
    data["diet_logs"].append(entry)
    data["diet_logs"].sort(key=lambda x: x["date"])
    return entry

if __name__ == "__main__":
    print("健身数据记录模块已加载")
    print(f"数据文件: {DATA_FILE}")
