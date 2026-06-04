"""Signal effectiveness — statistical correlation vs forward cotton prices (PI10 Track E)."""

from backend.app.services.research.signal_effectiveness.analysis import (
    SignalEffectivenessResult,
    run_signal_effectiveness_analysis,
)
from backend.app.services.research.signal_effectiveness.report import (
    render_signal_effectiveness_report_markdown,
)

__all__ = [
    "SignalEffectivenessResult",
    "render_signal_effectiveness_report_markdown",
    "run_signal_effectiveness_analysis",
]
