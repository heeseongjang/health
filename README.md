# 수업일지 웹뷰

PT 수업일지를 날짜별로 볼 수 있게 정리한 정적 페이지입니다.
`index.html` 한 장으로 끝나며, GitHub Pages로 배포합니다.

## 갱신 방법

로컬 생성 스크립트(`stt/workout-log/`)에서 시트를 다시 읽어 `index.html`을 만든 뒤,
이 저장소에 커밋·푸시하면 몇 분 안에 반영됩니다.

```bash
cd ~/workspace/stt/workout-log && python3 parse.py && python3 build.py
cd ~/workspace/workout-log-site && git add -A && git commit -m "기록 갱신" && git push
```

> 원본 스프레드시트 주소와 파싱 스크립트는 이 저장소에 두지 않습니다.
