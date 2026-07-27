# Fotos de empleados — Análisis de la carga inicial (2026-07-24)

Carpeta: `media/empleados_fotos/` — **14,305 archivos confirmados** (coincide con el total esperado).

## Resumen por categoría

| Categoría | Cantidad | Resolución |
|---|---|---|
| Nombre limpio `<numempleado>.{jpg,jpeg,png,JPG,JPEG,PNG}` | ~13,277 | Match directo, sin ambigüedad. |
| Mismo número con variantes (`-1`, `-2`, `_back`, `.jpeg`+`.jpg`, etc.) | 121 archivos / 59 números | 57 grupos sí tienen una versión limpia junto con la variante — se usa esa y se ignora la variante. **2 grupos no tienen versión limpia** (ver abajo) → revisión manual. |
| Con forma de RFC/CURP (ej. `NAMU010412.jpg`) | 831 | Se cruza automáticamente contra el campo RFC del empleado (tabla `EmpleadoFotoAlias`, ver plan). |
| Sin ningún patrón reconocible | 76 | **Omitidos de la carga automática** — no hay forma segura de saber a quién pertenecen. Revisión manual. |

**Total: 13,277 + 121 + 831 + 76 = 14,305** ✓

---

## Archivos que requieren revisión manual (78 en total)

### A) Sin ningún patrón reconocible (76) — no se intentó ningún match automático

```
ALFONSO GILBERT LOPEZ LLORENS.jpg
BADENROL 26.jpg
BADENROL 37.jpg
BADENROL0.jpg
BADENROL1.jpg
BADENROL10.jpg
BADENROL11.jpg
BADENROL13.jpg
BADENROL14.jpg
BADENROL15.jpg
BADENROL16.jpg
BADENROL17.jpg
BADENROL18.jpg
BADENROL19.jpg
BADENROL2.jpg
BADENROL20.jpg
BADENROL21.jpg
BADENROL3.jpg
BADENROL31.jpg
BADENROL4.jpg
BADENROL5.jpg
BADENROL6.jpg
BADENROL7.jpg
BADENROL8.jpg
BADENROL9.jpg
CAPO01620.jpg
CARLOS EMILIANO MARTINEZ MARTINEZ.jpg
CUCEE980708.jpg
DANIELA TERAN RUVALCABA.jpg
DDIPA680607.jpg
DELLO20916.jpg
DEOPI681130.jpg
DIAL61111.jpg
ENRIQUE GOMEZ RESENDIZ.jpg
ERIK GERADO GARCIA TELLEZ.jpg
ERROR.jpg
EVA780313.jpg
GAK010609.jpg
GORCE900219.jpg
Guadalajara.zip          <- no es una foto, es un .zip
HLJ740216.jpg
IGNACIO RAMIREZ HERNANDEZ.jpg
ISAAC ALEJO HERNANDEZ.jpg
JACOBO DEL ANGEL SOSA.jpg
JGJ941125.jpg
JORGE RODOLFO LOPEZ RODRIGUEZ.jpg
JUAN JOSE RESENDIZ HERNANDEZ.JPG
LOG981016.jpg
LUIS ALBERTO MONROY REYES.jpg
MAHB00422.jpg
MARIA DE LOURDES ARREOLA GARCIA.JPG
MIA590116.jpg
MILOS.jpg
MILOS222.jpg
OMAR DIAZ GALVAN.jpg
PAULINA ORTEGA GARCIA.jpg
PRUEBA.jpg               <- probablemente un archivo de prueba, no una foto real
QJ921030.jpg
Queretaro.zip            <- no es una foto, es un .zip
RESD78011.jpg
RIR021004.jpg
ROG991101.jpg
ROJZ0103.jpg
RUI031106.jpg
SAGM.jpg
SS-RH.jpg
TEME96.jpg
THOMAS MURPHIN ARTEAGA.JPG
VEVC CARLOS JAVIER.jpg
VMI040702.jpg
alex _tonatiu.jpg
bad enrol 30.jpg
desktop.ini               <- no es una foto, es basura de Windows
marin.jpg
noooj980426.jpg
rae810130.jpg
```

**Nota:** `desktop.ini`, `Guadalajara.zip`, `Queretaro.zip` y `PRUEBA.jpg` casi seguro no son fotos de empleados — probablemente se puedan borrar directamente en vez de investigarlos.

### B) Grupos con variantes SIN ninguna versión limpia (2) — necesitan que elijas cuál es la correcta

```
20221139  -> 20221139-777.jpg   |   20221139-O.jpg
2025129   -> 2025129-2.jpg      |   2025129-3.jpg
```

---

## Regla de desempate aplicada automáticamente (57 grupos, sin necesidad de revisión)

Cuando existen varios archivos para el mismo número de empleado, se usa la versión **sin sufijo** (`<num>.jpg`/`.JPG`/`.jpeg`/`.png`) y se ignoran las demás (`_back`, `_1`, `_2`, `-1`, `-2`, `(2)`, `BAD ENROL`, `NO ES`, etc.) — esas variantes casi siempre son reversos de credencial, reintentos o marcas de "esta no sirve".

Ejemplos ya resueltos así (57 de 59 grupos):
```
202203182   -> se usa 202203182.jpg          (se ignora 202203182_back.jpg)
202321137   -> se usa 202321137.jpg          (se ignora "202321137 BAD ENROL.jpg")
20260913    -> se usa 20260913.jpg           (se ignora "20260913___NO ES.jpg")
20251183    -> se usa 20251183.jpg           (se ignora "20251183-bad enrol 1.jpg")
```

---

## Arquitectura de resolución (pensada para que la carpeta crezca sola, sin mantenimiento)

Ver discusión completa en la conversación con Claude — resumen:

1. **Resolución en vivo, sin tabla, para el caso estándar**: el endpoint de foto busca directo en disco `<numempleado>.{jpg,jpeg,png,JPG,JPEG,PNG}`. Cualquier foto nueva que se copie a la carpeta con ese nombre queda disponible de inmediato — sin ningún job de sincronización, sin depender de que corra celery.
2. **Tabla `EmpleadoFotoAlias`** — solo para las ~890 excepciones históricas (831 con forma de RFC + 57 grupos con variantes) cuyo nombre de archivo real no coincide con el número de empleado. Se llena UNA vez con el comando de carga masiva.
3. **Convención obligatoria hacia adelante**: toda foto nueva debe subirse como `<numempleado>.<ext>`. Si eso se respeta, la tabla de alias nunca vuelve a crecer y el sistema se mantiene solo indefinidamente.
