# datasheet-intelligence skill 소개

## agentskills.io와 skill.sh

요근래 Claude 가 만든 skills 가 OpenAI, Cursor, Antigravity 등이 받아들이며 [**agentskills.io**](http://agentskills.io/) 라는 표준이 되었습니다. 

agentskill.io를 짧게 요약하자면 "에이전트 스킬은 에이전트가 보다 정확하고 효율적으로 업무를 수행하는 데 사용할 수 있는 지침, 스크립트 및 리소스 폴더" 라고 할수 있습니다. (공식문서 참조)

또한 누구나 agent skill을 만들고 사용할 수 있으며, vercel의 [skill.sh](https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem)를 활용하여 다른 사람이 작성한 skill을 손쉽게 본인의 환경에 셋업이 가능합니다.

## datasheet-intelligence skill 만들어보기

저 또한 이번 명절에 agent skill을 하나 만들어보았는데요. 이전 미팅때 Walter께서 BSP개발할때 pdf/docx 형태의 문서를  ai agent가 제대로 읽어들이지 못한다는 문제를 공유받아 이를 skill로 해결해보면 어떨까?라는 아이디어에서 시작되었습니다.

### 이전 문제점

저는 전문적인 임베디드 개발 경험이 없지만, 다음과 같은 예시 작업을 통해 이전의 문제점들을 유추해보았습니다.

1. workspace 내에 데이터 시트 준비 [RP-008371-DS-1-rp2040-datasheet.pdf](https://pip-assets.raspberrypi.com/categories/814-rp2040/documents/RP-008371-DS-1-rp2040-datasheet.pdf?disposition=inline) (총 642 페이지)
2. task 작업 명령:
    
    > "제공된 데이터시트를 참고하여 RP2040의 I2C0 컨트롤러를 100kHz 마스터 모드로 초기화하는 C 코드를 작성해. 관련 레지스터 주소와 비트 설정은 반드시 데이터시트를 근거로 해야 해."
    > 
3. ai agent의 동작 확인 (참고: 저는 antigravity의 gemini-3-pro 사용했습니다.)

위 작업을 10번정도 시켜보니 다음과 같은 몇가지 양상의 워크플로우를 보여주는데요, 

- pdf 를 분석하기 위해 pdftotext 파이썬 라이브러리를 활용해서 pdf 전문의 텍스트 파싱
    
    → 문제) 문서 내 목차/헤더/테이블과 같은 레이아웃이 다 깨짐

-  pdf -> text 변환 후, 642페이지에 해당하는 방대한 내용을 `grep`으로 찾고자 하는 키워드 검색
    
    → 문제) 키워드가 포함된 페이지가 너무 적거나, 내용 출력이 너무 많아서 컨텍스트에 다 담기지 않음 (진짜 필요한 내용을 찾기 어려워함)
    
- Antigravity 기능인 브라우저 랜더링을 활용하여 pdf 랜더링 후 멀티모달 인식을 통해 문서 내용 파악
    
    → 문제) 시간/토큰소모 굉장히 비효율적
    
- 스스로 pdf 문서를 분석하는 파이썬 코드를 생성 후, ai agent 스스로 찾고자 하는 키워드를 기반으로 검색 가능하도록 수행
    
    → **아이디어 good) 이 방법을 통해 나온 결과물이 가장 실제 문서 참조율이 높음!**

### datasheet-intelligence skill 설명

위 세 번째 접근 방식("키워드 기반 탐색 → 해당 페이지 읽기 → 반복")을 **스킬로 표준화**한 것이 바로 `datasheet-intelligence`입니다.

AI 에이전트가 데이터시트(PDF/DOCX/XLSX)를 다룰 때, 문서 전체를 통째로 읽는 대신 **"찾고 → 읽고 → 다시 찾고"** 루프를 따르도록 유도합니다.

스킬은 세 개의 Python 스크립트로 구성되어 있습니다:

| 스크립트 | 역할 | 설명 |
| :--- | :--- | :--- |
| `scripts/toc.py` | 목차 추출 | PDF 북마크 또는 Heading 분석을 통해 문서 구조를 파악 |
| `scripts/search.py` | 키워드 검색 | 레지스터명, 베이스 주소 등 키워드로 해당 페이지를 빠르게 탐색 |
| `scripts/read.py` | 타겟 읽기 | 필요한 페이지 범위만 선택적으로 텍스트 추출 |

에이전트의 동작 흐름은 다음과 같습니다:

