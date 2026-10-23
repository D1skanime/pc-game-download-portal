import { defineConfig } from "@playwright/test";

if (process.env.E2E_BASE_URL)
  throw new Error("Screenshot tests require the isolated local preview");
// The owned build directory avoids shared outputs; this static server has no backend proxy.
// Prepare it with npm run build -- --outDir /tmp/za-37-04-dist.
const buildRoot = process.env.ZA_SCREENSHOT_BUILD_ROOT ?? "/tmp/za-37-04-dist";
const server = `import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const root=path.resolve(${JSON.stringify(buildRoot)}); const types={".js":"text/javascript",".css":"text/css",".svg":"image/svg+xml",".png":"image/png",".woff2":"font/woff2"};
http.createServer((req,res)=>{let file=path.resolve(root,"."+decodeURIComponent(new URL(req.url,"http://localhost").pathname));
if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
if(!fs.existsSync(file)||fs.statSync(file).isDirectory())file=path.join(root,"index.html");
res.setHeader("Content-Type",types[path.extname(file)]||"text/html");fs.createReadStream(file).pipe(res);}).listen(4177,"127.0.0.1");`;
export default defineConfig({
  testDir: "./e2e",
  testMatch: "screenshot-management.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: "list",
  outputDir:
    process.env.ZA_SCREENSHOT_OUTPUT_DIR ??
    "../.planning/phases/37-zockarchive-screenshot-management-ui-redesign/evidence/browser-results",
  use: {
    baseURL: "http://127.0.0.1:4177",
    serviceWorkers: "block",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    hasTouch: true,
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        launchOptions: {
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
        },
      },
    },
  ],
  webServer: {
    command: `node --input-type=module -e "import('data:text/javascript;base64,${Buffer.from(server).toString("base64")}')"`,
    url: "http://127.0.0.1:4177",
    reuseExistingServer: false,
    timeout: 15_000,
  },
});
