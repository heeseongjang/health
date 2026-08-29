#!/usr/bin/env python3
"""template.html + workout.json -> index.html"""
import json

data = json.load(open("workout.json"))
blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
html = open("template.html").read().replace("__DATA__", blob)
open("index.html", "w").write(html)
print(f"index.html ({len(html):,} bytes, 기록 {len(data)}일치)")
