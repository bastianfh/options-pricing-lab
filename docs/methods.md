# Methods

This note documents the models in `pricing/`, the numerical choices behind them,
and how each one is validated. Notation: spot $S$, strike $K$, time to expiry $T$
(years), risk-free rate $r$, continuous dividend yield $q$ (for FX, the foreign
rate $r_f$), volatility $\sigma$, $\phi = +1$ for a call and $-1$ for a put,
$N(\cdot)$ and $n(\cdot)$ the standard normal CDF and PDF.

## 1. Black-Scholes-Merton and Garman-Kohlhagen

**Model.** Under the risk-neutral measure the asset follows geometric Brownian motion,
$dS_t = (r - q)S_t\,dt + \sigma S_t\,dW_t$. A self-financing delta hedge removes
all risk, so the option value $V(S,t)$ satisfies the Black-Scholes PDE

$$
\frac{\partial V}{\partial t} + \tfrac12\sigma^2 S^2 \frac{\partial^2 V}{\partial S^2} + (r-q)S\frac{\partial V}{\partial S} - rV = 0 .
$$

**Closed form** (`pricing/models/black_scholes.py`):

$$
V = \phi\left[S e^{-qT} N(\phi d_1) - K e^{-rT} N(\phi d_2)\right], \qquad
d_{1,2} = \frac{\ln(S/K) + (r - q \pm \tfrac12\sigma^2)T}{\sigma\sqrt T}.
$$

**Garman-Kohlhagen** is the same formula with $r = r_d$ and $q = r_f$, because a
unit of foreign currency earns the foreign rate just as a share earns its dividend
yield. Spot is quoted as domestic per foreign (e.g. USD per EUR).

**Edge cases.** As $\sigma\sqrt T \to 0$ the price tends to the discounted forward
intrinsic value $\max(\phi(Se^{-qT} - Ke^{-rT}), 0)$, which the code returns
explicitly instead of dividing by zero.

**Validation.** Hull Example 15.6 (call 4.7594, put 0.8086), Haug's dividend-yield
put (2.4648) and Garman-Kohlhagen call (0.0291); put-call parity
$C - P = Se^{-qT} - Ke^{-rT}$ to $10^{-10}$; no-arbitrage bounds; monotonicity in $\sigma$.

## 2. Binomial tree (Cox-Ross-Rubinstein)

With $\Delta t = T/N$, the tree moves up by $u = e^{\sigma\sqrt{\Delta t}}$ or down
by $d = 1/u$, with risk-neutral probability $p = (e^{(r-q)\Delta t} - d)/(u-d)$.
Backward induction from the payoff:

$$
V_{i,j} = e^{-r\Delta t}\left[p V_{i+1,j+1} + (1-p)V_{i+1,j}\right], \qquad
V^{\text{Amer}}_{i,j} = \max\left(V_{i,j},\ \text{payoff}(S u^{2j-i})\right).
$$

**Implementation.** One vector of length $N+1$ is overwritten in place: $O(N^2)$
time, $O(N)$ memory. $p \notin [0,1]$ (too few steps for the carry) raises an error.

**Greeks.** Δ, Γ and Θ are read off the nodes at steps 1 and 2 (Hull §21.1). Bumping
spot on a tree is unreliable: the CRR price oscillates in $S$ with period
$2\sigma\sqrt{\Delta t}$ in log-spot, so a 1% bump with $N = 500$ aliases badly
(gamma came out 26% too high before this change). ν and ρ use bump-and-reprice.

**Convergence.** The European price converges at $O(1/N)$. Off the money the error
oscillates as the strike moves between terminal nodes (Leisen & Reimer, 1996), so the
test checks that $N\cdot|\varepsilon_N|$ stays bounded and fits the order on a dense
sweep of $N$.

**Validation.** Hull's five-step American put (4.49); American ≥ European ≥ intrinsic;
American call without dividends equals European (Merton, 1973); measured order ≈ 1.00.

## 3. Monte Carlo

The terminal price is sampled exactly, so there is no time-discretisation bias:

