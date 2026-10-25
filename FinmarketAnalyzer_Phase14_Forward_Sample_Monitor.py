import csv
import glob
import hashlib

# ============================================================
# FINMARKET ANALYZER
# Phase 12.2 - S/R Diagnostic + Clean Accounting
# Built from the tested Phase 12 project; Phase 11 remains unchanged.
# Financial Market Analysis Application
# ============================================================

# Stores all market assets added manually.
market_assets = []

# Stores closing prices imported from the MT5 CSV file.
csv_prices = []


# ============================================================
# PHASE 11 - HELPER / CALCULATION FUNCTIONS
# ============================================================

def check_csv_data():
    """Check whether MT5 closing prices have been imported."""

    if not csv_prices:
        print("\nERROR: No CSV market data has been imported.")
        print("Please select Option 11 - CSV Data Import first.")
        return False

    return True


def calculate_sma(prices, period):
    """Calculate a Simple Moving Average for the latest period."""

    if len(prices) < period:
        return None

    return sum(prices[-period:]) / period


def calculate_ema(prices, period):
    """
    Calculate an Exponential Moving Average.

    The first EMA value is initialized with an SMA using
    the first 'period' prices. This provides a more standard
    EMA starting point than using the first price directly.
    """

    if len(prices) < period:
        return []

    multiplier = 2 / (period + 1)

    ema_values = [None] * len(prices)

    # Initial EMA value = SMA of first period prices.
    initial_sma = sum(prices[:period]) / period
    ema_values[period - 1] = initial_sma

    # Continue EMA calculation from the next price.
    for i in range(period, len(prices)):

        ema_values[i] = (
            (prices[i] - ema_values[i - 1])
            * multiplier
            + ema_values[i - 1]
        )

    return ema_values


def calculate_rsi(prices, period=14):
    """
    Calculate RSI using Wilder-style smoothing.

    Returns a list containing RSI values. Values before the
    first complete RSI calculation are stored as None.
    """

    if len(prices) <= period:
        return []

    rsi_values = [None] * len(prices)

    gains = []
    losses = []

    # Calculate individual gains and losses.
    for i in range(1, len(prices)):

        change = prices[i] - prices[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)

        elif change < 0:
            gains.append(0)
            losses.append(abs(change))

        else:
            gains.append(0)
            losses.append(0)

    # Initial averages use the first 14 changes.
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    # First RSI value.
    if average_loss == 0:
        rsi_values[period] = 100

    else:
        relative_strength = average_gain / average_loss

        rsi_values[period] = (
            100 - (100 / (1 + relative_strength))
        )

    # Wilder smoothing for the remaining values.
    for i in range(period + 1, len(prices)):

        current_gain = gains[i - 1]
        current_loss = losses[i - 1]

        average_gain = (
            ((average_gain * (period - 1)) + current_gain)
            / period
        )

        average_loss = (
            ((average_loss * (period - 1)) + current_loss)
            / period
        )

        if average_loss == 0:
            rsi_values[i] = 100

        else:
            relative_strength = average_gain / average_loss

            rsi_values[i] = (
                100 - (100 / (1 + relative_strength))
            )

    return rsi_values


def calculate_macd(prices):
    """
    Calculate standard MACD components:

    Fast EMA  = 12 periods
    Slow EMA  = 26 periods
    Signal    = 9-period EMA of MACD

    Returns:
        ema_12_values
        ema_26_values
        macd_values
        signal_values
        histogram_values
    """

    if len(prices) < 26:
        return [], [], [], [], []

    ema_12_values = calculate_ema(prices, 12)
    ema_26_values = calculate_ema(prices, 26)

    # MACD begins when both EMAs are available.
    macd_values = [None] * len(prices)

    for i in range(len(prices)):

        if (
            ema_12_values[i] is not None
            and ema_26_values[i] is not None
        ):
            macd_values[i] = (
                ema_12_values[i] -
                ema_26_values[i]
            )

    # Extract valid MACD values for signal calculation.
    valid_macd = [
        value for value in macd_values
        if value is not None
    ]

    signal_valid = calculate_ema(valid_macd, 9)

    signal_values = [None] * len(prices)

    # The first valid MACD value occurs at index 25.
    first_macd_index = 25

    for j, value in enumerate(signal_valid):

        if value is not None:
            actual_index = first_macd_index + j

            if actual_index < len(signal_values):
                signal_values[actual_index] = value

    # Histogram = MACD - Signal.
    histogram_values = [None] * len(prices)

    for i in range(len(prices)):

        if (
            macd_values[i] is not None
            and signal_values[i] is not None
        ):
            histogram_values[i] = (
                macd_values[i] -
                signal_values[i]
            )

    return (
        ema_12_values,
        ema_26_values,
        macd_values,
        signal_values,
        histogram_values
    )


def find_latest_macd_crossover(macd_values, signal_values):
    """Find the most recent valid MACD crossover."""

    crossover = "NO RECENT CROSSOVER"
    crossover_index = None

    for i in range(1, len(macd_values)):

        if (
            macd_values[i - 1] is None
            or signal_values[i - 1] is None
            or macd_values[i] is None
            or signal_values[i] is None
        ):
            continue

        previous_macd = macd_values[i - 1]
        previous_signal = signal_values[i - 1]

        current_macd = macd_values[i]
        current_signal = signal_values[i]

        # Bullish crossover.
        if (
            previous_macd <= previous_signal
            and current_macd > current_signal
        ):
            crossover = "BULLISH CROSSOVER"
            crossover_index = i

        # Bearish crossover.
        elif (
            previous_macd >= previous_signal
            and current_macd < current_signal
        ):
            crossover = "BEARISH CROSSOVER"
            crossover_index = i

    return crossover, crossover_index


def get_latest_valid(values):
    """Return the most recent non-None value."""

    for value in reversed(values):

        if value is not None:
            return value

    return None


# ============================================================
# OPTION 1 - ADD MARKET ASSET
# ============================================================

def add_market_asset():
    """Add a new financial asset to the system."""

    print("\n========================================")
    print("          ADD MARKET ASSET")
    print("========================================")

    try:
        asset_name = input("Enter asset name: ").strip()
        asset_type = input("Enter asset type: ").strip()

        current_price = float(input("Enter current price: "))
        previous_price = float(input("Enter previous price: "))

        if previous_price == 0:
            print("\nERROR: Previous price cannot be zero.")
            return

        asset = {
            "name": asset_name,
            "type": asset_type,
            "current_price": current_price,
            "previous_price": previous_price
        }

        market_assets.append(asset)

        print("\nAsset added successfully!")

    except ValueError:
        print("\nERROR: Please enter valid numeric prices.")


# ============================================================
# OPTION 2 - VIEW MARKET ASSETS
# ============================================================

def view_market_assets():
    """Display all assets stored in the system."""

    print("\n========================================")
    print("          MARKET ASSETS")
    print("========================================")

    if len(market_assets) == 0:
        print("No market assets have been added yet.")
        return

    for asset in market_assets:

        print("----------------------------------------")
        print(f"Asset: {asset['name']}")
        print(f"Type: {asset['type']}")
        print(f"Current Price: ${asset['current_price']:.2f}")
        print(f"Previous Price: ${asset['previous_price']:.2f}")

    print("----------------------------------------")


# ============================================================
# OPTION 3 - ANALYZE MARKET ASSETS
# ============================================================

def analyze_asset():
    """Analyze all stored market assets."""

    print("\n========================================")
    print("          MARKET ANALYSIS")
    print("========================================")

    if len(market_assets) == 0:
        print("No market assets available for analysis.")
        return

    for asset in market_assets:

        price_change = (
            asset["current_price"]
            - asset["previous_price"]
        )

        percentage_change = (
            price_change /
            asset["previous_price"]
        ) * 100

        if price_change > 0:
            direction = "UP"

        elif price_change < 0:
            direction = "DOWN"

        else:
            direction = "UNCHANGED"

        print("----------------------------------------")
        print(f"Asset: {asset['name']}")
        print(f"Type: {asset['type']}")
        print(f"Current Price: ${asset['current_price']:.2f}")
        print(f"Price Change: ${price_change:.2f}")
        print(f"Percentage Change: {percentage_change:.2f}%")
        print(f"Direction: {direction}")

    print("----------------------------------------")


# ============================================================
# OPTION 4 - MARKET STATISTICS
# ============================================================

def market_statistics():
    """Calculate basic statistics for all market assets."""

    print("\n========================================")
    print("        MARKET STATISTICS")
    print("========================================")

    if len(market_assets) == 0:
        print("No market assets available.")
        return

    prices = []
    percentage_changes = []

    for asset in market_assets:

        current_price = asset["current_price"]
        previous_price = asset["previous_price"]

        prices.append(current_price)

        price_change = current_price - previous_price

        percentage_change = (
            price_change /
            previous_price
        ) * 100

        percentage_changes.append(percentage_change)

    number_of_assets = len(market_assets)

    average_price = sum(prices) / number_of_assets
    highest_price = max(prices)
    lowest_price = min(prices)

    price_range = highest_price - lowest_price

    average_percentage_change = (
        sum(percentage_changes)
        / number_of_assets
    )

    print(f"Number of Assets: {number_of_assets}")
    print(f"Average Price: ${average_price:.2f}")
    print(f"Highest Price: ${highest_price:.2f}")
    print(f"Lowest Price: ${lowest_price:.2f}")
    print(f"Price Range: ${price_range:.2f}")
    print(
        f"Average Percentage Change: "
        f"{average_percentage_change:.2f}%"
    )

    print("----------------------------------------")


# ============================================================
# OPTION 5 - VOLATILITY ANALYSIS
# ============================================================

def volatility_analysis():
    """Calculate variance and standard deviation of returns."""

    print("\n========================================")
    print("       VOLATILITY ANALYSIS")
    print("========================================")

    if len(market_assets) == 0:
        print("No market assets available.")
        return

    returns = []

    for asset in market_assets:

        price_change = (
            asset["current_price"]
            - asset["previous_price"]
        )

        percentage_change = (
            price_change /
            asset["previous_price"]
        ) * 100

        returns.append(percentage_change)

    mean_return = sum(returns) / len(returns)

    squared_differences = []

    for value in returns:

        difference = value - mean_return
        squared_difference = difference ** 2

        squared_differences.append(squared_difference)

    variance = (
        sum(squared_differences)
        / len(returns)
    )

    standard_deviation = variance ** 0.5

    print(f"Mean Return: {mean_return:.2f}%")
    print(f"Variance: {variance:.4f}")
    print(
        f"Standard Deviation: "
        f"{standard_deviation:.2f}%"
    )

    if standard_deviation < 1:
        volatility_level = "Low"

    elif standard_deviation < 3:
        volatility_level = "Moderate"

    else:
        volatility_level = "High"

    print(f"Volatility Level: {volatility_level}")

    print("----------------------------------------")


# ============================================================
# OPTION 6 - HISTORICAL PRICE ANALYSIS
# ============================================================

def historical_price_analysis():
    """Analyze historical closing prices imported from MT5."""

    print("\n========================================")
    print("     HISTORICAL PRICE ANALYSIS")
    print("========================================")

    if not check_csv_data():
        return

    asset_name = input(
        "Enter asset name (e.g., XAUUSD): "
    ).strip()

    prices = csv_prices
    average_price = sum(prices) / len(prices)
    latest_price = prices[-1]

    if latest_price > average_price:
        trend = "ABOVE HISTORICAL AVERAGE"

    elif latest_price < average_price:
        trend = "BELOW HISTORICAL AVERAGE"

    else:
        trend = "AT HISTORICAL AVERAGE"

    print("\n----------------------------------------")
    print("      HISTORICAL PRICE RESULTS")
    print("----------------------------------------")

    print(f"Asset: {asset_name}")
    print(f"Historical records analyzed: {len(prices)}")

    print("\nMost Recent 10 Closing Prices:")
    print("----------------------------------------")

    recent_prices = prices[-10:]

    start_number = (
        len(prices)
        - len(recent_prices)
        + 1
    )

    for number, price in enumerate(
        recent_prices,
        start=start_number
    ):
        print(f"Record {number}: ${price:.2f}")

    print("----------------------------------------")
    print(f"Latest Price: ${latest_price:.2f}")
    print(f"Historical Average: ${average_price:.2f}")
    print(f"Position: {trend}")

    print("----------------------------------------")
    print("HISTORICAL ANALYSIS COMPLETE")
    print("----------------------------------------")


# ============================================================
# OPTION 7 - MOVING AVERAGE ANALYSIS
# ============================================================

def moving_average_analysis():
    """Calculate multiple simple moving averages."""

    print("\n========================================")
    print("       MOVING AVERAGE ANALYSIS")
    print("========================================")

    if not check_csv_data():
        return

    asset_name = input("Enter asset name: ").strip()

    prices = csv_prices
    number_of_prices = len(prices)

    if number_of_prices < 5:
        print("\nAt least 5 prices are required.")
        return

    latest_price = prices[-1]

    print("\n----------------------------------------")
    print("       MOVING AVERAGE RESULTS")
    print("----------------------------------------")

    print(f"Asset: {asset_name}")
    print(f"Records analyzed: {number_of_prices}")
    print(f"Latest Price: ${latest_price:.2f}")

    print("\nSimple Moving Averages:")
    print("----------------------------------------")

    periods = [5, 10, 20, 50, 200]
    sma_values = {}

    for period in periods:

        sma = calculate_sma(prices, period)
        sma_values[period] = sma

        if sma is not None:
            print(f"{period}-Period SMA: ${sma:.2f}")

        else:
            print(
                f"{period}-Period SMA: "
                f"Not enough data"
            )

    print("----------------------------------------")
    print("PRICE POSITION")
    print("----------------------------------------")

    for period in periods:

        sma = sma_values[period]

        if sma is None:
            continue

        if latest_price > sma:
            position = "ABOVE"

        elif latest_price < sma:
            position = "BELOW"

        else:
            position = "AT"

        print(
            f"{period}-Period SMA: "
            f"{position}"
        )

    print("----------------------------------------")
    print("MOVING AVERAGE ANALYSIS COMPLETE")
    print("----------------------------------------")


# ============================================================
# OPTION 8 - RSI ANALYSIS
# ============================================================

def rsi_analysis():
    """Calculate a 14-period RSI using Wilder smoothing."""

    print("\n========================================")
    print("          RSI ANALYSIS")
    print("========================================")

    if not check_csv_data():
        return

    asset_name = input(
        "Enter asset name (e.g., XAUUSD): "
    ).strip()

    prices = csv_prices

    if len(prices) < 15:
        print(
            "\nAt least 15 closing prices "
            "are required for RSI."
        )
        return

    rsi_values = calculate_rsi(prices, 14)
    latest_rsi = get_latest_valid(rsi_values)

    if latest_rsi is None:
        print("\nERROR: RSI could not be calculated.")
        return

    if latest_rsi >= 70:
        interpretation = "Potentially overbought"

    elif latest_rsi <= 30:
        interpretation = "Potentially oversold"

    else:
        interpretation = "Neutral momentum range"

    # Calculate the latest average gain/loss for display.
    gains = []
    losses = []

    for i in range(1, len(prices)):

        change = prices[i] - prices[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)

        elif change < 0:
            gains.append(0)
            losses.append(abs(change))

        else:
            gains.append(0)
            losses.append(0)

    recent_gains = gains[-14:]
    recent_losses = losses[-14:]

    average_gain = sum(recent_gains) / 14
    average_loss = sum(recent_losses) / 14

    print("\n----------------------------------------")
    print("             RSI RESULTS")
    print("----------------------------------------")

    print(f"Asset: {asset_name}")
    print(f"Records analyzed: {len(prices)}")
    print(f"Latest Price: ${prices[-1]:.2f}")
    print(f"Average Gain: ${average_gain:.2f}")
    print(f"Average Loss: ${average_loss:.2f}")
    print(f"14-Period RSI: {latest_rsi:.2f}")
    print(f"Interpretation: {interpretation}")

    print("----------------------------------------")
    print("RSI ANALYSIS COMPLETE")
    print("----------------------------------------")


# ============================================================
# OPTION 9 - MACD ANALYSIS
# ============================================================

def macd_analysis():
    """Calculate and analyze MACD using imported MT5 data."""

    print("\n========================================")
    print("          MACD ANALYSIS")
    print("========================================")

    if not check_csv_data():
        return

    asset_name = input(
        "Enter asset name (e.g., XAUUSD): "
    ).strip()

    prices = csv_prices

    if len(prices) < 34:
        print(
            "\nAt least 34 prices are recommended "
            "for a complete 12/26/9 MACD."
        )
        return

    (
        ema_12_values,
        ema_26_values,
        macd_values,
        signal_values,
        histogram_values
    ) = calculate_macd(prices)

    latest_ema_12 = get_latest_valid(ema_12_values)
    latest_ema_26 = get_latest_valid(ema_26_values)
    latest_macd = get_latest_valid(macd_values)
    latest_signal = get_latest_valid(signal_values)
    latest_histogram = get_latest_valid(histogram_values)

    if (
        latest_macd is None
        or latest_signal is None
        or latest_histogram is None
    ):
        print("\nERROR: MACD could not be calculated.")
        return

    if latest_macd > latest_signal:
        macd_trend = "BULLISH"

    elif latest_macd < latest_signal:
        macd_trend = "BEARISH"

    else:
        macd_trend = "NEUTRAL"

    if latest_histogram > 0:
        momentum = "POSITIVE"

    elif latest_histogram < 0:
        momentum = "NEGATIVE"

    else:
        momentum = "NEUTRAL"

    crossover, crossover_index = (
        find_latest_macd_crossover(
            macd_values,
            signal_values
        )
    )

    print("\n----------------------------------------")
    print("             MACD RESULTS")
    print("----------------------------------------")

    print(f"Asset: {asset_name}")
    print(f"Records analyzed: {len(prices)}")
    print(f"Latest Price: ${prices[-1]:.2f}")
    print(f"12-Period EMA: ${latest_ema_12:.4f}")
    print(f"26-Period EMA: ${latest_ema_26:.4f}")
    print(f"MACD Line: {latest_macd:.4f}")
    print(f"Signal Line: {latest_signal:.4f}")
    print(f"MACD Histogram: {latest_histogram:.4f}")
    print(f"MACD Trend: {macd_trend}")
    print(f"Momentum: {momentum}")
    print(f"Most Recent Crossover: {crossover}")

    if crossover_index is not None:
        print(
            f"Crossover Record: "
            f"{crossover_index + 1}"
        )

    else:
        print("Crossover Record: None")

    print("----------------------------------------")
    print("MACD ANALYSIS COMPLETE")
    print("----------------------------------------")


# ============================================================
# OPTION 10 - PHASE 11 COMBINED MARKET SIGNAL
# ============================================================

def combined_market_signal():
    """
    Combine 20-SMA trend, 14-period RSI, and MACD.

    Phase 11 improvements:
    - Uses the professional RSI calculation.
    - Uses the professional 12/26 EMA calculation.
    - Uses a proper 9-period MACD signal EMA.
    - Detects the latest valid MACD crossover.
    - Uses a transparent indicator score.
    """

    print("\n========================================")
    print("      COMBINED MARKET SIGNAL")
    print("========================================")

    if not check_csv_data():
        return

    asset_name = input(
        "Enter asset name (e.g., XAUUSD): "
    ).strip()

    prices = csv_prices
    number_of_prices = len(prices)

    if number_of_prices < 34:
        print(
            "\nAt least 34 prices are required "
            "for the combined analysis."
        )
        return

    latest_price = prices[-1]

    # ========================================================
    # 1. 20-PERIOD SMA
    # ========================================================

    sma_20 = calculate_sma(prices, 20)

    if latest_price > sma_20:
        trend = "BULLISH"

    elif latest_price < sma_20:
        trend = "BEARISH"

    else:
        trend = "NEUTRAL"

    # ========================================================
    # 2. 14-PERIOD RSI
    # ========================================================

    rsi_values = calculate_rsi(prices, 14)
    rsi = get_latest_valid(rsi_values)

    if rsi is None:
        print("\nERROR: RSI could not be calculated.")
        return

    if rsi >= 70:
        rsi_condition = "OVERBOUGHT"

    elif rsi <= 30:
        rsi_condition = "OVERSOLD"

    elif rsi > 50:
        rsi_condition = "BULLISH"

    elif rsi < 50:
        rsi_condition = "BEARISH"

    else:
        rsi_condition = "NEUTRAL"

    # ========================================================
    # 3. MACD
    # ========================================================

    (
        ema_12_values,
        ema_26_values,
        macd_values,
        signal_values,
        histogram_values
    ) = calculate_macd(prices)

    latest_ema_12 = get_latest_valid(ema_12_values)
    latest_ema_26 = get_latest_valid(ema_26_values)
    latest_macd = get_latest_valid(macd_values)
    latest_signal = get_latest_valid(signal_values)
    latest_histogram = get_latest_valid(histogram_values)

    if (
        latest_macd is None
        or latest_signal is None
        or latest_histogram is None
    ):
        print("\nERROR: MACD could not be calculated.")
        return

    if latest_macd > latest_signal:
        macd_trend = "BULLISH"

    elif latest_macd < latest_signal:
        macd_trend = "BEARISH"

    else:
        macd_trend = "NEUTRAL"

    if latest_histogram > 0:
        macd_momentum = "POSITIVE"

    elif latest_histogram < 0:
        macd_momentum = "NEGATIVE"

    else:
        macd_momentum = "NEUTRAL"

    # ========================================================
    # 4. MACD CROSSOVER
    # ========================================================

    crossover, crossover_index = (
        find_latest_macd_crossover(
            macd_values,
            signal_values
        )
    )

    # ========================================================
    # 5. PHASE 11 INDICATOR SCORE
    # ========================================================

    bullish_points = 0
    bearish_points = 0

    # SMA contribution.
    if trend == "BULLISH":
        bullish_points += 1

    elif trend == "BEARISH":
        bearish_points += 1

    # RSI contribution.
    if rsi_condition == "BULLISH":
        bullish_points += 1

    elif rsi_condition == "BEARISH":
        bearish_points += 1

    # Overbought/oversold conditions are displayed separately.
    # They do not automatically create a BUY or SELL signal.

    # MACD contribution.
    if macd_trend == "BULLISH":
        bullish_points += 1

    elif macd_trend == "BEARISH":
        bearish_points += 1

    # ========================================================
    # 6. OVERALL SIGNAL
    # ========================================================

    if bullish_points == 3:
        overall_signal = "BUY"

    elif bearish_points == 3:
        overall_signal = "SELL"

    elif bullish_points > bearish_points:
        overall_signal = "BULLISH BIAS"

    elif bearish_points > bullish_points:
        overall_signal = "BEARISH BIAS"

    else:
        overall_signal = "NEUTRAL"

    # ========================================================
    # 7. DISPLAY RESULTS
    # ========================================================

    print("\n----------------------------------------")
    print("      COMBINED MARKET RESULTS")
    print("----------------------------------------")

    print(f"Asset: {asset_name}")
    print(f"Records analyzed: {number_of_prices}")
    print(f"Latest Price: ${latest_price:.2f}")

    print("\nPRICE TREND")
    print("----------------------------------------")
    print(f"20-Period SMA: ${sma_20:.2f}")
    print(f"Trend: {trend}")

    print("\nRSI")
    print("----------------------------------------")
    print(f"14-Period RSI: {rsi:.2f}")
    print(f"RSI Condition: {rsi_condition}")

    print("\nMACD")
    print("----------------------------------------")
    print(f"12-Period EMA: ${latest_ema_12:.4f}")
    print(f"26-Period EMA: ${latest_ema_26:.4f}")
    print(f"MACD Line: {latest_macd:.4f}")
    print(f"Signal Line: {latest_signal:.4f}")
    print(f"MACD Histogram: {latest_histogram:.4f}")
    print(f"MACD Trend: {macd_trend}")
    print(f"MACD Momentum: {macd_momentum}")

    print("\nMACD CROSSOVER")
    print("----------------------------------------")
    print(f"Most Recent Crossover: {crossover}")

    if crossover_index is not None:
        print(
            f"Crossover Record: "
            f"{crossover_index + 1}"
        )

    else:
        print("Crossover Record: None")

    print("\nINDICATOR SCORE")
    print("----------------------------------------")
    print(f"Bullish Points: {bullish_points}/3")
    print(f"Bearish Points: {bearish_points}/3")

    print("\n----------------------------------------")
    print(f"OVERALL SIGNAL: {overall_signal}")
    print("----------------------------------------")

    print("\nCOMBINED MARKET ANALYSIS COMPLETE")
    print("----------------------------------------")


# ============================================================
# ============================================================
# PHASE 12 - HISTORICAL BACKTESTING ENGINE
# ============================================================

import os
import math
from datetime import datetime, timedelta

# Full OHLC records loaded from the MT5 CSV.
csv_records = []

# The CSV file name used by the project.
CSV_FILE_NAME = "XAUUSD_H1_2026.csv"

# Risk/reward configurations to compare.
BACKTEST_RR = [1.5, 2.0, 2.5, 3.0]


def rolling_sma_series(prices, period):
    """Return an SMA value at every index where enough data exists."""
    result = [None] * len(prices)
    if len(prices) < period:
        return result

    running_sum = sum(prices[:period])
    result[period - 1] = running_sum / period

    for i in range(period, len(prices)):
        running_sum += prices[i]
        running_sum -= prices[i - period]
        result[i] = running_sum / period

    return result


def calculate_atr(records, period=14):
    """Calculate Wilder ATR using OHLC data without look-ahead."""
    n = len(records)
    atr = [None] * n
    if n <= period:
        return atr

    true_ranges = [None] * n

    for i in range(1, n):
        high = records[i]["high"]
        low = records[i]["low"]
        previous_close = records[i - 1]["close"]
        true_ranges[i] = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )

    first_values = [true_ranges[i] for i in range(1, period + 1)]
    first_atr = sum(first_values) / period
    atr[period] = first_atr

    for i in range(period + 1, n):
        atr[i] = (
            ((atr[i - 1] * (period - 1)) + true_ranges[i])
            / period
        )

    return atr


def average_prior(values, index, lookback):
    """Average only values strictly before index."""
    start = max(0, index - lookback)
    prior = [v for v in values[start:index] if v is not None]
    if not prior:
        return None
    return sum(prior) / len(prior)


def candle_confirmation(records, index):
    """Return bullish, bearish or neutral candle confirmation."""
    if index < 1:
        return "NEUTRAL"

    current = records[index]
    previous = records[index - 1]

    o = current["open"]
    h = current["high"]
    l = current["low"]
    c = current["close"]

    po = previous["open"]
    pc = previous["close"]

    body = abs(c - o)
    candle_range = h - l

    if candle_range <= 0:
        return "NEUTRAL"

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Bullish engulfing.
    bullish_engulfing = (
        pc < po and
        c > o and
        o <= pc and
        c >= po
    )

    # Bearish engulfing.
    bearish_engulfing = (
        pc > po and
        c < o and
        o >= pc and
        c <= po
    )

    strong_bullish = c > o and (body / candle_range) >= 0.65
    strong_bearish = c < o and (body / candle_range) >= 0.65

    bullish_rejection = (
        c > o and
        lower_wick >= max(body * 1.5, candle_range * 0.25) and
        c >= l + candle_range * 0.60
    )

    bearish_rejection = (
        c < o and
        upper_wick >= max(body * 1.5, candle_range * 0.25) and
        c <= l + candle_range * 0.40
    )

    if bullish_engulfing or strong_bullish or bullish_rejection:
        return "BULLISH"

    if bearish_engulfing or strong_bearish or bearish_rejection:
        return "BEARISH"

    return "NEUTRAL"


def market_structure(records, index, swing_strength=2, lookback=60):
    """Determine structure using only swings confirmed by bars already known."""
    if index < swing_strength * 2 + 5:
        return "UNCLEAR"

    start = max(swing_strength, index - lookback)
    end = index - swing_strength

    swing_highs = []
    swing_lows = []

    for i in range(start, end + 1):
        high = records[i]["high"]
        low = records[i]["low"]

        left_highs = [records[j]["high"] for j in range(i - swing_strength, i)]
        right_highs = [records[j]["high"] for j in range(i + 1, i + swing_strength + 1)]
        left_lows = [records[j]["low"] for j in range(i - swing_strength, i)]
        right_lows = [records[j]["low"] for j in range(i + 1, i + swing_strength + 1)]

        if left_highs and right_highs and high > max(left_highs) and high >= max(right_highs):
            swing_highs.append((i, high))

        if left_lows and right_lows and low < min(left_lows) and low <= min(right_lows):
            swing_lows.append((i, low))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "UNCLEAR"

    previous_high = swing_highs[-2][1]
    latest_high = swing_highs[-1][1]
    previous_low = swing_lows[-2][1]
    latest_low = swing_lows[-1][1]

    if latest_high > previous_high and latest_low > previous_low:
        return "BULLISH"

    if latest_high < previous_high and latest_low < previous_low:
        return "BEARISH"

    return "RANGING"


