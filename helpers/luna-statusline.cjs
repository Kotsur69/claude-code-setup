#!/usr/bin/env node
/**
 * LunaCore â€” statusline / mini-dashboard for Claude Code.
 *
 * Standalone, zero-dependency, cross-platform. Reads the JSON Claude Code pipes
 * to a statusLine command on stdin and renders (matching the "LunaCore // dash"
 * design â€” dark mono, cyanâ†’magenta):
 *
 *   line 0  <model> â€˘ <ctx%> â€˘ <elapsed> â€˘ <mcp> â€˘ $<cost>     â”
 *   line 1  â—Ź <60 send it   â—Ź 60-85 compact maybe?  â—Ź >85 â€¦    â”‚  big "LunaCore"
 *   line 2  cheat â†’ Ctrl+]  Â·  LunaCore // dash                â”‚  block wordmark
 *   line 3  solo Â· lean Â· v1                                   â”‚  on the right
 *   line 4  (spacer)                                           â”
 *
 * The three context LEDs are a legend: the CURRENT zone is bright, the others
 * dimmed. Zones: green <60%, amber 60â€“85%, red >85% (the "compact this shit"
 * zone). It never shells out to a CLI â€” ctx% is computed from the transcript,
 * MCP count from local config.
 *
 * Env overrides:
 *   LUNA_SL_ART=0            hide the big LunaCore wordmark (compact mode)
 *   LUNA_SL_HIDE_COST=1      hide the cost segment
 *   LUNA_SL_COST_SYMBOL=$    change the cost symbol (e.g. âšˇ, â‚¬)
 *   LUNA_SL_CTX_LIMIT=200000 context window size used for the % (default 200000)
 *   LUNA_SL_CTX_WARN=60      amber threshold (default 60)
 *   LUNA_SL_CTX_DANGER=85    red / "compact this shit" threshold (default 85)
 *   LUNA_SL_CHEAT_URL=...    cheatsheet link shown on the hint line
 *   LUNA_SL_NOCOLOR=1        disable ANSI colors
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

// â”€â”€ config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const CTX_LIMIT = Number(process.env.LUNA_SL_CTX_LIMIT || 200000);
const CTX_WARN = Number(process.env.LUNA_SL_CTX_WARN || 60);
const CTX_DANGER = Number(process.env.LUNA_SL_CTX_DANGER || 85);
const SHOW_ART = !/^(0|false|no|off)$/i.test(process.env.LUNA_SL_ART || '');
const CHEAT_URL =
  process.env.LUNA_SL_CHEAT_URL ||
  'file:///C:/Users/mmazur/.claude/helpers/ecc-sciagawka-mati.html';

// â”€â”€ ANSI helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const NOCOLOR = /^(1|true|yes|on)$/i.test(process.env.LUNA_SL_NOCOLOR || '');
const c = (code, s) => (NOCOLOR ? s : `\x1b[${code}m${s}\x1b[0m`);
const cyan = (s) => c('96', s);    // Luna / model â€” bright cyan
const magenta = (s) => c('95', s); // Core / elapsed â€” bright magenta
const green = (s) => c('92', s);   // ctx ok / cost
const yellow = (s) => c('93', s);  // ctx warn
const red = (s) => c('91', s);     // ctx danger
const blue = (s) => c('94', s);    // mcp
const gray = (s) => c('90', s);    // separators / dimmed
const bold = (s) => c('1', s);
const sep = gray('  \u2022  ');
const stripAnsi = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');
// Hard-truncate a possibly-ANSI-colored string to at most `maxVisible` visible
// chars, copying escape codes through uncounted. This is the safety net that
// guarantees a left-column line can never push the total printed width past
// the art's start column â€” which is what was wrapping the wordmark.
function truncateVisible(s, maxVisible) {
  if (maxVisible <= 0) return '';
  if (stripAnsi(s).length <= maxVisible) return s;
  let out = '';
  let visible = 0;
  for (let i = 0; i < s.length; i++) {
    if (s[i] === '\x1b') {
      const m = /^\x1b\[[0-9;]*m/.exec(s.slice(i));
      if (m) { out += m[0]; i += m[0].length - 1; continue; }
    }
    if (visible >= maxVisible - 1) { out += '\u2026'; visible++; break; }
    out += s[i];
    visible++;
  }
  return out + (NOCOLOR ? '' : '\x1b[0m');
}
// Real available terminal width. Claude Code v2.1.153+ sets COLUMNS/LINES to
// the actual render-pane width before running the statusLine command â€” this
// is authoritative (correct even over SSH/tmux/split panes) and MUST win over
// anything else. process.stdout.columns is unset when Claude Code pipes our
// stdout (not a TTY); `mode con` queries the raw Windows console buffer,
// which can differ from the pane Claude Code actually renders into, so it's
// now only a last-resort fallback.
function getCols() {
  const envCols = Number(process.env.COLUMNS);
  if (envCols > 0) return envCols;
  if (process.stdout.columns) return process.stdout.columns;
  if (process.platform === 'win32') {
    try {
      const out = execSync('mode con', { timeout: 300, windowsHide: true }).toString();
      const m = /Columns:\s*(\d+)/i.exec(out);
      if (m) return Number(m[1]);
    } catch (_) { /* no console attached / mode unavailable */ }
  }
  return 80;
}

