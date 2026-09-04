"""Deterministic SMC research engine with explicit confirmation timing."""

from __future__ import annotations

from dataclasses import dataclass

from al_kripto.market_data import Candle

from .models import (
    BreakKind,
    Direction,
    FairValueGap,
    LiquiditySweep,
    OrderBlock,
    SMCAnalysis,
    StructureBreak,
    SwingKind,
    SwingPoint,
)


@dataclass(frozen=True, slots=True)
class SMCEngineConfig:
    """Parameters that make subjective SMC concepts explicit and reproducible."""

    swing_strength: int = 2
    order_block_lookback: int = 8

    def __post_init__(self) -> None:
        if self.swing_strength <= 0:
            raise ValueError("swing_strength must be > 0.")
        if self.order_block_lookback <= 0:
            raise ValueError("order_block_lookback must be > 0.")


def detect_swings(candles: tuple[Candle, ...], *, strength: int = 2) -> tuple[SwingPoint, ...]:
    """Detect strict local extrema and record when each extremum becomes knowable."""
    if strength <= 0:
        raise ValueError("strength must be > 0.")
    if len(candles) < (2 * strength) + 1:
        return ()

    swings: list[SwingPoint] = []
    for index in range(strength, len(candles) - strength):
        current = candles[index]
        neighbours = candles[index - strength : index] + candles[index + 1 : index + strength + 1]
        confirmation_index = index + strength
        confirmation_time = candles[confirmation_index].close_time_ms

        if all(current.high > candle.high for candle in neighbours):
            swings.append(
                SwingPoint(
                    kind=SwingKind.HIGH,
                    index=index,
                    price=current.high,
                    occurred_at_ms=current.close_time_ms,
                    confirmed_index=confirmation_index,
                    confirmed_at_ms=confirmation_time,
                )
            )
        if all(current.low < candle.low for candle in neighbours):
            swings.append(
                SwingPoint(
                    kind=SwingKind.LOW,
                    index=index,
                    price=current.low,
                    occurred_at_ms=current.close_time_ms,
                    confirmed_index=confirmation_index,
                    confirmed_at_ms=confirmation_time,
                )
            )
    return tuple(swings)


def detect_fair_value_gaps(candles: tuple[Candle, ...]) -> tuple[FairValueGap, ...]:
    """Detect strict three-candle high/low non-overlap zones."""
    gaps: list[FairValueGap] = []
    for index in range(2, len(candles)):
        first = candles[index - 2]
        third = candles[index]
        if third.low > first.high:
            gaps.append(
                FairValueGap(
                    direction=Direction.BULLISH,
                    index=index,
                    lower=first.high,
                    upper=third.low,
                    event_time_ms=third.close_time_ms,
                )
            )
        elif third.high < first.low:
            gaps.append(
                FairValueGap(
                    direction=Direction.BEARISH,
                    index=index,
                    lower=third.high,
                    upper=first.low,
                    event_time_ms=third.close_time_ms,
                )
            )
    return tuple(gaps)


