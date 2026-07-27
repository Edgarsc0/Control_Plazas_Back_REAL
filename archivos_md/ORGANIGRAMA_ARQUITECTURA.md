# Organigrama — Arquitectura y lógica de negocio

Documento de referencia (backend + frontend) para planear cambios sobre el módulo de Organigrama. Generado a partir de una revisión de código en ambos repos el 2026-07-16, actualizado el mismo día tras implementar: toggle Vista Institucional/Alineación, nivel "Enlace", layout de carriles horizontales por jerarquía, y reordenamiento de hermanos por drag-and-drop. Actualizado de nuevo el 2026-07-17 tras: permisos granulares por vista (`view_organigrama_institucional`/`_alineacion`/`_sig`, `edit_organigrama`) y Vista SIG agregados por un compañero, retiro del botón "Alineación" de la UI, reparación de nodos huérfanos en `subordinados` (ver §13-bis), una verificación de integridad que encontró y corrigió 2 gaps (SIG no era inmune a reordenamiento manual; condición de carrera al cambiar de vista rápido — §13-ter), la separación total Institucional/SIG en tablas distintas (`ORGANIGRAMA_ANAM_SIG`, §13-quater) para que tampoco el contenido pueda filtrarse entre vistas, y finalmente la reescritura de la exportación a PDF a 100% vectorial (§9-ter), reemplazando el enfoque rasterizado de un compañero.

> **Hallazgo estructural clave**: existen dos features distintos con "organigrama" en el nombre que **no comparten código**:
> 1. `/dashboard/organigrama` — el árbol jerárquico visual real. Es el objeto de este documento.
> 2. `AlineacionOrganizacionalTab.jsx` (subtab "Movimientos" de Plantilla de Empleados) — pese al nombre, es una tabla de auditoría MOV_POS vs EMPLEADOS_COMPLETOS_SIG, no dibuja ningún árbol ni usa los endpoints de organigrama. No se documenta aquí.

---

## 1. Modelo de datos (backend)

### `OrganigramaAnam` — `plantilla/models.py:969-1000`

Tabla legacy `ORGANIGRAMA_ANAM`, adoptada vía migración (`0024_adopt_organigrama_anam.py`, solo `state_operations`, sin DDL — la tabla ya existía en producción), poblada originalmente por el pipeline ZAFIRO.

| Campo | Rol |
|---|---|
| `departamento` (PK, CharField 255) | **"Determinante"**: código jerárquico que codifica la posición del nodo en el árbol. 10 u 11 caracteres, segmentado en 5 tramos G(eneral)/C(entral)/A(rea-Director)/S(ubdirección)/D(epto). Anchos: 11 chars → `[3,2,2,2,2]`; 10 chars → `[2,2,2,2,2]`. |
| `unidad_negocio` | Agrupa el "lienzo" completo de un organigrama (una Dirección General + todo su árbol). Parámetro de filtro principal del árbol. |
| `nivel_direccion` | Nivel textual: `Titular` > `General` > `Central` > `Director` > `Subdir.` > `Jefe Depto` > `Enlace` > `(en blanco)`. Orden numérico vía `LEVEL_ORDER` (Titular=7 … en blanco=0). `Enlace` es un nivel **puramente manual** (ver §6.11) sin tramo propio en el determinante — su código es el del padre + 2 dígitos, por lo que su longitud siempre es >11 (nunca choca con un código real de ZAFIRO). |
| `unidad_administrativa`, `doaf` | Metadatos descriptivos del nodo. |
| `num_posicion_gerente` | Nº de plaza del titular del nodo (resuelve ocupante). |
| `posicion_director` | Nº de plaza del jefe directo (fallback de resolución de padre). |
| `subordinados` (TextField, migración 0026) | **CSV de códigos hijos directos**. Es lo que el árbol lee en cada request (Vista Institucional) — ya no recalcula parentesco on-the-fly salvo fallback. El **orden** del CSV es ahora significativo: es el orden visual mostrado, reordenable por el usuario vía drag-and-drop (ver §9-bis) y persistido tal cual (ya no se re-ordena alfabéticamente al servir, ver §3). |
| `modificado_por`, `fecha_modificacion` (migración 0025) | Auditoría de ediciones. |

### Catálogos paralelos (no son el árbol)

- **`CatNivelJerarquicoPlaza`** (`plantilla/models.py:1065-1096`, tabla `cat_nivel_jerarquico_plaza`) — asigna un **nivel jerárquico numérico (0-8) por número de plaza**, independiente del árbol. Clasifica NJ de empleados, no construye jerarquía.
- **`NivelJerarquicoPrioridadConfig`** (singleton pk=1) — decide si la fuente de verdad del nivel es manual o `nvl_direc_origen` (ZAFIRO/MOV_POS).
- Enum `NIVELES_JERARQUICOS` (`models.py:1003-1019`): nivel 3 tiene **dos** descripciones válidas ("Director" / "Titular de Aduana") — la clave única es la descripción, no el número.
- **Riesgo de confusión conceptual**: `nivel_direccion` (textual, del árbol) y `nivel_jerarquico` (numérico, de plaza) son dos taxonomías distintas, no mapeadas entre sí en el código.

### Otras tablas que alimentan el árbol

- `MovPosLatest` (tabla `MOV_POS_LATEST`) — estado más reciente por plaza (`Estado Psn`), fuente de "¿está activa?".
- `EmpleadosCompletosSig` — datos del ocupante actual de una plaza.
- App `ua` (`UnidadAdministrativa`: solo `nombre`+`codigo`) — catálogo plano de enriquecimiento, no participa en la jerarquía del árbol.

---

## 2. Endpoints REST (`plantilla/views.py`)

| Ruta | View | Método | Notas |
|---|---|---|---|
| `organigrama-deptos/` | `OrganigramaDeptoView` (4234) | GET | Catálogo plano depto→descripción/nivel. Permiso `view_plantilla_catalogos`. |
| `organigrama-tree/?unidad_negocio=&vista=` | `OrganigramaTreeView` (4258) | GET | **Endpoint principal**. Construye el árbol JSON anidado. `vista` opcional: `"institucional"` (default, lee `ORGANIGRAMA_ANAM.subordinados`, editable) — o dos vistas de solo lectura que **fuerzan recálculo puro desde el determinante** (`forzar_recalculo=True`, ignoran `subordinados`, ver §3): `"alineacion"` (recalcula sobre `ORGANIGRAMA_ANAM` completa, ya sin botón propio en la UI, ver §7/§11) y `"sig"` (recalcula sobre `ORGANIGRAMA_ANAM_SIG`, una **tabla completamente aparte**, foto fija/inmune a cualquier edición manual — ver §13-quater). **Permiso por vista** (agregado por un compañero): cada valor de `vista` exige su propio permiso (`view_organigrama_institucional`/`_alineacion`/`_sig`) vía `request.user.has_perm(...)`, devuelve 403 si falta — ya no es el antiguo permiso único `view_organigrama` (deprecado/reemplazado). |
| `organigrama-posicion-info/?posicion=` | `OrganigramaPosicionInfoView` (4381) | GET | Activa/vacante/ocupante de una plaza puntual. |
| `organigrama-unidades/` | `OrganigramaUnidadesView` (4436) | GET | Catálogo dinámico de "unidades de negocio" (reemplazó un array estático que vivía en el frontend). |
| `organigrama-crear-nodo/` | `OrganigramaCrearNodoView` (4471) | POST | Alta de nodos (raíz o hijo) — ver §6. `edit_permission = "authentication.edit_organigrama"`. |
| `cat-organigrama-anam/` (+`<pk>/`) | `OrganigramaAnamViewSet` (4825) | CRUD | `LOCKED_UPDATE_FIELDS = (departamento, nivel_direccion, unidad_negocio)`; bloquea DELETE si hay hijos. PATCH a `subordinados` permitido pero validado como **permutación exacta** del valor actual (mismo conjunto de códigos, solo reordenados) — lo usa el drag-and-drop de reordenamiento de hermanos (§9-bis), rechaza con 400 cualquier intento de agregar/quitar códigos por esta vía. `view_permission`/`edit_permission` son tuplas OR: `view_plantilla_catalogos` **o** `view_organigrama_institucional` para leer; `view_plantilla_catalogos` **o** `edit_organigrama` para escribir (se usa desde 2 superficies: tab Catálogos y el árbol — ver §10). |
| `plantilla/organigrama_search/` | `OrganigramaSearchView` (3861) | GET `?q=` | Búsqueda plana sobre la tabla cruda; el frontend precarga **todo** el catálogo una vez con esto para buscar en memoria. Ahora también devuelve `isSIGInfo` por fila (para que el frontend filtre sugerencias de búsqueda según la vista activa, ver §7). |
| `empleados-search/` | `EmpleadosBusquedaView` (4716) | GET | Búsqueda de empleado para reasignar titular/superior. |

