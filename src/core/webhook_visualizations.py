# =============================================================================
# QuranBot - Rich Webhook Visualizations
# =============================================================================
# This module provides rich visual elements for Discord webhook embeds including
# progress bars, charts, graphs, and other visual representations using Unicode
# characters and Discord's formatting capabilities.
# =============================================================================

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import math


class ChartType(Enum):
    """Types of charts available for visualization."""
    BAR = "bar"
    LINE = "line"
    PROGRESS = "progress"
    CIRCULAR = "circular"
    HEATMAP = "heatmap"
    SPARKLINE = "sparkline"
    GAUGE = "gauge"
    COMPARISON = "comparison"


@dataclass
class ChartColors:
    """Color schemes for different chart types."""
    # Discord color codes
    GREEN = 0x00FF00
    YELLOW = 0xFFFF00
    RED = 0xFF0000
    BLUE = 0x0099FF
    PURPLE = 0x9B59B6
    ORANGE = 0xFF8C00
    PINK = 0xFF69B4
    TEAL = 0x00CED1
    GRAY = 0x95A5A6
    
    # Gradient colors for progress
    GRADIENT_EXCELLENT = 0x00FF00  # Green
    GRADIENT_GOOD = 0x7FFF00      # Chartreuse
    GRADIENT_AVERAGE = 0xFFFF00   # Yellow
    GRADIENT_POOR = 0xFF8C00      # Dark Orange
    GRADIENT_CRITICAL = 0xFF0000  # Red


