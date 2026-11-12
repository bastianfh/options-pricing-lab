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