Endpoints relacionados pero **no** parte del árbol: `CadenaMandoView` (jerarquía paralela por `DependenciaDirecta` de empleado, CTE recursivo), `DesgloseJerarquicoView`/`Ocupados` (reportes tabulares, no árbol), `CuadroVacanciaView` (totalizador institucional).

### `OrganigramaTreeView` en detalle
1. Query param obligatorio `unidad_negocio`; `vista` opcional (default `"institucional"`).
2. Valida el permiso específico de la vista pedida (`VISTA_PERMISSIONS`) — 403 si falta.
3. Trae las filas de esa unidad (SQL crudo); si `vista == "sig"`, la consulta apunta a `ORGANIGRAMA_ANAM_SIG` (tabla aparte, sin filtro adicional — ver §13-quater) en vez de `ORGANIGRAMA_ANAM`. SIG también fuerza `forzar_recalculo=True` (igual que Alineación).
4. `_build_occupant_map`: 2 queries batch (no N+1) — `MOV_POS_LATEST` para activas + `EMPLEADOS_COMPLETOS_SIG` para el ocupante. Reglas:
   - No está en activas → `{activa: False, vacante: None}`.
   - Activa sin SMB/fila → `{activa: True, vacante: True}`.
   - Activa con ocupante → `{activa: True, vacante: False, nombre, nivel, smb}`.
5. Llama a `build_tree(rows, occupant_map, forzar_recalculo=(vista == "alineacion"))` de `organigrama_tree.py`.

---

## 3. Algoritmo del árbol — `plantilla/organigrama_tree.py`

Dos modos, seleccionados por `build_tree(data, occupant_map, forzar_recalculo=False)`:

### A) Vista Institucional (`forzar_recalculo=False`, default — el que corre en cada request salvo que se pida `vista=alineacion`)
- Si alguna fila trae `subordinados` no vacío, arma el árbol leyendo esa columna directo (`build_children_map_from_column`) — **O(n)**, sin recalcular parentesco, **preservando el orden del CSV tal cual** (es el orden reordenable por drag-and-drop, ver §9-bis).
- **Fallback**: si *ninguna* fila de la unidad tiene `subordinados` poblado, recae en el modo B (cálculo en vivo) para no romper la vista. ⚠️ Si solo *algunas* filas cambian y el resto conserva CSV viejo, el árbol puede quedar parcialmente inconsistente (el fallback solo se activa si *ninguna* fila tiene el campo).
- `find_root`: la fila con mayor `LEVEL_ORDER` (Titular > General); empate → código más corto/lexicográficamente menor.
- `build_tree_node`: recursión con `visited` set (evita ciclos si el CSV estuviera corrupto). **Ya NO reordena los hijos** — usa `by_parent.get(code, [])` tal cual (el orden ya lo decidió quien construyó `by_parent`: la columna CSV en este modo, o `build_children_map` ordenado en el modo B). Antes (antes de implementar el reordenamiento manual) siempre re-ordenaba por `(-LEVEL_ORDER, descripcion_larga)`, ignorando el orden real del CSV.

### B) Vista Alineación (`forzar_recalculo=True`, vía `?vista=alineacion`, y también el algoritmo que usa el management command) — cálculo puro desde el determinante, **solo lectura** en el frontend
- Antes de calcular, **filtra fuera todos los nodos `nivel_direccion == "Enlace"`** — ese nivel es puramente manual (no tiene tramo en el código de 5 segmentos), así que nunca aparece en esta vista, ni colgado de la raíz ni de nadie.
- `parse_code`: segmenta el código en 5 tramos según longitud (10 u 11 chars) — los códigos de `Enlace` (>11 chars) nunca llegan aquí porque ya fueron filtrados.
- `candidate_parents`: genera candidatos de código padre poniendo a cero el segmento más profundo no-cero, sucesivamente, filtrando contra los códigos existentes en la unidad.
- `resolve_by_position`: fallback — busca por `posicion_director` contra `num_posicion_gerente` de otras filas, desambiguando por mayor prefijo común + mayor `LEVEL_ORDER`.
- `build_parent_map`: orden de resolución de padre → 1) coincide con raíz → `None`; 2) `candidate_parents`; 3) `resolve_by_position`; 4) **caída segura a la raíz** si todo falla (nunca deja un nodo huérfano — puede esconder errores de datos legados en vez de exponerlos).
- `build_children_map`: arma `by_parent` desde `parent_map` y **aquí sí ordena** cada lista de hijos por `(-LEVEL_ORDER, descripcion_larga)` — en este modo no hay "orden elegido por el usuario" que preservar, así que se normaliza.
- Lógica portada de un pipeline externo/legacy (`Webwright_runs/generar_organigramas.py`, no presente en este repo).

### Comando `poblar_subordinados_organigrama`
Recorre cada `unidad_negocio`, corre el modo B completo (`build_parent_map`+`build_children_map`), escribe `subordinados` vía `bulk_update`.

⚠️ **Brecha operativa**: debe re-correrse **manualmente** cada vez que ZAFIRO reimporta `ORGANIGRAMA_ANAM` — no hay ningún hook automático que lo dispare (a diferencia de la sincronización de nivel jerárquico, que sí corre en cada ciclo). Si nadie lo re-corre tras un cambio estructural, el árbol servido queda desactualizado.

⚠️⚠️ **Este comando RECALCULA relaciones padre-hijo desde cero** (ignora el `subordinados` actual) — si se vuelve a correr después de que el equipo haya reordenado/reparentado nodos manualmente (o creado nodos `Enlace`), **destruye esas ediciones manuales**. No confundir con el comando nuevo de abajo.

### Comando nuevo `ordenar_subordinados_organigrama` (backfill, una sola vez)
Distinto del anterior: **no recalcula relaciones padre-hijo**, solo reordena el CSV `subordinados` EXISTENTE de cada fila con el criterio `(-LEVEL_ORDER, descripcion_larga)` — se corrió una vez al implementar el reordenamiento manual (para que el orden visual no "saltara" al quitar el reordenamiento automático de `build_tree_node`). Seguro de re-correr si hiciera falta (no destruye estructura manual, solo normaliza orden), pero no debería ser necesario de nuevo salvo un caso excepcional.

---

## 4. `ai_app/tools/organigrama.py` (tool del agente de IA)

- `buscar_organigrama(query, limite)` — **completamente independiente** de `organigrama_tree.py` y de las vistas REST.
- Escribe su propia consulta SQL cruda, casi idéntica a `OrganigramaSearchView` (mismo `SELECT ... FROM ORGANIGRAMA_ANAM WHERE descripcion_larga LIKE %s OR departamento LIKE %s`), pero con `LIMIT` parametrizable y formato de texto plano con emojis para el LLM.
- No reutiliza `build_tree`, no conoce `subordinados`, no calcula ocupación/vacancia.
- **Riesgo de duplicación/drift**: dos copias del mismo SQL — si cambia `OrganigramaSearchView`, esta tool no se actualiza sola.

---

