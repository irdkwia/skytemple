#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
import logging
import re
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from gi.repository import Gtk

from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import BinaryName
from skytemple.core.string_provider import StringType
from skytemple_files.common.i18n_util import _
from skytemple_files.hardcoded.iq import HardcodedIq

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_ITEM_ENTRY = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)
FIRST_GUMMI_ITEM_ID = 119
WONDER_GUMMI_ITEM_ID = 136
FAIRY_GUMMI_ITEM_ID = 138
NECTAR_ITEM_ID = 103


class IqGainOtherItem(Enum):
    WONDER_GUMMI = auto()
    NECTAR = auto()
    JUICE_BAR_NECTAR = auto()


class IqController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self._string_provider = module.project.get_string_provider()
        self.builder: Optional[Gtk.Builder] = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'iq.glade')
        box: Gtk.Box = self.builder.get_object('box_list')

        self._init_iq_gains()
        self._init_iq_skills()
        self._init_misc_settings()

        self.builder.connect_signals(self)
        return box

    def on_entry_min_iq_exclusive_move_user_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.ARM9, lambda bin: HardcodedIq.set_min_iq_for_exclusive_move_user(val, bin, static_data))
        self.module.mark_iq_as_modified()

    def on_entry_min_iq_item_master_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.ARM9, lambda bin: HardcodedIq.set_min_iq_for_item_master(val, bin, static_data))
        self.module.mark_iq_as_modified()

    def on_intimidator_activation_chance_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedIq.set_intimidator_chance(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def _init_misc_settings(self):
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        ov10 = self.module.project.get_binary(BinaryName.OVERLAY_10)
        static_data = self.module.project.get_rom_module().get_static_data()

        self.builder.get_object('entry_min_iq_exclusive_move_user').set_text(str(HardcodedIq.get_min_iq_for_exclusive_move_user(arm9, static_data)))
        self.builder.get_object('entry_min_iq_item_master').set_text(str(HardcodedIq.get_min_iq_for_item_master(arm9, static_data)))
        self.builder.get_object('intimidator_activation_chance').set_text(str(HardcodedIq.get_intimidator_chance(ov10, static_data)))

    def _init_iq_gains(self):
        """
        Store format:
        - int: id
        - str: gummi name
        For each gummi:
        - str: (type name)
        Tree is the same layout. Name column already exists.
        """
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        ov29 = self.module.project.get_binary(BinaryName.OVERLAY_29)
        static_data = self.module.project.get_rom_module().get_static_data()
        patch_applied = self.module.project.is_patch_applied("AddTypes")
        type_strings = self._string_provider.get_all(StringType.TYPE_NAMES)
        gummi_iq_gain_table = HardcodedIq.get_gummi_iq_gains(arm9, static_data, patch_applied)
        gummi_belly_gain_table = HardcodedIq.get_gummi_belly_heal(arm9, static_data, patch_applied)
        num_types = min(len(gummi_iq_gain_table), len(type_strings))

        # Normal Gummis
        store: Gtk.ListStore = Gtk.ListStore(*([int, str] + [str] * num_types))
        tree: Gtk.TreeView = self.builder.get_object('tree_iq_gain')
        store_belly: Gtk.ListStore = Gtk.ListStore(*([int, str] + [str] * num_types))
        tree_belly: Gtk.TreeView = self.builder.get_object('tree_belly_gain')
        tree.set_model(store)
        tree_belly.set_model(store_belly)
        for i in range(0, num_types):
            gummi_item_id = FIRST_GUMMI_ITEM_ID + i - 1
            if i == 18:
                gummi_item_id = FAIRY_GUMMI_ITEM_ID
            gummi_name = self._string_provider.get_value(StringType.ITEM_NAMES, gummi_item_id) if i != 0 else '/'
            data = [i, gummi_name]
            data_belly = [i, gummi_name]
            for j in range(0, num_types):
                data.append(str(gummi_iq_gain_table[j][i]))
                data_belly.append(str(gummi_belly_gain_table[j][i]))
            store.append(data)
            store_belly.append(data_belly)

            # column and cell renderer
            renderer = Gtk.CellRendererText(editable=True)
            column = Gtk.TreeViewColumn(title=type_strings[i], cell_renderer=renderer, text=i + 2)
            tree.append_column(column)
            renderer = Gtk.CellRendererText(editable=True)
            column = Gtk.TreeViewColumn(title=type_strings[i], cell_renderer=renderer, text=i + 2)
            tree_belly.append_column(column)

        # Other items
        store_other_items: Gtk.Store = self.builder.get_object('iq_gain_other_items')
        store_other_items.append([
            IqGainOtherItem.WONDER_GUMMI,
            self._string_provider.get_value(StringType.ITEM_NAMES, WONDER_GUMMI_ITEM_ID),
            str(HardcodedIq.get_wonder_gummi_gain(arm9, static_data))
        ])
        store_other_items.append([
            IqGainOtherItem.NECTAR,
            self._string_provider.get_value(StringType.ITEM_NAMES, NECTAR_ITEM_ID),
            str(HardcodedIq.get_nectar_gain(ov29, static_data))
        ])
        store_other_items.append([
            IqGainOtherItem.JUICE_BAR_NECTAR,
            _("Juice Bar Nectar"),
            str(HardcodedIq.get_juice_bar_nectar_gain(arm9, static_data))
        ])

    def _init_iq_skills(self):
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        static_data = self.module.project.get_rom_module().get_static_data()
        iq_skills = HardcodedIq.get_iq_skills(arm9, static_data)
        store: Gtk.ListStore = self.builder.get_object('iq_skills_store')

        for i, skill in enumerate(iq_skills):
            store.append([
                str(i), self._string_provider.get_value(
                    StringType.IQ_SKILL_NAMES, i - 1
                ) if i > 0 else '/', str(skill.iq_required), str(skill.unk2)
            ])
