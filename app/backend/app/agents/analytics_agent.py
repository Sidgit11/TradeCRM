"""Analytics Agent — Campaign Performance Analyst.

Summarizes campaign performance and produces actionable insights.
"""
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger("agents.analytics")


class AnalyticsAgent:
    """Analyzes campaign performance and generates insights."""

    TIMEOUT = 60  # seconds

    async def analyze_campaign(
        self,
        campaign_name: str,
        stats: Dict[str, int],
        step_stats: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze campaign performance and generate a summary.

        Args:
            campaign_name: Name of the campaign
            stats: {total_sent, delivered, opened, clicked, replied, failed, bounced}
            step_stats: Per-step breakdown [{step_number, channel, sent, delivered, replied}]

        Returns:
            {
                "summary": str,
                "metrics": dict,
                "recommendations": list[str],
                "health": "good" | "average" | "poor",
            }
        """
        logger.info("Analyzing campaign: %s", campaign_name)

        total = stats.get("total_sent", 0)
        delivered = stats.get("delivered", 0)
        opened = stats.get("opened", 0)
        replied = stats.get("replied", 0)
        failed = stats.get("failed", 0)
        bounced = stats.get("bounced", 0)

        # Calculate rates
        delivery_rate = (delivered / total * 100) if total > 0 else 0
        open_rate = (opened / delivered * 100) if delivered > 0 else 0
        reply_rate = (replied / delivered * 100) if delivered > 0 else 0
        bounce_rate = (bounced / total * 100) if total > 0 else 0

        metrics = {
            "total_sent": total,
            "delivered": delivered,
            "delivery_rate": round(delivery_rate, 1),
            "opened": opened,
            "open_rate": round(open_rate, 1),
            "replied": replied,
            "reply_rate": round(reply_rate, 1),
            "failed": failed,
            "bounced": bounced,
            "bounce_rate": round(bounce_rate, 1),
        }

        # Generate recommendations
        recommendations = []
        if bounce_rate > 5:
            recommendations.append("High bounce rate detected. Review and clean contact email addresses.")
        if open_rate < 20 and total > 10:
            recommendations.append("Low open rate. Consider testing different subject lines.")
        if reply_rate < 5 and total > 20:
            recommendations.append("Low reply rate. Try adding more personalization or adjusting the call to action.")
        if delivery_rate < 90 and total > 10:
            recommendations.append("Delivery issues detected. Check sender reputation and authentication records.")

        # Analyze step performance if available
        if step_stats:
            best_step = max(step_stats, key=lambda s: s.get("replied", 0))
            if best_step.get("replied", 0) > 0:
                recommendations.append(
                    f"Step {best_step['step_number']} ({best_step.get('channel', 'unknown')}) "
                    f"has the highest reply rate. Consider using this channel earlier in the sequence."
                )

        # Determine health
        if reply_rate >= 10:
            health = "good"
        elif reply_rate >= 3:
            health = "average"
        else:
            health = "poor"

        # Generate summary
        summary = (
            f"Campaign '{campaign_name}' sent {total} messages with "
            f"{delivery_rate:.0f}% delivery rate. "
            f"Open rate: {open_rate:.0f}%, Reply rate: {reply_rate:.1f}%. "
        )
        if replied > 0:
            summary += f"{replied} contacts replied."
        else:
            summary += "No replies received yet."

        result = {
            "summary": summary,
            "metrics": metrics,
            "recommendations": recommendations,
            "health": health,
        }

        logger.info("Campaign analysis: health=%s reply_rate=%.1f%%", health, reply_rate)
        return result


analytics_agent = AnalyticsAgent()
