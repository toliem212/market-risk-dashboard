"""Risk distribution and tail-risk analytics for VaR monitoring."""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd


VOLATILITY_LOW = "Thấp"
VOLATILITY_NORMAL = "Bình thường"
VOLATILITY_HIGH = "Cao"
VOLATILITY_VERY_HIGH = "Rất cao"


def _clean_loss_series(losses: pd.Series) -> pd.Series:
    """Return a numeric loss series without NaN or infinite values."""
    values = pd.to_numeric(losses, errors="coerce")
    return values.replace([np.inf, -np.inf], np.nan).dropna()


def _historical_var_es(losses: pd.Series, confidence: float) -> tuple[float, float]:
    """Calculate historical VaR and ES from a loss series."""
    sample = _clean_loss_series(losses)
    if sample.empty:
        return np.nan, np.nan

    var_value = float(sample.quantile(confidence))
    tail = sample[sample >= var_value]
    es_value = float(tail.mean()) if not tail.empty else var_value

    return max(var_value, 0.0), max(es_value, var_value, 0.0)


def _parametric_var_es(losses: pd.Series, confidence: float) -> tuple[float, float]:
    """Calculate normal-parametric VaR and ES from a loss series."""
    sample = _clean_loss_series(losses)
    if len(sample) < 2:
        return np.nan, np.nan

    mean_loss = float(sample.mean())
    std_loss = float(sample.std(ddof=1))

    if std_loss == 0:
        value = max(mean_loss, 0.0)
        return value, value

    normal = NormalDist()
    z_score = normal.inv_cdf(confidence)
    density = np.exp(-0.5 * z_score**2) / np.sqrt(2 * np.pi)

    var_value = mean_loss + z_score * std_loss
    es_value = mean_loss + std_loss * density / (1 - confidence)

    return max(float(var_value), 0.0), max(float(es_value), float(var_value), 0.0)


def build_confidence_ladder(
    losses: pd.Series,
    confidence_levels: tuple[float, ...] = (0.95, 0.975, 0.99),
) -> pd.DataFrame:
    """Build a VaR/ES comparison table across confidence levels."""
    rows: list[dict[str, float | str | int]] = []
    sample = _clean_loss_series(losses)

    for confidence in confidence_levels:
        historical_var, historical_es = _historical_var_es(sample, confidence)
        parametric_var, parametric_es = _parametric_var_es(sample, confidence)

        rows.append(
            {
                "confidence": confidence,
                "method": "Mô phỏng lịch sử",
                "var": historical_var,
                "es": historical_es,
                "es_var_ratio": (
                    historical_es / historical_var
                    if historical_var > 0
                    else np.nan
                ),
                "observations": len(sample),
            }
        )
        rows.append(
            {
                "confidence": confidence,
                "method": "Tham số",
                "var": parametric_var,
                "es": parametric_es,
                "es_var_ratio": (
                    parametric_es / parametric_var
                    if parametric_var > 0
                    else np.nan
                ),
                "observations": len(sample),
            }
        )

    return pd.DataFrame(rows)


def summarize_tail_risk(
    losses: pd.Series,
    confidence: float = 0.99,
) -> dict[str, float | int]:
    """Summarize the distribution and loss tail for the selected sample."""
    sample = _clean_loss_series(losses)

    if sample.empty:
        return {
            "historical_var": np.nan,
            "historical_es": np.nan,
            "tail_loss_ratio": np.nan,
            "parametric_var": np.nan,
            "model_var_ratio": np.nan,
            "maximum_loss": np.nan,
            "tail_observations": 0,
            "skewness": np.nan,
            "excess_kurtosis": np.nan,
            "downside_deviation": np.nan,
        }

    historical_var, historical_es = _historical_var_es(sample, confidence)
    parametric_var, _ = _parametric_var_es(sample, confidence)
    tail = sample[sample >= historical_var] if pd.notna(historical_var) else sample.iloc[0:0]
    downside = sample[sample > 0]

    downside_deviation = (
        float(np.sqrt(np.mean(np.square(downside))))
        if not downside.empty
        else 0.0
    )

    return {
        "historical_var": historical_var,
        "historical_es": historical_es,
        "tail_loss_ratio": (
            historical_es / historical_var
            if historical_var > 0
            else np.nan
        ),
        "parametric_var": parametric_var,
        "model_var_ratio": (
            parametric_var / historical_var
            if historical_var > 0
            else np.nan
        ),
        "maximum_loss": float(sample.max()),
        "tail_observations": int(len(tail)),
        "skewness": float(sample.skew()),
        "excess_kurtosis": float(sample.kurt()),
        "downside_deviation": downside_deviation,
    }


def _rolling_es(values: np.ndarray, confidence: float) -> float:
    """Calculate historical ES for one rolling window."""
    clean = values[np.isfinite(values)]
    if clean.size == 0:
        return np.nan

    var_value = np.quantile(clean, confidence)
    tail = clean[clean >= var_value]
    return float(tail.mean()) if tail.size else float(var_value)


