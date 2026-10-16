"""
Timeline integrada ao NLA (requisito 3) e indicador de gravação no Viewport.

Os controles são *acrescentados* aos headers nativos (append), sem substituir
nada. O NLA já tem régua de tempo, scrub e marcadores, então com estes
controles ele cumpre o papel da Timeline.
"""

import bpy

from .. import preferences
from ..i18n import iface
from ..utils import nla


def _draw_transporte(layout, context):
    """Mesmos controles do header da Timeline (space_time.py)."""
    scene = context.scene
    tool_settings = context.tool_settings
    screen = context.screen

    row = layout.row(align=True)
    row.prop(tool_settings, "use_keyframe_insert_auto", text="", toggle=True)
    if hasattr(bpy.types, "TIME_PT_auto_keyframing"):
        sub = row.row(align=True)
        sub.active = tool_settings.use_keyframe_insert_auto
        sub.popover(panel="TIME_PT_auto_keyframing", text="")

    row = layout.row(align=True)
    row.operator("screen.frame_jump", text="", icon='REW').end = False
    row.operator("screen.keyframe_jump", text="", icon='PREV_KEYFRAME').next = False
    if not screen.is_animation_playing:
        row.operator("screen.animation_play", text="", icon='PLAY_REVERSE').reverse = True
        row.operator("screen.animation_play", text="", icon='PLAY')
    else:
        row.scale_x = 2
        row.operator("screen.animation_play", text="", icon='PAUSE')
        row.scale_x = 1
    row.operator("screen.keyframe_jump", text="", icon='NEXT_KEYFRAME').next = True
    row.operator("screen.frame_jump", text="", icon='FF').end = True

    row = layout.row()
    row.scale_x = 0.95
    row.prop(scene, "frame_current", text="")

    row = layout.row(align=True)
    row.prop(scene, "use_preview_range", text="", toggle=True)
    sub = row.row(align=True)
    sub.scale_x = 0.8
    if not scene.use_preview_range:
        sub.prop(scene, "frame_start", text="Start")
        sub.prop(scene, "frame_end", text="End")
    else:
        sub.prop(scene, "frame_preview_start", text="Start")
        sub.prop(scene, "frame_preview_end", text="End")


def _draw_indicador(layout, context):
    """Etiqueta curta: em qual parte as keys serão gravadas."""
    editando, modo, _anim = nla.editing_info(context.scene)
    row = layout.row(align=True)
    if editando is not None:
        part = nla.part_for_action(context.scene, editando)
        if modo == 'CONTEXT':
            texto = iface("Recording: {}")
        else:
            texto = iface("Recording: {} (solo)")
        row.label(text=texto.format(part.name if part else editando.name), icon='REC')
        row.operator("animflow.part_stop", text="", icon='PAUSE')
    else:
        row.alert = True
        row.label(text="No part being recorded", icon='ERROR')


def draw_nla_header(self, context):
    prefs = preferences.get_prefs(context)
    if prefs is not None and not prefs.timeline_in_nla:
        return
    layout = self.layout
    layout.separator_spacer()
    _draw_indicador(layout, context)
    _draw_transporte(layout, context)


def draw_view3d_header(self, context):
    prefs = preferences.get_prefs(context)
    if context.mode != 'POSE' or (prefs is not None and not prefs.record_in_viewport):
        return
    _draw_indicador(self.layout, context)


def register():
    bpy.types.NLA_HT_header.append(draw_nla_header)
    bpy.types.VIEW3D_HT_header.append(draw_view3d_header)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_view3d_header)
    bpy.types.NLA_HT_header.remove(draw_nla_header)
