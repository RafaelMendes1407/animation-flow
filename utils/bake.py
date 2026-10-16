"""
Bake de animações (composições de partes).

Para cada animação marcada:
1. Para a gravação de partes e salva o estado de cada objeto.
2. Deixa audíveis só as camadas dessa animação (as não silenciadas).
3. Faz o bake com ``bpy_extras.anim_utils.bake_action_objects`` numa Action nova.
4. Registra o resultado como uma **Parte** "<animação>_bake" e uma
   **Animação** "<animação> [bake]" com uma única strip por objeto.
"""

import math

import bpy
from bpy_extras import anim_utils

from . import compat
from . import nla
from ..i18n import rpt


def animation_summary(scene, anim, all_bones=False):
    """
    O que entra no bake da animação: {objeto: {"bones": set, "object": bool}}.

    Por padrão: bones com keys em alguma parte usada + bones com constraints.
    """
    resumo = {}
    for ob, track, _i in nla.animation_tracks(scene, anim):
        dados = resumo.setdefault(ob, {"bones": set(), "object": ob.type != 'ARMATURE'})
        for s in track.strips:
            if s.action is None:
                continue
            dados["bones"] |= nla.keyed_bone_names(s.action, s.action_slot)
            if nla.has_object_channels(s.action, s.action_slot):
                dados["object"] = True
    for ob, dados in resumo.items():
        if ob.type != 'ARMATURE':
            continue
        if all_bones:
            dados["bones"] = {pb.name for pb in ob.pose.bones}
        else:
            dados["bones"] |= bones_movidos_pelo_rig(ob)
    return resumo


def bones_movidos_pelo_rig(ob):
    """
    Bones cuja pose vem do rig e não só das keys: com constraints, membros de
    cadeias de IK/Spline IK (ex.: a coxa numa IK de 2 bones na canela, que
    não tem constraint própria) e bones com drivers.
    """
    nomes = set()
    for pb in ob.pose.bones:
        for c in pb.constraints:
            if not c.enabled:
                continue
            nomes.add(pb.name)
            if c.type in {'IK', 'SPLINE_IK'}:
                # chain_count 0 = a cadeia sobe até a raiz.
                restantes = c.chain_count - 1 if c.chain_count > 0 else -1
                pai = pb.parent
                while pai is not None and restantes != 0:
                    nomes.add(pai.name)
                    pai = pai.parent
                    restantes -= 1
    ad = ob.animation_data
    if ad is not None:
        for d in ad.drivers:
            bone, _prop = nla.parse_bone_path(d.data_path)
            if bone is not None:
                nomes.add(bone)
    return nomes