// â”€â”€ read stdin JSON (best-effort) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function readStdin() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {};
  }
}

// â”€â”€ ctx% from the session transcript â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Claude Code writes the session as JSONL at data.transcript_path. The last
// message carrying a usage block tells us how many tokens are currently in the
// context window. We tail the file so large sessions stay cheap. Returns 0 when
// the session is fresh (no usage yet) so the green LED still shows.
function contextPct(data) {
  const tp = data.transcript_path;
  try {
    if (!tp || !fs.existsSync(tp)) {
      if (data.exceeds_200k_tokens) return 100;
      return 0;
    }
    const stat = fs.statSync(tp);
    const readBytes = Math.min(stat.size, 262144); // last 256 KB
    const fd = fs.openSync(tp, 'r');
    const buf = Buffer.alloc(readBytes);
    fs.readSync(fd, buf, 0, readBytes, stat.size - readBytes);
    fs.closeSync(fd);
    const lines = buf.toString('utf8').split('\n').filter(Boolean);
    for (let i = lines.length - 1; i >= 0; i--) {
      let obj;
      try { obj = JSON.parse(lines[i]); } catch (_) { continue; }
      const u = (obj.message && obj.message.usage) || obj.usage;
      if (u && (u.input_tokens != null || u.cache_read_input_tokens != null)) {
        const used =
          (u.input_tokens || 0) +
          (u.cache_read_input_tokens || 0) +
          (u.cache_creation_input_tokens || 0);
        return Math.min(100, Math.round((used / CTX_LIMIT) * 100));
      }
    }
  } catch (_) { /* ignore */ }
  return 0;
}

// â”€â”€ MCP status from local config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Native stdin carries no live MCP handshake state, so we report the number of
// MCP servers actually wired up: user (~/.claude.json) + project (.mcp.json) +
// every ENABLED plugin's own .mcp.json (disabled plugins skipped, so a turned-
// off ruflo no longer counts). Deduped by name, cached 30s.
function readJSON(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return null; }
}
function mcpStatus() {
  const cacheFile = path.join(os.tmpdir(), 'luna-sl-mcp.json');
  try {
    const st = fs.statSync(cacheFile);
    if (Date.now() - st.mtimeMs < 30000) return readJSON(cacheFile).count;
  } catch (_) { /* stale/missing â†’ recompute */ }

  const home = os.homedir();
  const names = new Set();
  const add = (o) => { if (o && typeof o === 'object') Object.keys(o).forEach((k) => names.add(k)); };

  const uj = readJSON(path.join(home, '.claude.json'));
  if (uj) add(uj.mcpServers);
  const pj = readJSON(path.join(process.cwd(), '.mcp.json'));
  if (pj) add(pj.mcpServers);

  const settings = readJSON(path.join(home, '.claude', 'settings.json')) || {};
  const enabled = settings.enabledPlugins || {};
  const installed = readJSON(path.join(home, '.claude', 'plugins', 'installed_plugins.json'));
  if (installed && installed.plugins) {
    for (const pname of Object.keys(installed.plugins)) {
      if (enabled[pname] === false) continue; // skip disabled plugins (e.g. ruflo)
      for (const inst of installed.plugins[pname]) {
        if (!inst || !inst.installPath) continue;
        const mj = readJSON(path.join(inst.installPath, '.mcp.json'));
        if (mj) add(mj.mcpServers);
      }
    }
  }

  const count = names.size;
  try { fs.writeFileSync(cacheFile, JSON.stringify({ count, names: [...names] })); } catch (_) {}
  return count;
}

