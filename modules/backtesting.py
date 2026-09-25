"""
VaR Backtesting Engine
======================

Mô-đun kiểm định chuỗi Rolling Historical VaR.

Các kiểm định:
- Kupiec Proportion of Failures (POF): kiểm tra tỷ lệ vượt VaR.
- Christoffersen Independence: kiểm tra hiện tượng vượt VaR có bị cụm hay không.
- Christoffersen Conditional Coverage: kết hợp tỷ lệ vượt và tính độc lập.

Đầu vào là chuỗi lỗ thực tế, Rolling VaR và biến exception đã được tạo
bởi var_engine. Kết quả mang ý nghĩa kiểm định thống kê cho mô hình minh họa,
không phải kết luận phê duyệt mô hình nội bộ của một tổ chức cụ thể.
"""

from __future__ import annotations

from math import erfc, exp, log, sqrt

import numpy as np
import pandas as pd


RESULT_NOT_REJECTED = "Không bác bỏ"
RESULT_REJECTED = "Bác bỏ"
RESULT_NOT_AVAILABLE = "Không đủ dữ liệu"

OVERALL_ACCEPTABLE = "Không bác bỏ mô hình"
OVERALL_REVIEW = "Cần xem xét"
OVERALL_NOT_AVAILABLE = "Chưa đủ dữ liệu"


def chi_square_survival(statistic: float, degrees_of_freedom: int) -> float:
    """Tính survival function của Chi-square cho df = 1 hoặc df = 2."""
    if pd.isna(statistic) or statistic < 0:
        return np.nan

    if degrees_of_freedom == 1:
        return float(erfc(sqrt(statistic / 2.0)))

    if degrees_of_freedom == 2:
        return float(exp(-statistic / 2.0))

    raise ValueError("Hàm hiện chỉ hỗ trợ Chi-square với 1 hoặc 2 bậc tự do.")


def bernoulli_log_likelihood(successes: int, failures: int, probability: float) -> float:
    """Tính log-likelihood Bernoulli với xử lý biên probability = 0 hoặc 1."""
    if successes < 0 or failures < 0:
        raise ValueError("Số lần thành công/thất bại không được âm.")

    if not 0.0 <= probability <= 1.0:
        raise ValueError("Xác suất phải nằm trong khoảng [0, 1].")

    if probability == 0.0:
        return 0.0 if successes == 0 else -np.inf

    if probability == 1.0:
        return 0.0 if failures == 0 else -np.inf

    return successes * log(probability) + failures * log(1.0 - probability)


def classify_test_result(p_value: float, significance_level: float) -> str:
    """Phân loại kết quả kiểm định theo p-value."""
    if pd.isna(p_value):
        return RESULT_NOT_AVAILABLE

    if p_value < significance_level:
        return RESULT_REJECTED

    return RESULT_NOT_REJECTED


