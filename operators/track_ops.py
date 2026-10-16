"""
Operadores de canais (F-Curves por bone) das Partes: copiar, colar,
enviar (copiar/mover para outra parte) e apagar.
"""

import bpy
from bpy.props import BoolProperty, EnumProperty

from ..i18n import rpt
from ..utils import compat
from ..utils import nla
from ..utils.nla import AnimFlowError


# Área de transferência de canais.
_clipboard_canais = {"curves": []}

# O Blender exige que as strings de enums dinâmicos continuem referenciadas.
_cache_itens = []


def _itens_partes(_self, context):
    props = context.scene.animflow
    _cache_itens[:] = [(str(i), p.name, "") for i, p in enumerate(props.parts)]
    if not _cache_itens:
        _cache_itens.append(('-1', "(none)", ""))
    return _cache_itens


def _origem(context):
    """(objeto, parte, slot) de onde os canais saem, com validação."""
    ob = context.object
    if ob is None:
        raise AnimFlowError(rpt("No active object"))
    part = nla.active_part(context)
    if part is None or part.action is None:
        raise AnimFlowError(rpt("No active part"))
    slot = nla.part_slot_for(part.action, ob)
    if slot is None:
        raise AnimFlowError(rpt("'{}' has no animation in part '{}'").format(ob.name, part.name))
    return ob, part, slot


def _curvas_filtradas(ob, action, slot, todos):
    """F-Curves do slot, filtradas pelos bones selecionados (se não *todos*)."""
    curvas = compat.fcurves_for(action, slot)
    if todos or ob.type != 'ARMATURE':
        return curvas
    selecionados = {pb.name for pb in ob.pose.bones if compat.pose_bone_is_selected(pb)}
    if not selecionados:
        raise AnimFlowError(rpt("No bone selected (or check 'All Bones')"))
    return [fc for fc in curvas if nla.parse_bone_path(fc.data_path)[0] in selecionados]


def _escrever(ob, action, dados, replace, offset):
    slot = nla.part_slot_for(action, ob) or compat.ensure_slot(action, ob)
    channelbag = compat.ensure_channelbag(action, slot)
    for d in dados:
        nla.dict_to_fcurve(channelbag, d, offset=offset, replace=replace)


class _CanalOperator:
    todos: BoolProperty(
        name="All Bones", default=False,
        description="Use every channel of the object, not only those of the selected bones",
    )

    def execute(self, context):
        try:
            return self.run(context)
        except AnimFlowError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}


class ANIMFLOW_OT_channels_copy(_CanalOperator, bpy.types.Operator):
    """Copy the channels (keys) of the selected bones in the active part"""

    bl_idname = "animflow.channels_copy"
    bl_label = "Copy Channels"

    def run(self, context):
        ob, part, slot = _origem(context)
        curvas = _curvas_filtradas(ob, part.action, slot, self.todos)
        if not curvas:
            raise AnimFlowError(rpt("There are no keys to copy"))
        _clipboard_canais["curves"] = [nla.fcurve_to_dict(fc) for fc in curvas]
        self.report({'INFO'}, rpt("{} channel(s) copied from '{}'").format(len(curvas), part.name))
        return {'FINISHED'}


class ANIMFLOW_OT_channels_paste(_CanalOperator, bpy.types.Operator):
    """Paste the copied channels into the active part, on the active object"""

    bl_idname = "animflow.channels_paste"
    bl_label = "Paste Channels"
    bl_options = {'REGISTER', 'UNDO'}

    replace: BoolProperty(name="Replace", default=True,
                          description="Replace the existing keys; off: merge with them")
    at_current_frame: BoolProperty(name="At Current Frame", default=False,
                                   description="Offset the keys so they start at the current frame")

    @classmethod
    def poll(cls, _context):
        return bool(_clipboard_canais["curves"])

    def run(self, context):
        ob = context.object
        part = nla.active_part(context)
        if ob is None:
            raise AnimFlowError(rpt("No active object"))
        if part is None or part.action is None:
            raise AnimFlowError(rpt("No active part"))
        dados = _clipboard_canais["curves"]
        offset = 0.0
        if self.at_current_frame:
            primeiros = [d["co"][0] for d in dados if d["co"]]
            offset = context.scene.frame_current - min(primeiros) if primeiros else 0.0
        _escrever(ob, part.action, dados, self.replace, offset)
        nla.sync_part_strips(context.scene, part.action)
        self.report({'INFO'}, rpt("{} channel(s) pasted into '{}'").format(len(dados), part.name))
        return {'FINISHED'}


class ANIMFLOW_OT_channels_transfer(_CanalOperator, bpy.types.Operator):
    """Copy or move the channels of the selected bones to another part"""

    bl_idname = "animflow.channels_transfer"
    bl_label = "Send Channels to Part"
    bl_options = {'REGISTER', 'UNDO'}

    target: EnumProperty(name="Target", items=_itens_partes)
    move: BoolProperty(name="Move (Remove from Source)", default=True)
    replace: BoolProperty(name="Replace Keys in Target", default=True)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, _context):
        layout = self.layout
        layout.prop(self, "target")
        layout.prop(self, "move")
        layout.prop(self, "replace")
        layout.prop(self, "todos")

    def run(self, context):
        scene = context.scene
        ob, part, slot = _origem(context)
        idx = int(self.target)
        if not (0 <= idx < len(scene.animflow.parts)):
            raise AnimFlowError(rpt("Choose a target part"))
        destino = scene.animflow.parts[idx]
        if destino.action is None or destino.action == part.action:
            raise AnimFlowError(rpt("Choose a target part different from the source"))

        curvas = _curvas_filtradas(ob, part.action, slot, self.todos)
        if not curvas:
            raise AnimFlowError(rpt("There are no keys to send"))
        dados = [nla.fcurve_to_dict(fc) for fc in curvas]
        _escrever(ob, destino.action, dados, self.replace, 0.0)

        if self.move:
            channelbag = compat.get_channelbag(part.action, slot)
            for fc in curvas:
                channelbag.fcurves.remove(fc)
            nla.sync_part_strips(scene, part.action)
        nla.sync_part_strips(scene, destino.action)

        if self.move:
            msg = rpt("{} channel(s) moved to '{}'")
        else:
            msg = rpt("{} channel(s) copied to '{}'")
        self.report({'INFO'}, msg.format(len(dados), destino.name))
        return {'FINISHED'}


class ANIMFLOW_OT_channels_delete(_CanalOperator, bpy.types.Operator):
    """Delete the channels of the selected bones from the active part"""

    bl_idname = "animflow.channels_delete"
    bl_label = "Delete Channels"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        ob, part, slot = _origem(context)
        curvas = _curvas_filtradas(ob, part.action, slot, self.todos)
        if not curvas:
            raise AnimFlowError(rpt("There are no keys to delete"))
        channelbag = compat.get_channelbag(part.action, slot)
        for fc in curvas:
            channelbag.fcurves.remove(fc)
        nla.sync_part_strips(context.scene, part.action)
        self.report({'INFO'}, rpt("{} channel(s) deleted from '{}'").format(len(curvas), part.name))
        return {'FINISHED'}


classes = (
    ANIMFLOW_OT_channels_copy,
    ANIMFLOW_OT_channels_paste,
    ANIMFLOW_OT_channels_transfer,
    ANIMFLOW_OT_channels_delete,
)
