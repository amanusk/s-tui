"""Tests for urwid widget wrappers: ScalableBarGraph, LabeledBarGraphVector,
BarGraphVector, SummaryTextList, and ViListBox."""

import pytest
from unittest.mock import MagicMock
from collections import OrderedDict

import urwid

from s_tui.sturwid.complex_bar_graph import ScalableBarGraph, LabeledBarGraphVector
from s_tui.sturwid.bar_graph_vector import BarGraphVector
from s_tui.sturwid.summary_text_list import SummaryTextList
from s_tui.sturwid.ui_elements import ViListBox


# =====================================================================
# ScalableBarGraph
# =====================================================================

class TestScalableBarGraph:
    def test_init(self):
        """ScalableBarGraph can be constructed with segment colours."""
        g = ScalableBarGraph(["bg", "colA", "colB"])
        assert isinstance(g, urwid.BarGraph)

    def test_get_size_default(self):
        """Before rendering, size is (0, 0)."""
        g = ScalableBarGraph(["bg", "colA", "colB"])
        assert g.get_size() == (0, 0)

    def test_calculate_bar_widths_with_bar_width(self):
        """When bar_width is set, widths are uniform."""
        g = ScalableBarGraph(["bg", "colA", "colB"])
        g.set_bar_width(2)
        widths = g.calculate_bar_widths((10, 5), [[1], [2], [3]])
        assert widths == [2, 2, 2]

    def test_calculate_bar_widths_bar_width_clips(self):
        """Bars are clipped when they don't fit."""
        g = ScalableBarGraph(["bg", "colA", "colB"])
        g.set_bar_width(3)
        widths = g.calculate_bar_widths((7, 5), [[1], [2], [3], [4], [5]])
        # Only 7//3 = 2 bars fit
        assert len(widths) == 2

    def test_calculate_bar_widths_stretch(self):
        """When bar_width is None, bars stretch to fill space."""
        g = ScalableBarGraph(["bg", "colA", "colB"])
        g.set_bar_width(None)
        widths = g.calculate_bar_widths((10, 5), [[1], [2]])
        assert sum(widths) == 10

    def test_calculate_bar_widths_more_bars_than_cols(self):
        """When data bars >= maxcol, each bar is width 1."""
        g = ScalableBarGraph(["bg", "colA", "colB"])
        g.set_bar_width(None)
        widths = g.calculate_bar_widths((3, 5), [[1], [2], [3], [4]])
        assert widths == [1, 1, 1]


# =====================================================================
# LabeledBarGraphVector
# =====================================================================

class TestLabeledBarGraphVector:
    def _make(self, n_graphs=2, visible=None):
        """Helper to build a LabeledBarGraphVector."""
        graphs = [ScalableBarGraph(["bg", "a", "b"]) for _ in range(n_graphs)]
        if visible is None:
            visible = [True] * n_graphs
        return LabeledBarGraphVector(
            "Title", [f"sub{i}" for i in range(n_graphs)], [], graphs, visible
        )

    def test_init(self):
        """Construction succeeds with valid args."""
        v = self._make(2)
        assert isinstance(v, urwid.WidgetPlaceholder)

    def test_rejects_non_scalable_graph(self):
        """Constructor raises if graph is not ScalableBarGraph."""
        with pytest.raises(Exception, match="ScalableBarGraph"):
            LabeledBarGraphVector(
                "T", ["s"], [], [urwid.BarGraph(["bg", "a"])], [True]
            )

    def test_set_visible_graphs(self):
        """set_visible_graphs hides/shows sub-graphs."""
        v = self._make(2)
        v.set_visible_graphs([True, False])
        assert v.visible_graph_list == [True, False]

    def test_set_visible_graphs_all_false(self):
        """When all disabled, widget is empty Pile."""
        v = self._make(2)
        v.set_visible_graphs([False, False])
        assert isinstance(v.original_widget, urwid.Pile)

    def test_set_title(self):
        """set_title changes the title widget text."""
        v = self._make(1)
        v.set_title("New Title")
        # Should not crash

    def test_check_label_empty(self):
        """Empty y_label is valid."""
        v = self._make(1)
        assert v.check_label([]) is True

    def test_bar_graph_vector_stored(self):
        """bar_graph_vector is accessible."""
        v = self._make(3)
        assert len(v.bar_graph_vector) == 3


# =====================================================================
# BarGraphVector
# =====================================================================

