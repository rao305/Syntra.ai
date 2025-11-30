"""Visualization service for rendering charts and graphs using matplotlib."""
import io
import base64
import uuid
from typing import List, Optional
from datetime import datetime
import logging

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

from app.services.collaborate.models import (
    VisualizationSpec,
    RenderedChart,
)

logger = logging.getLogger(__name__)

# Color palette for charts
COLORS = [
    '#1f77b4',  # blue
    '#ff7f0e',  # orange
    '#2ca02c',  # green
    '#d62728',  # red
    '#9467bd',  # purple
    '#8c564b',  # brown
    '#e377c2',  # pink
    '#7f7f7f',  # gray
    '#bcbd22',  # olive
    '#17becf',  # cyan
]


def get_color(index: int) -> str:
    """Get a color from the palette by index."""
    return COLORS[index % len(COLORS)]


async def render_chart(spec: VisualizationSpec, run_id: str) -> Optional[RenderedChart]:
    """
    Render a chart from a visualization spec.

    Returns RenderedChart with base64-encoded image data,
    or None if rendering fails.
    """
    try:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8f9fa')

        if not spec.data:
            logger.warning(f"No data provided for visualization {spec.id}")
            return None

        labels = spec.data.labels

        # Render based on chart type
        chart_type = spec.chart_type or "line"

        if chart_type == "line":
            _render_line_chart(ax, spec, labels)
        elif chart_type == "bar":
            _render_bar_chart(ax, spec, labels)
        elif chart_type == "stacked_bar":
            _render_stacked_bar_chart(ax, spec, labels)
        elif chart_type == "pie":
            _render_pie_chart(fig, spec, labels)
        elif chart_type == "area":
            _render_area_chart(ax, spec, labels)
        elif chart_type == "scatter":
            _render_scatter_chart(ax, spec, labels)
        else:
            logger.warning(f"Unknown chart type: {chart_type}")
            return None

        # Add title and labels
        if spec.title:
            ax.set_title(spec.title, fontsize=14, fontweight='bold', pad=20)

        if spec.x_axis_label and chart_type != "pie":
            ax.set_xlabel(spec.x_axis_label, fontsize=11)

        if spec.y_axis_label and chart_type != "pie":
            ax.set_ylabel(spec.y_axis_label, fontsize=11)

        # Add legend if there are multiple series
        if len(spec.data.series) > 1 and chart_type != "pie":
            ax.legend(loc='upper left', framealpha=0.9)

        # Format grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Tight layout
        plt.tight_layout()

        # Render to PNG bytes
        img_bytes = io.BytesIO()
        fig.savefig(img_bytes, format='png', dpi=100, bbox_inches='tight')
        img_bytes.seek(0)
        plt.close(fig)

        # Encode as base64 data URI
        b64_str = base64.b64encode(img_bytes.read()).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_str}"

        # Create RenderedChart object
        return RenderedChart(
            id=spec.id,
            url=data_uri,
            title=spec.title,
            alt=spec.description or f"{spec.title or 'Chart'} visualization",
            mime_type="image/png",
        )

    except Exception as e:
        logger.error(f"Failed to render chart {spec.id}: {str(e)}")
        return None


def _render_line_chart(ax, spec: VisualizationSpec, labels: List[str]) -> None:
    """Render a line chart."""
    for idx, series in enumerate(spec.data.series):
        ax.plot(
            labels,
            series.values,
            marker='o',
            label=series.name,
            linewidth=2.5,
            markersize=6,
            color=get_color(idx),
        )

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0)


def _render_bar_chart(ax, spec: VisualizationSpec, labels: List[str]) -> None:
    """Render a bar chart."""
    x = range(len(labels))
    bar_width = 0.8 / len(spec.data.series)

    for idx, series in enumerate(spec.data.series):
        offset = (idx - len(spec.data.series) / 2 + 0.5) * bar_width
        ax.bar(
            [i + offset for i in x],
            series.values,
            bar_width,
            label=series.name,
            color=get_color(idx),
            alpha=0.85,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0)


def _render_stacked_bar_chart(ax, spec: VisualizationSpec, labels: List[str]) -> None:
    """Render a stacked bar chart."""
    x = range(len(labels))
    bottom = [0] * len(labels)

    for idx, series in enumerate(spec.data.series):
        ax.bar(
            x,
            series.values,
            label=series.name,
            bottom=bottom,
            color=get_color(idx),
            alpha=0.85,
        )
        bottom = [bottom[i] + series.values[i] for i in range(len(labels))]

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0)


def _render_pie_chart(fig, spec: VisualizationSpec, labels: List[str]) -> None:
    """Render a pie chart."""
    ax = fig.add_subplot(111)

    # For pie, use first series or sum all series
    if spec.data.series:
        values = spec.data.series[0].values
    else:
        return

    colors = [get_color(i) for i in range(len(labels))]

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)

    ax.axis('equal')


def _render_area_chart(ax, spec: VisualizationSpec, labels: List[str]) -> None:
    """Render an area chart."""
    x = range(len(labels))
    bottom = None

    for idx, series in enumerate(spec.data.series):
        ax.fill_between(
            x,
            series.values,
            alpha=0.6,
            label=series.name,
            color=get_color(idx),
        )

    # Overlay lines for clarity
    for idx, series in enumerate(spec.data.series):
        ax.plot(
            x,
            series.values,
            linewidth=2,
            color=get_color(idx),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0)


def _render_scatter_chart(ax, spec: VisualizationSpec, labels: List[str]) -> None:
    """Render a scatter chart."""
    x = range(len(labels))

    for idx, series in enumerate(spec.data.series):
        ax.scatter(
            x,
            series.values,
            s=100,
            label=series.name,
            color=get_color(idx),
            alpha=0.7,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0)


async def render_visualizations(
    specs: List[VisualizationSpec],
    run_id: str,
) -> List[RenderedChart]:
    """
    Render a list of visualization specs into rendered charts.

    Args:
        specs: List of VisualizationSpec objects
        run_id: Run ID for logging/tracking

    Returns:
        List of RenderedChart objects (may contain fewer items if some failed)
    """
    rendered = []

    for spec in specs:
        try:
            chart = await render_chart(spec, run_id)
            if chart:
                rendered.append(chart)
        except Exception as e:
            logger.error(f"Failed to render visualization {spec.id}: {str(e)}")
            continue

    return rendered
