import { readFileSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

type HttpMethod = "GET" | "HEAD" | "POST" | "PUT" | "PATCH" | "DELETE";
type StorageClass = "external_read_only" | "resources" | "assets" | "database";

interface RawCall {
  importer: string;
  call: string;
  method: HttpMethod;
  route: string;
}

interface Authority extends RawCall {
  operation: string;
  storageClass: StorageClass | "unknown";
  forbidden: boolean;
}

const repositoryRoot = resolve(process.cwd(), "..");
const v2Root = resolve(process.cwd(), "src/v2");
const romServicePath = resolve(process.cwd(), "src/services/api/rom.ts");

const routeAuthorities = [
  {
    method: "DELETE",
    route: /^\/roms\/\{[^}]+\}\/files\/\{[^}]+\}$/,
    operation: "DELETE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "POST",
    route: /^\/roms\/\{[^}]+\}\/manuals\/files$/,
    operation: "SIDECAR_WRITE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "DELETE",
    route: /^\/roms\/\{[^}]+\}\/manuals\/files\/\{[^}]+\}$/,
    operation: "DELETE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "POST",
    route: /^\/roms\/\{[^}]+\}\/soundtracks$/,
    operation: "SIDECAR_WRITE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "DELETE",
    route: /^\/roms\/\{[^}]+\}\/soundtracks\/\{[^}]+\}$/,
    operation: "DELETE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "POST",
    route: /^\/roms\/\{[^}]+\}\/screenshots$/,
    operation: "COVER_WRITE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "DELETE",
    route: /^\/roms\/\{[^}]+\}\/screenshots\/\{[^}]+\}$/,
    operation: "DELETE",
    storageClass: "external_read_only",
    forbidden: true,
  },
  {
    method: "POST",
    route: /^\/roms\/\{[^}]+\}\/manuals$/,
    operation: "UPLOAD",
    storageClass: "resources",
    forbidden: false,
  },
  {
    method: "POST",
    route: /^\/roms\/\{[^}]+\}\/manuals\/redownload$/,
    operation: "OVERWRITE",
    storageClass: "resources",
    forbidden: false,
  },
  {
    method: "DELETE",
    route: /^\/roms\/\{[^}]+\}\/manuals$/,
    operation: "DELETE",
    storageClass: "resources",
    forbidden: false,
  },
  {
    method: "POST",
    route: /^\/screenshots$/,
    operation: "UPLOAD",
    storageClass: "assets",
    forbidden: false,
  },
  {
    method: "PUT",
    route: /^\/screenshots\/\{[^}]+\}$/,
    operation: "WRITE",
    storageClass: "database",
    forbidden: false,
  },
  {
    method: "DELETE",
    route: /^\/screenshots\/\{[^}]+\}$/,
    operation: "DELETE",
    storageClass: "assets",
    forbidden: false,
  },
] as const;

const coveredFamily =
  /^\/roms\/\{[^}]+\}\/(?:files|manuals\/files|soundtracks|screenshots)(?:\/|$)/;
const httpMethods = new Set<HttpMethod>([
  "GET",
  "HEAD",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
]);

function scriptFrom(source: string): string {
  const match = source.match(/<script\s+setup[^>]*>([\s\S]*?)<\/script>/);
  return match?.[1] ?? source;
}

function routeText(
  node: ts.Expression,
  sourceFile: ts.SourceFile,
): string | null {
  if (ts.isStringLiteralLike(node)) return node.text;
  if (!ts.isTemplateExpression(node)) return null;
  let route = node.head.text;
  for (const span of node.templateSpans) {
    const name = span.expression
      .getText(sourceFile)
      .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
      .replace(/[^a-zA-Z0-9_]/g, "_")
      .replace(/^_+|_+$/g, "")
      .toLowerCase();
    route += `{${name || "id"}}${span.literal.text}`;
  }
  return route;
}

function normalizeRoute(route: string): string {
  const clean = route
    .split("?")[0]
    .replace(/^\/api/, "")
    .replace(/\/+$/, "");
  return (clean || "/").replace(/\/\d+(?=\/|$)/g, "/{id}");
}

function enclosingFunction(node: ts.Node): string {
  let current: ts.Node | undefined = node;
  while (current) {
    if (ts.isFunctionDeclaration(current) && current.name)
      return current.name.text;
    if (
      (ts.isArrowFunction(current) || ts.isFunctionExpression(current)) &&
      current.parent &&
      ts.isVariableDeclaration(current.parent) &&
      ts.isIdentifier(current.parent.name)
    ) {
      return current.parent.name.text;
    }
    current = current.parent;
  }
  return "module";
}

