# Intent template 3D E2E evidence

Run `npm run test:e2e:3d --prefix frontend` while the backend is available at
`127.0.0.1:8000` and the frontend at `127.0.0.1:5173`.

The test submits five representative natural-language prompts through the real
browser UI, opens the 3D circuit page, waits for all four GLB parts, verifies the
rendered WebGL canvas and jumper-wire count, and writes one full-page screenshot
per demo into this directory.