class SMCEngine:
    """Emit deterministic price-structure research events from closed candles."""

    def __init__(self, config: SMCEngineConfig | None = None) -> None:
        self._config = config or SMCEngineConfig()

    def analyze(self, candles: tuple[Candle, ...]) -> SMCAnalysis:
        _validate_sequence(candles)
        swings = detect_swings(candles, strength=self._config.swing_strength)
        gaps = detect_fair_value_gaps(candles)
        highs = tuple(swing for swing in swings if swing.kind is SwingKind.HIGH)
        lows = tuple(swing for swing in swings if swing.kind is SwingKind.LOW)

        broken_highs: set[int] = set()
        broken_lows: set[int] = set()
        swept_highs: set[int] = set()
        swept_lows: set[int] = set()
        sweeps: list[LiquiditySweep] = []
        breaks: list[StructureBreak] = []
        blocks: list[OrderBlock] = []
        last_break_direction: Direction | None = None

        for index, candle in enumerate(candles):
            swing_high = _latest_available(highs, index=index, excluded=broken_highs)
            swing_low = _latest_available(lows, index=index, excluded=broken_lows)

            if swing_high is not None and swing_high.index not in swept_highs:
                if candle.high > swing_high.price and candle.close < swing_high.price:
                    sweeps.append(
                        LiquiditySweep(
                            direction=Direction.BEARISH,
                            index=index,
                            swing_index=swing_high.index,
                            level=swing_high.price,
                            event_time_ms=candle.close_time_ms,
                        )
                    )
                    swept_highs.add(swing_high.index)

            if swing_low is not None and swing_low.index not in swept_lows:
                if candle.low < swing_low.price and candle.close > swing_low.price:
                    sweeps.append(
                        LiquiditySweep(
                            direction=Direction.BULLISH,
                            index=index,
                            swing_index=swing_low.index,
                            level=swing_low.price,
                            event_time_ms=candle.close_time_ms,
                        )
                    )
                    swept_lows.add(swing_low.index)

            if swing_high is not None and candle.close > swing_high.price:
                break_kind = _break_kind(last_break_direction, Direction.BULLISH)
                breaks.append(
                    StructureBreak(
                        kind=break_kind,
                        direction=Direction.BULLISH,
                        index=index,
                        swing_index=swing_high.index,
                        level=swing_high.price,
                        event_time_ms=candle.close_time_ms,
                    )
                )
                broken_highs.add(swing_high.index)
                last_break_direction = Direction.BULLISH
                block = _find_order_block(
                    candles,
                    break_index=index,
                    direction=Direction.BULLISH,
                    lookback=self._config.order_block_lookback,
                )
                if block is not None:
                    blocks.append(block)

            if swing_low is not None and candle.close < swing_low.price:
                break_kind = _break_kind(last_break_direction, Direction.BEARISH)
                breaks.append(
                    StructureBreak(
                        kind=break_kind,
                        direction=Direction.BEARISH,
                        index=index,
                        swing_index=swing_low.index,
                        level=swing_low.price,
                        event_time_ms=candle.close_time_ms,
                    )
                )
                broken_lows.add(swing_low.index)
                last_break_direction = Direction.BEARISH
                block = _find_order_block(
                    candles,
                    break_index=index,
                    direction=Direction.BEARISH,
                    lookback=self._config.order_block_lookback,
                )
                if block is not None:
                    blocks.append(block)

        return SMCAnalysis(
            swings=swings,
            sweeps=tuple(sweeps),
            breaks=tuple(breaks),
            fair_value_gaps=gaps,
            order_blocks=tuple(blocks),
        )


def _latest_available(
    swings: tuple[SwingPoint, ...],
    *,
    index: int,
    excluded: set[int],
) -> SwingPoint | None:
    for swing in reversed(swings):
        if swing.confirmed_index < index and swing.index not in excluded:
            return swing
    return None


def _break_kind(previous: Direction | None, current: Direction) -> BreakKind:
    if previous is not None and previous is not current:
        return BreakKind.CHOCH
    return BreakKind.BOS


def _find_order_block(
    candles: tuple[Candle, ...],
    *,
    break_index: int,
    direction: Direction,
    lookback: int,
) -> OrderBlock | None:
    start = max(0, break_index - lookback)
    for index in range(break_index - 1, start - 1, -1):
        candle = candles[index]
        opposite = (
            candle.close < candle.open
            if direction is Direction.BULLISH
            else candle.close > candle.open
        )
        if opposite:
            return OrderBlock(
                direction=direction,
                index=index,
                lower=candle.low,
                upper=candle.high,
                confirmed_by_index=break_index,
                event_time_ms=candles[break_index].close_time_ms,
            )
    return None


def _validate_sequence(candles: tuple[Candle, ...]) -> None:
    if not candles:
        return
    symbol = candles[0].symbol
    previous_open = -1
    for candle in candles:
        if candle.symbol != symbol:
            raise ValueError("All candles in an SMC analysis must use the same symbol.")
        if candle.open_time_ms <= previous_open:
            raise ValueError("Candles must be strictly chronological.")
        previous_open = candle.open_time_ms