function importedClients(sourceFile: ts.SourceFile): Set<string> {
  const clients = new Set<string>();
  for (const statement of sourceFile.statements) {
    if (
      !ts.isImportDeclaration(statement) ||
      !ts.isStringLiteral(statement.moduleSpecifier)
    )
      continue;
    const moduleName = statement.moduleSpecifier.text;
    if (moduleName !== "axios" && !moduleName.includes("/services/api"))
      continue;
    const clause = statement.importClause;
    if (clause?.name) clients.add(clause.name.text);
    if (clause?.namedBindings && ts.isNamedImports(clause.namedBindings)) {
      for (const element of clause.namedBindings.elements)
        clients.add(element.name.text);
    }
  }
  return clients;
}

function collectAliases(sourceFile: ts.SourceFile, clients: Set<string>): void {
  let changed = true;
  while (changed) {
    changed = false;
    const visit = (node: ts.Node) => {
      if (
        ts.isVariableDeclaration(node) &&
        ts.isIdentifier(node.name) &&
        node.initializer &&
        ts.isIdentifier(node.initializer) &&
        clients.has(node.initializer.text) &&
        !clients.has(node.name.text)
      ) {
        clients.add(node.name.text);
        changed = true;
      }
      ts.forEachChild(node, visit);
    };
    visit(sourceFile);
  }
}

