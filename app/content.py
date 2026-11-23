"""All user-facing wording for the app, in one place.

Every label, tooltip, explanation and heading has a ``plain`` (Plain English)
and a ``pro`` variant. Pages never hard-code wording: they call :func:`t` with
a key. Strings may contain ``{placeholders}`` filled in by the caller.

To change any text in the app, edit this file.

Entry formats
-------------
* ``"key": "text"``                         same text in both modes
* ``"key": {"plain": "...", "pro": "..."}``  mode-specific text
"""

from __future__ import annotations

from typing import Union

Entry = Union[str, dict[str, str]]

SIMPLE, PLAIN, PRO = "Simple", "Plain English", "Pro"
MODES = (SIMPLE, PLAIN, PRO)

TEXT: dict[str, Entry] = {
    # ------------------------------------------------------------------ app
    "app.name": "Options Pricing Lab",
    "app.tagline": {
        "plain": "Find out what an option is worth, why, and how sure we can be.",
        "pro": "A from-scratch options pricing and risk library, made interactive.",
    },
    "mode.label": "Explanations",
    "mode.help": (
        "Simple is for complete beginners: just the price, profit and loss, and risk, on two tools. "
        "Plain English translates every term, adds a one-line explanation under each result and keeps "
        "advanced settings on sensible defaults. Pro shows standard notation, every parameter, "
        "technical diagnostics and the equations. All three use exactly the same pricing engine."
    ),
    "mode.caption": {
        "plain": "Everyday words, sensible defaults.",
        "pro": "Standard notation, all parameters.",
    },
    "nav.home": "Home",
    "nav.pricer": "Pricer",
    "nav.greeks": "Greeks explorer",
    "nav.payoff": "Payoff & P&L",
    "nav.surface": "Volatility surface",
    "nav.validation": "Validation",
    "nav.methods": "Methods",
    "nav.market": "Market data",
    "nav.backtest": "Backtest",
    "navshort.backtest": "Backtest",
    "navshort.market": "Market",
    "navshort.pricer": {"plain": "Pricer", "pro": "Pricer", "simple": "Option price"},
    "navshort.greeks": "Greeks",
    "navshort.payoff": "Payoff",
    "navshort.surface": "Surface",
    "navshort.validation": "Validation",
    "navshort.methods": "Methods",
    "sidebar.footer": "Pricing engine written from scratch in NumPy & SciPy. No pricing libraries.",
    "sidebar.source": "Source code on GitHub",
    "disclaimer": "For education and research. Model prices are not trading advice.",

    # ---------------------------------------------------------------- guide
    # First-run guide. Text in [BRACKETS] is shown as an on-screen label. Lines starting
    # with "- " become bullet points.
    "share.button": "Share link",
    "share.help": "Copy a link that opens this tool with exactly these settings",
    "share.caption": "Anyone who opens this link sees this tool with exactly the settings you have now. Use the copy icon on the right.",
    "report.button": "Generate report",
    "report.help": "Download a report of these inputs, results and charts (HTML; print it to PDF from your browser)",
    "guide.button": "Guide",
    "guide.button.help": "Open the step-by-step guide to the app",
    "guide.dialog_title": "Guide",
    "guide.step_of": "Step {n:02d} / {total:02d}",
    "guide.next": "Next",
    "guide.back": "Back",
    "guide.skip": "Skip guide",
    "guide.start": "Start the guide",
    "guide.finish": "Start exploring",
    "guide.map.tools": "Tools",
    "guide.map.readout": "Readout",
    "guide.map.mode": "Mode",
    "guide.map.guide": "Guide",
    "guide.map.examples": "Examples",
    "guide.map.inputs": "Your option",
    "guide.map.value": "Price",
    "guide.map.methods": "4 methods",
    "guide.map.greeks": "Greeks",
    "guide.map.chart": "Chart",
    "guide.welcome.title": "Welcome",
    "guide.welcome.body": (
        "This app works out what an option is worth, four different ways, and shows you what makes "
        "that price move.\n"
        "This guide takes about a minute and shows you where everything is. You can leave it at any "
        "time and reopen it from [GUIDE] in the top bar."
    ),
    "guide.tools.title": "The tools",
    "guide.tools.body": (
        "Across the top are eight tools. You're on [PRICER] now.\n"
        "- [PRICER]: price one option and see what drives it\n"
        "- [MARKET]: load a real US stock and use its numbers\n"
        "- [BACKTEST]: replay a strategy on a stock's real history\n"
        "- [GREEKS]: watch how the risks change with price and time\n"
        "- [PAYOFF]: see what a strategy makes or loses\n"
        "- [SURFACE]: see how much movement the market expects\n"
        "- [VALIDATION]: proof that the maths is right\n"
        "- [METHODS]: how each model works"
    ),
    "guide.mode.title": "Simple, Plain English or Pro",
    "guide.mode.body": (
        "Top right. [SIMPLE] strips everything back to price, profit and risk for complete beginners. "
        "[PLAIN ENGLISH] uses everyday words, explains every result and keeps advanced "
        "settings out of the way. [PRO] shows standard finance notation, every setting and extra "
        "diagnostics.\n"
        "The maths is identical in all three. Brand new to options? Try [SIMPLE] first."
    ),
    "guide.readout.title": "The live readout",
    "guide.readout.body": (
        "This strip shows the settings in use right now:\n"
        "- [MODEL]: the pricing model (BSM is Black-Scholes, GK is its currency version)\n"
        "- [r]: the interest rate\n"
        "- [σ]: volatility, how much the price tends to move\n"
        "- [T]: days until the option expires\n"
        "The green [LIVE] light means every result on screen is up to date."
    ),
    "guide.inputs.title": {"plain": "Describe your option", "pro": "The parameter bay"},
    "guide.inputs.body": {
        "plain": (
            "The panel on the left is where you set up the option: what you're trading, a call (the "
            "right to buy) or a put (the right to sell), today's price, the agreed price, how long it "
            "lasts and how much the price tends to move.\n"
            "Not sure what a box means? Hover over its [?] for a short explanation. Your settings "
            "carry across every tool."
        ),
        "pro": (
            "The left bay holds the contract and market data: underlying, call or put, exercise style, "
            "[SPOT [S]], [STRIKE [K]], [TIME [T]], [VOLATILITY [σ]], rates and yield. "
            "[NUMERICAL SETTINGS] at the bottom controls steps, paths and grid size.\n"
            "Every field has a [?] tooltip, and settings carry across every tool."
        ),
    },
    "guide.examples.title": "Try an example",
    "guide.examples.body": {
        "plain": (
            "Not sure what to type? These buttons load a ready-made situation, such as protecting "
            "shares you own, betting on a big move, or a EUR/USD currency option."
        ),
        "pro": (
            "Example scenarios (protective put, straddle, EUR/USD call, covered call) are shown in "
            "[PLAIN ENGLISH] mode, above the parameter bay."
        ),
    },
    "guide.value.title": "What it's worth",
    "guide.value.body": (
        "The big number is the option's price today. [CALL] or [PUT] beside it tells you which kind "
        "it is.\n"
        "The boxes next to it split that price up: what it would be worth if used right now, what "
        "you're paying for the time left, and how long until it expires."
    ),
    "guide.methods.title": "Four ways to get the same answer",
    "guide.methods.body": (
        "The app prices the option four independent ways: an exact formula, a tree of possible "
        "prices, thousands of simulated futures, and a grid solver.\n"
        "Faded digits show exactly where a method starts to differ from the exact answer. When "
        "four different routes land on the same number, you can trust it."
    ),
    "guide.greeks.title": "What moves the price",
    "guide.greeks.body": (
        "These five boxes are the Greeks, the standard measures of an option's risk:\n"
        "- [Δ]: how much the option moves when the asset moves\n"
        "- [Γ]: how quickly that sensitivity changes\n"
        "- [ν]: how much it gains if the market expects bigger moves\n"
        "- [Θ]: how much value it loses each day\n"
        "- [ρ]: how it reacts to interest rates"
    ),
    "guide.chart.title": "The picture",
    "guide.chart.body": (
        "The chart shows what the option is worth at every asset price: today (the orange line) and "
        "on the day it expires (the dashed line). Hover over it to read exact values."
    ),
    "guide.done.title": "You're all set",
    "guide.done.body": (
        "Change anything on the left and every number and chart updates instantly. Try the other "
        "tools along the top when you're ready.\n"
        "You can reopen this guide at any time with [GUIDE] in the top bar."
    ),

    # --------------------------------------------------------------- inputs
    "inputs.contract": {"plain": "The option", "pro": "Parameters"},
    "inputs.market": {"plain": "The market", "pro": "Market data"},
    "inputs.numerics": {"plain": "Advanced settings", "pro": "Numerical settings"},
    "inputs.numerics_hint": {
        "plain": "",
        "pro": "Resolution of the numerical methods. Higher is more accurate and slower.",
    },
    "in.asset.label": {"plain": "What are you trading?", "pro": "Underlying"},
    "in.asset.help": {
        "plain": "A company's shares (or an index), or a currency pair such as EUR/USD.",
        "pro": "Equity/index uses Black-Scholes-Merton with dividend yield q. FX uses Garman-Kohlhagen with domestic and foreign rates.",
    },
    "in.asset.stock": {"plain": "A stock", "pro": "Equity / index"},
    "in.asset.fx": {"plain": "A currency", "pro": "FX"},
    "in.pair.label": {"plain": "Currency pair", "pro": "Pair"},
    "in.pair.help": {
        "plain": "The first currency is the one you buy or sell; prices are quoted in the second.",
        "pro": "BASE/QUOTE. Spot and premium are in quote (domestic) currency per unit of base (foreign).",
    },
    "in.option_type.label": {"plain": "Type of option", "pro": "Option type"},
    "in.option_type.help": {
        "plain": "A call is the right to BUY at the agreed price. A put is the right to SELL at the agreed price.",
        "pro": "Call payoff max(S_T - K, 0); put payoff max(K - S_T, 0).",
    },
    "in.option_type.call": {"plain": "Call (buy)", "pro": "Call"},
    "in.option_type.put": {"plain": "Put (sell)", "pro": "Put"},
    "in.exercise.label": {"plain": "When can you use it?", "pro": "Exercise style"},
    "in.exercise.help": {
        "plain": "European options can only be used on the expiry date. American options can be used any day until then, which can make them worth a little more.",
        "pro": "European: exercise at T only. American: any time up to T (priced by tree and PDE; no closed form).",
    },
    "in.exercise.european": {"plain": "Only at expiry", "pro": "European"},
    "in.exercise.american": {"plain": "Any time", "pro": "American"},
    "in.S.label": {"plain": "Price of the asset today", "pro": "Spot [S]"},
    "in.S.help": {
        "plain": "What one share (or one unit of currency) costs right now.",
        "pro": "Current price of the underlying, S_0.",
    },
    "in.K.label": {"plain": "Agreed price", "pro": "Strike [K]"},
    "in.K.help": {
        "plain": "The price you are allowed to buy (call) or sell (put) at. Also called the strike.",
        "pro": "Strike price K.",
    },
    "in.days.label": {"plain": "Days until it expires", "pro": "Time [T] (days)"},
    "in.days.help": {
        "plain": "How long the option lasts. More time means more chance of a big move, so options with longer lives usually cost more.",
        "pro": "Calendar days; T = days / 365 (ACT/365).",
    },
    "in.vol.label": {"plain": "How much the price tends to move (%)", "pro": "Volatility [σ] (%)"},
    "in.vol.help": {
        "plain": "How jumpy the asset is, as a yearly percentage. 20% means a typical yearly move of about ±20%. Big-tech stocks are often 25–40%, major currency pairs 5–10%.",
        "pro": "Annualised volatility of log-returns, σ.",
    },
    "in.r.label": {"plain": "Interest rate (%)", "pro": "Risk-free rate [r] (%)"},
    "in.r.help": {
        "plain": "What you'd earn on cash in the bank per year. Higher rates make calls slightly more valuable and puts slightly less.",
        "pro": "Continuously compounded risk-free rate r.",
    },
    "in.r_fx.label": {"plain": "Interest rate of the {quote} (%)", "pro": "Domestic rate [r_d] ({quote}, %)"},
    "in.r_fx.help": {
        "plain": "What you'd earn per year holding the second currency of the pair in the bank.",
        "pro": "Continuously compounded domestic (quote currency) rate r_d.",
    },
    "in.q.label": {"plain": "Dividend yield (%)", "pro": "Dividend yield [q] (%)"},
    "in.q.help": {
        "plain": "Cash the company pays shareholders per year, as a % of the share price. Dividends lower call prices and raise put prices.",
        "pro": "Continuous dividend yield q.",
    },
    "in.q_fx.label": {"plain": "Interest rate of the {base} (%)", "pro": "Foreign rate [r_f] ({base}, %)"},
    "in.q_fx.help": {
        "plain": "What you'd earn per year holding the first currency of the pair. It works like a dividend.",
        "pro": "Continuously compounded foreign (base currency) rate r_f; enters as q = r_f.",
    },
    "in.steps.label": "Binomial steps [N]",
    "in.steps.help": "Time steps in the CRR tree. Error ~ O(1/N); cost ~ O(N²).",
    "in.paths.label": "Monte Carlo paths [n]",
    "in.paths.help": "Simulated terminal prices. Standard error ~ O(1/√n).",
    "in.antithetic.label": "Antithetic variates",
    "in.antithetic.help": "Pair each draw Z with −Z. Reduces variance for monotone payoffs.",
    "in.cv.label": "Control variate",
    "in.cv.help": "Use the discounted terminal price (known mean S·e^(−qT)) as a control variate with optimal β.",
    "in.seed.label": "Random seed",
    "in.seed.help": "Fixed seed makes Monte Carlo reproducible and enables common random numbers for Greeks.",
    "in.grid.label": "PDE grid [M = N]",
    "in.grid.help": "Space and time steps for Crank-Nicolson. Error ~ O(ΔS² + Δt²).",
    "in.T_years": "T = {T:.4f} yr",

    # --------------------------------------------------------------- presets
    "presets.title": {"plain": "Try an example", "pro": "Presets"},
    
    "presets.subtitle": {
        "plain": "Not sure where to start? Pick a real-world situation.",
        "pro": "Load a representative contract.",
    },
    "preset.protect.title": "Protect a stock I own",
    "preset.protect.desc": "Buy a put: insurance that pays out if the price falls below $95.",
    "preset.bigmove.title": "Bet on a big move",
    "preset.bigmove.desc": "A straddle profits if the price jumps either way, by enough.",
    "preset.fx.title": "EUR/USD call",
    "preset.fx.desc": "The right to buy euros at 1.10 dollars in three months.",
    "preset.income.title": "Earn income on shares",
    "preset.income.desc": "A covered call: get paid now, give up gains above $110.",

    # ----------------------------------------------------------------- home
    "home.title": {
        "plain": "What is an option worth?",
        "pro": "Options pricing & risk, from first principles",
    },
    "home.lede": {
        "plain": "Price options four different ways, see what moves their value, and check the maths holds up, with every term explained in plain English.",
        "pro": "Black-Scholes / Garman-Kohlhagen, Cox-Ross-Rubinstein trees, Monte Carlo with variance reduction and a Crank-Nicolson PDE solver, plus Greeks, implied volatility and a full convergence study.",
    },
    "home.quick.title": {"plain": "Quick price", "pro": "Quick price"},
    "home.quick.open": "Open the full pricer",
    "home.sections": {"plain": "Explore", "pro": "Sections"},
    "home.proof": {
        "plain": "Every answer is checked four ways, and {n} automated tests make sure the maths stays right.",
        "pro": "Four independent methods, validated against theory, with {n} unit tests running in CI on every push.",
    },
    "pricer.readout.title": {"plain": "What it's worth", "pro": "Theoretical value"},
    "pricer.ledger.method": "Method",
    "pricer.ledger.price": "Price",
    "pricer.ledger.diff": {"plain": "Difference", "pro": "Δ vs reference"},
    "pricer.ledger.agree": {"plain": "Matching digits", "pro": "Decimals agreed"},
    "pricer.ledger.detail": {"plain": "Notes", "pro": "Detail"},
    "pricer.ledger.reference": {"plain": "exact answer", "pro": "reference"},
    "pricer.ledger.key": {
        "plain": "Faded digits are where a method starts to differ from the exact formula.",
        "pro": "Digits are aligned on the decimal point; faded digits are where a method departs from the reference.",
    },
    "pricer.facts.intrinsic": {"plain": "Worth if used right now", "pro": "Intrinsic value"},
    "pricer.facts.time_value": {"plain": "Extra for the time left", "pro": "Time value"},
    "pricer.facts.expires": {"plain": "Expires in", "pro": "Days to expiry"},
    "pricer.facts.forward": {"plain": "Expected price at expiry", "pro": "Forward F"},
    "card.pricer": {
        "plain": "Get a price and see four methods agree.",
        "pro": "All four methods side by side, analytical vs numerical Greeks.",
    },
    "card.greeks": {
        "plain": "See how risk changes as the price and time move.",
        "pro": "Greeks across spot and time to expiry.",
    },
    "card.payoff": {
        "plain": "See what you make or lose with common strategies.",
        "pro": "Expiry payoff and mark-to-model P&L for multi-leg strategies.",
    },
    "card.surface": {
        "plain": "See how the market prices risk across strikes and dates.",
        "pro": "Implied volatility surface, smiles and term structure.",
    },
    "card.validation": {
        "plain": "Proof the numbers are right.",
        "pro": "Convergence orders, error tables and Greeks checks.",
    },
    "card.methods": {
        "plain": "How each method works, in plain words.",
        "pro": "Models, equations and implementation notes.",
    },

    # --------------------------------------------------------------- pricer
    "pricer.title": {"plain": "Price an option", "pro": "Pricer"},
    "pricer.lede": {
        "plain": "Describe the option. Its value, and what drives it, update as you change the inputs.",
        "pro": "One contract, four independent methods, analytical vs numerical Greeks.",
    },
    "pricer.hero.label": {"plain": "What this option is worth today", "pro": "{model} price"},
    "pricer.hero.label_american": {"plain": "What this option is worth today", "pro": "American price (binomial tree)"},
    "pricer.hero.explain_stock": {
        "plain": "This option costs {price}, about {pct:.1f}% of the share price. {moneyness}",
        "pro": "d₁ = {d1:.4f}, d₂ = {d2:.4f}, forward F = {forward}, {pct:.2f}% of spot.",
    },
    "pricer.hero.explain_fx": {
        "plain": "This option costs {price} {quote} per 1 {base} ({pct:.2f}% of spot), so about {notional} on a {base} 1 million deal. {moneyness}",
        "pro": "{pips} {quote} pips, or {notional} per {base} 1m notional. d₁ = {d1:.4f}, forward F = {forward}.",
    },
    "pricer.hero.explain_american": {
        "plain": "This option costs {price}. Being able to use it early adds {premium} compared with an only-at-expiry option.",
        "pro": "Early-exercise premium over the European value: {premium}. PDE value: {pde}.",
    },
    "moneyness.itm": "If it expired today it would be worth {intrinsic}; the rest is time value.",
    "moneyness.atm": "The agreed price is close to today's price, so all of its value is time value.",
    "moneyness.otm": "It is worth nothing if it expired today; you are paying for the chance the price moves your way.",
    "pricer.methods.title": {"plain": "Four ways to get the same answer", "pro": "Method comparison"},
    "pricer.methods.agree": {
        "plain": "All the methods agree to within {spread}. They take completely different routes to the same answer, which is a good sign the maths is right.",
        "pro": "Max deviation from {model}: {spread}. Monte Carlo 95% CI {ci}.",
    },
    "pricer.methods.agree_american": {
        "plain": "The tree and the grid both handle early exercise and agree to within {spread}. The formula and the simulation only work for options used at expiry.",
        "pro": "American: no closed form. Tree vs PDE deviation {spread}. BS and MC (European-only) shown greyed out.",
    },
    "pricer.vs_reference": {"plain": "{diff} vs formula", "pro": "{diff} vs BS"},
    "pricer.vs_tree": {"plain": "{diff} vs tree", "pro": "{diff} vs CRR"},
    "pips": "{x} pips",
    "pricer.unavailable": {"plain": "Only for options used at expiry", "pro": "European only"},
    "pricer.runtime": "{ms:.1f} ms",
    "pricer.ci": {"plain": "Likely range {lo} to {hi}", "pro": "95% CI [{lo}, {hi}], SE {se}"},
    "pricer.greeks.title": {"plain": "What moves the price", "pro": "Greeks: analytical vs numerical"},
    "pricer.greeks.lede": {
        "plain": "These numbers, called the Greeks, tell you how the option's value reacts when something changes.",
        "pro": "Black-Scholes closed form vs finite differences on each numerical model (tree/grid differences for Δ, Γ, Θ; bump-and-reprice otherwise). Units: Δ per 1 of S, Γ per 1 of S, ν per vol point, Θ per day, ρ per 1%.",
    },
    "pricer.greeks.col.greek": "Greek",
    "pricer.greeks.col.analytical": "Analytical (BS)",
    "pricer.greeks.col.maxdiff": "Max |Δ|",
    "pricer.greeks.col.maxdiff_help": "Largest absolute difference between any numerical method and the analytical value.",
    "method.short.black_scholes": "BS",
    "method.short.binomial": "CRR",
    "method.short.monte_carlo": "MC",
    "method.short.finite_difference": "PDE",
    "pricer.chart.title": {
        "plain": "What the option is worth at different asset prices",
        "pro": "Value vs spot",
    },
    "pricer.chart.today": {"plain": "Worth today", "pro": "Value today"},
    "pricer.chart.expiry": {"plain": "Worth at expiry", "pro": "Payoff at expiry"},
    "pricer.chart.x": {"plain": "Price of the asset", "pro": "Spot S"},
    "pricer.chart.y": {"plain": "Option value", "pro": "Option value V"},
    "pricer.chart.spot": {"plain": "Today's price", "pro": "S₀"},

    # ------------------------------------------------------- method labels
    "method.black_scholes": {"plain": "Formula", "pro": "Black-Scholes"},
    "method.black_scholes_fx": {"plain": "Formula", "pro": "Garman-Kohlhagen"},
    "method.binomial": {"plain": "Price tree", "pro": "Binomial (CRR)"},
    "method.monte_carlo": {"plain": "Simulation", "pro": "Monte Carlo"},
    "method.finite_difference": {"plain": "Grid solver", "pro": "Crank-Nicolson"},
    "method.black_scholes.desc": {
        "plain": "The classic closed-form formula. Exact and instant.",
        "pro": "Closed form.",
    },
    "method.binomial.desc": {
        "plain": "Steps back through a tree of up and down moves.",
        "pro": "{steps:,} steps, error O(1/N)",
    },
    "method.monte_carlo.desc": {
        "plain": "Averages the payoff over {paths:,} simulated futures.",
        "pro": "{paths:,} paths, {vr}",
    },
    "method.finite_difference.desc": {
        "plain": "Solves the pricing equation on a fine grid.",
        "pro": "{grid} × {grid} grid, Rannacher start",
    },
    "mc.vr.both": "antithetic + control variate",
    "mc.vr.anti": "antithetic",
    "mc.vr.cv": "control variate",
    "mc.vr.none": "no variance reduction",

    # --------------------------------------------------------------- greeks
    "greek.delta.name": {"plain": "Price sensitivity", "pro": "Delta Δ"},
    "greek.gamma.name": {"plain": "Sensitivity change", "pro": "Gamma Γ"},
    "greek.vega.name": {"plain": "Volatility sensitivity", "pro": "Vega ν"},
    "greek.theta.name": {"plain": "Daily time decay", "pro": "Theta Θ"},
    "greek.rho.name": {"plain": "Interest-rate sensitivity", "pro": "Rho ρ"},
    "greek.delta.short": "Delta",
    "greek.gamma.short": "Gamma",
    "greek.vega.short": "Vega",
    "greek.theta.short": "Theta",
    "greek.rho.short": "Rho",
    "greek.delta.unit": "per 1.00 move in S",
    "greek.gamma.unit": "Δ change per 1.00 move in S",
    "greek.vega.unit": "per 1 vol point",
    "greek.theta.unit": "per calendar day",
    "greek.rho.unit": "per 1% rate move",
    "greek.delta.explain": {
        "plain": "How much the option's value moves when the asset moves {one}. Here: about {value} per {one}.",
        "pro": "∂V/∂S",
    },
    "greek.gamma.explain": {
        "plain": "How quickly the sensitivity above changes as the asset moves. Highest when the agreed price is near today's price.",
        "pro": "∂²V/∂S²",
    },
    "greek.vega.explain": {
        "plain": "If the market expects 1% more movement, the option gains about {value}.",
        "pro": "∂V/∂σ, per 0.01",
    },
    "greek.theta.explain": {
        "plain": "Value the option loses each day just from time passing: about {value} per day.",
        "pro": "∂V/∂t, per day",
    },
    "greek.rho.explain": {
        "plain": "If interest rates rise by 1%, the option's value changes by about {value}.",
        "pro": "∂V/∂r, per 0.01",
    },

    # ------------------------------------------------------ greeks explorer
    "gx.title": {"plain": "How risk changes", "pro": "Greeks explorer"},
    "gx.lede": {
        "plain": "Pick one of the sensitivities and watch how it changes as the asset price moves and as expiry gets closer.",
        "pro": "Black-Scholes Greeks across spot and time to expiry for the contract on the left.",
    },
    "gx.select": {"plain": "Which sensitivity?", "pro": "Greek"},
    "gx.vs_spot.title": {"plain": "As the asset price changes", "pro": "{greek} vs spot, by time to expiry"},
    "gx.vs_time.title": {"plain": "As expiry gets closer", "pro": "{greek} vs time to expiry, by moneyness"},
    "gx.heatmap.title": {"plain": "The full picture", "pro": "{greek} over spot × time"},
    "gx.x_spot": {"plain": "Price of the asset", "pro": "Spot S"},
    "gx.x_time": {"plain": "Days until expiry", "pro": "Days to expiry"},
    "gx.days_left": {"plain": "{d} days left", "pro": "{d}d"},
    "gx.itm": {"plain": "In the money", "pro": "ITM (K/S = {m:.2f})"},
    "gx.atm": {"plain": "At the money", "pro": "ATM"},
    "gx.otm": {"plain": "Out of the money", "pro": "OTM (K/S = {m:.2f})"},
    "gx.insight.delta": {
        "plain": "Far below the agreed price a call barely reacts (close to 0); far above it moves almost one-for-one with the asset (close to 1). Close to expiry, that switch gets sharp.",
        "pro": "Δ_call = e^(−qT) N(d₁) ∈ (0, e^(−qT)). As T → 0 it tends to a step function at K.",
    },
    "gx.insight.gamma": {
        "plain": "Sensitivity changes fastest when the price is near the agreed price, and that spike gets taller as expiry approaches. This is why options close to expiry can swing wildly.",
        "pro": "Γ peaks near the forward and scales like 1/(Sσ√T), so ATM gamma blows up as T → 0.",
    },
    "gx.insight.vega": {
        "plain": "Options with more time left react most to changes in expected movement, especially when the agreed price is near today's price.",
        "pro": "ν = S e^(−qT) n(d₁) √T: grows with √T, peaks near ATM, identical for calls and puts.",
    },
    "gx.insight.theta": {
        "plain": "Time decay is fastest for options near the agreed price in their final weeks. Each day costs more than the one before.",
        "pro": "ATM Θ ~ −S σ n(d₁) / (2√T): accelerates as T → 0. Deep ITM European puts can have positive Θ.",
    },
    "gx.insight.rho": {
        "plain": "Interest rates matter more for options with lots of time left.",
        "pro": "ρ_call = K T e^(−rT) N(d₂): roughly linear in T.",
    },

    # --------------------------------------------------------------- payoff
    "pay.title": {"plain": "What could I make or lose?", "pro": "Payoff & P&L"},
    "pay.lede": {
        "plain": "Choose a strategy. The chart shows your profit or loss for every possible asset price, today and at expiry.",
        "pro": "Expiry payoff and mark-to-model P&L for single and multi-leg strategies, at model prices or (optionally) live quotes.",
    },
    "pay.strategy": {"plain": "Strategy", "pro": "Strategy"},
    "pay.center": {"plain": "Main agreed price", "pro": "Central strike K"},
    "pay.center.help": {
        "plain": "The agreed price the strategy is built around.",
        "pro": "Strike for single-strike strategies; centre of the wings otherwise.",
    },
    "pay.width": {"plain": "Gap between agreed prices", "pro": "Wing width"},
    "pay.width.help": {
        "plain": "For two-price strategies: how far each agreed price sits from the main one.",
        "pro": "Strangle: K ± w. Spreads: K ∓ w for the long/short legs.",
    },
    "pay.horizon": {"plain": "Show the value after this many days", "pro": "Horizon (days elapsed)"},
    "pay.horizon.help": {
        "plain": "Slide to see how profit or loss changes as time passes before expiry.",
        "pro": "Mark-to-model P&L after this many days, holding σ, r, q fixed.",
    },
    "pay.cost.debit": {"plain": "You pay", "pro": "Net debit"},
    "pay.cost.credit": {"plain": "You receive", "pro": "Net credit"},
    "pay.max_profit": {"plain": "Best case", "pro": "Max profit"},
    "pay.max_loss": {"plain": "Worst case", "pro": "Max loss"},
    "pay.breakeven": {"plain": "Break-even price", "pro": "Breakeven(s)"},
    "pay.unlimited": {"plain": "Unlimited", "pro": "Unbounded"},
    "pay.none": "None",
    "pay.chart.expiry": {"plain": "At expiry", "pro": "P&L at expiry"},
    "pay.chart.today": {"plain": "Today", "pro": "P&L today (t = 0)"},
    "pay.chart.horizon": {"plain": "After {d} days", "pro": "P&L at t = {d}d"},
    "pay.chart.x": {"plain": "Price of the asset at that time", "pro": "Spot S"},
    "pay.chart.y": {"plain": "Profit / loss", "pro": "P&L"},
    "pay.legs.title": {"plain": "What the strategy is made of", "pro": "Legs"},
    "pay.legs.custom_hint": "Edit quantities (+ long, − short) and strikes. Rows with zero quantity are ignored.",
    "pay.greeks.title": {"plain": "Position risk today", "pro": "Position Greeks"},
    "pay.explain": {
        "plain": "{summary} The shaded area shows profit (green) and loss (red) at expiry.",
        "pro": "{summary}",
    },
    "pay.leg.long": {"plain": "Buy", "pro": "Long"},
    "pay.leg.short": {"plain": "Sell", "pro": "Short"},
    "pay.leg.stock": {"plain": "the asset", "pro": "underlying"},
    "pay.col.side": "Side",
    "pay.col.qty": "Quantity",
    "pay.col.instrument": "Instrument",
    "pay.col.strike": "Strike",
    "pay.col.premium": "Premium (each)",
    "pay.live": {"plain": "Use real market prices", "pro": "Price from live option chain"},
    "pay.live.help": {
        "plain": "Off: options are priced with the model. On: each option uses today's real quote for the stock loaded in MARKET (you buy at the asking price, sell at the bid).",
        "pro": "Snaps legs to listed strikes of the MARKET ticker; longs fill at the ask, shorts at the bid, each with its own implied vol. Off by default (model prices).",
    },
    "pay.live.ticker_note": "Using {ticker} from the MARKET tool. Load a different stock there to change it.",
    "pay.live.expiry": {"plain": "Expiry date", "pro": "Expiry"},
    "pay.live.unavailable": "Live quotes aren't available right now. Turn this off to use model prices, or load a stock with listed options in MARKET.",
    "pay.live.no_quote": "Some legs have no usable market quote and were left out.",
    "pay.live.spot": "Spot",
    "pay.live.ticker": "Ticker",
    "pay.live.days": "Expiry",
    "pay.live.atm": "ATM IV",
    "pay.live.at_market": "at market",
    "pay.pop": {"plain": "Chance of making money", "pro": "Prob. of profit"},
    "pay.pop.pro": "Probability of profit",
    "pay.pop.sub": {"plain": "model estimate", "pro": "risk-neutral"},
    "pay.move": {"plain": "Typical move by expiry", "pro": "Expected move (1σ)"},
    "pay.move.pro": "Expected move (1 sd)",
    "pay.max_profit.pro": "Max profit",
    "pay.max_loss.pro": "Max loss",
    "pay.breakeven.pro": "Breakeven(s)",
    "pay.col.bid": "Bid",
    "pay.col.ask": "Ask",
    "pay.col.iv": "IV",
    "pay.legs.title.pro": "Legs",
    "pay.greeks.title.pro": "Position Greeks",
    "pay.report_title": "Option strategy analysis",
    "pay.report.setup": "Setup",
    "pay.report.results": "Results",
    "pay.report.chart": "Profit and loss",
    "pay.report.method": "Method",
    "pay.report.method_body": (
        "Expiry P&L is each leg's payoff minus the cost of entering the position. P&L before expiry marks each "
        "option to Black-Scholes-Merton (with its own implied volatility when live quotes are used). Probability "
        "of profit integrates the expiry P&L against the risk-neutral lognormal distribution of the stock price, "
        "so it is a model estimate rather than a forecast. The expected move is one standard deviation, spot x "
        "volatility x sqrt(time). Financing, early exercise and transaction costs beyond the quoted spread are "
        "not included."
    ),
    "strategy.long_call": {"plain": "Buy a call", "pro": "Long call"},
    "strategy.long_put": {"plain": "Buy a put", "pro": "Long put"},
    "strategy.straddle": {"plain": "Bet on a big move (straddle)", "pro": "Straddle"},
    "strategy.strangle": {"plain": "Cheaper big-move bet (strangle)", "pro": "Strangle"},
    "strategy.bull_call_spread": {"plain": "Bet on a moderate rise", "pro": "Bull call spread"},
    "strategy.bear_put_spread": {"plain": "Bet on a moderate fall", "pro": "Bear put spread"},
    "strategy.covered_call": {"plain": "Earn income on shares (covered call)", "pro": "Covered call"},
    "strategy.protective_put": {"plain": "Insure shares (protective put)", "pro": "Protective put"},
    "strategy.custom": {"plain": "Build my own", "pro": "Custom legs"},
    "strategy.long_call.summary": "Profit if the price ends above the agreed price plus what you paid. You can lose at most what you paid.",
    "strategy.long_put.summary": "Profit if the price ends below the agreed price minus what you paid. You can lose at most what you paid.",
    "strategy.straddle.summary": "You profit if the price moves far enough either way to cover the cost of both options. The worst case is no move at all.",
    "strategy.strangle.summary": "Like a straddle but cheaper: it needs a bigger move before it pays, in either direction.",
    "strategy.bull_call_spread.summary": "Profits if the price rises, but gains stop at the higher agreed price. Selling the second call makes it cheaper.",
    "strategy.bear_put_spread.summary": "Profits if the price falls, but gains stop at the lower agreed price. Selling the second put makes it cheaper.",
    "strategy.covered_call.summary": "You own the asset and sell someone the right to buy it from you. You collect cash now but give up gains above the agreed price.",
    "strategy.protective_put.summary": "You own the asset and buy insurance: losses stop below the agreed price, while gains are unlimited.",
    "strategy.custom.summary": "Your own combination of options and the asset.",

    # -------------------------------------------------------------- surface
    "vs.title": {"plain": "How the market prices risk", "pro": "Implied volatility surface"},
    "vs.lede": {
        "plain": "Option prices can be turned back into how much movement the market expects. Plotting that across agreed prices and expiry dates gives a surface. Real markets are not flat: protection against crashes costs extra.",
        "pro": "OTM option prices on a strike × expiry grid inverted with the Newton-Raphson/bisection solver. Prices come from a parametric smile (or your CSV), so the surface is a solver round trip.",
    },
    "vs.source": {"plain": "Data", "pro": "Price source"},
    "vs.source.synthetic": {"plain": "Example market", "pro": "Synthetic smile"},
    "vs.source.upload": {"plain": "Upload prices", "pro": "Upload CSV"},
    "vs.atm": {"plain": "Typical expected movement (%)", "pro": "ATM vol [σ_ATM] (%)"},
    "vs.atm.help": {"plain": "Expected movement for options near today's price.", "pro": "ATM level at T = 6M."},
    "vs.skew": {"plain": "Extra cost of crash protection", "pro": "Skew"},
    "vs.skew.help": {
        "plain": "More negative means protection against falls (low agreed prices) is more expensive, as in stock markets.",
        "pro": "Slope in standardised moneyness m = ln(K/F)/√T. Negative = equity-style put skew.",
    },
    "vs.curv": {"plain": "Extra cost of extreme moves", "pro": "Curvature (smile)"},
    "vs.curv.help": {
        "plain": "Higher means options far from today's price, in either direction, cost more. Typical of currencies.",
        "pro": "Quadratic coefficient in m. Higher = more pronounced smile.",
    },
    "vs.term": {"plain": "Longer-dated options expect more movement", "pro": "Term slope"},
    "vs.term.help": {
        "plain": "Positive: the market expects more movement further out. Negative: it's nervous right now.",
        "pro": "σ_ATM(T) = σ_ATM + slope·(√T − √0.5).",
    },
    "vs.upload.help": "CSV with columns: strike, expiry (years), price, type (call/put). Uses spot and rates from the inputs below.",
    "vs.upload.error": "Could not read that file. Expected columns: strike, expiry, price, type.",
    "vs.surface.title": {"plain": "Expected movement across agreed prices and dates", "pro": "σ_imp(K, T)"},
    "vs.smile.title": {"plain": "The smile: one line per expiry date", "pro": "Smile slices"},
    "vs.term_structure.title": {"plain": "Near today's price, by expiry date", "pro": "ATM term structure"},
    "vs.x_strike": {"plain": "Agreed price", "pro": "Strike K"},
    "vs.x_moneyness": {"plain": "Agreed price ÷ today's price", "pro": "K / S"},
    "vs.y_expiry": {"plain": "Years to expiry", "pro": "T (years)"},
    "vs.z_vol": {"plain": "Expected movement (%)", "pro": "Implied vol (%)"},
    "vs.diag.title": "Solver diagnostics",
    "vs.diag.points": "Grid points",
    "vs.diag.solved": "Solved",
    "vs.diag.max_err": "Max |σ_imp − σ_true|",
    "vs.diag.newton": "Newton steps (share)",
    "vs.diag.iters": "Mean iterations",
    "vs.insight": {
        "plain": "Low agreed prices show higher expected movement: investors pay up for protection against falls. That tilt is the 'skew', and it is steepest for short-dated options.",
        "pro": "Skew steepens at short maturities because skew is set in √T-scaled moneyness. A flat surface would mean Black-Scholes with constant σ is exactly right.",
    },

    # ----------------------------------------------------------- validation
    "val.title": {"plain": "Are the numbers right?", "pro": "Validation"},
    "val.lede": {
        "plain": "There is an exact formula for simple options, so we can check the other three methods against it. Each should get closer to the exact answer as we give it more computing power, at a predictable speed.",
        "pro": "Each numerical method is checked against the Black-Scholes closed form as resolution increases, with measured orders of convergence compared with theory. American options (no closed form) are checked tree vs PDE.",
    },
    "val.case": {"plain": "Test option", "pro": "Test contract"},
    "val.case.help": "All studies use this contract (European unless stated).",
    "val.summary.title": {"plain": "Summary", "pro": "Summary"},
    "val.col.method": "Method",
    "val.col.resolution": "Resolution",
    "val.col.expected": "Expected order",
    "val.col.measured": "Measured order",
    "val.col.final_error": "Error at finest",
    "val.col.status": "Check",
    "val.pass": "✓ Pass",
    "val.running": "Running convergence studies…",
    "val.summary.order_suffix": ", order of convergence",
    "val.summary.sub": {
        "plain": "{check}, final error {final}",
        "pro": "expected {expected}, final {what} {final}",
    },
    "val.summary.explain": (
        "The big numbers measure how fast each method closes in on the exact answer. 1 means doubling the "
        "effort halves the error; 2 means it quarters it; 0.5 means you need 4× the effort to halve it. "
        "All three match the theory."
    ),
    "val.bin.even": {"plain": "Even number of steps", "pro": "even N"},
    "val.bin.odd": {"plain": "Odd number of steps", "pro": "odd N"},
    "val.table": {"plain": "Show the numbers", "pro": "Error table"},
    "val.am.x": {"plain": "Steps / grid size", "pro": "N (tree) / M = N (PDE)"},
    "val.fail": "✗ Check",
    "val.work.title": {"plain": "Accuracy vs computing time", "pro": "Work-precision diagram"},
    "val.work.lede": {
        "plain": "Lower and further left is better: more accurate, faster. The grid solver wins for simple options; simulation is slowest to become precise but works for almost any option.",
        "pro": "|error| against wall-clock time per price. Lines further down-left dominate. Crank-Nicolson's O(h²) wins on vanillas; MC's dimension-independent O(n^-1/2) is why it dominates for path-dependent and multi-asset products.",
    },
    "val.work.x": {"plain": "Computing time (milliseconds)", "pro": "Runtime per price (ms)"},
    "val.work.y": {"plain": "Error vs exact formula", "pro": "|V − V_BS|"},
    "val.bin.title": {"plain": "Price tree", "pro": "Binomial tree (CRR)"},
    "val.bin.lede": {
        "plain": "With more steps the tree price settles onto the exact answer. It zig-zags because of where the agreed price falls between the tree's branches, but the zig-zag shrinks steadily.",
        "pro": "Error is O(1/N) with an odd/even oscillation from the strike's position relative to the terminal nodes (Leisen & Reimer, 1996). N·|error| stays bounded.",
    },
    "val.bin.x": {"plain": "Number of steps", "pro": "Steps N"},
    "val.mc.title": {"plain": "Simulation", "pro": "Monte Carlo"},
    "val.mc.lede": {
        "plain": "Simulation is never exact: it gives an estimate and a likely range. With 100× more simulations the range only gets 10× narrower. Two tricks (mirroring each random path and correcting with a known quantity) narrow the range much faster.",
        "pro": "Standard error ∝ n^-1/2 for every estimator; variance reduction shifts the line down by √(variance reduction factor). Shaded bands: 95% CIs.",
    },
    "val.mc.x": {"plain": "Number of simulations", "pro": "Paths n"},
    "val.mc.se_y": {"plain": "Size of the likely range", "pro": "Standard error"},
    "val.mc.price_y": {"plain": "Estimated price", "pro": "Estimate ± 95% CI"},
    "val.mc.variant.plain": {"plain": "Basic", "pro": "Plain"},
    "val.mc.variant.antithetic": {"plain": "Mirrored paths", "pro": "Antithetic"},
    "val.mc.variant.control_variate": {"plain": "Corrected", "pro": "Control variate"},
    "val.mc.variant.antithetic_control_variate": {"plain": "Both tricks", "pro": "Antithetic + CV"},
    "val.mc.vrf": "Variance reduction factor",
    "val.mc.vrf_help": "(SE_plain / SE)²: how many times more plain paths you'd need for the same accuracy.",
    "val.pde.title": {"plain": "Grid solver", "pro": "Crank-Nicolson finite differences"},
    "val.pde.lede": {
        "plain": "Doubling the grid makes the error about 4× smaller, exactly as the theory predicts. That is why this method is so fast to get precise.",
        "pro": "Second order in Δx and Δτ with Rannacher smoothing and a cell-averaged payoff at the strike. Doubling M = N divides the error by ~4.",
    },
    "val.pde.x": {"plain": "Grid size", "pro": "M = N"},
    "val.ref_slope": {"plain": "Expected speed", "pro": "Reference slope O(n^-{p})"},
    "val.error_y": {"plain": "Error vs exact formula", "pro": "|V − V_BS|"},
    "val.price_y": {"plain": "Price", "pro": "Price"},
    "val.exact": {"plain": "Exact formula", "pro": "Black-Scholes"},
    "val.am.title": {"plain": "Options you can use early", "pro": "American put: tree vs PDE"},
    "val.am.lede": {
        "plain": "There's no exact formula for options you can use any time, so instead we check that two completely different methods land on the same value. The ability to use it early is always worth something extra.",
        "pro": "No closed form exists, so the CRR tree and the projected Crank-Nicolson scheme are checked against each other, with the early-exercise premium over the European value.",
    },
    "val.am.european": {"plain": "Only-at-expiry version", "pro": "European (BS)"},
    "val.am.premium": {"plain": "Value of using early", "pro": "Early-exercise premium"},
    "val.greeks.title": {"plain": "Sensitivities", "pro": "Greeks: numerical vs analytical"},
    "val.greeks.lede": {
        "plain": "Each method's sensitivities, worked out by nudging the inputs, match the exact formulas.",
        "pro": "Finite-difference Greeks for each model vs closed form. Displayed in market units (ν per vol pt, Θ per day, ρ per 1%).",
    },
    "val.parity.title": {"plain": "Calls and puts are consistent", "pro": "Put-call parity"},
    "val.parity.lede": {
        "plain": "A call minus a put must equal a fixed amount (today's price minus the discounted agreed price). Every method respects this.",
        "pro": "C − P − (S e^(−qT) − K e^(−rT)) for each method, European.",
    },
    "val.parity.col": "C − P − (Se^(−qT) − Ke^(−rT))",
    "val.iv.title": {"plain": "Reversing the formula", "pro": "Implied vol round trip"},
    "val.iv.lede": {
        "plain": "Turning a price back into expected movement and then into a price again gets back exactly where we started, across hundreds of options.",
        "pro": "σ → price → σ_imp over a strike × expiry × vol grid.",
    },
    "val.iv.cases": "Options tested",
    "val.iv.max_vol_err": "Max |σ_imp − σ|",
    "val.iv.max_price_err": "Max price error",
    "val.iv.bisection": "Needed bisection fallback",
    "val.tests": {
        "plain": "These checks, and {n} more, run automatically every time the code changes.",
        "pro": "The same properties are asserted in the pytest suite ({n} tests), run in CI on every push.",
    },
    "table.price": "Price",
    "table.error": "Error",
    "table.n_error": "N × |error|",
    "table.ratio": "Error ratio",
    "table.runtime": "Runtime (ms)",
    "table.se": "Std. error",
    "table.ci": "95% CI",
    "table.contains": "CI ∋ BS",

    # ----------------------------------------------------------- market data
    "mk.title": {"plain": "Real stock data", "pro": "Market data"},
    "mk.lede": {
        "plain": "Load any US stock to see how it has behaved, then send its real numbers to the pricer.",
        "pro": "Daily history, realised volatility, return statistics and the live option chain for a US equity.",
    },
    "mk.source": {"plain": "Pick a stock", "pro": "Source"},
    "mk.source.ticker": {"plain": "Search a ticker", "pro": "Ticker"},
    "mk.source.upload": {"plain": "Upload a file", "pro": "Upload file"},
    "mk.ticker": {"plain": "Ticker symbol", "pro": "Ticker"},
    "mk.ticker.help": {
        "plain": "The short code a stock trades under, like AAPL for Apple. Pick one or type your own.",
        "pro": "Any US-listed symbol Yahoo Finance knows (BRK.B and BRK-B both work). Type to add one not listed.",
    },
    "mk.period": {"plain": "How much history", "pro": "History"},
    "mk.load": "Load",
    "mk.upload": {"plain": "Price history (CSV or Excel)", "pro": "Price history (CSV / Excel)"},
    "mk.upload.help": (
        "Daily prices as CSV or Excel (.xlsx, .xls), with a date column and a closing-price column. "
        "Exports from FactSet, Yahoo Finance, Nasdaq.com and Stooq work as they are: title rows above the "
        "table are skipped and the first sheet with prices is used. An optional Dividends column is used for the yield."
    ),
    "mk.upload.sample": "Download a template CSV",
    "mk.loading": "Loading {ticker} from Yahoo Finance…",
    "mk.empty": "Pick a ticker and press LOAD, or upload a CSV or Excel file of daily prices.",
    "mk.source_note": "Source: {source}. Last close {date}. Prices are delayed and for research only.",
    "mk.snapshot": {"plain": "At a glance", "pro": "Snapshot"},
    "mk.last": {"plain": "Last price", "pro": "Last close [S]"},
    "mk.change": {"plain": "Change on the day", "pro": "1D change"},
    "mk.range": "52-week range",
    "mk.yield": {"plain": "Dividend yield", "pro": "Dividend yield [q]"},
    "mk.hv": {"plain": "Typical movement, {w}", "pro": "Realised vol {w}"},
    "mk.rf": {"plain": "Interest rate (T-bill)", "pro": "Risk-free [r] (13w T-bill)"},
    "mk.rf_na": "n/a",
    "mk.explain": (
        "{ticker} last closed at {price}. Over the past year it moved about {hv1y:.0%} a year (its historical "
        "volatility), and over the last month about {hv30:.0%}. It pays a dividend yield of {q:.2%}."
    ),
    "mk.send.title": {"plain": "Use these numbers", "pro": "Send to the lab"},
    "mk.send.lede": {
        "plain": "Fill the pricer with this stock's real price, movement, dividend yield and interest rate.",
        "pro": "Sets S, K (at the money), σ, q and r in the Pricer. Days to expiry are kept.",
    },
    "mk.send.sigma": {"plain": "Which movement figure to use", "pro": "Volatility input [σ]"},
    "mk.send.sigma.help": {
        "plain": "Recent periods react faster to news; a full year is steadier. Implied volatility is what option buyers are paying for right now.",
        "pro": "Realised vol over a trailing window, or the at-the-money implied vol of the loaded expiry.",
    },
    "mk.send.atm_iv": {"plain": "Market's expectation", "pro": "ATM implied"},
    "mk.send.button": {"plain": "Send to the pricer", "pro": "Send to Pricer"},
    "mk.history.title": {"plain": "Price over time", "pro": "Price history"},
    "mk.history.close": {"plain": "Price", "pro": "Close (adjusted)"},
    "mk.history.ma50": "50-day average",
    "mk.history.ma200": "200-day average",
    "mk.history.y": {"plain": "Price", "pro": "Price"},
    "mk.vol.title": {"plain": "How jumpy it has been", "pro": "Rolling realised volatility"},
    "mk.vol.lede": {
        "plain": "Each line is the stock's yearly movement measured over a sliding window. Spikes are turbulent periods.",
        "pro": "Annualised standard deviation of daily log returns over 21- and 63-day windows.",
    },
    "mk.vol.y": {"plain": "Movement per year (%)", "pro": "σ (%)"},
    "mk.vol.atm": {"plain": "Option market now", "pro": "ATM implied"},
    "mk.returns.title": {"plain": "Good days and bad days", "pro": "Return distribution"},
    "mk.returns.lede": {
        "plain": "How often the stock rose or fell by each amount in a day. The grey curve is what a perfectly 'normal' stock would do; real stocks have more extreme days.",
        "pro": "Daily log returns against a normal density with the same mean and variance. Excess kurtosis > 0 means fat tails.",
    },
    "mk.returns.x": {"plain": "Daily change (%)", "pro": "Daily log return (%)"},
    "mk.returns.y": {"plain": "How often", "pro": "Density"},
    "mk.returns.normal": {"plain": "Normal curve", "pro": "Normal fit"},
    "mk.returns.actual": {"plain": "Actual days", "pro": "Empirical"},
    "mk.stat.return": {"plain": "Yearly return", "pro": "Annualised return"},
    "mk.stat.vol": {"plain": "Yearly movement", "pro": "Annualised vol"},
    "mk.stat.sharpe": {"plain": "Return per unit of risk", "pro": "Sharpe ratio"},
    "mk.stat.drawdown": {"plain": "Worst fall from a peak", "pro": "Max drawdown"},
    "mk.stat.skew": {"plain": "Lopsidedness", "pro": "Skewness"},
    "mk.stat.kurt": {"plain": "Extreme days", "pro": "Excess kurtosis"},
    "mk.stat.worst": {"plain": "Worst day", "pro": "Worst day"},
    "mk.stat.best": {"plain": "Best day", "pro": "Best day"},
    "mk.chain.title": {"plain": "What options on this stock cost", "pro": "Option chain"},
    "mk.chain.lede": {
        "plain": "Live quotes for options on this stock. The app turns each price back into the movement the market expects, using its own solver, and compares with Yahoo's figure.",
        "pro": "Out-of-the-money quotes (mid, or last trade if one-sided), inverted with the lab's Newton/bisection solver and compared with Yahoo's IV. US equity options are American; BS IV is the market convention.",
    },
    "mk.chain.expiry": {"plain": "Expiry date", "pro": "Expiry"},
    "mk.chain.none": "No listed options found for this stock.",
    "mk.chain.only_live": "Option chains are available for tickers loaded from Yahoo Finance, not for uploaded files.",
    "mk.chain.ours": {"plain": "This app", "pro": "Lab solver"},
    "mk.chain.yahoo": "Yahoo",
    "mk.chain.x": {"plain": "Agreed price", "pro": "Strike K"},
    "mk.chain.y": {"plain": "Expected movement (%)", "pro": "Implied vol (%)"},
    "mk.chain.surface": {"plain": "Build the full market surface", "pro": "Build market vol surface"},
    "mk.chain.surface.help": "Loads several expiries and opens them on the Volatility surface page.",
    "mk.chain.building": "Loading {n} expiries…",
    "mk.col.type": "Type",
    "mk.col.strike": "Strike",
    "mk.col.bid": "Bid",
    "mk.col.ask": "Ask",
    "mk.col.price": "Price used",
    "mk.col.iv": "IV (lab)",
    "mk.col.yahoo_iv": "IV (Yahoo)",
    "mk.col.volume": "Volume",
    "mk.col.oi": "Open interest",
    "vs.source.market": {"plain": "Real market ({ticker})", "pro": "Market ({ticker})"},
    "vs.market.note": "Market quotes for {ticker} on {date}: {n} out-of-the-money options across {k} expiries.",

    # -------------------------------------------------------------- backtest
    # ------------------------------------------------------------------ Simple mode
    "simple.price.title": "Option price",
    "simple.price.lede": "Pick a stock and a strategy.",
    "simple.bt.title": "Backtest",
    "simple.bt.lede": "How a strategy would have done.",
    "simple.ticker": "Stock",
    "simple.strategy": "Strategy",
    "simple.gap": "How far from today's price (%)",
    "simple.contracts": "Contracts",
    "simple.legs": "Your legs",
    "simple.legs.help": "One row per position. Qty is per contract (100 shares).",
    "simple.legs.help.bt": "One row per position. Strike is % of the price (100 = today's price).",
    "simple.legs.empty": "Add at least one leg.",
    "simple.manual": "Live prices unavailable. Enter them:",
    "simple.manual.price": "Stock price ($)",
    "simple.manual.moves": "How much it moves",
    "simple.moves.calm": "Calm",
    "simple.moves.normal": "Normal",
    "simple.moves.wild": "Wild",
    "simple.pay": "You pay",
    "simple.receive": "You receive",
    "simple.breakeven": "Break-even",
    "simple.max_profit": "Max profit",
    "simple.max_loss": "Max loss",
    "simple.chance": "Chance of profit",
    "simple.unlimited": "Unlimited",
    "simple.none": "None",
    "simple.today": "Today",
    "simple.chart.x": "{ticker} price at expiry",
    "simple.expiry": "Expires in",
    "simple.exp.1w": "1W",
    "simple.exp.1m": "1M",
    "simple.exp.3m": "3M",
    "simple.exp.6m": "6M",
    "simple.exp.1y": "1Y",
    "simple.exp.long.1w": "1 week",
    "simple.exp.long.1m": "1 month",
    "simple.exp.long.3m": "3 months",
    "simple.exp.long.6m": "6 months",
    "simple.exp.long.1y": "1 year",
    "simple.price.note": "Estimate based on {ticker}'s past year.",
    "simple.bt.amount": "Starting amount ($)",
    "simple.bt.file": "Use a price file",
    "simple.bt.became": "Your {amount} became",
    "simple.bt.shares_line": "Just owning the shares: {value} ({ret})",
    "simple.bt.vs": "Vs shares",
    "simple.bt.per_year": "Per year",
    "simple.bt.drop": "Biggest drop",
    "simple.bt.risk": "Risk",
    "simple.bt.wins": "Winning months",
    "simple.bt.wins.value": "{wins}/{total}",
    "simple.bt.shares": "Shares",
    "simple.bt.months": "Each month",
    "simple.bt.note": "Estimate using model option prices and typical costs.",
    "simple.risk.low": "Low",
    "simple.risk.medium": "Medium",
    "simple.risk.high": "High",
    "simple.strat.long_call": "Buy a call",
    "simple.strat.long_put": "Buy a put",
    "simple.strat.covered_call": "Covered call",
    "simple.strat.protective_put": "Protective put",
    "simple.strat.collar": "Collar",
    "simple.strat.cash_secured_put": "Cash-secured put",
    "simple.strat.long_straddle": "Straddle",
    "simple.strat.long_strangle": "Strangle",
    "simple.strat.bull_call_spread": "Bull call spread",
    "simple.strat.bear_put_spread": "Bear put spread",
    "simple.strat.iron_condor": "Iron condor",
    "simple.strat.custom": "Build your own",
    "simple.tag.long_call": "Bet it goes up",
    "simple.tag.long_put": "Bet it goes down",
    "simple.tag.covered_call": "Earn income on shares",
    "simple.tag.protective_put": "Insure your shares",
    "simple.tag.collar": "Cheap insurance, capped upside",
    "simple.tag.cash_secured_put": "Get paid to wait",
    "simple.tag.long_straddle": "Bet on a big move",
    "simple.tag.long_strangle": "Cheaper big-move bet",
    "simple.tag.bull_call_spread": "Cheaper bet it goes up",
    "simple.tag.bear_put_spread": "Cheaper bet it goes down",
    "simple.tag.iron_condor": "Bet on a quiet market",
    "simple.tag.custom": "Mix calls, puts and shares",
    "simple.report.price": "Option price",
    "simple.report.bt": "Strategy backtest",
    "simple.report.setup": "Your choices",
    "simple.report.results": "Results",
    "simple.report.stock": "Stock",
    "simple.report.today": "Price today",
    "simple.report.legs": "Legs",
    "simple.report.period": "Period",
    "simple.report.profit": "Profit / loss",
    "simple.report.col.month": "Month ended",
    "simple.report.table": "Month by month",
    "simple.report.col.pnl": "Profit / loss",
    "simple.report.manual": "Stock price and movement entered by hand.",
    "simple.report.how": "How it was estimated",
    "simple.report.how.price": (
        "Options are priced with the Black-Scholes model, using how much {ticker} moved over the past year "
        "({vol} a year), a {rate} interest rate and a {div} dividend yield. Profit and loss are at expiry, before "
        "trading costs. The chance of profit is a model estimate, not a forecast. One contract covers 100 shares."
    ),
    "simple.report.how.bt": (
        "Every 30 days the strategy opens new options at the same distance from the price, holds them to expiry "
        "and starts again. Options are priced with the Black-Scholes model from the stock's recent ups and downs "
        "plus 10%, not from real historical option prices. Costs: half of a 5% bid-ask spread on each option, "
        "plus $0.65 per contract. Cash earns {rate} a year."
    ),
    "feedback.button": "Feedback",
    "feedback.button.help": "Found a bug or something confusing? Tell me here (opens in a new tab).",
    "bt.title": {"plain": "How would it have done?", "pro": "Backtest"},
    "bt.lede": {
        "plain": "Replay an option strategy on a real stock's history and compare it with simply owning the shares.",
        "pro": "Rolling option strategies on real prices; options model-priced from trailing realised vol.",
    },
    "bt.report_title": "Strategy backtest",
    "pricer.report_title": "Option valuation",
    "pricer.report.setup": "Contract and market data",
    "pricer.report.price": "Price by method",
    "pricer.report.greeks": "Greeks (market units)",
    "pricer.report.method": "Method",
    "pricer.report.method_body": (
        "The option is priced four independent ways: the Black-Scholes-Merton closed form (Garman-Kohlhagen for FX), "
        "a Cox-Ross-Rubinstein binomial tree, Monte Carlo simulation with antithetic variates and a control variate, "
        "and a Crank-Nicolson finite-difference solver. Greeks are analytical for Black-Scholes and finite "
        "differences for the numerical methods. Vega is per volatility point, theta per calendar day and rho per 1%."
    ),
    "mk.report_title": "Market data analysis",
    "val.report_title": "Numerical validation",
    "val.report.case": "Test contract",
    "val.report.orders": "Measured vs theoretical order of convergence",
    "val.report.mc": "Monte Carlo variance reduction",
    "val.report.pde": "Crank-Nicolson error by grid size",
    "val.report.greeks": "Greeks: numerical vs analytical",
    "val.report.method": "Method",
    "val.report.method_body": (
        "Each numerical method is run at increasing resolution and compared with the Black-Scholes closed form. "
        "The empirical order of convergence is the least-squares slope of log(error) against log(resolution). "
        "Theory predicts order 1 for the CRR tree, 2 for Crank-Nicolson and 1/2 for the Monte Carlo standard error."
    ),
    "bt.data": {"plain": "The stock", "pro": "Data"},
    "bt.strategy": {"plain": "The strategy", "pro": "Strategy"},
    "bt.strategy.buy_and_hold": {"plain": "Just own the shares", "pro": "Buy and hold"},
    "bt.strategy.covered_call": {"plain": "Covered call", "pro": "Covered call"},
    "bt.strategy.protective_put": {"plain": "Protective put", "pro": "Protective put"},
    "bt.strategy.collar": {"plain": "Collar", "pro": "Collar"},
    "bt.strategy.cash_secured_put": {"plain": "Cash-secured put", "pro": "Cash-secured put"},
    "bt.strategy.long_straddle": {"plain": "Long straddle", "pro": "Long straddle"},
    "bt.strategy.long_strangle": {"plain": "Long strangle", "pro": "Long strangle"},
    "bt.strategy.bull_call_spread": {"plain": "Bull call spread", "pro": "Bull call spread"},
    "bt.strategy.bear_put_spread": {"plain": "Bear put spread", "pro": "Bear put spread"},
    "bt.strategy.iron_condor": {"plain": "Iron condor", "pro": "Iron condor"},
    "bt.strategy.buy_and_hold.desc": "Hold one share the whole time. The benchmark everything else is compared with.",
    "bt.strategy.covered_call.desc": "Own the shares and sell a call above the price each period: earn premium, give up big gains.",
    "bt.strategy.protective_put.desc": "Own the shares and buy a put below the price each period: insurance against falls.",
    "bt.strategy.collar.desc": "Own the shares, buy a put below and sell a call above: the call pays for the insurance.",
    "bt.strategy.cash_secured_put.desc": "Keep cash and sell a put below the price each period: paid to wait for a lower entry.",
    "bt.strategy.long_straddle.desc": "Buy a call and a put at today's price each period: wins on big moves either way.",
    "bt.strategy.long_strangle.desc": "Buy a call above and a put below each period: a cheaper bet on big moves.",
    "bt.strategy.bull_call_spread.desc": "Buy a call at today's price, sell one above: a cheaper, capped bet on a rise.",
    "bt.strategy.bear_put_spread.desc": "Buy a put at today's price, sell one below: a cheaper, capped bet on a fall.",
    "bt.strategy.iron_condor.desc": "Sell a put below and a call above, buy further-out wings: paid if the price stays in a range.",
    "bt.strategy.custom": {"plain": "Build your own", "pro": "Custom legs"},
    "bt.strategy.custom.desc": (
        "Combine up to 8 legs: shares, calls and puts, bought or sold. Strikes are set as a percentage of "
        "the stock price on the day the options are opened, and every option leg rolls on the same schedule."
    ),
    "bt.custom.start": {"plain": "Start from a ready-made one", "pro": "Load template"},
    "bt.custom.start.help": "Fills the table with that strategy's legs so you can change them.",
    "bt.custom.start.placeholder": "Pick a strategy to copy",
    "bt.custom.legs": {"plain": "Your legs", "pro": "Legs"},
    "bt.custom.legs.help": (
        "One row per position; add rows with + and delete them by selecting a row. Quantity is per share of "
        "stock: 1 means one option on one share (a contract covers 100). Strike is a percentage of the "
        "stock price when the option is opened: 100 is at the money, 105 is 5% above. Share rows ignore the strike."
    ),
    "bt.custom.col.side": "Side",
    "bt.custom.col.kind": "Type",
    "bt.custom.col.qty": "Qty",
    "bt.custom.col.strike": "Strike %",
    "bt.custom.side.buy": "Buy",
    "bt.custom.side.sell": "Sell",
    "bt.custom.kind.call": "Call",
    "bt.custom.kind.put": "Put",
    "bt.custom.kind.stock": "Shares",
    "bt.custom.name": {"plain": "Give it a name", "pro": "Strategy name"},
    "bt.custom.name.help": "Shown on the charts and in the report. Up to 40 characters.",
    "bt.custom.default_name": "Custom strategy",
    "bt.custom.empty": "Add at least one leg with a quantity above zero to run the backtest.",
    "bt.custom.trimmed": "Only the first 8 legs are used.",
    "bt.custom.unlimited": (
        "Heads up: this strategy is short more calls (or shares) than it owns, so its losses have no limit "
        "if the stock rallies."
    ),
    "bt.custom.blown": (
        "The portfolio's value fell to zero or below at some point, so the per-year return, volatility and "
        "Sharpe ratio can't be calculated. In real life a broker would have closed the position with a margin call first."
    ),
    "bt.payoff": {"plain": "One period, start to finish", "pro": "Payoff at expiry (one cycle)"},
    "bt.payoff.pro": "Payoff at expiry (one cycle)",
    "bt.payoff.lede": {
        "plain": "Profit or loss on $100 of stock when the options expire, depending on where the price ends up. "
                 "Options are priced with today's volatility, before trading costs.",
        "pro": "P&L per 100 of spot at expiry vs S_T, premium at the latest trailing vol (incl. vol premium), before costs.",
    },
    "bt.payoff.x": {"plain": "Stock price at expiry (% of today)", "pro": "S_T / S_0 (%)"},
    "bt.payoff.y": {"plain": "Profit / loss ($)", "pro": "P&L per 100 spot"},
    "bt.payoff.today": "Today",
    "bt.tenor": {"plain": "Roll every", "pro": "Tenor [days]"},
    "bt.tenor.help": {
        "plain": "How long each set of options lasts before the strategy opens the next one.",
        "pro": "Calendar days to expiry for each cycle; options are held to expiry and rolled.",
    },
    "bt.otm_call": {"plain": "Call this far above the price (%)", "pro": "Call OTM [%]"},
    "bt.otm_call.help": "Strike of the call as a percentage above the stock price on the day it's opened.",
    "bt.otm_put": {"plain": "Put this far below the price (%)", "pro": "Put OTM [%]"},
    "bt.otm_put.help": "Strike of the put as a percentage below the stock price on the day it's opened.",
    "bt.wing": {"plain": "Protection wings (%)", "pro": "Wing width [%]"},
    "bt.wing.help": "How much further out the protective options are bought, as a percentage of the price.",
    "bt.sizes": {"plain": "How many of each", "pro": "Leg sizes"},
    "bt.sizes.help": (
        "How many of this leg to trade, per share of stock (1 = one option on one share; a contract covers 100). "
        "Uneven sizes change the bet: 2 calls with 1 put makes a straddle lean towards a rise, 1 call with 2 puts "
        "leans towards a fall. Buying more than 1 share borrows the extra at the interest rate."
    ),
    "bt.exits": {"plain": "When to close early", "pro": "Exit rules"},
    "bt.exits.toggle": {"plain": "Use exit rules (optional)", "pro": "Enable exit rules"},
    "bt.exits.help": (
        "Off by default: the options are held until they expire. Turn this on to close them early once they've "
        "made or lost a set share of the premium, like many traders do. After closing, the strategy waits for "
        "its next regular roll date before opening new options."
    ),
    "bt.tp": {"plain": "Take profit (%)", "pro": "Take profit [%]"},
    "bt.tp.help": (
        "Close once the options have gained this much, as a percentage of the premium. If you were paid a "
        "premium (selling options), 50 means close when they can be bought back for half. If you paid one, "
        "50 means close when they're worth 1.5 times what you paid. 0 turns it off."
    ),
    "bt.sl": {"plain": "Stop loss (%)", "pro": "Stop loss [%]"},
    "bt.sl.help": (
        "Close once the options have lost this much, as a percentage of the premium. 200 on a trade that was "
        "paid $1 closes it when it's down $2. If you paid for the options, the most they can lose is 100%, "
        "so higher values never trigger. 0 turns it off."
    ),
    "bt.exits.note": "Both are a % of the premium; 0 turns one off. Closing early pays the spread and commission again.",
    "bt.exits.summary": "{early} of {total} periods closed early: {tp} at the profit target, {sl} at the stop loss.",
    "bt.exit.expiry": "expiry",
    "bt.exit.take profit": "take profit",
    "bt.exit.stop loss": "stop loss",
    "bt.col.closed": "Closed",
    "bt.col.exit": "Exit",
    "bt.view.single": {"plain": "This strategy", "pro": "Single"},
    "bt.view.compare": {"plain": "Compare ({n}/4)", "pro": "Compare ({n}/4)"},
    "bt.cmp.add": "+ Add to comparison",
    "bt.cmp.add.help": (
        "Saves the strategy on the left (legs, roll period and exit rules) so you can compare up to 4 side by side. "
        "All of them are tested on the same stock, dates and cost assumptions."
    ),
    "bt.cmp.added": "Added {name} to the comparison ({n}/4).",
    "bt.cmp.duplicate": "That strategy is already in the comparison.",
    "bt.cmp.full": "The comparison already has 4 strategies. Remove one first.",
    "bt.cmp.empty": (
        "Nothing to compare yet. Set up a strategy on the left and press + ADD TO COMPARISON, then change it "
        "and add another (up to 4)."
    ),
    "bt.cmp.title": {"plain": "Strategies in the comparison", "pro": "Comparison set"},
    "bt.cmp.remove": "Remove",
    "bt.cmp.clear": "Clear all",
    "bt.cmp.rolls": "every {tenor}d",
    "bt.cmp.exits": "TP {tp} / SL {sl}",
    "bt.cmp.off": "off",
    "bt.cmp.table": {"plain": "Side by side", "pro": "Performance comparison"},
    "bt.cmp.table.pro": "Performance comparison",
    "bt.cmp.col.strategy": "Strategy",
    "bt.cmp.col.total": "Total return %",
    "bt.cmp.col.annual": "Per year %",
    "bt.cmp.col.vol": "Volatility %",
    "bt.cmp.col.sharpe": "Sharpe",
    "bt.cmp.col.dd": "Max drawdown %",
    "bt.cmp.col.win": "Win rate %",
    "bt.cmp.col.premium": "Net premium $",
    "bt.cmp.col.costs": "Costs $",
    "bt.cmp.col.early": "Closed early",
    "bt.cmp.best": (
        "Highest total return: {ret_name} ({ret}). Best return per unit of risk: {sharpe_name} (Sharpe {sharpe}). "
        "Smallest worst fall: {dd_name} ({dd})."
    ),
    "bt.cmp.error": "{name} couldn't be tested on this data: {error}",
    "bt.cmp.report_title": "Strategy comparison",
    "bt.cmp.download": "Download daily values of all (CSV)",
    "bt.paper": {"plain": "For your paper", "pro": "Writing it up"},
    "bt.paper.method": "A methods paragraph you can adapt (copy button at the top right):",
    "bt.paper.checklist_title": "What to include",
    "bt.paper.checklist": (
        "- The stock, the dates and where the prices came from.\n"
        "- Every leg of the strategy, how often it's rolled, and any exit rules.\n"
        "- That option prices come from Black-Scholes and the stock's recent volatility, not real historical "
        "quotes, and what that leaves out (the volatility smile, jumps around earnings, early assignment).\n"
        "- The trading costs you assumed.\n"
        "- Risk next to return: volatility, Sharpe ratio and worst fall from a peak, compared with buy and hold. "
        "Return on its own can make a risky strategy look good.\n"
        "- The report (GENERATE REPORT) or the SHARE LINK in an appendix, so your results can be checked.\n"
        "- A citation for the tool:"
    ),
    "bt.assumptions": {"plain": "Assumptions", "pro": "Model and cost assumptions"},
    "bt.window": {"plain": "Movement measured over", "pro": "Realised-vol window"},
    "bt.window.help": "How many trading days of past prices are used to estimate volatility when pricing each option.",
    "bt.vol_premium": {"plain": "Extra the market charges (%)", "pro": "Vol premium [%]"},
    "bt.vol_premium.help": {
        "plain": "Options usually cost more than past movement alone suggests. 10% prices options at 1.1x the measured movement.",
        "pro": "Pricing vol = realised vol x (1 + premium). Implied vol has historically exceeded realised vol on average.",
    },
    "bt.rate": {"plain": "Interest rate (%)", "pro": "Risk-free [r] (%)"},
    "bt.rate.help": "Interest earned on cash and used in option pricing. Defaults to the current 13-week T-bill rate.",
    "bt.spread": {"plain": "Bid-ask spread (% of option price)", "pro": "Spread [% of price]"},
    "bt.spread.help": "The gap between buying and selling prices. Half of it is paid on each option opened.",
    "bt.commission": {"plain": "Commission per contract ($)", "pro": "Commission [$/contract]"},
    "bt.commission.help": "Broker fee per option contract (100 shares). $0.65 is typical for US retail brokers.",
    "bt.strike_step": {"plain": "Round strikes to", "pro": "Strike increment"},
    "bt.strike_step.help": "Listed options only exist at certain strikes (often $1, $2.50 or $5 apart).",
    "bt.exact": "Exact",
    "bt.range": {"plain": "Dates to test", "pro": "Backtest window"},
    "bt.range.help": "The first few weeks are used to measure volatility before the first trade.",
    "bt.summary": {"plain": "Results", "pro": "Performance"},
    "bt.total_return": {"plain": "Total return", "pro": "Total return"},
    "bt.total_return.pro": "Total return",
    "bt.annual_return": {"plain": "Per year", "pro": "Annualised return"},
    "bt.volatility": {"plain": "Ups and downs", "pro": "Annualised vol"},
    "bt.sharpe": {"plain": "Return per unit of risk", "pro": "Sharpe ratio"},
    "bt.drawdown": {"plain": "Worst fall from a peak", "pro": "Max drawdown"},
    "bt.win_rate": {"plain": "Periods that made money", "pro": "Win rate"},
    "bt.premium": {"plain": "Net option cash received", "pro": "Net premium"},
    "bt.costs": {"plain": "Trading costs paid", "pro": "Costs"},
    "bt.costs_sub": "costs",
    "bt.excess": {"plain": "Compared with owning the shares", "pro": "Excess vs buy & hold"},
    "bt.excess.ahead": "ahead of buy & hold",
    "bt.excess.behind": "behind buy & hold",
    "bt.cycles": "cycles",
    "bt.per_share": "per share",
    "bt.bh_short": "Buy & hold",
    "bt.bh_long": "Buy & hold {ticker}",
    "bt.verdict.better": "beat",
    "bt.verdict.worse": "trailed",
    "bt.explain": (
        "From {start} to {end}, the {strategy} on {ticker} returned {ret}, which {verdict} simply owning the "
        "shares ({bh}). Its worst fall from a peak was {dd}, against {bhdd} for the shares."
    ),
    "bt.caveat": (
        "Options are priced with Black-Scholes from the stock's recent realised volatility (plus the premium above), "
        "not from historical option quotes, which aren't freely available. Treat results as a model-based estimate "
        "and say so in your write-up."
    ),
    "bt.equity": {"plain": "Growth of $100", "pro": "Equity curve (rebased to 100)"},
    "bt.equity.pro": "Equity curve (rebased to 100)",
    "bt.equity.y": {"plain": "Value of $100", "pro": "Value (start = 100)"},
    "bt.drawdown_chart": {"plain": "Falls from the previous high", "pro": "Drawdown"},
    "bt.drawdown_chart.pro": "Drawdown",
    "bt.drawdown.y": {"plain": "Below previous high (%)", "pro": "Drawdown (%)"},
    "bt.cycle_chart": {"plain": "Profit or loss each period", "pro": "P&L by cycle"},
    "bt.cycle_chart.pro": "P&L by cycle",
    "bt.cycle_chart.lede": {
        "plain": "Each bar is one round of options, from opening to expiry, including the stock's move.",
        "pro": "Change in portfolio value over each roll (per share), including the stock leg.",
    },
    "bt.cycle_chart.y": {"plain": "Profit / loss ($)", "pro": "P&L per share"},
    "bt.cycle_pnl": "P&L",
    "bt.log": {"plain": "Every trade", "pro": "Trade log"},
    "bt.log.pro": "Trade log",
    "bt.col.open": "Opened",
    "bt.col.expiry": "Expired",
    "bt.col.spot_open": "Price at open",
    "bt.col.spot_expiry": "Price at expiry",
    "bt.col.sigma": "Vol used",
    "bt.col.strikes": "Strikes",
    "bt.col.premium": "Premium",
    "bt.col.costs": "Costs",
    "bt.col.payoff": "Payoff",
    "bt.col.pnl": "Cycle P&L",
    "bt.download.daily": "Download daily values (CSV)",
    "bt.download.log": "Download trade log (CSV)",
    "bt.report.setup": "Setup",
    "bt.report.results": "Results",
    "bt.report.method": "Method and limitations",
    "bt.report.method_body": (
        "Capital starts at one share's price. Strategies holding stock keep one share throughout; remaining "
        "capital is cash earning the risk-free rate. On each roll date the option legs are opened with strikes "
        "set relative to the current price and an expiry the chosen number of days later, held to expiry, settled "
        "at intrinsic value and replaced. Positions are marked daily with Black-Scholes-Merton.\n"
        "Option prices are model prices: each option is priced from the stock's trailing realised volatility, "
        "scaled by the volatility premium, because historical option quotes are not freely available. Real fills "
        "would differ, especially for short-dated or far out-of-the-money options and around earnings. Early "
        "exercise of American options, margin requirements and taxes are not modelled. Dividends are paid in cash "
        "on shares held. The benchmark buys one share at the start and keeps dividends in cash earning the same rate."
    ),

    # -------------------------------------------------------------- methods
    "methods.title": {"plain": "How it works", "pro": "Methods"},
    "methods.lede": {
        "plain": "A short, jargon-free tour of each method. Switch to Pro for the equations.",
        "pro": "Models, equations and implementation choices. Full derivations and references are in docs/methods.md.",
    },
    "methods.references": "References",
}

