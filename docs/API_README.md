# LooKEY Backend API

프론트엔드 연동을 위한 초기 목업 API 문서입니다.

## Run

```powershell
cd backend
uvicorn app.main:app --reload
```

Swagger 문서는 서버 실행 후 아래 주소에서 확인할 수 있습니다.

```text
http://127.0.0.1:8000/docs
```

## Endpoints

### `GET /health`

서버가 정상 실행 중인지 확인합니다.

### `GET /api/v1/circuit/demo`

프론트엔드 React Flow 캔버스에 바로 연결할 수 있는 더미 회로 JSON을 반환합니다.

### `POST /api/v1/circuit/generate`

자연어 프롬프트를 받아 현재는 데모 회로 JSON을 반환합니다.

Request:

```json
{
  "prompt": "버튼을 누르면 LED가 켜지는 회로를 만들고 싶어"
}
```

Response 주요 구조:

```json
{
  "id": "demo-button-led",
  "title": "버튼으로 LED 켜기",
  "nodes": [],
  "edges": [],
  "code": "...",
  "warnings": [],
  "explanation": []
}
```
