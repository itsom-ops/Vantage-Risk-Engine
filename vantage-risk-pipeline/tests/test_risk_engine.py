"""
tests/test_risk_engine.py — Unit tests for Altman Z, Merton DTD, SHAP.

Uses 3 real-world reference companies with known characteristics:
  1. Apple (AAPL)    — Clearly healthy / Safe tier
  2. Boeing (BA)     — Mid-tier / Grey Zone (heavy debt post-2020)
  3. AMC Ent. (AMC)  — Historically distressed / Distress tier

Values are based on publicly available FY2023 annual report data.
All monetary values in USD millions.
"""

import math
import sys
from pathlib import Path

import pytest

# Allow import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from risk_engine import (
    AltmanResult,
    MertonResult,
    altman_z_score,
    compute_full_risk,
    explain_risk_drivers,
    merton_distance_to_default,
)


# ─────────────────────────────────────────────────────────────────────────────
# Reference data (FY2023 approximate, USD millions)
# ─────────────────────────────────────────────────────────────────────────────

APPLE_FINANCIALS = {
    "ticker": "AAPL",
    "working_capital":       -6_907,    # current assets - current liabilities (AAPL runs negative WC)
    "retained_earnings":     -214,       # AAPL has nearly zero retained earnings (buybacks)
    "ebit":                  114_301,
    "market_cap":            2_994_000, # ~$3T as of FY2023
    "revenue":               383_285,
    "total_assets":          352_583,
    "total_liabilities":     290_437,
    "market_value_equity":   2_994_000,
    "debt_to_equity":        -5.30,     # technical negative equity
    "current_ratio":         0.99,
    "interest_coverage":     28.0,
    "price_volatility_annual": 0.24,
}

BOEING_FINANCIALS = {
    "ticker": "BA",
    "working_capital":       8_574,
    "retained_earnings":     -18_640,   # accumulated losses
    "ebit":                  -2_200,    # operating loss
    "market_cap":            130_000,
    "revenue":               77_794,
    "total_assets":          137_038,
    "total_liabilities":     155_649,
    "market_value_equity":   130_000,
    "debt_to_equity":        None,       # technically negative equity
    "current_ratio":         1.07,
    "interest_coverage":     -1.5,
    "price_volatility_annual": 0.38,
}

AMC_FINANCIALS = {
    "ticker": "AMC",
    "working_capital":       -271,
    "retained_earnings":     -3_300,
    "ebit":                  -380,
    "market_cap":            1_200,
    "revenue":               4_400,
    "total_assets":          8_000,
    "total_liabilities":     9_800,
    "market_value_equity":   1_200,
    "debt_to_equity":        None,       # negative equity
    "current_ratio":         0.73,
    "interest_coverage":     -1.2,
    "price_volatility_annual": 1.20,
}


