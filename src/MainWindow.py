import gi
from widgets.BulbSelectionWidget import BulbSelectionWidget

gi.require_version('Gtk', '3.0')

from BulbWrapper import BulbWrapper, ColorModes
from constants import *
from utils.color_utils import parse_rgb
from utils.widget_utils import drop_scroll_event

from gi.repository import Gtk, Gio
from gi.overrides.Gdk import RGBA


# TODO add predefined options


# noinspection PyArgumentList
class MainWindow(Gtk.ApplicationWindow):
    bulbs_selection_button = NotImplemented

    def __init__(self, *args, **kwargs):
        Gtk.Window.__init__(self, *args, **kwargs)

        self.set_default_size(500, 600)
        self.set_resizable(True)

        self.header_bar = self.init_header_bar()

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.set_vexpand(True)
        self.add(self.box)

        self.spinner = Gtk.Spinner()

        self.discovered_bulbs = []
        self.bulb_wrapper: BulbWrapper = None

        self.no_result_box = None
        self.control_box = None
        self.loading = False

        self.start_discovery()

    # noinspection PyAttributeOutsideInit
    def init_control_layout(self):
        control_box_container = Gtk.VBox()
        control_box = Gtk.ListBox()
        control_box.set_selection_mode(Gtk.SelectionMode.NONE)

        self.row_info = BulbInfoRow()
        control_box_container.pack_start(self.row_info, False, False, 0)

        row = BulbOptionRow()
        self.power_switch = Gtk.Switch()
        self.power_switch.props.valign = Gtk.Align.CENTER
        self.power_switch.connect('state-set', self.toggle_bulb)
        row.set_content(Gtk.Label(label="Power", xalign=0), self.power_switch, control_expand=False)
        control_box.add(row)

        row2 = BulbOptionRow()
        self.brightness_slider = Gtk.Scale.new_with_range(orientation=Gtk.Orientation.HORIZONTAL, min=1, max=100, step=1)
        self.brightness_slider.connect("button-release-event", self.change_brightness)
        self.brightness_slider.connect("scroll-event", drop_scroll_event)
        row2.set_content(Gtk.Label(label="Brightness", xalign=0), self.brightness_slider)
        control_box.add(row2)

        row3 = BulbOptionRow()
        self.delay_spin_button = Gtk.SpinButton.new_with_range(min=0, max=60, step=1)
        self.delay_spin_button.connect('value-changed', self.change_delay_off)
        self.delay_spin_button.connect("scroll-event", drop_scroll_event)
        row3.set_content(Gtk.Label(label="Delay off (minutes)", xalign=0), self.delay_spin_button, control_expand=False)
        control_box.add(row3)

        if self.bulb_wrapper.bulb_status.color_mode == ColorModes.COLOR_MODE:
            row4 = BulbOptionRow()
            self.color_button = Gtk.ColorButton.new_with_rgba(rgba=RGBA())
            self.color_button.connect('color-set', self.change_color)
            row4.set_content(Gtk.Label(label="Color", xalign=0), self.color_button, control_expand=False)
            control_box.add(row4)

        # Make the control box scrollable
        control_box_container.pack_start(control_box, True, True, 0)
        scrollable_win = Gtk.ScrolledWindow()
        scrollable_win.add_with_viewport(control_box_container)
        self.control_box = scrollable_win

        # noinspection PyUnusedLocal

    def toggle_bulb(self, widget, status):
        self.bulb_wrapper.toggle(status=status, on_complete=self.update_status_on_complete)

    def show_loading(self, loading, control_only=False):
        if loading:
            if self.loading:
                return False
            if not control_only:
                self.bulbs_selection_button.set_sensitive(False)
            if self.control_box:
                self.box.remove(self.control_box)
            if self.no_result_box is not None:
                self.box.remove(self.no_result_box)
            self.spinner.start()
            self.box.pack_start(self.spinner, True, True, 150)
            self.box.show_all()
        else:
            self.spinner.stop()
            self.box.remove(self.spinner)
        self.loading = loading
        return True

    # noinspection PyUnusedLocal
    def start_discovery(self, widget=None):
        if self.show_loading(True):
            BulbWrapper.discovery_bulbs(on_complete=self.discovered)

    def discovered(self, wrappers):
        self.discovered_bulbs = wrappers or []

        self.show_loading(False)

        self.bulbs_selection_button.fill_popover(bulbs=self.discovered_bulbs, listener=self.on_bulb_selected)

        if len(self.discovered_bulbs) == 0:
            self.show_no_result()
            self.box.show_all()

    def on_bulb_selected(self, bulb_display_text):
        for bw in self.discovered_bulbs:
            if bw.get_bulb_display_text() == bulb_display_text:
                if self.bulb_wrapper != bw:
                    self.bulb_wrapper = bw
                    self.init_control_layout()

        self.show_loading(True, control_only=True)
        self.bulb_wrapper.update_status(on_complete=self.bulb_connected)

    def bulb_connected(self):
        self.update_status_on_complete()
        self.show_loading(False, control_only=True)
        if not self.control_box.get_parent():
            self.box.pack_start(self.control_box, True, True, 0)
            self.show_all()

    # noinspection PyUnusedLocal
    def change_brightness(self, widget, event):
        bright = self.brightness_slider.get_value()
        self.bulb_wrapper.change_brightness(bright, self.update_status_on_complete)

    # noinspection PyTypeChecker,PyUnusedLocal
    def change_color(self, widget):
        self.bulb_wrapper.change_color(self.color_button.get_rgba(), self.update_status_on_complete)

    # noinspection PyUnusedLocal
    def change_delay_off(self, widget):
        self.bulb_wrapper.change_delay_off(delay=self.delay_spin_button.get_value(), on_complete=self.update_status_on_complete)

    def update_status(self):
        self.bulb_wrapper.update_status(self.update_status_on_complete)

    def update_status_on_complete(self):
        self.row_info.update_content(self.bulb_wrapper)
        self.power_switch.set_active(self.bulb_wrapper.bulb_status.power == 'on')
        self.brightness_slider.set_value(self.bulb_wrapper.bulb_status.bright)
        self.delay_spin_button.set_value(self.bulb_wrapper.bulb_status.delay_off)

        if self.bulb_wrapper.bulb_status.color_mode == ColorModes.COLOR_MODE:
            if self.bulb_wrapper.bulb_status.rgb:
                self.color_button.set_rgba(parse_rgb(self.bulb_wrapper.bulb_status.rgb))
            else:
                self.color_button.set_rgba(RGBA())

        self.show_all()

    def show_no_result(self):
        self.no_result_box = Gtk.VBox(homogeneous=False)

        pixbuf = Gtk.IconTheme.get_default().load_icon('computer-fail-symbolic', 64, 0)

        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        label = Gtk.Label(label='No bulb found')
        button = Gtk.Button(label='Retry')
        button.connect("clicked", self.start_discovery)
        button.set_hexpand(False)
        button.set_halign(Gtk.Align.CENTER)
        self.no_result_box.pack_start(icon, False, True, 0)
        self.no_result_box.pack_start(label, False, False, 8)
        self.no_result_box.pack_start(button, False, False, 16)
        self.no_result_box.set_valign(Gtk.Align.CENTER)

        self.box.pack_start(self.no_result_box, True, False, 0)

    def init_header_bar(self):
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        header_bar.props.title = APP_NAME
        self.set_titlebar(header_bar)

        refresh_button = Gtk.Button()
        icon = Gio.ThemedIcon(name="view-refresh-symbolic")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        refresh_button.add(image)
        header_bar.pack_end(refresh_button)
        refresh_button.connect('clicked', self.start_discovery)

        self.bulbs_selection_button = BulbSelectionWidget(default_label='Select bulb')
        header_bar.pack_start(self.bulbs_selection_button)

        return header_bar

