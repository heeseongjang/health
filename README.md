# 수업일지 웹뷰

PT 수업일지 스프레드시트를 날짜별로 볼 수 있게 정리한 정적 페이지.

**https://heeseongjang.github.io/health/**

## 갱신

GitHub Actions가 **매일 21:00(KST)** 시트를 다시 읽어 페이지를 만들고,
바뀐 게 있을 때만 커밋합니다. 노트북은 켜져 있지 않아도 됩니다.

바로 반영하고 싶으면 **Actions → 수업일지 갱신 → Run workflow** (휴대폰에서도 가능).

## 구성

| 파일 | 역할 |
|---|---|
| `parse.py` | 시트를 내려받아 `workout.json` 생성 |
| `build.py` | `template.html` + `workout.json` → `index.html` |
| `template.html` | 페이지 본체 (데이터는 `__DATA__` 자리에 주입) |

시트 주소는 저장소에 두지 않고 Actions 시크릿 `SHEET_ID`로 주입합니다.
로컬에서 돌릴 때는 `.sheet-id` 파일(gitignore됨)에 적거나 환경변수로 넘기세요.

```bash
SHEET_ID=... python3 parse.py && python3 build.py
```
