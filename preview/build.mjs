import { build } from "esbuild";
import { mkdir, copyFile, cp } from "node:fs/promises";
await mkdir("dist", { recursive: true });
await build({
  entryPoints: ["src/main.tsx"],
  bundle: true,
  minify: true,
  sourcemap: true,
  outfile: "dist/app.js",
  external: ["./ornaments/*"],
});
await copyFile("index.html", "dist/index.html");
for (const name of ["studio.css", "refinements.css", "type.css"])
  await copyFile(`../prototypes/phase2/${name}`, `dist/${name}`);
for (const name of ["themes", "ornaments"])
  await cp(`../prototypes/phase2/${name}`, `dist/${name}`, { recursive: true });
