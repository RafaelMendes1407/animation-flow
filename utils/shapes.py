"""
Biblioteca de shapes (widgets) para bones.

Cada shape é uma malha só de arestas (wireframe), criada sob demanda e
reaproveitada por todos os bones que a usam. As malhas ficam na coleção
oculta ``WGT_AnimFlow``.

Convenção de eixos (espaço do bone): Y aponta ao longo do bone, então
os shapes "planos" (círculo, quadrado...) ficam no plano XZ, envolvendo o bone,
como nos rigs do Rigify.
"""

import math

import bpy

COLECAO_WIDGETS = "WGT_AnimFlow"
PREFIXO_OBJETO = "WGT_AF_"

# (identificador, nome, ícone, descrição) usado nos enums e menus.
SHAPES = (
    ('CIRCLE', "Circle", 'MESH_CIRCLE', "Circle around the bone"),
    ('SEMICIRCLE', "Semicircle", 'MESH_CIRCLE', "Half circle (e.g. eyebrows, eyelids)"),
    ('SQUARE', "Square", 'MESH_PLANE', "Square around the bone"),
    ('DIAMOND', "Diamond", 'DECORATE_KEYFRAME', "Diamond around the bone"),
    ('HEXAGON', "Hexagon", 'SEQ_CHROMA_SCOPE', "Hexagon around the bone"),
    ('TRIANGLE', "Triangle", 'MARKER', "Triangle around the bone"),
    ('SPHERE', "Sphere", 'MESH_UVSPHERE', "Three orthogonal circles"),
    ('CUBE', "Cube", 'MESH_CUBE', "Wireframe cube"),
    ('PYRAMID', "Pyramid", 'MESH_CONE', "Pyramid pointing along the bone"),
    ('ARROW', "Arrow", 'SORT_DESC', "Arrow along the bone"),
    ('DOUBLE_ARROW', "Double Arrow", 'ARROW_LEFTRIGHT', "Arrow with two heads"),
    ('FOUR_ARROWS', "Four Arrows", 'OBJECT_ORIGIN', "Cross with arrows (move/root control)"),
    ('CROSS', "Cross", 'ADD', "Simple cross"),
    ('TARGET', "Target", 'PIVOT_CURSOR', "Circle with a cross (IK target / eyes)"),
    ('ROTATE', "Rotate", 'FILE_REFRESH', "Arc with arrows (rotation control)"),
    ('LINE', "Line", 'REMOVE', "Line along the bone"),
)

SHAPE_ITEMS = [(ident, nome, desc, icone, i) for i, (ident, nome, icone, desc) in enumerate(SHAPES)]
SHAPE_NOMES = {ident: nome for ident, nome, _icone, _desc in SHAPES}


# -----------------------------------------------------------------------------
# Geradores de geometria. Cada um retorna (vertices, arestas).

def _arco(raio, segmentos, inicio=0.0, fim=2 * math.pi, plano="XZ", fechado=True, y=0.0):
    verts = []
    n = segmentos if fechado else segmentos + 1
    for i in range(n):
        a = inicio + (fim - inicio) * i / segmentos
        c, s = math.cos(a) * raio, math.sin(a) * raio
        if plano == "XZ":
            verts.append((c, y, s))
        elif plano == "XY":
            verts.append((c, s + y, 0.0))
        else:  # YZ
            verts.append((0.0, c + y, s))
    edges = [(i, i + 1) for i in range(n - 1)]
    if fechado:
        edges.append((n - 1, 0))
    return verts, edges


def _juntar(*partes):
    verts, edges = [], []
    for v, e in partes:
        base = len(verts)
        verts.extend(v)
        edges.extend((a + base, b + base) for a, b in e)
    return verts, edges


def _poligono(lados, raio=0.5, rot=0.0):
    return _arco(raio, lados, inicio=rot, fim=rot + 2 * math.pi)


def _seta(comprimento=1.0, ponta=0.15, y0=0.0):
    # Seta no plano XY apontando para +Y.
    verts = [(0, y0, 0), (0, y0 + comprimento, 0),
             (-ponta, y0 + comprimento - ponta, 0), (ponta, y0 + comprimento - ponta, 0)]
    return verts, [(0, 1), (1, 2), (1, 3)]


def _geo_circle():
    return _arco(0.5, 32)


def _geo_semicircle():
    v, e = _arco(0.5, 16, 0.0, math.pi, fechado=False)
    return v, e + [(len(v) - 1, 0)]


def _geo_square():
    return _poligono(4, 0.5 * math.sqrt(2), math.pi / 4)


def _geo_diamond():
    return _poligono(4, 0.5)


def _geo_hexagon():
    return _poligono(6, 0.5)


def _geo_triangle():
    return _poligono(3, 0.5, math.pi / 2)


