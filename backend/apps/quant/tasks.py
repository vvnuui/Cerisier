from celery import shared_task
from decimal import Decimal
import logging
import pandas as pd
from datetime import date, timedelta

from .models import (
    StockBasic,
    KlineData,
    MoneyFlow,
    MarginData,
    FinancialReport,
    NewsArticle,
)
from .datasources import DataSourceRouter

logger = logging.getLogger(__name__)


@shared_task(name="quant.sync_stock_list")
def sync_stock_list():
    """Sync the list of all A-share stocks."""
    router = DataSourceRouter()
    df = router.fetch_stock_list()
    if df.empty:
        logger.warning("Empty stock list from data source")
        return {"synced": 0}

    created = 0
    updated = 0
    for _, row in df.iterrows():
        _, was_created = StockBasic.objects.update_or_create(
            code=row["code"],
            defaults={
                "name": row.get("name", ""),
                "industry": row.get("industry", ""),
                "market": row.get("market", ""),
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    logger.info(f"Stock list synced: {created} created, {updated} updated")
    return {"created": created, "updated": updated}


@shared_task(name="quant.sync_daily_kline", bind=True, max_retries=3)
def sync_daily_kline(self, stock_code: str | None = None, days: int = 30):
    """Sync daily K-line data. If no stock_code, sync all active stocks."""
    router = DataSourceRouter()
    end_date = date.today().strftime("%Y%m%d")
    start_date = (date.today() - timedelta(days=days)).strftime("%Y%m%d")

    if stock_code:
        codes = [stock_code]
    else:
        codes = list(
            StockBasic.objects.filter(is_active=True).values_list("code", flat=True)
        )

    synced_total = 0
    errors = 0

    for code in codes:
        try:
            df = router.fetch_kline(code, start_date, end_date)
            if df.empty:
                continue

            for _, row in df.iterrows():
                KlineData.objects.update_or_create(
                    stock_id=code,
                    date=row["date"],
                    defaults={
                        "open": Decimal(str(row["open"])),
                        "high": Decimal(str(row["high"])),
                        "low": Decimal(str(row["low"])),
                        "close": Decimal(str(row["close"])),
                        "volume": int(row["volume"]),
                        "amount": Decimal(str(row["amount"])),
                        "turnover": Decimal(str(row["turnover"]))
                        if pd.notna(row.get("turnover"))
                        else None,
                        "change_pct": Decimal(str(row["change_pct"]))
                        if pd.notna(row.get("change_pct"))
                        else None,
                    },
                )
            synced_total += len(df)
        except Exception as e:
            logger.error(f"Failed to sync kline for {code}: {e}")
            errors += 1

    logger.info(f"Kline sync done: {synced_total} records, {errors} errors")
    return {"synced": synced_total, "errors": errors}


@shared_task(name="quant.sync_money_flow")
def sync_money_flow(stock_code: str | None = None):
    """Sync money flow data."""
    router = DataSourceRouter()

    if stock_code:
        codes = [stock_code]
    else:
        codes = list(
            StockBasic.objects.filter(is_active=True).values_list("code", flat=True)
        )

    synced_total = 0
    errors = 0

    for code in codes:
        try:
            df = router.fetch_money_flow(code)
            if df.empty:
                continue

            for _, row in df.iterrows():
                MoneyFlow.objects.update_or_create(
                    stock_id=code,
                    date=row["date"],
                    defaults={
                        "main_net": Decimal(str(row["main_net"])),
                        "huge_net": Decimal(str(row["huge_net"])),
                        "big_net": Decimal(str(row["big_net"])),
                        "mid_net": Decimal(str(row["mid_net"])),
                        "small_net": Decimal(str(row["small_net"])),
                    },
                )
            synced_total += len(df)
        except Exception as e:
            logger.error(f"Failed to sync money flow for {code}: {e}")
            errors += 1

    return {"synced": synced_total, "errors": errors}


@shared_task(name="quant.sync_margin_data")
def sync_margin_data(stock_code: str | None = None):
    """Sync margin trading data."""
    router = DataSourceRouter()

    if stock_code:
        codes = [stock_code]
    else:
        codes = list(
            StockBasic.objects.filter(is_active=True).values_list("code", flat=True)
        )

    synced_total = 0
    errors = 0

    for code in codes:
        try:
            df = router.fetch_margin_data(code)
            if df.empty:
                continue
            for _, row in df.iterrows():
                MarginData.objects.update_or_create(
                    stock_id=code,
                    date=row["date"],
                    defaults={
                        "margin_balance": Decimal(str(row["margin_balance"])),
                        "short_balance": Decimal(str(row["short_balance"])),
                        "margin_buy": Decimal(str(row["margin_buy"])),
                        "margin_repay": Decimal(str(row["margin_repay"])),
                    },
                )
            synced_total += len(df)
        except Exception as e:
            logger.error(f"Failed to sync margin data for {code}: {e}")
            errors += 1

    return {"synced": synced_total, "errors": errors}


@shared_task(name="quant.sync_financial_reports")
def sync_financial_reports(stock_code: str | None = None):
    """Sync financial report data."""
    router = DataSourceRouter()

    if stock_code:
        codes = [stock_code]
    else:
        codes = list(
            StockBasic.objects.filter(is_active=True).values_list("code", flat=True)
        )

    synced_total = 0
    errors = 0

    for code in codes:
        try:
            df = router.fetch_financial_report(code)
            if df.empty:
                continue
            for _, row in df.iterrows():
                defaults = {}
                for field in [
                    "pe_ratio",
                    "pb_ratio",
                    "roe",
                    "revenue",
                    "net_profit",
                    "gross_margin",
                    "debt_ratio",
                ]:
                    val = row.get(field)
                    defaults[field] = Decimal(str(val)) if pd.notna(val) else None
                if pd.notna(row.get("report_date")):
                    defaults["report_date"] = row["report_date"]

                FinancialReport.objects.update_or_create(
                    stock_id=code,
                    period=str(row["period"]),
                    defaults=defaults,
                )
            synced_total += len(df)
        except Exception as e:
            logger.error(f"Failed to sync financial reports for {code}: {e}")
            errors += 1

    return {"synced": synced_total, "errors": errors}


@shared_task(name="quant.sync_news")
def sync_news(stock_code: str | None = None, limit: int = 50):
    """Sync news articles."""
    router = DataSourceRouter()
    articles = router.fetch_news(stock_code, limit=limit)

    created = 0
    for article in articles:
        _, was_created = NewsArticle.objects.get_or_create(
            title=article["title"],
            published_at=article["published_at"],
            defaults={
                "stock_id": stock_code,
                "content": article.get("content", ""),
                "source": article.get("source", ""),
                "url": article.get("url", ""),
            },
        )
        if was_created:
            created += 1

    return {"created": created, "total_fetched": len(articles)}


@shared_task(name="quant.validate_data")
def validate_data():
    """Daily data validation: check for gaps, anomalies."""
    issues = []
    today = date.today()

    # Check: stocks with no kline data in last 5 trading days
    threshold = today - timedelta(days=7)
    active_stocks = StockBasic.objects.filter(is_active=True).count()
    stocks_with_recent = (
        KlineData.objects.filter(date__gte=threshold)
        .values("stock")
        .distinct()
        .count()
    )

    if stocks_with_recent < active_stocks * 0.8:
        issues.append(
            f"Only {stocks_with_recent}/{active_stocks} stocks have recent kline data"
        )

    # Check: kline data with zero volume (suspicious)
    zero_volume = KlineData.objects.filter(date__gte=threshold, volume=0).count()
    if zero_volume > 0:
        issues.append(f"{zero_volume} kline records with zero volume in last week")

    if issues:
        logger.warning(f"Data validation issues: {issues}")
    else:
        logger.info("Data validation passed")

    return {
        "issues": issues,
        "active_stocks": active_stocks,
        "stocks_with_recent_data": stocks_with_recent,
    }


# ---------------------------------------------------------------------------
# Analysis pipeline tasks
# ---------------------------------------------------------------------------


@shared_task(name="quant.run_analysis_pipeline")
def run_analysis_pipeline(style: str = "swing"):
    """Run the full analysis pipeline for all active stocks.

    Steps:
    1. Get all active stocks
    2. For each stock, run MultiFactorScorer
    3. For each scored stock, generate TradingSignal
    4. Filter top picks (BUY signals sorted by score descending)
    5. Log and return results summary

    Args:
        style: Trading style string ("ultra_short", "swing", "mid_long")
    """
    from .analyzers import MultiFactorScorer, SignalGenerator, TradingStyle

    # Parse style string to enum
    style_map = {
        "ultra_short": TradingStyle.ULTRA_SHORT,
        "swing": TradingStyle.SWING,
        "mid_long": TradingStyle.MID_LONG,
    }
    trading_style = style_map.get(style, TradingStyle.SWING)

    scorer = MultiFactorScorer(style=trading_style)
    signal_gen = SignalGenerator()

    active_stocks = list(
        StockBasic.objects.filter(is_active=True).values_list("code", flat=True)
    )

    results = []
    errors = 0

    for code in active_stocks:
        try:
            score_result = scorer.score(code)
            signal = signal_gen.generate(code, score_result)
            results.append({
                "stock_code": code,
                "score": score_result["final_score"],
                "signal": score_result["signal"].value,
                "confidence": score_result["confidence"],
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "position_pct": signal.position_pct,
            })
        except Exception as e:
            logger.error(f"Analysis failed for {code}: {e}")
            errors += 1

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Filter top picks (BUY signals)
    buy_signals = [r for r in results if r["signal"] == "BUY"]
    sell_signals = [r for r in results if r["signal"] == "SELL"]

    logger.info(
        f"Analysis pipeline ({style}): "
        f"{len(results)} stocks analyzed, "
        f"{len(buy_signals)} BUY, {len(sell_signals)} SELL, "
        f"{errors} errors"
    )

    return {
        "style": style,
        "total_analyzed": len(results),
        "buy_count": len(buy_signals),
        "sell_count": len(sell_signals),
        "hold_count": len(results) - len(buy_signals) - len(sell_signals),
        "errors": errors,
        "top_picks": buy_signals[:10],  # Top 10 BUY signals
        "top_sells": sell_signals[:10],  # Top 10 SELL signals
    }


@shared_task(name="quant.analyze_single_stock")
def analyze_single_stock(stock_code: str, style: str = "swing"):
    """Run analysis for a single stock.

    Useful for on-demand analysis via API.
    """
    from .analyzers import MultiFactorScorer, SignalGenerator, TradingStyle

    style_map = {
        "ultra_short": TradingStyle.ULTRA_SHORT,
        "swing": TradingStyle.SWING,
        "mid_long": TradingStyle.MID_LONG,
    }
    trading_style = style_map.get(style, TradingStyle.SWING)

    scorer = MultiFactorScorer(style=trading_style)
    signal_gen = SignalGenerator()

    score_result = scorer.score(stock_code)
    signal = signal_gen.generate(stock_code, score_result)

    return {
        "stock_code": stock_code,
        "style": style,
        "score": score_result["final_score"],
        "signal": score_result["signal"].value,
        "confidence": score_result["confidence"],
        "explanation": score_result["explanation"],
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "position_pct": signal.position_pct,
        "risk_reward_ratio": signal.risk_reward_ratio,
        "component_scores": score_result["component_scores"],
    }