$$
S_T = S_0 \exp\left[(r - q - \tfrac12\sigma^2)T + \sigma\sqrt T Z\right], \qquad
\hat V = e^{-rT}\frac1n\sum_i f(S_T^{(i)}), \qquad \text{SE} = s/\sqrt n .
$$

**Antithetic variates.** Each $Z$ is paired with $-Z$ and the two payoffs averaged.
The pair means are i.i.d., so the standard error is computed from them, not from the
$2n$ correlated paths (a common mistake that overstates precision).

**Control variate.** $X = e^{-rT}S_T$ has known mean $S_0e^{-qT}$. The estimator
$\bar Y - \hat\beta(\bar X - S_0e^{-qT})$ with $\hat\beta = \widehat{\mathrm{Cov}}(Y,X)/\widehat{\mathrm{Var}}(X)$
has variance $(1-\rho^2_{XY})\mathrm{Var}(\bar Y)$. Estimating $\hat\beta$ in-sample
adds an $O(1/n)$ bias, negligible beside the $O(1/\sqrt n)$ standard error.

A side effect worth noting: since $C - P = e^{-rT}(S_T - K)$ is linear in the control,
calls and puts get *identical* standard errors with the control variate on, and
Monte Carlo put-call parity holds to machine precision.

**Greeks.** Bump-and-reprice with common random numbers (fixed seed). Without them the
difference of two independent estimates is dominated by noise.

**Validation.** Every variant within 4 SE of Black-Scholes; empirical 95% CI coverage
across 400 independent runs lies in [92%, 98%]; SE scales as $n^{-1/2}$ (measured
order 0.50); antithetic + control variate gives a variance reduction of ≈ 20×.

## 4. Finite differences (Crank-Nicolson)

In $x = \ln S$ and $\tau = T - t$ the PDE has constant coefficients:
$V_\tau = \tfrac12\sigma^2V_{xx} + (r - q - \tfrac12\sigma^2)V_x - rV \equiv \mathcal L V$.
Central differences in $x$ and the θ-scheme in $\tau$ give a tridiagonal system per step,

$$
(I - \theta\Delta\tau L)V^{n+1} = (I + (1-\theta)\Delta\tau L)V^n, \qquad \theta = \tfrac12,
$$

solved with `scipy.linalg.solve_banded`.

| Choice | Reason |
|---|---|
| Grid centred exactly on $\ln S_0$ | price read at a node, no interpolation error |
| Half-width $6\sigma\sqrt T + \lvert\ln(K/S)\rvert$ | truncation error below $10^{-9}$ |
| Rannacher start: first 2 steps as 4 implicit half-steps | Crank-Nicolson alone lets the payoff kink ring, especially in Γ |
| Cell-averaged payoff in the strike's cell | without it the error depends on where $K$ falls between nodes and convergence looks erratic (Pooley, Vetzal & Forsyth, 2003) |
| Dirichlet boundaries from asymptotic values | simple and accurate this far out |
| American: $V \leftarrow \max(V, \text{payoff})$ after each step | simple and stable; first order near the exercise boundary |

**Validation.** Error within $10^{-3}$ at the default 400×400 grid; measured order
1.99 (error ratio ≈ 4.0 per doubling); grid Δ and Γ match the closed form to $10^{-4}$;
American put matches the 4000-step tree to $5\times10^{-3}$.

## 5. Greeks

Closed form (Hull ch. 19):

$$
\Delta = \phi e^{-qT}N(\phi d_1), \quad \Gamma = \frac{e^{-qT}n(d_1)}{S\sigma\sqrt T}, \quad \nu = Se^{-qT}n(d_1)\sqrt T,
$$
$$
\Theta = -\frac{Se^{-qT}n(d_1)\sigma}{2\sqrt T} - \phi rKe^{-rT}N(\phi d_2) + \phi qSe^{-qT}N(\phi d_1), \quad \rho = \phi KTe^{-rT}N(\phi d_2).
$$

