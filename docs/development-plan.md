# Development plan

This document records the structure and build order chosen at the start of the
project, plus the design decisions made along the way.

## Repository structure

```
options-pricing-lab/
├── pricing/                  # Pricing library: pure Python + NumPy/SciPy, no UI code
│   ├── __init__.py           # Public API
│   ├── utils.py              # Shared types (OptionType, ExerciseStyle), validation, payoffs
│   ├── models/
│   │   ├── black_scholes.py  # Black-Scholes-Merton and Garman-Kohlhagen closed forms
│   │   ├── binomial.py       # Cox-Ross-Rubinstein tree, European + American
│   │   ├── monte_carlo.py    # GBM Monte Carlo with antithetic + control variates
│   │   └── finite_difference.py  # Crank-Nicolson PDE solver (Rannacher start)
│   ├── greeks.py             # Analytical BS Greeks + generic bump-and-reprice Greeks
│   ├── implied_vol.py        # Newton-Raphson IV with bisection fallback, IV surface
│   └── strategies.py         # Multi-leg payoff / P&L for option strategies
├── app/                      # Streamlit UI (imports `pricing`, never the reverse)
│   ├── content.py            # ALL user-facing wording for Plain English and Pro modes
│   ├── theme.py              # Palette + shared Plotly chart template
│   ├── ui.py                 # Shared layout helpers: CSS, sidebar, cards, inputs
│   ├── style.css             # Small custom stylesheet
│   └── pages/                # One file per page
├── tests/                    # pytest suite
├── docs/                     # Methods write-up, validation report, images
├── scripts/                  # Figure / screenshot generation
├── .streamlit/config.toml    # Custom light + dark theme
├── .github/workflows/        # CI: run tests on every push
└── streamlit_app.py          # Entry point (Streamlit Community Cloud default name)
```

## Milestones

1. **Engine + tests**
   1. Shared utilities and Black-Scholes / Garman-Kohlhagen, tested against textbook values and put-call parity
   2. CRR binomial tree (European + American)
   3. Monte Carlo with antithetic and control variates, standard errors and confidence intervals
   4. Crank-Nicolson finite-difference solver
   5. Analytical and numerical Greeks
   6. Implied volatility solver and surface
   7. Strategy payoffs
   8. CI workflow
2. **UI**: theme + content dictionary + chart template, then one page at a time
   (Home, Pricer, Greeks explorer, Payoff & P&L, Volatility surface, Validation, Methods)
3. **Polish**: screenshot review loop, README, docs, deployment instructions

## Design and scope decisions

| Decision | Choice | Why |
|---|---|---|
| Dividend / foreign rate | One continuous yield `q` throughout. Garman-Kohlhagen is Black-Scholes-Merton with `q = r_f`. | One code path, and FX falls out for free. |
| Greek units in the library | Raw derivatives: vega per 1.00 vol, theta per year, rho per 1.00 rate. The UI converts to "per 1%" and "per day". | Keeps the math clean and testable; display conventions live in the UI. |
| Monte Carlo scheme | Exact GBM terminal sampling (European payoffs only). | No discretisation bias, so the only error is statistical, which makes the convergence study clean. |
| Monte Carlo control variate | Discounted terminal asset price, `E[e^{-rT} S_T] = S_0 e^{-qT}`, optimal β estimated from the sample. | Known expectation, highly correlated with call/put payoffs. |
| Monte Carlo Greeks | Bump-and-reprice with common random numbers (same seed). | Without common random numbers, bumped prices are dominated by noise. |
| PDE grid | Log-spot grid centred exactly on `ln S0`; Rannacher start (first steps fully implicit). | No interpolation error at the spot; damps Crank-Nicolson oscillations caused by the kinked payoff. |
| American exercise in the PDE | Early-exercise projection after each time step. | Simple and robust; PSOR is listed as a next step. |
| Volatility surface data | Synthetic smile (skew, curvature, term structure) priced with Black-Scholes and then inverted by the IV solver, plus optional CSV upload of real quotes. | Works offline with no data feed, and exercises the solver end to end. |
| App entry point | `streamlit_app.py` with `st.navigation` and a hidden default menu; custom sidebar with the mode toggle above the page links. | The toggle stays at the top of the sidebar on every page. |
| Light / dark mode | `[theme.light]` and `[theme.dark]` in `config.toml`; CSS and Plotly colours read `st.context.theme.type`. | Both modes are designed rather than one being an afterthought. |
| Binomial Greeks | Δ, Γ, Θ from the first two tree steps; ν, ρ bumped. | Spot bumps alias against the lattice's oscillation (bumped Γ was 26% off). |
| PDE payoff | Cell-average the payoff in the strike's cell. | Without it, error depended on where K fell between nodes; with it, a clean O(h²). |
| Benchmark timing | Best of up to 7 repeats within a 25 ms budget. | Sub-millisecond timings were dominated by warm-up and jitter. |
| FX display | Method differences in pips; premium per 1m base notional. | The units an FX trader actually quotes. |
| Python version | 3.12+ | NumPy 2.5 (pinned) requires it. |
| Screenshot tooling | Node Playwright (`scripts/*.cjs`). | Reuses the pre-installed browser; no second Playwright install. |

