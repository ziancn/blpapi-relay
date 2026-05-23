"""
This module houses method to obtain data from non-API online sources.
"""

import asyncio
import httpx
import re
import html

from bs4 import BeautifulSoup


async def extract_pre_tag_text(url: str) -> str:
    print(f"Getting {url}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        html_content = resp.text

    soup = BeautifulSoup(html_content, "html.parser")
    pre = soup.find("pre")

    if pre:
        return pre.get_text()
    else:
        raise ValueError(f"No <pre> tag found for {url}")


def parse_hkex_ss_pre_text(text: str) -> list[dict[str, any]]:
    # === Part One: Table ===
    pattern = re.compile(
        r"^\s*(?P<prefix>%?)\s*(?P<code>\d+)\s+"
        r"(?P<name>.*?)\s{2,}"
        r"(?P<shares>[\d,]+)\s+"
        r"(?P<value>[\d,]+)\s*$"
    )

    records = []
    for line in text.splitlines():
        if line.startswith("Total No. of all Securities"):
            break

        m = pattern.match(line.rstrip())
        if not m:
            continue

        records.append({
            "code": m.group("code"),
            "name": html.unescape(m.group("name").strip()),
            "shares": int(m.group("shares").replace(",", "")),
            "value": int(m.group("value").replace(",", "")),
            "non_hkd": m.group("prefix") == "%"
        })
    
    return records


async def get_hkex_ss_turnover():
    urls = {
        "mb_eoam": "https://www.hkex.com.hk/eng/stat/smstat/ssturnover/ncms/mshtmain.htm",
        "mb_eod": "https://www.hkex.com.hk/eng/stat/smstat/ssturnover/ncms/ashtmain.htm",
        "gem_eoam": "https://www.hkex.com.hk/eng/stat/smstat/ssturnover/ncms/mshtgem.htm",
        "gem_eod": "https://www.hkex.com.hk/eng/stat/smstat/ssturnover/ncms/ashtgem.htm",
    }
    
    # === Get all data from HKEX websites ===
    tasks = [extract_pre_tag_text(url) for url in urls.values()]
    texts = await asyncio.gather(*tasks, return_exceptions=True)

    # === Parse data ===
    result = {}
    for key, text in zip(urls.keys(), texts):
        result[key] = parse_hkex_ss_pre_text(text)

    return result



if __name__ == "__main__":
    test = asyncio.run(get_hkex_ss_turnover())
    print(test)