## 5. Cacheo (Redis)

- **Ninguna vista de organigrama usa `cache.get/set`** (`OrganigramaTreeView`, `Deptos`, `Unidades`, `PosicionInfo`, `Search`, `CrearNodo`, `AnamViewSet`) — todas consultan en vivo. Probablemente porque `ORGANIGRAMA_ANAM` es pequeña y cambia poco (contraste con el resto del módulo `plantilla`, que sí cachea agresivo).
- `desglose_jerarquico`/`desglose_jerarquico_ocupados` (reportes tabulares, no el árbol) sí cachean 1200s, invalidados tras cada import ZAFIRO (`tasks.py:1362-1384`) y al aplicar prioridad de nivel jerárquico (`nivel_jerarquico_sync.py`).
- `obtener_posiciones_activas()` cachea 1200s pero **ninguna vista de organigrama la usa** — el árbol resuelve "activa" con su propia query directa a `MOV_POS_LATEST`, duplicando el criterio en vez de reutilizar esa función/cache.

---

## 6. Reglas de negocio no obvias

1. **El código PK codifica la jerarquía**: todo el árbol depende de parsear correctamente el "determinante" (segmentos G/C/A/S/D); longitud 10 vs 11 cambia los anchos.
2. **`"(en blanco)"` como centinela** de "sin nivel/sin posición" — comparaciones explícitas contra ese string literal en varios puntos.
3. **Caída segura a la raíz** si no se resuelve el padre — nunca deja nodos huérfanos, a costa de posiblemente esconder errores de datos.
4. **Creación de nodos estructurales** (`OrganigramaCrearNodoView._crear_hijo`, tipos General/Central/Director/Subdir./Jefe Depto):
   - Modo `"General"` = alta de raíz nueva (nuevo lienzo); requiere `unidad_negocio`+`departamento` a mano (códigos externos SAT/SIG).
   - Modo hijo: código autogenerado heredando segmentos del padre, poniendo a cero niveles saltados, siguiente número de 2 dígitos libre entre "hermanos". Si se agotan los 100 posibles → 409.
   - `LEVEL_SEGPOS = {General:0, Central:1, Director:2, Subdir.:3, Jefe Depto:4, Enlace:5}` valida que el hijo sea estrictamente más profundo que el padre (`target_pos <= parent_pos` → 400). "Titular" del padre se trata como posición 0 (caso especial no cubierto por el mapa).
   - Actualiza el CSV `subordinados` del padre en la misma transacción.
5. **Creación de nodos "Enlace"** (`OrganigramaCrearNodoView._crear_enlace`, rama separada de `_crear_hijo`): como el código determinante solo tiene 5 tramos y "Jefe Depto" ya ocupa el último, un `Enlace` **no ocupa tramo** — su código es literalmente `código_del_padre + 2 dígitos` (ej. `00200000001` → `0020000000101`), sea cual sea el nivel del padre (no hay regla estricta de que deba colgar de un Jefe Depto, aunque es el caso típico). Esto garantiza que el código nunca colisiona con uno real de ZAFIRO (siempre exactamente 10 u 11 chars). Un nodo Enlace es automáticamente terminal/hoja: ningún tipo de `LEVEL_SEGPOS` supera su valor (5), así que "Agregar subordinado" nunca ofrece opciones bajo un Enlace.
6. **`LOCKED_UPDATE_FIELDS`**: `departamento`, `nivel_direccion`, `unidad_negocio` no editables vía API una vez creado el nodo — para "mover"/"renivelar" hay que crear uno nuevo y eliminar el viejo. `subordinados` **sí es editable**, pero solo como permutación (ver §2) — es lo que habilita el reordenamiento manual de hermanos.
7. **Protección de borrado**: no se puede eliminar un nodo con hijos (409); al eliminar hoja se limpia la referencia del padre.
8. **Exclusiones no documentadas** en `DesgloseJerarquicoView`/`Ocupados`: plazas `LIKE '103L%'`, `LIKE '1039%'`, partida `'11401'` — sin comentario explicativo, a confirmar con negocio antes de replicar.
9. **~~Permiso `view_organigrama` declarado pero no conectado~~ — YA CORREGIDO**: un compañero reemplazó el permiso único `view_organigrama` por 4 permisos granulares (`authentication/models.py:53-56`): `view_organigrama_institucional`, `view_organigrama_alineacion`, `view_organigrama_sig`, `edit_organigrama`. Ahora sí están conectados server-side: `OrganigramaTreeView` valida el permiso específico de la `vista` pedida (403 si falta), `OrganigramaCrearNodoView`/`OrganigramaAnamViewSet` usan `edit_permission`/`view_permission` — ver §2/§11. El punto 2 de §14 (histórico) ya no aplica.
10. **Dos jerarquías paralelas coexisten**: la departamental (`ORGANIGRAMA_ANAM`) y la de cadena de mando por empleado (`CadenaMandoView` vía `DependenciaDirecta`) — sin garantía de que coincidan.
11. **`Enlace` es exclusivo de Vista Institucional**: nunca aparece en Vista Alineación (filtrado explícitamente en `build_tree`, ver §3) — es un nivel "manual" sin equivalente en el determinante oficial, por decisión de negocio explícita (no un accidente del algoritmo).

---

## 7. Frontend — Renderizado del árbol (`src/app/dashboard/organigrama/page.jsx`, ~2300 líneas)

Rediseñado por completo (ya no es la recursión anidada original — ver historial si hace falta el diseño viejo):