The library returns raw derivatives (ν per 1.00 of σ, Θ per year, ρ per 1.00 of $r$);
the UI converts to market units (per vol point, per day, per 1%). Numerical Greeks use
central differences with $O(h^2)$ truncation error; the default spot bump is 0.5% (1%
for Monte Carlo, where smaller bumps amplify noise in Γ).

**Validation.** Hull Example 19.1 values; parity relations ($\Delta_c - \Delta_p = e^{-qT}$,
equal Γ and ν); the PDE identity $\Theta + (r-q)S\Delta + \tfrac12\sigma^2S^2\Gamma = rV$
to $10^{-10}$; numerical vs analytical for every model.

## 6. Implied volatility

Solve $BS(\sigma) = V_{\text{mkt}}$ by Newton-Raphson, $\sigma_{k+1} = \sigma_k - (BS(\sigma_k) - V)/\nu(\sigma_k)$,
inside a bracket $[\sigma_{lo}, \sigma_{hi}]$ that is tightened every iteration (price is
strictly increasing in σ, so the sign of the error says which side the root is on). A
step that leaves the bracket, or a vanishing vega, falls back to bisection, so
convergence is guaranteed (cf. `rtsafe`, *Numerical Recipes* §9.4). Start:
$\sigma_0 = \sqrt{2\pi/T}\,V/(Se^{-qT})$ (Brenner-Subrahmanyam). Stop when the price error
is below $10^{-12}$ or the σ update is below $10^{-12}$; the second criterion matters
for far-OTM options whose prices are too small for an absolute price tolerance to pin σ.

Prices outside $(\max(\phi(Se^{-qT}-Ke^{-rT}),0),\ Se^{-qT}\text{ or }Ke^{-rT})$ are rejected.

**Surface.** For each grid point the OTM option is used (puts below the forward, calls
above), as in market practice. The demo surface prices a parametric smile in
standardised moneyness $m = \ln(K/F)/\sqrt T$,
$\sigma = \sigma_{ATM}(T) + \text{skew}\cdot m + \text{curv}\cdot m^2$, then inverts the
prices. This is an illustration, not an arbitrage-free parameterisation such as SVI.

**Validation.** Round trip price → σ → price over 160 combinations of type, strike,
expiry and σ; recovered σ to relative $10^{-5}$; bisection fallback exercised from a
deliberately bad start; full surface recovery to $10^{-7}$ wherever the price exceeds $10^{-8}$.

## References

- Black, F. & Scholes, M. (1973). The pricing of options and corporate liabilities. *JPE* 81(3).
- Merton, R. (1973). Theory of rational option pricing. *Bell J. Econ.* 4(1).
- Garman, M. & Kohlhagen, S. (1983). Foreign currency option values. *J. Int. Money Finance* 2(3).
- Cox, J., Ross, S. & Rubinstein, M. (1979). Option pricing: a simplified approach. *JFE* 7(3).
- Leisen, D. & Reimer, M. (1996). Binomial models for option valuation: examining and improving convergence. *Applied Math. Finance* 3(4).
- Boyle, P. (1977). Options: a Monte Carlo approach. *JFE* 4(3).
- Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer.
- Crank, J. & Nicolson, P. (1947). A practical method for numerical evaluation of solutions of PDEs of the heat-conduction type. *Proc. Camb. Phil. Soc.* 43(1).
- Rannacher, R. (1984). Finite element solution of diffusion problems with irregular data. *Numer. Math.* 43.
- Pooley, D., Vetzal, K. & Forsyth, P. (2003). Convergence remedies for non-smooth payoffs in option pricing. *J. Comp. Finance* 6(4).
- Brenner, M. & Subrahmanyam, M. (1988). A simple formula to compute the implied standard deviation. *FAJ* 44(5).
- Hull, J. *Options, Futures, and Other Derivatives*, 11th ed. Pearson.
- Haug, E. G. (2007). *The Complete Guide to Option Pricing Formulas*, 2nd ed. McGraw-Hill.
- Wilmott, P. (2006). *Paul Wilmott on Quantitative Finance*, 2nd ed. Wiley.
- Gatheral, J. (2006). *The Volatility Surface*. Wiley.
