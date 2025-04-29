"""
贝壳成都二手房信息采集脚本
--------------------------------------
• 目标：抓取 https://cd.ke.com/ershoufang/ 前 10 页房源详情页，
  并输出包含以下字段的 CSV 文件（UTF‑8‑SIG）：

    房屋总价、房屋单价、小区名称、所在区域、房屋户型、户型结构、所在楼层、
    套内面积、房屋朝向、装修情况、配备电梯、建筑面积、建筑类型、楼层高度、
    建筑结构、梯户比例、挂牌时间、上次交易、房屋年限、抵押信息、房源核验码、
    交易权属、房屋用途、产权所属、房本备件

• 使用方法：
    $ pip install requests beautifulsoup4 lxml
    $ python spider.py

• 注意事项：
  1. 贝壳有反爬策略，请保持 1~3 秒随机间隔，必要时自行添加代理 / cookie。
  2. 如响应为 403，可尝试更换 UA、IP 或使用 Selenium + 有头浏览器。
  3. 采集数据仅供学习，请遵守目标站 robots 协议和当地法律法规。
"""

import csv
import random
import time
from pathlib import Path
import traceback

import requests
from bs4 import BeautifulSoup

# ------------------------- 配置区域 -------------------------
BASE_LIST_URL = "https://cd.ke.com/ershoufang/pg{page}/"  # 列表页模板
PAGES = 10                                                 # 抓取页数
OUT_FILE = Path("chengdu_ke_ershoufang.csv")               # 输出文件,

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://cd.ke.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
REQUEST_KW = {
    "headers": HEADERS,
    "timeout": 10,
}
DELAY_RANGE = (1.2, 2.8)  # 每次请求后的随机延时（秒）

# 需要采集的字段（中文即为 CSV 列名）
FIELDS: list[str] = [
    "房屋总价", "房屋单价", "小区名称", "所在区域", "房屋户型", "户型结构", "所在楼层", "套内面积",
    "房屋朝向", "装修情况", "配备电梯", "建筑面积", "建筑类型", "楼层高度", "建筑结构", "梯户比例",
    "挂牌时间", "上次交易", "房屋年限", "抵押信息", "房源核验码", "交易权属", "房屋用途", "产权所属",
    "房本备件",
]

# ------------------------- 工具函数 -------------------------

def sleep_random():
    """随机等待，避免高频请求"""
    time.sleep(random.uniform(*DELAY_RANGE))


def get_soup(url: str) -> BeautifulSoup:
    """请求页面并返回 BeautifulSoup 对象"""
    resp = requests.get(url, **REQUEST_KW)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def parse_list_page(soup: BeautifulSoup) -> list[str]:
    """从列表页提取房源详情链接（去重）"""
    links = []
    for a in soup.select("div.clear a.maidian-detail"):
        href = a.get("href")
        if href:
            links.append(href if href.startswith("http") else "https:" + href)
    return list(dict.fromkeys(links))  # 去重并保持顺序


def extract_base_info(soup: BeautifulSoup) -> dict[str, str]:
    """解析详情页中“房源基本信息”与“概述”两张表格"""
    data: dict[str, str] = {k: "" for k in FIELDS}

    # 顶部价格
    total_price = soup.select_one("span.total")
    if total_price:
        data["房屋总价"] = total_price.get_text(strip=True) + "万"
    unit_price = soup.select_one("span.unitPriceValue")
    if unit_price:
        data["房屋单价"] = unit_price.get_text(strip=True)

    # 小区 
    info_section = soup.select_one("div.aroundInfo")
    if info_section:
        data["小区名称"] = soup.select_one("a.info").get_text(strip=True)
    
    # 区域
    info_section = soup.select_one("div.areaName")
    if info_section:
        # 获取所有的 <a> 标签
        links = info_section.select("a")
        if len(links) >= 2:
            data["所在区域"] = links[0].get_text(strip=True) + links[1].get_text(strip=True)


    # 详情表格 key-value
    for section in soup.select("div.base, div.transaction"):
        for li in section.select("li"):
            # li.stripped_strings 会把 <span> 标签里的文字和后面的文字都拆出来
            parts = list(li.stripped_strings)
            if len(parts) >= 2:
                key, value = parts[0], "".join(parts[1:])  # 把后面几段粘回去
                if key in data:
                    data[key] = value

    return data

# ------------------------- 主流程 -------------------------

def main():
    print(f"开始抓取前 {PAGES} 页数据 …\n")
    results: list[dict[str, str]] = []

    for page in range(1, PAGES + 1):
        list_url = BASE_LIST_URL.format(page=page)
        print(f"[列表] 第 {page} 页 → {list_url}")
        try:
            list_soup = get_soup(list_url)
        except Exception as e:
            print(f"列表页请求失败：{e}")
            continue

        detail_links = parse_list_page(list_soup)
        print(f"  发现 {len(detail_links)} 条房源")
        for idx, link in enumerate(detail_links, 1):
            print(f"    ({idx}/{len(detail_links)}) 详情页 → {link}")
            try:
                detail_soup = get_soup(link)
                data = extract_base_info(detail_soup)
                results.append(data)
            except Exception as e:
                print(f"详情页解析失败：{e}")
                traceback.print_exc()
            sleep_random()
        sleep_random()

    # 写出 CSV
    with OUT_FILE.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n 已写入 {len(results)} 条记录 → {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()