// â”€â”€ formatting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function fmtDuration(ms) {
  if (!ms || ms < 0) return null;
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h) return `${h}h${String(m).padStart(2, '0')}m`;
  if (m) return `${m}m${String(sec).padStart(2, '0')}s`;
  return `${sec}s`;
}

function ctxZone(pct) {
  if (pct > CTX_DANGER) return 'r';
  if (pct >= CTX_WARN) return 'y';
  return 'g';
}
const ZONE_COLOR = { g: green, y: yellow, r: red };

// -- right-aligned wordmark -----------------------------------------------
function gradientText(text) {
  const start = [90, 220, 230];
  const end = [215, 0, 190];
  const width = Math.max(1, text.length - 1);
  let out = '';
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const t = i / width;
    const r = Math.round(start[0] + (end[0] - start[0]) * t);
    const g = Math.round(start[1] + (end[1] - start[1]) * t);
    const b = Math.round(start[2] + (end[2] - start[2]) * t);
    out += NOCOLOR ? ch : `\x1b[1;38;2;${r};${g};${b}m${ch}`;
  }
  return out + (NOCOLOR ? '' : '\x1b[0m');
}
function wordmark() {
  return gradientText('LUNACORE');
}

function main() {
  const data = readStdin();

// â”€â”€ left column â”€â”€
  const model =
    (data.model && (data.model.display_name || data.model.id)) || 'claude';
  const pct = contextPct(data);
  const zone = ctxZone(pct);
  const dur = fmtDuration(data.cost && data.cost.total_duration_ms);
  const mcp = mcpStatus();

  // line 0 â€” mini dashboard
  const d0 = [];
  d0.push(cyan(model));
  d0.push(ZONE_COLOR[zone](`\u25CF ${pct}% ctx`));
  if (dur) d0.push(magenta(dur));
  d0.push((mcp > 0 ? green('\u25CF') : gray('\u25CF')) + blue(` mcp ${mcp}`));
  const hideCost = /^(1|true|yes|on)$/i.test(process.env.LUNA_SL_HIDE_COST || '');
  if (!hideCost && data.cost && typeof data.cost.total_cost_usd === 'number') {
    const sym = process.env.LUNA_SL_COST_SYMBOL ?? '$';
    d0.push(green(`${sym}${data.cost.total_cost_usd.toFixed(2)}`));
  }
  const line0 = d0.join(sep);

  // line 1 â€” context LED legend (current zone bright, others dimmed).
  // Two label sets: full text when there's room next to the art, a compact
  // one when the panel is narrow â€” chosen once we know the real budget below.
  const led = (z, label, color) => {
    const txt = z === zone ? bold(color(label)) : gray(label);
    return (z === zone ? color('\u25CF') : gray('\u25CF')) + ' ' + txt;
  };
  const buildLine1 = (labels) =>
    led('g', labels.g, green) + '   ' +
    led('y', labels.y, yellow) + '   ' +
    led('r', labels.r, red);
  const LEGEND_FULL = {
    g: `<${CTX_WARN} send it`,
    y: `${CTX_WARN}-${CTX_DANGER} compact maybe?`,
    r: `>${CTX_DANGER} compact this shit`,
  };
  const LEGEND_COMPACT = {
    g: `<${CTX_WARN} ok`,
    y: `${CTX_WARN}-${CTX_DANGER}`,
    r: `>${CTX_DANGER} !!`,
  };

  // line 2 - cheatsheet hint. No keybinding opens this (ctrl+] is already
  // Claude Code's own "open last artifact" shortcut) - it's just the link.
  const line2 = magenta('cheat \u2192 ') + cyan(CHEAT_URL);

  // Right-aligning the wordmark next to the dashboard text turned out too
  // fragile across terminal widths/panes, so it's now just its own
  // left-aligned line under everything else - simple and always lands
  // in the same place.
  const cols = Math.max(1, getCols() - 1);
  const line1Full = buildLine1(LEGEND_FULL);
  const line1 = stripAnsi(line1Full).length <= cols ? line1Full : buildLine1(LEGEND_COMPACT);
  const rows = [line0, line1, line2].map((s) => truncateVisible(s, cols));

  if (SHOW_ART) rows.push(truncateVisible(wordmark(), cols));

  process.stdout.write(rows.join('\n'));
}

main();
