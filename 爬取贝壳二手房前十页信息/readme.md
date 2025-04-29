# 导入库的解读
```python
import csv # 1.导入列名2.写入列表嵌套字典result
import random # 这个是为了随机时间的
import time # 这个是为了停顿随机时间的
from pathlib import Path # 这个是为了输出导出的csv文件的，本质上是创建了路径这一个实例
import traceback # 这是我第一次出bug调试用的
import requests # 获取html源码
from bs4 import BeautifulSoup #解析html源码
```

# 配置区域
**HEADERS**: 请求头
**REQUEST_KW**：字典，解包传入request，只是为了表达上的清晰才分开处理
**FIELDS**：这是准备传入csv的字段
**DELAY_RANGE**: 这是一个元组,准备被解包作为位置参数传入

# 工具函数
## 前一部分
```python
def sleep_random():
    """随机等待，避免高频请求"""
    time.sleep(random.uniform(*DELAY_RANGE)) # *DELAY_RANGE被解包作为位置参数传入
# uniform是对*DELAY_RANGE这个范围随机生成一个浮点数

def get_soup(url: str) -> BeautifulSoup:
    """请求页面并返回 BeautifulSoup 对象"""
    resp = requests.get(url, **REQUEST_KW)
    resp.raise_for_status() # 如果异常会报错，程序终止
    return BeautifulSoup(resp.text, "lxml") # 使用lxml是因为它比html.parser要快，缺点是要手动pip库

def parse_list_page(soup: BeautifulSoup) -> list[str]:
    """从列表页提取房源详情链接（去重）"""
    """
        fromkeys是根据一个可迭代对象创建一个新字典，并统一设置所有 key 对应的 value,如果不设置value参数(, value = 一个你想要的值),默认是None,这里是去掉重复的链接，并且保持原列表序。
        list是再把键名转回列表
    """
    links = []
    for a in soup.select("div.clear a.maidian-detail"):
        href = a.get("href")
        if href:
            links.append(href if href.startswith("http") else "https:" + href)
    return list(dict.fromkeys(links))  # 去重并保持顺序

```
你好
## 后一部分
```python
def extract_base_info(soup: BeautifulSoup) -> dict[str, str]:
    """解析详情页中“房源基本信息”与“概述”两张表格"""
    data: dict[str, str] = {k: "" for k in FIELDS}

    # 顶部价格
    total_price = soup.select_one("span.total") # 根据源码拿到
    if total_price:
        data["房屋总价"] = total_price.get_text(strip=True) + "万"
    unit_price = soup.select_one("span.unitPriceValue") # 根据源码拿到
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
        if len(links) >= 2: # 这个地区据我观察是成对出现的。就算没有也能安全写入csv
            data["所在区域"] = links[0].get_text(strip=True) + links[1].get_text(strip=True)


    # 详情表格 key-value
    for section in soup.select("div.base, div.transaction"):
        for li in section.select("li"):
            # li.stripped_strings 会把 <span> 标签里的文字和后面的文字都拆出来
            parts = list(li.stripped_strings)
            if len(parts) >= 2:
                key, value = parts[0], "".join(parts[1:])  # 把后面几段粘回去，如果有补充信息也不怕报错，很安全
                if key in data:
                    data[key] = value

    return data
```
# 主流程就是拿取想要的数据
#### OUT_FILE.resolve()的意思是返回解析的csv的绝对路径
#### 在项目根目录下运行 python spider.py就能完成贝壳二手房前十页信息的爬取