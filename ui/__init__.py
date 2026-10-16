"""Registro da interface: listas, painéis, menus e headers."""

import bpy

from . import lists
from . import menus
from . import nla_header
from . import nla_panels

_modulos_classes = (lists, menus, nla_panels)


def register():
    for mod in _modulos_classes:
        for cls in mod.classes:
            bpy.utils.register_class(cls)
    menus.register()
    nla_header.register()


def unregister():
    nla_header.unregister()
    menus.unregister()
    for mod in reversed(_modulos_classes):
        for cls in reversed(mod.classes):
            bpy.utils.unregister_class(cls)
