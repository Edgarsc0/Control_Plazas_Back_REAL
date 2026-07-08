"""
organigrama_tree.py
====================
Construye el árbol jerárquico (mismo formato que los antiguos JSON estáticos
en eje_central_front/public/organigramas/) a partir de filas planas de
ORGANIGRAMA_ANAM para una sola unidad_negocio.

Lógica portada de Webwright_runs/generar_organigramas.py — ver ese archivo
para la explicación completa del algoritmo de segmentación de códigos.
"""

LEVEL_ORDER = {
    "Titular": 6,
    "General": 5,
    "Central": 4,
    "Director": 3,
    "Subdir.": 2,
    "Jefe Depto": 1,
    "(en blanco)": 0,
}


def parse_code(code):
    if len(code) == 11:
        return code[0:3], code[3:5], code[5:7], code[7:9], code[9:11]
    elif len(code) == 10:
        return code[0:2], code[2:4], code[4:6], code[6:8], code[8:10]
    return None


def is_zero(seg):
    return seg.lstrip("0") == "" or seg == ""


def candidate_parents(code, available):
    segs = parse_code(code)
    if segs is None:
        return []

    G, C, A, S, D = segs
    L = len(code)
    candidates = []

    if L == 11:
        if not is_zero(D):
            candidates.append(G + C + A + S + "00")
            if is_zero(S):
                candidates.append(G + C + A + "0000")
            candidates.append(G + C + A + "0000")
            candidates.append(G + C + "000000")
            candidates.append(G + "00000000")
        elif not is_zero(S):
            candidates.append(G + C + A + "0000")
            candidates.append(G + C + "000000")
            candidates.append(G + "00000000")
        elif not is_zero(A):
            candidates.append(G + C + "000000")
            candidates.append(G + "00000000")
        elif not is_zero(C):
            candidates.append(G + "00000000")
    elif L == 10:
        G2, C2, A2, S2, D2 = segs
        if not is_zero(D2):
            candidates.append(G2 + C2 + A2 + S2 + "00")
            candidates.append(G2 + C2 + A2 + "0000")
            candidates.append(G2 + C2 + "000000")
            candidates.append(G2 + "00000000")
        elif not is_zero(S2):
            candidates.append(G2 + C2 + A2 + "0000")
            candidates.append(G2 + C2 + "000000")
            candidates.append(G2 + "00000000")
        elif not is_zero(A2):
            candidates.append(G2 + C2 + "000000")
            candidates.append(G2 + "00000000")
        elif not is_zero(C2):
            candidates.append(G2 + "00000000")

    seen = set()
    result = []
    for c in candidates:
        if c not in seen and c != code and c in available:
            result.append(c)
            seen.add(c)
    return result


def build_position_index(data):
    by_mgr = {}
    for d in data:
        mgr = d.get("num_posicion_gerente", "")
        if mgr and mgr not in ("(en blanco)", ""):
            by_mgr.setdefault(mgr, []).append(d)
    return by_mgr


def common_prefix_len(s1, s2):
    n = 0
    for a, b in zip(s1, s2):
        if a == b:
            n += 1
        else:
            break
    return n


def resolve_by_position(d, by_mgr, available):
    pid = d.get("posicion_director", "")
    if not pid or pid in ("(en blanco)", ""):
        return None
    dept_id = d["departamento"]
    candidates = [
        c for c in by_mgr.get(pid, [])
        if c["departamento"] != dept_id and c["departamento"] in available
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]["departamento"]
    best = max(
        candidates,
        key=lambda c: (
            common_prefix_len(dept_id, c["departamento"]),
            LEVEL_ORDER.get(c["nivel_direccion"], 0),
        ),
    )
    return best["departamento"]


def find_root(data):
    max_level = max(LEVEL_ORDER.get(d["nivel_direccion"], 0) for d in data)
    roots = [d for d in data if LEVEL_ORDER.get(d["nivel_direccion"], 0) == max_level]
    return min(roots, key=lambda d: (len(d["departamento"]), d["departamento"]))


def build_parent_map(data):
    available = {d["departamento"] for d in data}
    by_mgr = build_position_index(data)
    root = find_root(data)
    root_code = root["departamento"]

    parent_map = {}
    for d in data:
        code = d["departamento"]
        if code == root_code:
            parent_map[code] = None
            continue

        parents_by_prefix = candidate_parents(code, available)
        if parents_by_prefix:
            parent_map[code] = parents_by_prefix[0]
            continue

        by_pos = resolve_by_position(d, by_mgr, available)
        if by_pos:
            parent_map[code] = by_pos
            continue

        parent_map[code] = root_code

    return parent_map, root_code


def build_children_map(data, parent_map):
    by_parent = {}
    for d in data:
        p = parent_map.get(d["departamento"])
        by_parent.setdefault(p or "ROOT", []).append(d)
    return by_parent


def build_tree_node(node, by_parent, visited=None):
    if visited is None:
        visited = set()
    code = node["departamento"]
    if code in visited:
        return None
    visited.add(code)

    children_raw = by_parent.get(code, [])
    children_sorted = sorted(
        children_raw,
        key=lambda x: (
            -LEVEL_ORDER.get(x["nivel_direccion"], 0),
            x["descripcion_larga"],
        ),
    )

    subordinados = []
    for child in children_sorted:
        node_child = build_tree_node(child, by_parent, visited)
        if node_child is not None:
            subordinados.append(node_child)

    return {
        "departamento": node["departamento"],
        "descripcion_larga": node["descripcion_larga"],
        "nivel_direccion": node.get("nivel_direccion", ""),
        "unidad_negocio": node["unidad_negocio"],
        "unidad_administrativa": node["unidad_administrativa"],
        "doaf": node["doaf"],
        "num_posicion_gerente": node["num_posicion_gerente"],
        "posicion_director": node["posicion_director"],
        "subordinados": subordinados,
    }


def build_tree(data):
    """
    data: lista de dicts con las columnas de ORGANIGRAMA_ANAM (ya filtradas
    por unidad_negocio). Retorna el nodo raíz anidado, o None si data está vacío.
    """
    if not data:
        return None
    parent_map, root_code = build_parent_map(data)
    by_parent = build_children_map(data, parent_map)
    root_node = next(d for d in data if d["departamento"] == root_code)
    return build_tree_node(root_node, by_parent)
