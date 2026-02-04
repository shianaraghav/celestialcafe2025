from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class StrategyConfig:
    # weights (sum should be 1.0)
    liquidity_weight: float = 0.3
    momentum_weight: float = 0.35
    volatility_weight: float = 0.15
    trend_weight: float = 0.2

    # selection / thresholds
    top_n: int = 5
    composite_threshold: float = 0.55  # Lowered from 0.7 for more signals
    min_24h_volume: float = 50_000_000  # Lowered from 150M to 50M

    # volatility / ATR preferences
    preferred_volatility_ratio: float = 0.02
    atr_stop_multiplier: float = 1.5       # Slightly wider stop-loss
    trailing_atr_multiplier: float = 1.2   # Wider trailing stop
    trailing_pct: float = 0.005
    trailing_activation_pct: float = 0.01  # activate trail earlier
    profit_tiers: Tuple[float, ...] = (0.06, 0.12, 0.18)  # Higher profit targets (6%, 12%, 18%)

    # lookbacks / operational
    volume_lookback_mins: int = 24 * 60

    # higher-timeframe trend filter
    htf_resample: str = "4h"
    htf_min_bars: int = 200
    require_htf_uptrend: bool = True  # Require HTF uptrend (disable for backtesting)
    
    # BACKTESTING FLAGS (do not affect live trading)
    relax_ema_check: bool = False  # Ignore EMA9>EMA21 requirement
    relax_liquidity: bool = False  # Ignore min_24h_volume threshold
    relax_composite: bool = False  # Allow entry even if composite < threshold


