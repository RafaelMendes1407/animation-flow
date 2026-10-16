"""
Anim Flow — fluxo de animação orientado a animações no NLA.

* Substituição de shapes de bones (clique direito no Pose Mode).
* NLA organizado por animação, com bones animados resumidos.
* Controles de timeline dentro do NLA.
* Criação explícita de tracks e indicador de onde as keys serão gravadas.
* Destaque das animações/tracks com keys dos bones selecionados.
* Bake simplificado com lista de conferência.

Requer Blender 4.4+ (Actions em camadas com slots).
"""

# bl_info só é usado na instalação como add-on "legado" (.zip pelo Install
# from Disk antigo). Como extensão, vale o blender_manifest.toml.
bl_info = {
    "name": "Anim Flow",
    "author": "Rafael Mendes",
    "version": (1, 7, 0),
    "blender": (4, 4, 0),
    "location": "NLA / 3D Viewport > Sidebar (N) > Anim Flow; Pose Mode > right-click",
    "description": "Parts, NLA animations composed from parts, bone shapes and simple baking",
    "category": "Animation",
}

import bpy

from . import handlers
from . import i18n
from . import operators
from . import preferences
from . import properties
from . import ui

# Ordem de registro: traduções -> dados -> preferências -> operadores -> UI -> handlers.
_modulos = (i18n, properties, preferences, operators, ui, handlers)


def register():
    if bpy.app.version < (4, 4, 0):
        raise RuntimeError("Anim Flow requer Blender 4.4 ou mais novo")
    for mod in _modulos:
        mod.register()


def unregister():
    for mod in reversed(_modulos):
        mod.unregister()
