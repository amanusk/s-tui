"""Tests for issue #258: graph/summary update errors must not crash the app.

`GraphView.update_displayed_information()` guards `source.update()` against any
recoverable exception, but the graph and summary rendering loops only caught
`IndexError`.  Any other exception raised while a widget redraws terminated the
whole application instead of being logged and skipped.
"""

from unittest.mock import MagicMock

import pytest

from s_tui.s_tui import GraphView


def make_view(graph=None, summary=None, debug=False):
    """Build the minimal attribute set update_displayed_information() touches."""
    view = MagicMock()
    view.controller.sources = []
    view.controller.args.debug = debug
    view.controller.args.debug_run = False
    view.controller.stress_controller.get_current_mode.return_value = "Monitor"
    view.source_update_errors = {}
    view.visible_graphs = {"CPU Util": graph} if graph is not None else {}
    view.visible_summaries = {"CPU Util": summary} if summary is not None else {}
    return view


class TestGraphSummaryUpdateErrors:
    @pytest.mark.parametrize(
        "error", [TypeError("bad shape"), ValueError("bad value"), OSError("gone")]
    )
    def test_graph_update_error_does_not_propagate(self, error):
        """A non-IndexError from graph.update() must not reach the event loop."""
        graph = MagicMock()
        graph.update.side_effect = error
        view = make_view(graph=graph)

        GraphView.update_displayed_information(view)

        assert graph.update.called

    @pytest.mark.parametrize(
        "error", [TypeError("bad shape"), ValueError("bad value"), OSError("gone")]
    )
    def test_summary_update_error_does_not_propagate(self, error):
        """A non-IndexError from summary.update() must not reach the event loop."""
        summary = MagicMock()
        summary.update.side_effect = error
        view = make_view(summary=summary)

        GraphView.update_displayed_information(view)

        assert summary.update.called

    def test_graph_update_error_raises_in_debug_mode(self):
        """Debug mode still surfaces unexpected widget errors for diagnosis."""
        graph = MagicMock()
        graph.update.side_effect = TypeError("bad shape")
        view = make_view(graph=graph, debug=True)

        with pytest.raises(TypeError):
            GraphView.update_displayed_information(view)