@dataclass
class SignalResult:
    timestamp: pd.Timestamp
    composite_score: float
    entry_signal: bool
    stop_loss: float
    take_profit_prices: List[float]
    trailing_params: Dict[str, float]
    metrics: Dict[str, float]
    close_price: float
    atr: float


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the frame enriched with EMA/ATR/RSI columns."""
    indicators = df.copy()
    indicators["ema9"] = indicators["close"].ewm(span=9, adjust=False).mean()
    indicators["ema21"] = indicators["close"].ewm(span=21, adjust=False).mean()
    indicators["ema200"] = indicators["close"].ewm(span=200, adjust=False).mean()

    previous_close = indicators["close"].shift(1)
    high_low = indicators["high"] - indicators["low"]
    high_close = (indicators["high"] - previous_close).abs()
    low_close = (indicators["low"] - previous_close).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    indicators["atr14"] = true_range.rolling(window=14, min_periods=1).mean()

    delta = indicators["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
    indicators["rsi14"] = 100 - (100 / (1 + rs))

    return indicators


def _liquidity_score(volume_24h: float, config: StrategyConfig) -> float:
    """
    Return a normalized liquidity score in [0,1].
    The old implementation had a logic bug that often returned 1.0 whenever volume > min.
    We normalize by a sensible upper bound (min_24h_volume * 5) to spread scores.
    """
    if volume_24h <= config.min_24h_volume:
        return 0.0
    # scale volumes so that very large volumes saturate at 1.0
    denom = max(config.min_24h_volume * 5.0, 1.0)
    score = float(np.clip(volume_24h / denom, 0.0, 1.0))
    return score


def _volatility_score(atr: float, price: float, config: StrategyConfig) -> float:
    """Score volatility relative to preferred ratio; small ATRs yield low score."""
    if price == 0 or np.isnan(atr) or price <= 0:
        return 0.0
    ratio = atr / price
    # prefer volatility near preferred_volatility_ratio; penalize too-low or too-high
    diff = abs(ratio - config.preferred_volatility_ratio)
    # set a reasonable max_diff scale (e.g., twice the preferred ratio)
    max_diff = max(config.preferred_volatility_ratio * 2, 1e-6)
    return max(0.0, 1.0 - (diff / max_diff))


def _momentum_score(ema9: float, ema21: float, rsi: float) -> float:
    if ema9 <= ema21 or np.isnan(rsi):
        return 0.0
    normalized_rsi = np.clip((rsi - 45) / 25.0, 0.0, 1.0)
    return normalized_rsi


def _trend_score(price: float, ema200: float) -> float:
    if np.isnan(price) or np.isnan(ema200):
        return 0.0
    return 1.0 if price > ema200 else 0.0


def _composite_score(liquidity: float, momentum: float, volatility: float, trend: float, config: StrategyConfig) -> float:
    raw = (
        liquidity * config.liquidity_weight
        + momentum * config.momentum_weight
        + volatility * config.volatility_weight
        + trend * config.trend_weight
    )
    return np.clip(raw * 100.0, 0.0, 100.0)


def _24h_volume(indicators: pd.DataFrame, config: StrategyConfig) -> float:
    """Calculate 24h USDT volume. For hourly data, use last 24 bars."""
    # For hourly data, 24 bars = 24 hours
    lookback = min(len(indicators), 24)  # Last 24 hours
    if lookback == 0:
        return 0.0
    # Calculate USDT volume (price * volume)
    recent = indicators.tail(lookback)
    usdt_volume = (recent["close"] * recent["volume"]).sum()
    return usdt_volume


def _htf_ema_value(df: pd.DataFrame, resample_rule: str, span: int = 200) -> float | None:
    """
    Compute a higher timeframe EMA (resampled) and return the latest value.
    Returns None if not enough HTF bars exist.
    """
    try:
        # Use last-known index timezone-aware resample
        htf = df["close"].resample(resample_rule).last()
        if len(htf) < span:
            return None
        htf_ema = htf.ewm(span=span, adjust=False).mean()
        return float(htf_ema.iloc[-1])
    except Exception:
        return None


def generate_signal(df: pd.DataFrame, config: StrategyConfig | None = None) -> SignalResult:
    """Analyze minute OHLCV and return composite score plus trade guidance."""

    if config is None:
        config = StrategyConfig()

    if df.empty:
        raise ValueError("DataFrame must contain at least one bar.")

    indicators = compute_indicators(df)
    latest = indicators.iloc[-1]
    volume_24h = _24h_volume(indicators, config)

    # scores
    liquidity = _liquidity_score(volume_24h, config)
    volatility = _volatility_score(latest["atr14"], latest["close"], config)
    momentum = _momentum_score(latest["ema9"], latest["ema21"], latest["rsi14"])
    trend = _trend_score(latest["close"], latest["ema200"])

    # higher timeframe trend check (4H by default). If HTF EMA is present, require price above it.
    htf_ema = _htf_ema_value(indicators, config.htf_resample, span=200)
    htf_trend_ok = True
    if config.require_htf_uptrend and htf_ema is not None:
        htf_trend_ok = latest["close"] > htf_ema
    # composite score (0..100) kept for backward compatibility
    composite = _composite_score(liquidity, momentum, volatility, trend, config)

    # ATR ratio filter: ensure a minimum volatility so we avoid extremely quiet markets
    atr_ratio = (latest["atr14"] / latest["close"]) if latest["close"] > 0 else 0.0
    min_atr_ratio = config.preferred_volatility_ratio * 0.5

    # Build informative rejection reasons (useful for debugging & backtester analysis)
    rejection_reasons: List[str] = []

    if liquidity <= 0.0 and not config.relax_liquidity:
        rejection_reasons.append("low_liquidity")
    if not (atr_ratio >= min_atr_ratio):
        rejection_reasons.append("low_atr")
    if momentum <= 0.0:
        rejection_reasons.append("no_momentum")
    if trend != 1.0:
        rejection_reasons.append("long_term_downtrend")
    if not htf_trend_ok:
        rejection_reasons.append("htf_downtrend")
    # Relaxed RSI band for more signals (45-70 instead of 50-65)
    if np.isnan(latest["rsi14"]) or not (45.0 <= latest["rsi14"] <= 70.0):
        rejection_reasons.append("rsi_out_of_range")
    if not config.relax_ema_check and not (latest["ema9"] > latest["ema21"]):
        rejection_reasons.append("ema9_below_ema21")

    # Final entry decision: use backtesting flags for flexibility
    entry_signal = (
        (composite >= config.composite_threshold * 100 or config.relax_composite)
        and momentum > 0
        and (liquidity > 0 or config.relax_liquidity)
        and (atr_ratio >= min_atr_ratio)
        and htf_trend_ok
        and (45.0 <= latest["rsi14"] <= 70.0)  # Relaxed RSI range
        and (config.relax_ema_check or latest["ema9"] > latest["ema21"])
        and (latest["close"] > latest["ema9"])
    )

    close_price = latest["close"]
    atr = latest["atr14"]

    # Stop-loss: tighter ATR-based
    stop_loss = close_price - atr * config.atr_stop_multiplier if not np.isnan(atr) else close_price
    stop_loss = max(stop_loss, 0.0)

    # Take-profits: extended tiers
    take_profits = [close_price * (1 + tier) for tier in config.profit_tiers]

    trailing_distance = max(
        close_price * config.trailing_pct,
        (atr if not np.isnan(atr) else 0.0) * config.trailing_atr_multiplier,
    )
    trailing_params = {
        "activation_price": close_price * (1 + config.trailing_activation_pct),
        "trail_distance": trailing_distance,
    }

    metrics = {
        "liquidity": liquidity,
        "momentum": momentum,
        "volatility": volatility,
        "trend": trend,
        "volume_24h": volume_24h,
        "atr_ratio": atr_ratio,
        "htf_ema": htf_ema if htf_ema is not None else np.nan,
        "rejection_reasons": ",".join(rejection_reasons) if rejection_reasons else "",
    }

    return SignalResult(
        timestamp=pd.Timestamp(indicators.index[-1]),
        composite_score=composite,
        entry_signal=entry_signal,
        stop_loss=stop_loss,
        take_profit_prices=take_profits,
        trailing_params=trailing_params,
        metrics=metrics,
        close_price=close_price,
        atr=atr,
    )