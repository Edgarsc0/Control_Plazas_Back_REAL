from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings

from .models import PlantillaQuincenal, Plantilla1800Plazas, EmpleadosCompletosSig, MovPos
from django.db.models import Count, Q, Sum, Case, When, IntegerField, Max, Subquery, OuterRef
from django.db.models.expressions import RawSQL

LATEST_MOVPOS_RAW_SQL = """
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY `Nº Pos Actual` 
            ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
        ) as rn
        FROM MOV_POS
    ) ranked WHERE rn = 1
"""

OCUPADAS_RAW_SQL = """
    SELECT                                                                                                                                                           
        e.`Posición`
    FROM EMPLEADOS_COMPLETOS_SIG e
    INNER JOIN MOV_POS m 
        ON e.`Posición` = m.`Nº Pos Actual`
    INNER JOIN (
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY `Nº Pos Actual`
                ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
            ) as rn
            FROM MOV_POS
        ) ranked WHERE rn = 1
    ) latest ON m.id = latest.id
    WHERE m.`Estado Psn` = 'A' AND `Estado Nómina` <> ' ' AND `Estado Nómina` IS NOT NULL;
"""

from django.core.cache import cache
from django.db import connection

def obtener_posiciones_activas():
    # Cache active position codes for 60 seconds to speed up parallel requests on page load
    cache_key = "active_position_codes"
    cached_val = cache.get(cache_key)
    if cached_val is not None:
        return cached_val

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT `Nº Pos Actual` FROM (
                SELECT `Nº Pos Actual`, `Estado Psn`, ROW_NUMBER() OVER (
                    PARTITION BY `Nº Pos Actual` 
                    ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                ) as rn
                FROM MOV_POS
            ) ranked WHERE rn = 1 AND `Estado Psn` = 'A'
        """)
        result = [row[0] for row in cursor.fetchall() if row[0]]
        
    cache.set(cache_key, result, 1200)
    return result


# Create your views here.
import io
import pandas as pd
from django.http import HttpResponse
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment

class ExportExcelView(APIView):
    """
    Vista genérica para exportar datos JSON a un archivo Excel (.xlsx) real con estilos institucionales.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        filename = request.query_params.get('filename', 'Export.xlsx')

        if not data or not isinstance(data, list):
            return Response(
                {"error": "Se requiere una lista de objetos para exportar."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Convertir JSON a DataFrame de Pandas
            df = pd.DataFrame(data)

            # Crear el archivo Excel en memoria
            output = io.BytesIO()
            
            # Forzar conversión de todas las columnas a tipos básicos para evitar errores de serialización
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna('')

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Plantilla')
                
                workbook = writer.book
                worksheet = writer.sheets['Plantilla']

                # --- ESTILOS ROBUSTOS ---
                # Usamos códigos ARGB completos (FF + Hex) para máxima compatibilidad
                header_fill = PatternFill(start_color="FF621F32", end_color="FF621F32", fill_type="solid")
                zebra_fill = PatternFill(start_color="FFF9FAFB", end_color="FFF9FAFB", fill_type="solid")
                header_font = Font(color="FFFFFFFF", bold=True, size=11, name='Calibri')
                data_font = Font(size=10, name='Calibri')
                
                side = Side(style='thin', color="FFD1D5DB")
                thin_border = Border(left=side, right=side, top=side, bottom=side)

                align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
                align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

                # --- PROCESAR ENCABEZADOS ---
                for col_num, column_title in enumerate(df.columns, 1):
                    cell = worksheet.cell(row=1, column=col_num)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.border = thin_border
                    cell.alignment = align_center
                    
                    # Cálculo de ancho ultra-seguro
                    try:
                        # Obtenemos el máximo largo de los datos en esta columna
                        # Filtramos nulos y convertimos a string antes de medir
                        lengths = df[column_title].astype(str).map(len)
                        max_val_len = lengths.max() if not lengths.empty else 0
                        
                        # Manejo de NaN o valores no numéricos en el cálculo
                        if pd.isna(max_val_len): max_val_len = 0
                        
                        header_len = len(str(column_title))
                        final_width = max(float(max_val_len), float(header_len)) + 3
                        
                        worksheet.column_dimensions[get_column_letter(col_num)].width = min(final_width, 60)
                    except:
                        worksheet.column_dimensions[get_column_letter(col_num)].width = 20

                # --- PROCESAR DATOS ---
                # Limitamos el procesamiento de estilos si el dataset es masivo para evitar timeouts
                max_styled_rows = 5000 
                rows_to_process = min(len(df), max_styled_rows)

                for row_num in range(2, rows_to_process + 2):
                    is_zebra = row_num % 2 == 0
                    for col_num in range(1, len(df.columns) + 1):
                        cell = worksheet.cell(row=row_num, column=col_num)
                        cell.border = thin_border
                        cell.alignment = align_left
                        cell.font = data_font
                        if is_zebra:
                            cell.fill = zebra_fill

                # Congelar paneles
                worksheet.freeze_panes = 'B2'

            output.seek(0)
            file_data = output.read()

            if not file_data:
                raise ValueError("El archivo generado está vacío.")

            # Preparar la respuesta HTTP
            response = HttpResponse(
                file_data,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response

        except Exception as e:
            # Loguear el error en la consola del servidor para diagnóstico
            import traceback
            traceback.print_exc()
            return Response(
                {"error": "Fallo crítico al generar Excel", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlantillaVacantesPorNivelView(APIView):
    permission_classes = [IsAuthenticated]

    # Devuelve el resumen de las posiciones ocupadas y vacantes por nivel
    def get(self, request):
        cache_key = "plantilla_vacantes_por_nivel"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        active_position_codes = obtener_posiciones_activas()
        
        resultados = list(
            EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)
            .values("nivel")
            .annotate(
                Activo=Count("estado_nomina", filter=Q(estado_nomina="Activo")),
                Vacante=Count("estado_nomina", filter=Q(estado_nomina="Vacante")),
                Suspendido=Count("estado_nomina", filter=Q(estado_nomina="Suspendido")),
                Permiso_Retribuido=Count(
                    "estado_nomina", filter=Q(estado_nomina="Permiso Retribuido")
                ),
                Permiso=Count("estado_nomina", filter=Q(estado_nomina="Permiso")),
            )
            .order_by("nivel")
        )
        cache.set(cache_key, resultados, 1200)
        return Response(resultados, status=status.HTTP_200_OK)


class PlantillaVacantesPorNivelResumenView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def obtener_resumen_dinamico():
        cache_key = "plantilla_vacantes_por_nivel_resumen"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        active_position_codes = obtener_posiciones_activas()
        
        base_qs = EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes).exclude(
            Q(estado_nomina__isnull=True) | Q(estado_nomina="Estado Nomina")
        )

        estados_unicos = (
            base_qs.values_list("estado_nomina", flat=True).distinct()
        )

        # total_niveles: Conteo de niveles distintos
        # total_registros: Conteo total de filas válidas
        agregaciones = {
            "total_niveles": Count("nivel", distinct=True),
            "total_registros": Count("*"),
        }

        # 3. Iteramos sobre los estados para crear el equivalente al SUM(CASE...)
        for estado in estados_unicos:
            # Usamos el nombre del estado con la primera letra en mayúscula y sin espacios
            # para ser consistentes con la otra vista y evitar colisiones con campos del modelo (que son minúsculas)
            llave = estado.replace(" ", "_")

            agregaciones[llave] = Sum(
                Case(
                    When(estado_nomina=estado, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            )

        # 4. Ejecutamos la consulta pasándole el diccionario desempaquetado (**agregaciones)
        resultado = base_qs.aggregate(**agregaciones)
        cache.set(cache_key, resultado, 1200)

        return resultado

    def get(self, request, *args, **kwargs):
        try:
            datos = self.obtener_resumen_dinamico()
            return Response(datos, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosCompletosEstatusNominaResumenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = "empleados_completos_estatus_resumen"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()
            total_registros = len(active_position_codes)

            # 2. Agrupar EmpleadosCompletosSig en posiciones activas por estado_nomina
            conteo_raw = (
                EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)
                .values("estado_nomina")
                .annotate(total=Count("pk"))
            )
            
            resumen = {
                "total_registros": total_registros,
                "Activo": 0,
                "Vacante": 0,
                "Suspendido": 0,
                "Licencia": 0,
                "Licencia_Medica": 0,
            }
            
            for item in conteo_raw:
                estado = item.get("estado_nomina")
                total = item.get("total") or 0
                
                # Normalizar estados según el mapeo solicitado
                if not estado or estado.strip() == "":
                    label = "Vacante"
                else:
                    estado_upper = estado.strip().upper()
                    if estado_upper == "A":
                        label = "Activo"
                    elif estado_upper == "S":
                        label = "Suspendido"
                    elif estado_upper == "L":
                        label = "Licencia"
                    elif estado_upper == "P":
                        label = "Licencia_Medica"
                    else:
                        label = "Vacante"
                
                resumen[label] = resumen.get(label, 0) + total
            
            cache.set(cache_key, resumen, 1200)
            return Response(resumen, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosCompletosActivosDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")

        if oficio or nivel:
            cache_key = f"empleados_completos_activos_detalle_{oficio}_{nivel}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data, status=status.HTTP_200_OK)

            try:
                # Obtener posiciones de Plantilla1800Plazas que cumplan los filtros
                posiciones_qs = Plantilla1800Plazas.objects.all()
                if oficio:
                    if oficio == "(vacío)":
                        posiciones_qs = posiciones_qs.filter(Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud=""))
                    else:
                        posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
                if nivel:
                    posiciones_qs = posiciones_qs.filter(nivel=nivel)

                posiciones_list = list(posiciones_qs.values_list("posición", flat=True))

                # Filtrar EmpleadosCompletosSig
                queryset = EmpleadosCompletosSig.objects.filter(posicion__in=posiciones_list)
                resultados = list(queryset.values())

                cache.set(cache_key, resultados, 300)
                return Response(resultados, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        cache_key = "empleados_completos_activos_detalle"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener todos los registros de EMPLEADOS_COMPLETOS_SIG en esas posiciones
            queryset = EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)
            
            # 3. Serializar directamente
            resultados = list(queryset.values())
            
            cache.set(cache_key, resultados, 1200)
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosPorNivelYEstatusView(APIView):
    """
    Retorna empleados filtrados por nivel y estado de nómina.
    Query params: nivel, estado_nomina
    Ejemplo: /api/empleados/?nivel=C1&estado_nomina=Activo
    """

    def get(self, request):
        nivel = request.query_params.get("nivel")
        estado_nomina = request.query_params.get("estado_nomina")

        if not nivel or not estado_nomina:
            return Response(
                {"error": "Los parámetros 'nivel' y 'estado_nomina' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Map full names back to letters for EmpleadosCompletosSig DB query
        estatus_map_reverse = {
            "Activo": "A",
            "Suspendido": "S",
            "Licencia": "L",
            "Licencia Médica": "P",
            "Vacante": "V"
        }
        db_estado_nomina = estatus_map_reverse.get(estado_nomina, estado_nomina)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener los registros de EMPLEADOS_COMPLETOS_SIG correspondientes al nivel y estatus
            base_qs = EmpleadosCompletosSig.objects.filter(
                posicion__in=active_position_codes
            )

            if nivel == "SIN NIVEL":
                base_qs = base_qs.filter(Q(nivel__isnull=True) | Q(nivel__exact=""))
            else:
                base_qs = base_qs.filter(nivel=nivel)

            if estado_nomina == "Vacante":
                # La UI agrupa bajo "Vacante" todo lo que no sea A, S, L, P
                queryset = base_qs.exclude(estado_nomina__in=['A', 'a', 'S', 's', 'L', 'l', 'P', 'p'])
            else:
                queryset = base_qs.filter(estado_nomina__iexact=db_estado_nomina)

            return Response(
                {
                    "total": queryset.count(),
                    "resultados": list(queryset.values()),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OcupacionPorOficiosResumenView(APIView):
    """
    Devuelve un resumen dinámico de ocupación por 'Of. De Solicitud' con desglose por Nivel.

    Usa Django ORM para construir dinámicamente el equivalente a la query SQL con ROLLUP.
    Las columnas se generan automáticamente según los valores únicos de Nivel encontrados.

    Retorna:
    {
        "filas": [
            {
                "Of. De Solicitud": "Oficina A",
                "A212": 5,
                "D312": 3,
                "(vacío)": 1,
                "Total Resultado": 11
            },
            ...
        ],
        "columnas": ["Of. De Solicitud", "A212", "D312", "(vacío)", "Total Resultado"],
        "total_general": 1857
    }
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def obtener_resumen_dinamico():
        """
        Construye dinámicamente el resumen usando Django ORM de forma optimizada en O(1) queries.
        Equivalente a la query SQL con GROUP BY ... WITH ROLLUP
        """

        # 1. Obtener los niveles únicos (DISTINCT)
        niveles_unicos = (
            Plantilla1800Plazas.objects.exclude(Q(nivel__isnull=True) | Q(nivel=""))
            .values_list("nivel", flat=True)
            .distinct()
            .order_by("nivel")
        )
        niveles = list(niveles_unicos)

        # 2. Hacer una consulta agrupada para obtener los conteos totales de oficina y nivel
        conteo_agrupado = (
            Plantilla1800Plazas.objects.values("of_de_solicitud", "nivel")
            .annotate(cantidad=Count("id"))
            .order_by("of_de_solicitud", "nivel")
        )

        # 3. Procesar en memoria en Python los totales
        data_dict = {}
        for item in conteo_agrupado:
            oficina = item["of_de_solicitud"] or "(vacío)"
            nivel = item["nivel"]
            if not nivel:
                nivel = "(vacío)"
            cantidad = item["cantidad"]

            if oficina not in data_dict:
                data_dict[oficina] = {}
            data_dict[oficina][nivel] = data_dict[oficina].get(nivel, 0) + cantidad

        # 4. Obtener los conteos de ocupados agrupados
        conteo_ocupado = (
            Plantilla1800Plazas.objects.exclude(
                Q(rfc__isnull=True) | Q(rfc="") |
                Q(curp__isnull=True) | Q(curp="") |
                Q(num_empleado__isnull=True) | Q(num_empleado="") |
                Q(nombres__isnull=True) | Q(nombres="")
            ).values("of_de_solicitud", "nivel")
            .annotate(cantidad=Count("id"))
            .order_by("of_de_solicitud", "nivel")
        )

        ocupadas_dict = {}
        for item in conteo_ocupado:
            oficina = item["of_de_solicitud"] or "(vacío)"
            nivel = item["nivel"]
            if not nivel:
                nivel = "(vacío)"
            cantidad = item["cantidad"]

            if oficina not in ocupadas_dict:
                ocupadas_dict[oficina] = {}
            ocupadas_dict[oficina][nivel] = ocupadas_dict[oficina].get(nivel, 0) + cantidad

        # 5. Construir las filas
        filas = []
        totales_generales = {nivel: 0 for nivel in niveles}
        totales_generales["(vacío)"] = 0
        
        totales_ocupados_generales = {nivel: 0 for nivel in niveles}
        totales_ocupados_generales["(vacío)"] = 0

        total_gral = 0
        total_ocupadas_gral = 0

        # Ordenar oficinas
        oficinas_ordenadas = sorted(list(data_dict.keys()), key=lambda x: (x == "(vacío)", x))

        for oficina in oficinas_ordenadas:
            conteos_nivel = data_dict[oficina]
            total_oficina = sum(conteos_nivel.values())

            ocupadas_oficina = ocupadas_dict.get(oficina, {})
            total_ocupadas_oficina = sum(ocupadas_oficina.values())

            fila = {"Of. De Solicitud": oficina}

            for nivel in niveles:
                count_nivel = conteos_nivel.get(nivel, 0)
                fila[nivel] = count_nivel
                totales_generales[nivel] += count_nivel
                
                count_ocupadas = ocupadas_oficina.get(nivel, 0)
                fila[f"ocupadas_{nivel}"] = count_ocupadas
                totales_ocupados_generales[nivel] += count_ocupadas

            # Nivel vacío en esta oficina
            count_vacio = conteos_nivel.get("(vacío)", 0)
            fila["(vacío)"] = count_vacio
            totales_generales["(vacío)"] += count_vacio
            
            count_ocupadas_vacio = ocupadas_oficina.get("(vacío)", 0)
            fila["ocupadas_(vacío)"] = count_ocupadas_vacio
            totales_ocupados_generales["(vacío)"] += count_ocupadas_vacio

            fila["Total Resultado"] = total_oficina
            fila["ocupadas_Total Resultado"] = total_ocupadas_oficina
            
            total_gral += total_oficina
            total_ocupadas_gral += total_ocupadas_oficina

            filas.append(fila)

        # 6. Agregar fila de totales (equivalente a ROLLUP)
        fila_total = {"Of. De Solicitud": "Total Resultado"}
        for nivel in niveles:
            fila_total[nivel] = totales_generales[nivel]
            fila_total[f"ocupadas_{nivel}"] = totales_ocupados_generales[nivel]
            
        fila_total["(vacío)"] = totales_generales["(vacío)"]
        fila_total["ocupadas_(vacío)"] = totales_ocupados_generales["(vacío)"]
        
        fila_total["Total Resultado"] = total_gral
        fila_total["ocupadas_Total Resultado"] = total_ocupadas_gral

        filas.append(fila_total)

        # 7. Definir columnas en el orden correcto
        columnas = ["Of. De Solicitud"] + niveles + ["(vacío)", "Total Resultado"]

        # 8. Conteo de posiciones ocupadas que inician con 2026
        ocupadas_2026 = Plantilla1800Plazas.objects.filter(
            posición__startswith='2026'
        ).exclude(rfc__isnull=True).exclude(rfc__exact='') \
         .exclude(curp__isnull=True).exclude(curp__exact='') \
         .exclude(num_empleado__isnull=True).exclude(num_empleado__exact='') \
         .exclude(nombres__isnull=True).exclude(nombres__exact='') \
         .count()

        # 9. Conteo de empleados ocupados en EmpleadosCompletosSig que inician con 2026
        ocupadas_sig = EmpleadosCompletosSig.objects.filter(val_estat='Ocupada', posicion__startswith='2026').count()

        return {
            "filas": filas,
            "columnas": columnas,
            "total_general": Plantilla1800Plazas.objects.count(),
            "ocupadas_2026": ocupadas_2026,
            "ocupadas_sig": ocupadas_sig,
        }

    def get(self, request, *args, **kwargs):
        """
        GET /api/plantilla/ocupacion_por_oficios_resumen/

        Retorna el resumen dinámico de ocupación por oficios con desglose por nivel,
        construido usando Django ORM.
        """
        try:
            datos = self.obtener_resumen_dinamico()
            return Response(datos, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {
                    "error": str(e),
                    "detail": "Error al generar el resumen de ocupación por oficios",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RegistrosPorOficio1800PlazasView(APIView):
    """
    Devuelve los registros detallados del modelo Plantilla1800Plazas filtrados por 'Of. De Solicitud' y opcionalmente por 'Nivel'.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        no_oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")
        resumen = request.query_params.get("resumen") == "true"

        if not no_oficio and not nivel:
            return Response(
                {
                    "error": "No se especificó ningun filtro. Se requiere al menos 'oficio' o 'nivel' como parámetro de consulta."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Plantilla1800Plazas.objects.all()

        # Filtro dinámico por oficio
        if no_oficio:
            if no_oficio == "(vacío)":
                queryset = queryset.filter(
                    Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud="")
                )
            else:
                queryset = queryset.filter(of_de_solicitud=no_oficio)

        # Filtro dinámico por nivel
        if nivel:
            queryset = queryset.filter(nivel=nivel)

        if resumen:
            # Agrupamos por nivel y oficio, y contamos
            resultados = list(
                queryset.values("nivel", "of_de_solicitud")
                .annotate(total=Count("*"))
                .order_by("of_de_solicitud", "nivel")
            )
            total_registros = sum(r["total"] for r in resultados)
            total_count = len(resultados)
        else:
            # Traemos todos los campos (registros completos)
            resultados = list(queryset.order_by("nivel").values())
            total_registros = len(resultados)
            total_count = total_registros

        if not resultados:
            return Response(
                {
                    "mensaje": "No se encontraron registros con los filtros proporcionados."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Respuesta consolidada
        data = {
            "total_registros": total_registros,
            "resultados": resultados,
            "tipo_vista": "resumen" if resumen else "detallado"
        }
        if not resumen:
            data["total"] = total_count
        else:
            data["total_grupos"] = total_count

        if no_oficio:
            data["oficio"] = no_oficio
        if nivel:
            data["nivel"] = nivel

        return Response(data, status=status.HTTP_200_OK)


class Plantilla1800PlazasListView(APIView):
    """
    Vista para listar y actualizar registros de la plantilla de 1800 plazas.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Plantilla1800Plazas.objects.all().order_by('id')
        # Simple pagination or limit if needed, for now all
        resultados = list(queryset.values())
        return Response(resultados, status=status.HTTP_200_OK)

    def patch(self, request):
        """
        Actualización parcial de registros. 
        Se espera un objeto con el ID y los campos a cambiar, o una lista de ellos.
        """
        data = request.data
        if not isinstance(data, list):
            data = [data]
        
        actualizados = 0
        errores = []

        for item in data:
            id_registro = item.get('id')
            if not id_registro:
                errores.append({"error": "ID no proporcionado", "item": item})
                continue
            
            try:
                registro = Plantilla1800Plazas.objects.get(id=id_registro)
                for field, value in item.items():
                    if field != 'id' and hasattr(registro, field):
                        setattr(registro, field, value)
                registro.save()
                actualizados += 1
            except Plantilla1800Plazas.DoesNotExist:
                errores.append({"error": f"Registro con ID {id_registro} no existe", "id": id_registro})
            except Exception as e:
                errores.append({"error": str(e), "id": id_registro})

        return Response({
            "mensaje": f"{actualizados} registros actualizados correctamente.",
            "errores": errores
        }, status=status.HTTP_200_OK if not errores else status.HTTP_207_MULTI_STATUS)


class EmpleadosEstatusPorNivelUaView(APIView):
    """
    Vista para resumir el estatus de la nómina por nivel y por unidad administrativa (UA)
    de los empleados correspondientes a las posiciones activas.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = "empleados_estatus_por_nivel_ua"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener todos los registros de EMPLEADOS_COMPLETOS_SIG en esas posiciones
            active_employees = EmpleadosCompletosSig.objects.filter(posicion__in=active_position_codes)

            # 3. Agrupación por Nivel y Estado de Nómina
            nivel_data = active_employees.values('nivel', 'estado_nomina').annotate(count=Count('id'))
            
            por_nivel = {}
            for item in nivel_data:
                nv = item['nivel'] or "SIN NIVEL"
                est = item['estado_nomina'] or "SIN ESTATUS"
                if nv not in por_nivel:
                    por_nivel[nv] = {}
                por_nivel[nv][est] = item['count']

            # 4. Agrupación por Unidad Administrativa, Nivel y Estado de Nómina
            ua_data = active_employees.values('unidad_administrativa', 'nivel', 'estado_nomina').annotate(count=Count('id'))
            
            por_ua = {}
            for item in ua_data:
                ua_name = item['unidad_administrativa'] or "SIN UA"
                nv = item['nivel'] or "SIN NIVEL"
                est = item['estado_nomina'] or "SIN ESTATUS"
                if ua_name not in por_ua:
                    por_ua[ua_name] = {}
                if nv not in por_ua[ua_name]:
                    por_ua[ua_name][nv] = {}
                por_ua[ua_name][nv][est] = item['count']

            res_data = {
                "por_nivel": por_nivel,
                "por_ua": por_ua
            }
            cache.set(cache_key, res_data, 1200)
            return Response(res_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmpleadosDistribucionGeograficaView(APIView):
    """
    Retorna la distribución geográfica agrupada por coordenadas para los empleados activos.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = "empleados_distribucion_geografica"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Obtener posiciones actualmente activas
            active_position_codes = obtener_posiciones_activas()

            # 2. Obtener todos los registros de EMPLEADOS_COMPLETOS_SIG en esas posiciones con coordenadas válidas
            active_employees = EmpleadosCompletosSig.objects.filter(
                posicion__in=active_position_codes
            ).exclude(
                latitud__isnull=True
            ).exclude(
                latitud=''
            ).exclude(
                longitud__isnull=True
            ).exclude(
                longitud=''
            )

            # 3. Traer los campos necesarios para agrupar
            queryset_values = active_employees.values(
                'latitud', 
                'longitud', 
                'descripcion_ubicacion', 
                'aduana', 
                'tipo',
                'unidad_administrativa'
            )

            groups = {}
            for emp in queryset_values:
                lat_raw = emp['latitud']
                lng_raw = emp['longitud']
                
                if not lat_raw or not lng_raw:
                    continue
                
                lat = lat_raw.strip()
                lng = lng_raw.strip()
                
                if not lat or not lng:
                    continue
                
                try:
                    float(lat)
                    float(lng)
                except ValueError:
                    continue
                
                key = (lat, lng)
                aduana_name = emp['aduana'] or ""
                is_aduana = aduana_name.strip().upper().startswith("ADUANA")
                tipo_val = emp['tipo'] or ""
                desc = emp['descripcion_ubicacion'] or ""
                ua = emp['unidad_administrativa'] or ""

                if key not in groups:
                    groups[key] = {
                        'latitud': lat,
                        'longitud': lng,
                        'descripcion_ubicacion': desc,
                        'aduana': aduana_name,
                        'is_aduana': is_aduana,
                        'tipo': tipo_val,
                        'count': 0,
                        'descripciones_set': set(),
                        'aduanas_set': set(),
                        'tipos_set': set(),
                        'uas_set': set()
                    }

                g = groups[key]
                g['count'] += 1
                if desc:
                    g['descripciones_set'].add(desc)
                if aduana_name:
                    g['aduanas_set'].add(aduana_name)
                if tipo_val:
                    g['tipos_set'].add(tipo_val)
                if ua:
                    g['uas_set'].add(ua)

                if is_aduana:
                    g['is_aduana'] = True
                    if not g['aduana'] or not g['aduana'].strip().upper().startswith("ADUANA"):
                        g['aduana'] = aduana_name
                    if tipo_val and not g['tipo']:
                        g['tipo'] = tipo_val

            resultados = []
            for key, g in groups.items():
                nombre_principal = g['aduana'] if g['is_aduana'] and g['aduana'] else g['descripcion_ubicacion']
                if not nombre_principal and g['descripciones_set']:
                    nombre_principal = list(g['descripciones_set'])[0]
                
                resultados.append({
                    'latitud': float(g['latitud']),
                    'longitud': float(g['longitud']),
                    'nombre': nombre_principal or "Ubicación sin nombre",
                    'is_aduana': g['is_aduana'],
                    'tipo': g['tipo'],
                    'count': g['count'],
                    'descripciones': list(g['descripciones_set']),
                    'aduanas': list(g['aduanas_set']),
                    'tipos': list(g['tipos_set']),
                    'uas': list(g['uas_set'])
                })

            cache.set(cache_key, resultados, 1200)
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MovPosDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")

        if oficio or nivel:
            cache_key = f"mov_pos_detalle_{oficio}_{nivel}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data, status=status.HTTP_200_OK)

            try:
                # Obtener posiciones de Plantilla1800Plazas que cumplan los filtros
                posiciones_qs = Plantilla1800Plazas.objects.all()
                if oficio:
                    if oficio == "(vacío)":
                        posiciones_qs = posiciones_qs.filter(Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud=""))
                    else:
                        posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
                if nivel:
                    posiciones_qs = posiciones_qs.filter(nivel=nivel)

                posiciones_list = list(posiciones_qs.values_list("posición", flat=True))

                # 1. Contar movimientos totales por posición
                counts = dict(MovPos.objects.filter(no_pos_actual__in=posiciones_list).values_list('no_pos_actual').annotate(c=Count('id')))

                # 2. Obtener el último registro por posición de MovPos
                with connection.cursor() as cursor:
                    cursor.execute(LATEST_MOVPOS_RAW_SQL)
                    sub_ids = [row[0] for row in cursor.fetchall() if row[0]]
                    
                    cursor.execute(OCUPADAS_RAW_SQL)
                    posiciones_ocupadas = set([row[0] for row in cursor.fetchall() if row[0]])

                # 3. Filtrar los últimos registros
                queryset = MovPos.objects.filter(id__in=sub_ids).filter(no_pos_actual__in=posiciones_list)
                resultados = list(queryset.values())

                # 4. Mapear en memoria
                for r in resultados:
                    pos = r.get('no_pos_actual')
                    r['total_movimientos'] = counts.get(pos, 1)
                    r['estatus_ocupacion'] = 'Ocupada' if pos in posiciones_ocupadas else 'Vacante'

                cache.set(cache_key, resultados, 300)
                return Response(resultados, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        cache_key = "mov_pos_detalle"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            # 1. Contar movimientos totales por posición (Consulta agrupada súper rápida)
            counts = dict(MovPos.objects.values_list('no_pos_actual').annotate(c=Count('id')))

            # 2. Obtener el último registro por posición de MovPos
            # Evaluamos la subquery en memoria de Python para evitar subconsultas correlacionadas lentas en SQLite
            with connection.cursor() as cursor:
                cursor.execute(LATEST_MOVPOS_RAW_SQL)
                sub_ids = [row[0] for row in cursor.fetchall() if row[0]]

                cursor.execute(OCUPADAS_RAW_SQL)
                posiciones_ocupadas = set([row[0] for row in cursor.fetchall() if row[0]])
            
            # 3. Filtrar los últimos registros
            queryset = MovPos.objects.filter(id__in=sub_ids)
            resultados = list(queryset.values())
            
            # 4. Mapear en memoria para evitar el problema N+1 o Subquery correlacionado en SQL
            for r in resultados:
                pos = r.get('no_pos_actual')
                r['total_movimientos'] = counts.get(pos, 1)
                r['estatus_ocupacion'] = 'Ocupada' if pos in posiciones_ocupadas else 'Vacante'
            
            cache.set(cache_key, resultados, 1200)
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MovPosHistoriaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        posicion = request.query_params.get("posicion")
        if not posicion:
            return Response(
                {"error": "Parámetro 'posicion' es requerido."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Obtener todos los registros para la posición, ordenados del más reciente al más antiguo
            queryset = MovPos.objects.filter(no_pos_actual=posicion).order_by('-id')
            
            resultados = list(queryset.values())
            
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from django.db import connection

class CadenaMandoView(APIView):
    """
    Vista para buscar la cadena de mando jerárquica (Bottom-Up) en EMPLEADOS_COMPLETOS_SIG.
    Busca por posición, nombre completo o número de empleado, y usa un CTE recursivo para subir la jerarquía.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({"error": "Se requiere el parámetro 'q' para buscar."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Buscar la posición base (la hoja/subordinado)
        base_employee = EmpleadosCompletosSig.objects.filter(
            Q(posicion=query) | 
            Q(nombres__icontains=query) | 
            Q(id_empleado=query)
        ).first()

        if not base_employee:
            return Response({"error": f"No se encontró un empleado con el criterio '{query}'."}, status=status.HTTP_404_NOT_FOUND)

        base_posicion = base_employee.posicion

        # 2. Ejecutar CTE recursivo
        sql = """
            WITH RECURSIVE CadenaHaciaArriba AS (
                SELECT 
                    `Posición` AS Posicion,
                    `Nombres` AS Empleado,
                    `Nombre Puesto Funcional` AS Puesto_Funcional,
                    `Nivel` AS Nivel,
                    `DependenciaDirecta` AS Jefe_Directo,
                    1 AS Nivel_Hacia_Arriba
                FROM EMPLEADOS_COMPLETOS_SIG
                WHERE `Posición` = %s

                UNION ALL

                SELECT 
                    jefe.`Posición`,
                    jefe.`Nombres`,
                    jefe.`Nombre Puesto Funcional`,
                    jefe.`Nivel`,
                    jefe.`DependenciaDirecta`,
                    empleado.Nivel_Hacia_Arriba + 1
                FROM EMPLEADOS_COMPLETOS_SIG jefe
                INNER JOIN CadenaHaciaArriba empleado ON jefe.`Posición` = empleado.Jefe_Directo
                WHERE empleado.Jefe_Directo IS NOT NULL 
                  AND empleado.Jefe_Directo != '' 
                  AND empleado.Jefe_Directo != '0'
                  AND jefe.`Posición` != empleado.Posicion
            )
            SELECT 
                Posicion, Empleado, Puesto_Funcional, Nivel, Jefe_Directo, Nivel_Hacia_Arriba 
            FROM CadenaHaciaArriba 
            ORDER BY Nivel_Hacia_Arriba ASC;
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, [base_posicion])
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return Response({
                    "empleado_base": {
                        "posicion": base_employee.posicion,
                        "nombres": base_employee.nombres,
                        "puesto_funcional": base_employee.nombre_puesto_funcional if hasattr(base_employee, 'nombre_puesto_funcional') else '',
                        "nivel": base_employee.nivel if hasattr(base_employee, 'nivel') else '',
                    },
                    "cadena": results
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from .models import ZafiroBitacora

class ZafiroBitacoraView(APIView):
    """
    Endpoint para obtener el historial de ejecuciones de ZAFIRO.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        logs = ZafiroBitacora.objects.all()[:limit]
        
        data = []
        for log in logs:
            data.append({
                "id": log.id,
                "fecha_ejecucion": log.fecha_ejecucion.isoformat(),
                "duracion_segundos": log.duracion_segundos,
                "registros_posiciones": log.registros_posiciones,
                "registros_completos": log.registros_completos,
                "registros_bajas": log.registros_bajas,
                "registros_historial": log.registros_historial,
                "status": log.status,
                "error_message": log.error_message,
                "es_historico": log.es_historico,
                "logs_en_vivo": log.logs_en_vivo,
            })
            
        return Response(data, status=status.HTTP_200_OK)

class UltimaActualizacionZafiroView(APIView):
    """
    Endpoint público para obtener la fecha y estatus de la última actualización exitosa de ZAFIRO.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        last_success = ZafiroBitacora.objects.filter(status="EXITO").order_by("-fecha_ejecucion").first()
        if not last_success:
            last_success = ZafiroBitacora.objects.filter(status="OK").order_by("-fecha_ejecucion").first()
        if not last_success:
            last_success = ZafiroBitacora.objects.all().first()
            
        if last_success:
            return Response({
                "fecha": last_success.fecha_ejecucion.isoformat(),
                "status": last_success.status
            }, status=status.HTTP_200_OK)
            
        return Response({"fecha": None, "status": None}, status=status.HTTP_200_OK)

from django.views import View

class ZafiroSSEView(View):
    """
    Endpoint de Server-Sent Events (SSE) para notificar actualizaciones en tiempo real a clientes.
    """

    def get(self, request):
        from django.http import StreamingHttpResponse
        import redis

        def event_stream():
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            pubsub = r.pubsub()
            pubsub.subscribe('zafiro_updates')

            # Enviamos evento de inicialización de conexión
            yield "data: init\n\n"

            try:
                while True:
                    # Esperar mensajes en el canal de redis con timeout de 20s
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=20.0)
                    if message:
                        date_str = message['data'].decode('utf-8')
                        yield f"data: {date_str}\n\n"
                    else:
                        # Mantener conexión viva enviando pings
                        yield ": ping\n\n"
            except GeneratorExit:
                try:
                    pubsub.unsubscribe('zafiro_updates')
                    pubsub.close()
                except Exception:
                    pass

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

from .models import BajasSig
from django.db.models import Count

class BajasSigListView(APIView):
    """
    Endpoint para obtener todos los registros de bajas sin paginación.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        oficio = request.query_params.get("oficio")
        nivel = request.query_params.get("nivel")

        if oficio or nivel:
            cache_key = f"bajas_sig_list_{oficio}_{nivel}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data, status=status.HTTP_200_OK)

            try:
                # Obtener posiciones de Plantilla1800Plazas que cumplan los filtros
                posiciones_qs = Plantilla1800Plazas.objects.all()
                if oficio:
                    if oficio == "(vacío)":
                        posiciones_qs = posiciones_qs.filter(Q(of_de_solicitud__isnull=True) | Q(of_de_solicitud=""))
                    else:
                        posiciones_qs = posiciones_qs.filter(of_de_solicitud=oficio)
                if nivel:
                    posiciones_qs = posiciones_qs.filter(nivel=nivel)

                posiciones_list = list(posiciones_qs.values_list("posición", flat=True))

                bajas = list(BajasSig.objects.filter(posicion__in=posiciones_list).values())
                cache.set(cache_key, bajas, 300)
                return Response(bajas, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        cache_key = "bajas_sig_list"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        bajas = list(BajasSig.objects.all().values())
        cache.set(cache_key, bajas, 1200)
        return Response(bajas, status=status.HTTP_200_OK)


class BajasMotivosPieView(APIView):
    """
    Devuelve el conteo de bajas agrupado por Motivo para la gráfica de pastel.
    Respuesta: [{"motivo": "...", "total": N}, ...] ordenado por total descendente.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "bajas_motivos_pie"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        data = (
            BajasSig.objects
            .exclude(motivo_descr__isnull=True)
            .exclude(motivo_descr__exact="")
            .values("motivo_descr")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        result = [{"motivo": row["motivo_descr"], "total": row["total"]} for row in data]
        cache.set(cache_key, result, 1200)
        return Response(result, status=status.HTTP_200_OK)


class BajasHistoricoView(APIView):
    """
    Devuelve la evolución histórica de bajas_sig obtenida de ZAFIRO_BITACORA.
    Agrupado por día (el registro más reciente de cada día donde registros_bajas > 0).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = "bajas_historico"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        from .models import ZafiroBitacora
        queryset = ZafiroBitacora.objects.filter(registros_bajas__gt=0).order_by('fecha_ejecucion')
        bajas_por_dia = {}
        for r in queryset:
            bajas_por_dia[str(r.fecha_ejecucion.date())] = r.registros_bajas
        
        resultado = [{"fecha": fecha, "registros_bajas": count} for fecha, count in sorted(bajas_por_dia.items())]
        cache.set(cache_key, resultado, 1200)
        return Response(resultado, status=status.HTTP_200_OK)


class ExportarEstatusExcelView(APIView):
    """
    Genera y exporta un archivo Excel (.xlsx) estructurado e interactivo.
    Si ya existe en caché para esa consulta exacta, lo retorna instantáneamente.
    Si no, lo genera de forma síncrona en el hilo de la petición y lo retorna.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.core.cache import cache
        from django.utils import timezone
        from plantilla.tasks import generar_excel_estatus_task

        uas_param = request.query_params.get("uas", "")
        levels_param = request.query_params.get("levels", "")
        group_by = request.query_params.get("group_by", "ua")

        # Consultar si ya existe el archivo Excel final generado en caché para esta consulta exacta
        cache_key_excel = f"excel_estatus_file_{uas_param}_{levels_param}_{group_by}"
        cached_excel_data = cache.get(cache_key_excel)
        if cached_excel_data is not None:
            filename = f"Reporte_Plantilla_Estatus_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
            response = HttpResponse(
                cached_excel_data,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        try:
            # Ejecutar la generación de forma síncrona
            generar_excel_estatus_task.__wrapped__(uas_param, levels_param, group_by)
        except Exception as e:
            return HttpResponse(f"Error generando el reporte de Excel: {str(e)}", status=500)

        # Recuperar el archivo generado desde la caché
        file_data = cache.get(cache_key_excel)
        if not file_data:
            return HttpResponse("Error: No se pudo recuperar el archivo generado de la caché.", status=500)

        filename = f"Reporte_Plantilla_Estatus_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
        response = HttpResponse(
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class OrganigramaSearchView(APIView):
    """
    Busca sobre la tabla cruda ORGANIGRAMA_ANAM por descripcion_larga o departamento.
    Si no se envía query, retorna todo el catálogo (útil para caché en memoria).
    Retorna la unidad_negocio para que el frontend sepa qué JSON cargar.
    """
    def get(self, request):
        query = request.GET.get("q", "").strip()
            
        with connection.cursor() as cursor:
            if not query:
                sql = """
                    SELECT departamento, descripcion_larga, unidad_negocio, nivel_direccion 
                    FROM ORGANIGRAMA_ANAM
                """
                cursor.execute(sql)
            else:
                sql = """
                    SELECT departamento, descripcion_larga, unidad_negocio, nivel_direccion 
                    FROM ORGANIGRAMA_ANAM 
                    WHERE descripcion_larga LIKE %s OR departamento LIKE %s
                    LIMIT 50
                """
                cursor.execute(sql, [f"%{query}%", f"%{query}%"])
            
            rows = cursor.fetchall()
            
        results = [
            {
                "departamento": r[0],
                "descripcion_larga": r[1],
                "unidad_negocio": r[2],
                "nivel_direccion": r[3]
            }
            for r in rows
        ]
        return Response(results)


class TorreCaballito3DView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.db import connection
        query = '''
            SELECT 
                e.`Descripción ubicación`,
                e.`Unidad Administrativa`,
                COUNT(*) as Total
            FROM EMPLEADOS_COMPLETOS_SIG e
            INNER JOIN (
                SELECT `Nº Pos Actual` FROM (
                    SELECT `Nº Pos Actual`, `Estado Psn`, ROW_NUMBER() OVER (
                        PARTITION BY `Nº Pos Actual` 
                        ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                    ) as rn
                    FROM MOV_POS
                ) ranked WHERE rn = 1 AND `Estado Psn` = 'A'
            ) activas ON e.`Posición` = activas.`Nº Pos Actual`
            WHERE e.`Descripción ubicación` IS NOT NULL 
              AND (
                  e.`Descripción ubicación` LIKE '%Caballito Reforma 10 P%' 
                  OR e.`Descripción ubicación` LIKE '%Torre Caballito Reforma 10 P%'
              )
            GROUP BY e.`Descripción ubicación`, e.`Unidad Administrativa`
            ORDER BY e.`Descripción ubicación`, Total DESC;
        '''
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            
        # Aggregate by floor
        floors_dict = {}
        for row in results:
            piso = row[0]
            ua = row[1] if row[1] else "No Asignada"
            count = row[2]
            
            if piso not in floors_dict:
                floors_dict[piso] = {
                    'piso': piso,
                    'count': 0,
                    'uas': []
                }
            
            floors_dict[piso]['count'] += count
            floors_dict[piso]['uas'].append({
                'nombre': ua,
                'count': count
            })
            
        return Response(list(floors_dict.values()))


class TorreCaballitoEmpleadosView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        piso = request.query_params.get('piso', None)
        ua = request.query_params.get('ua', None)
        
        if not piso:
            return Response({"error": "Falta el parametro piso"}, status=400)
            
        from django.db import connection
        if ua and ua.strip():
            query = '''
                SELECT 
                    e.`Posición`,
                    e.`Numempleado`,
                    e.`Nombres`,
                    e.`Unidad Administrativa`,
                    e.`Descripción ubicación`,
                    e.`Estado Nómina`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN (
                    SELECT `Nº Pos Actual` FROM (
                        SELECT `Nº Pos Actual`, `Estado Psn`, ROW_NUMBER() OVER (
                            PARTITION BY `Nº Pos Actual` 
                            ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                        ) as rn
                        FROM MOV_POS
                    ) ranked WHERE rn = 1 AND `Estado Psn` = 'A'
                ) activas ON e.`Posición` = activas.`Nº Pos Actual`
                WHERE e.`Descripción ubicación` = %s 
                  AND e.`Unidad Administrativa` = %s
                ORDER BY e.`Nombres`;
            '''
            params = [piso, ua]
        else:
            query = '''
                SELECT 
                    e.`Posición`,
                    e.`Numempleado`,
                    e.`Nombres`,
                    e.`Unidad Administrativa`,
                    e.`Descripción ubicación`,
                    e.`Estado Nómina`
                FROM EMPLEADOS_COMPLETOS_SIG e
                INNER JOIN (
                    SELECT `Nº Pos Actual` FROM (
                        SELECT `Nº Pos Actual`, `Estado Psn`, ROW_NUMBER() OVER (
                            PARTITION BY `Nº Pos Actual` 
                            ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                        ) as rn
                        FROM MOV_POS
                    ) ranked WHERE rn = 1 AND `Estado Psn` = 'A'
                ) activas ON e.`Posición` = activas.`Nº Pos Actual`
                WHERE e.`Descripción ubicación` = %s 
                ORDER BY e.`Nombres`;
            '''
            params = [piso]
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
        data = []
        for row in results:
            raw_estatus = row[5]
            if not raw_estatus or str(raw_estatus).strip() == '':
                estatus = "Vacante"
            else:
                val = str(raw_estatus).strip().upper()
                if val == "A": estatus = "Activo"
                elif val == "S": estatus = "Suspendido"
                elif val == "L": estatus = "Licencia"
                elif val == "P": estatus = "Licencia Médica"
                else: estatus = "Vacante"
                
            data.append({
                "posicion": row[0],
                "num_empleado": row[1],
                "nombre": row[2],
                "ua": row[3],
                "ubicacion": row[4],
                "estado_nomina": estatus
            })
            
        return Response(data)

class TorreCaballitoSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q or len(q) < 3:
            return Response({"results": []})
        
        from django.db import connection
        query = '''
            SELECT
                e.`Posición`,
                e.`Numempleado`,
                e.`Nombres`,
                e.`Unidad Administrativa`,
                e.`Descripción ubicación`
            FROM EMPLEADOS_COMPLETOS_SIG e
            INNER JOIN (
                SELECT `Nº Pos Actual` FROM (
                    SELECT `Nº Pos Actual`, `Estado Psn`, ROW_NUMBER() OVER (
                        PARTITION BY `Nº Pos Actual`
                        ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                    ) as rn
                    FROM MOV_POS
                ) ranked WHERE rn = 1 AND `Estado Psn` = 'A'
            ) activas ON e.`Posición` = activas.`Nº Pos Actual`
            WHERE e.`Descripción ubicación` IS NOT NULL
              AND (
                  e.`Descripción ubicación` LIKE '%%Caballito Reforma 10 P%%'
                  OR e.`Descripción ubicación` LIKE '%%Torre Caballito Reforma 10 P%%'
              )
              AND (e.`Nombres` LIKE %s OR e.`Numempleado` LIKE %s)
            LIMIT 20;
        '''
        
        like_q = f'%{q}%'
        with connection.cursor() as cursor:
            cursor.execute(query, [like_q, like_q])
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        # Parse piso for frontend convenience
        import re
        for r in results:
            match = re.search(r'10\s*P(?:iso)?\s*(\d+)', r['Descripción ubicación'] or '', re.IGNORECASE)
            if match:
                r['piso_num'] = match.group(1)
            else:
                r['piso_num'] = None
                
        return Response({"results": results})


from rest_framework.pagination import PageNumberPagination

class MovimientosPersonalPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 10000

class MovimientosPersonalListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = MovimientosPersonalPagination

    def get(self, request):
        from .models import CpTblMovCompleto290526
        from .serializers import CpTblMovCompleto290526Serializer
        
        queryset = CpTblMovCompleto290526.objects.all()
        
        # Check if requesting distinct values for a field
        distinct_field = request.query_params.get('distinct_field', '').strip()
        
        # Search query
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(posicion__icontains=search_query) |
                Q(num_empleado__icontains=search_query) |
                Q(nombre__icontains=search_query) |
                Q(ap_pat__icontains=search_query) |
                Q(ap_mat__icontains=search_query) |
                Q(accion_nombre__icontains=search_query) |
                Q(motivo_nombre__icontains=search_query) |
                Q(un_admin__icontains=search_query)
            )

        # Dynamic Column Filters
        valid_fields = [f.name for f in CpTblMovCompleto290526._meta.get_fields()]
        text_fields = [f.name for f in CpTblMovCompleto290526._meta.get_fields() if f.get_internal_type() in ['CharField', 'TextField']]
        from django.db.models.functions import Trim
        
        for param, val in request.query_params.items():
            if param == 'distinct_field':
                continue
            is_exclude = False
            actual_param = param
            if param.startswith('exclude__'):
                is_exclude = True
                actual_param = param[9:]
                
            base_field = actual_param.split('__')[0]
            
            # Skip applying filter on the column we are querying distinct values for
            if distinct_field and base_field == distinct_field:
                continue
                
            if base_field in valid_fields and val:
                is_text = base_field in text_fields
                target_field = f"trimmed_{base_field}" if is_text else base_field
                if is_text and target_field not in queryset.query.annotations:
                    queryset = queryset.annotate(**{target_field: Trim(base_field)})
                
                # Detect lookup suffix if any
                if '__' in actual_param:
                    suffix = actual_param.split('__', 1)[1]
                    actual_param_target = f"{target_field}__{suffix}"
                else:
                    suffix = None
                    actual_param_target = target_field
                
                val_list = [v.strip() for v in val.split(',') if v.strip()]
                if suffix == 'in' or (not suffix and len(val_list) > 1):
                    lookup = f"{target_field}__in"
                    if is_exclude:
                        queryset = queryset.exclude(**{lookup: val_list})
                    else:
                        queryset = queryset.filter(**{lookup: val_list})
                elif suffix:
                    # Specific suffix (e.g. __istartswith, __iexact, etc.)
                    if is_exclude:
                        queryset = queryset.exclude(**{actual_param_target: val_list[0] if len(val_list) == 1 else val_list})
                    else:
                        queryset = queryset.filter(**{actual_param_target: val_list[0] if len(val_list) == 1 else val_list})
                else:
                    if is_text:
                        lookup = f"{target_field}__icontains"
                        if is_exclude:
                            queryset = queryset.exclude(**{lookup: val_list[0]})
                        else:
                            queryset = queryset.filter(**{lookup: val_list[0]})
                    else:
                        lookup = target_field
                        if is_exclude:
                            queryset = queryset.exclude(**{lookup: val_list[0]})
                        else:
                            queryset = queryset.filter(**{lookup: val_list[0]})

        # If distinct_field requested, return distinct values directly
        if distinct_field in valid_fields:
            is_text = distinct_field in text_fields
            target_distinct_field = f"trimmed_{distinct_field}" if is_text else distinct_field
            if is_text and target_distinct_field not in queryset.query.annotations:
                queryset = queryset.annotate(**{target_distinct_field: Trim(distinct_field)})
            
            # Apply search filter on the distinct field if present
            distinct_search = request.query_params.get('distinct_search', '').strip()
            if distinct_search:
                if is_text:
                    queryset = queryset.filter(**{f"{target_distinct_field}__icontains": distinct_search})
                else:
                    queryset = queryset.filter(**{target_distinct_field: distinct_search})
            
            distinct_qs = (
                queryset.values(target_distinct_field)
                .annotate(count=Count('*'))
                .order_by(target_distinct_field)
            )
            
            results = []
            for item in distinct_qs:
                val = item[target_distinct_field]
                results.append({
                    'value': val if val is not None else '',
                    'count': item['count']
                })
            return Response(results)

        # Sorting
        sort_by_param = request.query_params.get('sort_by', '').strip()
        sort_order = request.query_params.get('sort_order', 'asc').strip().lower()
        if sort_by_param:
            sort_fields = [f.strip() for f in sort_by_param.split(',')]
            order_by_args = []
            for field in sort_fields:
                if field in valid_fields:
                    is_text = field in text_fields
                    target_sort_field = f"trimmed_{field}" if is_text else field
                    if is_text and target_sort_field not in queryset.query.annotations:
                        queryset = queryset.annotate(**{target_sort_field: Trim(field)})
                    if sort_order == 'desc':
                        order_by_args.append(f"-{target_sort_field}")
                    else:
                        order_by_args.append(target_sort_field)
            if order_by_args:
                queryset = queryset.order_by(*order_by_args)
            else:
                queryset = queryset.order_by('-fecha_efectiva', '-sec')
        else:
            # Default ordering
            queryset = queryset.order_by('-fecha_efectiva', '-sec')

        # Excel download or full list without pagination
        no_pagination = request.query_params.get('no_pagination', 'false').strip().lower() == 'true'
        if no_pagination:
            serializer = CpTblMovCompleto290526Serializer(queryset, many=True)
            return Response(serializer.data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = CpTblMovCompleto290526Serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CpTblMovCompleto290526Serializer(queryset, many=True)
        return Response(serializer.data)


class MovimientosPersonalStatsView(APIView):
    """
    Devuelve la estadística de movimientos de personal agrupado por accion_nombre y año.
    Respuesta: {
        "by_year": {
            "2026": [{"accion_nombre": "REINGRESO", "total": 10}, ...],
            ...
        },
        "all": [{"accion_nombre": "REINGRESO", "total": 150}, ...]
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accion_nombre = request.query_params.get('accion_nombre')

        from django.core.cache import cache
        import hashlib
        
        if accion_nombre:
            name_hash = hashlib.md5(accion_nombre.encode('utf-8')).hexdigest()
            cache_key = f"movimientos_personal_stats_{name_hash}"
        else:
            cache_key = "movimientos_personal_stats"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        from .models import CpTblMovCompleto290526
        from django.db.models.functions import ExtractYear
        from django.db.models import Count

        queryset = CpTblMovCompleto290526.objects
        if accion_nombre:
            queryset = queryset.filter(accion_nombre=accion_nombre)
            group_field = 'motivo_nombre'
        else:
            group_field = 'accion_nombre'

        # Fetch stats grouped by year and group_field
        stats_by_year = (
            queryset
            .exclude(**{f"{group_field}__isnull": True})
            .exclude(**{f"{group_field}__exact": ""})
            .annotate(year=ExtractYear('fecha_efectiva'))
            .values('year', group_field)
            .annotate(total=Count('*'))
            .order_by('-year', '-total')
        )

        # Fetch stats for ALL years combined
        stats_all = (
            queryset
            .exclude(**{f"{group_field}__isnull": True})
            .exclude(**{f"{group_field}__exact": ""})
            .values(group_field)
            .annotate(total=Count('*'))
            .order_by('-total')
        )

        by_year_dict = {}
        for row in stats_by_year:
            year_val = row['year']
            year_str = str(year_val) if year_val is not None else "Sin Año"
            if year_str not in by_year_dict:
                by_year_dict[year_str] = []
            by_year_dict[year_str].append({
                group_field: row[group_field],
                "total": row['total']
            })

        all_list = [{
            group_field: row[group_field],
            "total": row['total']
        } for row in stats_all]

        result = {
            "by_year": by_year_dict,
            "all": all_list
        }

        cache.set(cache_key, result, 1200)
        return Response(result, status=status.HTTP_200_OK)

