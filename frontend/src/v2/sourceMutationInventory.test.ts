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
const serviceRoot = resolve(process.cwd(), "src/services/api");

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

function placeholderText(
  node: ts.Expression,
  sourceFile: ts.SourceFile,
): string {
  const name = node
    .getText(sourceFile)
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9_]/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  return "{" + (name || "id") + "}";
}

function constBindings(sourceFile: ts.SourceFile): Map<string, ts.Expression> {
  const bindings = new Map<string, ts.Expression>();
  const rejected = new Set<string>();
  const visit = (node: ts.Node) => {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer
    ) {
      const declarationList = node.parent;
      if (
        ts.isVariableDeclarationList(declarationList) &&
        (declarationList.flags & ts.NodeFlags.Const) !== 0 &&
        !bindings.has(node.name.text)
      ) {
        bindings.set(node.name.text, node.initializer);
      } else {
        rejected.add(node.name.text);
      }
    }
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      ts.isIdentifier(node.left)
    ) {
      rejected.add(node.left.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  for (const name of rejected) bindings.delete(name);
  return bindings;
}

function resolveRoute(
  node: ts.Expression,
  sourceFile: ts.SourceFile,
  bindings: Map<string, ts.Expression>,
  embedded: boolean,
  resolving: Set<string>,
): string | null {
  if (ts.isStringLiteralLike(node)) return node.text;
  if (
    ts.isParenthesizedExpression(node) ||
    ts.isAsExpression(node) ||
    ts.isTypeAssertionExpression(node)
  ) {
    return resolveRoute(
      node.expression,
      sourceFile,
      bindings,
      embedded,
      resolving,
    );
  }
  if (ts.isTemplateExpression(node)) {
    let route = node.head.text;
    for (const span of node.templateSpans) {
      route +=
        (resolveRoute(span.expression, sourceFile, bindings, true, resolving) ??
          placeholderText(span.expression, sourceFile)) + span.literal.text;
    }
    return route;
  }
  if (
    ts.isBinaryExpression(node) &&
    node.operatorToken.kind === ts.SyntaxKind.PlusToken
  ) {
    const left = resolveRoute(node.left, sourceFile, bindings, true, resolving);
    const right = resolveRoute(
      node.right,
      sourceFile,
      bindings,
      true,
      resolving,
    );
    return left === null || right === null ? null : left + right;
  }
  if (ts.isIdentifier(node)) {
    const initializer = bindings.get(node.text);
    if (initializer) {
      if (resolving.has(node.text)) return null;
      resolving.add(node.text);
      const value = resolveRoute(
        initializer,
        sourceFile,
        bindings,
        embedded,
        resolving,
      );
      resolving.delete(node.text);
      return value;
    }
    return embedded ? placeholderText(node, sourceFile) : null;
  }
  return embedded &&
    (ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node))
    ? placeholderText(node, sourceFile)
    : null;
}

