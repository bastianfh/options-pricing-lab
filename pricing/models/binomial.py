"""Cox-Ross-Rubinstein binomial tree for European and American options.

Reference: Cox, J., Ross, S. & Rubinstein, M. (1979), "Option pricing: a
simplified approach", *Journal of Financial Economics* 7(3), 229-263; Hull,
ch. 13 and 21.

Over each step of length :math:`\\Delta t = T/N` the asset moves up by
:math:`u` or down by :math:`d` with risk-neutral probability :math:`p`:

.. math::

    u = e^{\\sigma\\sqrt{\\Delta t}}, \\qquad d = 1/u, \\qquad
    p = \\frac{e^{(r-q)\\Delta t} - d}{u - d}

The option value is found by backward induction from the payoff at expiry,

.. math::

    V_{i,j} = e^{-r\\Delta t}\\left[p V_{i+1,j+1} + (1-p) V_{i+1,j}\\right],

and for American exercise each node is replaced by
:math:`\\max(V_{i,j}, \\text{payoff}(S_{i,j}))`.

The European CRR price converges to Black-Scholes at rate :math:`O(1/N)`,
with an oscillation between odd and even :math:`N` caused by where the strike
falls relative to the terminal nodes (Leisen & Reimer, 1996).
"""

from __future__ import annotations

from typing import Union

import numpy as np

from pricing.utils import (
    ExerciseStyle,
    OptionType,
    payoff,
    to_exercise_style,
    to_option_type,
    validate_inputs,
)


def crr_parameters(T: float, r: float, sigma: float, n_steps: int, q: float = 0.0) -> tuple[float, float, float]:
    """Return the CRR up factor ``u``, down factor ``d`` and risk-neutral probability ``p``.

    Raises ``ValueError`` if ``p`` falls outside ``[0, 1]``, which happens when
    the step is too coarse relative to the carry, i.e. when
    ``sigma * sqrt(dt) < |r - q| * dt``. Increasing ``n_steps`` fixes it.
    """
    dt = T / n_steps
    u = float(np.exp(sigma * np.sqrt(dt)))
    d = 1.0 / u
    p = float((np.exp((r - q) * dt) - d) / (u - d))
    if not 0.0 <= p <= 1.0:
        raise ValueError(
            f"Risk-neutral probability p={p:.4f} is outside [0, 1]; use more steps (n_steps={n_steps})."
        )
    return u, d, p


def binomial_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    exercise: Union[str, ExerciseStyle] = "european",
    n_steps: int = 500,
) -> float:
    """Price a vanilla option on a CRR binomial tree.

    Parameters
    ----------
    S, K, T, r, sigma, q
        Spot, strike, years to expiry, risk-free rate, volatility, continuous yield.
    option_type
        ``"call"`` or ``"put"``.
    exercise
        ``"european"`` or ``"american"``.
    n_steps
        Number of time steps ``N``. Cost is ``O(N^2)`` time and ``O(N)`` memory.

    Returns
    -------
    float
        Option value at time 0.

    Notes
    -----
    The tree is never stored. A single vector of length ``N + 1`` holds the
    values at the current time slice and is overwritten as we step backwards.
    Node ``j`` at step ``i`` has asset price ``S u^j d^{i-j} = S u^{2j - i}``.
    """
    validate_inputs(S, K, T, sigma)
    opt = to_option_type(option_type)
    style = to_exercise_style(exercise)
    if n_steps < 1:
        raise ValueError("n_steps must be at least 1.")
    if T == 0.0:
        return float(payoff(S, K, opt))
    if sigma <= 0.0:
        raise ValueError("The binomial tree requires sigma > 0.")

    return float(_backward_induction(S, K, T, r, sigma, q, opt, style, n_steps)[0][0])


def _backward_induction(
    S: float, K: float, T: float, r: float, sigma: float, q: float,
    opt: OptionType, style: ExerciseStyle, n_steps: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Roll the tree back to time 0, returning the value vectors at steps 0, 1 and 2.

    Steps 1 and 2 are kept because the tree Greeks are read off them; entries
    for steps beyond ``n_steps`` are empty arrays.
    """
    u, _, p = crr_parameters(T, r, sigma, n_steps, q)
    disc = np.exp(-r * T / n_steps)
    disc_p, disc_1mp = disc * p, disc * (1.0 - p)

    # Terminal asset prices, j = 0 (all down moves) ... N (all up moves).
    j = np.arange(n_steps + 1)
    values = payoff(S * u ** (2 * j - n_steps), K, opt)
    kept: dict[int, np.ndarray] = {n_steps: values} if n_steps <= 2 else {}

    american = style is ExerciseStyle.AMERICAN
    for i in range(n_steps - 1, -1, -1):
        values = disc_p * values[1:] + disc_1mp * values[:-1]
        if american:
            spot_i = S * u ** (2 * np.arange(i + 1) - i)
            np.maximum(values, payoff(spot_i, K, opt), out=values)
        if i <= 2:
            kept[i] = values
    empty = np.empty(0)
    return kept[0], kept.get(1, empty), kept.get(2, empty)


def binomial_tree_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: Union[str, OptionType] = "call",
    exercise: Union[str, ExerciseStyle] = "european",
    n_steps: int = 500,
) -> tuple[float, float, float, float]:
    """Price, delta, gamma and theta read directly from the tree (Hull, sec. 21.1).

    With :math:`f_{i,j}` the value at step :math:`i`, node :math:`j`:

    .. math::

        \\Delta = \\frac{f_{1,1} - f_{1,0}}{Su - Sd}, \\qquad
        \\Gamma = \\frac{\\dfrac{f_{2,2} - f_{2,1}}{Su^2 - S} - \\dfrac{f_{2,1} - f_{2,0}}{S - Sd^2}}
                       {\\tfrac12 (Su^2 - Sd^2)}, \\qquad
        \\Theta = \\frac{f_{2,1} - f_{0,0}}{2\\Delta t}

    These are finite differences on the lattice itself. They avoid the
    problem with bump-and-reprice on a tree: the CRR price "wiggles" as a
    function of ``S`` with period ``2 sigma sqrt(dt)`` in log-spot, so a spot
    bump of similar size gives a badly aliased gamma.

    Returns
    -------
    (price, delta, gamma, theta)
    """
    validate_inputs(S, K, T, sigma)
    if n_steps < 3 or T <= 0.0 or sigma <= 0.0:
        raise ValueError("Tree Greeks need n_steps >= 3, T > 0 and sigma > 0.")
    opt, style = to_option_type(option_type), to_exercise_style(exercise)
    u, d, _ = crr_parameters(T, r, sigma, n_steps, q)
    f0, f1, f2 = _backward_induction(S, K, T, r, sigma, q, opt, style, n_steps)
    dt = T / n_steps

    delta = (f1[1] - f1[0]) / (S * u - S * d)
    s_uu, s_dd = S * u * u, S * d * d
    delta_up = (f2[2] - f2[1]) / (s_uu - S)
    delta_dn = (f2[1] - f2[0]) / (S - s_dd)
    gamma = (delta_up - delta_dn) / (0.5 * (s_uu - s_dd))
    theta = (f2[1] - f0[0]) / (2 * dt)
    return float(f0[0]), float(delta), float(gamma), float(theta)