class TestBarGraphVector:
    @pytest.fixture
    def mock_source(self):
        """Create a mock source for BarGraphVector."""
        src = MagicMock()
        src.get_source_name.return_value = "CPU Util"
        src.get_measurement_unit.return_value = "%"
        src.get_sensor_list.return_value = ["Avg", "Core 0"]
        src.get_is_available.return_value = True
        src.get_reading_list.return_value = [25.0, 30.0]
        src.get_top.return_value = 100
        src.get_edge_triggered.return_value = False
        return src

    def test_init(self, mock_source):
        """BarGraphVector initializes with source data."""
        bv = BarGraphVector(
            mock_source,
            ["colA", "colB", "smA", "smB"],
            graph_count=2,
            visible_graph_list=[True, True],
        )
        assert bv.graph_name == "CPU Util"
        assert bv.measurement_unit == "%"

    def test_append_latest_value(self):
        """append_latest_value rolls the window forward."""
        values = [1, 2, 3, 4, 5]
        result = BarGraphVector.append_latest_value(values, 6)
        assert result == [2, 3, 4, 5, 6]

    def test_max_samples(self):
        """MAX_SAMPLES is a reasonable constant."""
        assert BarGraphVector.MAX_SAMPLES > 0

    def test_graph_data_init(self, mock_source):
        """Each graph track starts with MAX_SAMPLES zeros."""
        bv = BarGraphVector(
            mock_source,
            ["colA", "colB", "smA", "smB"],
            graph_count=2,
            visible_graph_list=[True, True],
        )
        assert len(bv.graph_data) == 2
        assert len(bv.graph_data[0]) == BarGraphVector.MAX_SAMPLES
        assert all(v == 0 for v in bv.graph_data[0])

    def test_alert_colors_default(self, mock_source):
        """When no alert_colors given, falls back to regular_colors."""
        bv = BarGraphVector(
            mock_source,
            ["colA", "colB", "smA", "smB"],
            graph_count=1,
            visible_graph_list=[True],
        )
        assert bv.alert_colors == bv.regular_colors

    def test_alert_colors_custom(self, mock_source):
        """Custom alert_colors override defaults."""
        alert = ["alertA", "alertB", "alertSmA", "alertSmB"]
        bv = BarGraphVector(
            mock_source,
            ["colA", "colB", "smA", "smB"],
            graph_count=1,
            visible_graph_list=[True],
            alert_colors=alert,
        )
        assert bv.alert_colors == alert


# =====================================================================
# SummaryTextList
# =====================================================================

class TestSummaryTextList:
    @pytest.fixture
    def mock_source(self):
        src = MagicMock()
        src.get_source_name.return_value = "CPU Util"
        src.get_is_available.return_value = True
        summary = OrderedDict([
            ("CPU Util", ""),
            ("Avg", "25.0%"),
            ("Core 0", "30.0%"),
        ])
        src.get_summary.return_value = summary
        return src

    def test_init(self, mock_source):
        """SummaryTextList initializes with source and visibility."""
        stl = SummaryTextList(mock_source, [True, True])
        assert stl.source is mock_source

    def test_get_text_item_list(self, mock_source):
        """get_text_item_list returns urwid column widgets."""
        stl = SummaryTextList(mock_source, [True, True])
        items = stl.get_text_item_list()
        assert len(items) == 3  # title + 2 sensors (all visible)

    def test_hidden_sensors(self, mock_source):
        """Hidden sensors are excluded from get_text_item_list."""
        stl = SummaryTextList(mock_source, [True, False])
        items = stl.get_text_item_list()
        # Title + 1 visible sensor
        assert len(items) == 2

    def test_all_hidden_hides_title(self, mock_source):
        """When all sensors hidden, title is hidden too."""
        stl = SummaryTextList(mock_source, [False, False])
        items = stl.get_text_item_list()
        assert len(items) == 0

    def test_update(self, mock_source):
        """update() refreshes text values from source."""
        stl = SummaryTextList(mock_source, [True, True])
        stl.get_text_item_list()  # populates summary_text_items

        # Change source values
        new_summary = OrderedDict([
            ("CPU Util", ""),
            ("Avg", "50.0%"),
            ("Core 0", "60.0%"),
        ])
        mock_source.get_summary.return_value = new_summary
        stl.update()

        # Text widgets should be updated
        assert stl.summary_text_items["Avg"].get_text()[0] == "50.0%"

    def test_update_visibility(self, mock_source):
        """update_visibility changes which sensors are shown."""
        stl = SummaryTextList(mock_source, [True, True])
        stl.update_visibility([False, True])
        keys = list(stl.visible_summaries.keys())
        # Title visible if any visible
        assert stl.visible_summaries[keys[0]] is True
        assert stl.visible_summaries[keys[1]] is False
        assert stl.visible_summaries[keys[2]] is True

    def test_get_is_available(self, mock_source):
        """get_is_available delegates to source."""
        stl = SummaryTextList(mock_source, [True])
        assert stl.get_is_available() is True


# =====================================================================
# ViListBox
# =====================================================================

class TestViListBox:
    def _make(self):
        body = urwid.SimpleFocusListWalker([urwid.Text("line1"), urwid.Text("line2")])
        return ViListBox(body)

    def test_vi_j_maps_to_down(self):
        """'j' key maps to 'down'."""
        lb = self._make()
        result = lb.keypress((10, 10), "j")
        # If handled, returns None; if passed through, returns the remapped key
        # The key should be remapped but may not be fully consumed
        assert result is None or result == "down"

    def test_vi_k_maps_to_up(self):
        """'k' key maps to 'up'."""
        lb = self._make()
        # Focus on second item first
        lb.set_focus(1)
        result = lb.keypress((10, 10), "k")
        assert result is None or result == "up"

    def test_vi_h_maps_to_left(self):
        """'h' key maps to 'left'."""
        lb = self._make()
        result = lb.keypress((10, 10), "h")
        # left may not be consumed by a simple list
        assert result in (None, "left")

    def test_vi_l_maps_to_right(self):
        """'l' key maps to 'right'."""
        lb = self._make()
        result = lb.keypress((10, 10), "l")
        assert result in (None, "right")

    def test_q_passthrough(self):
        """'q' key passes through as 'q'."""
        lb = self._make()
        result = lb.keypress((10, 10), "q")
        assert result == "q"

    def test_normal_key_passthrough(self):
        """Non-vi keys pass through unchanged."""
        lb = self._make()
        result = lb.keypress((10, 10), "a")
        assert result == "a"
