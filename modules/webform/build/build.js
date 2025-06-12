const esbuild = require("esbuild");
const path = require("path");

const MODULE_DIR = path.resolve(__dirname, "..");
const DIST_DIR = path.join(__dirname, "dist");

esbuild.build({
  entryPoints: [
    path.join(__dirname, "webform_bundle.jsx"),
    path.join(__dirname, "Wizard.jsx")
  ],
  bundle: true,
  format: "esm",
  target: "esnext",
  outdir: DIST_DIR,              
  entryNames: "[name]",          
  jsx: "transform",
  loader: {
    ".js": "jsx",
    ".jsx": "jsx",
    ".svg": "file"               
  },
  sourcemap: false,
  minify: false
}).then(() => {
  console.log("✅ Build complete. Output in:", DIST_DIR);
}).catch((err) => {
  console.error("❌ Build failed:", err);
  process.exit(1);
});
