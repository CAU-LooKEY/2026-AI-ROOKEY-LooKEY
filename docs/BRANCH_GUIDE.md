# LooKEY 브랜치 안내서

이 저장소는 각 팀의 원본 브랜치를 보존하면서 전체 흐름을 시험할 수 있는 통합 브랜치를 제공합니다.

## 브랜치 구성

| 브랜치 | 내용 |
| --- | --- |
| `main` | 안정적인 기준선과 병합된 백엔드 목업 API |
| `feat/ai-init` | 1팀 자연어 파서와 부품 사전 |
| `dev/assets_db` | 2팀 자산, GLB 모델, 핀 앵커, 브레드보드 데이터, 지식 DB |
| `feature/validator-rules` | 3팀 회로 검증 규칙과 예외 사례 수집기 |
| `dev/frontend` | 5팀 단계형 React/React Flow 화면 |
| `feat/k-exaone-circuit-integration` | 실제 K-EXAONE API와 개선된 회로 렌더링 |
| `integration/mvp` | 최신 팀 작업을 함께 실행하고 시험하기 위한 통합 브랜치 |

각 팀의 원본 브랜치는 보존합니다. 새로운 통합 수정은 `integration/mvp`를 기준으로
기능 브랜치를 만든 뒤 검토를 거쳐 `main`에 반영해야 합니다.

## 모든 원격 브랜치 가져오기

일부 VS Code 복제본은 처음에 하나의 브랜치만 가져옵니다. 저장소 터미널에서 다음 명령을 실행합니다.

```powershell
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --prune
git branch -r
```

## 팀 브랜치 열기

브랜치를 전환하기 전에 로컬 변경 사항을 커밋하거나 stash에 보관합니다.

아직 로컬에 없는 브랜치를 여는 방법:

```powershell
git switch --track origin/dev/frontend
```

다른 팀 브랜치도 같은 형식으로 엽니다.

```powershell
git switch --track origin/feat/ai-init
git switch --track origin/dev/assets_db
git switch --track origin/feature/validator-rules
```

로컬 브랜치가 이미 있는 경우:

```powershell
git switch dev/frontend
git pull --ff-only
```

## 통합 MVP 실행

```powershell
git switch --track origin/integration/mvp
```

`integration/mvp`가 이미 로컬에 있다면 `git switch integration/mvp`를 실행한 뒤
`git pull --ff-only`를 사용합니다.

### 백엔드

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

K-EXAONE 키와 엔드포인트 ID는 `backend/.env`에만 입력합니다. `.env.example`의
키 필드는 의도적으로 비어 있으며 `.env`는 Git에서 제외됩니다.

### 프론트엔드

두 번째 터미널을 열고 다음 명령을 실행합니다.

```powershell
cd frontend
npm install
npm run dev
```

통합 사용자용 애플리케이션은 `frontend/`에 있습니다. 루트의 Vite 프로젝트는
`dev/assets_db`에서 가져온 2팀의 자산 데이터베이스 뷰어·프로토타입입니다.

## 권장 일일 작업 흐름

```powershell
git switch integration/mvp
git pull --ff-only
git switch -c feat/<short-work-name>
```

해당 작업의 파일만 커밋하고 새 브랜치를 push한 뒤 `integration/mvp`를 대상으로
Pull Request를 엽니다. 통합 작업 중에는 팀 브랜치나 `main`에 직접 커밋하지 않습니다.
