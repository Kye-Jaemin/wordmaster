# 설계안: 프로그래매틱 단어 페이지 `/word/<word>`

> 목적: 아카이브(이미 CTR ~33%, 최다 유입)가 증명한 "단어 단위 페이지가 검색에 먹힌다"는 패턴을 **수천 페이지 규모로 확장**한다. 경쟁사 Word Bee는 3.3만+ 단어 레퍼런스 페이지로 이 SERP를 점유 중.

---

## 1. 목표 & SEO 근거

- **타겟 쿼리**: `[word] meaning`, `[word] definition`, `what does [word] mean`, `[word] synonyms`, `[word] in a sentence` — 개별 볼륨은 작지만 **합산 롱테일이 거대**하고 난이도 낮음.
- **차별화(중요)**: 단순 사전 복제는 구글이 "scraped content"로 저평가. WordMaster만의 고유 가치를 페이지에 반드시 넣는다:
  1. **그 단어로 바로 플레이** (타일/애너그램/행맨 딥링크)
  2. **학습 각도** — "이 단어를 내 단어장에 추가", 난이도/카테고리 태그
  3. **이중언어**(en/ko) 정의·예문 — 한국 학습자용 차별점
- **내부링크 허브**: 아카이브·게임 결과·블로그에서 단어 페이지로, 단어 페이지에서 관련 단어·게임으로 연결 → 크롤 깊이·체류 개선.

## 2. URL · 라우팅

```
/word/<slug>            # 예: /word/quell  (소문자, 영문, 하이픈 없음)
/word/<slug>?lang=ko    # 한국어 변형 (기존 i18n 패턴 그대로)
```

- **slug 정규화**: 소문자, 공백→없음, 비영문 제거. 대문자/변형 요청은 301로 정규 slug로.
- **canonical**: 기존 base.html 규칙 그대로 — en은 `/word/quell`, ko는 `/word/quell?lang=ko`.
- **hreflang**: base.html가 `request.path` 기반으로 자동 처리하므로 추가 작업 불필요.
- **404 처리**: 사전에 없는/비속어/리스트 외 단어는 `noindex` + "단어를 찾을 수 없음 + 게임으로" 유도 (얇은 페이지 인덱싱 방지).

```python
# app.py 스케치
@app.route("/word/<slug>")
def word_page(slug):
    norm = re.sub(r"[^a-z]", "", slug.lower())
    if norm != slug:                      # 정규화 불일치 → 301
        return redirect(url_for("word_page", slug=norm), code=301)
    entry = get_word_entry(norm)          # 캐시/사전 조회 (아래 3장)
    if not entry:
        return render_template("word_not_found.html", word=norm), 404
    return render_template("word.html",
        title=f"{entry['word'].title()} — Meaning, Definition & Examples | WordMaster",
        meta_desc=build_meta(entry),      # "QUELL means … See definition, examples, synonyms, and play it as a word game."
        word=entry, **base_ctx())
```

## 3. 데이터 소스 (3단계, 권장: B)

기존 자산: 게임 단어 리스트(카테고리별 큐레이션) + 아카이브/학습카드가 쓰는 정의 파이프라인(무료 사전 API, dictionaryapi.dev 계열로 추정).

| 옵션 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A. 런타임 API 호출 | 요청마다 사전 API 조회 | 구현 빠름 | 봇 트래픽에 느림·레이트리밋·API 의존 |
| **B. 사전 빌드+캐시(권장)** | 큐레이션 단어들을 **사전에 한 번 fetch→JSON/SQLite로 저장**, 페이지는 캐시에서 렌더 | 빠름·안정·오프라인·구글 크롤 친화 | 갱신 배치 필요 |
| C. 정적 생성(SSG) | 빌드 시 HTML 생성 | 초고속 | Flask 동적성과 안 맞음 |

**권장 B 구현**:
1. 큐레이션 단어 풀 정의 (게임에 쓰는 단어 = 이미 양질·일반어). 1차 500~2,000개로 시작.
2. 빌드 스크립트 `scripts/build_word_cache.py` — 각 단어를 사전 API로 fetch → `data/words.sqlite`(또는 `data/words.json`)에 {word, ipa, pos, definitions[], examples[], synonyms[], antonyms[], etymology, ko_gloss} 저장. 레이트리밋 대비 sleep/backoff.
3. `get_word_entry()`는 이 캐시만 조회 (API 런타임 호출 0).
4. 한국어 글로스(`ko_gloss`)는 (a) 짧은 핵심 뜻만 수작업/번역 API로 채우거나 (b) 1차엔 영어 정의 + ko UI 라벨만으로 출발.

