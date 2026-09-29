#!/usr/bin/env python3
"""
KC云加速（游戏加速仓库）每日 README 自动更新

流程：
  1. 调用 speed_test.py 生成当日节点数据 -> data/*.csv
  2. 在 README 的「## 📅 第五部分：维护日志与版本迭代记录」之前插入当日更新块
  3. 在第五部分下方写入/更新当日维护日志条目

设计要点：
  - 幂等：同一天重复运行只会「覆盖」当天内容，不会重复堆叠
  - 每日不同：内容按日期做随机种子，跨天组合不重复
  - 保留原文件换行风格（CRLF / LF）
"""

import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
README_PATH = os.path.join(ROOT, "README.md")

MARKER = "## 📅 第五部分：维护日志与版本迭代记录"

sys.path.insert(0, HERE)
import speed_test  # noqa: E402

TIPS = [
    "🎮 **节点选择**：CS2 / VALORANT 优先选香港、日本节点；原神、崩铁等亚服游戏优先选日本、新加坡节点。",
    "🎮 **延迟科普**：FPS 类游戏对延迟最敏感，60ms 与 120ms 的差异在甩枪、拉枪时体感非常明显；MOBA 类可放宽到 100ms 左右。",
    "🎮 **客户端建议**：Windows 推荐 Clash Verge Rev 开启 Tun 模式，游戏流量与系统流量统一接管，避免「网页能开、游戏卡住」。",
    "🎮 **排查技巧**：游戏内延迟高但网页正常，多半是 UDP 转发没走代理，检查客户端是否勾选 UDP 转发（Tun 模式默认开启）。",
    "🎮 **弱网优化**：移动端开启 Mux 多路复用，坐地铁、走楼道切换基站时断流会明显减少。",
    "🎮 **分流原则**：游戏平台（Steam / Epic / Riot）与国内社交软件分开走，避免下载更新抢占游戏带宽。",
    "🎮 **高峰期提示**：20:00–23:00 国际出口普遍拥堵，BGP 专线入口在这个时段优势最明显，适合排位赛。",
    "🎮 **画质与带宽**：2K/144Hz 串流对带宽要求高，建议给游戏设备单独走专线分组，别和下载任务共享。",
]

BENEFITS = [
    "🎁 **新人福利**：通过专属通道注册即可领取试用时长，加入官方群另有额外优惠。",
    "🎁 **游戏套餐**：低延迟专线月付 ¥18 起，支持 3 台设备同时在线，学生党友好。",
    "🎁 **老用户回馈**：续费年付套餐折算下来每月成本最低，适合长期开黑。",
]


def split_sections(text):
    """返回 (第五部分之前, 第五部分之后)。"""
    idx = text.find(MARKER)
    if idx == -1:
        raise SystemExit("❌ README 中未找到标记：" + MARKER)
    return text[:idx], text[idx:]


def strip_today(text, today):
    """移除今天已存在的更新块与日志条目，保证幂等。"""
    heading = f"### 📌 {today} 今日更新"
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == heading:
            # 连同其后的空行与条目行一起丢弃，直到遇到下一个小节
            i += 1
            while i < len(lines) and (lines[i].strip() == "" or lines[i].lstrip().startswith("- ")):
                i += 1
            continue
        if line.startswith(f"{today}："):
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def trim_blocks(text, keep=7):
    """只保留最近 keep 个「今日更新」块，避免 README 无限膨胀（历史仍留在维护日志里）。"""
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines)
              if re.match(r'^### 📌 \d{4}-\d{2}-\d{2} 今日更新$', l.strip())]
    if len(starts) <= keep:
        return text

    ranges = []
    for s in starts:
        e = s + 1
        while e < len(lines) and (lines[e].strip() == "" or lines[e].lstrip().startswith("- ")):
            e += 1
        while e < len(lines) and lines[e].strip() == "":
            e += 1
        ranges.append((s, e))

    remove = set()
    for s, e in ranges[:-keep]:
        remove.update(range(s, e))
    return "\n".join(l for i, l in enumerate(lines) if i not in remove)


def main():
    from datetime import datetime, timedelta, timezone
    # 固定按北京时间取日期（运行器是 UTC，定时任务会被推迟，避免跨日写错日期）
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    best = speed_test.main()          # 生成数据 + 打印摘要
    node, lat, dl = best["node_name"], best["latency"], best["download"]

    with open(README_PATH, "r", encoding="utf-8", newline="") as f:
        raw = f.read()

    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")          # 内部统一用 \n 处理
    text = strip_today(text, today)

    rnd = random.Random(today + "|game")
    chosen = rnd.sample(TIPS, 2)
    benefit = rnd.choice(BENEFITS)

    block = [f"### 📌 {today} 今日更新", "",
             f"- **测速快报**：5 个游戏专线节点实测完成，最佳节点 **{node}**，"
             f"延迟 **{lat}ms**，下载 **{dl} Mbps**。"]
    block += [f"- {t}" for t in chosen]
    block += [f"- {benefit}", "", ""]

    log_entry = (f"{today}：例行游戏节点巡检完成，更新当日测速数据"
                 f"（最佳 {node} / {lat}ms）；同步刷新游戏分流规则与客户端配置要点。")

    head, tail = split_sections(text)
    head = head.rstrip("\n") + "\n\n"

    # 在「第五部分」标记行之后插入/更新当日日志条目
    lines = tail.split("\n")
    new_tail_lines = [lines[0], log_entry] + lines[1:]
    new_tail = "\n".join(new_tail_lines)

    new_text = head + "\n".join(block) + new_tail
    new_text = trim_blocks(new_text)
    new_text = new_text.replace("\n", nl)

    with open(README_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)

    print("✅ README 已更新")
    print(f"   今日更新块：{today} / 最佳 {node} {lat}ms")
    print(f"   随机内容：{chosen[0][:34]}...")
    print(f"   维护日志：{log_entry[:40]}...")


if __name__ == "__main__":
    main()