- Sin librería de árboles/gráficos (no D3, no react-flow) — pero tampoco recursión anidada: **layout de carriles horizontales por nivel jerárquico**.
- **`LANE_CONFIG`** (array a nivel de módulo): un carril por nivel en orden fijo (Titular, General, Central, Director, Subdir., Jefe Depto), más un carril catch-all etiquetado **"Enlace"** al final (`match: () => true`) que agrupa tanto los nodos reales de nivel `Enlace` como cualquier `nivel_direccion` no reconocido/vacío. `getLaneForLevel(nivel)` resuelve el carril de un nodo.
- **`treeLayout`** (`useMemo`): algoritmo de posicionamiento tipo árbol — hojas en posiciones X secuenciales (`SLOT_WIDTH` = ancho de tarjeta + gap), nodos internos centrados en el rango de sus hijos (post-order recursivo sobre `childrenByParent`, derivado del orden real de `node.subordinados`). Da `centerX` (Map departamento→x) y `totalWidth`.
- **`laneTopY`** (`useMemo`): posición Y acumulada de cada carril (`LABEL_ROW_HEIGHT` + `LANE_ROW_HEIGHT` + `LANE_GAP` por carril, en orden de `lanesToRender`). Junto con `treeLayout.centerX`, da un sistema de coordenadas **100% analítico** (calculado en JS, sin medir el DOM).
- **`visibleNodes`** (`useMemo`, separado del memo estructural de `allNodes`/`parentsMap` porque depende de `expandedNodes`): recorrido DFS que respeta expand/collapse (colapsar sigue ocultando toda la rama) y, durante un drag activo, sustituye el orden de los hijos del padre afectado por `previewOrder` (ver §9-bis) sin tocar `organigramaData`.
- **`lanesToRender`**: agrupa `visibleNodes` por carril (orden fijo de `LANE_CONFIG`, cada uno ordenado por el índice DFS), omitiendo carriles sin nodos visibles.
- **Extraídas a funciones puras module-level** (`computeVisibleNodes`/`computeLanesToRender`/`computeTreeLayout`/`computeLaneTopY`/`computeConnectors`, 2026-07-17): los 5 `useMemo` de arriba son ahora wrappers de 1 línea sobre estas funciones (mismos parámetros, mismo cuerpo). Se extrajeron para que la exportación a PDF (ver §9-ter) pueda invocarlas directo con un `expandedNodes` arbitrario (p.ej. "todo desglosado") **sin pasar por `setState`+esperar un re-render** — evita el problema de que la función de exportación, si leyera los valores memoizados del componente justo después de un `setExpandedNodes`, seguiría viendo los de antes del cambio hasta el siguiente render (closure obsoleto). `computeConnectors` devuelve `segments` crudos (`[x1,y1,x2,y2][]`) en vez de un `path` de SVG ya armado — tanto el `<path>` en pantalla (vía `segmentsToSvgPath`) como el dibujo vectorial del PDF consumen la misma geometría sin duplicar lógica de trazado.
- **`NodeCard`** (reemplaza al viejo `TreeNode`): tarjeta plana sin recursión, posicionada `absolute` dentro de su fila de carril según `treeLayout.centerX`. Cada carril es una fila horizontal continua (sin `flex-wrap`) que se desplaza con el scroll/drag del canvas.
- **Conectores**: overlay `<svg>` con un `<path>` por padre (no por arista) — un tronco baja del padre, un bus horizontal une el rango de sus hijos, y una vertical por hijo baja hasta su tarjeta (como un organigrama clásico); tolera hijos en carriles no adyacentes (niveles saltados) pasando visualmente detrás de las tarjetas intermedias (`z-index`). Coordenadas 100% analíticas (mismo sistema que `treeLayout`/`laneTopY`) — **deliberadamente no usa `getBoundingClientRect`**: medir con eso dentro de un contenedor con CSS `zoom` produce doble escalado (el propio SVG vive dentro del contenedor con `zoom`, así que una coordenada ya afectada por el zoom se reescala una segunda vez al pintarse) — bug real encontrado y corregido durante esta implementación.
- **Zoom**: CSS `zoom` (no `transform: scale`) sobre `#tree-capture-container`, rueda+Ctrl o botones +/-/reset, rango 0.3–2.0.
- **Pan**: drag-to-scroll manual, ignorado si el target es botón/input/`.cursor-pointer`.
- **Expand/collapse**: estado `expandedNodes`, toggle por doble clic o botón chevron; "Expandir/Colapsar Todo" en tarjeta flotante.
- **Toggle Institucional/SIG**: segmented control junto a "Colapsar Todo" (solo visible si el usuario tiene permiso para más de una vista, ver §11) — cambia `vistaModo` (`"institucional"`|`"sig"`), que se manda como `vista` al fetch de `organigrama-tree/`. Fuera de Institucional (`soloLectura = vistaModo !== "institucional"`), todas las acciones de edición quedan deshabilitadas (crear/editar/eliminar nodo, cambiar plaza, drag-and-drop) — mismo mecanismo `disabled`+`title` explicativo en cada botón, más un guard `if (soloLectura) return;` al inicio de cada handler real. El botón de **"Alineación" se retiró de la UI** (decisión de negocio: la Vista SIG de un compañero cumple ese rol para el equipo) — el backend sigue soportando `vista=alineacion` y el permiso `VIEW_ORGANIGRAMA_ALINEACION` sigue existiendo, solo no hay forma de llegar ahí desde el toggle.
- **Colores/badges por `nivel_direccion`**: definidos una sola vez en `LANE_CONFIG` (antes estaban triplicados en `TreeNode`/`SkeletonNode`/`OrganigramaSkeleton`, ya eliminados). Titular/General → `Building2` rosa; Central → `Network` rosa oscuro; Director → `Layers` ámbar; Subdir. → `Users` ámbar; Jefe Depto y el catch-all "Enlace" → `Briefcase` gris.
- Nodo seleccionado: borde rosa+ring. Nodo resaltado por búsqueda: borde ámbar+scale. Nodo objetivo de drop (drag-and-drop): borde rosa+ring (ver §9-bis).
- Skeleton de carga simplificado: unas pocas filas de tarjetas placeholder `animate-pulse` (ya no replica la lógica real de layout).

### Ocupante/vacante en la tarjeta
Cascada mostrada:
- Sin `num_posicion_gerente` o `"(en blanco)"` → "Sin plaza titular" (gris itálica).
- Con plaza pero `!ocupante || !ocupante.activa` → "Plaza inactiva" (rojo).
- `ocupante.vacante === true` → "Departamento vacante" (ámbar).
- Si no → nombre + Nivel + SMB (moneda MXN).

El modal de detalle (`PosicionOcupanteCard`) repite la cascada pero contra `posInfo` (de `organigrama-posicion-info/`, no del `ocupante` del árbol).

---

## 8. Frontend — Hooks/servicios → endpoints

Todo vía `PlantillaService`/`CatalogoEstructuraService` (`apiFetch`, inyecta cookie `auth_token`). **Sin TanStack Query/SWR** — `useState`+`useEffect` manual, sin caché real entre navegaciones (cambiar de unidad = fetch nuevo).

| Acción | Endpoint | Detalle |
|---|---|---|
| Carga unidades | `GET organigrama-unidades/` | Al montar. |
| Carga árbol | `GET organigrama-tree/?unidad_negocio=&vista=` | Al cambiar `selectedUnidad` o `vistaModo` (Institucional/Alineación). |
| Preload catálogo búsqueda | `GET plantilla/organigrama_search/` | Una sola vez, trae todo el catálogo plano. |
| Info plaza titular/superior | `GET organigrama-posicion-info/?posicion=` | 2 llamadas al seleccionar nodo. |
| Búsqueda empleado (reasignar/nuevo subordinado) | `GET empleados-search/?q=` | Debounce 300ms, mín. 3 caracteres. |
| Cambiar plaza titular/superior | `PATCH cat-organigrama-anam/{departamento}/` | `{num_posicion_gerente}` o `{posicion_director}`. |
| Crear Dirección General / subordinado | `POST organigrama-crear-nodo/` | Ver §9. |
| Editar nodo | `PATCH cat-organigrama-anam/{departamento}/` | Solo `{descripcion_larga, unidad_administrativa, doaf}`. |
| Eliminar nodo | `DELETE cat-organigrama-anam/{departamento}/` | — |
| Reordenar hermanos (drag-and-drop) | `PATCH cat-organigrama-anam/{departamento_del_padre}/` | `{subordinados: "cod1,cod2,..."}` — ver §9-bis. |

**Patrón "actualización optimista sin refetch"**: tras un cambio, el código **muta el objeto `allNodes[departamento]` en sitio** (mutación directa, no inmutable) y fuerza re-render con `bumpRender`, en vez de recargar `organigrama-tree/` — deliberado para no perder `expandedNodes`/scroll, pero el árbol en memoria puede divergir sutilmente del backend hasta el próximo cambio de unidad o refresh (ej.: al crear subordinado sin seleccionar empleado, la tarjeta muestra "Plaza inactiva" hasta recargar la página, por comentario explícito en el código).

Toast "cambio confirmado, revertir" con `onUndo` (segundo PATCH restaurando valor previo), autodescarta a los 10s.

---

## 9. Frontend — Creación de nodos (dos modales)

**a) "Nueva Dirección General"** (raíz nueva):
- Campos: `unidad_negocio*`, `departamento*` (texto libre, advertencia de "captúralos tal cual" por ser códigos oficiales externos), `descripcion_larga*`, `unidad_administrativa`, `doaf`, `num_posicion_gerente` (opcional).
- Validación cliente: solo no-vacíos tras `trim()` — **sin validar formato/longitud del código**, delegado 100% al backend.
- Éxito → recarga `organigrama-unidades/`, selecciona la nueva unidad, resetea zoom.