## 4. 페이지 콘텐츠 (얇은 콘텐츠 방지 = 사전+α)

```
H1: <Word> — Meaning & Definition           (ko: <단어> — 뜻과 정의)
1) 발음/IPA + 오디오(선택) + 품사
2) 정의 (번호 목록, 영어; ko면 한국어 글로스 우선 노출)
3) 예문 2~3개
4) 유의어 / 반의어 (각각 관련 단어 페이지로 내부링크)
5) 어원 (있으면)
6) ★ "이 단어로 플레이" — 타일/애너그램/행맨 딥링크 버튼 (고유 가치 + 체류↑)
   - 단, 정답 스포일러 방지: '랜덤 게임 시작'으로 연결하거나 별도 연습 모드
7) ★ "내 단어장에 추가" (localStorage) — 학습 훅
8) 관련 단어(같은 어근/카테고리/길이) 12개 그리드 → 내부링크 허브
9) 짧은 학습 카피(이 단어를 외우는 팁) — 페이지 고유 텍스트 100~150단어
```

- **최소 분량 가드레일**: 정의/예문/유의어 중 2개 이상 없으면 `noindex`(얇은 페이지 차단).
- **고유성**: 6·7·9번이 사전 사이트와 차별화하는 핵심. 반드시 포함.

## 5. 구조화 데이터 (스키마)

```json
{
  "@context":"https://schema.org",
  "@type":"DefinedTerm",
  "name":"quell",
  "description":"to put an end to, typically by force",
  "inDefinedTermSet":{"@type":"DefinedTermSet","name":"WordMaster Vocabulary","url":"https://wordmaster.store/word/"}
}
```
- 추가로 BreadcrumbList(홈 › Word › quell). base.html의 head_schema 블록 재사용.
- (선택) 예문에 대해선 별도 마크업 불필요.

## 6. 사이트맵 통합

- 기존 `sitemap.xml` 생성 로직에 단어 페이지 루프 추가 (en + `?lang=ko`).
- **분할**: 단어가 1,000개 넘으면 `sitemap_words.xml`로 분리하고 `sitemap_index.xml`로 묶기(구글 권장, URL/사이트맵당 5만 한도).
- priority 0.5, changefreq monthly (사전 내용은 자주 안 변함).
- 인덱싱은 **점진 공개**: 1차 500개 → GSC에서 인덱싱·노출 확인 → 2차 확대. 한 번에 수만 개 투하 금지(크롤 예산·품질 평가 리스크).

## 7. 롤아웃 단계

| 단계 | 범위 | 산출 |
|---|---|---|
| P0 | 라우트+템플릿+캐시 스크립트, 단어 300개 | /word/* 동작, 사이트맵 등록 |
| P1 | 아카이브·게임결과·블로그에서 내부링크 연결 | 크롤 경로 확보 |
| P2 | 1,000~2,000개로 확대 + ko 글로스 | 롱테일 노출 시작 |
| P3 | 관련어 그리드 고도화, GSC 성과 보고 | 인덱싱·클릭 측정 |

## 8. 리스크 & 가드레일

- **얇은/중복 콘텐츠**: 최소 분량 가드 + 고유 블록(플레이/학습/관련어) 필수.
- **사전 스크랩 저평가**: 정의를 그대로 베끼지 말고 요약+예문+학습 각도로 재구성. 출처 사전이 robots/약관상 허용하는지 확인.
- **API 레이트리밋**: 빌드 캐시(옵션 B)로 런타임 호출 제거.
- **크롤 예산**: 점진 공개 + 사이트맵 분할.
- **성과 측정**: GSC에서 `/word/` 디렉토리 필터로 노출·클릭·평균순위 추적(아카이브 18.9 → 단어 페이지 목표 추적).

## 9. 즉시 착수 체크리스트

- [ ] `templates/word.html`, `templates/word_not_found.html` 생성
- [ ] `/word/<slug>` 라우트 + slug 정규화/301/404
- [ ] `scripts/build_word_cache.py` (단어→사전 fetch→캐시)
- [ ] 사이트맵에 단어 URL 루프 + 분할
- [ ] 아카이브/결과/블로그 내부링크 추가
- [ ] DefinedTerm + Breadcrumb 스키마
- [ ] GSC에 사이트맵 재제출 + `/word/` 성과 모니터링