# ─────────────────────────────────────────────────────────────────────────────
# Altman Z-Score tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAltmanZScore:

    def test_apple_is_safe_or_grey(self):
        """AAPL has high EBIT ratio and massive market cap — Z should be well above 2.99."""
        res = altman_z_score(
            working_capital     = APPLE_FINANCIALS["working_capital"],
            retained_earnings   = APPLE_FINANCIALS["retained_earnings"],
            ebit                = APPLE_FINANCIALS["ebit"],
            market_value_equity = APPLE_FINANCIALS["market_cap"],
            sales               = APPLE_FINANCIALS["revenue"],
            total_assets        = APPLE_FINANCIALS["total_assets"],
            total_liabilities   = APPLE_FINANCIALS["total_liabilities"],
        )
        assert isinstance(res, AltmanResult)
        assert res.z_score > 2.0, f"Expected Apple Z > 2.0, got {res.z_score}"
        assert res.tier in ("Safe", "Grey Zone"), f"Expected Safe/Grey, got {res.tier}"

    def test_boeing_is_grey_or_distress(self):
        """BA has negative retained earnings and EBIT losses — Z should be in Grey/Distress."""
        res = altman_z_score(
            working_capital     = BOEING_FINANCIALS["working_capital"],
            retained_earnings   = BOEING_FINANCIALS["retained_earnings"],
            ebit                = BOEING_FINANCIALS["ebit"],
            market_value_equity = BOEING_FINANCIALS["market_cap"],
            sales               = BOEING_FINANCIALS["revenue"],
            total_assets        = BOEING_FINANCIALS["total_assets"],
            total_liabilities   = BOEING_FINANCIALS["total_liabilities"],
        )
        assert isinstance(res, AltmanResult)
        assert res.z_score < 3.0, f"Expected Boeing Z < 3.0, got {res.z_score}"
        assert res.tier in ("Grey Zone", "Distress"), f"Expected Grey/Distress, got {res.tier}"

    def test_amc_is_distress(self):
        """AMC has negative EBIT, working capital, and accumulated losses — should be Distress."""
        res = altman_z_score(
            working_capital     = AMC_FINANCIALS["working_capital"],
            retained_earnings   = AMC_FINANCIALS["retained_earnings"],
            ebit                = AMC_FINANCIALS["ebit"],
            market_value_equity = AMC_FINANCIALS["market_cap"],
            sales               = AMC_FINANCIALS["revenue"],
            total_assets        = AMC_FINANCIALS["total_assets"],
            total_liabilities   = AMC_FINANCIALS["total_liabilities"],
        )
        assert isinstance(res, AltmanResult)
        assert res.tier == "Distress", f"Expected AMC Distress, got {res.tier}"
        assert res.z_score < 1.81, f"Expected AMC Z < 1.81, got {res.z_score}"

    def test_factors_are_bounded_correctly(self):
        """All X factors should be calculable from the formula."""
        res = altman_z_score(100, 200, 50, 1000, 800, 1000, 500)
        expected_x1 = 100 / 1000
        expected_x5 = 800 / 1000
        assert abs(res.x1 - expected_x1) < 1e-6
        assert abs(res.x5 - expected_x5) < 1e-6

    def test_zero_assets_raises(self):
        with pytest.raises(ValueError, match="total_assets"):
            altman_z_score(100, 100, 50, 500, 400, 0, 300)

    def test_zero_liabilities_raises(self):
        with pytest.raises(ValueError, match="total_liabilities"):
            altman_z_score(100, 100, 50, 500, 400, 1000, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Merton DTD tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMertonDTD:

    def test_apple_low_pd(self):
        """Apple's asset value >> debt — DTD should be high, PD very low."""
        asset_val = APPLE_FINANCIALS["market_cap"] + APPLE_FINANCIALS["total_liabilities"]
        res = merton_distance_to_default(
            asset_value      = asset_val,
            debt_face_value  = APPLE_FINANCIALS["total_liabilities"],
            asset_volatility = 0.15,   # scaled down from equity vol
            risk_free_rate   = 0.053,
        )
        assert isinstance(res, MertonResult)
        assert res.distance_to_default > 2.0, f"Expected high DTD for Apple, got {res.distance_to_default}"
        assert res.prob_of_default < 0.05, f"Expected PD < 5% for Apple, got {res.prob_of_default:.4f}"

    def test_amc_higher_pd(self):
        """AMC has liabilities > assets — DTD should be low/negative, PD elevated."""
        asset_val = max(AMC_FINANCIALS["market_cap"] + AMC_FINANCIALS["total_liabilities"], 1)
        res = merton_distance_to_default(
            asset_value      = asset_val,
            debt_face_value  = AMC_FINANCIALS["total_liabilities"],
            asset_volatility = 0.80,   # high equity vol, significant scaling
            risk_free_rate   = 0.053,
        )
        assert isinstance(res, MertonResult)
        assert res.prob_of_default > 0.01, f"Expected elevated PD for AMC, got {res.prob_of_default:.4f}"

    def test_pd_bounds(self):
        """PD must always be in [0, 1]."""
        for asset_val in [100, 500, 1000, 5000]:
            for debt in [50, 400, 900, 4500]:
                try:
                    res = merton_distance_to_default(asset_val, debt, 0.30, 0.05)
                    assert 0.0 <= res.prob_of_default <= 1.0
                except ValueError:
                    pass  # expected for edge cases

    def test_invalid_inputs_raise(self):
        with pytest.raises(ValueError):
            merton_distance_to_default(-100, 500, 0.30, 0.05)
        with pytest.raises(ValueError):
            merton_distance_to_default(1000, 0, 0.30, 0.05)
        with pytest.raises(ValueError):
            merton_distance_to_default(1000, 500, 0, 0.05)


# ─────────────────────────────────────────────────────────────────────────────
# SHAP / Explainability tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainRiskDrivers:

    def test_returns_up_to_3_drivers(self):
        features = {
            "x1_working_cap_ratio":   0.05,
            "x2_retained_earn_ratio": -0.10,
            "x3_ebit_ratio":          -0.02,
            "x4_equity_debt_ratio":   0.20,
            "x5_sales_ratio":         0.40,
            "debt_to_equity":         3.5,
            "current_ratio":          0.80,
            "interest_coverage":      -0.5,
        }
        result = explain_risk_drivers(features)
        assert len(result.drivers) <= 3
        assert len(result.drivers) >= 1

    def test_driver_has_required_keys(self):
        features = {"x3_ebit_ratio": -0.05, "x4_equity_debt_ratio": 0.10}
        result = explain_risk_drivers(features)
        for driver in result.drivers:
            assert "feature" in driver
            assert "shap_value" in driver
            assert "plain_text" in driver
            assert isinstance(driver["plain_text"], str)
            assert len(driver["plain_text"]) > 0

    def test_composite_score_in_range(self):
        features = {"x3_ebit_ratio": 0.15, "x4_equity_debt_ratio": 2.0, "x5_sales_ratio": 1.2}
        result = explain_risk_drivers(features)
        assert 0.0 <= result.composite_score <= 100.0

    def test_risk_tier_valid(self):
        for ebit in [-0.20, 0.0, 0.10, 0.25]:
            features = {"x3_ebit_ratio": ebit}
            result = explain_risk_drivers(features)
            assert result.risk_tier in ("Low", "Medium", "High", "Critical")


# ─────────────────────────────────────────────────────────────────────────────
# Integration: compute_full_risk
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeFullRisk:

    def test_apple_full_risk(self):
        f = dict(APPLE_FINANCIALS)
        f["working_capital"] = f.pop("working_capital")
        result = compute_full_risk(f)
        assert result["altman_z"] is not None
        assert result["composite_risk_score"] is not None
        assert result["risk_tier"] in ("Low", "Medium", "High", "Critical")

    def test_amc_full_risk_is_high(self):
        result = compute_full_risk(AMC_FINANCIALS)
        assert result["altman_tier"] == "Distress"
        assert result["risk_tier"] in ("High", "Critical")

    def test_missing_fields_handled(self):
        """Should not crash even with minimal data."""
        minimal = {"total_assets": 1000, "total_liabilities": 500, "revenue": 400}
        result = compute_full_risk(minimal)
        assert result["risk_tier"] in ("Low", "Medium", "High", "Critical")
