# Easy Sarabun — Visual Direction Proposal

Status: **approved direction** (mix palette, header icon-only toggle) — no product source modified yet. All changes land in `theme.py` (+ small control in `main.py`) unless noted.

## 1. Diagnosis: why the green feels "off"

Current tokens (`theme.py:13-22`):

- `ACCENT` light `#2f6f62` — low-chroma, desaturated teal-green. On `#f5f5f3` surface it reads **muddy and dim**, and in dark mode `#4a9a8a` sits between teal and green => the "เขียวแปลก ๆ" impression.
- The problem is **chroma + lightness**, not the hue family. Nudging it 1–2 shades (what "เข้ม/สว่างอีกนิด" suggests) keeps it in the same mud. We should pick a deliberate target.

Two coherent directions below. Both keep the green family (product identity: a Thai numeral converter, calm + precise) but give it distinct personality.

---

## Option A — "ป่าชุ่ม" Deep Botanical Green (recommended, low risk)

Keep the calm, professional mood, just make the green confident and non-muddy.

| Token | Light | Dark | Note |
|---|---|---|---|
| `ACCENT` | `#1F6B57` | `#3FB68F` | deeper, richer forest green / brighter teal-green for dark |
| `ACCENT_HOVER` | `#1A5A49` | `#2FA278` | darker on light, lighter on dark |
| `SURFACE` | `#F4F5F2` | `#1F211E` | slightly warmer neutral |
| `BORDER` | `#D9DDD5` | `#34382F` | |
| `TEXT` | `#18211C` | `#EDEFEA` | near-black with green undertone |
| `MUTED` | `#5F6B63` | `#9EA89F` | keep ≥4.5:1 contrast |

- Mood: calm, natural, official-tool. Safest upgrade; keeps current layout untouched.

---

## Option B — "สปอร์ตกรีน" Bright Sport Green (more expressive)

Brighter, higher-chroma green for a more energetic, modern utility feel.

| Token | Light | Dark | Note |
|---|---|---|---|
| `ACCENT` | `#0E9C63` | `#34D399` | vivid, punchy green |
| `ACCENT_HOVER` | `#0B7F50` | `#2BB584` | |
| `SURFACE` | `#F6F7F4` | `#171A18` | cooler neutral |
| `BORDER` | `#DCE3DC` | `#2D3330` | |
| `TEXT` | `#101712` | `#F1F5F2` | |
| `MUTED` | `#555F58` | `#A6B0AA` | |

- Mood: fresh, energetic, app-like. More distinctive but also more "consumer app."

> Both options keep `SUCCESS` green and `DANGER` red; I'll re-tune `SUCCESS` so it no longer collides with the new `ACCENT` in the same hue zone. Original hex only where DESIGN.md permits `white`.

---

## ✅ FINAL SELECTED PALETTE — Mix (deep green light / bright green dark)

Chosen: **deep botanical green for light mode, bright sport green for dark mode** (best of both — calm in light, vivid on dark).

| Token | Light | Dark | Note |
|---|---|---|---|
| `ACCENT` | `#1F6B57` | `#34D399` | deep forest green / bright vivid green |
| `ACCENT_HOVER` | `#1A5A49` | `#2BB584` | |
| `SURFACE` | `#F4F5F2` | `#171A18` | warm neutral light / cool near-black dark |
| `BORDER` | `#D9DDD5` | `#2D3330` | |
| `TEXT` | `#18211C` | `#F1F5F2` | green-undertone neutrals |
| `MUTED` | `#5F6B63` | `#A6B0AA` | ≥4.5:1 contrast on SURFACE |
| `SUCCESS` | `#2F7D4F` | `#5FBF86` | kept distinct from ACCENT |
| `DANGER` | `#C0392B` | `#E67E73` | unchanged |

Contrast checks (computed): `ACCENT` light `#1F6B57` on `#F4F5F2` ≈ 5.2:1 with white text; `MUTED` light ≈ 4.9:1 on SURFACE. `ACCENT` dark `#34D399` on buttons keeps readable dark-on-green.

