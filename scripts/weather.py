import os
import requests
from datetime import datetime
import pytz

# 1. 获取北京时间
tz = pytz.timezone('Asia/Shanghai')
today = datetime.now(tz)
date_str = today.strftime('%Y-%m-%d')
time_str = today.strftime('%H:%M:%S')

# 2. 抓取天气 (用 wttr.in 这个对程序员友好的服务，换成你要的城市拼音)
city = "Beijing" 
# format=3 表示只抓取简单的一行天气信息
url = f"https://wttr.in/{city}?format=3"

try:
    response = requests.get(url)
    weather_info = response.text.strip()
except Exception as e:
    weather_info = "天气数据抓取失败，手动看看吧！"

# 3. 生成 Hugo 文章内容
file_content = f"""---
title: "📅 {date_str} 每日天气播报"
date: {today.isoformat()}
draft: false
tags: ["自动播报", "天气"]
---

## 🤖 机器人自动播报

**北京时间**：{date_str} {time_str}

**今日天气**：
> {weather_info}

*(本文章由 GitHub Actions 自动抓取并发布)*
"""

# 4. 写入文件到 content/posts 目录
# 也就是上一级目录的 content/posts
file_name = f"weather-{date_str}.md"
file_path = os.path.join("content", "posts", file_name)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(file_content)

print(f"成功生成文章：{file_path}")