/**
 * Build the standalone setup binaries with nomake.
 *
 *   deno run -A build.ts build     # -> dist/pp1-setup-{os}-{arch}
 *   deno run -A build.ts clean
 *
 * nomake is imported by URL (no installation needed); the `nomake` binary from
 * its releases runs the same file. `pp1-setup-*` is just `deno compile` of
 * scripts/onboard.ts, one target per platform.
 */

import * as NM from "https://github.com/thautwarm/nomake/raw/v0.1.12/mod.ts";

const DENO = Deno.execPath();

const TARGETS = [
  ["x86_64-unknown-linux-gnu", "linux-x64"],
  ["aarch64-unknown-linux-gnu", "linux-arm64"],
  ["x86_64-apple-darwin", "darwin-x64"],
  ["aarch64-apple-darwin", "darwin-arm64"],
  ["x86_64-pc-windows-msvc", "windows-x64.exe"],
] as const;

for (const [triple, name] of TARGETS) {
  NM.target({
    name: `dist/pp1-setup-${name}`,
    deps: { source: "scripts/onboard.ts" },
    async build({ deps, target }) {
      await NM.Shell.runChecked(
        [
          DENO,
          "compile",
          "--allow-all",
          "--target",
          triple,
          "--output",
          String(target),
          deps.source,
        ],
        { printCmd: true, logError: true },
      );
    },
  });
}

NM.target({
  name: "build",
  virtual: true,
  rebuild: "always",
  deps: TARGETS.map(([, name]) => `dist/pp1-setup-${name}`),
  build() {
    NM.Log.msg("setup binaries are in dist/");
  },
});

NM.target({
  name: "clean",
  virtual: true,
  rebuild: "always",
  async build() {
    await NM.Shell.run([DENO, "eval", "Deno.removeSync('dist', { recursive: true })"], {
      printCmd: true,
    }).catch(() => {});
  },
});

NM.makefile();
