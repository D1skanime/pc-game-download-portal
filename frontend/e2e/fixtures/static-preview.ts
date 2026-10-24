// Owned static browser preview. It serves build files only, with no backend proxy.
export function staticPreview(buildRoot: string) {
  const server = `import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const root=path.resolve(${JSON.stringify(buildRoot)}); const types={".js":"text/javascript",".css":"text/css",".svg":"image/svg+xml",".png":"image/png",".woff2":"font/woff2"};
http.createServer((req,res)=>{let file=path.resolve(root,"."+decodeURIComponent(new URL(req.url,"http://localhost").pathname));
if(file!==root&&!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
if(!fs.existsSync(file)||fs.statSync(file).isDirectory())file=path.join(root,"index.html");
res.setHeader("Content-Type",types[path.extname(file)]||"text/html");fs.createReadStream(file).pipe(res);}).listen(4177,"127.0.0.1");`;
  return {
    command: `node --input-type=module -e "import('data:text/javascript;base64,${Buffer.from(server).toString("base64")}')"`,
    url: "http://127.0.0.1:4177",
    reuseExistingServer: false,
    timeout: 15_000,
  };
}
