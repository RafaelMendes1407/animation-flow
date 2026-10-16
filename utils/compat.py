"""
Camada de compatibilidade com a API de animação do Blender 4.4+.

A partir do 4.4 as Actions são "em camadas" (layered) e usam *slots*:
uma única Action pode guardar a animação de vários objetos, cada um em seu
slot. As F-Curves ficam em um *channelbag* por slot, dentro de
``action.layers[i].strips[j]``. Concentramos aqui todo acesso a essa estrutura
para que o resto do add-on não dependa dos detalhes da API.
"""

import bpy


# -----------------------------------------------------------------------------
# Slots e channelbags

def slot_identifier_for(obj):
    """Identificador que um slot de objeto teria para *obj* ("OB" + nome)."""
    return "OB" + obj.name


def find_slot(action, obj):
    """Procura em *action* um slot apropriado para *obj* (ou None)."""
    if action is None:
        return None
    ident = slot_identifier_for(obj)
    for slot in action.slots:
        if slot.identifier == ident:
            return slot
    return None


def ensure_slot(action, obj):
    """Retorna o slot de *obj* em *action*, criando-o se necessário."""
    slot = find_slot(action, obj)
    if slot is None:
        slot = action.slots.new(id_type='OBJECT', name=obj.name)
    return slot


def get_channelbag(action, slot):
    """Primeiro channelbag de *slot* em *action* (ou None se não existir)."""
    if action is None or slot is None:
        return None
    for layer in action.layers:
        for strip in layer.strips:
            channelbag = strip.channelbag(slot)
            if channelbag:
                return channelbag
    return None


def ensure_channelbag(action, slot):
    """Garante camada + strip de keyframes + channelbag para *slot*."""
    layer = action.layers[0] if action.layers else action.layers.new("Layer")
    strip = layer.strips[0] if layer.strips else layer.strips.new(type='KEYFRAME')
    return strip.channelbag(slot, ensure=True)


def fcurves_for(action, slot):
    """Lista das F-Curves de *slot* em *action* (lista vazia se não houver)."""
    channelbag = get_channelbag(action, slot)
    return list(channelbag.fcurves) if channelbag else []


# -----------------------------------------------------------------------------
# Seleção de bones
#
# No 4.x a seleção de pose fica em ``pose_bone.bone.select``; em versões mais
# novas ela passou para ``pose_bone.select``. Os helpers abaixo tratam os dois.

def pose_bone_is_selected(pose_bone):
    if hasattr(pose_bone, "select"):
        return pose_bone.select
    return pose_bone.bone.select


def pose_bone_set_selected(pose_bone, value):
    if hasattr(pose_bone, "select"):
        pose_bone.select = value
    else:
        pose_bone.bone.select = value


def pose_armatures(view_layer):
    """Armatures que estão em Pose Mode na view layer."""
    return [
        ob for ob in view_layer.objects
        if ob.type == 'ARMATURE' and ob.mode == 'POSE'
    ]


def selected_bone_names(view_layer):
    """Dicionário {nome_do_objeto: {nomes de bones selecionados}} em Pose Mode."""
    result = {}
    for ob in pose_armatures(view_layer):
        names = {pb.name for pb in ob.pose.bones if pose_bone_is_selected(pb)}
        if names:
            result[ob.name] = names
    return result


# -----------------------------------------------------------------------------
# Diversos

def tag_redraw_all(area_types=('NLA_EDITOR', 'VIEW_3D', 'DOPESHEET_EDITOR', 'GRAPH_EDITOR')):
    """Força redesenho das áreas de animação em todas as janelas."""
    wm = bpy.context.window_manager
    if wm is None:
        return
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type in area_types:
                area.tag_redraw()
