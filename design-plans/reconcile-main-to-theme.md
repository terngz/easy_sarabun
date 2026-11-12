# Reconcile main.py with the theme.py design system

Written against: shallow commit unavailable (workspace is uncommitted; source state cited by line numbers below).

## Evidence chain

- Surface: `main.py` — the main `EasySarabunApp` window (`main.py:319`) and the `AboutDialog` (`main.py:263`)
- Problem: `main.py` never imports `theme.py`. It re-defines the entire token set locally (`main.py:52-62`) and builds every widget with raw `ctk.CTkButton` / `CTkFrame` calls instead of the `button()` / `card()` / `dropzone()` factories in `theme.py:68`, `theme.py:75`, `theme.py:79`. The rendered consequence is that muted text renders `#77756f` (`main.py:57`) instead of the documented contrast-tuned `#6a6862` (`theme.py:18` / `DESIGN.md:34`).
- Design evidence: `DESIGN.md:3` ("แก้ค่าทั้งหมดที่ `theme.py` ที่เดียว" — edit all values in `theme.py` in one place, all screens follow); `DESIGN.md:34` pins MUTED (light) to `#6a6862` for 5.1:1 contrast on SURFACE; `DESIGN.md:31` allows only `white` (and the switch knob) as in-`main.py` hex.
- Owner: `theme.py` (tokens, type scale, spacing, radius, variants, factories) is the single source of truth declared by the repo.
- Scope and affected surfaces: `main.py` main window + About dialog, the only consumer of the design system in this repository.
- Uncertainty: none — values and factories are deterministic from source. Visual rendering of the MUTED change is expected (slightly darker muted text), which is the intended contrast correction.

## Design decision

Adopt `theme.py` as the single source of truth in `main.py`: import the token and factory owners from `theme.py` and delete the duplicated local block at `main.py:52-62`. This resolves the root problem (parallel ownership) and, as a direct consequence, makes `MUTED` resolve to the documented `#6a6862 (light)` / `#9b9993 (dark)` instead of the undocumented `#77756f`. Widgets keep their current rendered look and behavior — only the muted color corrects and the old local constants are removed.

## Reuse

- Import token owners from `theme.py`: `ACCENT`, `ACCENT_HOVER`, `SURFACE`, `BORDER`, `TEXT`, `MUTED`, `SUCCESS`, `DANGER`, `KOFI`, `KOFI_HOVER`.
- Import factory owners from `theme.py`: `button()`, `card()`, `dropzone()`, plus `RADIUS` / `TYPE` / `SPACE` where the surface needs them directly.
- Reuse the existing `Fonts`/`font()` from `theme.py` instead of the local `self.font` helper where it is a duplicate owner.
- Exemplar (factory usage): the factory functions already declared in `theme.py:68-81`.
- No new primitive is required — the existing system already expresses every needed token and component contract.

## Changes

1. `main.py`
   - Change: Add `from theme import ACCENT, ACCENT_HOVER, SURFACE, BORDER, TEXT, MUTED, SUCCESS, DANGER, KOFI, KOFI_HOVER, button, card, dropzone, font, Fonts` (or import the module and reference `theme.X`). Delete the duplicated token block at `main.py:52-62` (`ACCENT` … `KOFI_HOVER`).
   - Preserve: The `EasySarabunApp::font()` helper may remain as the window's font accessor, but re-route its values via the imported owners so it cannot drift from `theme.py`. Do not change any widget layout, `pack` structure, command wiring, or non-color option.
   - Verify: No `#77756f` literal remains in `main.py`; `MUTED` referenced in `main.py` resolves to `#6a6862` in light mode.
2. `main.py` (mode card + clipboard/selection buttons + dropzone)
   - Change: Replace the hand-built `card` (`main.py:412`), `drop` (`main.py:437`), and raw `CTkButton` constructions (`main.py:394`, `main.py:400-404`, `main.py:455-459`, `main.py:462-466`, `main.py:472-476`, `main.py:291`, `main.py:456-465`) with the `card()` / `dropzone()` / `button()` factories from `theme.py`, passing the same text, size, variant, and command options.
   - Preserve: The exact primary/outline/ghost/chip visual contract (primary=clipboard button ACCENT, outline=highlighted button ACCENT border, ghost=small header/hotkey pills), the switch styling (`main.py:420-425`), spacing, and all commands. The `AboutDialog` kofi button (`main.py:291-295`) maps to the `kofi` variant.
   - Verify: Each replaced widget renders identically (same size, radius, color) and triggers the same `command`.
3. `main.py`
   - Change: Remove local `MUTED`-now-unused shadowing and any remaining raw ctk token literals that duplicate `theme.py` (e.g. hardcoded hex), leaving `white` only where DESIGN.md explicitly permits.
   - Preserve: The `white` text on primary/kofi buttons and the switch knob `white`/`#f0f0f0` unless documented otherwise; do not alter behavior.
   - Verify: `main.py` contains no token definition; all color values come from `theme.py`.

## Scope

- Inherit: `main.py` main window and `AboutDialog` — the only consumers of the design system in this repository.
- Verify: No other file imports the removed `main.py` constants (confirmed: only `main.py` defines/uses them); run the app and check light + dark modes for muted text and all button variants.
- Exclude: `theme.py` itself, `DESIGN.md` (documentation handled per "Design documentation" below), icon assets, and any behavioral/networking code (`updater`, `hotkey`, `clip_format`, `engine`, `docx_handler`, `file_handler`).

## Validation

- Product: The app still opens, converts clipboard/highlighted text, converts files, toggles mode, records hotkeys, and the About dialog opens; nothing functional changes.
- Interface: Light and dark appearance; header ghost pills (`อัปเดต`, `About`); mode card labels (active=MUTED in inactive side); dropzone (empty-border); primary clipboard button; outline highlight button; hotkey chip; about kofi button; status bar (`พร้อมใช้งาน`).
- System: Confirm every color/widget now draws from the imported `theme.py` owners with no parallel token definitions remaining in `main.py`.
- Repository: `python -c "import ast,sys; ast.parse(open('main.py',encoding='utf-8').read())"` → succeeds (syntax valid). Grep for the removed literals: `search_files` regex `#77756f|ACCENT =|MUTED =` in `main.py` → no matches after the change.

## Stop conditions

- Stop if any widget's visual contract or command behavior would have to change to satisfy the factories, or if `theme.py`'s `button()` variants cannot express an existing button (then preserve that widget's raw construction and note it). Stop if the local `font()`/`Fonts` and `theme.font()` cannot be reconciled without affecting rendering.

## Design documentation

- After acceptance and validation: no `DESIGN.md` change required — `DESIGN.md:3` already documents `theme.py` as the single source; this change brings `main.py` into conformance with the existing decision.