**b) "Agregar subordinado"** bajo el nodo seleccionado:
- `tipo*`: `<select>` que solo ofrece tipos de `TIPO_LABELS` (`Central`, `Director`, `Subdir.`, `Jefe Depto`, **`Enlace`**) con `LEVEL_SEGPOS` **estrictamente mayor** al del padre — replica en cliente la regla de negocio del backend (comentado explícitamente en el código, con referencia a `organigrama_tree.py`). El botón mismo solo aparece si hay al menos un tipo válido para ese nivel. Como `Enlace` tiene el `LEVEL_SEGPOS` más alto (5), es la **única** opción que aparece bajo un Jefe Depto (antes de agregar Enlace, el botón ni siquiera se mostraba ahí); bajo niveles más altos aparece junto con los tipos estructurales normales (no hay regla estricta de que solo cuelgue de un Jefe Depto).
- `descripcion_larga*`; `unidad_administrativa`/`doaf` opcionales.
- Plaza titular opcional: buscador de empleado o modo manual "vacante por número" (valida contra `organigrama-posicion-info/`).
- Éxito → inserta el nodo en el árbol en memoria (sin refetch), expande el padre, resalta/selecciona/scroll al nuevo nodo.
- Deshabilitado por completo en Vista Alineación (`soloLectura`).

---

## 9-bis. Frontend — Reordenar hermanos por drag-and-drop (con previsualización en vivo)

Fase 1 de una funcionalidad de reordenamiento planeada en dos fases (Fase 2 = re-parenteo, aún no implementada — ver plan histórico si hace falta el diseño). Solo reordena hermanos del **mismo padre**, nunca cambia relaciones padre-hijo — por eso no hay riesgo de romper la jerarquía (ej. que un Director dependa de una Subdirección).

- **`draggable={!soloLectura}`** en cada `NodeCard`; deshabilitado en Vista Alineación como el resto de acciones de edición.
- **`onDragStart`**: guarda el código en `draggingCode` y llama `e.dataTransfer.setData("text/plain", ...)` — imprescindible en Firefox (sin esto, `dragover` funciona pero `drop` puede no dispararse nunca; bug real encontrado durante la implementación).
- **`onDragOver`** (deduplicado vía un `ref` para no recalcular en cada `mousemove`): si el nodo bajo el cursor es hermano del que se arrastra (mismo `parentsMap`), calcula con `reorderSiblings(...)` (función pura, módulo-level) cómo quedaría el nuevo orden y lo guarda en `previewOrder = { parentCode, order: [...] }` — **sin mutar `organigramaData`**. Si no es hermano (distinto padre), limpia `previewOrder` (fase 1 no re-parenta).
- **Previsualización en vivo**: `visibleNodes` (el `useMemo` que recorre el árbol respetando expand/collapse) consume `previewOrder` — cuando llega al nodo padre en cuestión, sustituye el orden real de `node.subordinados` por el de `previewOrder.order` solo para ese recorrido. Como `treeLayout`/`laneTopY`/conectores son puros derivados de `visibleNodes`, todo el árbol (posiciones y líneas) se reacomoda visualmente en vivo mientras se arrastra, sin ningún side-effect ni llamada al backend.
- **`onDrop`**: confirma exactamente el `previewOrder` vigente (no recalcula desde cero, así "lo que se ve" es "lo que se guarda") — muta `parent.subordinados` en sitio (mismo patrón optimista que crear/editar/eliminar) + `bumpRender`, y persiste vía `PATCH cat-organigrama-anam/{padre}/` con `{subordinados: "...","}`. Si el backend rechaza (ej. carrera con otra edición), revierte el estado optimista.
- **`onDragEnd`**: limpia `draggingCode`/`dragOverCode`/`previewOrder` — si el drag se cancela (soltar fuera de una tarjeta válida), la previsualización desaparece sin dejar rastro (nunca se mutó nada real).
- Backend: ver §2/§6.6 (`LOCKED_UPDATE_FIELDS`) — el PATCH de `subordinados` se valida como permutación exacta del conjunto actual.

---

## 9-ter. Frontend — Exportación a PDF (100% vectorial, reescrita 2026-07-17)

Un compañero había implementado una primera versión que **rasterizaba** el árbol completo (`html-to-image` → `toSvg`/`toCanvas` → recorte por franjas a pixelRatio 4 → `jsPDF.addImage(..., "PNG")`). Funcionaba pero seguía siendo una imagen de ancho de píxeles finito: por más que se subiera la resolución, en algún nivel de zoom siempre terminaba pixelándose (justo el problema que el usuario ya había descartado explícitamente antes, ver plan histórico de PDF). Se reescribió por completo, sin conservar nada de ese enfoque salvo el botón/modal que lo dispara.

### Cómo funciona ahora
`handleExportPdf(type)` **ya no toca el DOM ni captura nada**: llama directo a las funciones puras `computeVisibleNodes`/`computeLanesToRender`/`computeTreeLayout`/`computeLaneTopY`/`computeConnectors` (las mismas que usan los `useMemo` en pantalla, ver §7) con el `expandedNodes` que corresponda al alcance elegido —

- **"Vista Actual"**: el `expandedNodes` real del componente.
- **"Todo Desglosado"**: un objeto sintético con todos los códigos de `allNodes` en `true`, calculado al vuelo — **sin llamar `setExpandedNodes`**. Como las funciones de layout son puras (no hooks), no hace falta esperar un re-render ni medir nada; se evita por completo la vieja necesidad de `await` + doble `requestAnimationFrame` para "esperar a que React pinte".

Con el layout resultante (`treeLayout`/`laneTopY`/`connectors`/`lanesToRender`), `buildOrganigramaPdf(...)` arma un `jsPDF` **dibujando directo con sus primitivas vectoriales** (`rect`/`roundedRect`/`text`/`line`/`setLineDashPattern`) — nunca genera ni pega una imagen. Cada tarjeta se dibuja con `drawOrganigramaCardPdf(...)`, reproduciendo el mismo contenido que `NodeCard` (badge de nivel, título con wrap a 2 líneas vía `splitTextToSize`, cascada ocupante/vacante/plaza inactiva idéntica a §7, footer con código+plaza), y los conectores/divisores de carril se trazan con los mismos `segments`/coordenadas que el `<svg>` en pantalla.

- **Página única** dimensionada exactamente al contenido (`treeLayout.totalWidth`/`laneTopY.totalHeight` + margen, convertido px→pt a 96dpi). Si excede `PDF_MAX_DIM_PT` (~194in, techo práctico de compatibilidad de lectores PDF) se reduce la escala física **uniformemente** — al ser vectorial, achicar la página no pierde nitidez: el lector puede hacer zoom arbitrario sobre los mismos trazos.
- **Nada de estados interactivos**: el PDF siempre dibuja las tarjetas en su estilo neutro (nunca reproduce selección/hover/drag-over) — es un documento, no una captura de pantalla.
- El modal/botón ("Exportar PDF" → "Vista Actual"/"Todo Desglosado") no cambió; solo cambió qué hace `handleExportPdf` internamente.
- Import `toSvg` de `html-to-image` eliminado de este archivo (ya no se usa aquí); el paquete sigue instalado porque `CuadrosVacanciaTab.jsx` lo usa para otra cosa (`toPng`, exportación de un tab no relacionado).

Verificado con un smoke test standalone (árbol sintético de 9 nodos vía Node+jsPDF, fuera del navegador): conteo de nodos visibles, agrupado por carril, `centerX`/`totalWidth`, un conector por padre con sus segmentos, y generación real del PDF sin excepciones — más una inspección visual del PDF resultante confirmando tarjetas, badges por color de carril, conectores correctamente enrutados y divisores de carril con etiqueta, todo como texto/trazos vectoriales reales (no una imagen).

### Bug encontrado y corregido el mismo día: texto amontonado en árboles grandes con "Todo Desglosado"
Primera versión probada en real por el usuario contra la unidad `00900` (454 áreas): el PDF se generaba nítido, pero el contenido de cada tarjeta salía amontonado/ilegible (badge, título, ocupante, footer todos superpuestos), mientras que en árboles chicos (el smoke test de 9 nodos) se veía perfecto.