def support_resistance(records, index, lookback=20):
    """Return recent support/resistance using bars before the signal candle."""
    start = max(0, index - lookback)
    window = records[start:index]

    if len(window) < 5:
        return None, None

    support = min(row["low"] for row in window)
    resistance = max(row["high"] for row in window)
    return support, resistance


def validate_market_data(records):
    """Check chronological order, duplicates and OHLC consistency."""
    problems = []
    timestamps = []

    for row in records:
        timestamps.append(row["timestamp"])
        if row["high"] < max(row["open"], row["close"]):
            problems.append("High below open/close")
        if row["low"] > min(row["open"], row["close"]):
            problems.append("Low above open/close")

    duplicates = len(timestamps) - len(set(timestamps))
    if duplicates:
        problems.append(f"Duplicate timestamps: {duplicates}")

    out_of_order = sum(
        1 for i in range(1, len(timestamps))
        if timestamps[i] <= timestamps[i - 1]
    )
    if out_of_order:
        problems.append(f"Non-chronological records: {out_of_order}")

    return problems


def build_indicator_series(records):
    """Build all Phase 12 indicators once for the historical dataset."""
    closes = [row["close"] for row in records]

    sma20 = rolling_sma_series(closes, 20)
    sma50 = rolling_sma_series(closes, 50)
    sma200 = rolling_sma_series(closes, 200)

    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    rsi14 = calculate_rsi(closes, 14)
    _, _, macd, signal, histogram = calculate_macd(closes)
    atr14 = calculate_atr(records, 14)

    return {
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "ema12": ema12,
        "ema26": ema26,
        "rsi14": rsi14,
        "macd": macd,
        "signal": signal,
        "histogram": histogram,
        "atr14": atr14
    }


def evaluate_signal(records, indicators, index):
    """Evaluate one historical candle using only information available at that candle."""
    minimum_index = 200
    if index < minimum_index:
        return None

    price = records[index]["close"]
    sma20 = indicators["sma20"][index]
    sma50 = indicators["sma50"][index]
    sma200 = indicators["sma200"][index]
    ema12 = indicators["ema12"][index]
    ema26 = indicators["ema26"][index]
    rsi = indicators["rsi14"][index]
    macd = indicators["macd"][index]
    macd_signal = indicators["signal"][index]
    histogram = indicators["histogram"][index]
    atr = indicators["atr14"][index]

    needed = [sma20, sma50, sma200, ema12, ema26, rsi, macd, macd_signal, histogram, atr]
    if any(value is None for value in needed):
        return None

    bullish = 0
    bearish = 0
    reasons = []

    # 1. SMA trend: all three relationships must agree.
    if price > sma20 and sma20 > sma50 and sma50 > sma200:
        bullish += 1
        reasons.append("SMA trend bullish")
    elif price < sma20 and sma20 < sma50 and sma50 < sma200:
        bearish += 1
        reasons.append("SMA trend bearish")

    # 2. EMA trend.
    if ema12 > ema26:
        bullish += 1
        reasons.append("EMA bullish")
    elif ema12 < ema26:
        bearish += 1
        reasons.append("EMA bearish")

    # 3. RSI.
    if rsi > 55:
        bullish += 1
        reasons.append("RSI bullish")
    elif rsi < 45:
        bearish += 1
        reasons.append("RSI bearish")

    # 4. MACD line vs signal.
    if macd > macd_signal:
        bullish += 1
        reasons.append("MACD bullish")
    elif macd < macd_signal:
        bearish += 1
        reasons.append("MACD bearish")

    # 5. Histogram momentum: compare with previous valid histogram.
    previous_histogram = indicators["histogram"][index - 1]
    if previous_histogram is not None:
        if histogram > 0 and histogram > previous_histogram:
            bullish += 1
            reasons.append("MACD momentum bullish")
        elif histogram < 0 and histogram < previous_histogram:
            bearish += 1
            reasons.append("MACD momentum bearish")

    # 6. Market structure.
    structure = market_structure(records, index)
    if structure == "BULLISH":
        bullish += 1
        reasons.append("Market structure bullish")
    elif structure == "BEARISH":
        bearish += 1
        reasons.append("Market structure bearish")

    # 7. Candle confirmation.
    candle = candle_confirmation(records, index)
    if candle == "BULLISH":
        bullish += 1
        reasons.append("Candle confirmation bullish")
    elif candle == "BEARISH":
        bearish += 1
        reasons.append("Candle confirmation bearish")

    # Quality filter A: usable volatility. This is not a directional point.
    prior_atr_average = average_prior(indicators["atr14"], index, 50)
    if prior_atr_average is None or prior_atr_average <= 0:
        return None

    volatility_ok = (
        atr >= prior_atr_average * 0.50 and
        atr <= prior_atr_average * 2.50
    )

    # Quality filter B: support/resistance location. Also not a directional point.
    support, resistance = support_resistance(records, index, 20)
    stop_distance = atr * 1.5

    room_for_long = (
        resistance is not None and
        (resistance - price) >= stop_distance * 1.5
    )

    room_for_short = (
        support is not None and
        (price - support) >= stop_distance * 1.5
    )

    if not volatility_ok:
        return {
            "signal": "NO TRADE",
            "bullish": bullish,
            "bearish": bearish,
            "structure": structure,
            "candle": candle,
            "atr": atr,
            "entry": price,
            "stop_distance": stop_distance,
            "support": support,
            "resistance": resistance,
            "reasons": reasons,
            "filter_reason": "Volatility outside permitted range"
        }

    # Strict Phase 12 qualification: 7/7 directional confirmations,
    # plus valid market conditions and room to the opposing level.
    if bullish >= 7 and bullish > bearish and room_for_long:
        return {
            "signal": "BUY",
            "bullish": bullish,
            "bearish": bearish,
            "structure": structure,
            "candle": candle,
            "atr": atr,
            "entry": price,
            "stop_distance": stop_distance,
            "support": support,
            "resistance": resistance,
            "reasons": reasons,
            "filter_reason": "Qualified"
        }

    if bearish >= 7 and bearish > bullish and room_for_short:
        return {
            "signal": "SELL",
            "bullish": bullish,
            "bearish": bearish,
            "structure": structure,
            "candle": candle,
            "atr": atr,
            "entry": price,
            "stop_distance": stop_distance,
            "support": support,
            "resistance": resistance,
            "reasons": reasons,
            "filter_reason": "Qualified"
        }

    if bullish >= 7 and bullish > bearish and not room_for_long:
        filter_reason = "Strong bullish score but resistance too close"
    elif bearish >= 7 and bearish > bullish and not room_for_short:
        filter_reason = "Strong bearish score but support too close"
    else:
        filter_reason = "Directional score below strict threshold"

    return {
        "signal": "NO TRADE",
        "bullish": bullish,
        "bearish": bearish,
        "structure": structure,
        "candle": candle,
        "atr": atr,
        "entry": price,
        "stop_distance": stop_distance,
        "support": support,
        "resistance": resistance,
        "reasons": reasons,
        "filter_reason": filter_reason
    }


def resolve_trade(records, entry_index, signal, entry, stop, target, max_bars=1000):
    """Walk forward through future candles and resolve one trade."""
    last_index = min(len(records) - 1, entry_index + max_bars)

    for i in range(entry_index + 1, last_index + 1):
        high = records[i]["high"]
        low = records[i]["low"]

        if signal == "BUY":
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            hit_stop = high >= stop
            hit_target = low <= target

        # Conservative assumption when both levels are touched in one candle:
        # stop is treated as first because intrabar order is unknown.
        if hit_stop and hit_target:
            return "LOSS", i, -1.0

        if hit_target:
            return "WIN", i, target

        if hit_stop:
            return "LOSS", i, -1.0

    return "TIMEOUT", last_index, 0.0


def resolve_trade_r(records, entry_index, signal, entry, risk_distance, rr, max_bars=1000):
    """Resolve a trade and return outcome in R-multiples."""
    if signal == "BUY":
        stop = entry - risk_distance
        target = entry + (risk_distance * rr)
    else:
        stop = entry + risk_distance
        target = entry - (risk_distance * rr)

    last_index = min(len(records) - 1, entry_index + max_bars)

    for i in range(entry_index + 1, last_index + 1):
        high = records[i]["high"]
        low = records[i]["low"]

        if signal == "BUY":
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            hit_stop = high >= stop
            hit_target = low <= target

        if hit_stop and hit_target:
            return {
                "outcome": "LOSS",
                "exit_index": i,
                "r": -1.0,
                "stop": stop,
                "target": target
            }

        if hit_target:
            return {
                "outcome": "WIN",
                "exit_index": i,
                "r": rr,
                "stop": stop,
                "target": target
            }

        if hit_stop:
            return {
                "outcome": "LOSS",
                "exit_index": i,
                "r": -1.0,
                "stop": stop,
                "target": target
            }

    return {
        "outcome": "TIMEOUT",
        "exit_index": last_index,
        "r": 0.0,
        "stop": stop,
        "target": target
    }


def calculate_drawdown(r_values):
    """Calculate maximum drawdown from cumulative R."""
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for value in r_values:
        equity += value
        peak = max(peak, equity)
        drawdown = peak - equity
        max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown


def calculate_backtest_metrics(trades, rr):
    """Calculate performance metrics for one R:R configuration."""
    wins = sum(1 for trade in trades if trade["outcome"] == "WIN")
    losses = sum(1 for trade in trades if trade["outcome"] == "LOSS")
    timeouts = sum(1 for trade in trades if trade["outcome"] == "TIMEOUT")

    r_values = [trade["r"] for trade in trades]
    positive_r = sum(value for value in r_values if value > 0)
    negative_r = abs(sum(value for value in r_values if value < 0))

    total_r = sum(r_values)
    average_r = total_r / len(r_values) if r_values else 0.0

    win_rate = (wins / len(trades) * 100) if trades else 0.0
    profit_factor = (
        positive_r / negative_r
        if negative_r > 0
        else (math.inf if positive_r > 0 else 0.0)
    )

    expectancy = average_r
    max_drawdown = calculate_drawdown(r_values)

    return {
        "rr": rr,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "average_r": average_r,
        "total_r": total_r,
        "expectancy": expectancy,
        "max_drawdown_r": max_drawdown
    }


