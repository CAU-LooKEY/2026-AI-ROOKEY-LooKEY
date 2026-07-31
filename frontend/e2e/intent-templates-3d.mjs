import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright-core";

const appUrl = process.env.E2E_APP_URL ?? "http://127.0.0.1:5173";
const chromePath = process.env.CHROME_PATH ?? "/usr/bin/google-chrome";
const evidenceDir = path.resolve(process.cwd(), "../docs/test-evidence/intent-templates-e2e");
const demos = [
  ["01-proximity-led", "손을 가까이 대면 LED가 켜지게 해줘", "5/5 부품", 7],
  ["02-proximity-led-ultrasonic", "초음파 센서로 가까이 온 손을 감지해 LED 켜기", "5/5 부품", 7],
  ["03-button-led", "버튼을 누르면 LED가 켜지게 해줘", "5/5 부품", 5],
  ["04-button-led-control", "푸시버튼으로 LED를 제어하고 싶어", "5/5 부품", 5],
  ["05-distance-alarm", "물체가 가까우면 거리 경보를 보여줘", "5/5 부품", 7],
];

await mkdir(evidenceDir, { recursive: true });
const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--use-angle=swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
const browserErrors = [];
page.on("console", (message) => {
  if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) {
    browserErrors.push(message.text());
  }
});
page.on("response", (response) => {
  if (response.status() >= 400 && !response.url().endsWith("/favicon.ico")) {
    browserErrors.push(`HTTP ${response.status()} ${response.url()}`);
  }
});
page.on("pageerror", (error) => browserErrors.push(error.message));

try {
  for (const [name, prompt, componentText, wireCount] of demos) {
    await page.goto(appUrl, { waitUntil: "networkidle" });
    await page.locator(".inputBox input").fill(prompt);
    await page.getByRole("button", { name: "AI로 회로 만들기" }).click();
    await page.getByRole("heading", { name: "프로젝트 요약" }).waitFor({ timeout: 15000 });
    await page.locator(".pageActions .mainBtn").click();
    await page.getByRole("heading", { name: "3D 회로 조립도" }).waitFor();
    await page.locator(".circuit3dCanvas canvas").waitFor({ timeout: 20000 });
    await page.locator(".circuit3dState").waitFor({ state: "detached", timeout: 20000 });
    await page.getByText(componentText, { exact: true }).waitFor();
    const renderedWires = await page.locator(".circuit3dLegendItem").count();
    if (renderedWires !== wireCount) {
      throw new Error(`${name}: expected ${wireCount} wires, rendered ${renderedWires}`);
    }
    const canvasBox = await page.locator(".circuit3dCanvas canvas").boundingBox();
    if (!canvasBox || canvasBox.width < 300 || canvasBox.height < 200) {
      throw new Error(`${name}: WebGL canvas has an invalid size`);
    }
    await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true });
    process.stdout.write(`PASS ${name}: ${componentText}, ${renderedWires} wires\n`);
  }
  if (browserErrors.length) {
    throw new Error(`Browser errors:\n${browserErrors.join("\n")}`);
  }
} finally {
  await browser.close();
}