def build_rolling_tail_metrics(
    loss_data: pd.DataFrame,
    confidence: float = 0.99,
    window: int = 250,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Build rolling historical/parametric VaR, ES and tail-risk metrics.

    The observation at date t is excluded from the estimation window by shift(1).
    """
    if min_periods is None:
        min_periods = max(60, window // 2)

    data = loss_data[["date", "loss"]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["loss"] = pd.to_numeric(data["loss"], errors="coerce")
    data = data.dropna(subset=["date", "loss"]).sort_values("date").reset_index(drop=True)

    history = data["loss"].shift(1)
    rolling = history.rolling(window=window, min_periods=min_periods)

    data["historical_var"] = rolling.quantile(confidence)
    data["historical_es"] = rolling.apply(
        lambda values: _rolling_es(values, confidence),
        raw=True,
    )

    rolling_mean = rolling.mean()
    rolling_std = rolling.std(ddof=1)

    normal = NormalDist()
    z_score = normal.inv_cdf(confidence)
    density = np.exp(-0.5 * z_score**2) / np.sqrt(2 * np.pi)

    data["parametric_var"] = rolling_mean + z_score * rolling_std
    data["parametric_es"] = (
        rolling_mean + rolling_std * density / (1 - confidence)
    )

    for column in [
        "historical_var",
        "historical_es",
        "parametric_var",
        "parametric_es",
    ]:
        data[column] = data[column].clip(lower=0)

    data["rolling_volatility"] = rolling_std
    data["tail_loss_ratio"] = data["historical_es"].div(
        data["historical_var"].replace(0, np.nan)
    )
    data["model_var_ratio"] = data["parametric_var"].div(
        data["historical_var"].replace(0, np.nan)
    )
    data["exception"] = (
        data["historical_var"].notna()
        & (data["loss"] > data["historical_var"])
    )
    data["excess_loss"] = np.where(
        data["exception"],
        data["loss"] - data["historical_var"],
        np.nan,
    )
    data["exception_severity"] = np.where(
        data["exception"] & data["historical_var"].gt(0),
        data["loss"] / data["historical_var"],
        np.nan,
    )

    volatility_history = data["rolling_volatility"].shift(1)
    volatility_window = volatility_history.rolling(
        window=window,
        min_periods=min_periods,
    )
    data["volatility_p50"] = volatility_window.quantile(0.50)
    data["volatility_p75"] = volatility_window.quantile(0.75)
    data["volatility_p90"] = volatility_window.quantile(0.90)

    conditions = [
        data["rolling_volatility"] >= data["volatility_p90"],
        data["rolling_volatility"] >= data["volatility_p75"],
        data["rolling_volatility"] < data["volatility_p50"],
    ]
    choices = [
        VOLATILITY_VERY_HIGH,
        VOLATILITY_HIGH,
        VOLATILITY_LOW,
    ]

    data["volatility_regime"] = np.select(
        conditions,
        choices,
        default=VOLATILITY_NORMAL,
    )

    unavailable = data["rolling_volatility"].isna() | data["volatility_p50"].isna()
    data.loc[unavailable, "volatility_regime"] = "Chưa đủ dữ liệu"

    return data


def summarize_rolling_tail_metrics(
    rolling_data: pd.DataFrame,
) -> dict[str, float | int | str]:
    """Return the latest rolling tail-risk indicators."""
    valid = rolling_data.dropna(subset=["historical_var"]).copy()

    if valid.empty:
        return {
            "latest_historical_var": np.nan,
            "latest_historical_es": np.nan,
            "latest_parametric_var": np.nan,
            "latest_parametric_es": np.nan,
            "latest_tail_loss_ratio": np.nan,
            "latest_model_var_ratio": np.nan,
            "latest_volatility": np.nan,
            "volatility_regime": "Chưa đủ dữ liệu",
            "exception_count": 0,
            "average_exception_severity": np.nan,
            "maximum_exception_severity": np.nan,
        }

    latest = valid.iloc[-1]
    exception_severity = valid["exception_severity"].dropna()

    return {
        "latest_historical_var": float(latest["historical_var"]),
        "latest_historical_es": float(latest["historical_es"]),
        "latest_parametric_var": float(latest["parametric_var"]),
        "latest_parametric_es": float(latest["parametric_es"]),
        "latest_tail_loss_ratio": float(latest["tail_loss_ratio"]),
        "latest_model_var_ratio": float(latest["model_var_ratio"]),
        "latest_volatility": float(latest["rolling_volatility"]),
        "volatility_regime": str(latest["volatility_regime"]),
        "exception_count": int(valid["exception"].sum()),
        "average_exception_severity": (
            float(exception_severity.mean())
            if not exception_severity.empty
            else np.nan
        ),
        "maximum_exception_severity": (
            float(exception_severity.max())
            if not exception_severity.empty
            else np.nan
        ),
    }


def build_tail_exception_table(
    rolling_data: pd.DataFrame,
    max_rows: int = 20,
) -> pd.DataFrame:
    """Return the most severe rolling VaR exceptions."""
    exceptions = rolling_data[rolling_data["exception"]].copy()

    if exceptions.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "loss",
                "historical_var",
                "historical_es",
                "excess_loss",
                "exception_severity",
            ]
        )

    return (
        exceptions.sort_values(
            ["exception_severity", "date"],
            ascending=[False, False],
        )
        .head(max_rows)[
            [
                "date",
                "loss",
                "historical_var",
                "historical_es",
                "excess_loss",
                "exception_severity",
            ]
        ]
        .reset_index(drop=True)
    )
