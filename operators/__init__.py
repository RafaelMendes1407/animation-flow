"""Registro de todos os operadores do Anim Flow."""

import bpy

from . import anims_ops
from . import bake_ops
from . import diag_ops
from . import parts_ops
from . import shapes_ops
from . import track_ops

_modulos = (shapes_ops, parts_ops, anims_ops, track_ops, bake_ops, diag_ops)


def register():
    for mod in _modulos:
        for cls in mod.classes:
            bpy.utils.register_class(cls)


def unregister():
    for mod in reversed(_modulos):
        for cls in reversed(mod.classes):
            bpy.utils.unregister_class(cls)