# FX pairs: (base, quote, pip size). Rates are illustrative defaults.
FX_PAIRS: dict[str, tuple[str, str, float]] = {
    "EUR/USD": ("EUR", "USD", 1e-4),
    "GBP/USD": ("GBP", "USD", 1e-4),
    "AUD/USD": ("AUD", "USD", 1e-4),
    "USD/CHF": ("USD", "CHF", 1e-4),
    "USD/CAD": ("USD", "CAD", 1e-4),
    "USD/JPY": ("USD", "JPY", 1e-2),
}

CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "CHF ", "CAD": "C$", "AUD": "A$"}

# Methods page: one section per model. ``pro`` is Markdown with LaTeX.
METHODS: list[dict[str, str]] = [
    {
        "title": "Black-Scholes and Garman-Kohlhagen",
        "plain": (
            "If we assume the asset's price wanders randomly with a steady level of jumpiness, and that you could "
            "continuously hedge the option by holding just the right amount of the asset, the option's risk can be "
            "cancelled out completely. A riskless position must earn the interest rate, and that single fact pins "
            "down one exact price: the Black-Scholes formula. For currencies, the second currency's interest rate "
            "plays the role of a dividend (Garman-Kohlhagen)."
        ),
        "pro": r"""
Under geometric Brownian motion $dS_t = (r-q)S_t\,dt + \sigma S_t\,dW_t$ (risk-neutral measure), a European option satisfies

$$
\frac{\partial V}{\partial t} + \tfrac12\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} + (r-q)S\frac{\partial V}{\partial S} - rV = 0,
$$

whose solution for a call or put ($\phi = \pm 1$) is

$$
V = \phi\left[S e^{-qT} N(\phi d_1) - K e^{-rT} N(\phi d_2)\right],\qquad
d_{1,2} = \frac{\ln(S/K) + (r - q \pm \tfrac12\sigma^2)T}{\sigma\sqrt{T}}.
$$

**Garman-Kohlhagen** is the same formula with $r = r_d$ (domestic) and $q = r_f$ (foreign): holding foreign currency earns $r_f$ just as a stock pays a dividend yield.

*Implementation:* fully vectorised; the $\sigma\sqrt{T}\to 0$ limit returns the discounted forward intrinsic value.
""",
        "refs": "Black & Scholes (1973); Merton (1973); Garman & Kohlhagen (1983); Hull, *Options, Futures and Other Derivatives*, ch. 15, 17.",
    },
    {
        "title": "Binomial tree (Cox-Ross-Rubinstein)",
        "plain": (
            "Chop the time until expiry into many small steps. In each step the price can only go up or down by a "
            "set amount. That gives a tree of possible prices. At the end of the tree we know exactly what the "
            "option pays. Working backwards one step at a time, the value at each point is the discounted average "
            "of the two values after it. For options you can use early, at each point we also check whether using "
            "it right now is worth more."
        ),
        "pro": r"""
With $\Delta t = T/N$:

$$
u = e^{\sigma\sqrt{\Delta t}},\quad d = 1/u,\quad p = \frac{e^{(r-q)\Delta t} - d}{u - d},
$$

$$
V_{i,j} = e^{-r\Delta t}\left[p\,V_{i+1,j+1} + (1-p)\,V_{i+1,j}\right],\qquad
V_{i,j}^{\text{Amer}} = \max\!\left(V_{i,j},\ \text{payoff}(S u^{j} d^{\,i-j})\right).
$$

The European price converges to Black-Scholes at $O(1/N)$ with an odd/even oscillation. Δ, Γ and Θ are read off the nodes at steps 1 and 2; ν and ρ by bump-and-reprice.

*Implementation:* one length-$(N{+}1)$ vector overwritten in place: $O(N^2)$ time, $O(N)$ memory.
""",
        "refs": "Cox, Ross & Rubinstein (1979); Hull, ch. 13 and 21; Leisen & Reimer (1996).",
    },
    {
        "title": "Monte Carlo simulation",
        "plain": (
            "Simulate many possible futures for the asset price using random numbers, work out what the option "
            "pays in each, and average them (adjusted for interest). The answer is an estimate, so we also report "
            "how uncertain it is. Two tricks make it more precise for the same effort: pairing every random future "
            "with its mirror image, and correcting the average using a quantity whose true value we already know."
        ),
        "pro": r"""
Exact terminal sampling: $S_T = S_0 \exp\!\left[(r - q - \tfrac12\sigma^2)T + \sigma\sqrt{T}Z\right]$, $Z\sim N(0,1)$, and

$$
\hat V = e^{-rT}\frac1n\sum_{i=1}^n f\big(S_T^{(i)}\big),\qquad \text{SE} = \frac{s}{\sqrt n},\qquad \text{CI}_{95\%} = \hat V \pm 1.96\,\text{SE}.
$$

**Antithetic variates:** average $f(S_T(Z))$ and $f(S_T(-Z))$; SE is computed on the pair means.

**Control variate:** $X = e^{-rT}S_T$ has known mean $S_0e^{-qT}$, so use

$$
\hat V_{cv} = \bar Y - \hat\beta(\bar X - S_0 e^{-qT}),\qquad \hat\beta = \frac{\widehat{\mathrm{Cov}}(Y,X)}{\widehat{\mathrm{Var}}(X)},
$$

with variance $(1-\rho_{XY}^2)\,\mathrm{Var}(\bar Y)$. Greeks use bump-and-reprice with common random numbers.
""",
        "refs": "Glasserman, *Monte Carlo Methods in Financial Engineering* (2003), ch. 4 and 7; Boyle (1977).",
    },
    {
        "title": "Finite differences (Crank-Nicolson)",
        "plain": (
            "The Black-Scholes model can also be written as an equation describing how the option's value changes "
            "with price and time. We lay a fine grid over prices and dates, start from the known value at expiry, "
            "and step backwards in time solving the equation on the grid. Crank-Nicolson is a particularly accurate "
            "and stable way of taking those steps."
        ),
        "pro": r"""
In $x = \ln S$ and $\tau = T - t$: $\;V_\tau = \tfrac12\sigma^2 V_{xx} + (r - q - \tfrac12\sigma^2)V_x - rV \equiv \mathcal{L}V$.

Central differences in $x$ and the θ-scheme in $\tau$:

$$
\left(I - \theta\,\Delta\tau\,L\right)V^{n+1} = \left(I + (1-\theta)\,\Delta\tau\,L\right)V^{n},\qquad \theta = \tfrac12,
$$

a tridiagonal solve per step, second order in $\Delta x$ and $\Delta\tau$.

*Implementation choices:* grid centred exactly on $\ln S_0$; **Rannacher start** (first steps as implicit half-steps) to damp oscillations from the payoff kink; **cell-averaged payoff** at the strike for clean $O(h^2)$ convergence; Dirichlet boundaries $\pm 6\sigma\sqrt T$ away; American exercise by projection $V \leftarrow \max(V, \text{payoff})$.
""",
        "refs": "Crank & Nicolson (1947); Rannacher (1984); Pooley, Vetzal & Forsyth (2003); Wilmott, *Paul Wilmott on Quantitative Finance*, ch. 78.",
    },
    {
        "title": "Greeks",
        "plain": (
            "The Greeks measure how the option's value reacts to each input. For the formula we have exact "
            "expressions. For the other methods we nudge one input up and down slightly, reprice, and measure the "
            "change. Comparing the two is a strong check that everything is consistent."
        ),
        "pro": r"""
Analytical (Black-Scholes-Merton):

$$
\Delta = \phi e^{-qT}N(\phi d_1),\quad
\Gamma = \frac{e^{-qT}n(d_1)}{S\sigma\sqrt T},\quad
\nu = S e^{-qT}n(d_1)\sqrt T,
$$

$$
\Theta = -\frac{S e^{-qT}n(d_1)\sigma}{2\sqrt T} - \phi rKe^{-rT}N(\phi d_2) + \phi qSe^{-qT}N(\phi d_1),\quad
\rho = \phi KTe^{-rT}N(\phi d_2).
$$

Numerical: central differences, e.g. $\Delta \approx \frac{V(S+h)-V(S-h)}{2h}$, $\Gamma \approx \frac{V(S+h)-2V(S)+V(S-h)}{h^2}$, with $O(h^2)$ truncation error. Trees and grids read Δ/Γ directly off their nodes. The identity $\Theta + (r-q)S\Delta + \tfrac12\sigma^2S^2\Gamma = rV$ is unit-tested.
""",
        "refs": "Hull, ch. 19; Haug, *The Complete Guide to Option Pricing Formulas* (2007), ch. 2; Glasserman (2003), ch. 7.",
    },
    {
        "title": "Implied volatility",
        "plain": (
            "Every input to the formula is observable except how much the price will move. So we turn the problem "
            "around: given a price someone paid, find the amount of movement that makes the formula give that "
            "price. We use a fast method that usually converges in a few steps, with a slower, fail-safe method "
            "as a backup."
        ),
        "pro": r"""
Solve $BS(\sigma) = V_{mkt}$. Newton-Raphson with vega:

$$
\sigma_{k+1} = \sigma_k - \frac{BS(\sigma_k) - V_{mkt}}{\nu(\sigma_k)},
$$

safeguarded by a bracket $[\sigma_{lo}, \sigma_{hi}]$ updated each iteration (price is strictly increasing in σ): any step leaving the bracket, or with vanishing vega, is replaced by bisection. Initial guess $\sigma_0 = \sqrt{2\pi/T}\,V/(Se^{-qT})$ (Brenner-Subrahmanyam). Prices outside the no-arbitrage bounds are rejected. Surfaces use OTM options (puts below the forward, calls above).
""",
        "refs": "Brenner & Subrahmanyam (1988); Press et al., *Numerical Recipes* (2007), §9.4; Gatheral, *The Volatility Surface* (2006).",
    },
]


def t(key: str, mode: str = PLAIN, **fmt: object) -> str:
    """Look up ``key`` for ``mode`` and fill in any ``{placeholders}``.

    Missing keys are returned in brackets so they are easy to spot in the UI.
    """
    entry = TEXT.get(key)
    if entry is None:
        return f"[{key}]"
    if isinstance(entry, dict):
        if mode == PRO:
            text = entry["pro"]
        elif mode == SIMPLE:
            text = entry.get("simple", entry["plain"])
        else:
            text = entry["plain"]
    else:
        text = entry
    return text.format(**fmt) if fmt else text
