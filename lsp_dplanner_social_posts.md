# LSP D-Planner — Social Media Posts

Posts for v2.20.21. Adapt tone and length to platform.

---

## Post A — Full Feature Overview (Reddit / forums / GitHub)

**Title:**
LSP D-Planner v2.20.21 — free open-source deco planner (Bühlmann ZHL-16C + VPM-B + VPM-B/GFS) with native Android app

**Body:**

LSP D-Planner is a free dive planning app by Three Cats LSP. Runs in any browser and as a native Android app — completely offline, no account, no ads, no subscription.

🌐 **Web app:** https://threecats-lsp.com/d-planner/
📲 **Android APK:** https://threecats-lsp.com/d-planner/download.html
💻 **GitHub:** https://github.com/Three-Cats-LSP/LSP_D-planner

> **Rebreather diver?** See [LSP D-Planner + CCR](https://threecats-lsp.com/d-planner-ccr/) — CCR, pSCR, bailout edition.

---

**Two modes: Rec and Tec**

Recreational:
- NDL tables (PADI RDP-based + Bühlmann) with GF-adjustable limits
- Multi-dive day planning with residual nitrogen tracking across up to 4 dives
- Surface Interval calculator — compartment tissue loading, controlling compartment, reverse-profile warning
- Average Depth converter

Technical:
- **Bühlmann ZHL-16C + GF** — 16 tissue compartments. GF Low/High via presets (GUE DecPlanner, MultiDeco, Abysner, Subsurface, DiveKit) or custom. Shallow gradient toggle.
- **VPM-B** — Varying Permeability Model. Conservatism +0 to +5.
- **VPM-B/GFS** — VPM-B deep stops + GF High at shallow stops.

---

**Gas Management:**
- Full trimix (O₂/He/N₂) for bottom gas and deco gases
- Travel gas card — auto-switch by MOD or manual
- Gas Consumption — total volume, rule of thirds / half tank, turn pressure, reserve, sufficiency
- SAC in litres or cubic feet

**Tools:**
- MOD Calculator · Best Mix · END Calculator · EAD Table · Gas Table · Unit Converter · CNS/OTU Tracker

**Export:**
- PDF (Dive Plan + Emergency Plan) · TXT · Deco Slate · Copy to clipboard

---

Free and open source (MIT). No account. No ads. No subscription.

---

## Post B — Short (Instagram / X / Mastodon)

LSP D-Planner v2.20.21 — free open-source deco planner for rec and tec divers.

Bühlmann ZHL-16C + GF · VPM-B · VPM-B/GFS
Trimix · travel gas · altitude · repetitive dives
Gas consumption · deco slate · PDF & TXT export
Android app — full offline, no account

🌐 https://threecats-lsp.com/d-planner/
📲 APK: https://threecats-lsp.com/d-planner/download.html

#scubadiving #technicaldiving #decompression #diveplanning #opensource #android #trimix

---

## Post C — Algorithm Focus (Reddit r/technicaldiving / r/scubadiving / ScubaBoard)

**Title:**
Open-source deco planner — Bühlmann ZHL-16C, VPM-B, VPM-B/GFS, trimix, altitude, math verification suite

**Body:**

LSP D-Planner is a client-side decompression planning app — single HTML file, no dependencies, runs offline.

**Three algorithms:**
- **Bühlmann ZHL-16C + GF** — 16 compartments, dissolved gas. GF Low/High presets or manual. Shallow gradient toggle (MultiDeco-compatible).
- **VPM-B** — Varying Permeability Model. Bubble nuclei tracking. Conservatism +0 to +5.
- **VPM-B/GFS** — Hybrid: VPM-B deep stops, GF High for shallow stops.

**Trimix** — O₂/He/N₂, He half-time selector (Bühlmann 2003 or Baker), END column, ppO₂/MOD checks both engines.

**Altitude** — surface pressure presets to 3000 m, acclimatization toggle. VPM altitude-adjusted radii: `r_alt = r₀ × (P_SL/P_alt)^(1/3)`.

**Math Verification Suite** (`tests-verify.html`) — cross-checks vs Baker/FORTRAN reference values. Covers: ZHL/VPM pinned regression, Baker Python cross-check, Maiken ordering, coefficient verification (16 compartments vs Bühlmann 2003 canonical), physics constants, determinism, MultiDeco/V-Planner compatibility.

🌐 https://threecats-lsp.com/d-planner/
🔬 https://three-cats-lsp.github.io/LSP_D-planner/tests-verify.html
💻 https://github.com/Three-Cats-LSP/LSP_D-planner

Free and open source.

---

## Post D — Android / APK Focus

**LSP D-Planner — Android deco planner. Direct APK.**

Native Android dive planning app built with Capacitor. No Play Store.

**Features:**
- Bühlmann ZHL-16C + GF, VPM-B, VPM-B/GFS
- Recreational NDL + multi-dive day planning
- Trimix, travel gas, altitude, repetitive dives
- Gas consumption (thirds / half tank, imperial or metric)
- Export TXT and PDF to Downloads folder
- Full offline

📲 **Download:** https://threecats-lsp.com/d-planner/download.html

Free, open source, no account required. Android 5.0+.