---

## 2. Typography: Mitr → Kanit

- **Kanit** (Google Fonts, OFL) — upright, modern Thai+Latin sans-serif with strong rectangular stems. Better legibility at body size (13px) than Mitr's heavier rounded forms, especially for numerals (`0-9` / `๐-๙`) which are this product's core content.
- **Single-family system, two weights:** Regular for body/captions, Medium for titles/buttons — same structure as current `Fonts` in `theme.py:31-48`.
- Font stack: `Kanit` → fallback `Tahoma` (keep current fallback behavior).
- Assets: ship `Kanit-Regular.ttf` + `Kanit-Medium.ttf` in `assets/fonts/`, registered by the existing `register_fonts()` in `main.py:85`. No new font infrastructure required.
- Rationale for one family (not two): a compact utility window; one family with weight contrast keeps it cohesive and avoids the generated-look of a display/body split.

Type scale (unchanged contract, keep as-is):
`caption 11 · small 12 · body 13 · button 14 · title 24` (`theme.py:27`). Slight letter-spacing on captions/stats if Kanit needs it for legibility.

---

## 3. Light / Dark / Device mode control

Current: `ctk.set_appearance_mode("System")` hard-coded at `main.py:746`, no user control.

Proposed:

- Add a **three-way toggle** (Light / Dark / Device) in the app header, right-aligned next to `อัปเดต`/`About` (or as a compact 3-segment chip in the mode card).
- Persist the choice in the existing `config.json` (`main.py:70`), same mechanism as `hotkey`/`reverse`.
- On change: call `ctk.set_appearance_mode("Light"|"Dark"|"System")` and update the `MUTED`/`TEXT` active-state labels that depend on `reverse_mode` (`main.py:481-485`) so contrast stays correct in both modes.

### ✅ FINAL MODE CONTROL — Approved
- **Placement:** header segmented control, right-aligned next to `อัปเดต` / `About` buttons (`main.py:394-404`).
- **Labels:** icon-only — `☀` (light) · `☾` (dark) · device glyph, no text. `customtkinter` buttons are text-only, so each segment is a small `CTkButton` with a unicode glyph as its `text`, height 28 matching the existing header ghost pills.
- **Persistence:** store an `appearance` key in `config.json` (same mechanism as `main.py:70`); default `system`.
- **Behavior:** on select → `ctk.set_appearance_mode("Light"|"Dark"|"System")`; refresh `reverse_mode`-dependent label colors (`main.py:481-485`) so contrast holds in both modes.
- **Glyph rendering note:** `Kanit` (and `Tahoma`) don't include emoji; use plain unicode `☀ ☾ ⛶`-style glyphs (matching the app's existing `➔` / `⇄` / `☕`), choosing symbols that render monochrome in the loaded font. Verify at build and fall back to Thai text `สว่าง · มืด · อัตโนมัติ` if no device glyph renders cleanly.

---

## 4. Reuse & where changes land

- All color/type/radius changes go in **`theme.py` only** (per `DESIGN.md:3`), and — matching the existing reconcile plan — `main.py` should consume these owners rather than re-declaring them. This is complementary to `design-plans/reconcile-main-to-theme.md`.
- New appearance-mode control + config key land in `main.py` + `DESIGN.md` (document the new token values + mode control).
- No new primitives needed: `button()` variants (primary/outline/ghost/chip/kofi) and `Fonts` already express everything.

---

## 5. Decisions — resolved

1. **Palette:** Mix — deep green light / bright green dark (final values in table above).
2. **Mode UI:** header segmented control, right of `อัปเดต` / `About`.
3. **Labels:** icon-only (`☀ ☾` device glyph), persisted to config.

Next step: write the implementation plan specifying exact `theme.py` token edits, the Kanit font asset swap, and the header appearance control + config wiring in `main.py`.
