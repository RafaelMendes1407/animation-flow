"""
Handlers:
* destaque automático das partes/animações/tracks que têm keys dos bones
  selecionados (requisito 5);
* migração automática de arquivos da versão 1.0 ao abrir.
"""

import bpy
from bpy.app.handlers import persistent

from . import preferences
from .utils import compat
from .utils import nla

# Resultado do destaque, lido pelas UILists e painéis.
#   parts:  {nome da Action (parte): quantos bones selecionados têm keys nela}
#   anims:  nomes das animações que usam essas partes
#   tracks: pares (nome_objeto, nome_track) com strips dessas partes
HIGHLIGHT = {"parts": {}, "anims": set(), "tracks": set(), "selecao": {}}


def _calcular(scene, selecao):
    parts, anims, tracks = {}, set(), set()
    owners = nla.track_owners(scene)
    for ob_name, bones in selecao.items():
        ob = scene.objects.get(ob_name)
        if ob is None:
            continue
        for part in scene.animflow.parts:
            action = part.action
            if action is None:
                continue
            slot = nla.part_slot_for(action, ob)
            if slot is None:
                continue
            comuns = nla.keyed_bone_names(action, slot) & bones
            if comuns:
                parts[action.name] = parts.get(action.name, 0) + len(comuns)
        ad = ob.animation_data
        if ad is None:
            continue
        for track in ad.nla_tracks:
            if any(s.action is not None and s.action.name in parts for s in track.strips):
                tracks.add((ob.name, track.name))
                dono = owners.get(track.name)
                if dono is not None:
                    anims.add(dono[0].name)
    return parts, anims, tracks


def _sincronizar_nla(scene, selecao, tracks):
    """Seleciona no NLA nativo as tracks destacadas (destaque visual nativo)."""
    for ob_name in selecao:
        ob = scene.objects.get(ob_name)
        if ob is None or ob.animation_data is None:
            continue
        for track in ob.animation_data.nla_tracks:
            alvo = (ob.name, track.name) in tracks
            if track.select != alvo:
                track.select = alvo


def refresh(scene, view_layer, forcar=False):
    selecao = compat.selected_bone_names(view_layer)
    mudou = selecao != HIGHLIGHT["selecao"]
    if not (mudou or forcar):
        return
    HIGHLIGHT["selecao"] = selecao
    HIGHLIGHT["parts"], HIGHLIGHT["anims"], HIGHLIGHT["tracks"] = _calcular(scene, selecao)

    prefs = preferences.get_prefs()
    if mudou and selecao and (prefs is None or prefs.sync_nla_selection):
        _sincronizar_nla(scene, selecao, HIGHLIGHT["tracks"])
    compat.tag_redraw_all(('NLA_EDITOR', 'VIEW_3D'))


@persistent
def _on_depsgraph_update(scene, depsgraph):
    try:
        acao_editada = any(isinstance(u.id, bpy.types.Action) for u in depsgraph.updates)
        refresh(scene, depsgraph.view_layer, forcar=acao_editada)
    except (ReferenceError, AttributeError):
        # Dados removidos durante a atualização (ex.: undo); ignora com segurança.
        pass


def migrate_all():
    """Converte dados da v1.0 e repara influências zeradas pelas v1.3–1.5."""
    reparadas = nla.repair_constraint_influence()
    if reparadas:
        print("Anim Flow: influence restored to 1.0 on: " + ", ".join(reparadas))
    for scene in bpy.data.scenes:
        props = getattr(scene, "animflow", None)
        if props is not None and any(a.action is not None for a in props.animations):
            n = nla.migrate_v1(scene)
            print(f"Anim Flow: {n} v1.0 animation(s) converted in '{scene.name}'")


@persistent
def _on_load_post(*_args):
    HIGHLIGHT.update(parts={}, anims=set(), tracks=set(), selecao={})
    migrate_all()


def register():
    bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)
    bpy.app.handlers.load_post.append(_on_load_post)
    # Arquivo já aberto ao ativar o add-on: migra assim que possível.
    bpy.app.timers.register(lambda: migrate_all() or None, first_interval=0.1)


def unregister():
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