def _bake_one(scene, anim, step, visual_keying, clean, all_bones):
    faixa = nla.animation_range(scene, anim)
    if faixa is None:
        raise nla.AnimFlowError(rpt("'{}' has no parts placed").format(anim.name))
    resumo = {
        ob: d for ob, d in animation_summary(scene, anim, all_bones).items()
        if d["object"] or d["bones"]
    }
    if not resumo:
        raise nla.AnimFlowError(rpt("'{}' has no keys to bake").format(anim.name))

    # O bake NUNCA mexe nas constraints do rig. Sem Visual Keying (padrão),
    # ele grava os canais (FK, alvos de IK...) e o rig recalcula IK/constraints
    # ao tocar: resultado idêntico no próprio Blender. Com Visual Keying (para
    # exportar), a pose final é gravada e, no Blender, as constraints continuam
    # agindo por cima (comportamento padrão do bake do Blender).
    nla.ensure_pose_base(scene, list(resumo))

    nomes_anim = {nla.layer_track_name(anim.name, l.name): l.mute for l in anim.layers}
    baked = nla.new_part_action(f"{anim.name}_bake")
    estados = {}

    try:
        for ob, dados in resumo.items():
            ad = ob.animation_data
            estados[ob] = {
                "action": ad.action, "slot": ad.action_slot,
                "blend": ad.action_blend_type, "influence": ad.action_influence,
                "mutes": {t.name: t.mute for t in ad.nla_tracks},
                "solo": [t.name for t in ad.nla_tracks if t.is_solo],
                "selecao": {},
                # Pose atual, para restaurar depois do bake.
                "basis": ob.matrix_basis.copy(),
                "pose": ({pb.name: pb.matrix_basis.copy() for pb in ob.pose.bones}
                         if ob.type == 'ARMATURE' else {}),
            }
            ad.action = None
            for t in ad.nla_tracks:
                if t.is_solo:
                    t.is_solo = False
                # Só as camadas da animação (e a pose base) tocam no bake.
                t.mute = False if t.name == nla.POSE_BASE_TRACK else nomes_anim.get(t.name, True)

            if ob.type == 'ARMATURE':
                for pb in ob.pose.bones:
                    estados[ob]["selecao"][pb.name] = compat.pose_bone_is_selected(pb)
                    compat.pose_bone_set_selected(pb, pb.name in dados["bones"])

            ad.action = baked
            ad.action_slot = compat.ensure_slot(baked, ob)

        # As opções valem para todos os objetos de uma chamada, então
        # agrupamos por combinação (pose, objeto).
        grupos = {}
        for ob, d in resumo.items():
            do_pose = ob.type == 'ARMATURE' and bool(d["bones"])
            grupos.setdefault((do_pose, d["object"]), []).append(ob)

        frames = range(math.floor(faixa[0]), math.ceil(faixa[1]) + 1, max(1, int(step)))
        for (do_pose, do_object), objetos in grupos.items():
            opcoes = anim_utils.BakeOptions(
                only_selected=True,
                do_pose=do_pose,
                do_object=do_object,
                do_visual_keying=visual_keying,
                do_constraint_clear=False,
                do_parents_clear=False,
                do_clean=clean,
                do_location=True,
                do_rotation=True,
                do_scale=True,
                do_bbone=True,
                do_custom_props=False,
            )
            anim_utils.bake_action_objects(
                [(ob, baked) for ob in objetos], frames=frames, bake_options=opcoes,
            )
    finally:
        for ob, estado in estados.items():
            ad = ob.animation_data
            ad.action = None
            for t in ad.nla_tracks:
                if t.name in estado["mutes"]:
                    t.mute = estado["mutes"][t.name]
                if t.name in estado["solo"]:
                    t.is_solo = True
            if ob.type == 'ARMATURE':
                for pb in ob.pose.bones:
                    if pb.name in estado["selecao"]:
                        compat.pose_bone_set_selected(pb, estado["selecao"][pb.name])
            if estado["action"] is not None:
                ad.action = estado["action"]
                if estado["slot"] is not None:
                    ad.action_slot = estado["slot"]
                ad.action_blend_type = estado["blend"]
                ad.action_influence = estado["influence"]
            # Devolve a pose de antes do bake (canais sem animação não ficam
            # presos na pose do último frame assado).
            ob.matrix_basis = estado["basis"]
            for nome, matriz in estado["pose"].items():
                pb = ob.pose.bones.get(nome)
                if pb is not None:
                    pb.matrix_basis = matriz

    return baked, list(resumo)


def bake_animations(context, nomes, step=1, visual_keying=True, clean=True, all_bones=False):
    """
    Faz o bake de cada animação cujo nome está em *nomes*.
    (Usamos nomes porque referências a itens de coleção ficam inválidas
    quando a coleção cresce.)
    Retorna lista de (animação_original, part_resultante, animação_resultante).
    """
    scene = context.scene
    props = scene.animflow
    nla.stop_part_edit(scene)
    nla.exit_tweak_all(scene)
    frame_atual = scene.frame_current
    ativa = nla.active_animation(context)
    nome_ativa = ativa.name if ativa else None

    resultados = []
    try:
        for nome_anim in nomes:
            anim = props.animations.get(nome_anim)
            if anim is None:
                continue
            baked, objetos = _bake_one(scene, anim, step, visual_keying, clean, all_bones)

            # Registra o resultado: nova Parte...
            part = props.parts.add()
            part.action = baked
            part.name = baked.name
            props.parts.move(len(props.parts) - 1, 0)

            # ... e nova Animação com uma strip por objeto.
            nome = nla.unique_name(f"{nome_anim} [bake]", {a.name for a in props.animations})
            nova = props.animations.add()
            nova.name = nome
            nova.track_prefix = nome
            layer = nova.layers.add()
            layer.name = layer.track_name = "Base"
            inicio = nla.part_range(baked)[0]
            nla.add_part_to_layer(scene, nova, 0, props.parts[0], inicio, objetos)
            resultados.append((nome_anim, props.parts[0].name, nome))
    finally:
        scene.frame_set(frame_atual)
        # Mantém tocando a animação que estava ativa.
        ativa = props.animations.get(nome_ativa) if nome_ativa else None
        if ativa is not None:
            nla.activate_animation(scene, ativa)
    return resultados