**Causa**: `drawOrganigramaCardPdf` tenía un piso de tamaño de fuente (`fs = (px) => Math.max(T(px), 4)`, "nunca bajar de 4pt") pensado para que el texto no quedara ilegiblemente chico. El problema es que ese piso **no aplicaba al interlineado/separaciones** (`T(13)`, `T(12)`, `T(16)`, etc., sin piso) — en árboles grandes exportados como "Todo Desglosado" (~250+ tarjetas hoja), `scale` se reduce mucho para que la página quepa en el techo físico de un PDF (~194in/14000pt), y el interlineado encogía junto con `scale` mientras el tamaño de fuente se quedaba fijo en el piso de 4pt: el resultado eran líneas más altas que el espacio asignado entre ellas → texto superpuesto.

**Fix**: se quitó el piso por completo (`fs = (px) => T(px)`, igual que en la etiqueta de carril) — tamaño de fuente e interlineado escalan siempre en la misma proporción, así nunca se amontonan, sin importar qué tan chico deba quedar `scale`. Al ser 100% vectorial esto no es una pérdida real de legibilidad: un tamaño nominal pequeño en el PDF sigue siendo trazos vectoriales reales, así que el lector puede acercar el zoom todo lo necesario sin perder nitidez — exactamente la razón por la que se pidió que fuera vectorial en primer lugar.

Verificado reproduciendo el bug con un smoke test sintético de 284 nodos (41 direcciones × 6 jefaturas, aproximando la proporción real de `00900`) antes y después del fix — con `scale≈0.258` el título quedaba en ~1.8pt de fuente real (sin piso) y, al renderizar el PDF a 600dpi con `pdftoppm` y recortar sobre una tarjeta, el contenido se ve completamente legible y sin superposición.

---

## 10. Frontend — Edición/eliminación (dos superficies no sincronizadas)

### a) Dentro del árbol
- Modal "Editar": solo `descripcion_larga`, `unidad_administrativa`, `doaf` — coincide con `LOCKED_UPDATE_FIELDS` del backend, y el propio código lo documenta con comentario explícito. Aviso visible al usuario: "Nivel jerárquico y unidad de negocio no son editables aquí... crea el nodo correcto y elimina este."
- Eliminar: botón deshabilitado si el nodo tiene subordinados (validación de UI redundante con el bloqueo real del backend).
- Plaza titular/superior se edita aparte vía `PosicionOcupanteCard`.

### b) Tab "Catálogos" de Plantilla de Empleados (`CatalogosEstructuraTab.jsx` + `catalogosConfig.js:123-161`)
Tabla CRUD genérica (misma UI que `cat-acciones`, `cat-pto-func`, etc.) apuntando también a `cat-organigrama-anam/`, **totalmente independiente del árbol visual**.

⚠️ **Discrepancia UI/backend**: solo `departamento` está marcado `disabledOnEdit: true`. **`unidad_negocio` y `nivel_direccion` NO están marcados** — el formulario genérico los deja editables (incluso pegables por clic-derecho), y se envían en el PATCH. Si el backend los descarta silenciosamente (que es lo que hace `LOCKED_UPDATE_FIELDS`), el usuario no se entera de que su cambio no se aplicó — no hay feedback explícito de "este campo no se guardó".

Esta tabla también permite crear/eliminar departamentos directo (POST/DELETE), **sin** la validación de `LEVEL_SEGPOS` que sí aplica el árbol — un segundo camino de alta/baja sin esa regla de negocio en cliente.

---

## 11. Frontend — Permisos (rediseñado por un compañero — ya no es un único permiso)

El antiguo `PERMISSIONS.VIEW_ORGANIGRAMA` único se reemplazó por 4 permisos granulares (`src/config/permissions.js:29-32`, mapeados 1:1 a `authentication/models.py:53-56`):

| Permiso frontend | Codename backend | Gatea |
|---|---|---|
| `VIEW_ORGANIGRAMA_INSTITUCIONAL` | `view_organigrama_institucional` | Ver Vista Institucional (árbol manual/curado, editable). |
| `VIEW_ORGANIGRAMA_ALINEACION` | `view_organigrama_alineacion` | Ver Vista Alineación (recalculada desde el determinante) — **ya sin botón en la UI** (ver §7/§9-bis), pero el permiso y el backend siguen existiendo. |
| `VIEW_ORGANIGRAMA_SIG` | `view_organigrama_sig` | Ver Vista SIG (filtrada a `isSIGInfo=1`, solo lectura). |
| `EDIT_ORGANIGRAMA` | `edit_organigrama` | Crear/editar/eliminar nodos y cambiar plaza titular/superior (solo aplica en Vista Institucional). |

- **Sí están conectados server-side** (a diferencia de lo que decía la versión anterior de este documento — ver §6.9): `OrganigramaTreeView.get()` valida `request.user.has_perm(VISTA_PERMISSIONS[vista])` y devuelve 403 si falta; `OrganigramaCrearNodoView`/`OrganigramaAnamViewSet` usan `edit_permission`/`view_permission` (tuplas OR con `view_plantilla_catalogos`, para no romper a quien ya editaba desde el tab Catálogos).
- **Frontend**: `canViewInstitucional`/`canViewSig` (`hasPermission(...)`) deciden qué botones del toggle se muestran (`[canViewInstitucional, canViewSig].filter(Boolean).length > 1` — si el usuario solo tiene acceso a una vista, ni siquiera se muestra el selector). Un `useEffect` fuerza `vistaModo` a la única vista permitida en cuanto cargan los permisos (mismo patrón que `activeTab` en `plantilla_empleados`). `canEditOrganigrama` (`EDIT_ORGANIGRAMA`) se combina con `vistaModo !== "institucional"` para calcular `soloLectura`.
- `<RequirePermission permission={[VIEW_ORGANIGRAMA_INSTITUCIONAL, VIEW_ORGANIGRAMA_ALINEACION, VIEW_ORGANIGRAMA_SIG]}>` sigue gateando la entrada a la página completa (basta con tener AL MENOS UNO de los 3) — redirige silenciosamente a `/dashboard` si no hay ninguno.
- El tab "Alineación Organizacional" (el otro feature con "organigrama" en el nombre, ver nota al inicio del documento) usa un permiso completamente distinto (`VIEW_PLANTILLA_MOVIMIENTOS`), sin relación con estos 4.

---

## 12. Frontend — Lógica de UI no obvia

- **Búsqueda de área**: en memoria sobre el catálogo global precargado (`organigrama_search/`, una vez) — no golpea el backend por tecla. Navegación con flechas+Enter. Si el resultado está en otra `unidad_negocio`, cambia de lienzo automáticamente y hace scroll al nodo una vez cargado.
- **Exportar a PDF** (100% vectorial, ver §9-ter): modo "Vista Actual" o "Todo Desglosado" (recalcula el layout con todos los códigos expandidos, sin tocar el estado real del componente).
- **Stats** (conteo por nivel): calculado client-side sobre el árbol completo cargado (aplanado memoizado), no solo lo visible.
- **Drag-and-drop de reordenamiento** (fase 1, ver §9-bis): reordena hermanos del mismo padre con previsualización en vivo. **Re-parenteo** (mover un nodo a un padre distinto arrastrando) sigue sin implementar — mover a otro padre todavía requiere eliminar y recrear.

---

## 13. Relación con hooks compartidos del módulo `plantilla_empleados`

- El árbol (`/dashboard/organigrama`) es **100% independiente** — no importa ningún hook de `plantilla_empleados/_hooks` (`useAdvancedFilters`, `useColumnFilters`, `useColumnState`, etc.). Vive en su propia ruta, fuera de ese árbol de componentes.
- `useOrganigramaCatalog` (compartido por 4 tabs de `plantilla_empleados`: Movimientos, Bajas, Mov. Posiciones, Plantilla Detalle) es un catálogo de **decoración** (código→nombre/nivel) sobre `organigrama-deptos/`, con caché a nivel de módulo (`cachedCatalogPromise`) para pedirlo una sola vez sin importar cuántos componentes lo monten. No tiene relación con el árbol visual.

---

## 13-bis. Incidente: nodos "huérfanos" en Vista Institucional (2026-07-17)