## What was built, by milestone

1. **Engine:** all six components, with 313 tests plus 2 doctests (textbook values, no-arbitrage, convergence orders, MC statistics, IV round trips, Greeks).
2. **UI:** seven pages, a Plain English / Pro switch bound to `?mode=`, persistent inputs across pages, presets.
3. **Polish:** screenshot review in light, dark and phone-width layouts; README figure generated from the library; CI on Python 3.12 and 3.13.

## Visual redesign (after the first release)

The first version used the default "AI SaaS" look: Tailwind indigo, Inter, identical rounded cards with soft shadows, uppercase eyebrow labels and callout boxes. The redesign gives it a point of view suited to a pricing tool:

| Choice | Detail |
|---|---|
| Palette | Cool paper `#f5f7f6`, slate ink `#16212a`, petrol accent `#0d5c61`; green/red reserved for gains and losses. Dark mode uses deep petrol-slate, not neutral black. |
| Type | One family, Archivo, with its width axis as the expressive variable: headings semi-expanded, body at normal width, all figures tabular. |
| Surfaces | Inputs sit on a tinted panel; results are open text and tables, not cards. |
| Signature element | The method ledger: prices aligned on the decimal point, with digits that diverge from the reference faded, so agreement is visible at a glance. |
| Removed | Card grids, eyebrow labels, the stat strip, callout boxes, arrows on links, and "·"-joined meta strings. |
| Fixed | Page title clipped under the top bar on phones; copy that said "on the left" when inputs sit above on a phone. |

## Visual redesign v2: quant desk x industrial hardware (supersedes the petrol design above)

A second overhaul to a bespoke terminal look: the data density of a derivatives desk with the Swiss-grid hardware minimalism of a synth panel. Only layout, styling and chart aesthetics changed; `pricing/` and `tests/` are untouched.

| Choice | Detail |
|---|---|
| Palette | Locked matte dark: carbon `#0A0A0B` canvas, graphite `#111113` modules, `#161619` input wells, `#222226` hairlines. Text `#F4F4F6` / `#8E8E93` / `#48484D`. Signal orange `#FF5500` for the active parameter, emerald `#00E676` for call/long/profit, crimson `#FF3B30` for put/short/loss, amber `#FFB800` for volatility. |
| Type | JetBrains Mono for every number, input, table and axis (tabular figures everywhere); Inter for short prose. Labels are uppercase hardware micro-labels with bracketed symbols (`SPOT [S]`, `VOLATILITY [σ]`), upper-cased in Python so Greek letters survive. |
| Geometry | Radii of 0-2px; modules share exposed 1px rules (CSS grid with a 1px gap over the rule colour). No shadows, gradients, glows or hover animations. |
| Topology | 40px telemetry bar (tool tabs `[01] PRICER` to `[06] METHODS`, live model / r / σ / T readout, status LED, Plain/Pro switch); left control bay; numbered analytical modules (`02 // THEORETICAL VALUE`, `03 // ...`). The app opens straight into the Pricer. |
| Charts | One helper: transparent paper, graphite plot area, `#1C1C20` grid, mirrored hairline axes, monospace 10px ticks, sharp dark tooltips, dashed grey/orange reference lines, single-hue orange (sensitivities) or amber (volatility) colour scales, crimson/emerald diverging scale only when a value changes sign. |

**Changes to earlier requirements, made deliberately:**
- Light mode was removed (the brief locks dark).
- The Plain English / Pro switch moved from the sidebar to the always-visible top bar, because the sidebar was removed.
- The Home page was removed; its example scenarios live on the Pricer.
- Plain English explanations were kept as small notes: they are a core feature, not filler.
- Emerald vs crimson is a red-green pair, so it is always paired with +/− signs, dashes, markers or text labels.