function routeText(
  node: ts.Expression,
  sourceFile: ts.SourceFile,
): string | null {
  return resolveRoute(
    node,
    sourceFile,
    constBindings(sourceFile),
    false,
    new Set(),
  );
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

function expressionPath(node: ts.Expression): string | null {
  if (ts.isIdentifier(node)) return node.text;
  if (ts.isPropertyAccessExpression(node)) {
    const receiver = expressionPath(node.expression);
    return receiver ? receiver + "." + node.name.text : null;
  }
  if (
    ts.isElementAccessExpression(node) &&
    node.argumentExpression &&
    ts.isStringLiteralLike(node.argumentExpression)
  ) {
    const receiver = expressionPath(node.expression);
    return receiver ? receiver + "." + node.argumentExpression.text : null;
  }
  return null;
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
    if (moduleName !== "axios" && !/(?:^|\/)services\/api$/.test(moduleName))
      continue;
    const clause = statement.importClause;
    if (clause?.name) clients.add(clause.name.text);
    if (clause?.namedBindings && ts.isNamedImports(clause.namedBindings)) {
      for (const element of clause.namedBindings.elements)
        clients.add(element.name.text);
    }
    if (clause?.namedBindings && ts.isNamespaceImport(clause.namedBindings)) {
      clients.add(clause.namedBindings.name.text + ".default");
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
        expressionPath(node.initializer) !== null &&
        clients.has(expressionPath(node.initializer)!) &&
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

function containsClient(node: ts.Node, clients: Set<string>): boolean {
  const path = ts.isExpression(node) ? expressionPath(node) : null;
  if (
    path &&
    [...clients].some(
      (client) => path === client || path.startsWith(client + "."),
    )
  )
    return true;
  let found = false;
  ts.forEachChild(node, (child) => {
    if (!found && containsClient(child, clients)) found = true;
  });
  return found;
}

function safeImporter(importer: string): string {
  const normalized = importer.replace(/\\/g, "/");
  if (/^(?:\/|[A-Za-z]:\/)/.test(normalized)) {
    return normalized.split("/").filter(Boolean).at(-1) ?? "unknown";
  }
  return normalized.slice(0, 120);
}

function unclassifiableCall(
  importer: string,
  call: string,
  method: string,
  route: string,
): never {
  throw new Error(
    "unclassifiable call importer=" +
      safeImporter(importer) +
      " call=" +
      call.slice(0, 120) +
      " method=" +
      method +
      " route=" +
      route +
      " operation=UNKNOWN storage=unknown",
  );
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
    if (!ts.isCallExpression(node)) {
      ts.forEachChild(node, visit);
      return;
    }
    const member = node.expression;
    if (
      !ts.isPropertyAccessExpression(member) &&
      !ts.isElementAccessExpression(member)
    ) {
      ts.forEachChild(node, visit);
      return;
    }
    const receiver = member.expression;
    const receiverPath = expressionPath(receiver);
    const receiverKnown = receiverPath !== null && clients.has(receiverPath);
    const memberText = ts.isPropertyAccessExpression(member)
      ? member.name.text
      : member.argumentExpression &&
          ts.isStringLiteralLike(member.argumentExpression)
        ? member.argumentExpression.text
        : null;
    const methodText = memberText?.toUpperCase() ?? "UNKNOWN";
    const method = httpMethods.has(methodText as HttpMethod)
      ? (methodText as HttpMethod)
      : null;
    const dynamicMember =
      ts.isElementAccessExpression(member) && memberText === null;
    if (!method && !dynamicMember) {
      ts.forEachChild(node, visit);
      return;
    }
    if (!receiverKnown && !(method && containsClient(receiver, clients))) {
      ts.forEachChild(node, visit);
      return;
    }
    const call =
      enclosingFunction(node) +
      ":" +
      (receiverPath ?? "receiver") +
      "." +
      (memberText?.toLowerCase() ?? "[dynamic]");
    const route = node.arguments[0]
      ? routeText(node.arguments[0], sourceFile)
      : null;
    if (!receiverKnown || !method || !route) {
      unclassifiableCall(
        importer,
        call,
        method?.toString() ?? "UNKNOWN",
        route ? normalizeRoute(route) : "unknown",
      );
    }
    calls.push({
      importer: safeImporter(importer),
      call,
      method,
      route: normalizeRoute(route),
    });
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

function importedRomServiceAliases(sourceFile: ts.SourceFile): {
  objects: Set<string>;
  functions: Map<string, string>;
} {
  const objects = new Set<string>();
  const functions = new Map<string, string>();
  for (const statement of sourceFile.statements) {
    if (
      !ts.isImportDeclaration(statement) ||
      !ts.isStringLiteral(statement.moduleSpecifier)
    )
      continue;
    if (statement.moduleSpecifier.text !== "@/services/api/rom") continue;
    const clause = statement.importClause;
    if (clause?.name) objects.add(clause.name.text);
    if (clause?.namedBindings && ts.isNamedImports(clause.namedBindings)) {
      for (const element of clause.namedBindings.elements) {
        const imported = element.propertyName?.text ?? element.name.text;
        if (imported === "default") objects.add(element.name.text);
        else functions.set(element.name.text, imported);
      }
    }
    if (clause?.namedBindings && ts.isNamespaceImport(clause.namedBindings)) {
      objects.add(clause.namedBindings.name.text);
      objects.add(clause.namedBindings.name.text + ".default");
    }
  }
  collectAliases(sourceFile, objects);
  return { objects, functions };
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
    if (!ts.isCallExpression(node)) {
      ts.forEachChild(node, visit);
      return;
    }
    let functionName: string | null = null;
    if (ts.isIdentifier(node.expression)) {
      functionName = aliases.functions.get(node.expression.text) ?? null;
    } else if (
      ts.isPropertyAccessExpression(node.expression) ||
      ts.isElementAccessExpression(node.expression)
    ) {
      const member = node.expression;
      const receiver = expressionPath(member.expression);
      const name = ts.isPropertyAccessExpression(member)
        ? member.name.text
        : member.argumentExpression &&
            ts.isStringLiteralLike(member.argumentExpression)
          ? member.argumentExpression.text
          : null;
      if (receiver && aliases.objects.has(receiver)) {
        if (!name) {
          unclassifiableCall(
            importer,
            enclosingFunction(node) + ":" + receiver + ".[dynamic]",
            "UNKNOWN",
            "unknown",
          );
        }
        functionName = name;
      }
    }
    if (functionName) {
      for (const serviceCall of callsByFunction.get(functionName) ?? []) {
        result.push({
          ...serviceCall,
          importer: safeImporter(importer),
          call:
            node.expression.getText(sourceFile).slice(0, 80) +
            " -> " +
            serviceCall.call,
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

const externalMutationOperations = [
  "CREATE",
  "UPLOAD",
  "WRITE",
  "OVERWRITE",
  "RENAME",
  "MOVE",
  "COPY",
  "DELETE",
  "EXTRACT",
  "PATCH",
  "MKDIR",
  "SIDECAR_WRITE",
  "COVER_WRITE",
] as const;

const reviewedMutationRoutes = [
  /^\/activity\/heartbeat$/,
  /^\/auth\/device\/(?:approve|deny)$/,
  /^\/(?:login|logout|forgot-password|reset-password)$/,
  /^\/client-tokens(?:\/|$)/,
  /^\/collections(?:\/|$)/,
  /^\/config\/(?:system|exclude|scan)(?:\/|$)/,
  /^\/firmware\/delete$/,
  /^\/permissions(?:\/|$)/,
  /^\/platforms\/\{[^}]+\}$/,
  /^\/play-sessions$/,
  /^\/roms\/remove-from-catalog$/,
  /^\/roms\/\{[^}]+\}$/,
  /^\/roms\/\{[^}]+\}\/(?:manuals|notes|props)(?:\/|\{|$)/,
  /^\/saves(?:\/|$)/,
  /^\/screenshots(?:\/|$)/,
  /^\/states(?:\/|$)/,
  /^\/streaming\/sessions(?:\/|$)/,
  /^\/tasks\/run\/\{[^}]+\}$/,
  /^\/users(?:\/|$)/,
] as const;

function importedServicePaths(source: string): string[] {
  const paths = new Set<string>();
  for (const match of source.matchAll(
    /from\s+["']@\/services\/api\/([^"']+)["']/g,
  )) {
    paths.add(resolve(serviceRoot, match[1] + ".ts"));
  }
  return [...paths];
}

function reachableServicePaths(): string[] {
  const pending = v2Files().flatMap((path) =>
    importedServicePaths(readFileSync(path, "utf8")),
  );
  const visited = new Set<string>();
  while (pending.length) {
    const path = pending.pop();
    if (!path || visited.has(path) || !statSync(path).isFile()) continue;
    visited.add(path);
    pending.push(...importedServicePaths(readFileSync(path, "utf8")));
  }
  return [...visited].sort();
}

function payloadCapabilities(source: string): string[] {
  const capabilities: string[] = [];
  if (/[.\s]fs_name\b/.test(source) || /["']fs_name["']\s*,/.test(source)) {
    capabilities.push("fs_name");
  }
  for (const capability of [
    "delete_from_fs",
    "artwork",
    "manual",
    "screenshot",
    "save",
    "state",
    "patch_file",
  ]) {
    if (new RegExp("\\b" + capability + "\\b").test(source)) {
      capabilities.push(capability);
    }
  }
  return capabilities;
}

function finalAuthority(call: RawCall, source: string): Authority {
  const functionName = call.call.split(":", 1)[0];
  const marker = "function " + functionName;
  const start = source.indexOf(marker);
  let authoritySource = source;
  if (start >= 0) {
    const candidates = [
      source.indexOf("\nasync function ", start + marker.length),
      source.indexOf("\nfunction ", start + marker.length),
      source.indexOf("\nexport default", start + marker.length),
    ].filter((index) => index >= 0);
    const end = candidates.length ? Math.min(...candidates) : source.length;
    authoritySource = source.slice(start, end);
  }
  const fixedRoute = routeAuthorities.find(
    (entry) => entry.method === call.method && entry.route.test(call.route),
  );
  if (fixedRoute) {
    return {
      ...call,
      operation: fixedRoute.operation,
      storageClass: fixedRoute.storageClass,
      forbidden: fixedRoute.forbidden,
    };
  }
  const capabilities = payloadCapabilities(authoritySource);
  if (call.method === "GET" || call.method === "HEAD") {
    return {
      ...call,
      operation: "READ",
      storageClass: "database",
      forbidden: false,
    };
  }
  if (
    call.method === "PUT" &&
    /^\/roms\/\{[^}]+\}$/.test(call.route) &&
    capabilities.includes("fs_name")
  ) {
    return {
      ...call,
      operation: "RENAME",
      storageClass: "external_read_only",
      forbidden: true,
    };
  }
  if (
    call.route === "/firmware/delete" &&
    capabilities.includes("delete_from_fs")
  ) {
    return {
      ...call,
      operation: "DELETE",
      storageClass: "external_read_only",
      forbidden: true,
    };
  }
  if (call.method === "POST" && /^\/roms\/\{[^}]+\}\/patch$/.test(call.route)) {
    return {
      ...call,
      operation: "READ(external)+PATCH",
      storageClass: "assets",
      forbidden: false,
    };
  }
  if (
    /^\/(?:saves|states|screenshots)(?:\/|$)/.test(call.route) ||
    /^\/roms\/\{[^}]+\}\/manuals(?:\/|$)/.test(call.route)
  ) {
    return {
      ...call,
      operation: call.method === "DELETE" ? "DELETE" : "WRITE",
      storageClass: call.route.startsWith("/roms/") ? "resources" : "assets",
      forbidden: false,
    };
  }
  if (!reviewedMutationRoutes.some((route) => route.test(call.route))) {
    throw new Error(
      "unclassified authority importer=" +
        call.importer +
        " call=" +
        call.call +
        " method=" +
        call.method +
        " route=" +
        call.route +
        " payload=" +
        (capabilities.join(",") || "none") +
        " operation=UNKNOWN storage=unknown",
    );
  }
  return {
    ...call,
    operation: "CONTROL_PLANE",
    storageClass: "database",
    forbidden: false,
  };
}

function finalInventorySource(
  source: string,
  importer: string,
  callsByFunction = new Map<string, RawCall[]>(),
): Authority[] {
  return inventorySource(source, importer, callsByFunction).map((call) =>
    finalAuthority(call, source),
  );
}

describe("final active v2 semantic mutation closure", () => {
  it("inventories every production v2 module and reachable API service", () => {
    const servicePaths = reachableServicePaths();
    expect(
      servicePaths.map((path) => path.slice(serviceRoot.length + 1)),
    ).toEqual(
      expect.arrayContaining([
        "client-token.ts",
        "firmware.ts",
        "rom.ts",
        "save.ts",
        "screenshot.ts",
        "state.ts",
      ]),
    );

    const inventory = [
      ...v2Files().flatMap((path) => {
        const source = readFileSync(path, "utf8");
        return extractRawCalls(
          source,
          path.slice(resolve(process.cwd(), "src").length + 1),
        ).map((call) => finalAuthority(call, source));
      }),
      ...servicePaths.flatMap((path) => {
        const source = readFileSync(path, "utf8");
        return extractRawCalls(
          source,
          path.slice(resolve(process.cwd(), "src").length + 1),
        ).map((call) => finalAuthority(call, source));
      }),
    ];
    const violations = inventory
      .filter((authority) => authority.forbidden)
      .map(
        (authority) =>
          authority.importer +
          " | " +
          authority.call +
          " | " +
          authority.method +
          " " +
          authority.route +
          " | " +
          authority.operation +
          " | " +
          authority.storageClass,
      );
    expect(violations).toEqual([]);
  });

  it("binds the complete external operation family and typed descriptors to live backend definitions", () => {
    const policy = readFileSync(
      resolve(repositoryRoot, "backend/handler/filesystem/storage_policy.py"),
      "utf8",
    );
    for (const operation of externalMutationOperations) {
      expect(policy).toMatch(new RegExp("^\\s*" + operation + "\\s*=", "m"));
      const readSet =
        policy.match(
          /EXTERNAL_READ_OPERATIONS\s*=\s*frozenset\(([\s\S]*?)\n\)/,
        )?.[1] ?? "";
      expect(readSet).not.toContain("StorageOperation." + operation);
    }
    for (const kind of [
      "DATABASE",
      "RESOURCES",
      "ASSETS",
      "CONFIG",
      "CACHE",
      "HASHES",
      "SCAN_STATE",
      "TEMP",
      "SYNC",
      "AUDIT",
    ]) {
      expect(policy).toMatch(new RegExp("^\\s*" + kind + "\\s*=", "m"));
    }
  });

  it("classifies patch, owned mutations, and database control-plane routes from live registrations", () => {
    const patchRoute = readFileSync(
      resolve(repositoryRoot, "backend/endpoints/roms/patch.py"),
      "utf8",
    );
    const romRoutes = readFileSync(
      resolve(repositoryRoot, "backend/endpoints/roms/__init__.py"),
      "utf8",
    );
    expect(patchRoute).toContain('"/{id}/patch"');
    expect(patchRoute).toContain(
      "StorageOperation.READ, legacy_external_storage",
    );
    expect(patchRoute).toContain("OwnedStorageKind.TEMP");
    expect(romRoutes).toContain("router.include_router(patch_router)");
    expect(romRoutes).toContain('router.put,\n    "/{id}"');
  });

  it("keeps generic-client stats, token, and log consumers source-neutral", () => {
    for (const importer of [
      "v2/components/Home/Widgets/LibraryStatsWidget.vue",
      "v2/views/Settings/ServerStats.vue",
      "v2/views/Settings/ClientApiTokens.vue",
      "v2/views/Settings/Logs.vue",
    ]) {
      const path = resolve(process.cwd(), "src", importer);
      const source = readFileSync(path, "utf8");
      const authorities = extractRawCalls(source, importer).map((call) =>
        finalAuthority(call, source),
      );
      expect(authorities.every((authority) => !authority.forbidden)).toBe(true);
    }
  });

  it("fails closed for string element access before classification", () => {
    const authorities = finalInventorySource(
      `
        import api from "@/services/api";
        api["delete"]("/roms/" + romId + "/files/" + fileId);
      `,
      "element-access-negative.ts",
    );
    expect(
      authorities,
      "RED: string element access must reach inventory classification",
    ).toMatchObject([
      {
        method: "DELETE",
        route: "/roms/{rom_id}/files/{file_id}",
        operation: "DELETE",
        storageClass: "external_read_only",
        forbidden: true,
      },
    ]);
  });

  it("normalizes const aliases and concatenated routes through inventory", () => {
    expect(
      finalInventorySource(
        `
          import api from "@/services/api";
          const prefix = "/roms/";
          const route = prefix + romId + "/files/" + fileId;
          api.delete(route);
        `,
        "const-route-negative.ts",
      ),
    ).toMatchObject([
      {
        route: "/roms/{rom_id}/files/{file_id}",
        operation: "DELETE",
        storageClass: "external_read_only",
        forbidden: true,
      },
    ]);
  });

  it("discovers default, named, aliased, namespace, and nested clients", () => {
    const authorities = finalInventorySource(
      `
        import defaultClient from "@/services/api";
        import { default as namedClient } from "@/services/api";
        import * as apiNamespace from "@/services/api";
        const alias = defaultClient;
        const nested = apiNamespace.default;
        defaultClient.get("/heartbeat");
        namedClient.head("/heartbeat");
        alias.post("/collections", {});
        apiNamespace.default.get("/heartbeat");
        nested.post("/collections", {});
      `,
      "client-imports-positive.ts",
    );
    expect(authorities).toHaveLength(5);
    expect(authorities.every((authority) => !authority.forbidden)).toBe(true);
  });

  it("discovers named, aliased, namespace, and nested shared-service calls", () => {
    const callsByFunction = serviceCalls(`
      import api from "@/services/api";
      function deleteSourceFile(romId: number, fileId: number) {
        return api.delete("/roms/" + romId + "/files/" + fileId);
      }
    `);
    const consumers = [
      `import romService from "@/services/api/rom";
        const alias = romService; alias.deleteSourceFile(1, 2);`,
      `import { deleteSourceFile as removeFile } from "@/services/api/rom";
        removeFile(1, 2);`,
      `import * as romNamespace from "@/services/api/rom";
        romNamespace.deleteSourceFile(1, 2);`,
      `import * as romNamespace from "@/services/api/rom";
        romNamespace.default.deleteSourceFile(1, 2);`,
    ];
    for (const [index, source] of consumers.entries()) {
      expect(
        inventorySource(source, `service-${index}.ts`, callsByFunction),
      ).toMatchObject([
        { forbidden: true, storageClass: "external_read_only" },
      ]);
    }
  });

  it("fails closed with bounded diagnostics for unresolved known-client forms", () => {
    const fixtures = [
      {
        importer: "dynamic-method.ts",
        source:
          'import api from "@/services/api"; api[method]("/roms/1/files/2");',
        method: "UNKNOWN",
      },
      {
        importer: "mutable-route.ts",
        source:
          'import api from "@/services/api"; let route = "/roms/1/files/2"; api.delete(route);',
        method: "DELETE",
      },
      {
        importer: "unsupported-receiver.ts",
        source:
          'import api from "@/services/api"; (enabled ? api : fallback).delete("/roms/1/files/2");',
        method: "DELETE",
      },
      {
        importer: "non-reducible-route.ts",
        source:
          'import api from "@/services/api"; api.delete("/roms/" + routePart());',
        method: "DELETE",
      },
    ];
    for (const fixture of fixtures) {
      expect(() =>
        finalInventorySource(fixture.source, fixture.importer),
      ).toThrow(`unclassifiable call importer=${fixture.importer} call=`);
      try {
        finalInventorySource(fixture.source, fixture.importer);
      } catch (error) {
        const diagnostic = String(error);
        expect(diagnostic).toContain(`method=${fixture.method}`);
        expect(diagnostic).toContain("operation=UNKNOWN storage=unknown");
        expect(diagnostic).not.toMatch(/\/home\/|\/romm\/library|[A-Z]:\\\\/);
        expect(diagnostic.length).toBeLessThan(320);
      }
    }
  });

  it("routes each external mutation family through extraction", () => {
    for (const operation of externalMutationOperations) {
      const importer = `negative-${operation.toLowerCase()}.ts`;
      const source = `import api from "@/services/api";
        api.post("/external/${operation.toLowerCase()}", {});`;
      expect(() => finalInventorySource(source, importer)).toThrow(
        `unclassified authority importer=${importer} call=module:api.post method=POST route=/external/${operation.toLowerCase()} payload=none operation=UNKNOWN storage=unknown`,
      );
    }
  });

  it("keeps conditional rename and firmware payloads on the extraction path", () => {
    expect(
      finalInventorySource(
        `import api from "@/services/api";
          api["put"]("/roms/" + romId, { fs_name: nextName });`,
        "raw-put.ts",
      ),
    ).toMatchObject([
      {
        operation: "RENAME",
        storageClass: "external_read_only",
        forbidden: true,
      },
    ]);
    expect(
      finalInventorySource(
        `import api from "@/services/api";
          const payload = enabled ? { delete_from_fs: true } : {};
          api.post("/firmware/delete", payload);`,
        "conditional-delete.ts",
      ),
    ).toMatchObject([
      {
        operation: "DELETE",
        storageClass: "external_read_only",
        forbidden: true,
      },
    ]);
    expect(() =>
      finalInventorySource(
        `import api from "@/services/api";
          api.patch("/roms/" + romId + "/unknown", {});`,
        "unknown-negative.ts",
      ),
    ).toThrow(
      "unclassified authority importer=unknown-negative.ts call=module:api.patch method=PATCH route=/roms/{rom_id}/unknown payload=none operation=UNKNOWN storage=unknown",
    );
  });
});
