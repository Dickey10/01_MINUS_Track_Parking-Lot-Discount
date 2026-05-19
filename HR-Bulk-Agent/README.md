# HR Bulk Change Agent

인사 변동사항을 자연어 프롬프트로 입력하고, 직원별 초안/역질문/플랫폼별 미리보기와 승인 절차를 거쳐 선물24/워크드에 반영하기 위한 1차 MVP입니다. 초기 운영 방향은 사내 서버가 아니라 담당자 PC 로컬 실행입니다.

## 구현 범위

- LLM 스타일 대화형 입력: 자연어 요청을 직원별 변경 초안으로 분리
- 역질문 생성: 사번, 적용일, 회사, 부서, 직급 등 누락값만 질문
- 단건/다건 변경 요청 생성: 입사, 퇴사, 휴직, 복직, 진급, 부서변경, 조직개편
- Excel/CSV 업로드 검증
- 설정 화면: LLM API 키, 선물24/워크드/시프티 연동값, Google Sheet URL, 로컬 마스터 파일 경로 관리
- 계정/권한: 관리자 계정으로 사용자 ID/PW 생성 및 등록/수정/삭제 권한 부여
- 직원 마스터: CSV 업로드 또는 입력창 저장
- 진급 후보: 입사일과 입사호봉 기준 현 호봉 계산 및 직급별 후보 추출
- 선물24/워크드 커넥터 구현
- 시프티, ERP, Amaranth10, IN HR 커넥터 확장 자리 제공
- 승인 후 실행 구조
- 기본값은 `dry-run`이며 실제 외부 API 쓰기 호출은 비활성화
- 감사 로그 저장 시 개인정보 마스킹/사번 해시 처리
- AI 보조는 개인정보 마스킹 후 호출하며, `OPENAI_API_KEY`가 없으면 로컬 규칙으로 동작

## 실행

```powershell
cd C:\Users\HOME\Downloads\HR-Bulk-Agent
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

담당자 PC에서 접속 URL:

```text
http://127.0.0.1:8011/
```

기존 8010 포트가 점유되어 있으면 `http://127.0.0.1:8010/static/index.html` 화면에서도 API는 8011 백엔드로 연결되도록 구성했습니다.

초기 로그인:

```text
ID: admin
PW: admin123!
```

최초 로그인 후 설정 화면에서 관리자 비밀번호를 변경하고, 사용자별 등록/수정/삭제 권한을 부여하세요.

## 안전 설정

실제 선물24/워크드 API를 호출하려면 `.env`에 아래 값을 명시해야 합니다.

```text
HR_AGENT_ALLOW_LIVE_CONNECTORS=true
GIFT24_CLIENT_ID=...
GIFT24_CLIENT_SECRET=...
WORKD_BASE_URL=...
WORKD_API_KEY=...
```

운영 전에는 API 문서의 실제 엔드포인트, payload 키, sandbox 여부를 반드시 확인해야 합니다.

## 업로드 컬럼

CSV/XLSX 첫 행은 아래 한글 컬럼 또는 내부 필드명을 사용할 수 있습니다.

```text
변경유형, 사번, 이름, 회사, 재직상태, 부서, 직급, 직책, 고용형태, 입사일, 퇴사일, 휴직시작일, 복직일, 이메일, 휴대전화, 생년월일, 대상플랫폼
```

`대상플랫폼`은 `gift24,workd`처럼 콤마로 입력합니다.

## 대화형 입력 예시

```text
6월 1일 입사자 등록해줘. 회사는 하츠.
사번 260601 홍길동 영업팀 대리 2026-06-01 입사 010-1234-5678 hong@example.com
사번 260602 김하나 개발팀 사원 2026-06-01 입사
연초 승진자도 반영 필요: 사번 1001 박민수 영업팀 과장 승진, 사번 1002 이서연 개발팀 차장 승진
```

여러 직원/여러 팀 변경은 줄 단위로 초안을 만들고, 누락된 항목은 화면에서 역질문으로 표시합니다.

## 참고 Repository

- ChiefOnboarding: 온보딩 작업 큐와 웹/Slack 흐름
- Horilla: HRMS, 입퇴사/근태/평가 모듈 구조
- Frappe HR: 직원 마스터와 HR 프로세스 모델
- MintHCM: AI-enabled HCM, 권한/프로필 구조
- Formbricks: 대화형/단계형 정보 수집 패턴
- Open Data QnA: 자연어 기반 DB 질의 패턴
- OpenAgent: 로컬 실행형 AI assistant 구조

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
.\.venv\Scripts\python.exe -m py_compile app\main.py app\models.py app\connectors\gift24.py app\connectors\workd.py
```