**Síntoma reportado**: Vista Institucional mostraba exactamente lo mismo que Vista SIG (mismo conteo de nodos, mismo contenido) — los cambios manuales del equipo (nodos creados vía "Agregar subordinado") no aparecían en ningún lado.

**Causa real**: no era un bug del toggle de vistas ni de caché — ambas vistas leen `subordinados` para armar el árbol (Institucional sin filtro, SIG filtrando a `isSIGInfo=1` antes de aplicar el mismo algoritmo, ver §3). El problema es que **154 filas de la unidad `00900`** (y unas pocas más en `00003`/`00700`) existían en `ORGANIGRAMA_ANAM` pero **nunca estaban referenciadas en el `subordinados` de ningún padre** — es decir, el algoritmo de árbol (camina desde la raíz siguiendo esos enlaces) nunca las alcanzaba, sin importar la vista. `modificado_por`/`fecha_modificacion` de esas filas apuntaban a ediciones reales y recientes del equipo (`sharon.leyva@anam.gob.mx` y otros), confirmando que eran los cambios manuales "perdidos".

⚠️ **Causa raíz del enlace roto: no confirmada a nivel de código.** Se revisó `OrganigramaCrearNodoView._crear_hijo`/`_crear_enlace` (el flujo de "Agregar subordinado", que el usuario reportó como origen) y **sí actualiza correctamente** el `subordinados` del padre dentro de la misma transacción — no se encontró un bug reproducible en ese código. Cómo exactamente se perdieron esos enlaces queda como pregunta abierta (posible condición de carrera si se crearon varios hermanos muy rápido sin refrescar entre uno y otro, alguna edición previa que haya sobreescrito `subordinados`, u otra causa aún no identificada). Si vuelve a ocurrir, vale la pena revisar con más detalle el momento exacto en que se pierde el enlace (ej. agregando logging temporal a `_crear_hijo`/`_crear_enlace`).

**Diagnóstico y reparación** (ver management command nuevo, no confundir con los otros dos que ya existían):
- `reparar_huerfanos_organigrama` (`plantilla/management/commands/`): para cada `unidad_negocio`, encuentra las filas no alcanzables desde la raíz vía `subordinados`, identifica cuáles son "raíz de su propia rama" (nadie las referencia — las demás se resuelven solas en cuanto se reconecta esa raíz), resuelve su padre real con el mismo algoritmo de segmentación que usa Vista Alineación (`candidate_parents`/`resolve_by_position`), y **solo si ese padre ya es alcanzable**, agrega el código al `subordinados` de ese padre — nunca modifica un enlace que ya existe, solo agrega los que faltan. Seguro de re-correr (es idempotente: si ya no hay huérfanos, no hace nada).
- Aplicado el 2026-07-17 sobre datos reales: `00900` (81 de 154 huérfanos reconectados directamente, el resto se resolvió solo) y `00003` (1 de 1) quedaron en 0 huérfanos, verificado contra el endpoint real (`institucional` pasó de 300 a 454 nodos en `00900`, coincidiendo con el total de filas de esa unidad).
- **`00700` quedó pendiente**: tiene 40 filas huérfanas pero **ninguna es "raíz"** (todas están referenciadas por alguien) — es decir, forman una o más ramas cerradas sobre sí mismas (posible referencia circular, ej. A referencia a B y B referencia a A) que el comando detecta y **omite automáticamente** en vez de intentar resolver a ciegas. Requiere inspección manual antes de repararse (ver huérfanos de esa unidad con el mismo patrón de diagnóstico usado arriba: caminar desde la raíz, listar los no alcanzados, y en este caso además detectar el ciclo).

---

## 13-ter. Verificación final de integridad (2026-07-17) — 2 gaps encontrados y corregidos

A pedido del usuario, se verificaron 4 garantías sobre el comportamiento del módulo, con pruebas reales (no solo lectura de código) contra la base de datos vía `APIRequestFactory`/`force_authenticate`. Dos de las cuatro tenían un gap real, ambos corregidos en el momento:

1. **Institucional persiste todo (crear/editar/eliminar/reordenar)** — confirmado sin cambios: cada acción ya hacía su PATCH/POST propio (ver §8/§9/§9-bis), no se encontró ningún caso donde una escritura no se guardara.

2. **SIG debe ser 100% inmune a cambios manuales — GAP ENCONTRADO Y CORREGIDO EN DOS PASADAS**:
   - **Primera pasada**: se probó reordenar (drag-and-drop) dos hermanos que SÍ tenían `isSIGInfo=1` ("datos oficiales") y **la Vista SIG reflejó el reordenamiento manual** — porque `vista=sig` solo filtraba qué FILAS incluir (`WHERE isSIGInfo=1`), pero seguía leyendo el `subordinados` editable de esas filas. Fix inicial: `forzar_recalculo=(vista in ("alineacion", "sig"))` — esto blindó estructura/orden, pero **no el contenido** (editar `descripcion_larga` de un nodo `isSIGInfo=1` seguía viéndose en SIG, porque ambas vistas leían la MISMA fila).
   - **Segunda pasada (definitiva, ver §13-quater)**: se creó una tabla completamente separada `ORGANIGRAMA_ANAM_SIG`, poblada una sola vez (foto fija) con los valores de hoy — Institucional y SIG ya no comparten ninguna fila ni columna. Confirmado con prueba real: reordenar hermanos Y editar `descripcion_larga` de un nodo oficial desde Institucional **no cambia absolutamente nada** en SIG, mientras Institucional refleja ambos cambios con normalidad.

3. **Cambio de vista confiable, sin resultados a medias — GAP ENCONTRADO Y CORREGIDO**: el `useEffect` que hace fetch del árbol al cambiar `vistaModo`/`selectedUnidad` no tenía guard de cancelación — si el usuario cambiaba de vista muy rápido (ej. Institucional→SIG→Institucional), una respuesta lenta de un fetch viejo podía llegar después y pisar los datos de la vista ya seleccionada, dejando en pantalla contenido que no correspondía al botón resaltado. **Fix**: se agregó el mismo patrón `let cancelled = false` / `return () => { cancelled = true }` que ya usaban otros 2 efectos de este mismo archivo (carga de unidades, búsqueda de empleado) — cualquier respuesta que llegue después de que el efecto se haya "cancelado" (por un cambio posterior de vista/unidad) se descarta en vez de aplicarse.

4. **Drag-and-drop no rompe la estructura (no desvincula padre-hijo)** — confirmado con una prueba de estrés: 5 reordenamientos consecutivos con orden aleatorio sobre el mismo padre (simulando arrastres rápidos seguidos) no perdieron ninguna fila (454 antes y después) ni desconectaron ningún nodo de la raíz (454 alcanzables antes y después). Esto se sostiene porque: (a) el frontend solo permite reordenar si `parentsMap[origen] === parentsMap[destino]` (mismo padre exacto, nunca re-parenta), y (b) el backend valida que el PATCH sea una permutación exacta del conjunto ya existente (§2/§6.8) — una reordenación nunca puede, por construcción, agregar/quitar/mover un código a otro padre, solo cambiar su posición dentro de la misma lista.
   - Nota aparte (no es un incidente, es un riesgo conocido de concurrencia): si **dos personas** reordenan hermanos del **mismo padre** casi al mismo tiempo desde dos sesiones distintas, es un `read-modify-write` sin bloqueo — quien guarda último "gana" el orden completo de ese padre, pudiendo descartar silenciosamente la preferencia de orden de la otra persona. Esto **no rompe la estructura** (nunca se pierde un nodo ni se desvincula nada, ver punto 4), solo podría perderse *cuál de los dos órdenes* quedó guardado. No se corrigió porque no es lo que se preguntó (integridad estructural) y el caso de uso (edición simultánea del mismo padre en el mismo instante) es poco común hoy.

---

## 13-quater. Separación total Institucional/SIG: tabla `ORGANIGRAMA_ANAM_SIG` (2026-07-17)