def _geo_sphere():
    return _juntar(_arco(0.5, 32, plano="XZ"), _arco(0.5, 32, plano="XY"), _arco(0.5, 32, plano="YZ"))


def _geo_cube():
    h = 0.5
    verts = [(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)]
    edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    # Desloca para cobrir o bone de 0 a 1 em Y.
    return [(x, y + h, z) for x, y, z in verts], edges


def _geo_pyramid():
    h = 0.35
    verts = [(-h, 0, -h), (h, 0, -h), (h, 0, h), (-h, 0, h), (0, 1, 0)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
    return verts, edges


def _geo_arrow():
    return _seta(1.0, 0.2)


def _geo_double_arrow():
    verts = [(0, 0, 0), (0, 1, 0), (-0.15, 0.85, 0), (0.15, 0.85, 0), (-0.15, 0.15, 0), (0.15, 0.15, 0)]
    return verts, [(0, 1), (1, 2), (1, 3), (0, 4), (0, 5)]


def _geo_four_arrows():
    p = 0.12
    braco = 0.5
    verts, edges = [(0, 0, 0)], []
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ponta = (dx * braco, 0, dz * braco)
        # Perpendicular no plano XZ para as abas da seta.
        px, pz = -dz, dx
        base = len(verts)
        verts += [ponta,
                  (ponta[0] - dx * p + px * p, 0, ponta[2] - dz * p + pz * p),
                  (ponta[0] - dx * p - px * p, 0, ponta[2] - dz * p - pz * p)]
        edges += [(0, base), (base, base + 1), (base, base + 2)]
    return verts, edges


def _geo_cross():
    verts = [(-0.5, 0, 0), (0.5, 0, 0), (0, 0, -0.5), (0, 0, 0.5)]
    return verts, [(0, 1), (2, 3)]


def _geo_target():
    return _juntar(_arco(0.4, 32), _geo_cross())


def _geo_rotate():
    r, h = 0.5, 0.1
    a0, a1 = math.radians(30), math.radians(150)
    v, e = _arco(r, 24, a0, a1, fechado=False)
    v, e = list(v), list(e)
    # Pontas de seta nas duas extremidades, apontando para fora do arco.
    for idx, ang, sinal in ((0, a0, -1), (len(v) - 1, a1, 1)):
        px, _py, pz = v[idx]
        # d = direção tangente (para fora do arco); n = direção radial.
        dx, dz = -math.sin(ang) * sinal, math.cos(ang) * sinal
        nx, nz = math.cos(ang), math.sin(ang)
        base = len(v)
        v += [(px - dx * h + nx * h, 0, pz - dz * h + nz * h),
              (px - dx * h - nx * h, 0, pz - dz * h - nz * h)]
        e += [(idx, base), (idx, base + 1)]
    return v, e


def _geo_line():
    return [(0, 0, 0), (0, 1, 0)], [(0, 1)]


_GERADORES = {
    'CIRCLE': _geo_circle,
    'SEMICIRCLE': _geo_semicircle,
    'SQUARE': _geo_square,
    'DIAMOND': _geo_diamond,
    'HEXAGON': _geo_hexagon,
    'TRIANGLE': _geo_triangle,
    'SPHERE': _geo_sphere,
    'CUBE': _geo_cube,
    'PYRAMID': _geo_pyramid,
    'ARROW': _geo_arrow,
    'DOUBLE_ARROW': _geo_double_arrow,
    'FOUR_ARROWS': _geo_four_arrows,
    'CROSS': _geo_cross,
    'TARGET': _geo_target,
    'ROTATE': _geo_rotate,
    'LINE': _geo_line,
}


# -----------------------------------------------------------------------------
# Criação dos objetos de widget

def _colecao_widgets(scene):
    """Coleção oculta onde os widgets ficam guardados."""
    col = bpy.data.collections.get(COLECAO_WIDGETS)
    if col is None:
        col = bpy.data.collections.new(COLECAO_WIDGETS)
        col.hide_render = True
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    # Esconde no viewport sem excluir da view layer (o shape continua visível no bone).
    col.hide_viewport = True
    return col


def get_widget(scene, shape_id):
    """Objeto de widget para *shape_id*, criado se ainda não existir."""
    if shape_id not in _GERADORES:
        raise ValueError(f"Shape desconhecido: {shape_id}")

    nome = PREFIXO_OBJETO + shape_id
    obj = bpy.data.objects.get(nome)
    if obj is not None and obj.type == 'MESH' and obj.library is None:
        return obj

    verts, edges = _GERADORES[shape_id]()
    mesh = bpy.data.meshes.new(nome)
    mesh.from_pydata(verts, edges, [])
    mesh.update()

    obj = bpy.data.objects.new(nome, mesh)
    _colecao_widgets(scene).objects.link(obj)
    obj.hide_render = True
    return obj