function extractRawCalls(source: string, importer: string): RawCall[] {
  const code = scriptFrom(source);
  const sourceFile = ts.createSourceFile(
    importer,
    code,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  );
  const clients = importedClients(sourceFile);
  clients.add("api");
  collectAliases(sourceFile, clients);
  const calls: RawCall[] = [];
  const visit = (node: ts.Node) => {
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression)
    ) {
      const method = node.expression.name.text.toUpperCase() as HttpMethod;
      const receiver = node.expression.expression;
      if (
        httpMethods.has(method) &&
        ts.isIdentifier(receiver) &&
        clients.has(receiver.text) &&
        node.arguments[0]
      ) {
        const route = routeText(node.arguments[0], sourceFile);
        if (route) {
          calls.push({
            importer,
            call: `${enclosingFunction(node)}:${receiver.text}.${method.toLowerCase()}`,
            method,
            route: normalizeRoute(route),
          });
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  return calls;
}

function serviceCalls(source: string): Map<string, RawCall[]> {
  const calls = extractRawCalls(source, "src/services/api/rom.ts");
  const result = new Map<string, RawCall[]>();
  for (const call of calls) {
    const functionName = call.call.split(":", 1)[0];
    result.set(functionName, [...(result.get(functionName) ?? []), call]);
  }
  return result;
}

function importedRomServiceAliases(sourceFile: ts.SourceFile): Set<string> {
  const aliases = new Set<string>();
  for (const statement of sourceFile.statements) {
    if (
      !ts.isImportDeclaration(statement) ||
      !ts.isStringLiteral(statement.moduleSpecifier)
    )
      continue;
    if (statement.moduleSpecifier.text !== "@/services/api/rom") continue;
    if (statement.importClause?.name)
      aliases.add(statement.importClause.name.text);
  }
  collectAliases(sourceFile, aliases);
  return aliases;
}

function usedServiceCalls(
  source: string,
  importer: string,
  callsByFunction: Map<string, RawCall[]>,
): RawCall[] {
  const code = scriptFrom(source);
  const sourceFile = ts.createSourceFile(
    importer,
    code,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  );
  const aliases = importedRomServiceAliases(sourceFile);
  const result: RawCall[] = [];
  const visit = (node: ts.Node) => {
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      ts.isIdentifier(node.expression.expression) &&
      aliases.has(node.expression.expression.text)
    ) {
      const functionName = node.expression.name.text;
      for (const serviceCall of callsByFunction.get(functionName) ?? []) {
        result.push({
          ...serviceCall,
          importer,
          call: `${node.expression.getText(sourceFile)} -> ${serviceCall.call}`,
        });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  return result;
}

function classify(call: RawCall): Authority {
  const match = routeAuthorities.find(
    (entry) => entry.method === call.method && entry.route.test(call.route),
  );
  if (match)
    return {
      ...call,
      operation: match.operation,
      storageClass: match.storageClass,
      forbidden: match.forbidden,
    };
  if (call.method === "GET" || call.method === "HEAD") {
    return {
      ...call,
      operation: "READ",
      storageClass: "external_read_only",
      forbidden: false,
    };
  }
  if (coveredFamily.test(call.route)) {
    throw new Error(
      `unclassified authority importer=${call.importer} call=${call.call} method=${call.method} route=${call.route} operation=UNKNOWN storage=unknown`,
    );
  }
  return {
    ...call,
    operation: "CONTROL_PLANE",
    storageClass: "database",
    forbidden: false,
  };
}

function v2Files(directory = v2Root): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = resolve(directory, entry);
    if (statSync(path).isDirectory()) return v2Files(path);
    return /\.(?:ts|vue)$/.test(entry) && !/\.test\.ts$/.test(entry)
      ? [path]
      : [];
  });
}

function inventorySource(
  source: string,
  importer: string,
  callsByFunction: Map<string, RawCall[]>,
): Authority[] {
  return [
    ...extractRawCalls(source, importer),
    ...usedServiceCalls(source, importer, callsByFunction),
  ].map(classify);
}

describe("active v2 source mutation authority inventory", () => {
  const romSource = readFileSync(romServicePath, "utf8");
  const callsByFunction = serviceCalls(romSource);

  it("uses live storage operations and trusted descriptor names", () => {
    const policy = readFileSync(
      resolve(repositoryRoot, "backend/handler/filesystem/storage_policy.py"),
      "utf8",
    );
    const composition = readFileSync(
      resolve(repositoryRoot, "backend/handler/filesystem/__init__.py"),
      "utf8",
    );
    for (const operation of ["SIDECAR_WRITE", "COVER_WRITE", "DELETE"]) {
      expect(policy).toMatch(new RegExp(`^\\s*${operation}\\s*=`, "m"));
    }
    expect(composition).toContain(
      "legacy_external_storage = storage_composition.legacy_external",
    );
    expect(composition).toContain("OwnedStorageKind.RESOURCES");
    expect(composition).toContain("OwnedStorageKind.ASSETS");
  });

  it("contains no forbidden external shared-file authority in active v2", () => {
    const inventory = v2Files().flatMap((path) => {
      const importer = path.slice(resolve(process.cwd(), "src").length + 1);
      return inventorySource(
        readFileSync(path, "utf8"),
        importer,
        callsByFunction,
      );
    });
    const violations = inventory
      .filter((entry) => entry.forbidden)
      .map(
        (entry) =>
          `${entry.importer} | ${entry.call} | ${entry.method} ${entry.route} | ${entry.operation} | ${entry.storageClass}`,
      );
    expect(violations).toEqual([]);
  });

  it("does not export forbidden external mutation service methods", () => {
    const forbiddenExports = [
      "deleteRomFile",
      "uploadManualFiles",
      "deleteManualFile",
      "uploadSoundtracks",
      "removeSoundtrack",
      "uploadScreenshots",
      "removeScreenshot",
    ];
    const exportBlock =
      romSource.match(/export default \{([\s\S]*?)\n\};/)?.[1] ?? "";
    expect(
      forbiddenExports.filter((name) =>
        new RegExp(`\\b${name}\\b`).test(exportBlock),
      ),
    ).toEqual([]);
  });

  it("classifies aliases and raw calls by concrete route instead of banning generic clients", () => {
    const fixture = `
      import transport from "@/services/api";
      const alias = transport;
      alias.get(\`/roms/\${romId}/files/\${fileId}\`);
      alias.post("/collections", { name: "Favorites" });
      alias.post(\`/roms/\${romId}/manuals\`, formData);
      alias.post("/screenshots", formData);
      alias.delete(\`/screenshots/\${screenshotId}\`);
    `;
    expect(
      inventorySource(fixture, "positive-fixture.ts", new Map()),
    ).toMatchObject([
      { method: "GET", operation: "READ", forbidden: false },
      {
        method: "POST",
        operation: "CONTROL_PLANE",
        storageClass: "database",
        forbidden: false,
      },
      {
        method: "POST",
        operation: "UPLOAD",
        storageClass: "resources",
        forbidden: false,
      },
      {
        method: "POST",
        operation: "UPLOAD",
        storageClass: "assets",
        forbidden: false,
      },
      {
        method: "DELETE",
        operation: "DELETE",
        storageClass: "assets",
        forbidden: false,
      },
    ]);
  });

  it("reports forbidden and unknown covered combinations with complete safe diagnostics", () => {
    const forbidden = inventorySource(
      `import api from "@/services/api"; const client = api; client.delete(\`/roms/\${romId}/soundtracks/\${fileId}\`);`,
      "aliased-negative.ts",
      new Map(),
    );
    expect(forbidden).toMatchObject([
      {
        importer: "aliased-negative.ts",
        method: "DELETE",
        operation: "DELETE",
        storageClass: "external_read_only",
        forbidden: true,
      },
    ]);
    expect(() =>
      inventorySource(
        `import api from "@/services/api"; api.patch(\`/roms/\${romId}/manuals/files\`, {});`,
        "unknown-negative.ts",
        new Map(),
      ),
    ).toThrow(
      "unclassified authority importer=unknown-negative.ts call=module:api.patch method=PATCH route=/roms/{rom_id}/manuals/files operation=UNKNOWN storage=unknown",
    );
  });
});
