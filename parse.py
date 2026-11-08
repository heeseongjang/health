#!/usr/bin/env python3
"""수업일지 시트 -> workout.json

Google 스프레드시트의 「수업일지」, 「수업일지2」 … 탭은 모두 같은 양식이다.
18행 주기로 세션 블록이 반복되고, 한 행에 좌(A~R) / 우(T~AK) 두 개가 들어간다.
"""
import collections, datetime, json, os, re, sys, urllib.request
import openpyxl

# 시트 주소는 저장소에 두지 않는다: 환경변수 SHEET_ID 또는 로컬 .sheet-id 파일에서 읽는다.
def sheet_id():
    v = os.environ.get("SHEET_ID", "").strip()
    if not v and os.path.exists(".sheet-id"):
        v = open(".sheet-id").read().strip()
    if not v:
        sys.exit("SHEET_ID가 없습니다. 환경변수로 넘기거나 .sheet-id 파일에 적어주세요.")
    return v

TAB_PREFIX = "수업일지"                      # 수업일지, 수업일지2, …
WD = ["월", "화", "수", "목", "금", "토", "일"]

BLOCK_STRIDE = 18
BLOCK_FIRST = 2                              # 첫 블록이 시작하는 행
COL_OFFSETS = (0, 19)                        # 좌/우 블록

DATE_TEXT = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})")


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
        "_raw": date,
        "_where": f"{ws.title}!{top}행{'좌' if off == 0 else '우'}",
        "time": c(top, 4),
        "part": c(top + 1, 2),
        "condition": c(top + 1, 4),
        "note": c(top, 8),
        "feedback": c(top + 3, 2),
        "totalVolume": num(c(top + 16, 14)) or 0,
        "exercises": exercises,
        # 날짜·부위만 적혀 있고 내용이 비면 아직 안 한 수업(예정)으로 본다
        "planned": not exercises,
    }


def resolve_dates(sessions):
    """날짜 셀을 iso/요일/표시용 라벨로 바꾼다.

    '10월 21시'처럼 잘못 적힌 칸은 월·일만 뽑아 쓰고, 연도는 제대로 적힌
    날짜들의 최빈 연도를 빌려온다. 추정한 칸은 경고로 남긴다.
    """
    years = collections.Counter(s["_raw"].year for s in sessions if hasattr(s["_raw"], "year"))
    fallback_year = years.most_common(1)[0][0] if years else datetime.date.today().year
    warnings = []

    for s in sessions:
        raw = s.pop("_raw")
        where = s.pop("_where")
        if hasattr(raw, "strftime"):
            d = datetime.date(raw.year, raw.month, raw.day)
        elif (m := DATE_TEXT.search(str(raw))):
            d = datetime.date(fallback_year, int(m.group(1)), int(m.group(2)))
            warnings.append(f"{where}: 날짜 칸이 '{raw}' → {d}로 추정했습니다. 시트를 고쳐주세요.")
        else:
            warnings.append(f"{where}: 날짜 '{raw}'를 읽지 못해 건너뜁니다.")
            s["date"] = None
            continue
        s["date"] = d.isoformat()
        s["weekday"] = WD[d.weekday()]
        s["dateLabel"] = f"{d.month}월 {d.day}일"

    return [s for s in sessions if s["date"]], warnings


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "wb.xlsx"
    if not sys.argv[1:]:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id()}/export?format=xlsx"
        urllib.request.urlretrieve(url, path)

    wb = openpyxl.load_workbook(path, data_only=True)
    tabs = [t for t in wb.sheetnames if t.startswith(TAB_PREFIX)]
    if not tabs:
        sys.exit(f"'{TAB_PREFIX}'로 시작하는 탭이 없습니다.")

    raw = []
    for tab in tabs:
        ws = wb[tab]
        for top in range(BLOCK_FIRST, (ws.max_row or BLOCK_FIRST) + 1, BLOCK_STRIDE):
            for off in COL_OFFSETS:
                if (s := parse_session(ws, top, off)):
                    raw.append(s)

    sessions, warnings = resolve_dates(raw)

    # 같은 날짜가 두 번 적혔으면 내용이 더 많은 쪽을 남긴다
    best = {}
    for s in sessions:
        cur = best.get(s["date"])
        if cur is None or len(s["exercises"]) > len(cur["exercises"]):
            best[s["date"]] = s
    sessions = sorted(best.values(), key=lambda s: s["date"])

    json.dump(sessions, open("workout.json", "w"), ensure_ascii=False, indent=2)

    done = [s for s in sessions if not s["planned"]]
    print(f"탭 {tabs} → 기록 {len(done)}일 + 예정 {len(sessions) - len(done)}일 → workout.json")
    for s in sessions:
        tail = "예정" if s["planned"] else f"운동 {len(s['exercises'])}개 · 볼륨 {s['totalVolume']}"
        print(f"  {s['date']}({s['weekday']}) {s['part']} · {tail}")
    for w in warnings:
        print(f"  ⚠ {w}")


if __name__ == "__main__":
    main()