def prepare_backtest_sample(rolling_data: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa tập quan sát có đủ loss và Rolling VaR để backtest."""
    required_columns = {"date", "loss", "rolling_var", "exception"}
    missing_columns = required_columns.difference(rolling_data.columns)

    if missing_columns:
        raise ValueError(
            "Dữ liệu backtesting thiếu các cột: "
            + ", ".join(sorted(missing_columns))
        )

    sample = rolling_data[
        ["date", "loss", "rolling_var", "exception"]
    ].copy()

    sample = sample.dropna(subset=["date", "loss", "rolling_var"])
    sample = sample.sort_values("date").reset_index(drop=True)
    sample["exception"] = sample["exception"].astype(bool)
    sample["exception_int"] = sample["exception"].astype(int)
    sample["excess_loss"] = sample["loss"] - sample["rolling_var"]

    return sample


def kupiec_pof_test(
    exceptions: pd.Series,
    confidence_level: float,
    significance_level: float = 0.05,
) -> dict[str, float | int | str]:
    """Thực hiện kiểm định Kupiec Proportion of Failures."""
    exception_series = pd.Series(exceptions).dropna().astype(bool)
    observations = len(exception_series)

    if observations == 0:
        return {
            "test": "Kupiec POF",
            "statistic": np.nan,
            "p_value": np.nan,
            "result": RESULT_NOT_AVAILABLE,
            "observations": 0,
            "exceptions": 0,
        }

    exception_count = int(exception_series.sum())
    expected_probability = 1.0 - float(confidence_level)
    observed_probability = exception_count / observations

    null_log_likelihood = bernoulli_log_likelihood(
        successes=exception_count,
        failures=observations - exception_count,
        probability=expected_probability,
    )

    alternative_log_likelihood = bernoulli_log_likelihood(
        successes=exception_count,
        failures=observations - exception_count,
        probability=observed_probability,
    )

    statistic = -2.0 * (
        null_log_likelihood - alternative_log_likelihood
    )
    statistic = max(float(statistic), 0.0)
    p_value = chi_square_survival(statistic, degrees_of_freedom=1)

    return {
        "test": "Kupiec POF",
        "statistic": statistic,
        "p_value": p_value,
        "result": classify_test_result(p_value, significance_level),
        "observations": observations,
        "exceptions": exception_count,
    }


def transition_counts(exceptions: pd.Series) -> dict[str, int]:
    """Đếm bốn loại chuyển trạng thái exception: 00, 01, 10 và 11."""
    series = pd.Series(exceptions).dropna().astype(int).reset_index(drop=True)

    counts = {
        "n00": 0,
        "n01": 0,
        "n10": 0,
        "n11": 0,
    }

    if len(series) < 2:
        return counts

    previous = series.iloc[:-1].to_numpy()
    current = series.iloc[1:].to_numpy()

    counts["n00"] = int(((previous == 0) & (current == 0)).sum())
    counts["n01"] = int(((previous == 0) & (current == 1)).sum())
    counts["n10"] = int(((previous == 1) & (current == 0)).sum())
    counts["n11"] = int(((previous == 1) & (current == 1)).sum())

    return counts


def christoffersen_independence_test(
    exceptions: pd.Series,
    significance_level: float = 0.05,
) -> dict[str, float | int | str]:
    """Kiểm định Christoffersen về tính độc lập của các lần vượt VaR."""
    exception_series = pd.Series(exceptions).dropna().astype(bool)
    observations = len(exception_series)
    counts = transition_counts(exception_series)

    n00 = counts["n00"]
    n01 = counts["n01"]
    n10 = counts["n10"]
    n11 = counts["n11"]

    transitions_from_zero = n00 + n01
    transitions_from_one = n10 + n11
    total_transitions = transitions_from_zero + transitions_from_one

    if (
        observations < 2
        or total_transitions == 0
        or transitions_from_zero == 0
        or transitions_from_one == 0
    ):
        return {
            "test": "Christoffersen Independence",
            "statistic": np.nan,
            "p_value": np.nan,
            "result": RESULT_NOT_AVAILABLE,
            **counts,
        }

    unconditional_probability = (n01 + n11) / total_transitions
    probability_after_zero = n01 / transitions_from_zero
    probability_after_one = n11 / transitions_from_one

    null_log_likelihood = bernoulli_log_likelihood(
        successes=n01 + n11,
        failures=n00 + n10,
        probability=unconditional_probability,
    )

    alternative_log_likelihood = (
        bernoulli_log_likelihood(
            successes=n01,
            failures=n00,
            probability=probability_after_zero,
        )
        + bernoulli_log_likelihood(
            successes=n11,
            failures=n10,
            probability=probability_after_one,
        )
    )

    statistic = -2.0 * (
        null_log_likelihood - alternative_log_likelihood
    )
    statistic = max(float(statistic), 0.0)
    p_value = chi_square_survival(statistic, degrees_of_freedom=1)

    return {
        "test": "Christoffersen Independence",
        "statistic": statistic,
        "p_value": p_value,
        "result": classify_test_result(p_value, significance_level),
        **counts,
    }


def conditional_coverage_test(
    kupiec_result: dict[str, float | int | str],
    independence_result: dict[str, float | int | str],
    significance_level: float = 0.05,
) -> dict[str, float | str]:
    """Kiểm định Christoffersen Conditional Coverage."""
    kupiec_statistic = kupiec_result["statistic"]
    independence_statistic = independence_result["statistic"]

    if pd.isna(kupiec_statistic) or pd.isna(independence_statistic):
        return {
            "test": "Christoffersen Conditional Coverage",
            "statistic": np.nan,
            "p_value": np.nan,
            "result": RESULT_NOT_AVAILABLE,
        }

    statistic = float(kupiec_statistic) + float(independence_statistic)
    p_value = chi_square_survival(statistic, degrees_of_freedom=2)

    return {
        "test": "Christoffersen Conditional Coverage",
        "statistic": statistic,
        "p_value": p_value,
        "result": classify_test_result(p_value, significance_level),
    }


def exception_run_statistics(exceptions: pd.Series) -> dict[str, float | int]:
    """Tính một số thống kê đơn giản về khoảng cách và chuỗi exception."""
    series = pd.Series(exceptions).dropna().astype(bool).reset_index(drop=True)
    exception_positions = np.flatnonzero(series.to_numpy())

    if len(exception_positions) == 0:
        return {
            "max_consecutive_exceptions": 0,
            "mean_gap": np.nan,
            "minimum_gap": np.nan,
        }

    longest_run = 0
    current_run = 0

    for value in series:
        if value:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0

    if len(exception_positions) < 2:
        mean_gap = np.nan
        minimum_gap = np.nan
    else:
        gaps = np.diff(exception_positions)
        mean_gap = float(gaps.mean())
        minimum_gap = int(gaps.min())

    return {
        "max_consecutive_exceptions": int(longest_run),
        "mean_gap": mean_gap,
        "minimum_gap": minimum_gap,
    }


def build_test_table(
    kupiec_result: dict[str, float | int | str],
    independence_result: dict[str, float | int | str],
    conditional_result: dict[str, float | str],
) -> pd.DataFrame:
    """Tạo bảng ba kiểm định backtesting."""
    rows = []

    for result in [
        kupiec_result,
        independence_result,
        conditional_result,
    ]:
        rows.append(
            {
                "test": result["test"],
                "statistic": result["statistic"],
                "p_value": result["p_value"],
                "result": result["result"],
            }
        )

    return pd.DataFrame(rows)


def build_exception_log(
    backtest_sample: pd.DataFrame,
    max_rows: int = 100,
) -> pd.DataFrame:
    """Tạo bảng chi tiết các ngày vượt VaR."""
    exceptions = backtest_sample[
        backtest_sample["exception"]
    ].copy()

    if exceptions.empty:
        return exceptions

    exceptions = exceptions.sort_values(
        "date",
        ascending=False,
    ).head(max_rows)

    return exceptions.reset_index(drop=True)


def build_cumulative_exception_series(
    backtest_sample: pd.DataFrame,
    confidence_level: float,
) -> pd.DataFrame:
    """Tạo chuỗi exception thực tế tích lũy và mức kỳ vọng tích lũy."""
    data = backtest_sample.copy()

    if data.empty:
        data["actual_cumulative"] = pd.Series(dtype="float64")
        data["expected_cumulative"] = pd.Series(dtype="float64")
        return data

    expected_probability = 1.0 - float(confidence_level)
    data["actual_cumulative"] = data["exception_int"].cumsum()
    data["expected_cumulative"] = (
        np.arange(1, len(data) + 1) * expected_probability
    )

    return data


def run_var_backtest(
    rolling_data: pd.DataFrame,
    confidence_level: float,
    significance_level: float = 0.05,
) -> dict[str, object]:
    """Chạy toàn bộ quy trình backtesting cho Rolling Historical VaR."""
    sample = prepare_backtest_sample(rolling_data)

    observations = len(sample)
    exception_count = int(sample["exception"].sum()) if observations else 0
    expected_probability = 1.0 - float(confidence_level)
    expected_exceptions = observations * expected_probability
    observed_rate = exception_count / observations if observations else np.nan

    kupiec_result = kupiec_pof_test(
        sample["exception"],
        confidence_level=confidence_level,
        significance_level=significance_level,
    )

    independence_result = christoffersen_independence_test(
        sample["exception"],
        significance_level=significance_level,
    )

    conditional_result = conditional_coverage_test(
        kupiec_result=kupiec_result,
        independence_result=independence_result,
        significance_level=significance_level,
    )

    test_table = build_test_table(
        kupiec_result=kupiec_result,
        independence_result=independence_result,
        conditional_result=conditional_result,
    )

    available_results = test_table[
        test_table["result"] != RESULT_NOT_AVAILABLE
    ]

    if available_results.empty:
        overall_result = OVERALL_NOT_AVAILABLE
    elif available_results["result"].eq(RESULT_REJECTED).any():
        overall_result = OVERALL_REVIEW
    else:
        overall_result = OVERALL_ACCEPTABLE

    run_statistics = exception_run_statistics(
        sample["exception"]
    )

    return {
        "sample": sample,
        "tests": test_table,
        "exceptions": build_exception_log(sample),
        "cumulative": build_cumulative_exception_series(
            sample,
            confidence_level,
        ),
        "observations": observations,
        "exception_count": exception_count,
        "expected_exceptions": expected_exceptions,
        "expected_rate": expected_probability,
        "observed_rate": observed_rate,
        "overall_result": overall_result,
        "significance_level": significance_level,
        **run_statistics,
    }
