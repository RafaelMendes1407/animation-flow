"""
Diagnóstico: gera um relatório da cena (NLA, pose base, constraints, shapes)
em ~/Documents/anim_flow_diagnostico.txt e num Text do Blender.
"""

import os

import bpy

from ..i18n import rpt
from ..utils import compat
from ..utils import nla


def _fmt(v):
    try:
        return "(" + ", ".join(f"{x:.3f}" for x in v) + ")"
    except TypeError:
        return f"{v:.3f}" if isinstance(v, float) else str(v)


def _relatorio(context):
    scene = context.scene
    props = scene.animflow
    L = []
    L.append(f"Blender {bpy.app.version_string} | cena '{scene.name}' | frames {scene.frame_start}-{scene.frame_end} "
             f"| atual {scene.frame_current} | preview {scene.use_preview_range} "
             f"{scene.frame_preview_start}-{scene.frame_preview_end}")
    editando, modo, anim_ed = nla.editing_info(scene)
    L.append(f"Gravando: {editando.name if editando else '-'} modo={modo} animação={anim_ed}")
    L.append(f"Pose base ligada: {props.use_pose_base} | gravar no contexto: {props.record_in_context}")

    L.append("\n== PARTES")
    for p in props.parts:
        a = p.action
        if a is None:
            L.append(f"  {p.name}: SEM ACTION")
            continue
        L.append(f"  {p.name}: range {_fmt(a.frame_range)} manual={a.use_frame_range} "
                 f"slots={[s.identifier for s in a.slots]} usos={nla.part_usage(scene, a)}")

    L.append("\n== ANIMAÇÕES")
    for i, an in enumerate(props.animations):
        ativa = " (ATIVA)" if i == props.active_anim_index else ""
        L.append(f"  {an.name}{ativa}: range={nla.animation_range(scene, an)} legado_action={an.action}")
        for j, ly in enumerate(an.layers):
            L.append(f"    camada {j} '{ly.name}' mute={ly.mute} segurar={ly.hold}")

    for ob in scene.objects:
        ad = ob.animation_data
        if ad is None and ob.type != 'ARMATURE':
            continue
        L.append(f"\n== OBJETO {ob.name} ({ob.type}) modo={ob.mode}")
        if ad is not None:
            L.append(f"  action ativa={ad.action.name if ad.action else None} "
                     f"slot={ad.action_slot.identifier if ad.action_slot else None} "
                     f"blend={ad.action_blend_type} infl={ad.action_influence:.2f} tweak={ad.use_tweak_mode}")
            L.append("  NLA (de baixo para cima):")
            for t in ad.nla_tracks:
                L.append(f"   [{t.name}] mute={t.mute} solo={t.is_solo} lock={t.lock}")
                for s in t.strips:
                    L.append(
                        f"      strip '{s.name}' action={s.action.name if s.action else None} "
                        f"slot={s.action_slot.identifier if s.action_slot else None} "
                        f"frames {s.frame_start:.2f}-{s.frame_end:.2f} action {s.action_frame_start:.2f}-"
                        f"{s.action_frame_end:.2f} extrap={s.extrapolation} blend={s.blend_type} "
                        f"rep={s.repeat:.2f} esc={s.scale:.2f} inv={s.use_reverse} mute={s.mute} "
                        f"sync={s.use_sync_length} blendIO={s.blend_in:.1f}/{s.blend_out:.1f} "
                        f"auto={s.use_auto_blend} infl_anim={s.use_animated_influence} infl={s.influence:.2f}")
            # Pose base: valores fora do esperado.
            base = bpy.data.actions.get(nla.POSE_BASE_PREFIX + ob.name)
            if base is not None:
                slot = compat.find_slot(base, ob)
                errados = []
                fcs = compat.fcurves_for(base, slot)
                for fc in fcs:
                    esperado = nla._default_do_canal(ob, fc.data_path, fc.array_index)
                    atual = fc.keyframe_points[0].co[1] if len(fc.keyframe_points) else None
                    if esperado is None or atual is None or abs(atual - esperado) > 1e-6:
                        errados.append(f"{fc.data_path}[{fc.array_index}]={atual} (esperado {esperado})")
                L.append(f"  Pose base: {len(fcs)} canais; fora do esperado: {len(errados)}")
                L.extend("    " + e for e in errados[:60])
            for dono, alvo, ancestral in nla.ik_cycles(ob):
                L.append(f"  CICLO DE IK: alvo '{alvo}' é filho de '{ancestral}', que está na cadeia do IK de '{dono}'")
            if ad.drivers:
                L.append(f"  Drivers: {[f'{d.data_path}[{d.array_index}]' for d in ad.drivers][:40]}")

        if ob.type == 'ARMATURE':
            L.append("  Bones:")
            for pb in ob.pose.bones:
                info = [f"rot={pb.rotation_mode}", f"pai={pb.parent.name if pb.parent else None}"]
                if pb.custom_shape:
                    info.append(f"shape={pb.custom_shape.name}")
                    if any(abs(v) > 1e-6 for v in pb.custom_shape_translation):
                        info.append(f"shape_offset={_fmt(pb.custom_shape_translation)}")
                    if any(abs(v) > 1e-6 for v in pb.custom_shape_rotation_euler):
                        info.append(f"shape_rot={_fmt(pb.custom_shape_rotation_euler)}")
                    if any(abs(v - 1) > 1e-6 for v in pb.custom_shape_scale_xyz):
                        info.append(f"shape_esc={_fmt(pb.custom_shape_scale_xyz)}")
                    if pb.custom_shape_transform:
                        info.append(f"SHAPE_SEGUE_BONE={pb.custom_shape_transform.name}")
                for c in pb.constraints:
                    alvo = getattr(c, "subtarget", "") or (getattr(c, "target", None) and c.target.name)
                    extra = ""
                    if c.type == 'IK':
                        extra = f" cadeia={c.chain_count} pole={c.pole_subtarget or None}"
                    info.append(f"C[{c.type} '{c.name}' alvo={alvo} infl={c.influence:.2f} "
                                f"ligada={c.enabled}{extra}]")
                L.append(f"    {pb.name}: loc={_fmt(pb.location)} " + " ".join(info))
    return "\n".join(L)


class ANIMFLOW_OT_diagnose(bpy.types.Operator):
    """Write a scene report (NLA, base pose, constraints, shapes) to help find problems"""

    bl_idname = "animflow.diagnose"
    bl_label = "Diagnostics"

    def execute(self, context):
        texto = _relatorio(context)
        caminho = os.path.join(os.path.expanduser("~"), "Documents", "anim_flow_diagnostico.txt")
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(texto)
        except OSError as ex:
            caminho = f"(could not save: {ex})"
        txt = bpy.data.texts.get("AnimFlow_Diagnostico") or bpy.data.texts.new("AnimFlow_Diagnostico")
        txt.clear()
        txt.write(texto)
        self.report({'INFO'}, rpt("Diagnostics saved to {}").format(caminho))
        return {'FINISHED'}


classes = (
    ANIMFLOW_OT_diagnose,
)
