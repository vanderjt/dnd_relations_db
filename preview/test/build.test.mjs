import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { copyFile, cp, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const output = join(root, "dist");

async function snapshot(folder = output) {
  const result = {};
  for (const entry of await readdir(folder, { withFileTypes: true })) {
    const path = join(folder, entry.name);
    if (entry.isDirectory()) Object.assign(result, await snapshot(path));
    else {
      result[relative(output, path)] = createHash("sha256")
        .update(await readFile(path))
        .digest("hex");
    }
  }
  return result;
}

function build() {
  // Use a different cwd to prove build paths are anchored to this script.
  execFileSync(process.execPath, [join(root, "build.mjs")], {
    cwd: dirname(root),
    stdio: "pipe",
  });
}

test("repeated builds remove stale output and reproduce the same files", async () => {
  build();
  const expected = await snapshot();
  for (const name of ["app.js", "app.css", "index.html", "studio.css"]) {
    assert.ok(expected[name], `Missing runtime asset ${name}`);
  }
  await mkdir(join(output, "legacy"), { recursive: true });
  await writeFile(join(output, "legacy", "removed-prototype.js"), "stale");
  await writeFile(join(output, "themes", "removed-theme.css"), "stale");
  build();
  assert.deepEqual(await snapshot(), expected);
});


test("a failed build keeps the last working output and removes staging", async () => {
  // A disposable project under preview can resolve the already installed
  // esbuild dependency without touching the real application source.
  const fixture = await mkdtemp(join(root, ".build-test-"));
  try {
    await copyFile(join(root, "build.mjs"), join(fixture, "build.mjs"));
    await copyFile(join(root, "index.html"), join(fixture, "index.html"));
    await cp(join(root, "assets"), join(fixture, "assets"), { recursive: true });
    await mkdir(join(fixture, "src"));
    await writeFile(join(fixture, "src/main.tsx"), 'console.log("working");');
    execFileSync(process.execPath, [join(fixture, "build.mjs")]);
    const working = await readFile(join(fixture, "dist/app.js"));
    await writeFile(join(fixture, "src/main.tsx"), "this is not valid TypeScript {{");
    assert.throws(() =>
      execFileSync(process.execPath, [join(fixture, "build.mjs")], { stdio: "pipe" }),
    );
    assert.deepEqual(await readFile(join(fixture, "dist/app.js")), working);
    await assert.rejects(readdir(join(fixture, ".dist-build")), { code: "ENOENT" });
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
});
