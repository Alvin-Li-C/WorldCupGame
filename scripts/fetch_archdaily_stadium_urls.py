#!/usr/bin/env python3
"""One-off: list image URLs from ArchDaily.cn WC 2026 stadium article."""
import re
import urllib.request

URL = 'https://www.archdaily.cn/cn/993991/2026nian-fifashi-jie-bei-zai-mei-guo-zai-mo-xi-ge-zai-jia-na-da'
html = urllib.request.urlopen(URL, timeout=60).read().decode('utf-8', 'ignore')
urls = re.findall(r'https://images\.adsttc\.com/media/images/[^"\']+', html)
for u in sorted(set(urls)):
    print(u)
