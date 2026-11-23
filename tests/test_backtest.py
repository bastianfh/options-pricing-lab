"""Backtest engine: accounting identities and known-answer cases."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pricing.backtest import (
    TEMPLATE_NAMES,
    BacktestConfig,
    LegTemplate,
    performance,
    run_backtest,
    template_legs,
)


def market(n: int = 600, sigma: float = 0.25, seed: int = 0, mu: float = 0.06) -> tuple[pd.DatetimeIndex, np.ndarray]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    dt = 1 / 252
    r = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * rng.standard_normal(n - 1)
    return dates, 100 * np.exp(np.concatenate([[0.0], np.cumsum(r)]))


def test_buy_and_hold_matches_the_benchmark_exactly() -> None:
    dates, p = market()
    divs = np.zeros_like(p)
    divs[[100, 200, 300]] = 0.5
    res = run_backtest(dates, p, BacktestConfig(template_legs("buy_and_hold")), dividends=divs)
    np.testing.assert_allclose(res.value, res.benchmark, rtol=1e-12)
    assert res.cycles == []


def test_conversion_grows_at_the_risk_free_rate_while_hedged() -> None:
    """Long stock + long put - short call at the same strike is riskless (put-call parity):
    while options are open, the portfolio must grow at exactly r, whatever the stock does."""
    dates, p = market(sigma=0.4, seed=3)
    legs = (LegTemplate("stock", 1), LegTemplate("put", 1, 1.0), LegTemplate("call", -1, 1.0))
    cfg = BacktestConfig(legs, tenor_days=30, rate=0.05)
    res = run_backtest(dates, p, cfg)
    last_expiry = res.cycles[-1].expiry_date
    hedged = res.dates <= last_expiry
    v, d = res.value[hedged], res.dates[hedged]
    growth = np.diff(np.log(v))
    expected = 0.05 * pd.Series(d).diff().dt.days.to_numpy()[1:] / 365.0
    np.testing.assert_allclose(growth, expected, atol=1e-10)


def test_far_out_of_the_money_covered_call_is_almost_buy_and_hold() -> None:
    dates, p = market()
    res = run_backtest(dates, p, BacktestConfig(template_legs("covered_call", otm_call=2.0)))
    assert np.max(np.abs(res.value / res.benchmark - 1)) < 1e-6


def test_costs_reduce_performance() -> None:
    dates, p = market()
    legs = template_legs("long_straddle")
    free = run_backtest(dates, p, BacktestConfig(legs))
    costly = run_backtest(dates, p, BacktestConfig(legs, spread=0.10, commission=0.0065))
    assert costly.value[-1] < free.value[-1]
    assert costly.total_costs > 0 == free.total_costs


def test_roll_schedule_and_settlement_at_intrinsic_value() -> None:
    dates, p = market(n=400)
    cfg = BacktestConfig(template_legs("covered_call", otm_call=0.05), tenor_days=28)
    res = run_backtest(dates, p, cfg)
    span = (res.dates[-1] - res.dates[0]).days
    assert span // 28 - 1 <= len(res.cycles) <= span // 28 + 1
    for c in res.cycles:
        (k,) = c.strikes
        assert c.payoff == pytest.approx(-max(c.spot_expiry - k, 0.0))
        assert (c.expiry_date - c.open_date).days >= 28
        assert c.premium > 0  # selling a call collects premium


def test_strike_rounding_and_vol_premium() -> None:
    dates, p = market()
    rounded = run_backtest(dates, p, BacktestConfig(template_legs("covered_call"), strike_step=5.0))
    assert all(k % 5 == 0 for c in rounded.cycles for k in c.strikes)
    rich = run_backtest(dates, p, BacktestConfig(template_legs("covered_call"), vol_premium=0.2))
    plain = run_backtest(dates, p, BacktestConfig(template_legs("covered_call")))
    assert rich.total_premium > plain.total_premium


def test_date_range_and_warm_up() -> None:
    dates, p = market()
    res = run_backtest(dates, p, BacktestConfig(template_legs("buy_and_hold"), vol_window=21),
                       start=dates[0], end=dates[300])
    assert res.dates[0] == dates[21] and res.dates[-1] == dates[300]
    with pytest.raises(ValueError):
        run_backtest(dates[:22], p[:22], BacktestConfig(template_legs("buy_and_hold")))


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_every_template_runs(name: str) -> None:
    dates, p = market(n=300)
    res = run_backtest(dates, p, BacktestConfig(template_legs(name)))
    assert np.isfinite(res.value).all() and len(res.value) == len(res.benchmark)
    stats = performance(res.value, res.dates, rate=0.04)
    assert set(stats) == {"total_return", "annual_return", "annual_volatility", "sharpe", "max_drawdown"}


def test_iron_condor_strikes_are_ordered() -> None:
    legs = template_legs("iron_condor", otm_call=0.05, otm_put=0.05, wing=0.05)
    assert [leg.moneyness for leg in legs] == pytest.approx([0.90, 0.95, 1.05, 1.10])


def test_invalid_configs_raise() -> None:
    with pytest.raises(ValueError):
        BacktestConfig(())
    with pytest.raises(ValueError):
        BacktestConfig(template_legs("collar"), spread=-0.1)
    with pytest.raises(ValueError):
        template_legs("martingale")


# --------------------------------------------------------------------------- custom strategies

from pricing.backtest import cycle_payoff, legs_from_code, legs_to_code, upside_exposure  # noqa: E402


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_leg_codes_round_trip_every_template(name: str) -> None:
    legs = template_legs(name, 0.05, 0.07, 0.03)
    back = legs_from_code(legs_to_code(legs))
    assert [(b.kind, b.quantity) for b in back] == [(a.kind, a.quantity) for a in legs]
    for a, b in zip(legs, back):
        if a.kind != "stock":
            assert b.moneyness == pytest.approx(a.moneyness)


def test_leg_code_format_is_readable() -> None:
    assert legs_to_code(template_legs("covered_call")) == "s+1,c-1@105"
    assert legs_from_code(" s+1, p+2@90 ,c-0.5@110") == (
        LegTemplate("stock", 1), LegTemplate("put", 2, 0.9), LegTemplate("call", -0.5, 1.1))


@pytest.mark.parametrize("bad", ["", "x+1", "c+1", "c0@100", "c+11@100", "c+1@0", "s+1@100", "c+nan@100",
                                 ",".join(["c+1@100"] * 9)])
def test_bad_leg_codes_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        legs_from_code(bad)


def test_upside_exposure_flags_naked_short_calls() -> None:
    assert upside_exposure(template_legs("covered_call")) == 0
    assert upside_exposure(legs_from_code("c-1@105")) < 0
    assert upside_exposure(legs_from_code("s+1,c-2@105")) < 0
    assert upside_exposure(template_legs("bull_call_spread")) == 0


def test_cycle_payoff_matches_textbook_shapes() -> None:
    grid = np.linspace(50, 150, 201)
    cc = cycle_payoff(template_legs("covered_call"), grid, 30, 0.04, 0.25)
    assert np.allclose(np.diff(cc[grid >= 105]), 0)  # capped above the strike
    assert np.allclose(np.diff(cc[grid <= 100]), 0.5)  # moves one-for-one with the stock below it
    straddle = cycle_payoff(template_legs("long_straddle"), grid, 30, 0.0, 0.25)
    assert straddle.min() == pytest.approx(straddle[100]) and straddle[100] < 0  # worst at the strike
    # Conversion (long stock, long put, short call, same strike) locks in a fixed P&L.
    conv = cycle_payoff((LegTemplate("stock", 1), LegTemplate("put", 1), LegTemplate("call", -1)), grid, 30, 0.04, 0.3)
    assert np.ptp(conv) < 1e-9


def test_custom_strategy_runs_like_the_matching_template() -> None:
    dates, p = market()
    a = run_backtest(dates, p, BacktestConfig(template_legs("collar")))
    b = run_backtest(dates, p, BacktestConfig(legs_from_code("s+1,p+1@95,c-1@105")))
    np.testing.assert_allclose(a.value, b.value)


from pricing.backtest import sized_legs, sizes_from_code, sizes_to_code  # noqa: E402


def test_sized_legs_keep_the_side_and_strike() -> None:
    strap = sized_legs(template_legs("long_straddle"), (2, 1))
    assert strap == (LegTemplate("call", 2, 1.0), LegTemplate("put", 1, 1.0))
    ratio = sized_legs(template_legs("bull_call_spread"), (1, 2))
    assert [leg.quantity for leg in ratio] == [1, -2]
    assert upside_exposure(ratio) < 0  # a 1x2 call spread is naked short one call


def test_doubling_every_leg_doubles_the_option_pnl() -> None:
    dates, p = market()
    one = run_backtest(dates, p, BacktestConfig(template_legs("long_straddle")))
    two = run_backtest(dates, p, BacktestConfig(sized_legs(template_legs("long_straddle"), (2, 2))))
    for field_ in ("premium", "payoff"):  # cycle P&L also holds interest on the cash, which doesn't scale
        np.testing.assert_allclose([getattr(c, field_) for c in two.cycles],
                                   [2 * getattr(c, field_) for c in one.cycles], rtol=1e-12)


@pytest.mark.parametrize("bad", ["", "0", "-1", "11", "1,a", ",".join(["1"] * 9)])
def test_bad_sizes_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        sizes_from_code(bad)


def test_sizes_round_trip() -> None:
    assert sizes_to_code(sizes_from_code("2, 1.5")) == "2,1.5"
    with pytest.raises(ValueError):
        sized_legs(template_legs("long_straddle"), (1,))


# --------------------------------------------------------------------------- exit rules

def _strangle(**kw) -> BacktestConfig:
    """A short strangle: sell a call 5% above and a put 5% below, a classic credit trade for exit rules."""
    short = tuple(LegTemplate(leg.kind, -leg.quantity, leg.moneyness) for leg in template_legs("long_strangle"))
    return BacktestConfig(short, tenor_days=45, rate=0.03, **kw)


def test_take_profit_closes_once_the_target_share_of_the_credit_is_earned() -> None:
    dates, p = market(n=900, seed=7)
    res = run_backtest(dates, p, _strangle(take_profit=0.5))
    hits = [c for c in res.cycles if c.exit_reason == "take profit"]
    assert hits, "expected some take-profit exits"
    for c in hits:
        assert c.premium > 0  # a short strangle collects a credit
        assert c.premium + c.payoff >= 0.5 * c.premium - 1e-9  # gain on the options when closed
        assert c.open_date < c.exit_date < c.expiry_date
    assert all(c.exit_date is None for c in res.cycles if c.exit_reason == "expiry")


def test_stop_loss_closes_once_the_loss_reaches_its_limit() -> None:
    dates, p = market(n=900, seed=11, sigma=0.45)
    res = run_backtest(dates, p, _strangle(stop_loss=1.0))
    hits = [c for c in res.cycles if c.exit_reason == "stop loss"]
    assert hits, "expected some stop-loss exits"
    for c in hits:
        assert c.premium + c.payoff <= -1.0 * c.premium + 1e-9


def test_after_an_early_exit_the_cash_just_earns_interest_until_the_next_roll() -> None:
    dates, p = market(n=900, seed=7)
    res = run_backtest(dates, p, _strangle(take_profit=0.3))
    c = next(c for c in res.cycles if c.exit_reason == "take profit")
    idle = (res.dates > c.exit_date) & (res.dates <= c.expiry_date)
    v = res.value[(res.dates >= c.exit_date) & (res.dates <= c.expiry_date)]
    d = res.dates[(res.dates >= c.exit_date) & (res.dates <= c.expiry_date)]
    assert idle.sum() > 0
    days = pd.Series(d).diff().dt.days.to_numpy()[1:]
    np.testing.assert_allclose(np.diff(np.log(v)), 0.03 * days / 365.0, atol=1e-12)


def test_exit_rules_that_never_trigger_change_nothing() -> None:
    dates, p = market()
    base = run_backtest(dates, p, _strangle())
    wide = run_backtest(dates, p, _strangle(take_profit=1e6, stop_loss=1e6))
    np.testing.assert_array_equal(base.value, wide.value)


def test_without_costs_an_early_exit_does_not_jump_the_portfolio_value() -> None:
    dates, p = market(n=900, seed=7)
    base = run_backtest(dates, p, _strangle())
    tp = run_backtest(dates, p, _strangle(take_profit=0.5))
    first = next(c for c in tp.cycles if c.exit_reason == "take profit")
    upto = tp.dates <= first.exit_date
    np.testing.assert_allclose(tp.value[upto], base.value[upto], rtol=1e-12)


def test_closing_early_pays_costs_again() -> None:
    dates, p = market(n=900, seed=7)
    res = run_backtest(dates, p, _strangle(take_profit=0.5, spread=0.1, commission=0.01))
    closed = [c for c in res.cycles if c.exit_reason == "take profit"]
    assert closed
    assert all(c.costs > 4 * 0.01 for c in closed)  # two legs' commission on opening, and again on closing


@pytest.mark.parametrize("kw", [dict(take_profit=0), dict(stop_loss=-1), dict(take_profit=float("inf"))])
def test_exit_rule_levels_must_be_positive(kw: dict) -> None:
    with pytest.raises(ValueError):
        BacktestConfig(template_legs("covered_call"), **kw)