```
1. toc.py로 문서 구조 파악 (목차 확인)
2. search.py로 관련 키워드가 있는 페이지 번호 탐색
3. read.py로 해당 페이지만 선택적으로 읽기
4. 부족하면? → 새 키워드로 2-3 반복
```

추가로 테이블/헤더 레이아웃이 중요한 경우 `--structured` 모드(docling 기반)를 사용하면 마크다운 형태로 정확한 구조를 보존한 파싱이 가능합니다.

### 적용 전후 비교

| | Before (스킬 없이) | After (스킬 적용) |
| :--- | :--- | :--- |
| **문서 파싱** | 전체 텍스트 추출 → 레이아웃 깨짐 | 페이지 단위 선택적 추출 |
| **탐색 방식** | 전문 읽기 또는 랜덤 접근 | 키워드 검색 → 타겟 읽기 |
| **테이블 인식** | ❌ 레지스터 맵 등 테이블 구조 파손 | ✅ `--structured` 모드로 구조 보존 |
| **근거 추적** | 출처 불명확 | 파일명 + 페이지 번호 명시 |
| **토큰 효율** | 수백 페이지 전체 소비 | 필요한 10~30페이지만 소비 |

---

## 설치 가이드

### 사전 준비

#### 1. Node.js (npx 사용을 위해 필요)

Vercel의 `skill.sh` CLI가 `npx`로 동작하므로 Node.js가 필요합니다.

| OS | 설치 방법 |
| :--- | :--- |
| **macOS** | `brew install node` 또는 [공식 설치](https://nodejs.org) |
| **Windows** | [공식 설치](https://nodejs.org) 또는 `winget install OpenJS.NodeJS.LTS` |
| **Linux (Ubuntu/Debian)** | `sudo apt install nodejs npm` 또는 [NodeSource](https://github.com/nodesource/distributions) |

#### 2. uv (Python 패키지 매니저 — 스킬 실행에 필요)

스킬 내부의 Python 스크립트를 실행하기 위해 `uv`가 필요합니다.

| OS | 설치 방법 |
| :--- | :--- |
| **macOS** | `brew install uv` 또는 `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Windows** | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| **Linux** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

> **참고**: `uv`는 `pip`/`venv`를 대체하는 초고속 Python 패키지 매니저입니다. 스킬 실행 시 별도의 가상환경 생성 없이 `uv run --project ...` 한 줄로 의존성 해결 + 스크립트 실행이 됩니다.

---

### 스킬 설치 (npx skills)

본인이 사용하는 AI 코딩 에이전트(Cursor, Claude Code, Antigravity 등)에 맞춰 스킬을 설치합니다.

```bash
npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence
```

실행하면 대화형 프롬프트가 나타나며, 아래 항목을 선택할 수 있습니다:

1. **설치할 스킬 선택** — `datasheet-intelligence` 선택
2. **대상 에이전트 선택** — 본인이 사용하는 도구 선택 (Cursor / Claude Code / Antigravity 등)
3. **설치 범위** — 글로벌 또는 프로젝트 레벨

설치가 완료되면 선택한 에이전트의 스킬 디렉토리에 `SKILL.md`가 복사됩니다.

```
# 설치 확인
npx skills list
```

> **Tip**: 스킬 업데이트가 있을 때는 아래 명령으로 간편하게 갱신할 수 있습니다.
> ```bash
> npx skills check    # 업데이트 확인
> npx skills update   # 업데이트 적용
> ```

---

### 설치 후 사용법

스킬이 설치되면 AI 에이전트에게 데이터시트 관련 작업을 지시하기만 하면 됩니다. 에이전트가 자동으로 스킬의 워크플로우를 따릅니다.

**예시 프롬프트:**

```
워크스페이스의 docs/rp2040.pdf 데이터시트를 참고하여
RP2040의 I2C0 컨트롤러를 100kHz 마스터 모드로 초기화하는 C 코드를 작성해.
관련 레지스터 주소와 비트 설정은 반드시 데이터시트를 근거로 해야 해.
```

에이전트는 스킬의 지침에 따라 자동으로:
1. `toc.py`로 문서 목차를 먼저 확인하고
2. `search.py`로 `I2C`, `IC_CON`, `I2C0_BASE` 등의 키워드를 검색하고
3. `read.py`로 관련 페이지만 읽어서 코드를 작성합니다.

결과물에는 데이터시트의 **파일명 + 페이지 번호** 근거가 함께 제공됩니다.
