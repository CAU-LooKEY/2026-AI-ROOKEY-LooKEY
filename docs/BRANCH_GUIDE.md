# LooKEY branch guide

This repository keeps each team's original branch and provides an integrated
branch for end-to-end testing.

## Branch map

| Branch | Contents |
| --- | --- |
| `main` | Stable baseline and merged backend mock API |
| `feat/ai-init` | Team 1 natural-language parser and component dictionary |
| `dev/assets_db` | Team 2 assets, GLB models, pin anchors, breadboard data, and knowledge DB |
| `feature/validator-rules` | Team 3 circuit validation rules and edge-case collector |
| `dev/frontend` | Team 5 staged React/React Flow interface |
| `feat/k-exaone-circuit-integration` | Live K-EXAONE API and improved circuit rendering |
| `integration/mvp` | Combined branch for running and testing the latest team work |

The original team branches are preserved. New integration fixes should be made
on a feature branch based on `integration/mvp`, then reviewed before reaching
`main`.

## Fetch every remote branch

Some VS Code clones initially fetch only one branch. Run these commands in the
repository terminal:

```powershell
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
git fetch origin --prune
git branch -r
```

## Open a team branch

Commit or stash local changes before switching branches.

For a branch that does not exist locally yet:

```powershell
git switch --track origin/dev/frontend
```

Use the same form for another team branch:

```powershell
git switch --track origin/feat/ai-init
git switch --track origin/dev/assets_db
git switch --track origin/feature/validator-rules
```

If the local branch already exists:

```powershell
git switch dev/frontend
git pull --ff-only
```

## Run the integrated MVP

```powershell
git switch --track origin/integration/mvp
```

If `integration/mvp` already exists locally, use `git switch integration/mvp`
and `git pull --ff-only` instead.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Enter the K-EXAONE key and endpoint ID only in `backend/.env`. The key field in
`.env.example` is intentionally empty and `.env` is ignored by Git.

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The integrated user-facing application lives under `frontend/`. The root-level
Vite project came from `dev/assets_db` and remains as Team 2's asset database
viewer/prototype.

## Recommended daily workflow

```powershell
git switch integration/mvp
git pull --ff-only
git switch -c feat/<short-work-name>
```

Commit only the files for that task, push the new branch, and open a pull
request back to `integration/mvp`. Avoid committing directly to team branches
or `main` while integration work is in progress.