Para cerrar el límite que dejó pendiente §13-ter punto 2 (SIG inmune a estructura/orden, pero no a contenido), se creó una tabla nueva y completamente independiente, exclusiva de Vista SIG.

### Investigación previa (importante para no repetir supuestos)
- `isSIGInfo` **no tiene ningún proceso vivo que lo actualice** — no el pipeline ZAFIRO (`plantilla/tasks.py` no toca `ORGANIGRAMA_ANAM` en absoluto), no ningún management command, no ninguna señal. Es una foto fija fijada una vez, sin origen reconstruible desde el código.
- **Tampoco tenía migración propia**: el campo se agregó al modelo (`models.py`) sin generar el `AddField` correspondiente — un bug de historial de migraciones pre-existente (no introducido por esta sesión). `makemigrations` lo detectó recién al crear la tabla nueva.
- Se decidió (con el usuario) **acotar el alcance solo al árbol** (`OrganigramaTreeView`) — `OrganigramaDeptoView` (catálogo de decoración de Movimientos/Bajas) y `OrganigramaSearchView` (sugerencias de búsqueda) **siguen usando el `isSIGInfo` de `ORGANIGRAMA_ANAM` exactamente igual que antes**, sin cambios — no se tocaron para no arriesgar romper algo que ya funcionaba y no era parte de la queja.

### Qué se creó
- **Modelo `OrganigramaAnamSig`** (`plantilla/models.py`, junto a `OrganigramaAnam`) — tabla nueva `ORGANIGRAMA_ANAM_SIG`, 100% gestionada por Django (a diferencia de `OrganigramaAnam`, que es legacy adoptada). Campos: `departamento` (PK), `descripcion_larga`, `nivel_direccion`, `unidad_negocio`, `unidad_administrativa`, `doaf`, `num_posicion_gerente`, `posicion_director` — **sin `subordinados`** (SIG siempre recalcula desde el determinante, nunca necesita leer esa columna).
- **Migración `0029_organigramaanamsig.py`**: `CreateModel` normal para la tabla nueva, más un `SeparateDatabaseAndState` (solo estado, sin DDL real) que registra formalmente `isSIGInfo` en el historial de Django — corrige el bug de migración faltante sin ejecutar ningún `ALTER TABLE` (la columna ya existe físicamente), mismo patrón que ya usa `0024_adopt_organigrama_anam.py` para esta misma tabla legacy. Verificado con `makemigrations --check --dry-run` → `No changes detected` tras aplicarla.
- **Management command `congelar_organigrama_sig`** (mismo estilo que `poblar_subordinados_organigrama`/`reparar_huerfanos_organigrama`): copia las filas `ORGANIGRAMA_ANAM.isSIGInfo=1` de HOY a `ORGANIGRAMA_ANAM_SIG` (trunca y repuebla, no hace merge). Corrido una vez: **1365 filas congeladas** (todas las unidades de negocio, no solo `00900`). No hay pipeline vivo que lo re-dispare — si se necesita "resetear" la foto SIG en el futuro, hay que volver a correrlo a mano.
- **`OrganigramaTreeView.get()`**: cuando `vista == "sig"`, el `SELECT` ya no apunta a `ORGANIGRAMA_ANAM` con `WHERE isSIGInfo=1` — apunta directo a `ORGANIGRAMA_ANAM_SIG` (tabla completa = conjunto SIG, sin filtro adicional). Sigue pasando `forzar_recalculo=True` para esa vista (por claridad/consistencia, aunque la tabla nueva ni siquiera tiene columna `subordinados` que pudiera leerse por error).

### Qué NO cambió (deliberado)
- `OrganigramaDeptoView`, `OrganigramaSearchView`, `OrganigramaAnamViewSet`, la columna `isSIGInfo` en `ORGANIGRAMA_ANAM` — intactos, siguen funcionando exactamente igual que antes de esta sesión.
- El frontend (`page.jsx`) — **cero cambios**. El contrato del endpoint (`GET organigrama-tree/?unidad_negocio=&vista=sig`) no cambió de forma, solo de dónde saca los datos internamente.

### Verificado con prueba real end-to-end
Reordenar hermanos oficiales + editar `descripcion_larga` de un nodo oficial vía PATCH real sobre `ORGANIGRAMA_ANAM` → SIG no cambió ni el orden ni el contenido; Institucional reflejó ambos cambios de inmediato; se restauraron los valores de prueba al terminar. Conteos de nodos sin cambios respecto a antes de esta sesión: Institucional 454, SIG 300, Alineación 451 (unidad `00900`).

---

## 14. Puntos a revisar antes de implementar cambios

1. **Consistencia `subordinados` vs re-cómputo**: si se van a hacer cambios masivos a `ORGANIGRAMA_ANAM` fuera del flujo normal (import manual, script), recordar correr `poblar_subordinados_organigrama` — no hay hook automático.
2. ~~Permiso `view_organigrama` sin aplicar en backend~~ — **YA RESUELTO** por un compañero (ver §6.9/§11): ahora hay 4 permisos granulares conectados server-side.
3. **Discrepancia de campos editables** entre el modal del árbol (respeta `LOCKED_UPDATE_FIELDS`) y la tabla CRUD genérica de Catálogos (no los deshabilita) — decidir si se corrige el formulario genérico o se documenta como comportamiento aceptado.
4. **Duplicación de SQL** entre `OrganigramaSearchView` (backend) y `ai_app/tools/organigrama.py` (tool IA) — si cambia una query, sincronizar la otra manualmente.
5. **Mutación optimista en memoria**: cualquier cambio a la lógica de creación/edición debe considerar que el árbol en cliente no se resincroniza con el backend hasta cambiar de unidad o refrescar — bugs de estado divergente son fáciles de introducir aquí.
6. **Dos taxonomías de nivel no mapeadas** (`nivel_direccion` textual del árbol vs `nivel_jerarquico` numérico de plaza) — si un cambio pretende unificarlas o cruzarlas, no hay mapeo existente en código a reutilizar.
7. **No usar `getBoundingClientRect` dentro de `#tree-capture-container`** para nada relacionado al layout — ese contenedor tiene CSS `zoom` aplicado, y cualquier medición vía esa API ya viene post-zoom; si se vuelve a usar como coordenada para posicionar/dibujar algo DENTRO del mismo contenedor, el navegador la reescala una segunda vez (bug real, ya corregido: los conectores SVG ahora son 100% analíticos vía `treeLayout`/`laneTopY`, no medidos).
8. **Reordenar hermanos (`subordinados`) es la única escritura que el backend valida como permutación** — cualquier endpoint/flujo nuevo que también escriba `subordinados` (ej. la futura Fase 2 de re-parenteo) debe decidir explícitamente si reutiliza esa validación o la reemplaza (re-parenteo SÍ necesita cambiar el conjunto, no solo el orden).
9. **`poblar_subordinados_organigrama` vs `ordenar_subordinados_organigrama` vs `reparar_huerfanos_organigrama`**: tres comandos con nombres parecidos y comportamiento muy distinto (el primero recalcula estructura completa y destruye ediciones manuales/Enlaces; el segundo solo reordena sin tocar estructura; el tercero solo agrega enlaces faltantes sin tocar los existentes) — confirmar cuál se necesita antes de correr cualquiera en un ambiente con datos manuales. Ver §13-bis para el incidente que motivó el tercero.
10. **`00700` sigue con 40 nodos huérfanos sin reparar** (ciclo/referencia circular, no resuelto por `reparar_huerfanos_organigrama` a propósito) — pendiente de diagnóstico manual, ver §13-bis.
11. **Causa raíz de cómo se pierden enlaces en `subordinados` sigue sin confirmarse** (ver §13-bis) — si vuelve a aparecer el mismo síntoma (Institucional "igual" a SIG/con menos nodos de los esperados), correr `reparar_huerfanos_organigrama` como mitigación inmediata, pero seguiría pendiente encontrar la causa de fondo para prevenir que vuelva a pasar.
