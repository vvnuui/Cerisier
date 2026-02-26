"""Paper trading simulator engine."""

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from ..models import KlineData, PerformanceMetric, Portfolio, Position, Trade

logger = logging.getLogger(__name__)

# A-share commission rate (万2.5, minimum 5 yuan)
DEFAULT_COMMISSION_RATE = Decimal("0.00025")
MIN_COMMISSION = Decimal("5.00")


class InsufficientFundsError(Exception):
    """Raised when portfolio has insufficient cash for a buy order."""

    pass


class InsufficientSharesError(Exception):
    """Raised when position has insufficient shares for a sell order."""

    pass


class SimulatorEngine:
    """Paper trading engine that manages portfolio operations.

    Handles buy/sell execution, position tracking, and performance calculation.
    Uses A-share market rules:
    - Buy/sell in lots of 100 (1手 = 100股)
    - Commission: 万2.5, minimum 5 yuan
    - No T+0 (handled at API level, not engine)
    """

    def __init__(
        self,
        portfolio: Portfolio,
        commission_rate: Decimal = DEFAULT_COMMISSION_RATE,
    ):
        self.portfolio = portfolio
        self.commission_rate = commission_rate

    def _calculate_commission(self, amount: Decimal) -> Decimal:
        """Calculate trading commission."""
        commission = (amount * self.commission_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return max(commission, MIN_COMMISSION)

    @transaction.atomic
    def buy(
        self,
        stock_code: str,
        shares: int,
        price: Decimal,
        reason: str = "",
    ) -> Trade:
        """Execute a buy order.

        Args:
            stock_code: Stock code
            shares: Number of shares to buy (should be multiple of 100)
            price: Price per share
            reason: Optional trade reason

        Returns:
            Trade record

        Raises:
            InsufficientFundsError: If cash is insufficient
            ValueError: If shares <= 0
        """
        if shares <= 0:
            raise ValueError("Shares must be positive")

        amount = (Decimal(str(shares)) * price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        commission = self._calculate_commission(amount)
        total_cost = amount + commission

        # Refresh portfolio from DB within transaction
        portfolio = Portfolio.objects.select_for_update().get(pk=self.portfolio.pk)

        if portfolio.cash_balance < total_cost:
            raise InsufficientFundsError(
                f"Need {total_cost}, only have {portfolio.cash_balance}"
            )

        # Deduct cash
        portfolio.cash_balance -= total_cost
        portfolio.save(update_fields=["cash_balance", "updated_at"])
        self.portfolio.refresh_from_db()

        # Update or create position
        position, created = Position.objects.get_or_create(
            portfolio=portfolio,
            stock_id=stock_code,
            defaults={
                "shares": 0,
                "avg_cost": Decimal("0"),
                "current_price": price,
            },
        )

        if not created:
            # Weighted average cost
            old_cost = position.shares * position.avg_cost
            new_cost = Decimal(str(shares)) * price
            total_shares = position.shares + shares
            if total_shares > 0:
                position.avg_cost = (
                    (old_cost + new_cost) / total_shares
                ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        else:
            position.avg_cost = price

        position.shares += shares
        position.current_price = price
        position.save()

        # Create trade record
        trade = Trade.objects.create(
            portfolio=portfolio,
            stock_id=stock_code,
            trade_type=Trade.BUY,
            shares=shares,
            price=price,
            amount=amount,
            commission=commission,
            reason=reason,
        )

        logger.info(
            f"BUY {stock_code} x {shares} @ {price} "
            f"for portfolio {portfolio.name}"
        )
        return trade

    @transaction.atomic
    def sell(
        self,
        stock_code: str,
        shares: int,
        price: Decimal,
        reason: str = "",
    ) -> Trade:
        """Execute a sell order.

        Args:
            stock_code: Stock code
            shares: Number of shares to sell
            price: Price per share
            reason: Optional trade reason

        Returns:
            Trade record

        Raises:
            InsufficientSharesError: If position has fewer shares
            ValueError: If shares <= 0
        """
        if shares <= 0:
            raise ValueError("Shares must be positive")

        amount = (Decimal(str(shares)) * price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        commission = self._calculate_commission(amount)
        net_proceeds = amount - commission

        # Get position
        try:
            position = Position.objects.select_for_update().get(
                portfolio=self.portfolio, stock_id=stock_code
            )
        except Position.DoesNotExist:
            raise InsufficientSharesError(f"No position in {stock_code}")

        if position.shares < shares:
            raise InsufficientSharesError(
                f"Have {position.shares}, need {shares}"
            )

        # Refresh portfolio
        portfolio = Portfolio.objects.select_for_update().get(
            pk=self.portfolio.pk
        )

        # Update position
        position.shares -= shares
        position.current_price = price
        if position.shares == 0:
            position.delete()
        else:
            position.save()

        # Add cash proceeds
        portfolio.cash_balance += net_proceeds
        portfolio.save(update_fields=["cash_balance", "updated_at"])
        self.portfolio.refresh_from_db()

        # Create trade record
        trade = Trade.objects.create(
            portfolio=portfolio,
            stock_id=stock_code,
            trade_type=Trade.SELL,
            shares=shares,
            price=price,
            amount=amount,
            commission=commission,
            reason=reason,
        )

        logger.info(
            f"SELL {stock_code} x {shares} @ {price} "
            f"for portfolio {portfolio.name}"
        )
        return trade

    def get_portfolio_summary(self) -> dict:
        """Get current portfolio summary.

        Returns:
            Dict with portfolio value breakdown.
        """
        self.portfolio.refresh_from_db()
        positions = list(
            self.portfolio.positions.select_related("stock").all()
        )

        total_market_value = sum(p.market_value for p in positions)
        total_cost_basis = sum(p.cost_basis for p in positions)
        total_unrealized_pnl = total_market_value - total_cost_basis

        total_value = self.portfolio.cash_balance + total_market_value
        total_return_pct = (
            float(
                (total_value - self.portfolio.initial_capital)
                / self.portfolio.initial_capital
                * 100
            )
            if self.portfolio.initial_capital
            else 0.0
        )

        return {
            "portfolio_id": self.portfolio.pk,
            "name": self.portfolio.name,
            "cash_balance": float(self.portfolio.cash_balance),
            "total_market_value": float(total_market_value),
            "total_value": float(total_value),
            "initial_capital": float(self.portfolio.initial_capital),
            "total_return_pct": round(total_return_pct, 4),
            "total_unrealized_pnl": float(total_unrealized_pnl),
            "position_count": len(positions),
            "positions": [
                {
                    "stock_code": p.stock_id,
                    "stock_name": p.stock.name,
                    "shares": p.shares,
                    "avg_cost": float(p.avg_cost),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pnl": float(p.unrealized_pnl),
                    "unrealized_pnl_pct": round(p.unrealized_pnl_pct, 2),
                }
                for p in positions
            ],
        }

    def update_positions_price(self):
        """Update all position current prices from latest KlineData."""
        positions = self.portfolio.positions.all()
        for position in positions:
            latest_kline = (
                KlineData.objects.filter(stock_id=position.stock_id)
                .order_by("-date")
                .first()
            )
            if latest_kline:
                position.current_price = latest_kline.close
                position.save(update_fields=["current_price", "updated_at"])

    def calculate_performance(
        self, as_of_date: date | None = None
    ) -> PerformanceMetric:
        """Calculate and save performance metrics for a given date.

        Args:
            as_of_date: Date for the metric. Defaults to today.

        Returns:
            PerformanceMetric instance
        """
        if as_of_date is None:
            as_of_date = date.today()

        self.portfolio.refresh_from_db()
        positions = list(self.portfolio.positions.all())

        # Total value
        total_market_value = sum(p.market_value for p in positions)
        total_value = self.portfolio.cash_balance + total_market_value

        # Get previous metric for daily return calculation
        prev_metric = (
            PerformanceMetric.objects.filter(
                portfolio=self.portfolio, date__lt=as_of_date
            )
            .order_by("-date")
            .first()
        )

        if prev_metric:
            prev_value = prev_metric.total_value
            daily_return = (
                ((total_value - prev_value) / prev_value * 100)
                if prev_value
                else Decimal("0")
            )
        else:
            daily_return = (
                (
                    (total_value - self.portfolio.initial_capital)
                    / self.portfolio.initial_capital
                    * 100
                )
                if self.portfolio.initial_capital
                else Decimal("0")
            )

        # Cumulative return
        cumulative_return = (
            (
                (total_value - self.portfolio.initial_capital)
                / self.portfolio.initial_capital
                * 100
            )
            if self.portfolio.initial_capital
            else Decimal("0")
        )

        # Max drawdown: peak-to-trough from all metrics
        all_metrics = list(
            PerformanceMetric.objects.filter(portfolio=self.portfolio)
            .order_by("date")
            .values_list("total_value", flat=True)
        )
        all_values = [float(v) for v in all_metrics] + [float(total_value)]
        max_drawdown = self._calc_max_drawdown(all_values)

        # Sharpe ratio (annualized, using all daily returns)
        all_daily_returns = list(
            PerformanceMetric.objects.filter(portfolio=self.portfolio)
            .order_by("date")
            .values_list("daily_return", flat=True)
        )
        all_daily_returns.append(daily_return)
        sharpe = self._calc_sharpe_ratio(
            [float(r) for r in all_daily_returns]
        )

        # Win rate
        completed_trades = Trade.objects.filter(
            portfolio=self.portfolio, trade_type=Trade.SELL
        )
        win_rate = self._calc_win_rate(completed_trades)

        # Save metric
        metric, _ = PerformanceMetric.objects.update_or_create(
            portfolio=self.portfolio,
            date=as_of_date,
            defaults={
                "total_value": (
                    total_value.quantize(Decimal("0.01"))
                    if isinstance(total_value, Decimal)
                    else Decimal(str(round(float(total_value), 2)))
                ),
                "daily_return": Decimal(str(round(float(daily_return), 4))),
                "cumulative_return": Decimal(
                    str(round(float(cumulative_return), 4))
                ),
                "max_drawdown": Decimal(str(round(max_drawdown, 4))),
                "sharpe_ratio": (
                    Decimal(str(round(sharpe, 4)))
                    if sharpe is not None
                    else None
                ),
                "win_rate": (
                    Decimal(str(round(win_rate, 4)))
                    if win_rate is not None
                    else None
                ),
            },
        )

        return metric

    @staticmethod
    def _calc_max_drawdown(values: list[float]) -> float:
        """Calculate maximum drawdown from a series of portfolio values."""
        if len(values) < 2:
            return 0.0

        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak * 100
                max_dd = max(max_dd, dd)
        return max_dd

    @staticmethod
    def _calc_sharpe_ratio(
        daily_returns: list[float], risk_free_rate: float = 3.0
    ) -> float | None:
        """Calculate annualized Sharpe ratio.

        Args:
            daily_returns: List of daily return percentages
            risk_free_rate: Annual risk-free rate (%)

        Returns:
            Sharpe ratio or None if insufficient data
        """
        if len(daily_returns) < 5:
            return None

        import numpy as np

        returns = np.array(daily_returns)
        mean_return = returns.mean()
        std_return = returns.std()

        if std_return == 0:
            return None

        # Annualize (assume 250 trading days)
        daily_rf = risk_free_rate / 250
        sharpe = (mean_return - daily_rf) / std_return * np.sqrt(250)
        return float(sharpe)

    @staticmethod
    def _calc_win_rate(sell_trades) -> float | None:
        """Calculate win rate from completed sell trades.

        A trade is a "win" if sell price > avg cost of that position at
        time of buy. Simplified: compare sell price with buy trades avg
        price for same stock.
        """
        if not sell_trades.exists():
            return None

        wins = 0
        total = 0
        for trade in sell_trades:
            # Get average buy price for this stock in this portfolio
            buy_trades = Trade.objects.filter(
                portfolio=trade.portfolio,
                stock=trade.stock,
                trade_type=Trade.BUY,
            )
            if buy_trades.exists():
                from django.db.models import Avg

                avg_buy_price = buy_trades.aggregate(
                    avg_price=Avg("price")
                )["avg_price"]
                if avg_buy_price and trade.price > avg_buy_price:
                    wins += 1
            total += 1

        return (wins / total * 100) if total > 0 else None
