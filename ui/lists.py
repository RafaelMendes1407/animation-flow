"""
UILists: partes, animações, camadas e animações do bake.
"""

import bpy

from .. import handlers
from ..utils import nla


class ANIMFLOW_UL_parts(bpy.types.UIList):
    """Biblioteca de partes. Clique seleciona; duplo clique adiciona como strip solta."""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_prop, index):
        if item.action is None:
            row = layout.row()
            row.alert = True
            row.label(text=item.name, translate=False, icon='ERROR')
            return
        n_bones = handlers.HIGHLIGHT["parts"].get(item.action.name, 0)
        gravando = nla.editing_part(context.scene) == item.action

        row = layout.row(align=True)
        # O nome é um botão: o operador detecta o duplo clique (o UIList não
        # oferece isso). O nome é editado no campo abaixo da lista.
        op = row.operator("animflow.part_click", text=item.name, emboss=False, translate=False,
                          icon='KEYFRAME_HLT' if n_bones else 'ACTION')
        op.index = index
        if n_bones:
            # Marca bem visível: os bones selecionados têm keys nesta parte.
            sub = row.row()
            sub.alert = True
            sub.label(text=str(n_bones), icon='BONE_DATA', translate=False)
        inicio, fim = nla.part_range(item.action)
        sub = row.row()
        sub.active = False
        sub.label(text=f"{inicio:.0f}–{fim:.0f}", translate=False)
        sub = row.row()
        sub.alert = gravando
        op = sub.operator("animflow.part_record", text="", icon='REC', depress=gravando)
        op.index = index

    def filter_items(self, _context, data, propname):
        # Filtro por nome padrão (o nome não é desenhado como propriedade).
        itens = getattr(data, propname)
        flags = [self.bitflag_filter_item] * len(itens)
        if self.filter_name:
            termo = self.filter_name.lower()
            flags = [f if termo in it.name.lower() else 0 for f, it in zip(flags, itens)]
        if self.use_filter_invert:
            flags = [f ^ self.bitflag_filter_item for f in flags]
        return flags, []


class ANIMFLOW_UL_animations(bpy.types.UIList):
    """Animações completas. Destaca as que usam partes com keys dos bones selecionados."""

    def draw_item(self, context, layout, data, item, _icon, _active_data, _active_prop, index):
        destacada = item.name in handlers.HIGHLIGHT["anims"]
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='KEYFRAME_HLT' if destacada else 'NLA')
        if destacada:
            sub = row.row()
            sub.alert = True
            sub.label(text="", icon='BONE_DATA')
        faixa = nla.animation_range(context.scene, item)
        sub = row.row()
        sub.active = False
        if faixa:
            sub.label(text=f"{faixa[0]:.0f}–{faixa[1]:.0f}", translate=False)
        else:
            sub.label(text="empty")
        tocando = data.active_anim_index == index and not data.loose_playing
        op = row.operator("animflow.anim_play", text="", icon='PLAY', depress=tocando)
        op.index = index


class ANIMFLOW_UL_layers(bpy.types.UIList):
    """Camadas da animação, de cima (sobreposta) para baixo (base)."""

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_prop, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='RENDERLAYERS' if index else 'NLA')
        row.prop(item, "hold", text="", emboss=False, icon='PINNED' if item.hold else 'UNPINNED')
        row.prop(item, "mute", text="", emboss=False, icon='HIDE_ON' if item.mute else 'HIDE_OFF')

    def filter_items(self, _context, data, propname):
        # Mostra invertido: a camada mais alta (índice maior) aparece em cima,
        # como na pilha do NLA.
        n = len(getattr(data, propname))
        return [self.bitflag_filter_item] * n, [n - 1 - i for i in range(n)]


class ANIMFLOW_UL_bake_anims(bpy.types.UIList):
    """Animações com caixa de seleção para o bake."""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_prop, _index):
        row = layout.row(align=True)
        row.prop(item, "bake_include", text="")
        row.label(text=item.name, icon='NLA', translate=False)
        faixa = nla.animation_range(context.scene, item)
        sub = row.row()
        sub.active = False
        if faixa:
            sub.label(text=f"{faixa[0]:.0f}–{faixa[1]:.0f}", translate=False)
        else:
            sub.label(text="empty")


classes = (
    ANIMFLOW_UL_parts,
    ANIMFLOW_UL_animations,
    ANIMFLOW_UL_layers,
    ANIMFLOW_UL_bake_anims,
)
