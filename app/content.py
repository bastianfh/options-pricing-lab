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

PLAIN, PRO = "Plain English", "Pro"
MODES = (PLAIN, PRO)

TEXT: dict[str, Entry] = {
    # ------------------------------------------------------------------ app
    "app.name": "Options Pricing Lab",
    "app.tagline": {
        "plain": "Find out what an option is worth, why, and how sure we can be.",
        "pro": "A from-scratch options pricing and risk library, made interactive.",
    },
    "mode.label": "Explanations",
    "mode.help": (
        "Plain English translates every term, adds a one-line explanation under each result and keeps "
        "advanced settings on sensible defaults. Pro shows standard notation, every parameter, "
        "technical diagnostics and the equations. Both use exactly the same pricing engine."
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
    "sidebar.footer": "Pricing engine written from scratch in NumPy & SciPy. No pricing libraries.",
    "sidebar.source": "Source code on GitHub",
    "disclaimer": "For education and research. Model prices are not trading advice.",

    # --------------------------------------------------------------- inputs
    "inputs.contract": {"plain": "The option", "pro": "Contract"},
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
    "in.option_type.call": {"plain": "Call · buy", "pro": "Call"},
    "in.option_type.put": {"plain": "Put · sell", "pro": "Put"},
    "in.exercise.label": {"plain": "When can you use it?", "pro": "Exercise style"},
    "in.exercise.help": {
        "plain": "European options can only be used on the expiry date. American options can be used any day until then, which can make them worth a little more.",
        "pro": "European: exercise at T only. American: any time up to T (priced by tree and PDE; no closed form).",
    },
    "in.exercise.european": {"plain": "Only at expiry", "pro": "European"},
    "in.exercise.american": {"plain": "Any time", "pro": "American"},
    "in.S.label": {"plain": "Price of the asset today", "pro": "Spot (S)"},
    "in.S.help": {
        "plain": "What one share (or one unit of currency) costs right now.",
        "pro": "Current price of the underlying, S_0.",
    },
    "in.K.label": {"plain": "Agreed price", "pro": "Strike (K)"},
    "in.K.help": {
        "plain": "The price you are allowed to buy (call) or sell (put) at. Also called the strike.",
        "pro": "Strike price K.",
    },
    "in.days.label": {"plain": "Days until it expires", "pro": "Days to expiry"},
    "in.days.help": {
        "plain": "How long the option lasts. More time means more chance of a big move, so options with longer lives usually cost more.",
        "pro": "Calendar days; T = days / 365 (ACT/365).",
    },
    "in.vol.label": {"plain": "How much the price tends to move (%)", "pro": "Volatility σ (%)"},
    "in.vol.help": {
        "plain": "How jumpy the asset is, as a yearly percentage. 20% means a typical yearly move of about ±20%. Big-tech stocks are often 25–40%, major currency pairs 5–10%.",
        "pro": "Annualised volatility of log-returns, σ.",
    },
    "in.r.label": {"plain": "Interest rate (%)", "pro": "Risk-free rate r (%)"},
    "in.r.help": {
        "plain": "What you'd earn on cash in the bank per year. Higher rates make calls slightly more valuable and puts slightly less.",
        "pro": "Continuously compounded risk-free rate r.",
    },
    "in.r_fx.label": {"plain": "Interest rate of the {quote} (%)", "pro": "Domestic rate r_d ({quote}, %)"},
    "in.r_fx.help": {
        "plain": "What you'd earn per year holding the second currency of the pair in the bank.",
        "pro": "Continuously compounded domestic (quote currency) rate r_d.",
    },
    "in.q.label": {"plain": "Dividend yield (%)", "pro": "Dividend yield q (%)"},
    "in.q.help": {
        "plain": "Cash the company pays shareholders per year, as a % of the share price. Dividends lower call prices and raise put prices.",
        "pro": "Continuous dividend yield q.",
    },
    "in.q_fx.label": {"plain": "Interest rate of the {base} (%)", "pro": "Foreign rate r_f ({base}, %)"},
    "in.q_fx.help": {
        "plain": "What you'd earn per year holding the first currency of the pair. It works like a dividend.",
        "pro": "Continuously compounded foreign (base currency) rate r_f; enters as q = r_f.",
    },
    "in.steps.label": "Binomial steps N",
    "in.steps.help": "Time steps in the CRR tree. Error ~ O(1/N); cost ~ O(N²).",
    "in.paths.label": "Monte Carlo paths",
    "in.paths.help": "Simulated terminal prices. Standard error ~ O(1/√n).",
    "in.antithetic.label": "Antithetic variates",
    "in.antithetic.help": "Pair each draw Z with −Z. Reduces variance for monotone payoffs.",
    "in.cv.label": "Control variate",
    "in.cv.help": "Use the discounted terminal price (known mean S·e^(−qT)) as a control variate with optimal β.",
    "in.seed.label": "Random seed",
    "in.seed.help": "Fixed seed makes Monte Carlo reproducible and enables common random numbers for Greeks.",
    "in.grid.label": "PDE grid size (M = N)",
    "in.grid.help": "Space and time steps for Crank-Nicolson. Error ~ O(ΔS² + Δt²).",
    "in.T_years": "T = {T:.4f} years",

    # --------------------------------------------------------------- presets
    "presets.title": {"plain": "Try an example", "pro": "Presets"},
    "presets.load": {"plain": "Load example →", "pro": "Load →"},
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
    "home.quick.open": "Open full pricer",
    "home.sections": {"plain": "Explore", "pro": "Sections"},
    "home.stat.methods": {"plain": "ways to price an option", "pro": "pricing methods"},
    "home.stat.tests": {"plain": "automated checks", "pro": "unit tests in CI"},
    "home.stat.libs": {"plain": "pricing libraries used", "pro": "external pricing libraries"},
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
        "plain": "Describe the option on the left. Its value, and what drives it, appear on the right.",
        "pro": "One contract, four independent methods, analytical vs numerical Greeks.",
    },
    "pricer.hero.label": {"plain": "What this option is worth today", "pro": "{model} price"},
    "pricer.hero.label_american": {"plain": "What this option is worth today", "pro": "American price (binomial tree)"},
    "pricer.hero.explain_stock": {
        "plain": "This option costs {price}, about {pct:.1f}% of the share price. {moneyness}",
        "pro": "d₁ = {d1:.4f} · d₂ = {d2:.4f} · forward F = {forward} · {pct:.2f}% of spot",
    },
    "pricer.hero.explain_fx": {
        "plain": "This option costs {price} {quote} per 1 {base} ({pct:.2f}% of spot), so about {notional} on a {base} 1 million deal. {moneyness}",
        "pro": "{pips} {quote} pips · {notional} per {base} 1m notional · d₁ = {d1:.4f} · forward F = {forward}",
    },
    "pricer.hero.explain_american": {
        "plain": "This option costs {price}. Being able to use it early adds {premium} compared with an only-at-expiry option.",
        "pro": "Early-exercise premium over European: {premium} · PDE: {pde}",
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
    "pricer.unavailable": {"plain": "Only for options used at expiry", "pro": "European only"},
    "pricer.runtime": "{ms:.1f} ms",
    "pricer.ci": {"plain": "Likely range {lo} to {hi}", "pro": "95% CI [{lo}, {hi}] · SE {se}"},
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
        "pro": "{steps:,} steps · O(1/N)",
    },
    "method.monte_carlo.desc": {
        "plain": "Averages the payoff over {paths:,} simulated futures.",
        "pro": "{paths:,} paths · {vr}",
    },
    "method.finite_difference.desc": {
        "plain": "Solves the pricing equation on a fine grid.",
        "pro": "{grid}×{grid} grid · Rannacher start",
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
        "pro": "Black-Scholes Greeks across spot and time to expiry for the contract set below.",
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
        "pro": "Expiry payoff and Black-Scholes mark-to-model P&L for single and multi-leg strategies (entry at model prices, no financing or costs).",
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
    "vs.atm": {"plain": "Typical expected movement (%)", "pro": "ATM vol σ_ATM (%)"},
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
        text = entry["pro"] if mode == PRO else entry["plain"]
    else:
        text = entry
    return text.format(**fmt) if fmt else text