def run_backtest_for_rr(records, indicators, rr):
    """Run one-pass chronological backtest for one target ratio."""
    trades = []
    next_available_index = 200

    for i in range(200, len(records)):
        if i < next_available_index:
            continue

        evaluation = evaluate_signal(records, indicators, i)
        if evaluation is None or evaluation["signal"] == "NO TRADE":
            continue

        signal = evaluation["signal"]
        entry = evaluation["entry"]
        risk_distance = evaluation["stop_distance"]

        if risk_distance <= 0:
            continue

        if signal == "BUY":
            stop = entry - risk_distance
            target = entry + risk_distance * rr
        else:
            stop = entry + risk_distance
            target = entry - risk_distance * rr

        result = resolve_trade_r(
            records,
            i,
            signal,
            entry,
            risk_distance,
            rr
        )

        trades.append({
            "timestamp": records[i]["timestamp"],
            "signal": signal,
            "entry": entry,
            "stop": stop,
            "target": target,
            "bullish_score": evaluation["bullish"],
            "bearish_score": evaluation["bearish"],
            "structure": evaluation["structure"],
            "candle": evaluation["candle"],
            "atr": evaluation["atr"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"]
        })

        # One open position at a time for each R:R test.
        next_available_index = result["exit_index"] + 1

    return trades, calculate_backtest_metrics(trades, rr)


def export_backtest_csv(all_results, summary_metrics, output_path):
    """Export every tested trade plus the summary metrics to CSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["PHASE 12 BACKTEST TRADE RESULTS"])
        writer.writerow([])
        writer.writerow([
            "R:R", "Timestamp", "Signal", "Entry", "Stop", "Target",
            "Bullish Score", "Bearish Score", "Structure", "Candle",
            "ATR", "Outcome", "R Result", "Exit Timestamp"
        ])

        for rr in BACKTEST_RR:
            for trade in all_results[rr]:
                writer.writerow([
                    rr,
                    trade["timestamp"],
                    trade["signal"],
                    f'{trade["entry"]:.5f}',
                    f'{trade["stop"]:.5f}',
                    f'{trade["target"]:.5f}',
                    trade["bullish_score"],
                    trade["bearish_score"],
                    trade["structure"],
                    trade["candle"],
                    f'{trade["atr"]:.5f}',
                    trade["outcome"],
                    f'{trade["r"]:.4f}',
                    trade["exit_timestamp"]
                ])

        writer.writerow([])
        writer.writerow(["SUMMARY"])
        writer.writerow([
            "R:R", "Trades", "Wins", "Losses", "Timeouts", "Win Rate %",
            "Profit Factor", "Average R", "Total R", "Expectancy", "Max Drawdown R"
        ])

        for metrics in summary_metrics:
            pf = metrics["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f'{pf:.4f}'
            writer.writerow([
                metrics["rr"],
                metrics["trades"],
                metrics["wins"],
                metrics["losses"],
                metrics["timeouts"],
                f'{metrics["win_rate"]:.2f}',
                pf_text,
                f'{metrics["average_r"]:.4f}',
                f'{metrics["total_r"]:.4f}',
                f'{metrics["expectancy"]:.4f}',
                f'{metrics["max_drawdown_r"]:.4f}'
            ])


def print_backtest_summary(summary_metrics):
    """Display the four R:R test results."""
    print("\n========================================")
    print("       PHASE 12 BACKTEST RESULTS")
    print("========================================")

    for metrics in summary_metrics:
        pf = metrics["profit_factor"]
        pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"

        print(f"\nR:R = 1:{metrics['rr']}")
        print("----------------------------------------")
        print(f"Trades:          {metrics['trades']}")
        print(f"Wins:            {metrics['wins']}")
        print(f"Losses:          {metrics['losses']}")
        print(f"Timeouts:        {metrics['timeouts']}")
        print(f"Win Rate:        {metrics['win_rate']:.2f}%")
        print(f"Profit Factor:   {pf_text}")
        print(f"Average R:       {metrics['average_r']:.4f}")
        print(f"Total R:         {metrics['total_r']:.4f}")
        print(f"Expectancy:      {metrics['expectancy']:.4f} R/trade")
        print(f"Max Drawdown:    {metrics['max_drawdown_r']:.4f} R")


def phase12_backtest():
    """Run the complete historical backtest and export CSV results."""
    if not csv_records:
        print("\nERROR: No OHLC CSV data is loaded.")
        print("Please select Option 11 - CSV Data Import first.")
        return

    if len(csv_records) < 300:
        print("\nERROR: At least 300 historical records are recommended for Phase 12.")
        print(f"Records currently loaded: {len(csv_records)}")
        return

    print("\n========================================")
    print("       PHASE 12 BACKTEST ENGINE")
    print("========================================")
    print(f"Historical records: {len(csv_records)}")
    print("Rules: Strict 7/7 directional confirmations")
    print("Risk model: 1.5 ATR stop distance")
    print("R:R tests: 1:1.5 | 1:2 | 1:2.5 | 1:3")
    print("Look-ahead protection: ENABLED")

    problems = validate_market_data(csv_records)
    if problems:
        print("\nDATA VALIDATION WARNING")
        for problem in problems[:10]:
            print(f"- {problem}")
        if len(problems) > 10:
            print(f"- ...and {len(problems) - 10} more")
        print("\nBacktest stopped. Fix the data issues first.")
        return

    indicators = build_indicator_series(csv_records)

    # Count raw directional opportunities and strict qualified signals.
    buy_count = 0
    sell_count = 0
    no_trade_count = 0

    for i in range(200, len(csv_records)):
        evaluation = evaluate_signal(csv_records, indicators, i)
        if evaluation is None:
            continue
        if evaluation["signal"] == "BUY":
            buy_count += 1
        elif evaluation["signal"] == "SELL":
            sell_count += 1
        else:
            no_trade_count += 1

    print("\nSIGNAL FILTER SUMMARY")
    print("----------------------------------------")
    print(f"Qualified BUY signals:   {buy_count}")
    print(f"Qualified SELL signals:  {sell_count}")
    print(f"NO TRADE decisions:      {no_trade_count}")

    all_results = {}
    summary_metrics = []

    for rr in BACKTEST_RR:
        trades, metrics = run_backtest_for_rr(csv_records, indicators, rr)
        all_results[rr] = trades
        summary_metrics.append(metrics)

    print_backtest_summary(summary_metrics)

    source_directory = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(
        source_directory,
        "XAUUSD_Phase12_Backtest_Results.csv"
    )

    export_backtest_csv(
        all_results,
        summary_metrics,
        output_path
    )

    print("\n========================================")
    print("BACKTEST CSV EXPORTED")
    print("========================================")
    print(output_path)
    print("\nThe CSV contains both trade-by-trade results and summary metrics.")
    print("========================================")



# ============================================================
# PHASE 12.1 - DIAGNOSTIC BACKTEST LAYER
# ============================================================

# IMPORTANT:
# This diagnostic layer DOES NOT change the official Phase 12 7/7
# trading rule. It measures why setups are being rejected.
#
# It also uses a causal market-structure diagnostic. A historical
# backtest must not use candles to the right of the signal candle.

DIAGNOSTIC_THRESHOLDS = [7, 6, 5, 4]


def causal_market_structure(records, index, swing_strength=2, lookback=60):
    """Determine market structure using only information known by index.

    A swing at candidate i is considered confirmed only after the
    required right-side bars have already closed. Therefore the latest
    usable swing candidate is index - swing_strength.
    """
    if index < (swing_strength * 2 + 5):
        return "UNCLEAR"

    start = max(swing_strength, index - lookback)
    end = index - swing_strength

    swing_highs = []
    swing_lows = []

    for i in range(start, end + 1):
        high = records[i]["high"]
        low = records[i]["low"]

        left_highs = [
            records[j]["high"]
            for j in range(i - swing_strength, i)
        ]
        right_highs = [
            records[j]["high"]
            for j in range(i + 1, i + swing_strength + 1)
        ]
        left_lows = [
            records[j]["low"]
            for j in range(i - swing_strength, i)
        ]
        right_lows = [
            records[j]["low"]
            for j in range(i + 1, i + swing_strength + 1)
        ]

        if (
            left_highs and right_highs
            and high > max(left_highs)
            and high >= max(right_highs)
        ):
            swing_highs.append((i, high))

        if (
            left_lows and right_lows
            and low < min(left_lows)
            and low <= min(right_lows)
        ):
            swing_lows.append((i, low))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "UNCLEAR"

    previous_high = swing_highs[-2][1]
    latest_high = swing_highs[-1][1]
    previous_low = swing_lows[-2][1]
    latest_low = swing_lows[-1][1]

    if latest_high > previous_high and latest_low > previous_low:
        return "BULLISH"

    if latest_high < previous_high and latest_low < previous_low:
        return "BEARISH"

    return "RANGING"


def diagnostic_score_components(records, indicators, index):
    """Return the seven directional component results for one candle.

    Values are +1 for bullish, -1 for bearish and 0 for neutral.
    This function does not apply volatility or S/R filters.
    """
    minimum_index = 200
    if index < minimum_index:
        return None

    price = records[index]["close"]
    sma20 = indicators["sma20"][index]
    sma50 = indicators["sma50"][index]
    sma200 = indicators["sma200"][index]
    ema12 = indicators["ema12"][index]
    ema26 = indicators["ema26"][index]
    rsi = indicators["rsi14"][index]
    macd = indicators["macd"][index]
    macd_signal = indicators["signal"][index]
    histogram = indicators["histogram"][index]
    atr = indicators["atr14"][index]

    needed = [
        sma20, sma50, sma200, ema12, ema26, rsi,
        macd, macd_signal, histogram, atr
    ]

    if any(value is None for value in needed):
        return None

    components = {}

    # 1. SMA trend
    if price > sma20 and sma20 > sma50 and sma50 > sma200:
        components["SMA Trend"] = 1
    elif price < sma20 and sma20 < sma50 and sma50 < sma200:
        components["SMA Trend"] = -1
    else:
        components["SMA Trend"] = 0

    # 2. EMA trend
    if ema12 > ema26:
        components["EMA Trend"] = 1
    elif ema12 < ema26:
        components["EMA Trend"] = -1
    else:
        components["EMA Trend"] = 0

    # 3. RSI
    if rsi > 55:
        components["RSI"] = 1
    elif rsi < 45:
        components["RSI"] = -1
    else:
        components["RSI"] = 0

    # 4. MACD line vs signal
    if macd > macd_signal:
        components["MACD"] = 1
    elif macd < macd_signal:
        components["MACD"] = -1
    else:
        components["MACD"] = 0

    # 5. MACD histogram momentum
    previous_histogram = indicators["histogram"][index - 1]
    if previous_histogram is None:
        components["MACD Momentum"] = 0
    elif histogram > 0 and histogram > previous_histogram:
        components["MACD Momentum"] = 1
    elif histogram < 0 and histogram < previous_histogram:
        components["MACD Momentum"] = -1
    else:
        components["MACD Momentum"] = 0

    # 6. Causal market structure
    structure = causal_market_structure(records, index)
    if structure == "BULLISH":
        components["Market Structure"] = 1
    elif structure == "BEARISH":
        components["Market Structure"] = -1
    else:
        components["Market Structure"] = 0

    # 7. Candle confirmation
    candle = candle_confirmation(records, index)
    if candle == "BULLISH":
        components["Candle Confirmation"] = 1
    elif candle == "BEARISH":
        components["Candle Confirmation"] = -1
    else:
        components["Candle Confirmation"] = 0

    bullish = sum(1 for value in components.values() if value == 1)
    bearish = sum(1 for value in components.values() if value == -1)

    return {
        "components": components,
        "bullish": bullish,
        "bearish": bearish,
        "max_score": max(bullish, bearish),
        "dominant_direction": (
            "BULLISH" if bullish > bearish
            else "BEARISH" if bearish > bullish
            else "TIE"
        ),
        "structure": structure,
        "candle": candle,
        "atr": atr
    }


def diagnostic_filter_status(records, indicators, index, score_data):
    """Evaluate volatility and S/R filters without creating a trade."""
    atr = score_data["atr"]
    price = records[index]["close"]

    prior_atr_average = average_prior(indicators["atr14"], index, 50)

    if prior_atr_average is None or prior_atr_average <= 0:
        volatility_ok = False
        volatility_reason = "ATR baseline unavailable"
    else:
        volatility_ok = (
            atr >= prior_atr_average * 0.50
            and atr <= prior_atr_average * 2.50
        )
        volatility_reason = (
            "PASS" if volatility_ok
            else "Volatility outside permitted range"
        )

    support, resistance = support_resistance(records, index, 20)
    stop_distance = atr * 1.5

    room_for_long = (
        resistance is not None
        and (resistance - price) >= stop_distance * 1.5
    )

    room_for_short = (
        support is not None
        and (price - support) >= stop_distance * 1.5
    )

    direction = score_data["dominant_direction"]

    if direction == "BULLISH":
        sr_ok = room_for_long
        sr_reason = "PASS" if sr_ok else "Resistance too close"
    elif direction == "BEARISH":
        sr_ok = room_for_short
        sr_reason = "PASS" if sr_ok else "Support too close"
    else:
        sr_ok = False
        sr_reason = "Directional tie"

    return {
        "volatility_ok": volatility_ok,
        "volatility_reason": volatility_reason,
        "support": support,
        "resistance": resistance,
        "sr_ok": sr_ok,
        "sr_reason": sr_reason,
        "stop_distance": stop_distance
    }


def print_distribution(title, counts, descending=True):
    """Print score counts in a consistent format."""
    print(f"\n{title}")
    print("----------------------------------------")
    values = sorted(counts.keys(), reverse=descending)
    for score in values:
        print(f"{score}/7 : {counts[score]}")


def phase12_1_diagnostic():
    """Run the diagnostic layer without changing official Phase 12 rules."""
    if not csv_records:
        print("\nERROR: No OHLC CSV data is loaded.")
        print("Please select Option 11 - CSV Data Import first.")
        return

    if len(csv_records) < 300:
        print("\nERROR: At least 300 historical records are recommended.")
        print(f"Records currently loaded: {len(csv_records)}")
        return

    print("\n========================================")
    print("      PHASE 12.1 DIAGNOSTIC ENGINE")
    print("========================================")
    print(f"Historical records: {len(csv_records)}")
    print("Official Phase 12 rule: STRICT 7/7")
    print("Diagnostic thresholds: 7/7 | 6/7 | 5/7 | 4/7")
    print("Purpose: Find where potential setups are filtered out")
    print("Look-ahead-safe structure diagnostic: ENABLED")

    problems = validate_market_data(csv_records)
    if problems:
        print("\nDATA VALIDATION WARNING")
        for problem in problems[:10]:
            print(f"- {problem}")
        if len(problems) > 10:
            print(f"- ...and {len(problems) - 10} more")
        print("\nDiagnostic stopped. Fix the data issues first.")
        return

    indicators = build_indicator_series(csv_records)

    score_distribution = {score: 0 for score in range(8)}
    bullish_distribution = {score: 0 for score in range(8)}
    bearish_distribution = {score: 0 for score in range(8)}

    component_counts = {
        name: {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
        for name in [
            "SMA Trend", "EMA Trend", "RSI", "MACD",
            "MACD Momentum", "Market Structure", "Candle Confirmation"
        ]
    }

    total_checked = 0
    indicator_ready = 0
    volatility_pass = 0
    volatility_rejected = 0
    sr_pass = 0
    sr_rejected = 0
    tie_count = 0

    # Candidate funnel counts after each filter, for each threshold.
    threshold_raw = {threshold: 0 for threshold in DIAGNOSTIC_THRESHOLDS}
    threshold_after_volatility = {threshold: 0 for threshold in DIAGNOSTIC_THRESHOLDS}
    threshold_after_sr = {threshold: 0 for threshold in DIAGNOSTIC_THRESHOLDS}

    rejection_reasons = {
        "Directional score below 4": 0,
        "Volatility rejected": 0,
        "Support/Resistance rejected": 0,
        "Directional tie": 0
    }

    strict_7_7_qualified = {"BUY": 0, "SELL": 0}

    # Individual confirmation frequency is counted across all
    # indicator-ready candles, not only qualified trades.
    for i in range(200, len(csv_records)):
        total_checked += 1

        score_data = diagnostic_score_components(
            csv_records, indicators, i
        )

        if score_data is None:
            continue

        indicator_ready += 1

        bullish = score_data["bullish"]
        bearish = score_data["bearish"]
        max_score = score_data["max_score"]
        direction = score_data["dominant_direction"]

        score_distribution[max_score] += 1
        bullish_distribution[bullish] += 1
        bearish_distribution[bearish] += 1

        if direction == "TIE":
            tie_count += 1

        for name, value in score_data["components"].items():
            if value == 1:
                component_counts[name]["BULLISH"] += 1
            elif value == -1:
                component_counts[name]["BEARISH"] += 1
            else:
                component_counts[name]["NEUTRAL"] += 1

        filters = diagnostic_filter_status(
            csv_records, indicators, i, score_data
        )

        if filters["volatility_ok"]:
            volatility_pass += 1
        else:
            volatility_rejected += 1

        if filters["sr_ok"]:
            sr_pass += 1
        else:
            sr_rejected += 1

        for threshold in DIAGNOSTIC_THRESHOLDS:
            if direction != "TIE" and max_score >= threshold:
                threshold_raw[threshold] += 1

                if filters["volatility_ok"]:
                    threshold_after_volatility[threshold] += 1

                    if filters["sr_ok"]:
                        threshold_after_sr[threshold] += 1

        if max_score < 4:
            rejection_reasons["Directional score below 4"] += 1
        elif direction == "TIE":
            rejection_reasons["Directional tie"] += 1
        elif not filters["volatility_ok"]:
            rejection_reasons["Volatility rejected"] += 1
        elif not filters["sr_ok"]:
            rejection_reasons["Support/Resistance rejected"] += 1

        # This represents what the official Phase 12 rule would have
        # qualified, using the diagnostic's causal structure calculation.
        if (
            max_score == 7
            and direction == "BULLISH"
            and filters["volatility_ok"]
            and filters["sr_ok"]
        ):
            strict_7_7_qualified["BUY"] += 1

        if (
            max_score == 7
            and direction == "BEARISH"
            and filters["volatility_ok"]
            and filters["sr_ok"]
        ):
            strict_7_7_qualified["SELL"] += 1

    print("\n========================================")
    print("       DATASET DIAGNOSTICS")
    print("========================================")
    print(f"Historical records:       {len(csv_records)}")
    print(f"Candles checked:          {total_checked}")
    print(f"Indicator-ready candles:  {indicator_ready}")
    print(f"Directional ties:         {tie_count}")

    print_distribution(
        "MAX DIRECTIONAL SCORE DISTRIBUTION",
        score_distribution
    )

    print_distribution(
        "BULLISH SCORE DISTRIBUTION",
        bullish_distribution
    )

    print_distribution(
        "BEARISH SCORE DISTRIBUTION",
        bearish_distribution
    )

    print("\n========================================")
    print("       INDIVIDUAL CONFIRMATIONS")
    print("========================================")
    for name, counts in component_counts.items():
        print(f"\n{name}")
        print(
            f"Bullish: {counts['BULLISH']} | "
            f"Bearish: {counts['BEARISH']} | "
            f"Neutral: {counts['NEUTRAL']}"
        )

    print("\n========================================")
    print("          FILTER DIAGNOSTICS")
    print("========================================")
    print(f"Volatility PASS:          {volatility_pass}")
    print(f"Volatility REJECTED:      {volatility_rejected}")
    print(f"S/R PASS:                 {sr_pass}")
    print(f"S/R REJECTED:             {sr_rejected}")

    print("\n========================================")
    print("        THRESHOLD FUNNEL")
    print("========================================")
    print(
        "Threshold | Raw candidates | After volatility | After S/R"
    )
    print("----------------------------------------")
    for threshold in DIAGNOSTIC_THRESHOLDS:
        print(
            f"{threshold}/7       | "
            f"{threshold_raw[threshold]:14d} | "
            f"{threshold_after_volatility[threshold]:16d} | "
            f"{threshold_after_sr[threshold]:10d}"
        )

    print("\n========================================")
    print("       REJECTION BREAKDOWN")
    print("========================================")
    for reason, count in rejection_reasons.items():
        print(f"{reason}: {count}")

    print("\n========================================")
    print("       OFFICIAL 7/7 DIAGNOSTIC")
    print("========================================")
    print(f"Potential 7/7 BUY setups:  {threshold_raw[7] if threshold_raw[7] else 0}")
    print(f"Potential 7/7 after S/R:   {threshold_after_sr[7] if threshold_after_sr[7] else 0}")
    print(f"Causal 7/7 BUY qualified:  {strict_7_7_qualified['BUY']}")
    print(f"Causal 7/7 SELL qualified: {strict_7_7_qualified['SELL']}")
    print(
        "\nIMPORTANT: These counts are diagnostic only. "
        "They do not change the official Phase 12 rule."
    )

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "XAUUSD_Phase12_1_Diagnostic.csv"
    )

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["PHASE 12.1 DIAGNOSTIC REPORT"])
        writer.writerow(["Historical Records", len(csv_records)])
        writer.writerow(["Candles Checked", total_checked])
        writer.writerow(["Indicator Ready", indicator_ready])
        writer.writerow([])

        writer.writerow(["MAX SCORE DISTRIBUTION"])
        writer.writerow(["Score", "Count"])
        for score in range(7, -1, -1):
            writer.writerow([f"{score}/7", score_distribution[score]])

        writer.writerow([])
        writer.writerow(["BULLISH SCORE DISTRIBUTION"])
        writer.writerow(["Score", "Count"])
        for score in range(7, -1, -1):
            writer.writerow([f"{score}/7", bullish_distribution[score]])

        writer.writerow([])
        writer.writerow(["BEARISH SCORE DISTRIBUTION"])
        writer.writerow(["Score", "Count"])
        for score in range(7, -1, -1):
            writer.writerow([f"{score}/7", bearish_distribution[score]])

        writer.writerow([])
        writer.writerow(["INDIVIDUAL CONFIRMATIONS"])
        writer.writerow(["Component", "Bullish", "Bearish", "Neutral"])
        for name, counts in component_counts.items():
            writer.writerow([
                name,
                counts["BULLISH"],
                counts["BEARISH"],
                counts["NEUTRAL"]
            ])

        writer.writerow([])
        writer.writerow(["FILTER DIAGNOSTICS"])
        writer.writerow(["Metric", "Count"])
        writer.writerow(["Volatility PASS", volatility_pass])
        writer.writerow(["Volatility REJECTED", volatility_rejected])
        writer.writerow(["S/R PASS", sr_pass])
        writer.writerow(["S/R REJECTED", sr_rejected])
        writer.writerow(["Directional ties", tie_count])

        writer.writerow([])
        writer.writerow(["THRESHOLD FUNNEL"])
        writer.writerow([
            "Threshold", "Raw Candidates",
            "After Volatility", "After S/R"
        ])
        for threshold in DIAGNOSTIC_THRESHOLDS:
            writer.writerow([
                f"{threshold}/7",
                threshold_raw[threshold],
                threshold_after_volatility[threshold],
                threshold_after_sr[threshold]
            ])

        writer.writerow([])
        writer.writerow(["REJECTION BREAKDOWN"])
        writer.writerow(["Reason", "Count"])
        for reason, count in rejection_reasons.items():
            writer.writerow([reason, count])

        writer.writerow([])
        writer.writerow(["CAUSAL 7/7 QUALIFIED"])
        writer.writerow(["Signal", "Count"])
        writer.writerow(["BUY", strict_7_7_qualified["BUY"]])
        writer.writerow(["SELL", strict_7_7_qualified["SELL"]])

    print("\n========================================")
    print("DIAGNOSTIC CSV EXPORTED")
    print("========================================")
    print(output_path)
    print("The CSV contains the score distribution, filters, and funnel diagnostics.")
    print("========================================")


# ============================================================
# PHASE 12.2 - S/R DIAGNOSTIC + CLEAN ACCOUNTING
# ============================================================

# Phase 12.2 does NOT change the official Phase 12 trading rule.
# It investigates the Support/Resistance bottleneck and fixes the
# diagnostic accounting so ties, score failures, and filter failures
# are mutually exclusive and clearly reported.

SR_DIAGNOSTIC_THRESHOLDS = [7, 6, 5, 4]
SR_CLEARANCE_MULTIPLIERS = [0.50, 1.00, 1.50, 2.00, 2.25, 2.50, 3.00]


def phase12_2_sr_status(records, indicators, index, score_data):
    """Return detailed, causal S/R information for one historical candle.

    Support and resistance are calculated only from bars BEFORE the signal
    candle. The current Phase 12 requirement is preserved:

        stop distance = 1.5 * ATR
        required clearance = 1.5 * stop distance = 2.25 * ATR

    This function reports the raw distances so the threshold can be studied
    without changing the official rule.
    """
    price = records[index]["close"]
    atr = score_data["atr"]

    support, resistance = support_resistance(records, index, 20)

    result = {
        "price": price,
        "atr": atr,
        "support": support,
        "resistance": resistance,
        "long_distance": None,
        "short_distance": None,
        "long_distance_atr": None,
        "short_distance_atr": None,
        "direction": score_data["dominant_direction"],
        "current_required_clearance_atr": 2.25,
        "sr_ok": False,
        "sr_reason": "Directional tie"
    }

    if support is not None:
        result["short_distance"] = price - support
        if atr and atr > 0:
            result["short_distance_atr"] = (price - support) / atr

    if resistance is not None:
        result["long_distance"] = resistance - price
        if atr and atr > 0:
            result["long_distance_atr"] = (resistance - price) / atr

    direction = score_data["dominant_direction"]

    if direction == "BULLISH":
        if result["long_distance_atr"] is None:
            result["sr_reason"] = "Resistance unavailable"
        elif result["long_distance_atr"] >= 2.25:
            result["sr_ok"] = True
            result["sr_reason"] = "PASS"
        else:
            result["sr_reason"] = "Resistance too close"

    elif direction == "BEARISH":
        if result["short_distance_atr"] is None:
            result["sr_reason"] = "Support unavailable"
        elif result["short_distance_atr"] >= 2.25:
            result["sr_ok"] = True
            result["sr_reason"] = "PASS"
        else:
            result["sr_reason"] = "Support too close"

    return result


def phase12_2_diagnostic():
    """Diagnose S/R filtering and produce cleaned diagnostic accounting."""
    if not csv_records:
        print("\nERROR: No OHLC CSV data is loaded.")
        print("Please select Option 11 - CSV Data Import first.")
        return

    if len(csv_records) < 300:
        print("\nERROR: At least 300 historical records are recommended.")
        print(f"Records currently loaded: {len(csv_records)}")
        return

    print("\n========================================")
    print("   PHASE 12.2 S/R DIAGNOSTIC ENGINE")
    print("========================================")
    print(f"Historical records: {len(csv_records)}")
    print("Official Phase 12 score: STRICT 7/7")
    print("Current official S/R clearance: 2.25 ATR")
    print("Look-ahead-safe S/R calculation: ENABLED")
    print("Purpose: Diagnose S/R filtering without changing rules")

    problems = validate_market_data(csv_records)
    if problems:
        print("\nDATA VALIDATION WARNING")
        for problem in problems[:10]:
            print(f"- {problem}")
        if len(problems) > 10:
            print(f"- ...and {len(problems) - 10} more")
        print("\nDiagnostic stopped. Fix the data issues first.")
        return

    indicators = build_indicator_series(csv_records)

    total_checked = 0
    indicator_ready = 0
    ties = 0
    non_tie_candidates = 0

    # Clean, mutually exclusive accounting.
    clean_rejections = {
        "Directional tie": 0,
        "Directional score below 4": 0,
        "Volatility rejected": 0,
        "Support/Resistance rejected": 0,
        "Qualified through filters": 0
    }

    component_names = [
        "SMA Trend", "EMA Trend", "RSI", "MACD",
        "MACD Momentum", "Market Structure", "Candle Confirmation"
    ]

    score_distribution = {score: 0 for score in range(8)}
    threshold_raw = {t: 0 for t in SR_DIAGNOSTIC_THRESHOLDS}
    threshold_after_volatility = {t: 0 for t in SR_DIAGNOSTIC_THRESHOLDS}
    threshold_after_sr = {t: 0 for t in SR_DIAGNOSTIC_THRESHOLDS}

    direction_counts = {
        "BULLISH": {t: 0 for t in SR_DIAGNOSTIC_THRESHOLDS},
        "BEARISH": {t: 0 for t in SR_DIAGNOSTIC_THRESHOLDS}
    }

    sr_reason_counts = {
        "BULLISH": {},
        "BEARISH": {}
    }

    current_sr = {
        "PASS": 0,
        "Resistance too close": 0,
        "Support too close": 0,
        "Resistance unavailable": 0,
        "Support unavailable": 0
    }

    # Candidate-only clearance distributions.
    clearance_samples = {
        "BULLISH": [],
        "BEARISH": []
    }

    # Threshold sensitivity: how many non-tie candidates would pass S/R
    # at each ATR clearance multiple. This is diagnostic only.
    multiplier_counts = {
        m: {"BULLISH": 0, "BEARISH": 0, "TOTAL": 0}
        for m in SR_CLEARANCE_MULTIPLIERS
    }

    # Specifically track strict 7/7 candidates.
    strict_7 = {
        "BULLISH": {"RAW": 0, "SR_PASS": 0},
        "BEARISH": {"RAW": 0, "SR_PASS": 0}
    }

    # Detailed candidate rows for CSV export.
    detail_rows = []

    for i in range(200, len(csv_records)):
        total_checked += 1

        score_data = diagnostic_score_components(
            csv_records, indicators, i
        )

        if score_data is None:
            continue

        indicator_ready += 1

        bullish = score_data["bullish"]
        bearish = score_data["bearish"]
        max_score = score_data["max_score"]
        direction = score_data["dominant_direction"]

        score_distribution[max_score] += 1

        if direction == "TIE":
            ties += 1
            clean_rejections["Directional tie"] += 1
            continue

        non_tie_candidates += 1

        # Diagnostic filter evaluation is only meaningful for a directional
        # candidate. This prevents ties from contaminating S/R statistics.
        filters = diagnostic_filter_status(
            csv_records, indicators, i, score_data
        )

        sr_detail = phase12_2_sr_status(
            csv_records, indicators, i, score_data
        )

        # Clean rejection funnel: exactly one final category per candle.
        if max_score < 4:
            clean_rejections["Directional score below 4"] += 1
        elif not filters["volatility_ok"]:
            clean_rejections["Volatility rejected"] += 1
        elif not sr_detail["sr_ok"]:
            clean_rejections["Support/Resistance rejected"] += 1
        else:
            clean_rejections["Qualified through filters"] += 1

        for threshold in SR_DIAGNOSTIC_THRESHOLDS:
            if max_score >= threshold:
                threshold_raw[threshold] += 1
                direction_counts[direction][threshold] += 1

                if filters["volatility_ok"]:
                    threshold_after_volatility[threshold] += 1
                    if sr_detail["sr_ok"]:
                        threshold_after_sr[threshold] += 1

        reason = sr_detail["sr_reason"]
        sr_reason_counts[direction][reason] = (
            sr_reason_counts[direction].get(reason, 0) + 1
        )
        if reason in current_sr:
            current_sr[reason] += 1

        # Store ATR-normalized clearance for every directional candidate.
        if direction == "BULLISH" and sr_detail["long_distance_atr"] is not None:
            clearance = sr_detail["long_distance_atr"]
            clearance_samples["BULLISH"].append(clearance)
        elif direction == "BEARISH" and sr_detail["short_distance_atr"] is not None:
            clearance = sr_detail["short_distance_atr"]
            clearance_samples["BEARISH"].append(clearance)
        else:
            clearance = None

        # Sensitivity table across alternative clearance multiples.
        for multiplier in SR_CLEARANCE_MULTIPLIERS:
            passes = (
                clearance is not None
                and clearance >= multiplier
            )
            if passes:
                multiplier_counts[multiplier][direction] += 1
                multiplier_counts[multiplier]["TOTAL"] += 1

        if max_score == 7:
            strict_7[direction]["RAW"] += 1
            if filters["volatility_ok"] and sr_detail["sr_ok"]:
                strict_7[direction]["SR_PASS"] += 1

        detail_rows.append({
            "index": i,
            "timestamp": csv_records[i]["timestamp"],
            "price": csv_records[i]["close"],
            "direction": direction,
            "bullish_score": bullish,
            "bearish_score": bearish,
            "max_score": max_score,
            "atr": sr_detail["atr"],
            "support": sr_detail["support"],
            "resistance": sr_detail["resistance"],
            "long_distance_atr": sr_detail["long_distance_atr"],
            "short_distance_atr": sr_detail["short_distance_atr"],
            "sr_reason": sr_detail["sr_reason"],
            "sr_pass_current": sr_detail["sr_ok"]
        })

    def average(values):
        return sum(values) / len(values) if values else None

    def median(values):
        if not values:
            return None
        ordered = sorted(values)
        n = len(ordered)
        middle = n // 2
        if n % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2

    print("\n========================================")
    print("        CLEAN DATASET ACCOUNTING")
    print("========================================")
    print(f"Historical records:       {len(csv_records)}")
    print(f"Candles checked:          {total_checked}")
    print(f"Indicator-ready candles:  {indicator_ready}")
    print(f"Directional candidates:   {non_tie_candidates}")
    print(f"Directional ties:         {ties}")
    print("\nEvery indicator-ready candle is assigned one clean category.")

    print("\n========================================")
    print("       CLEAN REJECTION BREAKDOWN")
    print("========================================")
    for reason, count in clean_rejections.items():
        print(f"{reason}: {count}")

    print("\n========================================")
    print("       CORRECTED SCORE FUNNEL")
    print("========================================")
    print("Threshold | Raw | After Volatility | After S/R")
    print("-----------------------------------------------")
    for threshold in SR_DIAGNOSTIC_THRESHOLDS:
        print(
            f"{threshold}/7       | "
            f"{threshold_raw[threshold]:3d} | "
            f"{threshold_after_volatility[threshold]:16d} | "
            f"{threshold_after_sr[threshold]:9d}"
        )

    print("\n========================================")
    print("      CURRENT S/R REJECTION REASONS")
    print("========================================")
    print(f"PASS:                    {current_sr['PASS']}")
    print(f"Resistance too close:    {current_sr['Resistance too close']}")
    print(f"Support too close:       {current_sr['Support too close']}")
    print(f"Resistance unavailable:  {current_sr['Resistance unavailable']}")
    print(f"Support unavailable:     {current_sr['Support unavailable']}")

    print("\n========================================")
    print("      7/7 CANDIDATE DIAGNOSTIC")
    print("========================================")
    print(f"7/7 bullish candidates:  {strict_7['BULLISH']['RAW']}")
    print(f"7/7 bearish candidates:  {strict_7['BEARISH']['RAW']}")
    print(f"7/7 total candidates:    {strict_7['BULLISH']['RAW'] + strict_7['BEARISH']['RAW']}")
    print(f"7/7 bullish after S/R:   {strict_7['BULLISH']['SR_PASS']}")
    print(f"7/7 bearish after S/R:   {strict_7['BEARISH']['SR_PASS']}")
    print(f"7/7 total after S/R:     {strict_7['BULLISH']['SR_PASS'] + strict_7['BEARISH']['SR_PASS']}")

    print("\n========================================")
    print("    S/R CLEARANCE SENSITIVITY")
    print("========================================")
    print("Clearance | Bullish | Bearish | Total")
    print("----------------------------------------")
    for multiplier in SR_CLEARANCE_MULTIPLIERS:
        counts = multiplier_counts[multiplier]
        label = f"{multiplier:.2f} ATR"
        print(
            f"{label:9s} | "
            f"{counts['BULLISH']:7d} | "
            f"{counts['BEARISH']:7d} | "
            f"{counts['TOTAL']:5d}"
        )

    print("\nCurrent official Phase 12 requirement = 2.25 ATR clearance.")
    print("The sensitivity table is diagnostic only; no official rule was changed.")

    print("\n========================================")
    print("      CLEARANCE STATISTICS")
    print("========================================")
    for direction in ["BULLISH", "BEARISH"]:
        values = clearance_samples[direction]
        print(f"\n{direction} candidates with usable S/R: {len(values)}")
        avg = average(values)
        med = median(values)
        minimum = min(values) if values else None
        maximum = max(values) if values else None
        print(f"Average clearance: {avg:.3f} ATR" if avg is not None else "Average clearance: N/A")
        print(f"Median clearance:  {med:.3f} ATR" if med is not None else "Median clearance: N/A")
        print(f"Minimum clearance: {minimum:.3f} ATR" if minimum is not None else "Minimum clearance: N/A")
        print(f"Maximum clearance: {maximum:.3f} ATR" if maximum is not None else "Maximum clearance: N/A")

    print("\n========================================")
    print("      PHASE 12.2 CONCLUSION")
    print("========================================")
    print("1. The official 7/7 score remains unchanged.")
    print("2. The official 2.25 ATR S/R clearance remains unchanged.")
    print("3. Tie counts are now separated before filter accounting.")
    print("4. S/R statistics exclude directional ties.")
    print("5. The sensitivity table shows what alternative S/R clearances would do,")
    print("   but it does NOT select or activate a new threshold.")
    print("6. No backtest performance claim is made by this diagnostic.")

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "XAUUSD_Phase12_2_SR_Diagnostic.csv"
    )

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["PHASE 12.2 S/R DIAGNOSTIC REPORT"])
        writer.writerow(["Historical Records", len(csv_records)])
        writer.writerow(["Candles Checked", total_checked])
        writer.writerow(["Indicator Ready", indicator_ready])
        writer.writerow(["Directional Candidates", non_tie_candidates])
        writer.writerow(["Directional Ties", ties])
        writer.writerow([])

        writer.writerow(["CLEAN REJECTION BREAKDOWN"])
        writer.writerow(["Reason", "Count"])
        for reason, count in clean_rejections.items():
            writer.writerow([reason, count])
        writer.writerow([])

        writer.writerow(["CORRECTED SCORE FUNNEL"])
        writer.writerow(["Threshold", "Raw", "After Volatility", "After S/R"])
        for threshold in SR_DIAGNOSTIC_THRESHOLDS:
            writer.writerow([
                f"{threshold}/7",
                threshold_raw[threshold],
                threshold_after_volatility[threshold],
                threshold_after_sr[threshold]
            ])
        writer.writerow([])

        writer.writerow(["CURRENT S/R REASONS"])
        writer.writerow(["Reason", "Count"])
        for reason, count in current_sr.items():
            writer.writerow([reason, count])
        writer.writerow([])

        writer.writerow(["7/7 CANDIDATES"])
        writer.writerow(["Direction", "Raw", "After S/R"])
        writer.writerow([
            "BULLISH",
            strict_7["BULLISH"]["RAW"],
            strict_7["BULLISH"]["SR_PASS"]
        ])
        writer.writerow([
            "BEARISH",
            strict_7["BEARISH"]["RAW"],
            strict_7["BEARISH"]["SR_PASS"]
        ])
        writer.writerow([])

        writer.writerow(["S/R CLEARANCE SENSITIVITY"])
        writer.writerow(["Clearance ATR", "Bullish", "Bearish", "Total"])
        for multiplier in SR_CLEARANCE_MULTIPLIERS:
            counts = multiplier_counts[multiplier]
            writer.writerow([
                multiplier,
                counts["BULLISH"],
                counts["BEARISH"],
                counts["TOTAL"]
            ])
        writer.writerow([])

        writer.writerow(["CANDIDATE DETAIL"])
        writer.writerow([
            "Index", "Timestamp", "Price", "Direction",
            "Bullish Score", "Bearish Score", "Max Score",
            "ATR", "Support", "Resistance",
            "Long Distance ATR", "Short Distance ATR",
            "S/R Reason", "Current S/R Pass"
        ])
        for row in detail_rows:
            writer.writerow([
                row["index"], row["timestamp"], row["price"],
                row["direction"], row["bullish_score"],
                row["bearish_score"], row["max_score"], row["atr"],
                row["support"], row["resistance"],
                row["long_distance_atr"], row["short_distance_atr"],
                row["sr_reason"], row["sr_pass_current"]
            ])

    print("\n========================================")
    print("PHASE 12.2 CSV EXPORTED")
    print("========================================")
    print(output_path)
    print("The CSV contains cleaned accounting, S/R reasons, sensitivity")
    print("results, 7/7 diagnostics, and candidate-level S/R details.")
    print("========================================")

# ============================================================
# OPTION 11 - CSV DATA IMPORT
# ============================================================

def csv_data_import():
    """Load the MT5 XAUUSD H1 CSV including OHLC data."""
    global csv_prices, csv_records

    print("\n==========================================")
    print("          CSV DATA IMPORT")
    print("==========================================")

    matches = glob.glob(
        r"C:\Users\**\XAUUSD_H1_2026.csv",
        recursive=True
    )

    if not matches:
        print("\nERROR: XAUUSD_H1_2026.csv could not be found.")
        print("Make sure the MT5 CSV file is saved somewhere under C:\\Users.")
        return

    file_name = matches[0]
    print(f"\nFile found: {file_name}")

    try:
        with open(file_name, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, delimiter="\t")

            if reader.fieldnames is None:
                print("\nERROR: The CSV file has no header row.")
                return

            column_map = {
                "<DATE>": "Date",
                "<TIME>": "Time",
                "<OPEN>": "Open",
                "<HIGH>": "High",
                "<LOW>": "Low",
                "<CLOSE>": "Close",
                "<TICKVOL>": "TickVol",
                "<VOL>": "Vol",
                "<SPREAD>": "Spread"
            }

            reader.fieldnames = [
                column_map.get(column.strip(), column.strip())
                for column in reader.fieldnames
            ]

            rows = list(reader)

        required_columns = ["Date", "Time", "Open", "High", "Low", "Close"]
        missing_columns = [
            column for column in required_columns
            if column not in reader.fieldnames
        ]

        if missing_columns:
            print("\nWARNING: Missing required columns:")
            for column in missing_columns:
                print(f"- {column}")
            return

        if not rows:
            print("\nWARNING: The CSV file contains no data.")
            return

        loaded_records = []
        skipped = 0

        for row in rows:
            try:
                date_text = row["Date"].strip()
                time_text = row["Time"].strip()
                timestamp = f"{date_text} {time_text}"

                # Validate timestamp when possible. MT5 commonly uses YYYY.MM.DD.
                parsed_timestamp = None
                for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        parsed_timestamp = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        pass

                if parsed_timestamp is None:
                    raise ValueError("Invalid date/time")

                loaded_records.append({
                    "date": date_text,
                    "time": time_text,
                    "timestamp": timestamp,
                    "datetime": parsed_timestamp,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "tickvol": float(row.get("TickVol", 0) or 0),
                    "vol": float(row.get("Vol", 0) or 0),
                    "spread": float(row.get("Spread", 0) or 0)
                })
            except (ValueError, TypeError, KeyError):
                skipped += 1

        if not loaded_records:
            print("\nERROR: No valid OHLC records were found.")
            return

        # MT5 should already be chronological, but sorting here ensures the
        # backtester always receives ordered records. Validation still checks
        # duplicates after sorting.
        loaded_records.sort(key=lambda row: row["datetime"])

        csv_records = loaded_records
        csv_prices = [row["close"] for row in loaded_records]

        print("\nCSV IMPORT SUCCESSFUL")
        print("==========================================")
        print(f"File: {file_name}")
        print(f"Rows in file: {len(rows)}")
        print(f"Valid OHLC records loaded: {len(csv_records)}")
        print(f"Skipped invalid rows: {skipped}")
        print(f"Closing prices loaded: {len(csv_prices)}")

        print("\nColumns found:")
        for column in reader.fieldnames:
            print(f"- {column}")

        print("\nFirst 5 records:")
        print("------------------------------------------")
        for row in csv_records[:5]:
            print(
                f"{row['timestamp']} | "
                f"Open: {row['open']} | "
                f"High: {row['high']} | "
                f"Low: {row['low']} | "
                f"Close: {row['close']}"
            )

        print("\n==========================================")
        print("CSV DATA READY FOR ANALYSIS AND BACKTESTING")
        print("==========================================")

    except FileNotFoundError:
        print("\nERROR: CSV file was not found.")
    except PermissionError:
        print("\nERROR: Permission denied when opening the CSV file.")
    except Exception as error:
        print(f"\nERROR: {error}")



# ============================================================
# PHASE 12.3 - 7/7 S/R + R:R COMPARATIVE BACKTEST
# ============================================================

# Phase 12.3 keeps the official directional score at STRICT 7/7.
# It does NOT select a new S/R threshold. Instead, it performs a
# controlled historical comparison across the diagnostic S/R
# clearance levels and the four requested R:R targets.
#
# Each (S/R threshold, R:R) combination is backtested independently
# in chronological order with one open position at a time.
# The entry, stop model, outcome resolution, and look-ahead protection
# are kept consistent across all combinations.

PHASE12_3_SR_THRESHOLDS = [0.50, 1.00, 1.50, 2.00, 2.25, 2.50, 3.00]
PHASE12_3_RR_TARGETS = [1.5, 2.0, 2.5, 3.0]
PHASE12_3_SCORE_THRESHOLD = 7
PHASE12_3_STOP_ATR = 1.5


def phase12_3_sr_pass(records, index, score_data, clearance_atr):
    """Return S/R pass/fail for one directional 7/7 candidate."""
    price = records[index]["close"]
    atr = score_data["atr"]
    direction = score_data["dominant_direction"]

    if atr is None or atr <= 0 or direction == "TIE":
        return False, None, None, "INVALID"

    support, resistance = support_resistance(records, index, 20)

    if direction == "BULLISH":
        if resistance is None:
            return False, support, resistance, "Resistance unavailable"

        distance_atr = (resistance - price) / atr

        if distance_atr >= clearance_atr:
            return True, support, resistance, "PASS"

        return False, support, resistance, "Resistance too close"

    if support is None:
        return False, support, resistance, "Support unavailable"

    distance_atr = (price - support) / atr

    if distance_atr >= clearance_atr:
        return True, support, resistance, "PASS"

    return False, support, resistance, "Support too close"


def phase12_3_candidate(records, indicators, index, clearance_atr):
    """Evaluate only the strict 7/7 directional setup for Phase 12.3."""
    score_data = diagnostic_score_components(records, indicators, index)

    if score_data is None:
        return None

    if score_data["max_score"] != PHASE12_3_SCORE_THRESHOLD:
        return None

    if score_data["dominant_direction"] not in ("BULLISH", "BEARISH"):
        return None

    sr_ok, support, resistance, sr_reason = phase12_3_sr_pass(
        records,
        index,
        score_data,
        clearance_atr
    )

    if not sr_ok:
        return None

    atr = score_data["atr"]
    entry = records[index]["close"]
    risk_distance = atr * PHASE12_3_STOP_ATR

    if risk_distance <= 0:
        return None

    signal = "BUY" if score_data["dominant_direction"] == "BULLISH" else "SELL"

    return {
        "signal": signal,
        "entry": entry,
        "risk_distance": risk_distance,
        "atr": atr,
        "bullish_score": score_data["bullish"],
        "bearish_score": score_data["bearish"],
        "structure": score_data["structure"],
        "candle": score_data["candle"],
        "support": support,
        "resistance": resistance,
        "sr_reason": sr_reason
    }


def phase12_3_backtest_combination(records, indicators, sr_threshold, rr):
    """Backtest one S/R threshold and one R:R target chronologically."""
    trades = []
    next_available_index = 200

    for index in range(200, len(records)):
        if index < next_available_index:
            continue

        candidate = phase12_3_candidate(
            records,
            indicators,
            index,
            sr_threshold
        )

        if candidate is None:
            continue

        result = resolve_trade_r(
            records,
            index,
            candidate["signal"],
            candidate["entry"],
            candidate["risk_distance"],
            rr
        )

        if candidate["signal"] == "BUY":
            stop = candidate["entry"] - candidate["risk_distance"]
            target = candidate["entry"] + candidate["risk_distance"] * rr
        else:
            stop = candidate["entry"] + candidate["risk_distance"]
            target = candidate["entry"] - candidate["risk_distance"] * rr

        trades.append({
            "sr_threshold": sr_threshold,
            "rr": rr,
            "timestamp": records[index]["timestamp"],
            "signal": candidate["signal"],
            "entry": candidate["entry"],
            "stop": stop,
            "target": target,
            "risk_distance": candidate["risk_distance"],
            "atr": candidate["atr"],
            "bullish_score": candidate["bullish_score"],
            "bearish_score": candidate["bearish_score"],
            "structure": candidate["structure"],
            "candle": candidate["candle"],
            "support": candidate["support"],
            "resistance": candidate["resistance"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"]
        })

        # One open position at a time for this combination.
        next_available_index = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, rr)
    metrics["sr_threshold"] = sr_threshold

    return trades, metrics


def phase12_3_candidate_counts(records, indicators):
    """Count raw 7/7 candidates and 7/7 candidates passing each S/R level."""
    raw = {"BULLISH": 0, "BEARISH": 0, "TOTAL": 0}
    passed = {
        threshold: {"BULLISH": 0, "BEARISH": 0, "TOTAL": 0}
        for threshold in PHASE12_3_SR_THRESHOLDS
    }

    for index in range(200, len(records)):
        score_data = diagnostic_score_components(records, indicators, index)

        if score_data is None or score_data["max_score"] != 7:
            continue

        direction = score_data["dominant_direction"]
        if direction not in ("BULLISH", "BEARISH"):
            continue

        raw[direction] += 1
        raw["TOTAL"] += 1

        for threshold in PHASE12_3_SR_THRESHOLDS:
            sr_ok, _, _, _ = phase12_3_sr_pass(
                records, index, score_data, threshold
            )

            if sr_ok:
                passed[threshold][direction] += 1
                passed[threshold]["TOTAL"] += 1

    return raw, passed


def export_phase12_3_csv(all_trades, all_metrics, candidate_raw, candidate_passed, output_path):
    """Export Phase 12.3 trade-level results and comparison summary."""
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["PHASE 12.3 - 7/7 S/R + R:R COMPARATIVE BACKTEST"])
        writer.writerow(["Score threshold", "7/7"] )
        writer.writerow(["Stop model", "1.5 ATR"])
        writer.writerow(["S/R thresholds", ", ".join(f"{x:.2f}" for x in PHASE12_3_SR_THRESHOLDS)])
        writer.writerow(["R:R targets", ", ".join(f"1:{x:g}" for x in PHASE12_3_RR_TARGETS)])
        writer.writerow(["Method", "Chronological; one open position at a time per combination"])
        writer.writerow([])

        writer.writerow(["7/7 CANDIDATE COUNTS BY S/R THRESHOLD"])
        writer.writerow(["S/R ATR", "Raw 7/7", "Bullish", "Bearish", "After S/R"])
        for threshold in PHASE12_3_SR_THRESHOLDS:
            counts = candidate_passed[threshold]
            writer.writerow([
                threshold,
                candidate_raw["TOTAL"],
                counts["BULLISH"],
                counts["BEARISH"],
                counts["TOTAL"]
            ])

        writer.writerow([])
        writer.writerow(["PERFORMANCE SUMMARY"])
        writer.writerow([
            "S/R ATR", "R:R", "Trades", "Wins", "Losses", "Timeouts",
            "Win Rate %", "Profit Factor", "Average R", "Total R",
            "Expectancy R/Trade", "Max Drawdown R"
        ])

        for metrics in all_metrics:
            pf = metrics["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.4f}"
            writer.writerow([
                metrics["sr_threshold"],
                metrics["rr"],
                metrics["trades"],
                metrics["wins"],
                metrics["losses"],
                metrics["timeouts"],
                f"{metrics['win_rate']:.2f}",
                pf_text,
                f"{metrics['average_r']:.4f}",
                f"{metrics['total_r']:.4f}",
                f"{metrics['expectancy']:.4f}",
                f"{metrics['max_drawdown_r']:.4f}"
            ])

        writer.writerow([])
        writer.writerow(["TRADE-BY-TRADE RESULTS"])
        writer.writerow([
            "S/R ATR", "R:R", "Timestamp", "Signal", "Entry", "Stop",
            "Target", "ATR", "Bullish Score", "Bearish Score",
            "Structure", "Candle", "Support", "Resistance",
            "Outcome", "R Result", "Exit Timestamp"
        ])

        for key in sorted(all_trades.keys()):
            for trade in all_trades[key]:
                writer.writerow([
                    trade["sr_threshold"],
                    trade["rr"],
                    trade["timestamp"],
                    trade["signal"],
                    f"{trade['entry']:.5f}",
                    f"{trade['stop']:.5f}",
                    f"{trade['target']:.5f}",
                    f"{trade['atr']:.5f}",
                    trade["bullish_score"],
                    trade["bearish_score"],
                    trade["structure"],
                    trade["candle"],
                    f"{trade['support']:.5f}" if trade["support"] is not None else "",
                    f"{trade['resistance']:.5f}" if trade["resistance"] is not None else "",
                    trade["outcome"],
                    f"{trade['r']:.4f}",
                    trade["exit_timestamp"]
                ])


def phase12_3_comparative_backtest():
    """Compare 7/7 setups across S/R clearances and four R:R targets."""
    if not csv_records:
        print("\nERROR: No OHLC CSV data is loaded.")
        print("Please select Option 11 - CSV Data Import first.")
        return

    if len(csv_records) < 300:
        print("\nERROR: At least 300 historical records are recommended.")
        print(f"Records currently loaded: {len(csv_records)}")
        return

    print("\n========================================")
    print(" PHASE 12.3 COMPARATIVE BACKTEST ENGINE")
    print("========================================")
    print(f"Historical records: {len(csv_records)}")
    print("Directional score: STRICT 7/7")
    print("Stop model: 1.5 ATR")
    print("S/R thresholds: 0.50 | 1.00 | 1.50 | 2.00 | 2.25 | 2.50 | 3.00 ATR")
    print("R:R targets: 1:1.5 | 1:2 | 1:2.5 | 1:3")
    print("Look-ahead protection: ENABLED")
    print("One open position at a time: ENABLED")
    print("Purpose: Compare S/R clearance and R:R without changing the 7/7 rule")

    problems = validate_market_data(csv_records)
    if problems:
        print("\nDATA VALIDATION WARNING")
        for problem in problems[:10]:
            print(f"- {problem}")
        if len(problems) > 10:
            print(f"- ...and {len(problems) - 10} more")
        print("\nComparative backtest stopped. Fix the data issues first.")
        return

    indicators = build_indicator_series(csv_records)
    candidate_raw, candidate_passed = phase12_3_candidate_counts(
        csv_records, indicators
    )

    print("\n========================================")
    print("       7/7 CANDIDATE COUNTS")
    print("========================================")
    print(f"Raw 7/7 bullish candidates: {candidate_raw['BULLISH']}")
    print(f"Raw 7/7 bearish candidates: {candidate_raw['BEARISH']}")
    print(f"Raw 7/7 total candidates:   {candidate_raw['TOTAL']}")

    print("\nS/R THRESHOLD | BULLISH | BEARISH | TOTAL")
    print("------------------------------------------")
    for threshold in PHASE12_3_SR_THRESHOLDS:
        counts = candidate_passed[threshold]
        print(
            f"{threshold:>7.2f} ATR | "
            f"{counts['BULLISH']:7d} | "
            f"{counts['BEARISH']:7d} | "
            f"{counts['TOTAL']:5d}"
        )

    all_trades = {}
    all_metrics = []

    for threshold in PHASE12_3_SR_THRESHOLDS:
        for rr in PHASE12_3_RR_TARGETS:
            key = (threshold, rr)
            trades, metrics = phase12_3_backtest_combination(
                csv_records, indicators, threshold, rr
            )
            all_trades[key] = trades
            all_metrics.append(metrics)

    print("\n========================================")
    print("       PERFORMANCE COMPARISON")
    print("========================================")
    print(
        "S/R ATR | R:R  | Trades | Win%  | PF     | Avg R  | Total R | Max DD"
    )
    print("-----------------------------------------------------------------------")

    for metrics in all_metrics:
        pf = metrics["profit_factor"]
        pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
        print(
            f"{metrics['sr_threshold']:>7.2f} | "
            f"1:{metrics['rr']:<4g} | "
            f"{metrics['trades']:6d} | "
            f"{metrics['win_rate']:5.1f}% | "
            f"{pf_text:>6} | "
            f"{metrics['average_r']:6.3f} | "
            f"{metrics['total_r']:7.2f} | "
            f"{metrics['max_drawdown_r']:6.2f}"
        )

    print("\n========================================")
    print("       CURRENT 2.25 ATR RESULTS")
    print("========================================")
    for rr in PHASE12_3_RR_TARGETS:
        metrics = next(
            item for item in all_metrics
            if item["sr_threshold"] == 2.25 and item["rr"] == rr
        )
        pf = metrics["profit_factor"]
        pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
        print(
            f"1:{rr:g} -> Trades: {metrics['trades']}, "
            f"Win Rate: {metrics['win_rate']:.2f}%, "
            f"PF: {pf_text}, Avg R: {metrics['average_r']:.4f}, "
            f"Total R: {metrics['total_r']:.4f}"
        )

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "XAUUSD_Phase12_3_Comparative_Backtest.csv"
    )

    export_phase12_3_csv(
        all_trades,
        all_metrics,
        candidate_raw,
        candidate_passed,
        output_path
    )

    print("\n========================================")
    print("PHASE 12.3 CSV EXPORTED")
    print("========================================")
    print(output_path)
    print("The CSV contains candidate counts, all 28 performance tests,")
    print("and trade-by-trade results.")
    print("\nIMPORTANT: This phase compares historical results only.")
    print("It does NOT select a winning threshold or claim future accuracy.")
    print("========================================")


# ============================================================
# PHASE 12.4 - 70/30 OUT-OF-SAMPLE VALIDATION
# ============================================================

PHASE12_4_SR_THRESHOLDS = [0.50, 0.75, 1.00, 1.25, 1.50]
PHASE12_4_RR_TARGETS = [1.5, 2.0, 2.5, 3.0]
PHASE12_4_SCORE_THRESHOLD = 7
PHASE12_4_STOP_ATR = 1.5
PHASE12_4_TRAIN_RATIO = 0.70


def resolve_trade_r_until(records, entry_index, signal, entry, risk_distance, rr, end_index):
    """Resolve a trade without crossing a chronological train/validation boundary."""
    if signal == "BUY":
        stop = entry - risk_distance
        target = entry + (risk_distance * rr)
    else:
        stop = entry + risk_distance
        target = entry - (risk_distance * rr)

    last_index = min(len(records) - 1, end_index)

    for i in range(entry_index + 1, last_index + 1):
        high = records[i]["high"]
        low = records[i]["low"]

        if signal == "BUY":
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            hit_stop = high >= stop
            hit_target = low <= target

        # Conservative rule: if both are touched in the same candle,
        # treat the stop as occurring first because intrabar order is unknown.
        if hit_stop and hit_target:
            return {"outcome": "LOSS", "exit_index": i, "r": -1.0,
                    "stop": stop, "target": target, "resolved": True}

        if hit_target:
            return {"outcome": "WIN", "exit_index": i, "r": rr,
                    "stop": stop, "target": target, "resolved": True}

        if hit_stop:
            return {"outcome": "LOSS", "exit_index": i, "r": -1.0,
                    "stop": stop, "target": target, "resolved": True}

    # Do not manufacture a timeout at the train/validation boundary.
    # The final unresolved candidate is excluded from the completed-trade metrics.
    return {"outcome": "BOUNDARY", "exit_index": last_index, "r": 0.0,
            "stop": stop, "target": target, "resolved": False}


def phase12_4_candidate(records, indicators, index, clearance_atr):
    """Evaluate one strict 7/7 candidate using only data available at index."""
    score_data = diagnostic_score_components(records, indicators, index)
    if score_data is None:
        return None

    if score_data["max_score"] != PHASE12_4_SCORE_THRESHOLD:
        return None

    direction = score_data["dominant_direction"]
    if direction not in ("BULLISH", "BEARISH"):
        return None

    atr = score_data["atr"]
    if atr is None or atr <= 0:
        return None

    support, resistance = support_resistance(records, index, 20)
    price = records[index]["close"]

    if direction == "BULLISH":
        if resistance is None:
            return None
        clearance = (resistance - price) / atr
        if clearance < clearance_atr:
            return None
        signal = "BUY"
    else:
        if support is None:
            return None
        clearance = (price - support) / atr
        if clearance < clearance_atr:
            return None
        signal = "SELL"

    return {
        "signal": signal,
        "entry": price,
        "risk_distance": atr * PHASE12_4_STOP_ATR,
        "atr": atr,
        "bullish_score": score_data["bullish"],
        "bearish_score": score_data["bearish"],
        "structure": score_data["structure"],
        "candle": score_data["candle"],
        "support": support,
        "resistance": resistance,
        "clearance_atr": clearance
    }


def phase12_4_backtest_period(records, indicators, start_index, end_index, sr_threshold, rr):
    """Backtest one configuration strictly inside one chronological period."""
    trades = []
    next_available_index = start_index

    for index in range(max(200, start_index), end_index + 1):
        if index < next_available_index:
            continue

        candidate = phase12_4_candidate(records, indicators, index, sr_threshold)
        if candidate is None:
            continue

        result = resolve_trade_r_until(
            records, index, candidate["signal"], candidate["entry"],
            candidate["risk_distance"], rr, end_index
        )

        # A trade that crosses the split boundary is not included in either
        # period's completed-trade statistics.
        if not result["resolved"]:
            continue

        if candidate["signal"] == "BUY":
            stop = candidate["entry"] - candidate["risk_distance"]
            target = candidate["entry"] + candidate["risk_distance"] * rr
        else:
            stop = candidate["entry"] + candidate["risk_distance"]
            target = candidate["entry"] - candidate["risk_distance"] * rr

        trades.append({
            "period": "TRAIN" if start_index == 200 else "VALIDATION",
            "sr_threshold": sr_threshold,
            "rr": rr,
            "timestamp": records[index]["timestamp"],
            "signal": candidate["signal"],
            "entry": candidate["entry"],
            "stop": stop,
            "target": target,
            "risk_distance": candidate["risk_distance"],
            "atr": candidate["atr"],
            "bullish_score": candidate["bullish_score"],
            "bearish_score": candidate["bearish_score"],
            "structure": candidate["structure"],
            "candle": candidate["candle"],
            "support": candidate["support"],
            "resistance": candidate["resistance"],
            "clearance_atr": candidate["clearance_atr"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"]
        })

        next_available_index = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, rr)
    metrics["sr_threshold"] = sr_threshold
    metrics["period"] = "TRAIN" if start_index == 200 else "VALIDATION"
    return trades, metrics


def export_phase12_4_csv(all_trades, all_metrics, split_index, output_path):
    """Export Phase 12.4 split definitions, summary metrics and trade details."""
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["PHASE 12.4 - 70/30 OUT-OF-SAMPLE VALIDATION"])
        writer.writerow(["Score threshold", "7/7"])
        writer.writerow(["Stop model", "1.5 ATR"])
        writer.writerow(["Training ratio", "70% chronological"])
        writer.writerow(["Validation ratio", "30% chronological"])
        writer.writerow(["Training end index", split_index - 1])
        writer.writerow(["Validation start index", split_index])
        writer.writerow(["S/R thresholds", ", ".join(f"{x:.2f}" for x in PHASE12_4_SR_THRESHOLDS)])
        writer.writerow(["R:R targets", ", ".join(f"1:{x:g}" for x in PHASE12_4_RR_TARGETS)])
        writer.writerow(["Method", "Chronological; one open position at a time; unresolved split-boundary trades excluded"])
        writer.writerow([])

        writer.writerow(["PERIOD SUMMARY"])
        writer.writerow([
            "Period", "S/R ATR", "R:R", "Trades", "Wins", "Losses",
            "Timeouts", "Win Rate %", "Profit Factor", "Average R",
            "Total R", "Expectancy R/Trade", "Max Drawdown R"
        ])

        for metrics in all_metrics:
            pf = metrics["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.4f}"
            writer.writerow([
                metrics["period"], metrics["sr_threshold"], metrics["rr"],
                metrics["trades"], metrics["wins"], metrics["losses"],
                metrics["timeouts"], f"{metrics['win_rate']:.2f}", pf_text,
                f"{metrics['average_r']:.4f}", f"{metrics['total_r']:.4f}",
                f"{metrics['expectancy']:.4f}", f"{metrics['max_drawdown_r']:.4f}"
            ])

        writer.writerow([])
        writer.writerow(["TRADE-BY-TRADE RESULTS"])
        writer.writerow([
            "Period", "S/R ATR", "R:R", "Timestamp", "Signal", "Entry",
            "Stop", "Target", "ATR", "Bullish Score", "Bearish Score",
            "Structure", "Candle", "Support", "Resistance",
            "Clearance ATR", "Outcome", "R Result", "Exit Timestamp"
        ])

        for key in sorted(all_trades.keys(), key=str):
            for trade in all_trades[key]:
                writer.writerow([
                    trade["period"], trade["sr_threshold"], trade["rr"],
                    trade["timestamp"], trade["signal"], f"{trade['entry']:.5f}",
                    f"{trade['stop']:.5f}", f"{trade['target']:.5f}",
                    f"{trade['atr']:.5f}", trade["bullish_score"],
                    trade["bearish_score"], trade["structure"], trade["candle"],
                    f"{trade['support']:.5f}" if trade["support"] is not None else "",
                    f"{trade['resistance']:.5f}" if trade["resistance"] is not None else "",
                    f"{trade['clearance_atr']:.4f}", trade["outcome"],
                    f"{trade['r']:.4f}", trade["exit_timestamp"]
                ])


def phase12_4_validation():
    """Run a chronological 70/30 development/validation experiment."""
    if not csv_records:
        print("\nERROR: No OHLC CSV data is loaded.")
        print("Please select Option 11 - CSV Data Import first.")
        return

    if len(csv_records) < 1000:
        print("\nERROR: At least 1000 historical records are recommended.")
        print(f"Records currently loaded: {len(csv_records)}")
        return

    problems = validate_market_data(csv_records)
    if problems:
        print("\nDATA VALIDATION WARNING")
        for problem in problems[:10]:
            print(f"- {problem}")
        if len(problems) > 10:
            print(f"- ...and {len(problems) - 10} more")
        print("\nValidation stopped. Fix the data issues first.")
        return

    split_index = int(len(csv_records) * PHASE12_4_TRAIN_RATIO)
    split_index = max(201, min(split_index, len(csv_records) - 1))

    train_count = split_index
    validation_count = len(csv_records) - split_index
    train_start = 200
    train_end = split_index - 1
    validation_start = split_index
    validation_end = len(csv_records) - 1

    print("\n========================================")
    print(" PHASE 12.4 OUT-OF-SAMPLE VALIDATION")
    print("========================================")
    print(f"Historical records: {len(csv_records)}")
    print("Directional score: STRICT 7/7")
    print("Stop model: 1.5 ATR")
    print("Chronological split: 70% TRAIN / 30% VALIDATION")
    print(f"Training records:   {train_count}")
    print(f"Validation records: {validation_count}")
    print(f"Training range:     index {train_start} to {train_end}")
    print(f"Validation range:   index {validation_start} to {validation_end}")
    print("S/R thresholds: 0.50 | 0.75 | 1.00 | 1.25 | 1.50 ATR")
    print("R:R targets: 1:1.5 | 1:2 | 1:2.5 | 1:3")
    print("Look-ahead protection: ENABLED")
    print("Split-boundary leakage protection: ENABLED")
    print("One open position at a time: ENABLED")
    print("\nPurpose: measure whether fixed 7/7 configurations remain stable")
    print("on later unseen historical data. No configuration is selected automatically.")

    indicators = build_indicator_series(csv_records)

    # Candidate counts are descriptive only and are calculated separately by period.
    candidate_counts = {
        "TRAIN": {threshold: {"BULLISH": 0, "BEARISH": 0, "TOTAL": 0} for threshold in PHASE12_4_SR_THRESHOLDS},
        "VALIDATION": {threshold: {"BULLISH": 0, "BEARISH": 0, "TOTAL": 0} for threshold in PHASE12_4_SR_THRESHOLDS}
    }

    for period_name, start_idx, end_idx in [
        ("TRAIN", train_start, train_end),
        ("VALIDATION", validation_start, validation_end)
    ]:
        for index in range(start_idx, end_idx + 1):
            score_data = diagnostic_score_components(csv_records, indicators, index)
            if score_data is None or score_data["max_score"] != 7:
                continue
            direction = score_data["dominant_direction"]
            if direction not in ("BULLISH", "BEARISH"):
                continue
            for threshold in PHASE12_4_SR_THRESHOLDS:
                candidate = phase12_4_candidate(csv_records, indicators, index, threshold)
                if candidate is not None:
                    candidate_counts[period_name][threshold][direction] += 1
                    candidate_counts[period_name][threshold]["TOTAL"] += 1

    print("\n========================================")
    print("       7/7 CANDIDATE COUNTS")
    print("========================================")
    print("S/R ATR | TRAIN | VALIDATION")
    print("--------------------------------")
    for threshold in PHASE12_4_SR_THRESHOLDS:
        print(
            f"{threshold:>7.2f} | "
            f"{candidate_counts['TRAIN'][threshold]['TOTAL']:5d} | "
            f"{candidate_counts['VALIDATION'][threshold]['TOTAL']:10d}"
        )

    all_trades = {}
    all_metrics = []

    for threshold in PHASE12_4_SR_THRESHOLDS:
        for rr in PHASE12_4_RR_TARGETS:
            train_trades, train_metrics = phase12_4_backtest_period(
                csv_records, indicators, train_start, train_end, threshold, rr
            )
            validation_trades, validation_metrics = phase12_4_backtest_period(
                csv_records, indicators, validation_start, validation_end, threshold, rr
            )

            key = (threshold, rr)
            all_trades[("TRAIN", threshold, rr)] = train_trades
            all_trades[("VALIDATION", threshold, rr)] = validation_trades
            all_metrics.extend([train_metrics, validation_metrics])

    def print_metrics_table(period):
        print(f"\n========================================")
        print(f" {period} PERFORMANCE")
        print("========================================")
        print("S/R ATR | R:R  | Trades | Win%  | PF     | Avg R  | Total R | Max DD")
        print("-----------------------------------------------------------------------")
        for metrics in all_metrics:
            if metrics["period"] != period:
                continue
            pf = metrics["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
            print(
                f"{metrics['sr_threshold']:>7.2f} | "
                f"1:{metrics['rr']:<4g} | "
                f"{metrics['trades']:6d} | "
                f"{metrics['win_rate']:5.1f}% | "
                f"{pf_text:>6} | "
                f"{metrics['average_r']:6.3f} | "
                f"{metrics['total_r']:7.2f} | "
                f"{metrics['max_drawdown_r']:6.2f}"
            )

    print_metrics_table("TRAIN")
    print_metrics_table("VALIDATION")

    print("\n========================================")
    print("       TRAIN / VALIDATION STABILITY")
    print("========================================")
    print("S/R ATR | R:R  | Train R | Valid R | Both Positive? | Trades T/V")
    print("-----------------------------------------------------------------")

    for threshold in PHASE12_4_SR_THRESHOLDS:
        for rr in PHASE12_4_RR_TARGETS:
            train = next(m for m in all_metrics if m["period"] == "TRAIN" and m["sr_threshold"] == threshold and m["rr"] == rr)
            valid = next(m for m in all_metrics if m["period"] == "VALIDATION" and m["sr_threshold"] == threshold and m["rr"] == rr)
            both_positive = train["total_r"] > 0 and valid["total_r"] > 0
            print(
                f"{threshold:>7.2f} | 1:{rr:<4g} | "
                f"{train['total_r']:>7.2f} | {valid['total_r']:>8.2f} | "
                f"{'YES' if both_positive else 'NO':>14} | "
                f"{train['trades']:>6d}/{valid['trades']:<6d}"
            )

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "XAUUSD_Phase12_4_70_30_Validation.csv"
    )

    export_phase12_4_csv(all_trades, all_metrics, split_index, output_path)

    print("\n========================================")
    print("PHASE 12.4 CSV EXPORTED")
    print("========================================")
    print(output_path)
    print("The CSV contains train/validation metrics and trade-by-trade results.")
    print("\nIMPORTANT:")
    print("- This is historical validation, not a guarantee of future performance.")
    print("- No configuration is automatically selected as the final strategy.")
    print("- Validation results are kept separate from training results.")
    print("========================================")

# ============================================================
# MAIN MENU - PHASE 12
# ============================================================

PHASE12_5_SR_THRESHOLDS = [0.50, 0.75, 1.00, 1.25, 1.50]
PHASE12_5_RR = 2.0
PHASE12_5_SCORE_THRESHOLD = 7
PHASE12_5_STOP_ATR = 1.5
PHASE12_5_WINDOWS = 5


def resolve_trade_r_until(records, entry_index, signal, entry, risk_distance, rr, end_index):
    """Resolve a trade without crossing a chronological train/validation boundary."""
    if signal == "BUY":
        stop = entry - risk_distance
        target = entry + (risk_distance * rr)
    else:
        stop = entry + risk_distance
        target = entry - (risk_distance * rr)

    last_index = min(len(records) - 1, end_index)

    for i in range(entry_index + 1, last_index + 1):
        high = records[i]["high"]
        low = records[i]["low"]

        if signal == "BUY":
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            hit_stop = high >= stop
            hit_target = low <= target

        # Conservative rule: if both are touched in the same candle,
        # treat the stop as occurring first because intrabar order is unknown.
        if hit_stop and hit_target:
            return {"outcome": "LOSS", "exit_index": i, "r": -1.0,
                    "stop": stop, "target": target, "resolved": True}

        if hit_target:
            return {"outcome": "WIN", "exit_index": i, "r": rr,
                    "stop": stop, "target": target, "resolved": True}

        if hit_stop:
            return {"outcome": "LOSS", "exit_index": i, "r": -1.0,
                    "stop": stop, "target": target, "resolved": True}

    # Do not manufacture a timeout at the train/validation boundary.
    # The final unresolved candidate is excluded from the completed-trade metrics.
    return {"outcome": "BOUNDARY", "exit_index": last_index, "r": 0.0,
            "stop": stop, "target": target, "resolved": False}


def phase12_5_candidate(records, indicators, index, clearance_atr):
    """Evaluate one strict 7/7 candidate using only data available at index."""
    score_data = diagnostic_score_components(records, indicators, index)
    if score_data is None:
        return None

    if score_data["max_score"] != PHASE12_5_SCORE_THRESHOLD:
        return None

    direction = score_data["dominant_direction"]
    if direction not in ("BULLISH", "BEARISH"):
        return None

    atr = score_data["atr"]
    if atr is None or atr <= 0:
        return None

    support, resistance = support_resistance(records, index, 20)
    price = records[index]["close"]

    if direction == "BULLISH":
        if resistance is None:
            return None
        clearance = (resistance - price) / atr
        if clearance < clearance_atr:
            return None
        signal = "BUY"
    else:
        if support is None:
            return None
        clearance = (price - support) / atr
        if clearance < clearance_atr:
            return None
        signal = "SELL"

    return {
        "signal": signal,
        "entry": price,
        "risk_distance": atr * PHASE12_5_STOP_ATR,
        "atr": atr,
        "bullish_score": score_data["bullish"],
        "bearish_score": score_data["bearish"],
        "structure": score_data["structure"],
        "candle": score_data["candle"],
        "support": support,
        "resistance": resistance,
        "clearance_atr": clearance
    }


def phase12_5_backtest_period(records, indicators, start_index, end_index, sr_threshold, rr, window_number):
    """Backtest one configuration strictly inside one chronological period."""
    trades = []
    next_available_index = start_index

    for index in range(max(200, start_index), end_index + 1):
        if index < next_available_index:
            continue

        candidate = phase12_5_candidate(records, indicators, index, sr_threshold)
        if candidate is None:
            continue

        result = resolve_trade_r_until(
            records, index, candidate["signal"], candidate["entry"],
            candidate["risk_distance"], rr, end_index
        )

        # A trade that crosses the split boundary is not included in either
        # period's completed-trade statistics.
        if not result["resolved"]:
            continue

        if candidate["signal"] == "BUY":
            stop = candidate["entry"] - candidate["risk_distance"]
            target = candidate["entry"] + candidate["risk_distance"] * rr
        else:
            stop = candidate["entry"] + candidate["risk_distance"]
            target = candidate["entry"] - candidate["risk_distance"] * rr

        trades.append({
            "period": f"WINDOW_{window_number}",
            "sr_threshold": sr_threshold,
            "rr": rr,
            "timestamp": records[index]["timestamp"],
            "signal": candidate["signal"],
            "entry": candidate["entry"],
            "stop": stop,
            "target": target,
            "risk_distance": candidate["risk_distance"],
            "atr": candidate["atr"],
            "bullish_score": candidate["bullish_score"],
            "bearish_score": candidate["bearish_score"],
            "structure": candidate["structure"],
            "candle": candidate["candle"],
            "support": candidate["support"],
            "resistance": candidate["resistance"],
            "clearance_atr": candidate["clearance_atr"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"]
        })

        next_available_index = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, rr)
    metrics["sr_threshold"] = sr_threshold
    metrics["period"] = f"WINDOW_{window_number}"
    return trades, metrics





def build_phase12_5_windows(records, usable_start=200, number_of_windows=5):
    """Create five contiguous chronological windows with no shuffling."""
    last_index = len(records) - 1
    usable_count = last_index - usable_start + 1

    if usable_count < number_of_windows:
        return []

    base_size = usable_count // number_of_windows
    remainder = usable_count % number_of_windows

    windows = []
    current = usable_start

    for n in range(number_of_windows):
        size = base_size + (1 if n < remainder else 0)
        start = current
        end = start + size - 1
        windows.append((start, end))
        current = end + 1

    return windows


def export_phase12_5_csv(all_trades, all_summaries, windows, output_path):
    """Export Phase 12.5 window definitions, summaries and trade details."""
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(["PHASE 12.5 - CORRECTED ROLLING MULTI-WINDOW VALIDATION"])
        writer.writerow(["Directional score", "7/7"])
        writer.writerow(["Stop model", "1.5 ATR"])
        writer.writerow(["R:R target", "1:2"])
        writer.writerow(["S/R thresholds", ", ".join(f"{x:.2f}" for x in PHASE12_5_SR_THRESHOLDS)])
        writer.writerow(["Windows", PHASE12_5_WINDOWS])
        writer.writerow(["Method", "Five contiguous chronological windows using the Phase 12.4 candidate and trade-resolution engine"])
        writer.writerow([])

        writer.writerow(["WINDOW DEFINITIONS"])
        writer.writerow(["Window", "Start Index", "End Index", "Start Timestamp", "End Timestamp"])
        for n, (start, end) in enumerate(windows, 1):
            writer.writerow([
                n, start, end,
                csv_records[start]["timestamp"],
                csv_records[end]["timestamp"]
            ])

        writer.writerow([])
        writer.writerow(["WINDOW SUMMARY"])
        writer.writerow([
            "Window", "S/R ATR", "R:R", "Trades", "Wins", "Losses",
            "Timeouts", "Win Rate %", "Profit Factor", "Average R",
            "Total R", "Expectancy R/Trade", "Max Drawdown R"
        ])

        for summary in all_summaries:
            pf = summary["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.4f}"
            writer.writerow([
                summary["window"], summary["sr_threshold"], summary["rr"],
                summary["trades"], summary["wins"], summary["losses"],
                summary["timeouts"], f"{summary['win_rate']:.2f}", pf_text,
                f"{summary['average_r']:.4f}", f"{summary['total_r']:.4f}",
                f"{summary['expectancy']:.4f}", f"{summary['max_drawdown_r']:.4f}"
            ])

        writer.writerow([])
        writer.writerow(["TRADE DETAILS"])
        writer.writerow([
            "Window", "S/R ATR", "R:R", "Timestamp", "Signal", "Entry",
            "Stop", "Target", "ATR", "Risk Distance", "Bullish Score",
            "Bearish Score", "Structure", "Candle", "Support", "Resistance",
            "Clearance ATR", "Outcome", "R", "Exit Timestamp", "Exit Index"
        ])

        for trade in all_trades:
            writer.writerow([
                trade["period"], trade["sr_threshold"], trade["rr"],
                trade["timestamp"], trade["signal"], trade["entry"],
                trade["stop"], trade["target"], trade["atr"],
                trade["risk_distance"], trade["bullish_score"],
                trade["bearish_score"], trade["structure"], trade["candle"],
                trade["support"], trade["resistance"], trade["clearance_atr"],
                trade["outcome"], trade["r"], trade["exit_timestamp"],
                trade["exit_index"]
            ])


def phase12_5_validation():
    """Run corrected five-window chronological validation."""
    print("\n========================================")
    print(" PHASE 12.5 CORRECTED ROLLING VALIDATION")
    print("========================================")

    if not check_csv_data():
        return

    # Phase 12.4 stores the imported MT5 OHLC data in the global
    # csv_records list. Keep Phase 12.5 on that exact same data source
    # so the rolling validation uses the identical Phase 12.4 dataset.
    records = csv_records
    if not records:
        print("ERROR: No valid OHLC records are available.")
        return

    indicators = build_indicator_series(records)
    usable_start = 200

    windows = build_phase12_5_windows(
        records,
        usable_start=usable_start,
        number_of_windows=PHASE12_5_WINDOWS
    )

    if len(windows) != PHASE12_5_WINDOWS:
        print("ERROR: Unable to create the required validation windows.")
        return

    print(f"\nHistorical records: {len(records)}")
    print(f"Indicator warm-up: {usable_start}")
    print("Validation windows: 5 chronological periods")
    print("Candidate engine: SAME as Phase 12.4")
    print("Trade engine: SAME as Phase 12.4")
    print("Score threshold: 7/7")
    print("Stop: 1.5 ATR")
    print("R:R: 1:2")

    print("\nWindow definitions:")
    for n, (start, end) in enumerate(windows, 1):
        print(
            f"  Window {n}: records {start} to {end} | "
            f"{records[start]['timestamp']} -> {records[end]['timestamp']}"
        )

    all_trades = []
    all_summaries = []

    for threshold in PHASE12_5_SR_THRESHOLDS:
        print("\n" + "=" * 72)
        print(f"S/R CLEARANCE = {threshold:.2f} ATR | R:R = 1:2")
        print("=" * 72)

        threshold_results = []

        for n, (start, end) in enumerate(windows, 1):
            trades, metrics = phase12_5_backtest_period(
                records,
                indicators,
                start,
                end,
                threshold,
                PHASE12_5_RR,
                n
            )

            all_trades.extend(trades)

            summary = dict(metrics)
            summary["window"] = n
            summary["sr_threshold"] = threshold
            summary["rr"] = PHASE12_5_RR
            all_summaries.append(summary)
            threshold_results.append(summary)

            pf = summary["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"

            print(
                f"Window {n}: Trades {summary['trades']}, "
                f"Win Rate {summary['win_rate']:.2f}%, "
                f"PF {pf_text}, Avg R {summary['average_r']:.4f}, "
                f"Total R {summary['total_r']:.2f}, "
                f"Max DD {summary['max_drawdown_r']:.2f}R"
            )

        positive = sum(1 for m in threshold_results if m["total_r"] > 0)
        nonnegative = sum(1 for m in threshold_results if m["total_r"] >= 0)
        total_trades = sum(m["trades"] for m in threshold_results)
        total_r = sum(m["total_r"] for m in threshold_results)

        print(
            f"\nThreshold summary: {positive}/5 windows positive | "
            f"{nonnegative}/5 non-negative | Trades {total_trades} | "
            f"Combined Total R {total_r:.2f}"
        )

    print("\n" + "=" * 72)
    print("PHASE 12.5 COMPARISON SUMMARY")
    print("=" * 72)
    print("\nThis summary is descriptive; it does not automatically select a final configuration.")
    print("\nThreshold | Positive | Non-negative | Trades | Total R")
    print("-" * 58)

    for threshold in PHASE12_5_SR_THRESHOLDS:
        rows = [m for m in all_summaries if m["sr_threshold"] == threshold]
        positive = sum(1 for m in rows if m["total_r"] > 0)
        nonnegative = sum(1 for m in rows if m["total_r"] >= 0)
        trades = sum(m["trades"] for m in rows)
        total_r = sum(m["total_r"] for m in rows)

        print(
            f"   {threshold:>4.2f}   |"
            f"    {positive}/5    |"
            f"      {nonnegative}/5      |"
            f"  {trades:>4}  |"
            f"  {total_r:>7.2f}"
        )

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "XAUUSD_Phase12_5_Corrected_Rolling_Validation.csv"
    )

    export_phase12_5_csv(
        all_trades,
        all_summaries,
        windows,
        output_path
    )

    print("\n========================================")
    print("PHASE 12.5 CSV EXPORTED")
    print("========================================")
    print(output_path)
    print("The CSV contains window definitions, summary metrics,")
    print("and trade-by-trade results.")
    print("\nPhase 12.5 corrected validation complete.")
    print("========================================")





# ============================================================
# PHASE 12.6 - TRADE-LEVEL FAILURE & FEATURE ANALYSIS
# ============================================================

PHASE12_6_SR_THRESHOLD = 0.50
PHASE12_6_RR = 2.0
PHASE12_6_MIN_INDEX = 200


def phase12_6_bucket(clearance):
    """Return a descriptive S/R clearance bucket for trade-level analysis."""
    if clearance < 0.75:
        return "0.50-<0.75 ATR"
    if clearance < 1.00:
        return "0.75-<1.00 ATR"
    if clearance < 1.25:
        return "1.00-<1.25 ATR"
    if clearance < 1.50:
        return "1.25-<1.50 ATR"
    return ">=1.50 ATR"


def phase12_6_feature_row(records, indicators, trade):
    """Build a detailed feature row for one baseline Phase 12.5 trade."""
    timestamp = trade["timestamp"]
    entry_index = None

    # Timestamps are unique in the imported MT5 H1 dataset.
    for i, row in enumerate(records):
        if row["timestamp"] == timestamp:
            entry_index = i
            break

    if entry_index is None:
        return None

    idx = entry_index
    price = records[idx]["close"]
    previous_hist = indicators["histogram"][idx - 1] if idx > 0 else None
    atr = indicators["atr14"][idx]
    atr_baseline = average_prior(indicators["atr14"], idx, 50)

    score_data = diagnostic_score_components(records, indicators, idx)
    components = score_data["components"] if score_data else {}

    row = {
        "window": trade["period"],
        "entry_index": idx,
        "timestamp": timestamp,
        "signal": trade["signal"],
        "outcome": trade["outcome"],
        "r": trade["r"],
        "exit_timestamp": trade["exit_timestamp"],
        "exit_index": trade["exit_index"],
        "holding_bars": trade["exit_index"] - idx,
        "entry": trade["entry"],
        "stop": trade["stop"],
        "target": trade["target"],
        "atr14": atr,
        "risk_distance": trade["risk_distance"],
        "clearance_atr": trade["clearance_atr"],
        "clearance_bucket": phase12_6_bucket(trade["clearance_atr"]),
        "support": trade["support"],
        "resistance": trade["resistance"],
        "sma20": indicators["sma20"][idx],
        "sma50": indicators["sma50"][idx],
        "sma200": indicators["sma200"][idx],
        "ema12": indicators["ema12"][idx],
        "ema26": indicators["ema26"][idx],
        "rsi14": indicators["rsi14"][idx],
        "macd": indicators["macd"][idx],
        "macd_signal": indicators["signal"][idx],
        "macd_histogram": indicators["histogram"][idx],
        "previous_histogram": previous_hist,
        "atr_50_bar_average": atr_baseline,
        "atr_vs_50_bar_average": (
            atr / atr_baseline if atr_baseline not in (None, 0) else None
        ),
        "bullish_score": trade["bullish_score"],
        "bearish_score": trade["bearish_score"],
        "sma_component": components.get("SMA Trend", 0),
        "ema_component": components.get("EMA Trend", 0),
        "rsi_component": components.get("RSI", 0),
        "macd_component": components.get("MACD", 0),
        "macd_momentum_component": components.get("MACD Momentum", 0),
        "structure_component": components.get("Market Structure", 0),
        "candle_component": components.get("Candle Confirmation", 0),
        "structure": trade["structure"],
        "candle": trade["candle"]
    }

    # Additional raw candle information available at entry.
    current = records[idx]
    row["open"] = current["open"]
    row["high"] = current["high"]
    row["low"] = current["low"]
    row["close"] = current["close"]
    row["candle_range"] = current["high"] - current["low"]
    row["candle_body"] = abs(current["close"] - current["open"])
    row["body_to_range"] = (
        row["candle_body"] / row["candle_range"]
        if row["candle_range"] > 0 else None
    )
    if current["close"] > current["open"]:
        row["candle_body_direction"] = "BULLISH"
    elif current["close"] < current["open"]:
        row["candle_body_direction"] = "BEARISH"
    else:
        row["candle_body_direction"] = "NEUTRAL"

    return row


def phase12_6_print_table(rows):
    """Print a readable compact table of the 22 baseline trades."""
    print("\n" + "=" * 112)
    print("PHASE 12.6 - ALL BASELINE TRADES")
    print("=" * 112)
    print(
        f"{'#':>2} {'Win':>4} {'Date/Time':<17} {'Sig':>4} "
        f"{'Clear':>6} {'RSI':>6} {'ATR':>7} {'Hold':>4} "
        f"{'Outcome':>7} {'R':>5}"
    )
    print("-" * 112)

    for n, row in enumerate(rows, 1):
        print(
            f"{n:>2} {row['window'].replace('WINDOW_', 'W'):>4} "
            f"{row['timestamp']:<17} {row['signal']:>4} "
            f"{row['clearance_atr']:>6.3f} {row['rsi14']:>6.2f} "
            f"{row['atr14']:>7.2f} {row['holding_bars']:>4} "
            f"{row['outcome']:>7} {row['r']:>5.1f}"
        )


def phase12_6_group_summary(rows, key_name, title):
    """Print grouped trade counts and R results."""
    groups = {}
    for row in rows:
        key = row[key_name]
        groups.setdefault(key, []).append(row)

    print("\n" + "=" * 86)
    print(title)
    print("=" * 86)
    print(
        f"{'Group':<22} {'Trades':>6} {'Wins':>6} {'Losses':>7} "
        f"{'Win %':>8} {'Total R':>9} {'Avg R':>8}"
    )
    print("-" * 86)

    for key, items in groups.items():
        wins = sum(1 for r in items if r["outcome"] == "WIN")
        losses = sum(1 for r in items if r["outcome"] == "LOSS")
        total_r = sum(r["r"] for r in items)
        win_rate = wins / len(items) * 100 if items else 0
        avg_r = total_r / len(items) if items else 0
        print(
            f"{str(key):<22} {len(items):>6} {wins:>6} {losses:>7} "
            f"{win_rate:>7.2f}% {total_r:>9.2f} {avg_r:>8.3f}"
        )


def phase12_6_validation():
    """Analyze the 0.50 ATR / 1:2 / 7-of-7 baseline without changing rules."""
    print("\n" + "=" * 96)
    print(" PHASE 12.6 TRADE-LEVEL FAILURE & FEATURE ANALYSIS")
    print("=" * 96)
    print("Baseline: 7/7 | S/R 0.50 ATR | Stop 1.5 ATR | R:R 1:2")
    print("Analysis only: NO strategy rules are changed by this phase.")

    if not check_csv_data():
        return

    records = csv_records
    if not records:
        print("ERROR: No valid OHLC records are available.")
        return

    indicators = build_indicator_series(records)
    windows = build_phase12_5_windows(
        records,
        usable_start=PHASE12_6_MIN_INDEX,
        number_of_windows=5
    )

    # Re-run exactly the established Phase 12.5 engine for the baseline.
    baseline_trades = []
    for n, (start, end) in enumerate(windows, 1):
        trades, _ = phase12_5_backtest_period(
            records,
            indicators,
            start,
            end,
            PHASE12_6_SR_THRESHOLD,
            PHASE12_6_RR,
            n
        )
        baseline_trades.extend(trades)

    rows = []
    for trade in baseline_trades:
        feature_row = phase12_6_feature_row(records, indicators, trade)
        if feature_row is not None:
            rows.append(feature_row)

    if not rows:
        print("ERROR: No baseline trades were reconstructed.")
        return

    rows.sort(key=lambda r: r["entry_index"])

    wins = sum(1 for r in rows if r["outcome"] == "WIN")
    losses = sum(1 for r in rows if r["outcome"] == "LOSS")
    total_r = sum(r["r"] for r in rows)
    avg_r = total_r / len(rows)
    win_rate = wins / len(rows) * 100

    print("\nBaseline reconstructed:")
    print(f"Trades: {len(rows)}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total R: {total_r:.2f}")
    print(f"Average R: {avg_r:.4f}")

    phase12_6_print_table(rows)
    phase12_6_group_summary(rows, "signal", "DIRECTION ANALYSIS")
    phase12_6_group_summary(rows, "clearance_bucket", "S/R CLEARANCE BUCKET ANALYSIS")
    phase12_6_group_summary(rows, "window", "WINDOW ANALYSIS")
    phase12_6_group_summary(rows, "outcome", "OUTCOME CHECK")

    # Hour-of-day grouping is descriptive only; no new trading rule is created.
    for row in rows:
        row["entry_hour"] = int(row["timestamp"].split()[1].split(":")[0])
    phase12_6_group_summary(rows, "entry_hour", "ENTRY HOUR ANALYSIS")

    print("\n" + "=" * 96)
    print("KEY DIAGNOSTIC COUNTS")
    print("=" * 96)

    losing_rows = [r for r in rows if r["outcome"] == "LOSS"]
    winning_rows = [r for r in rows if r["outcome"] == "WIN"]

    buy_losses = sum(1 for r in losing_rows if r["signal"] == "BUY")
    sell_losses = sum(1 for r in losing_rows if r["signal"] == "SELL")
    buy_wins = sum(1 for r in winning_rows if r["signal"] == "BUY")
    sell_wins = sum(1 for r in winning_rows if r["signal"] == "SELL")

    print(f"BUY:  {buy_wins} wins / {buy_losses} losses")
    print(f"SELL: {sell_wins} wins / {sell_losses} losses")

    print("\nLosing-trade clearance buckets:")
    loss_buckets = {}
    for row in losing_rows:
        loss_buckets[row["clearance_bucket"]] = loss_buckets.get(row["clearance_bucket"], 0) + 1
    for bucket, count in loss_buckets.items():
        print(f"  {bucket}: {count}")

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "XAUUSD_Phase12_6_Trade_Level_Analysis.csv"
    )

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 96)
    print("PHASE 12.6 CSV EXPORTED")
    print("=" * 96)
    print(output_path)
    print("Contains the reconstructed 22-trade baseline and underlying indicator features.")
    print("\nPhase 12.6 analysis complete.")
    print("=" * 96)


# ============================================================
# PHASE 12.7 - PREDEFINED HYPOTHESIS TESTING
# ============================================================

PHASE12_7_MIN_INDEX = 200
PHASE12_7_RR = 2.0
PHASE12_7_STOP_ATR = 1.5
PHASE12_7_BASE_SR = 0.50
PHASE12_7_WINDOWS = 5

# These hypotheses are fixed in advance for this experiment.
# They are NOT optimized per window.
PHASE12_7_HYPOTHESES = [
    {
        "id": "BASELINE",
        "label": "Baseline 7/7",
        "sell_only": False,
        "strong_rsi": False,
        "exclude_mid_clearance": False,
    },
    {
        "id": "SELL_ONLY",
        "label": "SELL-only",
        "sell_only": True,
        "strong_rsi": False,
        "exclude_mid_clearance": False,
    },
    {
        "id": "STRONG_RSI",
        "label": "Strong RSI (BUY >=60 / SELL <=40)",
        "sell_only": False,
        "strong_rsi": True,
        "exclude_mid_clearance": False,
    },
    {
        "id": "SR_GAP",
        "label": "Exclude 0.75-<1.00 ATR",
        "sell_only": False,
        "strong_rsi": False,
        "exclude_mid_clearance": True,
    },
    {
        "id": "SELL_SR",
        "label": "SELL-only + S/R gap exclusion",
        "sell_only": True,
        "strong_rsi": False,
        "exclude_mid_clearance": True,
    },
    {
        "id": "SELL_RSI",
        "label": "SELL-only + RSI <=40",
        "sell_only": True,
        "strong_rsi": True,
        "exclude_mid_clearance": False,
    },
    {
        "id": "COMBINED",
        "label": "SELL-only + RSI <=40 + S/R gap exclusion",
        "sell_only": True,
        "strong_rsi": True,
        "exclude_mid_clearance": True,
    },
]


def phase12_7_candidate(records, indicators, index, hypothesis):
    """Apply the exact Phase 12.5 candidate engine plus one fixed hypothesis."""
    score_data = diagnostic_score_components(records, indicators, index)
    if score_data is None:
        return None

    if score_data["max_score"] != 7:
        return None

    direction = score_data["dominant_direction"]
    if direction not in ("BULLISH", "BEARISH"):
        return None

    atr = score_data["atr"]
    if atr is None or atr <= 0:
        return None

    if hypothesis["sell_only"] and direction != "BEARISH":
        return None

    rsi = indicators["rsi14"][index]
    if hypothesis["strong_rsi"]:
        if direction == "BEARISH" and not (rsi is not None and rsi <= 40):
            return None
        if direction == "BULLISH" and not (rsi is not None and rsi >= 60):
            return None

    support, resistance = support_resistance(records, index, 20)
    price = records[index]["close"]

    if direction == "BULLISH":
        if resistance is None:
            return None
        clearance = (resistance - price) / atr
        signal = "BUY"
    else:
        if support is None:
            return None
        clearance = (price - support) / atr
        signal = "SELL"

    # Baseline remains 0.50 ATR. This hypothesis removes only the
    # empirically observed middle band 0.75 <= clearance < 1.00 ATR.
    if clearance < PHASE12_7_BASE_SR:
        return None
    if hypothesis["exclude_mid_clearance"] and 0.75 <= clearance < 1.00:
        return None

    return {
        "signal": signal,
        "entry": price,
        "risk_distance": atr * PHASE12_7_STOP_ATR,
        "atr": atr,
        "bullish_score": score_data["bullish"],
        "bearish_score": score_data["bearish"],
        "structure": score_data["structure"],
        "candle": score_data["candle"],
        "support": support,
        "resistance": resistance,
        "clearance_atr": clearance,
    }


def phase12_7_backtest_period(records, indicators, start_index, end_index, hypothesis, window_number):
    """Run one fixed hypothesis inside one chronological window."""
    trades = []
    next_available_index = start_index

    for index in range(max(PHASE12_7_MIN_INDEX, start_index), end_index + 1):
        if index < next_available_index:
            continue

        candidate = phase12_7_candidate(records, indicators, index, hypothesis)
        if candidate is None:
            continue

        result = resolve_trade_r_until(
            records, index, candidate["signal"], candidate["entry"],
            candidate["risk_distance"], PHASE12_7_RR, end_index
        )

        if not result["resolved"]:
            continue

        if candidate["signal"] == "BUY":
            stop = candidate["entry"] - candidate["risk_distance"]
            target = candidate["entry"] + candidate["risk_distance"] * PHASE12_7_RR
        else:
            stop = candidate["entry"] + candidate["risk_distance"]
            target = candidate["entry"] - candidate["risk_distance"] * PHASE12_7_RR

        trades.append({
            "period": f"WINDOW_{window_number}",
            "hypothesis": hypothesis["id"],
            "hypothesis_label": hypothesis["label"],
            "timestamp": records[index]["timestamp"],
            "signal": candidate["signal"],
            "entry": candidate["entry"],
            "stop": stop,
            "target": target,
            "risk_distance": candidate["risk_distance"],
            "atr": candidate["atr"],
            "bullish_score": candidate["bullish_score"],
            "bearish_score": candidate["bearish_score"],
            "structure": candidate["structure"],
            "candle": candidate["candle"],
            "support": candidate["support"],
            "resistance": candidate["resistance"],
            "clearance_atr": candidate["clearance_atr"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"],
        })

        next_available_index = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, PHASE12_7_RR)
    metrics["hypothesis"] = hypothesis["id"]
    metrics["window"] = window_number
    return trades, metrics


def phase12_7_print_window_result(hypothesis, window_number, metrics):
    pf = metrics["profit_factor"]
    pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
    print(
        f"Window {window_number}: Trades {metrics['trades']}, "
        f"Win Rate {metrics['win_rate']:.2f}%, PF {pf_text}, "
        f"Avg R {metrics['average_r']:.4f}, Total R {metrics['total_r']:.2f}, "
        f"Max DD {metrics['max_drawdown_r']:.2f}R"
    )


def phase12_7_export(all_trades, summaries, windows, output_path, timestamp_lookup):
    """Export Phase 12.7 experiment results."""
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["PHASE 12.7 - PREDEFINED HYPOTHESIS TESTING"])
        writer.writerow(["Baseline", "7/7 | S/R >= 0.50 ATR | Stop 1.5 ATR | R:R 1:2"])
        writer.writerow(["Important", "Hypotheses are fixed; no per-window optimization is performed."])
        writer.writerow(["Interpretation", "This is a hypothesis comparison on the existing 2026 dataset, not a virgin future holdout."])
        writer.writerow([])
        writer.writerow(["WINDOW DEFINITIONS"])
        writer.writerow(["Window", "Start Index", "End Index", "Start Timestamp", "End Timestamp"])
        for n, (start, end) in enumerate(windows, 1):
            writer.writerow([n, start, end, timestamp_lookup[start], timestamp_lookup[end]])
        writer.writerow([])
        writer.writerow(["SUMMARY"])
        writer.writerow([
            "Hypothesis", "Label", "Positive Windows", "Non-Negative Windows",
            "Trades", "Wins", "Losses", "Win Rate %", "Profit Factor",
            "Average R", "Total R", "Max Drawdown R"
        ])
        for srow in summaries:
            pf = srow["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.4f}"
            writer.writerow([
                srow["hypothesis"], srow["label"], srow["positive_windows"],
                srow["non_negative_windows"], srow["trades"], srow["wins"],
                srow["losses"], f"{srow['win_rate']:.2f}", pf_text,
                f"{srow['average_r']:.4f}", f"{srow['total_r']:.2f}",
                f"{srow['max_drawdown_r']:.2f}"
            ])
        writer.writerow([])
        writer.writerow(["TRADE DETAILS"])
        if all_trades:
            keys = [
                "hypothesis", "hypothesis_label", "period", "timestamp", "signal",
                "clearance_atr", "atr", "entry", "stop", "target", "outcome", "r",
                "exit_timestamp", "exit_index", "risk_distance"
            ]
            writer.writerow(keys)
            for trade in all_trades:
                writer.writerow([trade.get(k, "") for k in keys])



def phase12_7_2_trade_inspection():
    """Inspect the exact Phase 12.7 SELL-only + S/R-gap hypothesis trades."""
    print("\n" + "=" * 100)
    print(" PHASE 12.7.2 - 13-TRADE DEEP INSPECTION")
    print("=" * 100)
    print("Exact hypothesis: SELL-only + S/R gap exclusion (0.75 <= clearance < 1.00 ATR excluded)")
    print("Baseline: 7/7 | S/R >= 0.50 ATR | Stop 1.5 ATR | R:R 1:2")
    print("Analysis only: NO strategy rules are changed by this phase.")

    if not check_csv_data():
        return

    records = csv_records
    indicators = build_indicator_series(records)
    windows = build_phase12_5_windows(records, usable_start=PHASE12_7_MIN_INDEX, number_of_windows=PHASE12_7_WINDOWS)
    hypothesis = next(h for h in PHASE12_7_HYPOTHESES if h["id"] == "SELL_SR")

    all_trades = []
    for n, (start, end) in enumerate(windows, 1):
        trades, _ = phase12_7_backtest_period(records, indicators, start, end, hypothesis, n)
        all_trades.extend(trades)

    if not all_trades:
        print("ERROR: No SELL_SR trades were reconstructed.")
        return

    index_by_timestamp = {row["timestamp"]: i for i, row in enumerate(records)}
    enriched = []
    for trade in all_trades:
        idx = index_by_timestamp.get(trade["timestamp"])
        if idx is None:
            continue
        enriched.append({
            **trade,
            "index": idx,
            "rsi": indicators["rsi14"][idx],
            "macd": indicators["macd"][idx],
            "macd_signal": indicators["signal"][idx],
            "histogram": indicators["histogram"][idx],
            "holding_bars": trade["exit_index"] - idx,
            "entry_hour": records[idx]["datetime"].hour,
        })

    print("\nCOMPACT 13-TRADE TABLE")
    print("-" * 100)
    print(f"{'#':>2} {'Win':>3} {'Timestamp':<19} {'Sig':>4} {'Clr':>6} {'RSI':>6} {'ATR':>7} {'Hold':>4} {'Outcome':>7} {'R':>5}")
    print("-" * 100)
    for n, t in enumerate(enriched, 1):
        print(f"{n:>2} {t['period'].replace('WINDOW_','W'):>3} {t['timestamp']:<19} {t['signal']:>4} {t['clearance_atr']:>6.3f} {t['rsi']:>6.2f} {t['atr']:>7.2f} {t['holding_bars']:>4} {t['outcome']:>7} {t['r']:>5.1f}")

    winners = [t for t in enriched if t["outcome"] == "WIN"]
    losers = [t for t in enriched if t["outcome"] == "LOSS"]

    def avg(items, key):
        vals = [t[key] for t in items if t[key] is not None]
        return sum(vals) / len(vals) if vals else 0.0

    print("\nWINNER vs LOSER FEATURE COMPARISON")
    print("-" * 86)
    print(f"{'Feature':<28} {'Winners':>16} {'Losers':>16}")
    print("-" * 86)
    for label, key in [
        ("S/R clearance (ATR)", "clearance_atr"),
        ("RSI14", "rsi"),
        ("ATR14", "atr"),
        ("Holding bars", "holding_bars"),
        ("MACD line", "macd"),
        ("MACD signal", "macd_signal"),
        ("MACD histogram", "histogram"),
    ]:
        print(f"{label:<28} {avg(winners,key):>16.3f} {avg(losers,key):>16.3f}")

    print("\nCOUNTS")
    print(f"Winners: {len(winners)} | Losers: {len(losers)} | Total: {len(enriched)}")
    print(f"Win rate: {len(winners)/len(enriched)*100:.2f}%")
    print(f"Total R: {sum(t['r'] for t in enriched):.2f}")

    def bucket_summary(items, title):
        buckets = [(0.50,0.75),(0.75,1.00),(1.00,1.25),(1.25,1.50),(1.50,float('inf'))]
        print(f"\n{title}")
        print("-" * 64)
        print(f"{'Clearance bucket':<22} {'Trades':>7} {'Wins':>7} {'Losses':>8} {'Total R':>9}")
        for lo, hi in buckets:
            group=[t for t in items if t['clearance_atr'] >= lo and t['clearance_atr'] < hi]
            if group:
                w=sum(t['outcome']=='WIN' for t in group); l=sum(t['outcome']=='LOSS' for t in group)
                label=f"{lo:.2f}-<{hi:.2f} ATR" if hi != float('inf') else f">={lo:.2f} ATR"
                print(f"{label:<22} {len(group):>7} {w:>7} {l:>8} {sum(t['r'] for t in group):>9.2f}")

    bucket_summary(winners, "WINNER CLEARANCE DISTRIBUTION")
    bucket_summary(losers, "LOSER CLEARANCE DISTRIBUTION")

    print("\nENTRY HOUR")
    print("-" * 64)
    hours = sorted(set(t['entry_hour'] for t in enriched))
    for hour in hours:
        group=[t for t in enriched if t['entry_hour']==hour]
        w=sum(t['outcome']=='WIN' for t in group)
        print(f"Hour {hour:02d}:00 | Trades {len(group)} | Wins {w} | Losses {len(group)-w} | Total R {sum(t['r'] for t in group):.2f}")

    print("\nPHASE 12.7.2 INSPECTION COMPLETE")
    print("No strategy rules were changed.")
    print("=" * 100)


def phase12_7_3_component_inspection():
    """Inspect the seven directional components for the exact 13 SELL_SR trades."""
    print("\n" + "=" * 120)
    print(" PHASE 12.7.3 - 7-COMPONENT SETUP INSPECTION")
    print("=" * 120)
    print("Exact hypothesis: SELL-only + S/R gap exclusion")
    print("Purpose: descriptive comparison of the seven confirmation components.")
    print("Analysis only: NO strategy rules are changed.")

    if not check_csv_data():
        return

    records = csv_records
    indicators = build_indicator_series(records)
    windows = build_phase12_5_windows(
        records, usable_start=PHASE12_7_MIN_INDEX, number_of_windows=PHASE12_7_WINDOWS
    )
    hypothesis = next(h for h in PHASE12_7_HYPOTHESES if h["id"] == "SELL_SR")

    all_trades = []
    for n, (start, end) in enumerate(windows, 1):
        trades, _ = phase12_7_backtest_period(records, indicators, start, end, hypothesis, n)
        all_trades.extend(trades)

    if not all_trades:
        print("ERROR: No SELL_SR trades were reconstructed.")
        return

    index_by_timestamp = {row["timestamp"]: i for i, row in enumerate(records)}
    component_rows = []
    for trade in all_trades:
        idx = index_by_timestamp.get(trade["timestamp"])
        if idx is None:
            continue
        score = diagnostic_score_components(records, indicators, idx)
        if score is None:
            continue
        c = score["components"]
        component_rows.append({
            "trade": trade,
            "index": idx,
            "SMA Trend": c["SMA Trend"],
            "EMA Trend": c["EMA Trend"],
            "RSI": c["RSI"],
            "MACD": c["MACD"],
            "MACD Momentum": c["MACD Momentum"],
            "Market Structure": c["Market Structure"],
            "Candle Confirmation": c["Candle Confirmation"],
            "bullish": score["bullish"],
            "bearish": score["bearish"],
        })

    names = [
        "SMA Trend", "EMA Trend", "RSI", "MACD", "MACD Momentum",
        "Market Structure", "Candle Confirmation"
    ]

    def mark(value):
        return "BULL" if value == 1 else "BEAR" if value == -1 else "NEUT"

    print("\n13-TRADE COMPONENT MATRIX")
    print("-" * 160)
    print(f"{'#':>2} {'Timestamp':<19} {'Outcome':>7} " + " ".join(f"{n[:8]:>8}" for n in names) + f" {'Bull':>5} {'Bear':>5}")
    print("-" * 160)
    for n, row in enumerate(component_rows, 1):
        t=row["trade"]
        values=" ".join(f"{mark(row[name]):>8}" for name in names)
        print(f"{n:>2} {t['timestamp']:<19} {t['outcome']:>7} {values} {row['bullish']:>5} {row['bearish']:>5}")

    print("\nNUMERIC COMPONENT MATRIX (+1 bullish / -1 bearish / 0 neutral)")
    print("-" * 160)
    print(f"{'#':>2} {'Timestamp':<19} {'Outcome':>7} " + " ".join(f"{n[:8]:>8}" for n in names))
    print("-" * 160)
    for n, row in enumerate(component_rows, 1):
        t=row["trade"]
        values=" ".join(f"{row[name]:>8}" for name in names)
        print(f"{n:>2} {t['timestamp']:<19} {t['outcome']:>7} {values}")

    winners=[r for r in component_rows if r["trade"]["outcome"]=="WIN"]
    losers=[r for r in component_rows if r["trade"]["outcome"]=="LOSS"]

    print("\nCOMPONENT COUNTS: WINNERS vs LOSERS")
    print("-" * 92)
    print(f"{'Component':<24} {'Winner BEAR':>12} {'Winner BULL':>12} {'Winner NEUT':>12} {'Loser BEAR':>12} {'Loser BULL':>12} {'Loser NEUT':>12}")
    print("-" * 92)
    for name in names:
        wc=sum(r[name]==-1 for r in winners); wbu=sum(r[name]==1 for r in winners); wn=sum(r[name]==0 for r in winners)
        lc=sum(r[name]==-1 for r in losers); lbu=sum(r[name]==1 for r in losers); ln=sum(r[name]==0 for r in losers)
        print(f"{name:<24} {wc:>12} {wbu:>12} {wn:>12} {lc:>12} {lbu:>12} {ln:>12}")

    print("\nCOMPONENT CONSISTENCY (SELL SETUPS)")
    print("-" * 88)
    for name in names:
        w_bear=sum(r[name]==-1 for r in winners)
        l_bear=sum(r[name]==-1 for r in losers)
        print(f"{name:<24} Winners bearish: {w_bear}/{len(winners)} | Losers bearish: {l_bear}/{len(losers)}")

    print("\n7-COMPONENT SCORE CHECK")
    print("-" * 60)
    for n, row in enumerate(component_rows, 1):
        t=row["trade"]
        print(f"{n:>2} {t['timestamp']} | {t['outcome']:>4} | Bullish {row['bullish']} | Bearish {row['bearish']} | Dominant SELL")

    print("\nPHASE 12.7.3 INSPECTION COMPLETE")
    print("No strategy rules were changed.")
    print("=" * 120)

def phase12_7_validation():
    """Run fixed hypothesis tests across five chronological windows."""
    print("\n" + "=" * 96)
    print(" PHASE 12.7 - PREDEFINED HYPOTHESIS & FORWARD-WINDOW TESTING")
    print("=" * 96)
    print("Baseline: 7/7 | S/R >= 0.50 ATR | Stop 1.5 ATR | R:R 1:2")
    print("Hypotheses are fixed; NO per-window optimization is performed.")
    print("IMPORTANT: Because these hypotheses were informed by Phase 12.6, this is NOT a virgin holdout test.")
    print("It is a fixed hypothesis comparison across chronological windows.")

    if not check_csv_data():
        return

    records = csv_records
    indicators = build_indicator_series(records)
    windows = build_phase12_5_windows(
        records,
        usable_start=PHASE12_7_MIN_INDEX,
        number_of_windows=PHASE12_7_WINDOWS
    )

    if not windows:
        print("ERROR: Not enough historical records for five windows.")
        return

    print("\nWindow definitions:")
    for n, (start, end) in enumerate(windows, 1):
        print(
            f"  Window {n}: records {start} to {end} | "
            f"{records[start]['timestamp']} -> {records[end]['timestamp']}"
        )

    all_trades = []
    summaries = []

    for hypothesis in PHASE12_7_HYPOTHESES:
        print("\n" + "=" * 96)
        print(f"HYPOTHESIS: {hypothesis['id']} | {hypothesis['label']}")
        print("=" * 96)

        window_metrics = []
        hypothesis_trades = []

        for n, (start, end) in enumerate(windows, 1):
            trades, metrics = phase12_7_backtest_period(
                records, indicators, start, end, hypothesis, n
            )
            window_metrics.append(metrics)
            hypothesis_trades.extend(trades)
            phase12_7_print_window_result(hypothesis, n, metrics)

        total_trades = sum(m["trades"] for m in window_metrics)
        wins = sum(m["wins"] for m in window_metrics)
        losses = sum(m["losses"] for m in window_metrics)
        total_r = sum(m["total_r"] for m in window_metrics)
        gross_profit = sum(max(m.get("total_r", 0.0), 0.0) + max(-m.get("total_r", 0.0), 0.0) * 0 for m in window_metrics)
        gross_loss = sum(max(-m.get("total_r", 0.0), 0.0) for m in window_metrics)
        # Aggregate gross profit from trade-level R values so gains are not
        # canceled by losses inside an individual window.
        gross_profit = sum(max(trade.get("r", 0.0), 0.0) for trade in hypothesis_trades)
        gross_loss = sum(max(-trade.get("r", 0.0), 0.0) for trade in hypothesis_trades)
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
        average_r = total_r / total_trades if total_trades else 0.0
        win_rate = (wins / total_trades * 100.0) if total_trades else 0.0
        positive_windows = sum(1 for m in window_metrics if m["total_r"] > 0)
        non_negative_windows = sum(1 for m in window_metrics if m["total_r"] >= 0)
        max_dd = 0.0
        for m in window_metrics:
            max_dd = max(max_dd, m["max_drawdown_r"])

        print(
            f"Summary: Positive {positive_windows}/5 | "
            f"Non-negative {non_negative_windows}/5 | Trades {total_trades} | "
            f"Win Rate {win_rate:.2f}% | PF "
            f"{'INF' if math.isinf(pf) else f'{pf:.2f}'} | "
            f"Total R {total_r:.2f} | Max DD {max_dd:.2f}R"
        )

        summaries.append({
            "hypothesis": hypothesis["id"],
            "label": hypothesis["label"],
            "positive_windows": positive_windows,
            "non_negative_windows": non_negative_windows,
            "trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": pf,
            "average_r": average_r,
            "total_r": total_r,
            "max_drawdown_r": max_dd,
        })
        all_trades.extend(hypothesis_trades)

    print("\n" + "=" * 96)
    print("PHASE 12.7 COMPARISON SUMMARY")
    print("=" * 96)
    print("This table is descriptive. It does NOT automatically select a strategy.")
    print("Do not treat the best historical row as proof of future performance.")
    print("\nHypothesis                         Positive  Non-Neg  Trades  Total R  Max DD")
    print("--------------------------------------------------------------------------------")
    for srow in summaries:
        print(
            f"{srow['label']:<35} {srow['positive_windows']:>3}/5     "
            f"{srow['non_negative_windows']:>3}/5   {srow['trades']:>6}  "
            f"{srow['total_r']:>7.2f}  {srow['max_drawdown_r']:>6.2f}R"
        )

    timestamp_lookup = [row["timestamp"] for row in records]
    output_path = os.path.join(
        os.path.expanduser("~"),
        "Downloads",
        "XAUUSD_Phase12_7_Hypothesis_Testing.csv"
    )
    phase12_7_export(all_trades, summaries, windows, output_path, timestamp_lookup)
    print("\n" + "=" * 96)
    print("PHASE 12.7 CSV EXPORTED")
    print(output_path)
    print("Contains fixed-hypothesis window summaries and trade-by-trade results.")
    print("=" * 96)



def phase12_7_4_near_miss_analysis():
    """Analyze bearish 6/7 and 5/7 near-miss setups without changing strategy rules."""
    print("\n" + "=" * 120)
    print(" PHASE 12.7.4 - NEAR-MISS COMPONENT ANALYSIS")
    print("=" * 120)
    print("Purpose: inspect bearish 6/7 and 5/7 setups to see which confirmation components are missing.")
    print("Execution uses the same causal data, 1.5 ATR stop, 1:2 R:R, S/R >= 0.50 ATR,")
    print("and the Phase 12.7 S/R-gap exclusion (0.75 <= clearance < 1.00 ATR excluded).")
    print("Analysis only: NO strategy rules are changed or optimized.")
    print("Important: this is diagnostic evidence from the already-reviewed 2026 dataset, not a virgin holdout.")

    if not check_csv_data():
        return

    records = csv_records
    indicators = build_indicator_series(records)
    windows = build_phase12_5_windows(
        records, usable_start=PHASE12_7_MIN_INDEX, number_of_windows=PHASE12_7_WINDOWS
    )

    names = [
        "SMA Trend", "EMA Trend", "RSI", "MACD",
        "MACD Momentum", "Market Structure", "Candle Confirmation"
    ]

    def sr_eligible(score_data, index):
        atr = score_data["atr"]
        if atr is None or atr <= 0:
            return None
        support, resistance = support_resistance(records, index, 20)
        if support is None:
            return None
        price = records[index]["close"]
        clearance = (price - support) / atr
        if clearance < PHASE12_7_BASE_SR:
            return None
        if 0.75 <= clearance < 1.00:
            return None
        return {
            "support": support,
            "resistance": resistance,
            "clearance_atr": clearance,
            "atr": atr,
        }

    raw_counts = {5: 0, 6: 0}
    sr_counts = {5: 0, 6: 0}
    resolved_counts = {5: 0, 6: 0}
    raw_by_window = {5: [0] * 5, 6: [0] * 5}
    sr_by_window = {5: [0] * 5, 6: [0] * 5}
    all_trades = []

    # Run one unified causal near-miss stream per window so the same one-position-at-a-time
    # rule is respected. A 6/7 setup is inspected before a 5/7 setup at the same candle.
    for window_number, (start, end) in enumerate(windows, 1):
        next_available_index = start
        for index in range(max(PHASE12_7_MIN_INDEX, start), end + 1):
            if index < next_available_index:
                continue

            score = diagnostic_score_components(records, indicators, index)
            if score is None or score["dominant_direction"] != "BEARISH":
                continue

            score_level = score["max_score"]
            if score_level not in (5, 6):
                continue

            raw_counts[score_level] += 1
            raw_by_window[score_level][window_number - 1] += 1

            sr = sr_eligible(score, index)
            if sr is None:
                continue

            sr_counts[score_level] += 1
            sr_by_window[score_level][window_number - 1] += 1

            entry = records[index]["close"]
            risk_distance = score["atr"] * PHASE12_7_STOP_ATR
            result = resolve_trade_r_until(
                records, index, "SELL", entry, risk_distance, PHASE12_7_RR, end
            )
            if not result["resolved"]:
                continue

            resolved_counts[score_level] += 1
            stop = entry + risk_distance
            target = entry - risk_distance * PHASE12_7_RR
            missing = [name for name in names if score["components"][name] != -1]
            missing_labels = " + ".join(missing) if missing else "NONE"

            all_trades.append({
                "period": f"WINDOW_{window_number}",
                "score_level": score_level,
                "timestamp": records[index]["timestamp"],
                "signal": "SELL",
                "entry": entry,
                "stop": stop,
                "target": target,
                "atr": score["atr"],
                "clearance_atr": sr["clearance_atr"],
                "bullish_score": score["bullish"],
                "bearish_score": score["bearish"],
                "missing_components": missing_labels,
                "outcome": result["outcome"],
                "r": result["r"],
                "exit_timestamp": records[result["exit_index"]]["timestamp"],
                "exit_index": result["exit_index"],
            })
            next_available_index = result["exit_index"] + 1

    print("\nRAW BEARISH NEAR-MISS CANDIDATES")
    print("-" * 80)
    print(f"6/7 bearish candidates: {raw_counts[6]}")
    print(f"5/7 bearish candidates: {raw_counts[5]}")

    print("\nCANDIDATES AFTER SAME S/R FILTERS")
    print("-" * 80)
    print(f"6/7 after S/R filter: {sr_counts[6]}")
    print(f"5/7 after S/R filter: {sr_counts[5]}")

    print("\nRESOLVED NEAR-MISS TRADES")
    print("-" * 80)
    print(f"6/7 resolved trades: {resolved_counts[6]}")
    print(f"5/7 resolved trades: {resolved_counts[5]}")

    print("\nRAW CANDIDATES BY CHRONOLOGICAL WINDOW")
    print("-" * 80)
    print("Score   W1   W2   W3   W4   W5   Total")
    print("-----------------------------------------")
    for level in (6, 5):
        print(f"{level}/7    " + "   ".join(f"{x:>2}" for x in raw_by_window[level]) + f"   {sum(raw_by_window[level]):>3}")

    print("\nS/R-ELIGIBLE CANDIDATES BY CHRONOLOGICAL WINDOW")
    print("-" * 80)
    print("Score   W1   W2   W3   W4   W5   Total")
    print("-----------------------------------------")
    for level in (6, 5):
        print(f"{level}/7    " + "   ".join(f"{x:>2}" for x in sr_by_window[level]) + f"   {sum(sr_by_window[level]):>3}")

    for level in (6, 5):
        trades = [t for t in all_trades if t["score_level"] == level]
        wins = sum(t["outcome"] == "WIN" for t in trades)
        losses = sum(t["outcome"] == "LOSS" for t in trades)
        total_r = sum(t["r"] for t in trades)
        win_rate = (wins / len(trades) * 100) if trades else 0.0
        print(f"\n{level}/7 OUTCOME SUMMARY")
        print("-" * 80)
        print(f"Trades: {len(trades)} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.2f}% | Total R: {total_r:.2f}")

    six = [t for t in all_trades if t["score_level"] == 6]
    print("\n6/7 MISSING-COMPONENT ANALYSIS")
    print("-" * 120)
    print(f"{'Missing component':<28} {'Trades':>7} {'Wins':>6} {'Losses':>8} {'Win Rate':>10} {'Total R':>9}")
    print("-" * 120)
    for name in names:
        group = [t for t in six if t["missing_components"] == name]
        wins = sum(t["outcome"] == "WIN" for t in group)
        losses = sum(t["outcome"] == "LOSS" for t in group)
        total_r = sum(t["r"] for t in group)
        wr = wins / len(group) * 100 if group else 0.0
        print(f"{name:<28} {len(group):>7} {wins:>6} {losses:>8} {wr:>9.2f}% {total_r:>9.2f}")

    pairs = {}
    five = [t for t in all_trades if t["score_level"] == 5]
    for t in five:
        key = t["missing_components"]
        pairs.setdefault(key, []).append(t)

    print("\n5/7 MISSING-COMPONENT PAIR ANALYSIS")
    print("-" * 140)
    print(f"{'Missing component pair':<55} {'Trades':>7} {'Wins':>6} {'Losses':>8} {'Win Rate':>10} {'Total R':>9}")
    print("-" * 140)
    for key, group in sorted(pairs.items(), key=lambda item: (-len(item[1]), item[0])):
        wins = sum(t["outcome"] == "WIN" for t in group)
        losses = sum(t["outcome"] == "LOSS" for t in group)
        total_r = sum(t["r"] for t in group)
        wr = wins / len(group) * 100 if group else 0.0
        print(f"{key:<55} {len(group):>7} {wins:>6} {losses:>8} {wr:>9.2f}% {total_r:>9.2f}")

    print("\nRESOLVED NEAR-MISS TRADE DETAILS")
    print("-" * 150)
    print(f"{'#':>2} {'Timestamp':<19} {'Score':>5} {'Outcome':>7} {'Clear':>7} {'ATR':>7} {'Missing components':<55} {'R':>5}")
    print("-" * 150)
    for number, trade in enumerate(all_trades, 1):
        print(
            f"{number:>2} {trade['timestamp']:<19} {trade['score_level']:>5}/7 "
            f"{trade['outcome']:>7} {trade['clearance_atr']:>7.3f} {trade['atr']:>7.2f} "
            f"{trade['missing_components']:<55} {trade['r']:>5.1f}"
        )

    output_path = os.path.join(
        os.path.expanduser("~"),
        "Downloads",
        "XAUUSD_Phase12_7_4_Near_Miss_Component_Analysis.csv"
    )
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["PHASE 12.7.4 - NEAR-MISS COMPONENT ANALYSIS"])
        writer.writerow(["Scope", "Bearish 6/7 and 5/7 near-miss setups"])
        writer.writerow(["Filters", "S/R >= 0.50 ATR; exclude 0.75-<1.00 ATR; stop 1.5 ATR; R:R 1:2"])
        writer.writerow(["Important", "Diagnostic analysis on existing 2026 dataset; not a virgin future holdout."])
        writer.writerow([])
        writer.writerow(["SCORE", "RAW CANDIDATES", "S/R ELIGIBLE", "RESOLVED TRADES"])
        for level in (6, 5):
            writer.writerow([level, raw_counts[level], sr_counts[level], resolved_counts[level]])
        writer.writerow([])
        writer.writerow(["TRADE DETAILS"])
        writer.writerow([
            "period", "score_level", "timestamp", "signal", "entry", "stop",
            "target", "atr", "clearance_atr", "bullish_score", "bearish_score",
            "missing_components", "outcome", "r", "exit_timestamp", "exit_index"
        ])
        for trade in all_trades:
            writer.writerow([
                trade["period"], trade["score_level"], trade["timestamp"], trade["signal"],
                trade["entry"], trade["stop"], trade["target"], trade["atr"],
                trade["clearance_atr"], trade["bullish_score"], trade["bearish_score"],
                trade["missing_components"], trade["outcome"], trade["r"],
                trade["exit_timestamp"], trade["exit_index"]
            ])

    print("\n" + "=" * 120)
    print("PHASE 12.7.4 ANALYSIS COMPLETE")
    print("No strategy rules were changed.")
    print(f"CSV exported: {output_path}")
    print("=" * 120)


# ============================================================
# PHASE 12.7.5 - SELL SCORE THRESHOLD BACKTEST
# ============================================================

PHASE12_7_5_THRESHOLDS = [7, 6, 5]

def phase12_7_5_candidate(records, indicators, index, min_bearish_score):
    """Test a simple SELL bearish-score threshold with the frozen S/R/exit rules."""
    score_data = diagnostic_score_components(records, indicators, index)
    if score_data is None:
        return None

    # SELL-only: require the bearish side to meet the threshold and dominate.
    if score_data["bearish"] < min_bearish_score:
        return None
    if score_data["bearish"] <= score_data["bullish"]:
        return None

    atr = score_data["atr"]
    if atr is None or atr <= 0:
        return None

    support, resistance = support_resistance(records, index, 20)
    price = records[index]["close"]
    if support is None:
        return None

    clearance = (price - support) / atr

    # Same frozen S/R rules used by the Phase 12.7 SELL_SR hypothesis.
    if clearance < PHASE12_7_BASE_SR:
        return None
    if 0.75 <= clearance < 1.00:
        return None

    return {
        "signal": "SELL",
        "entry": price,
        "risk_distance": atr * PHASE12_7_STOP_ATR,
        "atr": atr,
        "bullish_score": score_data["bullish"],
        "bearish_score": score_data["bearish"],
        "structure": score_data["structure"],
        "candle": score_data["candle"],
        "support": support,
        "resistance": resistance,
        "clearance_atr": clearance,
    }


def phase12_7_5_backtest_period(records, indicators, start_index, end_index, threshold, window_number):
    trades = []
    next_available_index = start_index

    for index in range(max(PHASE12_7_MIN_INDEX, start_index), end_index + 1):
        if index < next_available_index:
            continue

        candidate = phase12_7_5_candidate(records, indicators, index, threshold)
        if candidate is None:
            continue

        result = resolve_trade_r_until(
            records, index, candidate["signal"], candidate["entry"],
            candidate["risk_distance"], PHASE12_7_RR, end_index
        )

        if not result["resolved"]:
            continue

        stop = candidate["entry"] + candidate["risk_distance"]
        target = candidate["entry"] - candidate["risk_distance"] * PHASE12_7_RR

        trades.append({
            "period": f"WINDOW_{window_number}",
            "threshold": threshold,
            "timestamp": records[index]["timestamp"],
            "signal": "SELL",
            "entry": candidate["entry"],
            "stop": stop,
            "target": target,
            "risk_distance": candidate["risk_distance"],
            "atr": candidate["atr"],
            "bullish_score": candidate["bullish_score"],
            "bearish_score": candidate["bearish_score"],
            "structure": candidate["structure"],
            "candle": candidate["candle"],
            "support": candidate["support"],
            "resistance": candidate["resistance"],
            "clearance_atr": candidate["clearance_atr"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"],
        })

        next_available_index = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, PHASE12_7_RR)
    metrics["threshold"] = threshold
    metrics["window"] = window_number
    return trades, metrics


def phase12_7_5_threshold_backtest():
    print("\n" + "=" * 120)
    print(" PHASE 12.7.5 - SELL SCORE THRESHOLD BACKTEST")
    print("=" * 120)
    print("Purpose: compare fixed SELL bearish-score thresholds of 7/7, 6/7, and 5/7.")
    print("Frozen rules: SELL-only | S/R >= 0.50 ATR | exclude 0.75-<1.00 ATR | stop 1.5 ATR | R:R 1:2")
    print("Five chronological windows | one open position at a time | no per-window optimization")
    print("Important: diagnostic/hypothesis evidence from the already-reviewed 2026 dataset, not a virgin holdout.")

    if not check_csv_data():
        return

    records = csv_records
    indicators = build_indicator_series(records)
    windows = build_phase12_5_windows(
        records, usable_start=PHASE12_7_MIN_INDEX, number_of_windows=PHASE12_7_WINDOWS
    )

    all_trades = []
    summaries = []

    for threshold in PHASE12_7_5_THRESHOLDS:
        threshold_trades = []
        print("\n" + "-" * 120)
        print(f"SELL THRESHOLD: {threshold}/7")
        print("-" * 120)

        positive_windows = 0
        non_negative_windows = 0

        for n, (start, end) in enumerate(windows, 1):
            trades, metrics = phase12_7_5_backtest_period(
                records, indicators, start, end, threshold, n
            )
            threshold_trades.extend(trades)
            if metrics["total_r"] > 0:
                positive_windows += 1
            if metrics["total_r"] >= 0:
                non_negative_windows += 1

            pf = metrics["profit_factor"]
            pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
            print(
                f"Window {n}: Trades {metrics['trades']}, "
                f"Win Rate {metrics['win_rate']:.2f}%, PF {pf_text}, "
                f"Avg R {metrics['average_r']:.4f}, Total R {metrics['total_r']:.2f}, "
                f"Max DD {metrics['max_drawdown_r']:.2f}R"
            )

        aggregate = calculate_backtest_metrics(threshold_trades, PHASE12_7_RR)
        summaries.append({
            "threshold": threshold,
            "positive_windows": positive_windows,
            "non_negative_windows": non_negative_windows,
            **aggregate,
        })
        all_trades.extend(threshold_trades)

    print("\n" + "=" * 120)
    print("THRESHOLD COMPARISON")
    print("=" * 120)
    print("Threshold | Pos W | Non-Neg W | Trades | Wins | Losses | Win Rate | PF   | Avg R   | Total R | Max DD")
    print("-" * 120)
    for s in summaries:
        pf = s["profit_factor"]
        pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
        print(
            f"{s['threshold']}/7       | {s['positive_windows']:>5} | "
            f"{s['non_negative_windows']:>10} | {s['trades']:>6} | "
            f"{s['wins']:>4} | {s['losses']:>6} | {s['win_rate']:>8.2f}% | "
            f"{pf_text:>4} | {s['average_r']:>7.4f} | {s['total_r']:>7.2f} | {s['max_drawdown_r']:>6.2f}R"
        )

    output_path = os.path.join(
        os.path.expanduser("~"), "Downloads",
        "XAUUSD_Phase12_7_5_Score_Threshold_Backtest.csv"
    )
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["PHASE 12.7.5 - SELL SCORE THRESHOLD BACKTEST"])
        writer.writerow(["Frozen rules", "SELL-only | S/R >= 0.50 ATR | exclude 0.75-<1.00 ATR | Stop 1.5 ATR | R:R 1:2"])
        writer.writerow(["Thresholds tested", "7/7, 6/7, 5/7"])
        writer.writerow(["Important", "Existing 2026 dataset; not a virgin holdout. No per-window optimization."])
        writer.writerow([])
        writer.writerow(["SUMMARY"])
        writer.writerow(["Threshold", "Positive Windows", "Non-Negative Windows", "Trades", "Wins", "Losses", "Win Rate %", "Profit Factor", "Average R", "Total R", "Max Drawdown R"])
        for s in summaries:
            pf = s["profit_factor"]
            writer.writerow([
                f"{s['threshold']}/7", s["positive_windows"], s["non_negative_windows"],
                s["trades"], s["wins"], s["losses"], f"{s['win_rate']:.2f}",
                "INF" if math.isinf(pf) else f"{pf:.4f}", f"{s['average_r']:.4f}",
                f"{s['total_r']:.2f}", f"{s['max_drawdown_r']:.2f}"
            ])
        writer.writerow([])
        writer.writerow(["TRADE DETAILS"])
        writer.writerow(["threshold", "period", "timestamp", "clearance_atr", "bearish_score", "bullish_score", "atr", "outcome", "r", "exit_timestamp", "exit_index"])
        for t in all_trades:
            writer.writerow([
                f"{t['threshold']}/7", t["period"], t["timestamp"], t["clearance_atr"],
                t["bearish_score"], t["bullish_score"], t["atr"], t["outcome"], t["r"],
                t["exit_timestamp"], t["exit_index"]
            ])

    print("\n" + "=" * 120)
    print("PHASE 12.7.5 ANALYSIS COMPLETE")
    print("No existing strategy rule was modified; this is a threshold comparison experiment.")
    print(f"CSV exported: {output_path}")
    print("=" * 120)



# ============================================================
# PHASE 13 - FROZEN OUT-OF-SAMPLE / FORWARD VALIDATION
# ============================================================

# These rules are frozen from the Phase 12.7 research cycle.
# Primary setup: 7/7 bearish SELL.
# Secondary setup: 6/7 bearish SELL.
# No threshold, S/R, stop, or R:R optimization is performed here.

PHASE13_PRIMARY_THRESHOLD = 7
PHASE13_SECONDARY_THRESHOLD = 6
PHASE13_SR_MIN = 0.50
PHASE13_SR_EXCLUDED_LOW = 0.75
PHASE13_SR_EXCLUDED_HIGH = 1.00
PHASE13_STOP_ATR = 1.5
PHASE13_RR = 2.0

# The development dataset used through Phase 12.7 ended here.
# Phase 13 evaluates only records AFTER this timestamp, while retaining
# earlier records in memory as indicator look-back context.
PHASE13_DEVELOPMENT_CUTOFF = datetime(2026, 9, 23, 21, 0, 0)


def phase13_load_csv(file_name):
    """Load an MT5 tab-delimited CSV for Phase 13 without changing the old global import."""
    try:
        with open(file_name, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, delimiter="\t")

            if reader.fieldnames is None:
                print("\nERROR: The CSV file has no header row.")
                return None

            column_map = {
                "<DATE>": "Date",
                "<TIME>": "Time",
                "<OPEN>": "Open",
                "<HIGH>": "High",
                "<LOW>": "Low",
                "<CLOSE>": "Close",
                "<TICKVOL>": "TickVol",
                "<VOL>": "Vol",
                "<SPREAD>": "Spread"
            }

            reader.fieldnames = [
                column_map.get(column.strip(), column.strip())
                for column in reader.fieldnames
            ]
            rows = list(reader)

        required = ["Date", "Time", "Open", "High", "Low", "Close"]
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            print("\nERROR: Missing required columns:")
            for column in missing:
                print(f"- {column}")
            return None

        records = []
        skipped = 0

        for row in rows:
            try:
                date_text = row["Date"].strip()
                time_text = row["Time"].strip()
                timestamp = f"{date_text} {time_text}"
                parsed = None
                for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        parsed = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        pass
                if parsed is None:
                    raise ValueError("Invalid date/time")

                records.append({
                    "date": date_text,
                    "time": time_text,
                    "timestamp": timestamp,
                    "datetime": parsed,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "tickvol": float(row.get("TickVol", 0) or 0),
                    "vol": float(row.get("Vol", 0) or 0),
                    "spread": float(row.get("Spread", 0) or 0),
                })
            except (ValueError, TypeError, KeyError):
                skipped += 1

        records.sort(key=lambda r: r["datetime"])

        # Duplicate timestamps would invalidate chronological evaluation.
        duplicate_count = 0
        seen = set()
        for row in records:
            if row["datetime"] in seen:
                duplicate_count += 1
            else:
                seen.add(row["datetime"])

        if duplicate_count:
            print(f"\nERROR: {duplicate_count} duplicate timestamps detected.")
            print("Export a clean MT5 H1 CSV before running Phase 13.")
            return None

        if not records:
            print("\nERROR: No valid OHLC records were found.")
            return None

        return records, len(rows), skipped

    except FileNotFoundError:
        print("\nERROR: CSV file was not found.")
        return None
    except PermissionError:
        print("\nERROR: Permission denied when opening the CSV file.")
        return None
    except Exception as error:
        print(f"\nERROR: {error}")
        return None


def phase13_candidate(records, indicators, index, threshold):
    """Apply the frozen Phase 13 SELL rules with no optimization."""
    score = diagnostic_score_components(records, indicators, index)
    if score is None:
        return None

    if score["bearish"] < threshold:
        return None
    if score["bearish"] <= score["bullish"]:
        return None

    atr = score["atr"]
    if atr is None or atr <= 0:
        return None

    support, resistance = support_resistance(records, index, 20)
    if support is None:
        return None

    price = records[index]["close"]
    clearance = (price - support) / atr

    if clearance < PHASE13_SR_MIN:
        return None
    if PHASE13_SR_EXCLUDED_LOW <= clearance < PHASE13_SR_EXCLUDED_HIGH:
        return None

    return {
        "signal": "SELL",
        "entry": price,
        "risk_distance": atr * PHASE13_STOP_ATR,
        "atr": atr,
        "bullish_score": score["bullish"],
        "bearish_score": score["bearish"],
        "structure": score["structure"],
        "candle": score["candle"],
        "support": support,
        "resistance": resistance,
        "clearance_atr": clearance,
    }


def phase13_run_threshold(records, indicators, start_index, threshold):
    """Run one frozen threshold across the unseen period only."""
    trades = []
    next_available = start_index
    unresolved_candidates = 0
    candidate_count = 0

    for index in range(start_index, len(records)):
        if index < next_available:
            continue

        candidate = phase13_candidate(records, indicators, index, threshold)
        if candidate is None:
            continue

        candidate_count += 1
        result = resolve_trade_r_until(
            records,
            index,
            "SELL",
            candidate["entry"],
            candidate["risk_distance"],
            PHASE13_RR,
            len(records) - 1
        )

        if not result["resolved"]:
            unresolved_candidates += 1
            continue

        risk = candidate["risk_distance"]
        trades.append({
            "threshold": threshold,
            "timestamp": records[index]["timestamp"],
            "datetime": records[index]["datetime"],
            "signal": "SELL",
            "entry": candidate["entry"],
            "stop": candidate["entry"] + risk,
            "target": candidate["entry"] - risk * PHASE13_RR,
            "risk_distance": risk,
            "atr": candidate["atr"],
            "bearish_score": candidate["bearish_score"],
            "bullish_score": candidate["bullish_score"],
            "clearance_atr": candidate["clearance_atr"],
            "support": candidate["support"],
            "resistance": candidate["resistance"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"],
        })

        next_available = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, PHASE13_RR)
    return trades, metrics, candidate_count, unresolved_candidates


def phase13_forward_validation():
    print("\n" + "=" * 120)
    print(" PHASE 13 - FROZEN OUT-OF-SAMPLE / FORWARD VALIDATION")
    print("=" * 120)
    print("PRIMARY: 7/7 bearish SELL | SECONDARY: 6/7 bearish SELL")
    print("Frozen rules: SELL-only | S/R >= 0.50 ATR | exclude 0.75-<1.00 ATR | stop 1.5 ATR | R:R 1:2")
    print("No threshold changes | no S/R optimization | no per-window optimization")
    print(f"Development cutoff: {PHASE13_DEVELOPMENT_CUTOFF.strftime('%Y-%m-%d %H:%M:%S')}")
    print("IMPORTANT: Only data after the cutoff is evaluated. Earlier records are used only as indicator look-back context.")

    print("\nEnter the path to your NEW MT5 XAUUSD H1 CSV.")
    print("If you exported an updated XAUUSD_H1_2026.csv, you can press Enter to auto-find it under C:\\Users.")
    file_name = input("CSV path (or Enter for auto-find): ").strip().strip('"')

    if not file_name:
        matches = glob.glob(r"C:\Users\**\XAUUSD_H1_2026.csv", recursive=True)
        if not matches:
            print("\nERROR: Could not auto-find XAUUSD_H1_2026.csv.")
            print("Export a new MT5 CSV and try again.")
            return
        # Prefer the newest modified copy if several exist.
        file_name = max(matches, key=lambda path: os.path.getmtime(path))

    print(f"\nLoading: {file_name}")
    loaded = phase13_load_csv(file_name)
    if loaded is None:
        return

    records, row_count, skipped = loaded
    first_dt = records[0]["datetime"]
    last_dt = records[-1]["datetime"]

    print("\nCSV LOAD SUCCESSFUL")
    print("------------------------------------------")
    print(f"Rows in file: {row_count}")
    print(f"Valid OHLC records: {len(records)}")
    print(f"Skipped invalid rows: {skipped}")
    print(f"First timestamp: {records[0]['timestamp']}")
    print(f"Last timestamp:  {records[-1]['timestamp']}")

    if last_dt <= PHASE13_DEVELOPMENT_CUTOFF:
        print("\nERROR: No data after the Phase 12.7 development cutoff was found.")
        print(f"Your file ends at {records[-1]['timestamp']}.")
        print("Export newer MT5 data after the cutoff before running Phase 13.")
        return

    forward_start = None
    for i, row in enumerate(records):
        if row["datetime"] > PHASE13_DEVELOPMENT_CUTOFF:
            forward_start = i
            break

    if forward_start is None:
        print("\nERROR: No forward-validation records found.")
        return

    forward_count = len(records) - forward_start
    print("\nFORWARD VALIDATION RANGE")
    print("------------------------------------------")
    print(f"Start: {records[forward_start]['timestamp']}")
    print(f"End:   {records[-1]['timestamp']}")
    print(f"New records evaluated: {forward_count}")
    print("Earlier records retained for indicator warm-up only.")

    indicators = build_indicator_series(records)

    results = []
    all_trades = []
    for threshold, label in [
        (PHASE13_PRIMARY_THRESHOLD, "PRIMARY 7/7"),
        (PHASE13_SECONDARY_THRESHOLD, "SECONDARY 6/7"),
    ]:
        print("\n" + "-" * 120)
        print(f"{label}")
        print("-" * 120)

        trades, metrics, candidates, unresolved = phase13_run_threshold(
            records, indicators, forward_start, threshold
        )
        all_trades.extend(trades)

        pf = metrics["profit_factor"]
        pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
        print(f"Candidates passing frozen filters: {candidates}")
        print(f"Resolved trades: {metrics['trades']}")
        print(f"Unresolved candidates at data end: {unresolved}")
        print(f"Wins: {metrics['wins']}")
        print(f"Losses: {metrics['losses']}")
        print(f"Win Rate: {metrics['win_rate']:.2f}%")
        print(f"Profit Factor: {pf_text}")
        print(f"Average R: {metrics['average_r']:.4f}")
        print(f"Total R: {metrics['total_r']:.2f}")
        print(f"Max Drawdown: {metrics['max_drawdown_r']:.2f}R")

        results.append({
            "threshold": threshold,
            "label": label,
            "candidates": candidates,
            "unresolved": unresolved,
            **metrics,
        })

    print("\n" + "=" * 120)
    print("PHASE 13 FROZEN VALIDATION SUMMARY")
    print("=" * 120)
    print("Setup          Candidates  Resolved  Wins  Losses  Win Rate   PF    Avg R   Total R   Max DD")
    print("-" * 120)
    for r in results:
        pf = r["profit_factor"]
        pf_text = "INF" if math.isinf(pf) else f"{pf:.2f}"
        print(
            f"{r['label']:<14} {r['candidates']:>10} {r['trades']:>9} "
            f"{r['wins']:>5} {r['losses']:>7} {r['win_rate']:>8.2f}% "
            f"{pf_text:>6} {r['average_r']:>8.4f} {r['total_r']:>9.2f} {r['max_drawdown_r']:>8.2f}R"
        )

    output_path = os.path.join(
        os.path.expanduser("~"), "Downloads",
        "XAUUSD_Phase13_Frozen_Forward_Validation.csv"
    )
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["PHASE 13 - FROZEN OUT-OF-SAMPLE / FORWARD VALIDATION"])
        writer.writerow(["Development cutoff", PHASE13_DEVELOPMENT_CUTOFF.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["Primary setup", "7/7 bearish SELL"])
        writer.writerow(["Secondary setup", "6/7 bearish SELL"])
        writer.writerow(["Frozen rules", "SELL-only | S/R >= 0.50 ATR | exclude 0.75-<1.00 ATR | Stop 1.5 ATR | R:R 1:2"])
        writer.writerow(["Important", "Only records after cutoff were evaluated; earlier records were look-back context."])
        writer.writerow([])
        writer.writerow(["SUMMARY"])
        writer.writerow(["Setup", "Candidates", "Unresolved", "Resolved", "Wins", "Losses", "Win Rate %", "Profit Factor", "Average R", "Total R", "Max Drawdown R"])
        for r in results:
            pf = r["profit_factor"]
            writer.writerow([
                r["label"], r["candidates"], r["unresolved"], r["trades"],
                r["wins"], r["losses"], f"{r['win_rate']:.2f}",
                "INF" if math.isinf(pf) else f"{pf:.4f}",
                f"{r['average_r']:.4f}", f"{r['total_r']:.2f}",
                f"{r['max_drawdown_r']:.2f}"
            ])
        writer.writerow([])
        writer.writerow(["TRADE DETAILS"])
        writer.writerow([
            "setup", "threshold", "timestamp", "entry", "stop", "target",
            "atr", "clearance_atr", "bearish_score", "bullish_score",
            "outcome", "r", "exit_timestamp", "exit_index"
        ])
        for t in all_trades:
            writer.writerow([
                "PRIMARY 7/7" if t["threshold"] == 7 else "SECONDARY 6/7",
                f"{t['threshold']}/7", t["timestamp"], t["entry"], t["stop"],
                t["target"], t["atr"], t["clearance_atr"],
                t["bearish_score"], t["bullish_score"], t["outcome"],
                t["r"], t["exit_timestamp"], t["exit_index"]
            ])

    print("\n" + "=" * 120)
    print("PHASE 13 COMPLETE")
    print("No strategy rules were changed or optimized.")
    print(f"CSV exported: {output_path}")
    print("=" * 120)


def phase13_combined_execution_audit():
    """Audit Phase 13 with one shared position across both frozen score tiers.

    This is a separate execution audit. It does not alter any frozen entry,
    stop, target, S/R, or indicator rules. When both tiers qualify on the same
    candle, the 7/7 primary tier receives precedence; otherwise a qualifying
    6/7 signal may be taken. Only one trade can be active at a time.
    """
    print("\n" + "=" * 112)
    print(" PHASE 13 - COMBINED EXECUTION AUDIT (SEPARATE COPY / FROZEN RULES)")
    print("=" * 112)
    print("Global one-position-at-a-time rule across 7/7 and 6/7 tiers.")
    print("Tie-break: 7/7 primary takes precedence over 6/7 secondary.")
    print("All entry filters, stop distance, target R:R, and cutoff remain frozen.")
    print(f"Development cutoff: {PHASE13_DEVELOPMENT_CUTOFF:%Y-%m-%d %H:%M:%S}")

    file_name = input("Enter the full path to your MT5 XAUUSD H1 CSV: ").strip().strip('"')
    if not file_name:
        print("No file path entered. Audit cancelled.")
        return

    loaded = phase13_load_csv(file_name)
    if loaded is None:
        return
    records, row_count, skipped = loaded
    print(f"\nCSV rows: {row_count} | Valid OHLC: {len(records)} | Skipped: {skipped}")
    print(f"First candle: {records[0]['timestamp']} | Last candle: {records[-1]['timestamp']}")

    if records[-1]["datetime"] <= PHASE13_DEVELOPMENT_CUTOFF:
        print("ERROR: This CSV has no candles after the frozen development cutoff.")
        return

    start_index = next((i for i, row in enumerate(records)
                        if row["datetime"] > PHASE13_DEVELOPMENT_CUTOFF), None)
    if start_index is None:
        print("ERROR: No forward-validation candles found.")
        return

    indicators = build_indicator_series(records)
    trades = []
    next_available = start_index
    candidate_count = 0
    unresolved_count = 0
    skipped_while_open = 0

    for index in range(start_index, len(records)):
        if index < next_available:
            skipped_while_open += 1
            continue

        # Disjoint attribution: test 7/7 first, then 6/7 only if 7/7 fails.
        candidate = phase13_candidate(records, indicators, index, PHASE13_PRIMARY_THRESHOLD)
        chosen_threshold = PHASE13_PRIMARY_THRESHOLD if candidate is not None else None
        if candidate is None:
            candidate = phase13_candidate(records, indicators, index, PHASE13_SECONDARY_THRESHOLD)
            if candidate is not None:
                chosen_threshold = PHASE13_SECONDARY_THRESHOLD

        if candidate is None:
            continue

        candidate_count += 1
        result = resolve_trade_r_until(
            records, index, "SELL", candidate["entry"],
            candidate["risk_distance"], PHASE13_RR, len(records) - 1
        )
        if not result["resolved"]:
            unresolved_count += 1
            # The remaining data cannot resolve this candidate; no later trade
            # can be safely simulated after this point in this forward sample.
            break

        risk = candidate["risk_distance"]
        trades.append({
            "setup": "PRIMARY 7/7" if chosen_threshold == 7 else "SECONDARY 6/7",
            "threshold": chosen_threshold,
            "timestamp": records[index]["timestamp"],
            "datetime": records[index]["datetime"],
            "entry": candidate["entry"],
            "stop": candidate["entry"] + risk,
            "target": candidate["entry"] - risk * PHASE13_RR,
            "atr": candidate["atr"],
            "clearance_atr": candidate["clearance_atr"],
            "bearish_score": candidate["bearish_score"],
            "bullish_score": candidate["bullish_score"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_timestamp": records[result["exit_index"]]["timestamp"],
            "exit_index": result["exit_index"],
        })
        next_available = result["exit_index"] + 1

    metrics = calculate_backtest_metrics(trades, PHASE13_RR)
    print("\n" + "-" * 112)
    print("COMBINED PORTFOLIO RESULTS — GLOBAL POSITION LIMIT")
    print("-" * 112)
    print(f"Forward candles: {len(records) - start_index}")
    print(f"Candidate signals accepted for execution: {candidate_count}")
    print(f"Candles skipped while a trade was active: {skipped_while_open}")
    print(f"Unresolved final candidates: {unresolved_count}")
    print(f"Completed trades: {metrics['trades']} | Wins: {metrics['wins']} | Losses: {metrics['losses']}")
    print(f"Win rate: {metrics['win_rate']:.2f}%")
    pf = metrics['profit_factor']
    print(f"Profit factor: {'INF' if math.isinf(pf) else f'{pf:.2f}'}")
    print(f"Average R: {metrics['average_r']:.4f} | Total R: {metrics['total_r']:.2f} | Max drawdown: {metrics['max_drawdown_r']:.2f}R")
    print("\nTRADE DETAILS")
    print("# | Setup          | Entry               | Exit                | Score | Clearance | Result | R")
    print("-" * 100)
    for n, t in enumerate(trades, 1):
        print(f"{n:>2} | {t['setup']:<14} | {t['timestamp']:<19} | {t['exit_timestamp']:<19} | "
              f"{t['bearish_score']}/7   | {t['clearance_atr']:>9.3f} | {t['outcome']:<6} | {t['r']:>+.1f}")

    output_path = os.path.join(
        os.path.expanduser("~"), "Downloads",
        "XAUUSD_Phase13_Combined_Execution_Audit.csv"
    )
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["PHASE 13 - COMBINED EXECUTION AUDIT"])
            w.writerow(["Mode", "One shared position across both tiers; 7/7 precedence"])
            w.writerow(["Development cutoff", PHASE13_DEVELOPMENT_CUTOFF.strftime("%Y-%m-%d %H:%M:%S")])
            w.writerow(["Frozen rules", "SELL-only | S/R >= 0.50 ATR | exclude 0.75-<1.00 ATR | stop 1.5 ATR | target 2R"])
            w.writerow(["CSV source", file_name])
            w.writerow([])
            w.writerow(["Metric", "Value"])
            w.writerow(["Forward candles", len(records) - start_index])
            w.writerow(["Executed candidates", candidate_count])
            w.writerow(["Candles skipped while active", skipped_while_open])
            w.writerow(["Unresolved final candidates", unresolved_count])
            w.writerow(["Completed trades", metrics["trades"]])
            w.writerow(["Wins", metrics["wins"]])
            w.writerow(["Losses", metrics["losses"]])
            w.writerow(["Win rate %", f"{metrics['win_rate']:.2f}"])
            w.writerow(["Profit factor", "INF" if math.isinf(pf) else f"{pf:.4f}"])
            w.writerow(["Average R", f"{metrics['average_r']:.4f}"])
            w.writerow(["Total R", f"{metrics['total_r']:.2f}"])
            w.writerow(["Max drawdown R", f"{metrics['max_drawdown_r']:.2f}"])
            w.writerow([])
            w.writerow(["setup", "threshold", "entry_timestamp", "exit_timestamp", "entry", "stop", "target", "atr", "clearance_atr", "bearish_score", "bullish_score", "outcome", "r", "exit_index"])
            for t in trades:
                w.writerow([t["setup"], f"{t['threshold']}/7", t["timestamp"], t["exit_timestamp"],
                            t["entry"], t["stop"], t["target"], t["atr"], t["clearance_atr"],
                            t["bearish_score"], t["bullish_score"], t["outcome"], t["r"], t["exit_index"]])
        print(f"\nAudit CSV exported: {output_path}")
    except OSError as error:
        print(f"\nCould not write audit CSV: {error}")
    print("\nAudit complete. Original Phase 13 logic and frozen parameters remain unchanged.")


def phase13_combined_execution_audit_v2():
    """Timestamp-explicit audit; frozen entry/exit rules remain unchanged.

    The existing Phase 13 combined execution audit is preserved as option 26.
    This v2 audit clarifies that MT5 H1 timestamps label bar opens: signals use
    the completed signal bar's close, and exits are only known to occur within
    the reported exit bar. No exact intrabar exit time is inferred.
    """
    print("\n" + "=" * 112)
    print(" PHASE 13 - COMBINED EXECUTION AUDIT v2 (TIMESTAMP / INTEGRITY REVIEW)")
    print("=" * 112)
    print("Frozen rules unchanged: SELL-only, 7/7 priority, 6/7 fallback, S/R filters, 1.5 ATR stop, 2R target.")
    print("MT5 H1 timestamps are treated as bar OPEN timestamps.")
    print("Entry price uses signal-bar CLOSE; assumed entry time is signal-bar open + 1 hour.")
    print("Exit timestamp identifies the bar in which SL/TP was touched; exact intrabar time is unknown.")
    print(f"Development cutoff: {PHASE13_DEVELOPMENT_CUTOFF:%Y-%m-%d %H:%M:%S}")

    file_name = input("Enter the full path to your MT5 XAUUSD H1 CSV: ").strip().strip('"')
    if not file_name:
        print("No file path entered. Audit cancelled.")
        return

    loaded = phase13_load_csv(file_name)
    if loaded is None:
        return
    records, row_count, skipped = loaded
    print(f"\nCSV rows: {row_count} | Valid OHLC: {len(records)} | Skipped: {skipped}")
    print(f"First bar open: {records[0]['timestamp']} | Last bar open: {records[-1]['timestamp']}")

    problems = validate_market_data(records)
    if problems:
        print("\nDATA INTEGRITY WARNINGS:")
        for problem in problems:
            print(f"- {problem}")
        print("Audit stopped: resolve data-integrity warnings before trusting results.")
        return

    if records[-1]["datetime"] <= PHASE13_DEVELOPMENT_CUTOFF:
        print("ERROR: This CSV has no bars after the frozen development cutoff.")
        return

    start_index = next((i for i, row in enumerate(records)
                        if row["datetime"] > PHASE13_DEVELOPMENT_CUTOFF), None)
    if start_index is None:
        print("ERROR: No forward-validation bars found.")
        return

    indicators = build_indicator_series(records)
    trades = []
    next_available = start_index
    candidate_count = 0
    unresolved_count = 0
    skipped_bar_count = 0

    for index in range(start_index, len(records)):
        if index < next_available:
            skipped_bar_count += 1
            continue

        # Priority is deterministic: try primary 7/7 first; use 6/7 only if
        # no primary candidate passes the full frozen filter set on this bar.
        candidate = phase13_candidate(records, indicators, index, PHASE13_PRIMARY_THRESHOLD)
        chosen_threshold = PHASE13_PRIMARY_THRESHOLD if candidate is not None else None
        if candidate is None:
            candidate = phase13_candidate(records, indicators, index, PHASE13_SECONDARY_THRESHOLD)
            if candidate is not None:
                chosen_threshold = PHASE13_SECONDARY_THRESHOLD
        if candidate is None:
            continue

        candidate_count += 1
        result = resolve_trade_r_until(
            records, index, "SELL", candidate["entry"],
            candidate["risk_distance"], PHASE13_RR, len(records) - 1
        )
        if not result["resolved"]:
            unresolved_count += 1
            break

        risk = candidate["risk_distance"]
        signal_bar_open = records[index]["datetime"]
        assumed_entry_time = signal_bar_open + timedelta(hours=1)
        exit_bar_open = records[result["exit_index"]]["datetime"]
        exit_bar_end = exit_bar_open + timedelta(hours=1)

        trades.append({
            "setup": "PRIMARY 7/7" if chosen_threshold == 7 else "SECONDARY 6/7",
            "threshold": chosen_threshold,
            "entry_index": index,
            "signal_bar_open": signal_bar_open,
            "assumed_entry_time": assumed_entry_time,
            "exit_bar_open": exit_bar_open,
            "exit_bar_end": exit_bar_end,
            "entry": candidate["entry"],
            "stop": candidate["entry"] + risk,
            "target": candidate["entry"] - risk * PHASE13_RR,
            "atr": candidate["atr"],
            "clearance_atr": candidate["clearance_atr"],
            "bearish_score": candidate["bearish_score"],
            "bullish_score": candidate["bullish_score"],
            "outcome": result["outcome"],
            "r": result["r"],
            "exit_index": result["exit_index"],
        })
        next_available = result["exit_index"] + 1

    # Integrity assertion: the next executed entry must be strictly after the
    # previous trade's exit bar, consistent with the shared-position rule.
    overlaps = []
    for previous, current in zip(trades, trades[1:]):
        if current["entry_index"] <= previous["exit_index"]:
            overlaps.append((previous["entry_index"], current["entry_index"]))

    if overlaps:
        print("\nERROR: Shared-position integrity check failed; overlapping trade indices detected:")
        for pair in overlaps:
            print(pair)
        print("Do not rely on this audit until the overlap is resolved.")
        return

    metrics = calculate_backtest_metrics(trades, PHASE13_RR)
    print("\n" + "-" * 112)
    print("COMBINED RESULTS — SHARED POSITION / EXPLICIT BAR TIMING")
    print("-" * 112)
    print(f"Forward H1 bars: {len(records) - start_index}")
    print(f"Accepted trade candidates: {candidate_count}")
    print(f"Bars skipped while a position was active / exit bar processed: {skipped_bar_count}")
    print(f"Unresolved final candidates: {unresolved_count}")
    print(f"Completed trades: {metrics['trades']} | Wins: {metrics['wins']} | Losses: {metrics['losses']}")
    print(f"Win rate: {metrics['win_rate']:.2f}%")
    pf = metrics['profit_factor']
    print(f"Profit factor: {'INF' if math.isinf(pf) else f'{pf:.2f}'}")
    print(f"Average R: {metrics['average_r']:.4f} | Total R: {metrics['total_r']:.2f} | Max drawdown: {metrics['max_drawdown_r']:.2f}R")
    print("Shared-position overlap check: PASS")
    print("Same-bar priority: PRIMARY 7/7 before SECONDARY 6/7")
    print("\nTRADE DETAILS (MT5 timestamps are bar opens)")
    print("# | Setup          | Signal bar open     | Assumed entry close  | Exit bar interval          | Result | R")
    print("-" * 112)
    for n, t in enumerate(trades, 1):
        interval = f"{t['exit_bar_open']:%Y-%m-%d %H:%M} to {t['exit_bar_end']:%H:%M}"
        print(f"{n:>2} | {t['setup']:<14} | {t['signal_bar_open']:%Y-%m-%d %H:%M} | "
              f"{t['assumed_entry_time']:%Y-%m-%d %H:%M} | {interval:<26} | {t['outcome']:<6} | {t['r']:>+.1f}")

    output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    output_path = os.path.join(output_dir, "XAUUSD_Phase13_Combined_Execution_Audit_v2.csv")
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["PHASE 13 - COMBINED EXECUTION AUDIT v2"])
            w.writerow(["Mode", "One shared position; primary 7/7 precedence; frozen rules unchanged"])
            w.writerow(["Development cutoff", PHASE13_DEVELOPMENT_CUTOFF.strftime("%Y-%m-%d %H:%M:%S")])
            w.writerow(["Timestamp convention", "MT5 H1 timestamps are bar opens; assumed entry is signal bar open + 1 hour; exit is within exit bar, exact time unknown"])
            w.writerow(["CSV source", file_name])
            w.writerow([])
            w.writerow(["Metric", "Value"])
            w.writerow(["Forward H1 bars", len(records) - start_index])
            w.writerow(["Accepted trade candidates", candidate_count])
            w.writerow(["Bars skipped while active / exit bar processed", skipped_bar_count])
            w.writerow(["Unresolved final candidates", unresolved_count])
            w.writerow(["Completed trades", metrics["trades"]])
            w.writerow(["Wins", metrics["wins"]])
            w.writerow(["Losses", metrics["losses"]])
            w.writerow(["Win rate %", f"{metrics['win_rate']:.2f}"])
            w.writerow(["Profit factor", "INF" if math.isinf(pf) else f"{pf:.4f}"])
            w.writerow(["Average R", f"{metrics['average_r']:.4f}"])
            w.writerow(["Total R", f"{metrics['total_r']:.2f}"])
            w.writerow(["Max drawdown R", f"{metrics['max_drawdown_r']:.2f}"])
            w.writerow(["Shared-position overlap check", "PASS"])
            w.writerow(["Same-bar priority", "PRIMARY 7/7 before SECONDARY 6/7"])
            w.writerow([])
            w.writerow(["setup", "threshold", "entry_index", "signal_bar_open", "assumed_entry_time_at_close",
                        "exit_bar_open", "exit_bar_end", "entry_close_price", "stop", "target", "atr",
                        "clearance_atr", "bearish_score", "bullish_score", "outcome", "r", "exit_index"])
            for t in trades:
                w.writerow([t["setup"], f"{t['threshold']}/7", t["entry_index"],
                            t["signal_bar_open"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["assumed_entry_time"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["exit_bar_open"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["exit_bar_end"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["entry"], t["stop"], t["target"], t["atr"], t["clearance_atr"],
                            t["bearish_score"], t["bullish_score"], t["outcome"], t["r"], t["exit_index"]])
        print(f"\nAudit v2 CSV exported: {output_path}")
    except OSError as error:
        print(f"\nCould not write audit v2 CSV: {error}")
    print("Audit v2 complete. Original Phase 13 logic and frozen parameters remain unchanged.")



def phase13_execution_realism_audit():
    """Separate realism sensitivity audit; does not change frozen strategy rules.

    Uses the same combined, shared-position trade selection as audit v2. It
    reports H1 intrabar ambiguity, gaps through stop/target levels, source
    spread quality, and illustrative per-trade cost sensitivity in R units.
    The cost scenarios are assumptions, not estimates of actual broker costs.
    """
    print("\n" + "=" * 100)
    print(" PHASE 13 - EXECUTION REALISM AUDIT (SEPARATE REPORT; FROZEN RULES)")
    print("=" * 100)
    print("No entry filters, stop/target levels, or signal thresholds are changed.")
    print("H1 OHLC cannot reveal intrabar order; any same-bar stop+target touch is flagged.")
    print("Cost scenarios are illustrative R per completed trade, not broker-specific estimates.")
    file_name = input("Enter full path to MT5 XAUUSD H1 CSV: ").strip().strip('"')
    if not file_name:
        print("No file path entered. Audit cancelled.")
        return
    loaded = phase13_load_csv(file_name)
    if loaded is None:
        return
    records, row_count, skipped = loaded
    problems = validate_market_data(records)
    if problems:
        print("\nDATA INTEGRITY WARNINGS:")
        for p in problems:
            print("- " + p)
        print("Audit stopped. Resolve data warnings first.")
        return
    if records[-1]["datetime"] <= PHASE13_DEVELOPMENT_CUTOFF:
        print("ERROR: No bars after the frozen development cutoff.")
        return

    start_index = next((i for i, r in enumerate(records)
                        if r["datetime"] > PHASE13_DEVELOPMENT_CUTOFF), None)
    if start_index is None:
        print("ERROR: No forward bars found.")
        return
    indicators = build_indicator_series(records)
    trades = []
    next_available = start_index
    skipped_active = 0
    candidate_count = 0
    unresolved = 0
    for i in range(start_index, len(records)):
        if i < next_available:
            skipped_active += 1
            continue
        candidate = phase13_candidate(records, indicators, i, PHASE13_PRIMARY_THRESHOLD)
        threshold = PHASE13_PRIMARY_THRESHOLD if candidate is not None else None
        if candidate is None:
            candidate = phase13_candidate(records, indicators, i, PHASE13_SECONDARY_THRESHOLD)
            if candidate is not None:
                threshold = PHASE13_SECONDARY_THRESHOLD
        if candidate is None:
            continue
        candidate_count += 1
        result = resolve_trade_r_until(records, i, "SELL", candidate["entry"],
                                       candidate["risk_distance"], PHASE13_RR, len(records) - 1)
        if not result["resolved"]:
            unresolved += 1
            break
        stop = candidate["entry"] + candidate["risk_distance"]
        target = candidate["entry"] - candidate["risk_distance"] * PHASE13_RR
        both_indices = []
        stop_gap_indices = []
        target_gap_indices = []
        for j in range(i + 1, result["exit_index"] + 1):
            bar = records[j]
            hit_stop = bar["high"] >= stop
            hit_target = bar["low"] <= target
            if hit_stop and hit_target:
                both_indices.append(j)
            # For a SELL, opening above the stop implies a gap through the stop;
            # opening below target implies a favorable target gap. Exact fills are unknown.
            if bar["open"] >= stop:
                stop_gap_indices.append(j)
            if bar["open"] <= target:
                target_gap_indices.append(j)
        exit_bar = records[result["exit_index"]]
        trades.append({
            "setup": "PRIMARY 7/7" if threshold == 7 else "SECONDARY 6/7",
            "threshold": threshold,
            "signal_index": i,
            "signal_bar_open": records[i]["datetime"],
            "assumed_entry_time": records[i]["datetime"] + timedelta(hours=1),
            "entry": candidate["entry"], "stop": stop, "target": target,
            "risk_distance": candidate["risk_distance"],
            "exit_index": result["exit_index"],
            "exit_bar_open": exit_bar["datetime"],
            "exit_bar_end": exit_bar["datetime"] + timedelta(hours=1),
            "outcome": result["outcome"], "r": result["r"],
            "ambiguous_bars": len(both_indices),
            "ambiguous_exit_bar": result["exit_index"] in both_indices,
            "stop_gap_bars": len(stop_gap_indices),
            "target_gap_bars": len(target_gap_indices),
            "spread_at_entry": records[i].get("spread", 0),
        })
        next_available = result["exit_index"] + 1

    # Validate the shared-position constraint independently.
    overlap_count = sum(1 for a, b in zip(trades, trades[1:]) if b["signal_index"] <= a["exit_index"])
    if overlap_count:
        print(f"ERROR: {overlap_count} overlapping executed trade pairs detected. No report written.")
        return

    base_total = sum(t["r"] for t in trades)
    total_ambiguous = sum(t["ambiguous_bars"] for t in trades)
    ambiguous_exits = sum(1 for t in trades if t["ambiguous_exit_bar"])
    stop_gap_count = sum(t["stop_gap_bars"] for t in trades)
    target_gap_count = sum(t["target_gap_bars"] for t in trades)
    spreads = [r.get("spread", 0) for r in records]
    nonzero_spreads = sum(1 for s in spreads if s != 0)

    print(f"\nRows read: {row_count} | Valid bars: {len(records)} | Skipped malformed rows: {skipped}")
    print(f"Forward bars: {len(records) - start_index} | Completed trades: {len(trades)} | Unresolved final: {unresolved}")
    print(f"Base result before costs: {base_total:+.2f}R")
    print(f"Same-bar stop AND target touched: {total_ambiguous} bar(s); ambiguous exit bars: {ambiguous_exits}")
    print(f"Bars opening through SELL stop: {stop_gap_count} | Bars opening beyond SELL target: {target_gap_count}")
    print(f"Source spread field: {nonzero_spreads}/{len(spreads)} bars have nonzero spread values.")
    if nonzero_spreads == 0:
        print("WARNING: Spread values are all zero/missing; actual spread-based costs cannot be estimated from this file.")
    print("\nILLUSTRATIVE COST SENSITIVITY (deducted per completed trade; not actual broker costs)")
    scenarios = [0.00, 0.02, 0.05, 0.10]
    print("Cost per trade (R) | Total costs (R) | Net total (R) | Average net/trade (R)")
    for cost in scenarios:
        total_cost = cost * len(trades)
        net = base_total - total_cost
        avg = net / len(trades) if trades else 0.0
        print(f"{cost:>16.2f} | {total_cost:>14.2f} | {net:>13.2f} | {avg:>21.3f}")

    print("\nTRADE DETAILS")
    for n, t in enumerate(trades, 1):
        print(f"{n}. {t['setup']} | entry assumed {t['assumed_entry_time']:%Y-%m-%d %H:%M} | "
              f"exit bar {t['exit_bar_open']:%Y-%m-%d %H:%M}–{t['exit_bar_end']:%H:%M} | "
              f"{t['outcome']} {t['r']:+.1f}R | ambiguous bars={t['ambiguous_bars']} | "
              f"stop-gap bars={t['stop_gap_bars']}")

    output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    output_path = os.path.join(output_dir, "XAUUSD_Phase13_Execution_Realism_Audit.csv")
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["PHASE 13 - EXECUTION REALISM AUDIT"])
            w.writerow(["Frozen rules", "Unchanged; one shared position; primary 7/7 precedence; secondary 6/7 fallback"])
            w.writerow(["Source CSV", file_name])
            w.writerow(["Forward bars", len(records) - start_index])
            w.writerow(["Completed trades", len(trades)])
            w.writerow(["Unresolved final candidates", unresolved])
            w.writerow(["Base total R before costs", f"{base_total:.4f}"])
            w.writerow(["Same-bar stop and target bars across trades", total_ambiguous])
            w.writerow(["Ambiguous exit bars", ambiguous_exits])
            w.writerow(["Bars opening through SELL stop", stop_gap_count])
            w.writerow(["Bars opening beyond SELL target", target_gap_count])
            w.writerow(["Nonzero spread values in source", f"{nonzero_spreads}/{len(spreads)}"])
            w.writerow(["Cost scenario note", "Illustrative per-trade R deductions; not actual broker costs. OHLC spread field may be zero or unsuitable for cost estimation."])
            w.writerow([])
            w.writerow(["Cost per trade R", "Total costs R", "Net total R", "Average net R/trade"])
            for cost in scenarios:
                total_cost = cost * len(trades)
                net = base_total - total_cost
                w.writerow([f"{cost:.2f}", f"{total_cost:.2f}", f"{net:.2f}", f"{net / len(trades) if trades else 0:.4f}"])
            w.writerow([])
            w.writerow(["setup", "threshold", "signal_bar_open", "assumed_entry_time", "exit_bar_open", "exit_bar_end", "entry", "stop", "target", "outcome", "gross_r", "ambiguous_bars", "ambiguous_exit_bar", "stop_gap_bars", "target_gap_bars", "source_spread_value"])
            for t in trades:
                w.writerow([t["setup"], f"{t['threshold']}/7", t["signal_bar_open"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["assumed_entry_time"].strftime("%Y-%m-%d %H:%M:%S"), t["exit_bar_open"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["exit_bar_end"].strftime("%Y-%m-%d %H:%M:%S"), t["entry"], t["stop"], t["target"],
                            t["outcome"], t["r"], t["ambiguous_bars"], t["ambiguous_exit_bar"], t["stop_gap_bars"],
                            t["target_gap_bars"], t["spread_at_entry"]])
        print(f"\nRealism audit CSV exported: {output_path}")
    except OSError as e:
        print(f"\nCould not write realism audit CSV: {e}")
    print("Execution realism audit complete. Frozen Phase 13 rules remain unchanged.")


def phase14_forward_sample_monitor():
    """Separate cumulative forward monitor; uses frozen Phase 13 rules unchanged."""
    print("\n" + "=" * 100)
    print(" PHASE 14 - FORWARD SAMPLE MONITOR (SEPARATE FROM FROZEN PHASE 13)")
    print("=" * 100)
    print("This is a cumulative re-check of the current MT5 export, not an automatic live feed.")
    print("Phase 13 thresholds, S/R rules, stop, target, and shared-position logic are unchanged.")
    file_name = input("Enter full path to the latest MT5 XAUUSD H1 CSV: ").strip().strip('"')
    if not file_name:
        print("No file path entered. Monitor cancelled.")
        return
    loaded = phase13_load_csv(file_name)
    if loaded is None:
        return
    records, row_count, skipped = loaded
    problems = validate_market_data(records)
    if problems:
        print("\nDATA INTEGRITY WARNINGS:")
        for problem in problems:
            print("- " + problem)
        print("Monitor stopped. Resolve data warnings first.")
        return
    start_index = next((i for i, r in enumerate(records)
                        if r["datetime"] > PHASE13_DEVELOPMENT_CUTOFF), None)
    if start_index is None:
        print("ERROR: No bars after the frozen development cutoff.")
        return

    indicators = build_indicator_series(records)
    trades = []
    next_available = start_index
    unresolved = 0
    candidate_count = 0
    for i in range(start_index, len(records)):
        if i < next_available:
            continue
        candidate = phase13_candidate(records, indicators, i, PHASE13_PRIMARY_THRESHOLD)
        threshold = PHASE13_PRIMARY_THRESHOLD if candidate is not None else None
        if candidate is None:
            candidate = phase13_candidate(records, indicators, i, PHASE13_SECONDARY_THRESHOLD)
            if candidate is not None:
                threshold = PHASE13_SECONDARY_THRESHOLD
        if candidate is None:
            continue
        candidate_count += 1
        result = resolve_trade_r_until(records, i, "SELL", candidate["entry"],
                                       candidate["risk_distance"], PHASE13_RR, len(records) - 1)
        if not result["resolved"]:
            unresolved += 1
            # A not-yet-resolved signal remains a candidate; do not score it as a completed trade.
            continue
        stop = candidate["entry"] + candidate["risk_distance"]
        target = candidate["entry"] - candidate["risk_distance"] * PHASE13_RR
        exit_bar = records[result["exit_index"]]
        trades.append({
            "setup": "PRIMARY 7/7" if threshold == 7 else "SECONDARY 6/7",
            "threshold": threshold,
            "signal_index": i,
            "signal_bar_open": records[i]["datetime"],
            "assumed_entry_time": records[i]["datetime"] + timedelta(hours=1),
            "entry": candidate["entry"], "stop": stop, "target": target,
            "exit_index": result["exit_index"],
            "exit_bar_open": exit_bar["datetime"],
            "exit_bar_end": exit_bar["datetime"] + timedelta(hours=1),
            "outcome": result["outcome"], "r": result["r"],
            "spread_at_entry": records[i].get("spread", 0),
        })
        next_available = result["exit_index"] + 1

    overlap_count = sum(1 for a, b in zip(trades, trades[1:])
                        if b["signal_index"] <= a["exit_index"])
    if overlap_count:
        print(f"ERROR: {overlap_count} overlapping trade pairs detected. No report written.")
        return

    wins = sum(1 for t in trades if t["r"] > 0)
    losses = sum(1 for t in trades if t["r"] < 0)
    flats = len(trades) - wins - losses
    total_r = sum(t["r"] for t in trades)
    avg_r = total_r / len(trades) if trades else 0.0
    spreads = [r.get("spread", 0) for r in records]
    nonzero_spreads = sum(1 for s in spreads if s != 0)
    fingerprint_payload = "\n".join(
        f"{r['datetime'].isoformat()}|{r['open']}|{r['high']}|{r['low']}|{r['close']}|{r.get('spread', 0)}"
        for r in records
    )
    fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()

    print(f"\nSource rows: {row_count} | Valid H1 bars: {len(records)} | Skipped malformed rows: {skipped}")
    print(f"Data range: {records[0]['datetime']} to {records[-1]['datetime']}")
    print(f"Forward bars after cutoff: {len(records) - start_index}")
    print(f"Completed trades: {len(trades)} | Unresolved candidates: {unresolved} | Wins/losses/flats: {wins}/{losses}/{flats}")
    print(f"Cumulative gross result: {total_r:+.2f}R | Average per completed trade: {avg_r:+.3f}R")
    print(f"Source nonzero spreads: {nonzero_spreads}/{len(spreads)}")
    if nonzero_spreads == 0:
        print("WARNING: spread data is all zero/missing; costs cannot be estimated from this export.")
    print("\nTRADE DETAILS")
    if not trades:
        print("No completed trades in the forward sample yet.")
    for n, t in enumerate(trades, 1):
        print(f"{n}. {t['setup']} | signal {t['signal_bar_open']:%Y-%m-%d %H:%M} | "
              f"assumed entry {t['assumed_entry_time']:%Y-%m-%d %H:%M} | "
              f"exit {t['exit_bar_open']:%Y-%m-%d %H:%M}–{t['exit_bar_end']:%H:%M} | "
              f"{t['outcome']} {t['r']:+.1f}R")

    output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "XAUUSD_Phase14_Forward_Sample_Monitor.csv")
    snapshot_path = os.path.join(output_dir, "XAUUSD_Phase14_Monitor_Snapshots.csv")
    try:
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["PHASE 14 - FORWARD SAMPLE MONITOR"])
            w.writerow(["Frozen Phase 13 rules", "UNCHANGED; primary 7/7 then secondary 6/7; one position at a time; S/R and risk rules unchanged"])
            w.writerow(["Source CSV", file_name])
            w.writerow(["Development cutoff", PHASE13_DEVELOPMENT_CUTOFF.strftime("%Y-%m-%d %H:%M:%S")])
            w.writerow(["First source bar", records[0]["datetime"].strftime("%Y-%m-%d %H:%M:%S")])
            w.writerow(["Last source bar", records[-1]["datetime"].strftime("%Y-%m-%d %H:%M:%S")])
            w.writerow(["Valid bars", len(records)])
            w.writerow(["Forward bars", len(records) - start_index])
            w.writerow(["Completed trades", len(trades)])
            w.writerow(["Unresolved candidates", unresolved])
            w.writerow(["Wins", wins]); w.writerow(["Losses", losses]); w.writerow(["Flats", flats])
            w.writerow(["Cumulative gross R", f"{total_r:.4f}"])
            w.writerow(["Average R per completed trade", f"{avg_r:.4f}"])
            w.writerow(["Nonzero spread values", f"{nonzero_spreads}/{len(spreads)}"])
            w.writerow(["Data SHA-256", fingerprint])
            w.writerow([])
            w.writerow(["setup", "threshold", "signal_bar_open", "assumed_entry_time", "exit_bar_open", "exit_bar_end", "entry", "stop", "target", "outcome", "gross_r", "source_spread_value"])
            for t in trades:
                w.writerow([t["setup"], f"{t['threshold']}/7", t["signal_bar_open"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["assumed_entry_time"].strftime("%Y-%m-%d %H:%M:%S"), t["exit_bar_open"].strftime("%Y-%m-%d %H:%M:%S"),
                            t["exit_bar_end"].strftime("%Y-%m-%d %H:%M:%S"), t["entry"], t["stop"], t["target"],
                            t["outcome"], t["r"], t["spread_at_entry"]])

        # Keep a lightweight run history, adding a row only when the source data changes.
        previous_fingerprint = None
        if os.path.exists(snapshot_path):
            try:
                with open(snapshot_path, "r", newline="", encoding="utf-8-sig") as f:
                    prior_rows = list(csv.DictReader(f))
                if prior_rows:
                    previous_fingerprint = prior_rows[-1].get("data_sha256")
            except (OSError, csv.Error):
                previous_fingerprint = None
        if previous_fingerprint != fingerprint:
            exists = os.path.exists(snapshot_path)
            with open(snapshot_path, "a", newline="", encoding="utf-8") as f:
                fields = ["snapshot_time", "source_file", "last_bar", "valid_bars", "forward_bars", "completed_trades", "unresolved_candidates", "wins", "losses", "gross_r", "avg_r", "nonzero_spreads", "data_sha256"]
                w = csv.DictWriter(f, fieldnames=fields)
                if not exists or os.path.getsize(snapshot_path) == 0:
                    w.writeheader()
                w.writerow({"snapshot_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source_file": file_name,
                            "last_bar": records[-1]["datetime"].strftime("%Y-%m-%d %H:%M:%S"), "valid_bars": len(records),
                            "forward_bars": len(records) - start_index, "completed_trades": len(trades),
                            "unresolved_candidates": unresolved, "wins": wins, "losses": losses,
                            "gross_r": f"{total_r:.4f}", "avg_r": f"{avg_r:.4f}",
                            "nonzero_spreads": f"{nonzero_spreads}/{len(spreads)}", "data_sha256": fingerprint})
            print(f"\nNew data snapshot recorded: {snapshot_path}")
        else:
            print("\nNo source-data change since the last snapshot; history was not duplicated.")
        print(f"Cumulative monitor report exported: {report_path}")
        print("This report is not a live feed. Re-export MT5 H1 data and rerun Option 29 to update it.")
        print("Phase 13 frozen rules remain unchanged.")
    except OSError as error:
        print(f"\nCould not write Phase 14 reports: {error}")

def main():
    """Display the main FinMarket Analyzer menu."""
    while True:
        print("\n========================================")
        print("       FINMARKET ANALYZER")
        print("========================================")
        print("1. Add Market Asset")
        print("2. View Market Assets")
        print("3. Analyze Asset")
        print("4. Market Statistics")
        print("5. Volatility Analysis")
        print("6. Historical Price Analysis")
        print("7. Moving Average Analysis")
        print("8. RSI Analysis")
        print("9. MACD Analysis")
        print("10. Combined Market Signal")
        print("11. CSV Data Import")
        print("12. Phase 12 Historical Backtest")
        print("13. Phase 12.1 Diagnostic Backtest")
        print("14. Phase 12.2 S/R Diagnostic")
        print("15. Phase 12.3 Comparative Backtest")
        print("16. Phase 12.4 70/30 Validation")
        print("17. Phase 12.5 Corrected Rolling Validation")
        print("18. Phase 12.6 Trade-Level Failure & Feature Analysis")
        print("19. Phase 12.7 Predefined Hypothesis Testing")
        print("20. Phase 12.7.2 13-Trade Deep Inspection")
        print("21. Phase 12.7.3 7-Component Setup Inspection")
        print("22. Phase 12.7.4 Near-Miss Component Analysis")
        print("23. Phase 12.7.5 SELL Score Threshold Backtest")
        print("24. Phase 13 Frozen Out-of-Sample Validation")
        print("25. Exit")
        print("26. Phase 13 Combined Execution Audit (original separate audit)")
        print("27. Phase 13 Combined Execution Audit v2 (timestamp + integrity checks)")
        print("28. Phase 13 Execution Realism Audit (cost sensitivity + intrabar ambiguity)")
        print("29. Phase 14 Forward Sample Monitor (separate cumulative monitoring)")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            add_market_asset()
        elif choice == "2":
            view_market_assets()
        elif choice == "3":
            analyze_asset()
        elif choice == "4":
            market_statistics()
        elif choice == "5":
            volatility_analysis()
        elif choice == "6":
            historical_price_analysis()
        elif choice == "7":
            moving_average_analysis()
        elif choice == "8":
            rsi_analysis()
        elif choice == "9":
            macd_analysis()
        elif choice == "10":
            combined_market_signal()
        elif choice == "11":
            csv_data_import()
        elif choice == "12":
            phase12_backtest()
        elif choice == "13":
            phase12_1_diagnostic()
        elif choice == "14":
            phase12_2_diagnostic()
        elif choice == "15":
            phase12_3_comparative_backtest()
        elif choice == "16":
            phase12_4_validation()
        elif choice == "17":
            phase12_5_validation()
        elif choice == "18":
            phase12_6_validation()
        elif choice == "19":
            phase12_7_validation()
        elif choice == "20":
            phase12_7_2_trade_inspection()
        elif choice == "21":
            phase12_7_3_component_inspection()
        elif choice == "22":
            phase12_7_4_near_miss_analysis()
        elif choice == "23":
            phase12_7_5_threshold_backtest()
        elif choice == "24":
            phase13_forward_validation()
        elif choice == "26":
            phase13_combined_execution_audit()
        elif choice == "27":
            phase13_combined_execution_audit_v2()
        elif choice == "28":
            phase13_execution_realism_audit()
        elif choice == "29":
            phase14_forward_sample_monitor()
        elif choice == "25":
            print("\nThank you for using FinMarket Analyzer.")
            break
        else:
            print("\nInvalid choice. Please try again.")


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    main()
