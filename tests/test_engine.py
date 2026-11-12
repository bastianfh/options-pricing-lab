"""The unified pricing engine used by the UI."""

import pytest

from pricing.engine import Method, NumericalSettings, OptionSpec, greeks, price, price_all, supports
from pricing.utils import ExerciseStyle, OptionType


def test_doc_example() -> None:
    assert price(OptionSpec(100, 100, 1.0, 0.05, 0.2), Method.BLACK_SCHOLES).price == pytest.approx(10.4506, abs=1e-4)


def test_all_four_methods_agree_for_european_options() -> None:
    spec = OptionSpec(S=100, K=95, T=0.5, r=0.04, sigma=0.25, q=0.01, option_type="put")
    results = price_all(spec)
    bs = results[Method.BLACK_SCHOLES].price
    for method, res in results.items():
        assert res.available and res.runtime_ms >= 0
        assert res.price == pytest.approx(bs, abs=0.02), method
    mc = results[Method.MONTE_CARLO]
    assert mc.std_error is not None and mc.ci_low < mc.price < mc.ci_high


def test_american_put_only_on_tree_and_pde() -> None:
    spec = OptionSpec(100, 100, 1.0, 0.05, 0.2, option_type="put", exercise="american")
    assert supports(spec, Method.BLACK_SCHOLES) == (False, "european_only")
    assert not supports(spec, Method.MONTE_CARLO)[0]
    results = price_all(spec)
    assert results[Method.BLACK_SCHOLES].price is None
    assert results[Method.BINOMIAL].price == pytest.approx(results[Method.FINITE_DIFFERENCE].price, abs=5e-3)
    assert greeks(spec, Method.BLACK_SCHOLES) is None


def test_american_call_without_dividends_allowed_everywhere() -> None:
    spec = OptionSpec(100, 100, 1.0, 0.05, 0.2, option_type="call", exercise="american")
    assert all(supports(spec, m)[0] for m in Method)


def test_spec_normalises_strings() -> None:
    spec = OptionSpec(100, 100, 1, 0.05, 0.2, option_type="PUT", exercise="American")
    assert spec.option_type is OptionType.PUT and spec.exercise is ExerciseStyle.AMERICAN
    assert spec.with_(S=110).S == 110


def test_settings_change_resolution() -> None:
    spec = OptionSpec(100, 100, 1, 0.05, 0.2)
    coarse = price(spec, Method.BINOMIAL, NumericalSettings(binomial_steps=10)).price
    fine = price(spec, Method.BINOMIAL, NumericalSettings(binomial_steps=1000)).price
    bs = price(spec, Method.BLACK_SCHOLES).price
    assert abs(fine - bs) < abs(coarse - bs)
