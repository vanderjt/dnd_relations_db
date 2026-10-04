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
  await copyFile(`assets/${name}`, `dist/${name}`);
for (const name of ["themes", "ornaments"])
  await cp(`assets/${name}`, `dist/${name}`, { recursive: true });
