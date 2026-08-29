#!/usr/bin/env python3
"""수업일지 시트 -> workout.json

Google 스프레드시트(수업일지 탭)는 18행 주기로 세션 블록이 반복되고,
한 행에 좌(A~R) / 우(T~AK) 두 개의 세션이 들어간다.
"""
import json, os, re, sys, urllib.request
import openpyxl

# 시트 주소는 저장소에 두지 않는다: 환경변수 SHEET_ID 또는 로컬 .sheet-id 파일에서 읽는다.
def sheet_id():
    v = os.environ.get("SHEET_ID", "").strip()
    if not v and os.path.exists(".sheet-id"):
        v = open(".sheet-id").read().strip()
    if not v:
        sys.exit("SHEET_ID가 없습니다. 환경변수로 넘기거나 .sheet-id 파일에 적어주세요.")
    return v

TAB = "수업일지"
WD = ["월", "화", "수", "목", "금", "토", "일"]

BLOCK_STRIDE = 18
BLOCK_STARTS = range(2, 111, BLOCK_STRIDE)   # 2, 20, 38, ... 110
COL_OFFSETS = (0, 19)                        # 좌/우 블록


def norm(s):
    """운동명 비교용 정규화: 공백/괄호/기호 제거"""
    return re.sub(r"[\s()\[\]/·.\-]", "", str(s or "")).lower()


def cell(ws, row, col):
    v = ws.cell(row=row, column=col).value
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f == int(f) else f


def parse_comments(text):
    """'운동명\n-포인트\n-포인트\n\n운동명\n...' -> [{name, points}]"""
    if not text:
        return []
    out = []
    for chunk in re.split(r"\n\s*\n", text.strip()):
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if not lines:
            continue
        out.append({
            "name": lines[0].lstrip("-·• ").strip(),
            "points": [l.lstrip("-·• ").strip() for l in lines[1:]],
        })
    return out


def parse_session(ws, top, off):
    c = lambda r, col: cell(ws, r, col + off)

    date = c(top, 2)
    if date is None:
        return None

    if hasattr(date, "strftime"):
        iso = date.strftime("%Y-%m-%d")
        weekday = WD[date.weekday()]
        label = f"{date.month}월 {date.day}일"
    else:  # 날짜가 텍스트로 들어온 경우
        iso, weekday, label = None, None, str(date)

    comments = parse_comments(c(top + 2, 15))
    by_name = {norm(x["name"]): x["points"] for x in comments}
    used = set()

    exercises = []
    for r in range(top + 10, top + 16):
        name = c(r, 1)
        if not name:
            continue
        sets = []
        for s in range(5):
            w = num(c(r, 4 + s * 2))
            reps = num(c(r, 5 + s * 2))
            if w is None and reps is None:
                continue
            sets.append({"weight": w, "reps": reps})
        key = norm(name)
        used.add(key)
        exercises.append({
            "name": name,
            "sets": sets,
            "volume": num(c(r, 14)) or 0,
            "points": by_name.get(key, []),
        })

    # 세트 기록 없이 코멘트만 있는 운동도 살려둔다
    for x in comments:
        if norm(x["name"]) not in used:
            exercises.append({"name": x["name"], "sets": [], "volume": 0, "points": x["points"]})

    return {
        "date": iso,
        "dateLabel": label,
        "weekday": weekday,
        "time": c(top, 4),
        "part": c(top + 1, 2),
        "condition": c(top + 1, 4),
        "note": c(top, 8),
        "feedback": c(top + 3, 2),
        "totalVolume": num(c(top + 16, 14)) or 0,
        "exercises": exercises,
    }


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "wb.xlsx"
    if not sys.argv[1:]:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id()}/export?format=xlsx"
        urllib.request.urlretrieve(url, path)

    ws = openpyxl.load_workbook(path, data_only=True)[TAB]
    sessions = [s for top in BLOCK_STARTS for off in COL_OFFSETS
                if (s := parse_session(ws, top, off))]
    sessions.sort(key=lambda s: s["date"] or "")

    json.dump(sessions, open("workout.json", "w"), ensure_ascii=False, indent=2)
    print(f"{len(sessions)}개 세션 → workout.json")
    for s in sessions:
        print(f"  {s['date']}({s['weekday']}) {s['part']} · 운동 {len(s['exercises'])}개 · 볼륨 {s['totalVolume']}")


if __name__ == "__main__":
    main()
