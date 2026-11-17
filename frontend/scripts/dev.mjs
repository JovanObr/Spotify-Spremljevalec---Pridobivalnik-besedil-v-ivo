// npm run dev: starts the Python API (python -m api) and the Vite dev server
// together in one window, with each line labelled. Ctrl+C stops both, and if
// one of them stops, the other is stopped too.
//
// The Python from the project's .venv is used when it exists; set PYTHON to
// use another one. To start only the frontend: npm run dev:web

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createInterface } from "node:readline";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const projectDir = resolve(frontendDir, "..");
const isWindows = process.platform === "win32";

function findPython() {
  if (process.env.PYTHON) return process.env.PYTHON;
  const venv = isWindows
    ? join(projectDir, ".venv", "Scripts", "python.exe")
    : join(projectDir, ".venv", "bin", "python");
  if (existsSync(venv)) return venv;
  return isWindows ? "python" : "python3";
}

const colors = { api: "\x1b[36m", web: "\x1b[35m" };
const reset = "\x1b[0m";
const children = [];
let stopping = false;

function run(name, command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, PYTHONUNBUFFERED: "1", FORCE_COLOR: "1" },
    stdio: ["inherit", "pipe", "pipe"],
  });
  const label = `${colors[name]}[${name}]${reset} `;
  for (const stream of [child.stdout, child.stderr]) {
    createInterface({ input: stream }).on("line", (line) => console.log(label + line));
  }
  child.on("error", (error) => {
    console.log(`${label}could not start "${command}": ${error.message}`);
    if (name === "api") console.log(`${label}set PYTHON to your Python, or create the .venv (see README).`);
    stopAll(1);
  });
  child.on("exit", (code) => {
    if (!stopping) {
      console.log(`${label}stopped${code ? ` (exit code ${code})` : ""}; stopping the other one too.`);
      stopAll(code ?? 0);
    }
  });
  children.push(child);
}

function stopAll(code) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode === null) child.kill();
  }
  setTimeout(() => process.exit(code), 300);
}

process.on("SIGINT", () => stopAll(0));
process.on("SIGTERM", () => stopAll(0));

const python = findPython();
console.log(`Starting the API (${python} -m api) and the frontend (Vite).`);
console.log("Open http://127.0.0.1:5173 once both are ready. Ctrl+C stops both.\n");

run("api", python, ["-m", "api"], projectDir);
run("web", process.execPath, [join(frontendDir, "node_modules", "vite", "bin", "vite.js")], frontendDir);