class BulbOptionRow(Gtk.ListBoxRow):
    def __init__(self):
        super().__init__()

    def set_content(self, label: Gtk.Label, control: Gtk.Widget, control_expand: bool = True):
        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=64)
        self.add(h_box)
        h_box.pack_start(label, False, False, 0)
        h_box.pack_end(control, control_expand, control_expand, 0)
        label.set_margin_start(16)
        control.set_margin_end(16)

        if not control_expand:
            control.set_halign(Gtk.Align.END)
        self.set_size_request(-1, 48)
        self.show_all()


class BulbInfoRow(Gtk.ListBoxRow):
    def __init__(self):
        super().__init__()
        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(64)
        self.add(self.grid)

        margin = 16
        self.grid.set_margin_start(margin)
        self.grid.set_margin_end(margin)
        self.grid.set_margin_top(margin)
        self.grid.set_margin_bottom(margin)

        self.set_halign(Gtk.Align.CENTER)

    def update_content(self, wrapper: BulbWrapper):
        row_index = 0
        to_dict = wrapper.to_dict(exclude_none=True)
        if 'Capabilities' in to_dict:
            del (to_dict['Capabilities'])
        for prop, value in to_dict.items():
            prop_label = self.grid.get_child_at(0, row_index) or Gtk.Label(xalign=0)  # Reusing old widget
            prop_label.set_markup('<b>' + prop + '</b>')
            if not prop_label.get_parent():
                self.grid.attach(prop_label, 0, row_index, 1, 1)

            value_label = self.grid.get_child_at(1, row_index) or Gtk.Label(xalign=0)
            value_label.set_markup('<tt>' + str(value) + '</tt>')
            value_label.set_line_wrap(True)
            if not value_label.get_parent():
                self.grid.attach(value_label, 1, row_index, 1, 1)

            row_index += 1

        for i in range(row_index, int(len(self.grid.get_children()) / 2)):
            self.grid.remove_row(i)  # Remove unused widgets

        self.show_all()
