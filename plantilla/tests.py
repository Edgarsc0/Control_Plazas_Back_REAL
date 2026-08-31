"""
Pruebas de la reconstrucción de la línea de tiempo de titularidad de aduanas.

Son SimpleTestCase: plantilla/rotacion_aduanas.py es lógica pura y no toca la
base, así que estas pruebas corren sin base de datos y protegen exactamente lo
que es fácil de romper — sobre todo la renumeración de unidades del 2022-07-01,
que no se nota a simple vista porque sigue produciendo 50 columnas.
"""

import datetime

from django.test import SimpleTestCase

from .rotacion_aduanas import (
    FECHA_RENUMERACION,
    SALIDA_ACTIVO,
    SALIDA_BAJA,
    SALIDA_OTRO_PUESTO,
    SALIDA_TRASLADO,
    construir_catalogo_previo,
    construir_rotacion,
    normalizar_unidad,
)

HOY = datetime.date(2026, 8, 29)

# Recorte del catálogo real de EMPLEADOS_COMPLETOS_SIG.
CATALOGO = {
    "123": "Aduana de Altamira con sede en Tamaulipas",
    "124": "Aduana de Cancún con sede en Quintana Roo",
    "105": "Aduana de Ciudad Juárez con sede en Chihuahua",
    "150": "Aduana de México con sede en la Ciudad de México",
    "113": "Aduana de Nuevo Laredo con sede en Tamaulipas",
}

_SIGUIENTE_ID = [1]


def mov(empleado, fecha, un_admin, desc_larga_un, accion="XFR", motivo="INT",
        cd_puesto="AD3004", posicion="10000001", sec=0, **extra):
    """Arma una fila de cp_tbl_mov_completo con lo mínimo que usa el algoritmo."""
    _SIGUIENTE_ID[0] += 1
    fila = {
        "id": _SIGUIENTE_ID[0],
        "num_empleado": empleado,
        "nombre": "Nombre",
        "ap_pat": "Apellido",
        "ap_mat": empleado,
        "fecha_efectiva": fecha,
        "sec": sec,
        "un_admin": un_admin,
        "desc_larga_un": desc_larga_un,
        "accion": accion,
        "accion_nombre": accion,
        "motivo": motivo,
        "motivo_nombre": motivo,
        "cd_puesto": cd_puesto,
        "posicion": posicion,
        "fecha_captura": fecha,
        "por": "TEST",
        "nivel_tabular": "A205",
        "sal_base": 100000,
        "sexo": "H",
    }
    fila.update(extra)
    return fila


def aduanas_por_nombre(resultado):
    return {a["aduana"]: a for a in resultado["aduanas"]}


class NormalizacionTest(SimpleTestCase):
    def test_colapsa_el_doble_espacio_de_desc_larga_un(self):
        # desc_larga_un trae dos espacios antes de "con sede" y el catálogo no.
        # Sin normalizar, las dos fuentes nunca empatan.
        self.assertEqual(
            normalizar_unidad("Aduana de Cancún  con sede en Quintana Roo"),
            "Aduana de Cancún con sede en Quintana Roo",
        )

    def test_tolera_none(self):
        self.assertEqual(normalizar_unidad(None), "")


class CatalogoPrevioTest(SimpleTestCase):
    def test_deriva_la_numeracion_vieja_solo_de_filas_anteriores(self):
        movimientos = [
            mov("A", datetime.date(2022, 1, 1), "123", "Aduana de Cancún con sede en Quintana Roo"),
            mov("A", datetime.date(2022, 3, 1), "123", "Aduana de Cancún con sede en Quintana Roo"),
            mov("B", datetime.date(2023, 1, 1), "123", "Aduana de Altamira con sede en Tamaulipas"),
        ]
        previo = construir_catalogo_previo(movimientos)
        self.assertEqual(previo["123"], "Aduana de Cancún con sede en Quintana Roo")

    def test_toma_la_etiqueta_dominante_cuando_hay_ruido(self):
        movimientos = [
            mov("A", datetime.date(2022, 1, 1), "105", "Aduana de Torreón con sede en Coahuila"),
            mov("B", datetime.date(2022, 2, 1), "105", "Aduana de Torreón con sede en Coahuila"),
            mov("C", datetime.date(2022, 3, 1), "105", "Etiqueta suelta"),
        ]
        previo = construir_catalogo_previo(movimientos)
        self.assertEqual(previo["105"], "Aduana de Torreón con sede en Coahuila")


