"""
Operador de bake: faz o bake das animações marcadas na lista do modo Bake.
"""

import bpy

from ..i18n import rpt
from ..utils import bake
from ..utils import nla


class ANIMFLOW_OT_bake(bpy.types.Operator):
    """Bake the checked animations (each one becomes a Part + a "[bake]" Animation)"""

    bl_idname = "animflow.bake"
    bl_label = "Bake Animations"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(a.bake_include for a in context.scene.animflow.animations)

    def execute(self, context):
        props = context.scene.animflow
        nomes = [a.name for a in props.animations if a.bake_include]
        try:
            resultados = bake.bake_animations(
                context, nomes,
                step=props.bake_step,
                visual_keying=props.bake_visual,
                clean=props.bake_clean,
                all_bones=props.bake_all_bones,
            )
        except nla.AnimFlowError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}

        # Os resultados não entram no próximo bake por padrão.
        for _orig, _part, nome in resultados:
            nova = props.animations.get(nome)
            if nova is not None:
                nova.bake_include = False

        resumo = ", ".join(nome for _o, _p, nome in resultados)
        self.report({'INFO'}, rpt("Bake finished: {}").format(resumo))
        return {'FINISHED'}


class ANIMFLOW_OT_bake_toggle_all(bpy.types.Operator):
    """Check or uncheck every animation for the bake"""

    bl_idname = "animflow.bake_toggle_all"
    bl_label = "Toggle All"
    bl_options = {'UNDO'}

    def execute(self, context):
        anims = context.scene.animflow.animations
        marcar = not all(a.bake_include for a in anims)
        for a in anims:
            a.bake_include = marcar
        return {'FINISHED'}


classes = (
    ANIMFLOW_OT_bake,
    ANIMFLOW_OT_bake_toggle_all,
)