class VisualizationBuilder:
    """Builder for creating rich visualizations in Discord embeds."""
    
    # Unicode characters for visualizations
    BLOCKS = {
        "full": "█",
        "seven_eighths": "▇",
        "three_quarters": "▆",
        "five_eighths": "▅",
        "half": "▄",
        "three_eighths": "▃",
        "quarter": "▂",
        "eighth": "▁",
        "empty": "░",
    }
    
    CIRCLES = {
        "full": "●",
        "three_quarters": "◕",
        "half": "◐",
        "quarter": "◔",
        "empty": "○",
    }
    
    ARROWS = {
        "up": "↑",
        "down": "↓",
        "right": "→",
        "left": "←",
        "up_right": "↗",
        "up_left": "↖",
        "down_right": "↘",
        "down_left": "↙",
        "double_up": "⇈",
        "double_down": "⇊",
    }
    
    SYMBOLS = {
        "check": "✅",
        "cross": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "star": "⭐",
        "fire": "🔥",
        "lightning": "⚡",
        "trophy": "🏆",
        "medal": "🥇",
        "heart": "❤️",
        "diamond": "💎",
        "clock": "🕐",
        "calendar": "📅",
        "chart": "📊",
        "speaker": "🔊",
        "book": "📖",
        "pray": "🤲",
        "mosque": "🕌",
        "crescent": "☪️",
    }
    
    @staticmethod
    def create_progress_bar(
        value: float,
        max_value: float,
        length: int = 20,
        show_percentage: bool = True,
        show_values: bool = False,
        filled_char: str = None,
        empty_char: str = None,
        include_emoji: bool = True
    ) -> str:
        """
        Create a progress bar visualization.
        
        Args:
            value: Current value
            max_value: Maximum value
            length: Length of the progress bar in characters
            show_percentage: Show percentage after the bar
            show_values: Show actual values (e.g., 50/100)
            filled_char: Character for filled portion
            empty_char: Character for empty portion
            include_emoji: Include emoji indicators
            
        Returns:
            Formatted progress bar string
        """
        if max_value <= 0:
            return "Invalid max value"
            
        # Calculate percentage
        percentage = min(100, max(0, (value / max_value) * 100))
        filled_length = int(length * percentage / 100)
        
        # Default characters
        if not filled_char:
            filled_char = VisualizationBuilder.BLOCKS["full"]
        if not empty_char:
            empty_char = VisualizationBuilder.BLOCKS["empty"]
        
        # Build the bar
        bar = filled_char * filled_length + empty_char * (length - filled_length)
        
        # Add percentage/values
        result = f"`{bar}`"
        
        if show_percentage and show_values:
            result += f" **{percentage:.1f}%** ({value}/{max_value})"
        elif show_percentage:
            result += f" **{percentage:.1f}%**"
        elif show_values:
            result += f" **{value}/{max_value}**"
        
        # Add emoji indicator
        if include_emoji:
            if percentage >= 90:
                result += " 🟢"
            elif percentage >= 70:
                result += " 🟡"
            elif percentage >= 50:
                result += " 🟠"
            else:
                result += " 🔴"
        
        return result
    
    @staticmethod
    def create_multi_progress_bars(
        items: List[Dict[str, Any]],
        max_value: float = None,
        bar_length: int = 15
    ) -> List[str]:
        """
        Create multiple progress bars for comparison.
        
        Args:
            items: List of dicts with 'name', 'value', and optional 'emoji'
            max_value: Maximum value for all bars (auto-calculated if None)
            bar_length: Length of each progress bar
            
        Returns:
            List of formatted progress bar strings
        """
        if not items:
            return []
        
        # Auto-calculate max value if not provided
        if max_value is None:
            max_value = max(item.get('value', 0) for item in items)
        
        if max_value <= 0:
            return ["No data available"]
        
        results = []
        for item in items:
            name = item.get('name', 'Unknown')
            value = item.get('value', 0)
            emoji = item.get('emoji', '')
            
            bar = VisualizationBuilder.create_progress_bar(
                value, max_value, bar_length, 
                show_percentage=True, 
                show_values=False,
                include_emoji=False
            )
            
            line = f"{emoji} **{name}**: {bar} ({value})"
            results.append(line)
        
        return results
    
    @staticmethod
    def create_bar_chart(
        data: List[Tuple[str, float]],
        max_height: int = 8,
        show_values: bool = True,
        horizontal: bool = False
    ) -> str:
        """
        Create a bar chart visualization.
        
        Args:
            data: List of (label, value) tuples
            max_height: Maximum height of bars in characters
            show_values: Show values on bars
            horizontal: Create horizontal bars instead of vertical
            
        Returns:
            Formatted bar chart string
        """
        if not data:
            return "No data available"
        
        max_value = max(value for _, value in data)
        if max_value <= 0:
            return "Invalid data"
        
        if horizontal:
            # Horizontal bar chart
            lines = []
            max_label_length = max(len(label) for label, _ in data)
            
            for label, value in data:
                bar_length = int((value / max_value) * 15)
                bar = VisualizationBuilder.BLOCKS["full"] * bar_length
                bar += VisualizationBuilder.BLOCKS["empty"] * (15 - bar_length)
                
                padded_label = label.ljust(max_label_length)
                value_str = f" {value}" if show_values else ""
                lines.append(f"`{padded_label}` `{bar}`{value_str}")
            
            return "\n".join(lines)
        else:
            # Vertical bar chart (simplified for Discord)
            chart_lines = []
            
            # Create bars
            bars = []
            for label, value in data:
                height = int((value / max_value) * max_height)
                bars.append((label[:3], height, value))  # Truncate labels
            
            # Build chart from top to bottom
            for level in range(max_height, 0, -1):
                line = ""
                for _, height, _ in bars:
                    if height >= level:
                        line += VisualizationBuilder.BLOCKS["full"] + " "
                    else:
                        line += "  "
                chart_lines.append(f"`{line}`")
            
            # Add labels
            label_line = "`"
            for label, _, _ in bars:
                label_line += label[:3].ljust(2)
            label_line += "`"
            chart_lines.append(label_line)
            
            # Add values if requested
            if show_values:
                value_line = "`"
                for _, _, value in bars:
                    value_line += str(int(value)).ljust(2)
                value_line += "`"
                chart_lines.append(value_line)
            
            return "\n".join(chart_lines)
    
    @staticmethod
    def create_sparkline(
        values: List[float],
        width: int = 20,
        show_trend: bool = True
    ) -> str:
        """
        Create a sparkline (mini line chart) visualization.
        
        Args:
            values: List of values to plot
            width: Width of the sparkline
            show_trend: Show trend arrow
            
        Returns:
            Formatted sparkline string
        """
        if not values or len(values) < 2:
            return "Insufficient data"
        
        # Normalize values to 0-7 range (for 8 spark levels)
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val
        
        if range_val == 0:
            # All values are the same
            sparkline = "▄" * min(len(values), width)
        else:
            # Map values to spark characters
            sparks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
            sparkline = ""
            
            # Sample values if too many
            if len(values) > width:
                step = len(values) / width
                sampled_values = [values[int(i * step)] for i in range(width)]
            else:
                sampled_values = values
            
            for val in sampled_values:
                normalized = (val - min_val) / range_val
                index = min(7, int(normalized * 7))
                sparkline += sparks[index]
        
        result = f"`{sparkline}`"
        
        # Add trend indicator
        if show_trend and len(values) >= 2:
            trend = values[-1] - values[0]
            if trend > 0:
                result += f" {VisualizationBuilder.ARROWS['up']} +{trend:.1f}"
            elif trend < 0:
                result += f" {VisualizationBuilder.ARROWS['down']} {trend:.1f}"
            else:
                result += f" {VisualizationBuilder.ARROWS['right']} 0.0"
        
        return result
    
    @staticmethod
    def create_circular_progress(
        value: float,
        max_value: float,
        size: str = "medium"
    ) -> str:
        """
        Create a circular progress indicator.
        
        Args:
            value: Current value
            max_value: Maximum value
            size: Size of the indicator ("small", "medium", "large")
            
        Returns:
            Formatted circular progress string
        """
        if max_value <= 0:
            return "Invalid max value"
        
        percentage = min(100, max(0, (value / max_value) * 100))
        
        # Choose appropriate circle based on percentage
        if percentage >= 87.5:
            circle = VisualizationBuilder.CIRCLES["full"]
        elif percentage >= 62.5:
            circle = VisualizationBuilder.CIRCLES["three_quarters"]
        elif percentage >= 37.5:
            circle = VisualizationBuilder.CIRCLES["half"]
        elif percentage >= 12.5:
            circle = VisualizationBuilder.CIRCLES["quarter"]
        else:
            circle = VisualizationBuilder.CIRCLES["empty"]
        
        # Format based on size
        if size == "small":
            return f"{circle} {percentage:.0f}%"
        elif size == "large":
            return f"# {circle} {percentage:.1f}%\n**{value}/{max_value}**"
        else:  # medium
            return f"**{circle} {percentage:.1f}%**"
    
    @staticmethod
    def create_gauge(
        value: float,
        min_value: float,
        max_value: float,
        thresholds: List[Tuple[float, str]] = None
    ) -> str:
        """
        Create a gauge visualization with thresholds.
        
        Args:
            value: Current value
            min_value: Minimum value
            max_value: Maximum value
            thresholds: List of (threshold_value, emoji) tuples
            
        Returns:
            Formatted gauge string
        """
        if max_value <= min_value:
            return "Invalid range"
        
        # Normalize value to 0-100
        percentage = ((value - min_value) / (max_value - min_value)) * 100
        percentage = min(100, max(0, percentage))
        
        # Default thresholds if not provided
        if not thresholds:
            thresholds = [
                (80, "🟢"),
                (60, "🟡"),
                (40, "🟠"),
                (20, "🔴"),
                (0, "⚫"),
            ]
        
        # Find appropriate emoji
        emoji = "⚫"
        for threshold, threshold_emoji in sorted(thresholds, reverse=True):
            if percentage >= threshold:
                emoji = threshold_emoji
                break
        
        # Create gauge visualization
        gauge_length = 10
        filled = int(gauge_length * percentage / 100)
        
        gauge = "["
        gauge += "=" * filled
        gauge += ">" if filled < gauge_length else ""
        gauge += " " * (gauge_length - filled - (1 if filled < gauge_length else 0))
        gauge += "]"
        
        return f"{emoji} `{gauge}` **{value:.1f}** ({percentage:.0f}%)"
    
    @staticmethod
    def create_comparison_bars(
        current: float,
        previous: float,
        label: str = "Change",
        show_percentage: bool = True
    ) -> str:
        """
        Create a comparison visualization showing change between two values.
        
        Args:
            current: Current value
            previous: Previous value
            label: Label for the comparison
            show_percentage: Show percentage change
            
        Returns:
            Formatted comparison string
        """
        if previous == 0:
            change_percent = 100 if current > 0 else 0
        else:
            change_percent = ((current - previous) / previous) * 100
        
        # Determine arrow and color
        if change_percent > 0:
            arrow = VisualizationBuilder.ARROWS["up"]
            indicator = "🟢"
        elif change_percent < 0:
            arrow = VisualizationBuilder.ARROWS["down"]
            indicator = "🔴"
        else:
            arrow = VisualizationBuilder.ARROWS["right"]
            indicator = "🟡"
        
        # Format the change
        change_str = f"{arrow} {abs(change_percent):.1f}%" if show_percentage else f"{arrow} {current - previous:+.1f}"
        
        # Create mini bars for visual comparison
        max_val = max(current, previous)
        if max_val > 0:
            current_bar = VisualizationBuilder.create_progress_bar(
                current, max_val, 8, show_percentage=False, include_emoji=False
            )
            previous_bar = VisualizationBuilder.create_progress_bar(
                previous, max_val, 8, show_percentage=False, include_emoji=False
            )
            
            return f"**{label}**: {change_str} {indicator}\nNow: {current_bar} {current:.1f}\nWas: {previous_bar} {previous:.1f}"
        else:
            return f"**{label}**: {change_str} {indicator}"
    
    @staticmethod
    def create_activity_heatmap(
        data: Dict[int, int],
        hours: int = 24,
        show_labels: bool = True
    ) -> str:
        """
        Create an activity heatmap for the last N hours.
        
        Args:
            data: Dict mapping hour to activity count
            hours: Number of hours to show
            show_labels: Show hour labels
            
        Returns:
            Formatted heatmap string
        """
        if not data:
            return "No activity data"
        
        max_activity = max(data.values()) if data else 1
        
        # Heat levels
        heat_chars = ["⬜", "🟦", "🟩", "🟨", "🟧", "🟥"]
        
        heatmap = ""
        current_hour = datetime.now().hour
        
        for i in range(hours):
            hour = (current_hour - hours + i + 1) % 24
            activity = data.get(hour, 0)
            
            # Map activity to heat level
            if max_activity > 0:
                heat_level = int((activity / max_activity) * (len(heat_chars) - 1))
            else:
                heat_level = 0
            
            heatmap += heat_chars[heat_level]
            
            # Add spacing every 6 hours
            if (i + 1) % 6 == 0 and i < hours - 1:
                heatmap += " "
        
        result = heatmap
        
        if show_labels:
            result = f"**Activity (Last {hours}h)**\n{heatmap}\n`00    06    12    18    24`"
        
        return result
    
    @staticmethod
    def format_number_with_trend(
        current: float,
        previous: float = None,
        decimals: int = 1,
        prefix: str = "",
        suffix: str = ""
    ) -> str:
        """
        Format a number with optional trend indicator.
        
        Args:
            current: Current value
            previous: Previous value for comparison
            decimals: Number of decimal places
            prefix: Prefix (e.g., "$")
            suffix: Suffix (e.g., "ms")
            
        Returns:
            Formatted number string with trend
        """
        formatted = f"{prefix}{current:.{decimals}f}{suffix}"
        
        if previous is not None:
            if current > previous:
                trend = VisualizationBuilder.ARROWS["up"]
                color = "🔴" if suffix in ["ms", "s", "errors"] else "🟢"
            elif current < previous:
                trend = VisualizationBuilder.ARROWS["down"]
                color = "🟢" if suffix in ["ms", "s", "errors"] else "🔴"
            else:
                trend = VisualizationBuilder.ARROWS["right"]
                color = "🟡"
            
            return f"**{formatted}** {trend} {color}"
        
        return f"**{formatted}**"
    
    @staticmethod
    def create_stats_card(
        title: str,
        stats: List[Dict[str, Any]],
        use_columns: bool = True
    ) -> Dict[str, Any]:
        """
        Create a formatted stats card for embedding.
        
        Args:
            title: Card title
            stats: List of stat dictionaries with 'label', 'value', 'trend', 'emoji'
            use_columns: Format stats in columns
            
        Returns:
            Dict suitable for Discord embed field
        """
        lines = []
        
        for stat in stats:
            label = stat.get('label', 'Unknown')
            value = stat.get('value', 0)
            trend = stat.get('trend', None)
            emoji = stat.get('emoji', '')
            
            # Format the stat line
            if trend is not None:
                formatted_value = VisualizationBuilder.format_number_with_trend(
                    value, trend
                )
            else:
                formatted_value = f"**{value}**"
            
            line = f"{emoji} {label}: {formatted_value}"
            lines.append(line)
        
        # Format for columns or list
        if use_columns and len(lines) > 1:
            # Split into two columns
            mid = (len(lines) + 1) // 2
            left_column = lines[:mid]
            right_column = lines[mid:]
            
            # Pad shorter column
            while len(right_column) < len(left_column):
                right_column.append("")
            
            content = ""
            for left, right in zip(left_column, right_column):
                if right:
                    content += f"{left}\n{right}\n"
                else:
                    content += f"{left}\n"
        else:
            content = "\n".join(lines)
        
        return {
            "name": title,
            "value": content,
            "inline": False
        }


# Convenience functions for quick visualizations
def quick_progress(label: str, current: float, total: float) -> str:
    """Quick helper to create a labeled progress bar."""
    bar = VisualizationBuilder.create_progress_bar(current, total)
    return f"**{label}**: {bar}"


def quick_sparkline(label: str, values: List[float]) -> str:
    """Quick helper to create a labeled sparkline."""
    spark = VisualizationBuilder.create_sparkline(values)
    return f"**{label}**: {spark}"


def quick_gauge(label: str, value: float, min_val: float = 0, max_val: float = 100) -> str:
    """Quick helper to create a labeled gauge."""
    gauge = VisualizationBuilder.create_gauge(value, min_val, max_val)
    return f"**{label}**: {gauge}"