class RenumeracionTest(SimpleTestCase):
    """El código 123 era Cancún y pasó a ser Altamira el 2022-07-01."""

    def _movimientos(self):
        return [
            # Titular que entra a Cancún bajo el código viejo 123 y sigue ahí
            # después de la renumeración, ya bajo el código nuevo 124.
            mov("EMP1", datetime.date(2022, 1, 1), "123",
                "Aduana de Cancún con sede en Quintana Roo", accion="HIR", motivo="PIT"),
            mov("EMP1", datetime.date(2023, 1, 1), "124",
                "Aduana de Cancún con sede en Quintana Roo", accion="PAY", motivo="ADJ"),
            # Titular distinto que entra a Altamira ya con la numeración nueva.
            mov("EMP2", datetime.date(2023, 6, 1), "123",
                "Aduana de Altamira con sede en Tamaulipas", posicion="20000002"),
        ]

    def test_el_mismo_codigo_no_junta_dos_aduanas(self):
        resultado = construir_rotacion(self._movimientos(), CATALOGO, HOY)
        nombres = {a["aduana"] for a in resultado["aduanas"]}
        self.assertEqual(nombres, {CATALOGO["124"], CATALOGO["123"]})

    def test_el_titular_que_no_se_movio_conserva_una_sola_gestion(self):
        # EMP1 nunca cambió de aduana: el código cambió de nombre debajo de él.
        # Sin el catálogo por época esto aparecería como un traslado falso.
        resultado = construir_rotacion(self._movimientos(), CATALOGO, HOY)
        cancun = aduanas_por_nombre(resultado)[CATALOGO["124"]]
        self.assertEqual(cancun["total_gestiones"], 1)
        self.assertEqual(cancun["gestiones"][0]["fecha_entrada"], datetime.date(2022, 1, 1))
        self.assertEqual(cancun["gestiones"][0]["tipo_salida"], SALIDA_ACTIVO)

    def test_no_inventa_traslados_en_la_fecha_de_renumeracion(self):
        resultado = construir_rotacion(self._movimientos(), CATALOGO, HOY)
        traslados = [
            g for a in resultado["aduanas"] for g in a["gestiones"]
            if g["tipo_salida"] == SALIDA_TRASLADO
        ]
        self.assertEqual(traslados, [])

    def test_la_fecha_de_corte_pertenece_al_catalogo_nuevo(self):
        # Una fila fechada exactamente el 2022-07-01 ya usa la numeración nueva.
        movimientos = [
            mov("EMP1", datetime.date(2022, 1, 1), "123",
                "Aduana de Cancún con sede en Quintana Roo"),
            mov("EMP1", FECHA_RENUMERACION, "123",
                "Aduana de Altamira con sede en Tamaulipas"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        self.assertEqual(
            [a["aduana"] for a in resultado["aduanas"]],
            sorted([CATALOGO["123"], CATALOGO["124"]]),
        )


class SegmentacionTest(SimpleTestCase):
    def test_el_par_te1_re1_del_mismo_dia_no_corta_la_titularidad(self):
        # Fin y reingreso de nombramiento el 1 de enero, distinguidos por sec.
        movimientos = [
            mov("EMP1", datetime.date(2023, 5, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("EMP1", datetime.date(2024, 1, 1), "113", CATALOGO["113"],
                accion="TE1", motivo="LTC", sec=0),
            mov("EMP1", datetime.date(2024, 1, 1), "113", CATALOGO["113"],
                accion="RE1", motivo="FX1", sec=1),
            mov("EMP1", datetime.date(2024, 7, 1), "113", CATALOGO["113"], accion="EXT"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        gestiones = aduanas_por_nombre(resultado)[CATALOGO["113"]]["gestiones"]
        self.assertEqual(len(gestiones), 1)
        self.assertEqual(gestiones[0]["tipo_salida"], SALIDA_ACTIVO)
        self.assertEqual(gestiones[0]["total_movimientos"], 4)

    def test_la_baja_y_el_alta_del_mismo_dia_no_parten_al_titular_saliente(self):
        # Ordenando por empleado, el alta del sucesor nunca se interpone en la
        # racha del saliente aunque comparta fecha_efectiva y sec.
        dia = datetime.date(2025, 7, 16)
        movimientos = [
            mov("SALE", datetime.date(2023, 7, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("SALE", datetime.date(2024, 9, 1), "113", CATALOGO["113"], accion="PAY"),
            mov("SALE", dia, "113", CATALOGO["113"], accion="TER", motivo="MUT", sec=0),
            mov("ENTRA", dia, "113", CATALOGO["113"], accion="XFR", motivo="IN2", sec=0),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        gestiones = aduanas_por_nombre(resultado)[CATALOGO["113"]]["gestiones"]
        self.assertEqual(len(gestiones), 2)
        self.assertEqual(gestiones[0]["total_movimientos"], 3)
        self.assertEqual(gestiones[0]["tipo_salida"], SALIDA_BAJA)
        self.assertEqual(gestiones[0]["fecha_salida"], dia)
        self.assertEqual(gestiones[1]["fecha_entrada"], dia)

    def test_clasifica_los_cuatro_tipos_de_salida(self):
        movimientos = [
            # Traslado a otra aduana.
            mov("EMP1", datetime.date(2022, 8, 1), "105", CATALOGO["105"], accion="XFR"),
            mov("EMP1", datetime.date(2023, 8, 1), "150", CATALOGO["150"], accion="XFR"),
            # Baja del sistema.
            mov("EMP2", datetime.date(2023, 1, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("EMP2", datetime.date(2024, 1, 1), "113", CATALOGO["113"],
                accion="TER", motivo="MUT"),
            # Salida hacia otro puesto: sigue en la ANAM pero deja la titularidad.
            mov("EMP3", datetime.date(2023, 2, 1), "124", CATALOGO["124"], accion="XFR"),
            mov("EMP3", datetime.date(2024, 2, 1), "100", "Dirección General de Operación Aduanera",
                accion="XFR", cd_puesto="AD3059"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        # EMP1 tiene dos gestiones, así que la clave es (empleado, aduana).
        tipos = {
            (g["num_empleado"], a["aduana"]): g["tipo_salida"]
            for a in resultado["aduanas"] for g in a["gestiones"]
        }
        self.assertEqual(tipos[("EMP1", CATALOGO["105"])], SALIDA_TRASLADO)
        self.assertEqual(tipos[("EMP1", CATALOGO["150"])], SALIDA_ACTIVO)
        self.assertEqual(tipos[("EMP2", CATALOGO["113"])], SALIDA_BAJA)
        self.assertEqual(tipos[("EMP3", CATALOGO["124"])], SALIDA_OTRO_PUESTO)
        # El destino de EMP3 es un puesto de oficinas centrales, no una aduana:
        # no debe aparecer como columna.
        self.assertNotIn("Dirección General de Operación Aduanera",
                         {a["aduana"] for a in resultado["aduanas"]})

    def test_la_salida_por_traslado_apunta_a_la_aduana_destino(self):
        movimientos = [
            mov("EMP1", datetime.date(2022, 8, 1), "105", CATALOGO["105"], accion="XFR"),
            mov("EMP1", datetime.date(2023, 8, 1), "150", CATALOGO["150"], accion="XFR"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        juarez = aduanas_por_nombre(resultado)[CATALOGO["105"]]
        self.assertEqual(juarez["gestiones"][0]["salida_destino_unidad"], CATALOGO["150"])
        # Y la gestión destino registra de dónde vino.
        mexico = aduanas_por_nombre(resultado)[CATALOGO["150"]]
        self.assertEqual(
            mexico["gestiones"][0]["origen"],
            {"tipo": "ADUANA", "valor": CATALOGO["105"]},
        )

    def test_un_titular_puede_volver_a_la_misma_aduana(self):
        movimientos = [
            mov("EMP1", datetime.date(2022, 8, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("EMP1", datetime.date(2023, 8, 1), "105", CATALOGO["105"], accion="XFR"),
            mov("EMP1", datetime.date(2024, 8, 1), "113", CATALOGO["113"], accion="XFR"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        laredo = aduanas_por_nombre(resultado)[CATALOGO["113"]]
        self.assertEqual(laredo["total_gestiones"], 2)


class VacanciasTest(SimpleTestCase):
    def test_calcula_el_hueco_entre_dos_gestiones(self):
        movimientos = [
            mov("EMP1", datetime.date(2023, 1, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("EMP1", datetime.date(2024, 10, 1), "113", CATALOGO["113"],
                accion="TER", motivo="MUT"),
            mov("EMP2", datetime.date(2025, 1, 1), "113", CATALOGO["113"],
                accion="HIR", motivo="FIX"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        vacancias = aduanas_por_nombre(resultado)[CATALOGO["113"]]["vacancias"]
        self.assertEqual(len(vacancias), 1)
        self.assertEqual(vacancias[0]["dias"], 92)
        self.assertFalse(vacancias[0]["abierta"])
        self.assertEqual(vacancias[0]["sale"], "Apellido EMP1 Nombre")
        self.assertEqual(vacancias[0]["entra"], "Apellido EMP2 Nombre")

    def test_el_relevo_el_mismo_dia_no_genera_vacancia(self):
        dia = datetime.date(2025, 7, 16)
        movimientos = [
            mov("EMP1", datetime.date(2023, 1, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("EMP1", dia, "113", CATALOGO["113"], accion="TER", motivo="MUT"),
            mov("EMP2", dia, "113", CATALOGO["113"], accion="XFR", motivo="IN2"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        self.assertEqual(aduanas_por_nombre(resultado)[CATALOGO["113"]]["vacancias"], [])

    def test_la_ultima_gestion_cerrada_deja_una_vacancia_abierta(self):
        movimientos = [
            mov("EMP1", datetime.date(2023, 1, 1), "113", CATALOGO["113"], accion="XFR"),
            mov("EMP1", datetime.date(2026, 7, 21), "113", CATALOGO["113"],
                accion="TER", motivo="MUT"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        aduana = aduanas_por_nombre(resultado)[CATALOGO["113"]]
        self.assertEqual(len(aduana["vacancias"]), 1)
        self.assertTrue(aduana["vacancias"][0]["abierta"])
        self.assertEqual(aduana["vacancias"][0]["dias"], 39)
        self.assertIsNone(aduana["titular_actual"])

    def test_una_aduana_con_titular_no_tiene_vacancia_abierta(self):
        movimientos = [
            mov("EMP1", datetime.date(2023, 1, 1), "113", CATALOGO["113"], accion="XFR"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        aduana = aduanas_por_nombre(resultado)[CATALOGO["113"]]
        self.assertEqual(aduana["vacancias"], [])
        self.assertEqual(aduana["titular_actual"], "Apellido EMP1 Nombre")
        self.assertEqual(aduana["titular_desde"], datetime.date(2023, 1, 1))


class OverrideMovPosTest(SimpleTestCase):
    """El caso real de la plaza 10334530 el 2022-07-01."""

    def _movimientos(self):
        return [
            # La plaza es de Cancún, pero estas dos filas conservaron el código
            # viejo 123, que bajo el catálogo nuevo apunta a Altamira.
            mov("SALE", datetime.date(2022, 1, 1), "123",
                "Aduana de Cancún con sede en Quintana Roo",
                accion="HIR", motivo="PIT", posicion="10334530"),
            mov("SALE", FECHA_RENUMERACION, "123",
                "Aduana de Altamira con sede en Tamaulipas",
                accion="TER", motivo="MUT", posicion="10334530"),
            mov("ENTRA", FECHA_RENUMERACION, "123",
                "Aduana de Altamira con sede en Tamaulipas",
                accion="XFR", motivo="INT", posicion="10334530"),
            mov("ENTRA", datetime.date(2022, 8, 1), "124",
                "Aduana de Cancún con sede en Quintana Roo",
                accion="ORG", motivo="REO", posicion="10334530"),
        ]

    def test_sin_override_aparece_una_gestion_fantasma_en_altamira(self):
        resultado = construir_rotacion(self._movimientos(), CATALOGO, HOY)
        nombres = {a["aduana"] for a in resultado["aduanas"]}
        self.assertIn(CATALOGO["123"], nombres)

    def test_el_override_devuelve_las_filas_a_cancun(self):
        def adscripcion(posicion, fecha):
            # MOV_POS: la plaza ya estaba renumerada a 124 (Cancún) ese día.
            if posicion == "10334530" and fecha >= FECHA_RENUMERACION:
                return ("124", "Alineación Organizacional")
            return ("123", "Nueva Posición")

        resultado = construir_rotacion(
            self._movimientos(), CATALOGO, HOY, adscripcion_plaza=adscripcion
        )
        nombres = {a["aduana"] for a in resultado["aduanas"]}
        self.assertEqual(nombres, {CATALOGO["124"]})
        self.assertEqual(resultado["filas_corregidas_por_mov_pos"], 2)

        cancun = aduanas_por_nombre(resultado)[CATALOGO["124"]]
        self.assertEqual(cancun["total_gestiones"], 2)
        # La gestión del sucesor arranca el día de la renumeración, no un mes
        # después como quedaría sin corregir.
        self.assertEqual(cancun["gestiones"][1]["fecha_entrada"], FECHA_RENUMERACION)
        self.assertTrue(cancun["gestiones"][1]["corregida_por_mov_pos"])

    def test_no_corrige_un_cambio_de_adscripcion_real(self):
        # Un titular que causa baja el mismo día que su plaza cambia de
        # adscripción es simultaneidad, no un error: la baja sigue siendo de
        # Nuevo Laredo.
        movimientos = [
            mov("EMP1", datetime.date(2022, 1, 1), "113", CATALOGO["113"],
                accion="HIR", posicion="10300081"),
            mov("EMP1", datetime.date(2023, 3, 16), "113", CATALOGO["113"],
                accion="TER", motivo="MUT", posicion="10300081"),
        ]

        def adscripcion(posicion, fecha):
            if fecha >= datetime.date(2023, 3, 16):
                return ("400", "Cmbio Adscripción s/Cambio Sal")
            return ("113", "Nueva Posición")

        resultado = construir_rotacion(
            movimientos, CATALOGO, HOY, adscripcion_plaza=adscripcion
        )
        self.assertEqual(resultado["filas_corregidas_por_mov_pos"], 0)
        self.assertEqual([a["aduana"] for a in resultado["aduanas"]], [CATALOGO["113"]])


class FormaDeLaRespuestaTest(SimpleTestCase):
    def test_expone_los_totales_y_los_codigos_de_unidad(self):
        movimientos = [
            mov("EMP1", datetime.date(2022, 1, 1), "123",
                "Aduana de Cancún con sede en Quintana Roo", accion="HIR"),
            mov("EMP1", datetime.date(2023, 1, 1), "124",
                "Aduana de Cancún con sede en Quintana Roo", accion="PAY"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        self.assertEqual(resultado["corte"], HOY)
        self.assertEqual(resultado["total_aduanas"], 1)
        self.assertEqual(resultado["total_gestiones"], 1)
        self.assertEqual(resultado["total_titulares"], 1)

        aduana = resultado["aduanas"][0]
        self.assertEqual(aduana["aduana_corta"], "Cancún")
        self.assertEqual(aduana["codigos_ua"], ["123"])
        self.assertEqual(aduana["plazas"], ["10000001"])
        self.assertEqual(aduana["gestiones"][0]["dias_gestion"], (HOY - datetime.date(2022, 1, 1)).days)

    def test_el_nombre_corto_quita_el_prefijo_y_la_sede(self):
        movimientos = [
            mov("EMP1", datetime.date(2023, 1, 1), "150", CATALOGO["150"], accion="HIR"),
        ]
        resultado = construir_rotacion(movimientos, CATALOGO, HOY)
        self.assertEqual(resultado["aduanas"][0]["aduana_corta"], "México")
