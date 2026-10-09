import { build } from "esbuild";
import { copyFile, cp, mkdir, rename, rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const output = join(root, "dist");
const staging = join(root, ".dist-build");

// Build into a fresh folder. Reusing dist could ship assets that source cleanup
// removed; staging also preserves the last working UI when compilation fails.
await rm(staging, { recursive: true, force: true });
await mkdir(staging, { recursive: true });
try {
  await build({
    absWorkingDir: root,
    entryPoints: ["src/main.tsx"],
    bundle: true,
    minify: true,
    sourcemap: true,
    outfile: join(staging, "app.js"),
    external: ["./ornaments/*"],
  });
  await copyFile(join(root, "index.html"), join(staging, "index.html"));
  for (const name of ["studio.css", "refinements.css", "type.css"]) {
    await copyFile(join(root, "assets", name), join(staging, name));
  }
  for (const name of ["themes", "ornaments"]) {
    await cp(join(root, "assets", name), join(staging, name), {
      recursive: true,
    });
  }
  await rm(output, { recursive: true, force: true });
  await rename(staging, output);
} finally {
  await rm(staging, { recursive: true, force: true });
}
