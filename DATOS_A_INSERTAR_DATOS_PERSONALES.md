# Datos exactos a insertar en DATOS_PERSONALES (conmutador / extension)

Generado desde `Directorio ANAM.xlsx` cruzado contra `EMPLEADOS_COMPLETOS_SIG` por numero de empleado.
Mecanismo de escritura: `plantilla.celda_override.registrar_y_aplicar_override_datos_personales(no_empleado, columna, valor_nuevo, usuario)`
(tabla=DATOS_PERSONALES, clave_negocio={"no_empleado": ...}) — NO se escribe directo en DATOS_PERSONALES
porque esa tabla se trunca y recarga completa cada `importar_zafiro` (swap blue-green); el override
sobrevive porque `aplicar_overrides_datos_personales()` lo reaplica despues de cada import.

## Resumen

- Total empleados con override de **conmutador**: **2274** (valor fijo `55-8889-0400` para todos)
- De esos, con override de **extension**: **1799**
  - Extension simple (string): 1792
  - Extension multiple (JSON, personas con 2+ areas): 7
- Sin extension en el excel (solo se inserta conmutador): 475

## Casos especiales: extension como JSON (multi-area)

Estas 7 personas cubren mas de un modulo/area con extension propia cada una — se detecto por
aparecer repetidas en la misma hoja del excel con extensiones distintas. El campo `extension`
se reformulo a `JSONField` en Django (migracion `0041_datos_personales_conmutador_extension_json`)
para soportar esto. Contrato: `[{"extension": "...", "area": "..."}, ...]`.

### Juan José Ramírez Salomé (no_empleado `00020222456`, Aduana de Ciudad Camargo con sede en Tamaulipas)

```json
[
  {
    "extension": "0237",
    "area": "Titular"
  },
  {
    "extension": "5308",
    "area": "Encargado de la Aduana (Subdirector Informática y Contabilidad)"
  }
]
```

### Heber López Hernández (no_empleado `00202324281`, Aduana de Chihuahua con sede en Chihuahua)

```json
[
  {
    "extension": "3414",
    "area": "Sección Carga"
  },
  {
    "extension": "3421",
    "area": "Oficina de Binomios"
  }
]
```

### Luis Ernesto Sena Hernandez (no_empleado `00202321137`, Aduana de Nuevo Laredo con sede en Tamaulipas)

```json
[
  {
    "extension": "3502",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3503",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3509",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3520",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3521",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3522",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3524",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3525",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3530",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3531",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3540",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3542",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3544",
    "area": "Subdirección de Informática y Contabilidad"
  },
  {
    "extension": "3546",
    "area": "Subdirección de Informática y Contabilidad"
  }
]
```

### Uriel Eduardo Uribe Calderon (no_empleado `00020222479`, Aduana de Nuevo Laredo con sede en Tamaulipas)

```json
[
  {
    "extension": "3507",
    "area": "Subdirección de Supervisión Aduanera"
  },
  {
    "extension": "3534",
    "area": "I Puente – Boletas"
  },
  {
    "extension": "3535",
    "area": "II Turismo"
  },
  {
    "extension": "3536",
    "area": "II Puente – Boletas"
  }
]
```

### Karla Beatriz Rangel Hernandez (no_empleado `00202203943`, Aduana de Nuevo Laredo con sede en Tamaulipas)

```json
[
  {
    "extension": "3508",
    "area": "Subdirección de Supervisión Aduanera"
  },
  {
    "extension": "3533",
    "area": "Módulo CIITEV"
  }
]
```

### Christian Daniel Ortiz Rodriguez (no_empleado `00020241015`, Aduana de San Luis Río Colorado con sede en Sonora)

```json
[
  {
    "extension": "4020",
    "area": "Verificadores"
  },
  {
    "extension": "4018",
    "area": "Almacen Fiscal"
  }
]
```

### Edgar Aguilar Serrano (no_empleado `00202203848`, Aduana de Toluca con sede en Estado de México)

```json
[
  {
    "extension": "2001",
    "area": "Operación Aduanera"
  },
  {
    "extension": "2003",
    "area": "Puerta México San Cayetano"
  }
]
```

## Casos excluidos (colision de fuzzy-match, NO se inserta nada)

Estos 10 numero_empleado tenian 2 nombres distintos del excel apuntando al mismo registro de BD
(bug del matching por similitud de apellidos). Se verifico a mano contra `EMPLEADOS_COMPLETOS_SIG.Nombres`
cual nombre es el correcto; el otro se descarta por completo (no se le atribuye su extension a este empleado).

| no_empleado | Nombre correcto (se usa) | Nombre descartado (excel, NO se usa) |
|---|---|---|
| 02022034500 | Anibal Alejandro Villegas Ramirez | Ruth Villegas Ramirez |
| 00020241039 | Efren Garcia Perez | Cielo Berenith Pérez García |
| 00020261046 | Fernando Garcia Hernandez | Liliana Hernandez Garcia |
| 00020251560 | Cristina Hernandez Morales | Karina Morales Hernández |
| 00202612376 | Karina Yocciry Rodriguez Jimenez | Karina Rios Rodriguez |
| 00202203476 | Alfredo Javier Lopez De La Paz | Alfredo Juan Lopez |
| 02022033589 | Adrian Hernández Hernández | Adrián Salustino García Hernández |
| 02022031544 | Grecia Robles Ibarra | Andrea Robles Ibarra |
| 02022034203 | Misael González Martínez | Karen Ivette Martinez Gonzalez |
| 00020221715 | Angelica Jimenez Gutierrez | Noel Jiménez Gutiérrez |

## Tabla completa (todos los empleados)

| no_empleado | Nombre | Aduana | Conmutador | Extension |
|---|---|---|---|---|
| 00020220323 | Oscar López Salmerón | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 0229 |
| 02022036063 | Ana María Moreno García | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6300 |
| 02022031808 | Adelina Román Trujillo | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6301 |
| 00202203140 | Sonia Rodríguez Cortez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6302 |
| 02022032343 | Ruth Faustino Tejada | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324541 | Sergio Carballo Juarez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6303 |
| 00202515146 | Efraín Yepez Sanchez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6310 |
| 02022034944 | Brenda Agapito García | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6305 |
| 00202324524 | Paola Monserrat Salazar Catalán | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035705 | Edgar Gonzalo Almaraz Gómez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203255 | Pedro León Cano | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6306 |
| 00202203514 | María Elena Flores Gutiérrez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6307 |
| 02022031880 | Gibran Espinoza Castillo | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031968 | Manuel Abraham Portillo Borunda | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324433 | Jafet Joab Campos Canizales | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035358 | Liliana López Lozano | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033505 | Mirna López Montes | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6309 |
| 02022035630 | Maricruz Guillén Nogueda | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036064 | Patricia Pindter Galeana | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251034 | Teresa de Jesus Valladares Escobar | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6308 |
| 00202321105 | Francisco Javier Cabello Rodríguez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | 6304 |
| 02022031187 | Adalberto Quiñonez Lorenzana | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032675 | Julio César Mayo López | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032654 | Lilia León Morales | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034237 | Luis Cantú Moctezuma | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034325 | Martha Campos Ríos | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033319 | Ulises Renteria Ramos | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034215 | Gabriela Guevara Silvestre | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324387 | Cristofer Flores Reyes | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035122 | Luis Manuel Cabrera Carballo | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515145 | Eneyda Ozuna Cruz | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612289 | Jorge Adrián Reynoso Chávez | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612287 | América Jacqueline Mejía | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612693 | Carlos Jesús Lagunas Balbuena | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232313 | Lidia Luna Zepeda | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032935 | Amado Sánchez Atrisco | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202418111 | Miguel Ángel Villanueva Moráles | Aduana de Acapulco con sede en Guerrero | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002025217 | Bernardo Rafael Sánchez Hernández | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 0232 |
| 02022034583 | Maybeth Karina Cuevas Ibarra | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5800 |
| 00202203309 | Myriam Villaseñor Padilla | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5801 |
| 00020242444 | Yenitzi Guadalupe Dorame García | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5802 |
| 02022035186 | Alberto Flores Melendrez | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5803 |
| 00020221728 | Irazema Margarita Villarreal Flores | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5804 |
| 02022035389 | Liliana Martinez Vargas | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5811 |
| 00202208121 | 2/o. Gdia. Nal. Juan Hernández Carrillo | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5809 |
| 00020240537 | 2/o. Ret. Marcos Cervantes Guerra | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5810 |
| 00202203456 | Manuel Alejandro Verazaluce Sánchez | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5806 |
| 02022033466 | Irving Arland Parra Aguiar | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5807 |
| 02022032177 | Enrique Aboytia Esquer | Aduana de Agua Prieta con sede en Sonora | 55-8889-0400 | 5808 |
| 00020250215 | Leoncio Reyes González | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 0233 |
| 00020250827 | Carlos Eduardo Ontiveros Ontiveros | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2529 |
| 00202203517 | Alvaro Eduardo Hernández Díaz | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2515 |
| 00020221921 | Luis Enrique Hernández Ramírez | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2530 |
| 00202203410 | Veronica Patricia Jasso Gámez | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2502 |
| 00202203921 | Irma Lizzeth Enriquez Saab | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2510 |
| 00020222483 | Pedro Javier Ocampo García | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2509 |
| 02022031161 | Julia Sánchez Muñiz | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2513 |
| 00020242422 | Luis Alberto González Ruiz | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 3029 |
| 02022031120 | Francisco Fernando Rodríguez Hernández | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2503 |
| 02022031789 | Ricardo Magallanes Delgado | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2506 |
| 02022032740 | Kenia Itzel Rosales Díaz | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2507 |
| 00202208226 | Sergio Cárdenas Pérez | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2511 |
| 02022033828 | Aure Estela Josefina Soto Salas | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2512 |
| 00020222427 | Ivonne Colin Quintero | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2514 |
| 00020222137 | Enrique Gochicoa Conde | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2516 |
| 02022035777 | José Manuel Torres Dávila | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2520 |
| 00202219179 | David Alejandro Ureste Enríquez | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2524 |
| 00202203983 | Oscar Melecio Tamaturgo | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2525 |
| 00020241810 | Marco Antonio Ángel Castro | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2526 |
| 00020241828 | María Yamilet Ayon Muñoz | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2527 |
| 00020241813 | Rodolfo Alcudia Alvarez | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2522 |
| 02022035346 | Reynolds Salazar Cortés | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2523 |
| 02022035928 | Ma. del Refugio Jasso Villalpando | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2504 |
| 00020240470 | Esau Yatniel Saucedo Sosa | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2508 |
| 02022035359 | Maria del Carmen Regalado Padilla | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2517 |
| 02022035952 | Ricardo Castillo Macias | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2518 |
| 02022035461 | Carlos Martínez León | Aduana de Aguascalientes con sede en Aguascalientes | 55-8889-0400 | 2519 |
| 02022031477 | Yuli Jeanethe Solís Sánchez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5100 |
| 00202203311 | Miguel Ángel Alfaro Rosas | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5101 |
| 00202203932 | Nura Elizabeth Fernández Mendoza | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5115 |
| 02022031903 | Christian Javier Monrreal Moya | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5113 |
| 02022034862 | Manuel del Jesús Góngora Damas | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5114 |
| 02022032709 | Sabino Trejo Sánchez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5102 |
| 00020230511 | Ana Zuly García Martínez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5116 |
| 02022032753 | Jessica Berenice Sánchez Rodriguez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5117 |
| 02022031924 | Erick Orlando Maldonado Rocha | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5106 |
| 00020251345 | Benito Hernández Martinez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5125 |
| 02022032467 | Marisol Turiján Elizalde | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5118 |
| 00202324395 | Eduardo Alejandro Torres Rivas | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5105 |
| 00202203228 | Juan Uzziel Reyes García | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5109 |
| 02022031762 | Alejandra Leticia Muñoz Alarcon | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5107 |
| 02022032217 | Efraín Bretón Bermúdez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5119 |
| 02022032072 | Miguel Ángel Herrera Alvarado | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5103 |
| 00202203774 | Carlos Alberto Hernández Guerrero | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5121 |
| 02022032293 | Angelica Mártir del Angel | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5120 |
| 00020251893 | Emilio Garin Muñoz | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5104 |
| 02022031353 | Josué Emanuel Orozco Solorio | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5110 |
| 00202203335 | Jorge Alberto Hernández Silva | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5122 |
| 00202203488 | Abraham David Gómez Trejo | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5111 |
| 02022033823 | Federico González Pérez | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5124 |
| 02022033933 | Jorge Luis Tello Ponce | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5108 |
| 02022033095 | Blanca Abigail Ruíz Lara | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5126 |
| 02022032664 | Eric Josué del Angel Guerrero | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5127 |
| 00020241749 | Eduardo Bolado Valencia | Aduana de Altamira con sede en Tamaulipas | 55-8889-0400 | 5112 |
| 00002023184 | Luis Antonio Balcazar Bustos | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 0235 |
| 00020220874 | Carlos Antonio Basilio | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5000 |
| 00020220638 | Marco Antonio Martinez Uribe | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5001 |
| 02022033985 | Diana Laura Gutierrez Sotelo | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5002 |
| 00020222432 | Julia Nayeli Bernal Gutierrez | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5003 |
| 02022034391 | Selene Garrido Can | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5004 |
| 00020221993 | Guillermo de Jesús Xolo Fiscal | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5005 |
| 02022031579 | Karla Victoria Martin Hernández | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5006 |
| 00002024223 | Abraham Pérez Acevedo | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5025 |
| 02022031737 | Maran Moreno Vilchiz | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5008 |
| 00202203693 | Juan José Silva Castillo | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5009 |
| 02022032186 | Nady Urbizu Manzanero | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5010 |
| 00202322241 | Carlos Brian Alvarado SandovaL | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5050 |
| 02022032127 | Fabiola Irene Quezada Suarez | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5020 |
| 02022033349 | Gustavo Hernández Flores | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5021 |
| 00020222487 | Leonardo Daniel Flores Noriega | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5011 |
| 00202203249 | Jorge Alberto Martinez Medina | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5012 |
| 02022032392 | Silvia Susana Álvarez Acosta | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5015 |
| 00202203366 | Yazmin Reyes Manngha | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5017 |
| 02022033291 | Yibriam Humberto Lucero Herrera | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5018 |
| 00202203632 | Daniel Paris Herrera Santillán | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5014 |
| 00020241618 | Jonathan Torres Álvarez | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5019 |
| 00002025139 | Lucio Peraza Itza | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5051 |
| 00202203155 | Mallely Jasmin Espinosa Martinez | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5034 |
| 02022032950 | Yessenia Yanet Rivera Piñon | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5052 |
| 00020220612 | Roberto Gomez La Verne | Aduana de Cancún con sede en Quintana Roo | 55-8889-0400 | 5033 |
| 00020220389 | Jubentino Hernández Rea | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034838 | Mariana Alexandra Casillas Luján | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3400 |
| 02022035513 | Mayra Teresa Alvarado Gamboa | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035160 | Anabel Chávez Alarcón | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020222428 | Daniel Carmona Ramírez | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3403 |
| 02022035331 | Nadia Lizeth Reza Enríquez | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3404 |
| 00202203843 | José Raúl Rodríguez Mendoza | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3405 |
| 00202224100 | Oscar Armando Esquincar Sánchez | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3406 |
| 00202215118 | Sonia Candelario Macario | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3407 |
| 02022033455 | Andrik Luna Quintana | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3409 |
| 02022034680 | Kenly Azucena Avitia Hernández | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3411 |
| 00202324281 | Heber López Hernández | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | [{"extension": "3414", "area": "Sección Carga"}, {"extension": "3421", "area": "Oficina de Binomios"}] |
| 00020232435 | Jorge Eduardo Priego Correa | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3415 |
| 00020232021 | Arturo Zeth Miranda Macías | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3416 |
| 00020241726 | Leobardo de Jesús de Jesús | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3412 |
| 00202615300 | Rafael Rodríguez Ramos | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3417 |
| 00020221940 | Caralampio López López | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3418 |
| 02022035275 | Abraham Zamora Ita | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3419 |
| 00202219262 | Edgar Santiago Romero | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3420 |
| 00020241858 | Carla Patricia Muñoz Fiscal | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3423 |
| 02022033937 | Raquelia Cuevas Rendón | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3424 |
| 02022035165 | Luz de Saharon Sánchez Córdova | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3425 |
| 02022035624 | Juan Salvador Mani Enríquez | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3426 |
| 02022036160 | Linda Bianey Durán Chávez | Aduana de Chihuahua con sede en Chihuahua | 55-8889-0400 | 3408 |
| 00020251215 | Rafael Alamillo Gurrola | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 0236 |
| 02022035501 | Nancy Vicenta Oyervides González | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4701 |
| 00020222457 | Luis Ángel Ramírez Paez | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4706 |
| 00020221939 | 1o. G. N. César Antonio Rivas Rivas | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4711 |
| 02022032329 | Miguel Ángel Bautista Franco | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4707 |
| 00202203523 | Omar Vargas Orozco | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4702 |
| 00202212145 | Samantha Rosas Grande | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4703 |
| 00202322258 | Ana Laura Aguilar Cruz | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4703 |
| 00202203531 | Julio César Hernández Álvarez | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4704 |
| 02022034871 | Ana Karen Herrera Rodríguez | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4705 |
| 02022036019 | Consuelo Hernández Salas | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4709 |
| 02022035969 | Juana Patricia Rivera Castro | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4713 |
| 02022031699 | Lucero Sánchez Correa | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4712 |
| 00020241621 | María de los Angeles Martínez Garza | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4700 |
| 00020250724 | Christian García Rodríguez | Aduana de Ciudad Acuña con sede en Coahuila de Zaragoza | 55-8889-0400 | 4700 |
| 00020222456 | Juan José Ramírez Salomé | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | [{"extension": "0237", "area": "Titular"}, {"extension": "5308", "area": "Encargado de la Aduana (Subdirector Informática y Contabilidad)"}] |
| 02022031133 | Karen Soleidy Ferrara Cardona | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5301 |
| 00020220867 | Cristian Terrazas Miranda | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5303 |
| 00202203146 | Gabriel Caballero Exzacarias | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5304 |
| 00020240538 | José Francisco Rosales Mares | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5305 |
| 00020222461 | Genaro Pérez Olmedo | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5306 |
| 00020222413 | Guadalupe Núñez Millan | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5306 |
| 02022035587 | Victor Eloy Moreno Martínez | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5307 |
| 02022034116 | Ezequiel Antonio Cruz | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5309 |
| 02022033069 | Angélica Yaneth Ornelas Garza | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5310 |
| 00020221523 | Alberto Visuet Sandoval | Aduana de Ciudad Camargo con sede en Tamaulipas | 55-8889-0400 | 5311 |
| 00020250214 | Alejandro Barrera Leal | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 0239 |
| 00020222466 | Moises Plutarco Baños Gallegos | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5759 |
| 02022034473 | Londy Liliana Barrios Villagomez | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5700 |
| 00020222459 | 2/o F. A. Metereológo Francisco Hernández Ruiz | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5719 |
| 02022034124 | Cynthia Yanery Alzati Hernandez | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5717 |
| 00202203294 | María de Lourdes Arévalo Damián | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5711 |
| 00202203997 | Salvador Rodas Garcia | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5701 |
| 00202203403 | Sergio Edgardo Olivares Ramos | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5702 |
| 00202203763 | Arturo Fernando Solano Labastida | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5755 |
| 00020250732 | Gustavo Velazquez Garcia | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5758 |
| 00202515113 | Adriana Mendez de la Rosa | Aduana de Ciudad Hidalgo con sede en Chiapas | 55-8889-0400 | 5760 |
| 00202615306 | Jose Luis Nolasco Lima | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 0240 |
| 00020251914 | Abdiel Moises Valadez Lugo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202514107 | Abel Otero Beltran | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202221127 | Adelino Job Calderon Galvan | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031487 | Adrian Torres Valtierra | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035783 | Adriana Margarita Sierra Cruz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020231347 | Agustin Arcos Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035672 | Aidee Maria Luisa Garcia Meraz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208318 | Alan Miguel Rangel Sánchez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033464 | Alan Ruiz Martinez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261042 | Alberto Gregorio Ramirez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 02022035734 | Alberto Ramirez Vasquez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232427 | Alejandro Cruz Contreras | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208282 | Alejandro Guevara Pedroza | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 02022035417 | Alejandro Inocencio Renteria Gutierrez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032895 | Alex Omar Cauich Silva | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033051 | Alfredo Armenta Varela | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261039 | Alfredo Jimenez Manzano | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034139 | Alma Delia Rodriguez Bobadilla | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034420 | Alvaro De Jesus Hernandez Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202203954 | Ana Luisa Cardenas Guerrero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208102 | Angel Ibrahin Villegas Barradas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035744 | Angelica Diaz Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034115 | Angelica Espinoza Castillo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034500 | Anibal Alejandro Villegas Ramirez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221284 | Antonio Ortiz Villatoro | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022033262 | Antonio Osuna Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261054 | Araceli Danin Dominguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202322252 | Armando Diaz Nava | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035851 | Aurora Garcia Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00202322250 | Azucena Del Carmen Altunar Flores | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00020252121 | Berenice Peña Nava | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022031330 | Bily Eduardo Lopez Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202219163 | Binisa Dessire Zarate Pineda | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035092 | Bricia Lorena Torres Medina | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034646 | Brisa Naquiahuit Corona Arochi | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035816 | Carlos Alberto Romero Muñoz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032775 | Carlos Alejandro Carmona Saldaña | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261038 | Carlos Alexis Santes Cruz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261053 | Carlos Briones Guadalupe | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221516 | Carlos Luna Cruz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022032075 | Carlos Luna Lazcano | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035634 | Carlos Rafael Guilbert Arellano | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261041 | Carlos Ricardo Romero Romero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 02022034815 | Carmela Jose Cortez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035423 | Carolina Jimenez Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202324276 | Cecilia Miranda Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022035661 | Cecilia Quiroz Cordova | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022032826 | Claudia Cabrera Arredondo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020251466 | Claudia Michelle Gonzalez Cajero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033668 | Claudia Yazmin Colunga Carreon | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020220854 | Cristian Andrade Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 00202324214 | Cristian Ayala Olvera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033401 | Cynthia Lizette Soto Alvarado | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036121 | Daniel Alejandro Luna Moyers | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261482 | Daniel Gutierrez Gutierrez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020221714 | Daniel Sanchez Monrreal | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3243 |
| 02022031265 | Daniela Guadalupe Emilian Medina | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035956 | Daniela Magdaleno Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3214 |
| 00202208185 | David Angel Espinoza Vega | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020252124 | Diana Berenice Robles Cruz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022033600 | Diana Cardenas Vega | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035075 | Diana Ivette Rico Grajeda | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036094 | Eduardo Antonio Sansores Morga | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020261068 | Eduardo Jaramillo Cortes | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202523123 | Eduardo Oscar Hidalgo Corral | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 00020221983 | Eduardo Tello Moxo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020241039 | Efren Garcia Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034303 | Einar Sebastian Roblero Roblero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203463 | Elizabeth Calzada Nieves | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261048 | Elizabeth Ramirez Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221733 | Elsie Margarita Castillo Mendoza | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022031618 | Elvia Lizbeth Vazquez Escamilla | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020231358 | Ember Eduardo Escudero Dzul | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 329 |
| 02022032488 | Enrique Totosaus Gamiño | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202324317 | Erick Fabian Gomez Gomez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261047 | Erick Hernandez Altamirano | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022036190 | Ernesto De Jesus Nares Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020240660 | Ernesto Ramirez Ceniceros | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022036013 | Ernesto Sanchez Monreal | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032007 | Eunice Ramirez Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208189 | Fabian Salazar Vasquez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202221246 | Fatima Anais Solis Sandoval | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261046 | Fernando Garcia Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020240661 | Fernando Olivas Aguirre | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 00020261065 | Filiberto Gonzalez Chavez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261067 | Fredy Del Valle Salas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261061 | Gabriel Diaz Martinez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202224240 | Gabriel Medina Diaz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032352 | Gabriela Raquel Verduzco Espinosa | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202322190 | Georgina Rodriguez Ramos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034276 | Georgina Tzunaly Ramirez Quezada | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035598 | Gerardo Arturo Jimenez Flores | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022033764 | Gerardo Castillo Olmos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 00020261045 | Gerardo Garfias Valdivia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261031 | Gerardo Lopez Jandete | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202322188 | Gerardo Ramos Ramirez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202322181 | Gustavo Adolfo Juarez Montoya | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208213 | Gustavo Garrido Cabrera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035931 | Haydee Molina Ochoa | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3250 |
| 02022032393 | Hector Manuel Marrufo Amaya | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202422100 | Hector Margarito Martinez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202321191 | Hugo Netzahualcoyotl Islas Sanchez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034438 | Iris Guadalupe Camacho Lizarraga | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035765 | Isidro Cortes Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 02022032931 | Ivan David Gonzalez Toxqui | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202224182 | Ivan Guzman Bautista | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261051 | Jairo Hernandez Ramos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261059 | Javier Peña Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261036 | Javier Tapia Tapia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022032112 | Jefferson Bringas Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020231332 | Jennifer Bautista Jimenez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022031336 | Jessica Lizbeth Pelayo Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 02022034184 | Jessica Maribel Molinar Higuera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261066 | Jesus Alejandro Vazquez Ruiz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020232459 | Jesus Antonio Camacho Cervantes | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036189 | Jesus Arturo Chavez Carreño | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034717 | Jesus Salas Naserau | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251550 | Jimena Padilla Bautista | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 00020261060 | Johana Isela Guerrero Salas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022032807 | Jonathan Emmanuel Rico Granados | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202212250 | Jonathan Zabdiel Montes Aymerich | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020251544 | Jorge Alonso Rico Romero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221713 | Jorge Armando Romero Olivas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020240662 | Jorge Eduardo Garcia Villa | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221724 | Jorge Gomez Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3243 |
| 00202212238 | Jorge Luis Garcia Santiago | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261029 | Jorge Ochoa Olivas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022033239 | Jorge Ovando Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232479 | José Armando Lopez Herrera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035202 | Jose David Gaspar Alva | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232486 | Jose Edwar Lopez Giron | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261034 | Jose Hernandez Bautista | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261032 | Jose Luis Mendoza Lopez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022036166 | Jose Osael Romero Islas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031127 | Josue Armando Nuñez Camarillo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3250 |
| 00020251038 | Josue Hiram Solano Sarmiento | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020231396 | Josue Luis Sanchez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261063 | Juan Carlos Benavides Becerra | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022036107 | Juan Carlos Gomez Aguirre | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032486 | Juan Carlos Juarez Gasca | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252131 | Juan Carlos Olvera Guerrero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202208396 | Juan Carlos Pelaez Barrera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202212257 | Juan Carlos Perez Cabrera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202324140 | Juan Carlos Uriostegui Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261064 | Juan Felipe Macedonio Santiago | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202322132 | Juan José Tagle Arcos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031255 | Juan Manuel Mejia Navarro | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033122 | Julio Cesar Eder Tovar Bueno | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034780 | Karla Angelica Loya Saenz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035910 | Karla Mariana Muela Lara | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022035234 | Karmen Gabriela Cardenas Guevara | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251388 | Katia Guadalupe Camacho Avila | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020251492 | Lenin Ramon Macias Guzman | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035998 | Leticia Margarita Ruiz Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022034802 | Lizbeth Gonzalez Bañuelos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261050 | Lorena Martin Rubio | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022031551 | Luis Alfredo Felix Zazueta | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261043 | Luis Antonio Ochoa Aguilar | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202212237 | Luis Antonio Olaya Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035702 | Luis Armando Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202212278 | Luis Cesar Hernandez Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022031885 | Luis Eduardo Gallegos Treviño | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232253 | Luis Flores Patricio | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035963 | Luis Gabriel Olivas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022031484 | Luis Gerardo Rodriguez Morales | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202212229 | Luis Gustavo Ruiz Penagos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202324192 | Luis Miguel Martinez Bonilla | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035163 | Luz Maria Miranda Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022031651 | Ma. Luisa Valenciana Torres | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3243 |
| 02022034758 | Magali Jacqueline Morante Anzures | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032800 | Manuel Alejandro Rodriguez Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203792 | Marcelo Rene Marin Santiago | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324198 | Marco Antonio Lazcano Jimenez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035444 | Margarita Carolina Castillo Mares | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022031648 | Maria Concepcion Cruz Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035434 | Maria De Guadalupe Caballero Aguilar | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032100 | Maria De La Luz Cruz Alvarado | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202224230 | Maria Del Carmen Antonio Antonio | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020251387 | Maria del Refugio Aguilar Zavala | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035356 | Maria Del Socorro Juarez Velazquez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00202203274 | Maria Elena Baca Duarte | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033774 | María Fernanda Martínez Cortez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032819 | Maria Guadalupe Morales Lizarraga | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035919 | Maria Guadalupe Ortiz Rosales | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251895 | Maria Irma Barrios Rascon | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3201 |
| 00020252358 | Maria Isabel Chavez Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202215142 | Maria Jose Sanchez Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035197 | Maria Nora Nevarez Calderon | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033229 | Mariano Aparicio Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020221727 | Maribel Molina Ochoa | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3250 |
| 02022036100 | Maribel Solano González | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202321187 | Mariel de Jesus Alonso | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034207 | Mariela Liliana Valdes Becerril | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022035867 | Marilyn Raquel Paredes Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031715 | Mario Garay Silva | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252122 | Mario Javier Barragan Martinez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020221746 | Mario Juarez Esparza | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00202324221 | Mario Perez Benitez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033580 | Marisela Mora Pérez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202321189 | Martin Alejandro Gomez Morales | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035337 | Martin Alonso Andreu Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020221554 | Mateo Hernandez Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022036139 | Mauricio Raya Ballesteros | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261030 | Mayra Cagal Caporal | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 02022032864 | Miguel Alejandro Rodriguez Ramirez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035886 | Miguel Angel Cortes Garduño | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033235 | Miguel Angel Hernandez Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324234 | Miguel Angel Velazquez Genis | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020252359 | Miriam Gabriela Vargas Montes | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221550 | Misael Moises Ortega Celestino | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261040 | Missael Diaz Cruz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022032107 | Monica Alejandra Castañeda Baez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00020261035 | Nahum Ranchito Mariano | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034271 | Nancy Guadalupe Rios Avitia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032021 | Nancy Joana Huerta Dominguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033293 | Neiry Yadira Hernandez Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035267 | Nora Cecilia Lopez Ontiveros | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324255 | Nora Elia Epitacio Iturbe | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035849 | Norma Yuriria Melgar Morales | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00202203759 | Olga Margarita Nuñez Noriega | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031438 | Omar Bello Cortes | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033334 | Oscar Alejandro Panduro Soto | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261056 | Oscar Andrey Juan Martinez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252123 | Oscar Armando Diaz Guzman | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202203458 | Oscar David Padilla Huerta | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020261556 | Oscar Manuel Juarez Torres | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232283 | Oscar Montan Ixtepan | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261052 | Oscar Ortiz Flores | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202203956 | Pablo Campos Dolz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202321188 | Pablo Toto Polito | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033088 | Pamela Mendoza Diaz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202212255 | Patricia Elizabeth Capulin Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035776 | Paula Gabriela Reyes Almaguer | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035221 | Pedro Cuevas Alcantar | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324278 | Pedro Emmanuel Amaya Rodriguez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034914 | Perla Liliana Vitela Ruiz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034494 | Ramon Amaton Diaz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261055 | Ramon Carrillo Valente | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 32229 |
| 02022035103 | Ramon De la Cruz Diaz | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202212274 | Rangel Martinez Padilla | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232272 | Raúl Alejandro Meza Martínez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035981 | Raul Alonso Venegas Escudero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031939 | Rene Campos Nolasco | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251522 | Ricardo Alberto Esparza Bonilla | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022032719 | Ricardo Ramon Valencia Martinez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261058 | Ricardo Reyes Palacios | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00002025198 | Ricardo Salgado Lopez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020261033 | Rigoberto Angeles Garcia | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020232428 | Roberto Carlos Luis Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202212225 | Roque Santiago Morales | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034605 | Rosa Icela Rincon Corrales | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033244 | Rosa Jazmin Jasso Cardenas | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020261049 | Rosendo Vadal Jimenez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202212105 | Ruben Yair Farias Almazan | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261062 | Sabas Cabrera Ramos | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202208404 | Sahian Michelle Osorio Mendoza | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022034775 | Salvador Muñoz Cano | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00202523128 | Salvador Valenzuela Navarrete | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00020261057 | Samantha Evelyn Yepez Gutierrez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3212 |
| 00020261044 | Samuel Lopez Mendez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022032933 | Sandra Esparza Mendoza | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 00020261489 | Sandra Hernandez Sanchez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00202212110 | Sergio Guadalupe Gonzalez Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020221740 | Sheila Macedonia Leon Jaquez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203996 | Sofia Margarita Zepeda Fernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035536 | Susana Romero Hidalgo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3250 |
| 02022033897 | Susana Vasquez Vazquez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 00020251934 | Valeria De Santiago Alcay | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022035256 | Veronica Ortiz Esquivel | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022034945 | Victor Hugo Perez Alvidrez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035148 | Viridiana Ivett Solorzano Hernandez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022033723 | Viridiana Lastra Guevara | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202224226 | Wilberth Uvaldo Mendoza Aguilar | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3229 |
| 02022031240 | Yanelli Ayala Pahua | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251917 | Yanet Guadalupe Lopez Parra | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3234 |
| 02022032673 | Yazmin Del Carmen Urquizo Perez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033236 | Yesenia Bugarini Flores | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032618 | Yessica Hernandez Fuentes | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034076 | Yutzil Celina Cortes Alcala | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035273 | Zaira Hernandez Cardenas Gonzalez | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031872 | Zulema Karina Cruz Astorga | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020241750 | Abel Ramón Aguilera | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3248 |
| 00002025136 | Daniel Obed Martinez León | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3248 |
| 02022033500 | Ana Paola Chavez Alderete | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032584 | Mario Inciriaga Cordero | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3233 |
| 00020251256 | Kenya Alejandra Quezada Bencomo | Aduana de Ciudad Juárez con sede en Chihuahua | 55-8889-0400 | 3246 |
| 00202612823 | Armando Martinez Villalobos | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 0241 |
| 00020240620 | Julio Cesar Garcia Robles | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4800 |
| 00202203240 | Anibal Santana Fuentes | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4801 |
| 00202203287 | Lucina Garza Arellano | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4802 |
| 00202203592 | Alma Yanet Valencia Velasco | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4803 |
| 00202203743 | Mayra Enciso Martinez | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4804 |
| 00202203689 | Roberto Alejandro Reza Castañeda | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4805 |
| 00020241751 | Luis Lauro Salazar Contreras | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4806 |
| 00202423151 | Jesús Ramón Peña Treviño | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4807 |
| 02022035680 | Sara Mayela Gomez Aleman | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4808 |
| 02022033827 | Leticia Hernandez Moreno | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4809 |
| 02022035218 | Marissa Fuentes Vega | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4810 |
| 02022035076 | Raul Garcia Hinojosa | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4811 |
| 00020221924 | Mario Alberto Antonio Cabrera | Aduana de Ciudad Miguel Alemán con sede en Tamaulipas | 55-8889-0400 | 4812 |
| 00002026131 | Gregorio Badillo Hernández | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 0242 |
| 00202203187 | Javier Humberto Rodriguez Lopez | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4639 |
| 00202203804 | Zennya Judith Robles Andrade | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4640 |
| 02022034474 | Yazmin de Jesus Martinez Llerena | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4615 |
| 00002022053 | Eder Ulises Palacios Millán | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4624 |
| 00202203770 | Olga Lidia Elizondo Rodríguez | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4623 |
| 02022031633 | Ruben Octavio Castañeda Estupiñan | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4623 |
| 02022031573 | Leticia Larios Morales | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4623 |
| 02022033044 | Ma. Guadalupe Delgadillo Diosdado | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4623 |
| 02022035373 | Anabel Esperanza Ramirez Cepeda | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4627 |
| 00202203977 | Cesar Ortiz Perez | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4620 |
| 00020220613 | Jorge Alberto Cruz Gil | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4622 |
| 00202203342 | Juan Paulo Ramos Bañuelos | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4628 |
| 00202203964 | Ruth Liliana Hernandez Canuto | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4508 |
| 00202203666 | Brisa Elizabeth Santana Figueroa | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4643 |
| 02022032180 | Mayra Nereyda Rios Velasco | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4508 |
| 02022031735 | Karina Guadalupe Martinez Alvarado | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4602 |
| 02022033733 | Jesús Enrique Urias Farias | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4618 |
| 02022034860 | Milca Daniella Lopez Escamilla | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4600 |
| 00202418108 | Maria de Jesus Meza Lima | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4649 |
| 00202203530 | Alejandra Elizabeth Gonzalez Ortiz | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4619 |
| 00202203504 | Manuel Arturo Ordoñez Abalos | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4607 |
| 00202203660 | Leticia Martinez Alvarez | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4616 |
| 00202203382 | Rocio Adriana Gaytan Ochoa | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4603 |
| 00202203858 | David Lopez Gonzalez | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4606 |
| 00202203910 | Moises Rodrigo Jacome Fortuna | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4605 |
| 02022032517 | Miguel Ángel Molina Lopez | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4604 |
| 02022033263 | Rogelio Corpus Cantu | Aduana de Ciudad Reynosa con sede en Tamaulipas | 55-8889-0400 | 4647 |
| 00002026058 | Felipe Pérez Maldonado | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 0238 |
| 00202324490 | Adolfina Rodríguez Gil | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3318 |
| 02022034423 | Edgar Jassael Campos Aquino | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3308 |
| 02022032164 | Guadalupe Del Rosario Luguardo Pérez | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3319 |
| 02022035612 | Yanet Rodríguez Silvan | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3311 |
| 02022033648 | Jonatan Enciso Austria | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3314 |
| 00202203427 | Abigail Del Carmen Bravo Tellez | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3303 |
| 00002022119 | London Renee Salazar | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3309 |
| 02022035189 | Hortencia Rosado López | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3323 |
| 00202203435 | Ana Del Carmen López Cocom | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3304 |
| 02022033882 | Edith Jazmin Canales Galindo | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3310 |
| 02022034309 | Roxana Elizabeth Zarate Cuevas | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3322 |
| 02022033706 | Yara Fabiola Pérez Reyes | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3313 |
| 02022033420 | Alondra Gissel Madrigal Gutierrez | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3306 |
| 00202203445 | Jossimar Gamboa Gómez | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3302 |
| 02022035089 | Del Carmen Delgado Prado | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3305 |
| 00202324381 | Cesar Eduardo Mendoza Hernández | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3317 |
| 00020251539 | David Manuel Mendoza Gómez | Aduana de Ciudad del Carmen con sede en Campeche | 55-8889-0400 | 3325 |
| 00020250211 | Mario Alberto Limas Lopez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 0244 |
| 02022031281 | Jhoana Vianey Gayosso Sanchez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3700 |
| 00202203775 | Aldo Alberto Diaz Rodriguez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3706 |
| 02022035110 | Sahid Marquez Martinez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3707 |
| 02022032295 | Cristian Lenin Cortes Martinez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3717 |
| 00202203631 | Reyna Yazmin Lugo Carrasco | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3703 |
| 02022034125 | Cynthia Ivette Ortiz Manzanarez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3712 |
| 00020230947 | Ismael Emilio Tarin Fuentes | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3713 |
| 00020232032 | José Luis Aguirre Gonzalez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3724 |
| 02022034627 | Carlos Castro Lara | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3722 |
| 00020251043 | Juvencio Hernandez Hernandez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3718 |
| 00020251317 | Michel Manuel Solis Gordillo | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3727 |
| 00202203753 | Jose Ramon Pérez Garcia | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3704 |
| 02022032059 | Christian Prieto Olivera | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3705 |
| 02022034742 | Mariana Carolina Chavarria Cruz | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3716 |
| 00202203239 | Everardo Jose Miguel Ibarra Armendariz | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3701 |
| 02022031001 | Oscar Antonio Reyes | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3721 |
| 02022033125 | David Perez Isidoro | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3719 |
| 02022033300 | Irving Juan Barriga Escobedo-Módulos | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3702 |
| 02022035026 | Karen Del Carmen Castillo Cruz-Buzón | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3714 |
| 02022032946 | Julian Javier Juarez Otero | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3720 |
| 02022034306 | Omar Morales Cruz | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3726 |
| 00202515138 | Jose Manuel Garcia Alcaraz | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3709 |
| 02022033724 | Maurice Fuentes Martinez | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3710 |
| 02022034335 | Adrian Cortes Fonseca | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3725 |
| 02022032920 | Teresa Margarita Lopez Zapata | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3715 |
| 02022033533 | Delfilia Padua Salazar | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3708 |
| 00020240429 | José Muñoz Ramos | Aduana de Coatzacoalcos con sede en Veracruz | 55-8889-0400 | 3711 |
| 00002025158 | Pablo Matadamas Valle | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 0245 |
| 02022035254 | Karina Ponce Jimenez | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6111 |
| 02022035181 | Narda Gabriela Gpe. Treviño | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6112 |
| 00202224311 | 1/o. F. A. A. M. A. Manuel Arturo Lara Pineda | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6101 |
| 02022035904 | Victoria Ballesteros Torres | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6116 |
| 00202203825 | Consuelo Gómez Pérez | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6104 |
| 00202224308 | 2/o. Gdia. Nal. Aurelio Neftalí Melo Parra | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6100 |
| 02022035217 | Adriana Zapata Campos | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6115 |
| 00002022246 | Karla Valeria Nicolas Espinosa | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6103 |
| 00202203485 | Albino Rangel Padron | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6105 |
| 00020222443 | Jahovy Samael Hernandez Mota | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6102 |
| 00202203732 | Gloria Aracely Castillo Gonzalez | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6106 |
| 02022033052 | Librada Gonzalez Alatorre | Aduana de Colombia con sede en Nuevo León | 55-8889-0400 | 6110 |
| 00020250210 | Marino Reyes Delgado | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 0246 |
| 02022033866 | Yuliana Alpirez Sánchez | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 5500 |
| 02022033934 | Pedro Waldo Obregón | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 5509 |
| 00202203928 | Hever Torres López | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 5504 |
| 02022034465 | Freddy Arley Blanco Monterrosa | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 5511 |
| 00020251397 | Guillermo Cruz Antonio | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 5505 |
| 02022034696 | Jessica Naydú de la Cruz Peregrino | Aduana de Dos Bocas con sede en Tabasco | 55-8889-0400 | 5507 |
| 00020242450 | José Luis Francisco Megniot Camacho | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 0247 |
| 02022035771 | Patricia Bravo Enríquez | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3600 |
| 00202203570 | Valeria Alejandra Ureña Jasso | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3618 |
| 00202203711 | Rosalba Ramírez Nuñez | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3602 |
| 02022032992 | Luis Octavio Paz Corona | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3603 |
| 02022035874 | Ana Maria Flores Velazco | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3604 |
| 00020231510 | Rubén Antonio Duarte Lara | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3619 |
| 02022035925 | Angélica Solorio Magaña | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3613 |
| 00202203960 | Danya López Estrada | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3606 |
| 02022032304 | Hernán Valenzuela Montoya | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3607 |
| 02022032204 | Yirha Yashyd Ceballos Herrera | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3605 |
| 02022033160 | Jared Alilud Landeros Cañas | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3609 |
| 00020260934 | Alfredo Fidencio López Fajardo | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3617 |
| 02022032505 | Iván de Jesús González Palafox | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3610 |
| 02022031563 | Barbara Fernanda Guzmán Arvizu | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3611 |
| 00202203620 | Jorge Antonio Badillo Martínez | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3612 |
| 02022031482 | Luisa Ramos Zayas | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3614 |
| 02022033139 | Guadalupe Jaquelin Velázquez Aparicio | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3615 |
| 02022032040 | Manuel De Jesus Lara García | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3616 |
| 00202515171 | Nancy Aguirre Sánchez | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3620 |
| 00202224284 | Luis Enrique Hernández González | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3621 |
| 00002025184 | José Esteban Rico Montalván | Aduana de Ensenada con sede en Baja California | 55-8889-0400 | 3622 |
| 00020220619 | Roberto Bedolla Morales | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 248 |
| 02022034070 | Liliana Gonzalez Razo | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5200 |
| 00020222441 | Hilario Carmona Peralta | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5206 |
| 02022034844 | Imelda Guadalupe Miro Córdova | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5204 |
| 00202219150 | Lisa Ulid Márquez Hernández | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5230 |
| 00020260786 | Alexis Ramirez Renteria | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5205 |
| 00020242015 | Enrique Alejandro Gomez Camacho | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5208 |
| 02022033965 | Martina Palacios Veterán | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5202 |
| 02022032532 | Ma. Lilibel Islas Martinez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5203 |
| 02022034664 | Yesenia Liliana Rodriguez Casillas | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5231 |
| 00202219212 | Jose Edgardo Chacón Godínez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5232 |
| 00020260771 | Marco Antonio Solis Juan | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5233 |
| 02022034462 | Miguel Angel Hernandez Ortiz | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5228 |
| 02022034235 | Raquel Adriana Sanchez Nuñez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5217 |
| 00020222422 | Diego Herrera Monroy | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5218 |
| 00202208350 | Paula Fernanda Juarez Cabrera | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5219 |
| 00202324187 | Luis Humberto Ventura Hurtado | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5220 |
| 00020250729 | Luis Ernesto Morales Valdivia | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5201 |
| 00020260766 | Sergio Jimenez Garcia | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5244 |
| 02022033331 | Lizeth Vazquez Arteaga | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5245 |
| 00020251930 | Yolanda Alvarez Sanchez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5246 |
| 00020251233 | Gabriela Franco Estrella | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5211 |
| 00202203520 | Laura Beatriz Gonzalez Lopez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5209 |
| 02022032700 | Julia Lorena Ocampo Ibarra | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5210 |
| 02022031630 | Ricardo Mondragon Sandoval | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5240 |
| 00020242282 | Venancio Pardo Hernandez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5237 |
| 00202321149 | Aleydi Luz Cazarin Chávez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5243 |
| 00202203738 | Saira Guadalupe Arana Ramirez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5229 |
| 00020251216 | Fernando Moran Villegas | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5221 |
| 02022035441 | Lidia Guadalupe Campos Ibarra | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5212 |
| 02022034508 | Maria del Rosario Rivera Tamayo | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5234 |
| 02022035137 | Ricardo Sanchez Gastelum | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5207 |
| 02022035784 | Alejandra Elizabeth Ruiz Cabrera | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5224 |
| 00020250825 | Ingrid Citlalli Blanco Rubio | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5214 |
| 02022034365 | Osvaldo Andrade Guerrero | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5222 |
| 02022035580 | Fabiola Margarita Hernandez Barajas | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5241 |
| 02022036186 | Sofia Isabel Moreno Aguilar | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5225 |
| 00020251436 | Jose Alberto Macias De la Cruz | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5215 |
| 02022035927 | Josué Sandoval García | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5239 |
| 00020260776 | Rosa Elizabeth Anza Lopez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5235 |
| 02022031005 | Julio David Hernandez Cabrera | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5213 |
| 00020261689 | Francisco Jeronimo Reyes | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5227 |
| 00020221526 | Perla Briyi Hernandez Martinez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5226 |
| 02022031422 | Maria Dolores Orquidea Cruz Valdez | Aduana de Guadalajara con sede en Jalisco | 55-8889-0400 | 5242 |
| 00020250927 | Otilio Ramírez Serrano | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 0249 |
| 00202203883 | Paulina Ramírez Flores | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2200 |
| 00202203253 | Armando Gómez Gómez | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2202 |
| 00202203710 | Mayra Lizeth Aranda Morales | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2203 |
| 00002025178 | Juan Rios Balderrama | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2201 |
| 00202203781 | Eduardo García Gutiérrez | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2204 |
| 00020221917 | José Alberto Hernández Reyes | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2217 |
| 02022034225 | Fabiola Gabriela Arenas Mares | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2205 |
| 02022031433 | José Ángel Ramos Aguirre | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2211 |
| 00002024069 | Fidencio Sánchez Arias | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2216 |
| 00202423147 | Pedro Monjaras | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2218 |
| 00002024197 | Carlos Buenrostro Márquez | Aduana de Guanajuato con sede en Guanajuato | 55-8889-0400 | 2213 |
| 00002025108 | Gerardo Tena López | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251391 | Eva Paulina Aranda Uriarte | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | 2809 |
| 00020251360 | Alvaro Melo Jurado | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032640 | Saul Landeros Gutiérrez | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203855 | Mariana López Garcia | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230420 | Pablo Cesar Cazares Molina | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034421 | María Judit López Ruiz | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203406 | Juan Gabriel Ruiz Mejia | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203951 | Jorge Jesús Sifuentes Garcia | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203610 | Gabriel Alejandro Rosas Montes | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251541 | Adalberto Aviles Malaga | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203927 | Limhi Padilla Hernandez | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203946 | Jesús Manuel Berrelleza Astorga | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251140 | Oscar García Monge | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020241613 | Denisse Martínez Franco | Aduana de Guaymas con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002025029 | Zenón Cruz Estrada | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 0251 |
| 00002025105 | Mario Ortiz Morales | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6400 |
| 02022033410 | Andrea Karely Ruiz Hernández | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6404 |
| 02022031949 | Juanita Annel Coronado Morales | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6411 |
| 02022035690 | Alma Susana Álvarez Abaroa | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6418 |
| 02022034136 | Sandra Lorena Moreno Gámiz | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6413 |
| 00202203334 | Mauricio Ruiz Aparicio | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6403 |
| 00202203441 | Juan Pedro Montaño Aguilar | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6405 |
| 00202203835 | María Esther Luja Ávila | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6409 |
| 02022032418 | Karina Guadalupe Ramírez Méndez | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6406 |
| 02022031495 | Alondra Vanessa Santillán Váldez | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6434 |
| 02022033632 | Lizeth Falcón Curiel | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6431 |
| 02022032239 | Mirna Malibé Cortez Bustamante | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6408 |
| 02022031951 | Ángel Pascual Beltrán Mercado | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6407 |
| 02022031731 | María del Rosario Cervantes Espinoza | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6433 |
| 00202203204 | Erick de Jesus Muñoz Ojeda | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6401 |
| 02022031280 | Luz Adriana López Aquino | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6410 |
| 00202203772 | Ney Denis Navidad Murrieta | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6402 |
| 00202418105 | Elizabeth López Garcia | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6432 |
| 02022033218 | Karen Guadalupe Rico Escobar | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6412 |
| 00202321166 | Amayrany García Andrade | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6416 |
| 02022033186 | Perla Judith Rodríguez Carrillo | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6417 |
| 00202203809 | Pastor Manzanarez Ayala | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6414 |
| 02022036037 | Iván Antonio Ceceña Novelo/Por asignar cambio usuario | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6419 |
| 02022035621 | Lineth Unzón Avilés/Por asignar cambio usuario | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6420 |
| 00202321102 | Jade Selene Matteotti Sánchez/Por asignar cambio usuario | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6415 |
| 00202203604 | María Laura Audino | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6421 |
| 02022032153 | Silvia Leonor Solís Núñez | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6422 |
| 02022034645 | Ángel Rafael Cartagena Montiel | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6423 |
| 02022034756 | Fernando Cuauhtémoc García Frías | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6428 |
| 02022031634 | Valeri Yuleima González Anzures | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6429 |
| 02022031441 | Aleksei Cervantes Zurita | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6430 |
| 00202203823 | Karla Amada Acosta Abaroa | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6424 |
| 02022031200 | Alaan Alberto Meza Payen/Por asignar cambio usuario | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6425 |
| 00202203402 | Nydia Betsabeth Chamorro Aldeco | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6507 |
| 00202203972 | Xochitl Liliana Tirado López | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6426 |
| 02022032917 | Oscar Corona Piña | Aduana de La Paz con sede en Baja California Sur | 55-8889-0400 | 6427 |
| 00202203102 | Armando Almaguer Vargas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 0252 |
| 00020250965 | Jose Israel Ordoñez Martínez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2964 |
| 00202324478 | Lizeth Ramírez Prado | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2900 |
| 00020230421 | Perfecto González Pérez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2919 |
| 00202221249 | Luis Fernando Plancarte Garcia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2900 |
| 00020230620 | Virginia Guatemala Rios | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2920 |
| 00202224316 | Jose Manuel Cabuto Fuentes | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2920 |
| 02022035725 | Olympia Castro Saenz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2923 |
| 00202215212 | Alberto Herrera Herrera | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2923 |
| 00202610200 | Carmen Julissa Jaimes Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2923 |
| 00202418110 | Ana Paola Ferez Barragán | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2923 |
| 00020241752 | Oscar Garcia Ayala | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2918 |
| 00020251312 | Hugo Manuel Duran Peñaloza | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2918 |
| 02022031786 | Veronica Garcia Aguilar | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2913 |
| 02022033295 | Lilia Ramirez Zaragoza | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2912 |
| 02022032476 | Laura Morales Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2913 |
| 00202324519 | Natalia de Jesus Garcia Galeana | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2913 |
| 00202612538 | Andres Uriel Lopez Castillo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2913 |
| 00202324462 | Juan Carlos Sanchez Serrano | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2914 |
| 02022032077 | Blanca Areli Muñoz Martinez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2914 |
| 00202612548 | Selenia Coral Ramirez Torres | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2914 |
| 02022033886 | Miguel Humberto Saucedo Berber | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2941 |
| 02022033791 | Cristian Ramirez Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2941 |
| 02022033166 | Osmara del Carmen Alonso Garcia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2941 |
| 02022035764 | Mayra Annie Hernandez Sotelo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2912 |
| 00020250748 | Everardo Cruz Villegas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2912 |
| 00202324416 | Gustavo Bibiano Rebollar | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 02022032200 | Fabiola Anabel Ruiz Nuñez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00020240839 | Arturo Sanchez de la Cruz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202402105 | Javier Martinez Del Viento | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00020232164 | Jesus Díaz Alvarado | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00020240833 | Jose Cruz Cruz Colector | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202324484 | Luis Ernesto Fuentes Santos | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202215211 | Martin Martinez Santiago | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 02022033272 | Jessica Itzel Rodriguez Torres | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00020240297 | Leo Michell Madrigal García | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00020251915 | Leonardo De Jesús Díaz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202324505 | Mauro Estudillo Santos | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612527 | Ricardo Aponte Bibiano | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612534 | Blanca Cecilia Morales Flores | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612526 | Humberto Prestegui Herrera | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612550 | Jazmin Patricia Loranca Baños | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612564 | Edin Meza Maldonado | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612569 | Amadeo Arnulfo Bolaños Romero | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612574 | Arizbeth Orozco Doroteo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612578 | Cuauhtemoc Popoca Cerpas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612337 | Hector Gomez de la Paz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612313 | Maritza Rodales Lara | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 00202612833 | Raul Navidad Hernandez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2944 |
| 02022031210 | Oscar Omar Nuñez Pulido | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00020230710 | David Pichal Coto | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202324570 | Zayra Alejandra Montiel Mendoza | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2972 |
| 00202215214 | Abraham Nery García | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202324494 | Ma. Fernanda Cisneros De La O | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00020240640 | Christa Yoshari Flores Sandoval | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022034757 | Ivan Emmanuel Trejo Flores | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00002025183 | Erik Meneses Espinosa | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022033082 | Christian Ivan Espinoza Meraz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00020231727 | Ma. Luisa Flores Carbajal | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022034227 | Marino Antonio Ordaz Tay | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022034003 | Mariela Ramirez Morales | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022031047 | Jose Guadalupe Govea Calzada | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022033991 | Maritza Velasco Chavarria | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022034543 | Diana Olivia Miranda Santos | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00020260541 | Monserrat Ramirez Calderon | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00020260540 | Maria de Lourdes Palomares Cortez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022032708 | Samira Nisamid Solis Galvez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022033824 | Fortino Cuauhtenango Salazar | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612542 | Mayra Alejandra Saucedo Perez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612529 | Flor Paola Ramos Garcia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612339 | Jorge Castañeda Garcia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612340 | Kevin Alexis Valdivia Molina | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612545 | Ulises Ledezma Vazquez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612533 | Liney Munguia Santiago | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612308 | Jose Miguel Ruiz Olea | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 00202612532 | Juan Pablo Servin Rodriguez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2971 |
| 02022032531 | Andrea Monserrat Santillan Baños | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2905 |
| 00020251910 | Edgar Agapito Castillo Rosas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2904 |
| 02022031314 | Carlos González Álvarez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2904 |
| 00020251911 | Jaime Jesús Espinosa Mora | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2904 |
| 00202612583 | Georgina Barajas Gonzalez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2905 |
| 02022034392 | Nataly Ramirez Castro | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2905 |
| 00202612582 | Ximena López Arzate | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2903 |
| 02022031934 | Lizeth Mendoza Delgadillo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2967 |
| 00020251918 | Marcelino Pietro Saenz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2967 |
| 00202612572 | Andrea Lizeth Gonzalez Acosta | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2967 |
| 00020240453 | Erick Alexis Fierro Medina | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2903 |
| 00020260544 | Guadalupe Montesinos Santiago | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2904 |
| 00020260536 | Mayra Savala Diaz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2905 |
| 02022033980 | Hector Darinel Gonzalez Luna | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2905 |
| 00020260539 | Jesús Ivan Mendoza Rodriguez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2904 |
| 00202612551 | Jesús Villanueva Morales | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2901 |
| 00020251882 | Itzel Juarez Galvan | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2901 |
| 00202612515 | Luis Angel Niño Morales | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2901 |
| 02022035947 | Raquel Cortes Silva | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2901 |
| 02022036200 | Neferita Peña Correa | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2901 |
| 00202203942 | Jose Antonio Hilarion Mejia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2905 |
| 00020260613 | Mario Naranjo Elvira | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612309 | Maria Guadalupe Castañeda Torres | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612537 | Sheyla Betzaida Soto Pineda | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612321 | Yunuhen Azucena Ibares Gonzalez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612563 | Alondra Amairani Vazquez Perez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612544 | Gustavo Adolfo Guzman Ortega | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612565 | Silvano Najera García | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612540 | Itzel Adonay Acosta Villegas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202203380 | Yolanda Hernandez Sanchez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00202612581 | Elesvan Revelino Patiño Salas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 02022033689 | Christopher Eden Wynter Peña | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2908 |
| 00020260538 | Kahori Ahumada Diaz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2969 |
| 00202224345 | Martha Zamudio Soto | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2969 |
| 00202612579 | yessica Morales Cabrera | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2969 |
| 00202612519 | Jose Luis Porras Vazquez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2969 |
| 00202215213 | Jacqueline Marisol Soto Vazquez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2969 |
| 02022035401 | Armando López Espíndola | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2967 |
| 00020251913 | Ignacio Prieto Quinatana | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2916 |
| 02022034660 | Daniel Jacome Cortes | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00002025196 | Hiram Vazquez Escobedo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202224319 | Jorge Garcia Cruz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00020240283 | Daniel Lopez Perez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202224320 | Eyder Arturo Lopez Barajas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00002025208 | Raul Nuñez Ramos | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 02022033854 | Luis Hernandez Briseño | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202612555 | Carla Iveth Lucatero Estrella | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202612558 | Ana Guadalupe Camacho Rodriguez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202612338 | Javier Gomez Zarco | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202612319 | Ulises Sierra Carrillo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00202612320 | Victor Hugo Vazquez Sanchez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00002025197 | Hugo Enrique Cruz Ibarra | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 02022032452 | Daniel Luna Castillo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 02022034792 | Ricardo Castro Parada | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 02022032561 | Leovigildo Israel Virgen Palacios | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 00020251855 | Raul Ramirez Galeana | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2915 |
| 02022033273 | Juan Alberto Villegas Valenzuela | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2963 |
| 02022032311 | Marcelino Lopez Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2963 |
| 02022031079 | Jorge Daniel Rocha Rea | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2963 |
| 02022032034 | Claudia Liliana Gutierrez Cano | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2973 |
| 00020240824 | Mauro Valentin Canto Yama | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2973 |
| 00020251829 | Ricardo Soto Alemán | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2968 |
| 02022034751 | Lluvia Cristal Sánchez Hernández | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 02022031577 | Yazmín Nagely Martínez Pizaña | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2909 |
| 02022034822 | Nancy Olguin Cruz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 02022032804 | Zintli Carachure Segura | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 02022031980 | Neftalí Adame Chávez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202215227 | Geovanny López Silva | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00020251916 | Rafael Suárez Garcia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202402109 | Apolinar Santiago Trinidad | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612552 | Victor Ivan Orozco Mendez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612322 | Larissa Perez Cabello | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612323 | Claudia Guadalupe Pano Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612176 | Adriana Lizeth Villicaña Reyes | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612177 | Yadira Carranza Serna | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612570 | Mauricio Boyzo Álvarez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612541 | Dioselina Trujillo Cruz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612554 | Carlos Enrique Reyes Villagómez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 02022033861 | Julio Antonio Jiménez Campos | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 02022031316 | David Carballo Carranza | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00020240293 | Daniel Ernesto Estrada Lucas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00020240822 | Omar Mayo Galmichi | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612315 | Ramon Olvera Balcazar | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612568 | Fredy Ramon Cuevas Carrillo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00202612560 | Jose Angel Yepez Fraga | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2911 |
| 00002026134 | Cesar Adolfo Gutierrez Suarez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2910 |
| 00020251811 | Francisco Aaron Jaramillo Soto | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2970 |
| 00202511100 | Mitzi Jocelyn Hernández Fuentes | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022033973 | Jose Adan Jiménez Rodríguez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2952 |
| 02022034410 | Cintia Irais Nuñez Gomez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022031146 | Victor Hugo Mercado Miranda | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00020251830 | Elizabeth Gerónimo García | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022034269 | Haide Rodríguez Lozano | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022033062 | Juan Jose del Rio Vargas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022032334 | Germain Orozco Diaz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022032385 | Perla Dalila Rodríguez Naranjo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022031380 | Celia Cruz Balderas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022032707 | Maria Cecilia Palomares Villanueva | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00020252125 | Brayan Isaac Palma Gutierrez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00020260545 | Guadalupe Carpintero Diaz | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00020260578 | Antonio Rosiles Madrid | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00020260537 | Victor Hugo Paz Araiza | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022032051 | Luis Mauricio Urrutia Torres | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612530 | Diego Ivan Lemus Troncoso | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612528 | Alejandro Mancera Callado | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612536 | Hugo Alejandro Galindo Ornelas | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612557 | Perla Alcala Aceves | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612562 | Diego Gabriel Beltran Mejia | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612566 | Karla Patricia Velasco Aburto | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612580 | Alejandra Serna Martinez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612311 | Norberto Javier Ramon Jimenez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00202612543 | Shary Hazel Vieyra Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 00020261259 | Armando Prado Trejo | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2956 |
| 02022031163 | Jael Abigail Damian Camaal | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2950 |
| 00202612575 | Angelita de la Cruz Ríos | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2950 |
| 00020250959 | Angel Alexis Guillen Hernandez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2950 |
| 00202612546 | Alicia Ramírez Luviano | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2950 |
| 00202612175 | Yunuen Soto Sandoval | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2950 |
| 00202203765 | Daniela Santiago Rondin | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2943 |
| 02022032211 | Adyeni Carrasco Parra | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2942 |
| 00020251491 | Alexis Rafael Aburto Galvez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2942 |
| 00202324342 | Alan Alberto Aguilar Caballero | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2922 |
| 02022033835 | Nery Mercado Cano | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202324548 | Sylvia Brown Rogel | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00020230625 | Edgar Roman Rodriguez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00020251144 | Fernando Magallón de la Rosa | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00002025199 | Cosme Ezequiel Espinosa Zarate | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00020260542 | Obed Simei Flores Jaimes | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00020230415 | Augusto Ernesto Navarrete Hernandez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612553 | Nancy Navarro Monjes | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612317 | Sofia Ramirez Lopez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612559 | Abigail Barrientos Vieyra | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612516 | Fabiola Rodriguez Maldonado | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612539 | Noemi Lopez Orozco | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612549 | Nancy Alejandra Rodriguez Rodriguez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00202612523 | Ricardo Osvaldo Escoboza Ayala | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00020221719 | Graciela Galvan Galvez | Aduana de Lázaro Cárdenas con sede en Michoacán | 55-8889-0400 | 2906 |
| 00020230849 | Rodolfo Torres Chávez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 0253 |
| 00020230724 | Jose Roberto Sandoval Gonzalez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1900 |
| 00202224327 | Fabiola Dimas García | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1900 |
| 02022034970 | Lidia Medina Morales | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1900 |
| 00202313222 | Felicita Velasquez Rodríguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1900 |
| 00202423150 | Jensen Daniel Cacho Villaseñor | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1937 |
| 00020230752 | Gonzalo Eduardo Medina Trejo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5519341811 |
| 00020252373 | Ediel Antonio Juan Alor | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9214386582 |
| 00020230741 | Citlaly Amairani Vargas Abadia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2294532102 |
| 00020240281 | Javier Casillas Sibaja | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9624200013 |
| 00202203646 | Yahaira Janet Espinosa Rubio | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1914 |
| 02022031185 | Luis Alejandro Jimenez Herrera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1914 |
| 02022034018 | Maria Josefina Larios Delgadillo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1914 |
| 00020231730 | Normando Lorenzo Paniagua Aquino | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1950 |
| 00002023073 | Diego Abraham Maldonado Arteaga | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1950 |
| 00202224322 | Jorge Luis Gonzalez Quintero | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1950 |
| 00020251243 | Javier Armando Balderas Garcia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1950 |
| 00020230740 | Enrique Mateo Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1950 |
| 00020230533 | Martha Valdez Dueñas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1950 |
| 02022031666 | Brenda Gabriela Gomez Sanchez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1900 |
| 02022034899 | Eddie Ascencio Mendez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 554 |
| 00020251227 | Gisel Gallegos Gálvez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022034825 | Grecia Trujillo Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 777 |
| 00020251490 | Erick Rafael Ceballos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 02022033558 | Edgar Noe Lozano Ladino | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00020251588 | Sergio Armando Cabrera Bernal | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00002024047 | Laura Cecilia Hernandez Cabezas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 553 |
| 00202324527 | Rafael Hernandez Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 774 |
| 00202324515 | Moises Alcocer De Jesus | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 774 |
| 02022034511 | Helen Abigail Itza Loeza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 998 |
| 00202612376 | Karina Yocciry Rodriguez Jimenez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3339230858 |
| 02022032342 | Miguel Adrian Jeronimo Bello | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 556 |
| 02022031567 | Adriana Luevano Peña | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 899 |
| 00020251532 | Alfredo Escobedo Lewis | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 646 |
| 02022033679 | Thelma Nizeth Ramos Bautista | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 867 |
| 00020232192 | Cain Gonzalez Linares | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00020251594 | Isabel Alonso Buenrostro | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 313 |
| 02022034043 | Patricia Magdalena Leal Sanchez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202321103 | Jose Cruz Nava | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020232198 | Luis Antonio Vazquez Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 552 |
| 00020251213 | David Everardo Garcia Alonso | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00020251533 | Jaime Verde Castañeda | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 669 |
| 02022032926 | Erick Noe Sanchez Torrez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 722 |
| 02022033070 | Ana Luz Romero Vargas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 755 |
| 02022032710 | Andrea Berenice Flores Zavala | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 445 |
| 02022032736 | Victor Manuel Amezcua Jimenez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022034226 | Benjamin Alejandro Villagran Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 331 |
| 00020251442 | Christopher Angel Vazquez Aguirre | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 557 |
| 00020232188 | José Gerardo Acosta Perales | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00020251445 | Alexis David Morales Epitacio | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 554 |
| 02022033215 | Edith Salvador Palacios | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 553 |
| 00020261261 | Miguel Alejandro Castro Salcedo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022031844 | Claudia Mercedes Vega Coria | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022032207 | Octavio Exjayar Sanchez Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 735 |
| 00020251374 | Carolina Urias Ruiz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 668 |
| 00020251441 | Juan Carlos Gonzalez Ayala | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 551 |
| 00020251816 | Jose Adrian Leonardo Abad | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251329 | Edwin Esteban Pineda Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 755 |
| 00020251589 | Maria de los Angeles Miranda Verjan | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022034730 | Francisco Javier Angeles Ramirez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 553 |
| 00202321167 | Jorge Villareal Leónides | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 555 |
| 00020251458 | Rodrigo Salvador Nuñez Ramos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 551 |
| 02022034501 | Mirna Maritza Santoyo Villa | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 622 |
| 00020230754 | Javier Arteaga Fragoso | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 713 |
| 02022033447 | Jovanna Escamilla Rodríguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 554 |
| 00020230747 | Carlos Alberto de la Cruz Vazquez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020230722 | Alejandro Reyes Jimenez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00020251461 | Arturo Vazquez Cabañas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 686 |
| 00020251815 | Miguel Angel Chavez Betanzos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 753 |
| 00020230731 | Hugo Espinosa Felipe | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 229 |
| 00202324350 | Ana Karen Cruz García | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 555 |
| 00202203262 | Irma Morett Araiza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1951 |
| 02022031301 | Roberto Gomez Gonzalez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1911 |
| 02022032731 | Erika Esmeralda Vargas Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1911 |
| 00202324533 | Ricardo Manuel Lopez Cardenas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1911 |
| 00020230536 | Juan Diego Santana Brambila | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1911 |
| 00020230755 | Irving Osorno Vasquez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1911 |
| 00020251818 | Adriana Guadalupe Barajas Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1911 |
| 00020251585 | Hugo Ivan Perez Castillo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1912 |
| 02022033426 | Jose Eduardo Chavez Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1912 |
| 02022032162 | Arsenio Chavez Manzano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1912 |
| 00020251839 | Juan Javier Guerrero Huitron | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1912 |
| 02022031998 | Laura Ojeda Godinez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 00202203833 | Yolanda Olivares Sanchez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 00202324480 | Lucia Verduzco Salazar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 02022031912 | Alma Monserrath Limon Escamilla | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 00020240651 | Uziel Ulises Lucho Gonzalez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 02022035421 | Maria Tayde Ochoa Chavez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1976 |
| 00020251870 | Maria Fernanda Ibarias Ventura | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 00020230757 | Jesus Hernandez Madrigal | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1973 |
| 00202203679 | Nubia Citlalli Guzman Alvarez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 02022033248 | Laura Susana Garcia Sotelo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 00020230535 | Maria Del Refugio Hernandez Peña | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 00002025159 | Mario Jose Chang Medina | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 00020251591 | Elizabeth Gudiño Mendoza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 00020230750 | Agustin Sarao Martinez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 00002023076 | Brenda Herrera Paredes | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1959 |
| 02022032836 | Fabiola Ramirez Peña | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1952 |
| 02022032492 | Lina Fabiola Murguia Robles | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1952 |
| 02022031007 | Fernando Roman Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1952 |
| 02022033707 | Nayeli Estefani Madrigal Orozco | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1952 |
| 00202324436 | Jenifer Noemy Ruiz Vargas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1952 |
| 00020240853 | Esther Espinoza Cardenas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1952 |
| 00020251496 | Mayra Hernandez Davila | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1976 |
| 02022032870 | Paulina Garcia Haaz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1976 |
| 02022032124 | Mirtha Berenice Torres Lugo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1976 |
| 00202224340 | Omar Alejandro Sanchez Betancourt | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1976 |
| 02022034143 | Yurai Hernandez Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1976 |
| 00202203395 | Julia Elizabeth Muñiz Sierra | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022033350 | Mayra Janeth Luna Nández | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020251592 | Fernando Coronel Ramirez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022032155 | Bernardo Alonso Velazquez Cordova | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020240413 | Cinthia Kaori Valdez Ornelas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 315 |
| 00020251025 | Lizbeth Bolaños Castillo de Lerin | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 554 |
| 02022033603 | Esther Fonseca Tamariz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 971 |
| 00020240239 | Martin Centeno Martinez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020240829 | Juvencio Marcelino Ayodoro | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022032637 | Xochilt Georgina Meza Ruiz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022031858 | Jhonny Fernando Partida Corona | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020250964 | Atenea Donaji Gonzalez Gerardo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 962 |
| 02022035115 | Miguel Angel Mendez Soria | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 551 |
| 02022034596 | Horacio Carreño Carreto | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202515121 | Ximena Monserrat Ramirez Galeana | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 777 |
| 00202402101 | Enrique Vicencio Carballo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 334 |
| 02022032868 | Rosa Hernández González | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022032520 | Lucero Hernandez Del Angel | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 785 |
| 00020251375 | Graciela del Carmen Rodriguez Martínez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 971 |
| 02022032039 | Cipriano Montes De la Mora | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3121002164 |
| 00020230748 | Luis Cruz Alatriste | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2293653725 |
| 00020251814 | Daniel Reyes López | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7531737335 |
| 00020230749 | Dacya Selene Lara Heredia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2291592243 |
| 00020251452 | Víctor Manuel Mendoza Hernández | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2282767998 |
| 00020251024 | Rogelio Manuel Suárez Medina | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 02022031247 | Omar Alfredo Damian Vilorio | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 00020230729 | Eric Ramiro Uc López | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 02022032109 | Luis Angel Solis Flores | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 02022032035 | Daniel De la Peña Rincon | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 00020251531 | Jair Roman Gallegos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 02022032929 | Maria Carolina Lopez Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1906 |
| 02022034230 | Crismar Agustin Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3311730844 |
| 02022033055 | Sergio Maximiliano Guzman Gomez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3143572726 |
| 02022034145 | Myriam Esmeralda Hernandez Ramirez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9581153344 |
| 02022031427 | Rubén López Moreno | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6311787633 |
| 00020230719 | Romeo Castillo Velasco | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3351203031 |
| 02022033847 | José De Jesús Vázquez Alvarado | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141614892 |
| 02022033527 | Vincent Slax Guadarrama Serrano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7224045464 |
| 02022033997 | Ángel Mauricio Rodríguez Rodríguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6643557284 |
| 00020230759 | Miguel Ángel Santiago Lucas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141249817 |
| 00020230746 | Héctor Noe Pérez Contreras | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9711263813 |
| 00020230744 | Luis Manuel Pérez Reyes | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2296050337 |
| 00020251497 | Angela del Rocío Sandoval Robles | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3121189174 |
| 02022033919 | Lourdes Martinez Agudo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3143524439 |
| 00202610180 | Manuel Humberto Espericueta Meza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6121510882 |
| 00020250960 | Iván Cardoso Hernández | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251593 | Cristihian Uscanga Solís | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020261560 | Iván Alejandro Reyes Romero | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 229 |
| 02022033634 | Jhovany Mendez Mendez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 477 |
| 00202203684 | Adriana Salazar Carrillo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031662 | Luis Alberto Nataren Ocaña | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034107 | Efrain Vazquez Iglesias | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033620 | Jorge Martinez Manuel | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020251029 | Alejandro Juarez Pineda | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033345 | Leonel Valdez Andrade | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020230733 | Rubi Esmeralda Luna Calderon | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034611 | Eduardo Hernández Lora | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022032028 | Karina Celene Lugo Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020240412 | Guillermo Alfonso Melgoza Flores | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00002023071 | Jordy Ulises Herrera Moreno | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033979 | Dulce Maria Peraza Díaz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031889 | Alejandro Carlo Hernandez Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033333 | Constanzo Davalos Ornelas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00202324459 | Josian Israel Juarez Martinez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00202324382 | Christian Nanyeli Gonzalez Flores | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00202215236 | Edgar Alejandro Gonzalez Mayo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031320 | Leticia Gonzalez Olvera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00202514100 | Zayra Guadalupe Figueroa Santos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033041 | Ana Isabel Chocoteco Hinojosa | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020251850 | Liczy Reyes Galindo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020240415 | Jeny Belen Delgado Sanchez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022032699 | Jonathan Ivan Calderon Olivares | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022032052 | Irving Colorado Gracia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020240277 | Carlos Daniel Lazcano Ortiz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020240241 | Jorge Guillermo Pichardo Sanchez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022032578 | Joiarib Medina Almanza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00202324466 | Judith Contreras Medina | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033684 | Daniel Enrique Lopez Martinez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020230756 | Arturo Grimaldo Vieyra | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034918 | Sergio Robles Zamora | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031167 | Diana Abigail Archila Solar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034598 | Alan Armando Garcia Fuller | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00202324499 | Maria Teresa Ornelas De la Paz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020251240 | María Guadalupe Pacheco Salgado | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00002024048 | Azucena Carrillo Verjan | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022035032 | Bernardo Maciel Salas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031780 | Magali Bribiesca Capitan | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031153 | Federico Mendez Garcia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022032265 | Cesar Ivan Zamora Gallegos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034789 | Manuel Sanchez Duran | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034638 | Simon Cedeño Ruiz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031361 | Ilse Vianey Martinez Guerrero | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022031673 | Yajaira Itzel Rueda Pineda | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034417 | Luis Enrique Lopez Flores | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034770 | Cesar Casarez Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022033369 | Natanael Sandoval Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022032565 | Jehovani David Rueda Guzman | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 00020230727 | Miriamm Jaquelin Hernandez Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1955 |
| 02022034300 | Abigail Solórzano Juárez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 962 |
| 00202203754 | Kenia Mariela Huerta Aguilar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 02022031859 | Alejandra Aleli Bautista Geronimo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020250961 | Jesus Abraham Perez Cristin | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9211056839 |
| 02022033767 | Jaqueline Samperio Polo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7751443885 |
| 00202324440 | Jhonny Negrete Madrid | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9622408685 |
| 02022033860 | Diana Ochoa Hermosillo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202203589 | Rosendo Alfredo Guzman Nañez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020250743 | Jorge David Mendoza Rodríguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00020251228 | Gustavo Alexis Márquez Cortés | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 564 |
| 00020251229 | Arnoldo Alcaraz Velázquez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00020251238 | César Daniel Romero Martell | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202203480 | Juan Carlos Martinez Chavez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022032111 | Yurixhi Acuario Guerrero Rendón | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 668 |
| 02022033179 | Mariel Sandoval Lozano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 222 |
| 02022031970 | Elsa Guadalupe Rosales Herrera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 311 |
| 02022031785 | Jose Daniel Maldonado Llamas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020251499 | Roxana Yesenia Robles Tello | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020251817 | Cecilia Guadalupe Madrigal Alonso | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033191 | Claudia Nohemi Vazquez Baliño | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 444 |
| 02022034396 | Melany Osorio Guillermo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202203974 | Gilberto Gutierrez Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022034762 | Rosa Mayra Carrasco Santiago | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 729 |
| 02022034062 | Ruben Rodolfo Camacho Bermudez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 744 |
| 02022031833 | Carlos Eugenio Lucas Sanchez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 229 |
| 02022032250 | Dulce Alejandra Solis Salazar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 868 |
| 00202324536 | Rosalinda Venegas Gomez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033637 | Julia Guadalupe Arana Ortega | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 775 |
| 02022032560 | Hermila Marbey Zunun Ramirez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 963 |
| 02022033540 | Alfredo De la Torre Nava | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 02022033528 | Reyna Elizalde Escudero | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 775 |
| 02022031945 | Josue Antonio Reyes Peña | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032351 | Valente Angeles Bautista | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 442 |
| 00020251590 | Guadalupe Monserrat Salcido Escobar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 669 |
| 02022032454 | Teresita De Jesus Melchor Gomez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1923 |
| 02022032023 | Uri David Ramirez Ballinas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1923 |
| 02022032556 | Doris Moncada Fernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 222 |
| 02022032648 | Carlos Alberto Mendez Pacheco | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 493 |
| 02022032587 | Maria Victoria Valencia Cuevas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 313 |
| 02022032569 | Wendy Zuleyma Abarca Ramirez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202224334 | Julio Cesar Osorno Hueso | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00020230739 | Luis Alberto Luna Monje | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230734 | Luis Enrique Alatriste Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002023072 | Roberto Carlos Marquez Salvador | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 615 |
| 00020230716 | Elber Rafael Pablo Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 971 |
| 00020232191 | Armando Hernández Santiago | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00002023074 | Luis Angel Rafael Martinez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2291289822 |
| 00020230712 | Jose Alfredo Villasana Valencia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3151098983 |
| 00202203990 | Clara Isabel Soto Salazar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141486084 |
| 02022034413 | Antonio De Jesus Malvaez Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141746194 |
| 02022033569 | Sergio Gonzalez Larios | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141164677 |
| 02022031276 | Arturo Cristaldi Rodriguez Zambrano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9621702713 |
| 02022032845 | Roberto Pérez Montes | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6145232366 |
| 02022034826 | Esmeralda Del Rosio Lopez Galvez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6623601548 |
| 02022034706 | Isai Ocaña Peralta | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3143384343 |
| 02022034059 | Alfredo Elizaldi Benitez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141227399 |
| 02022032791 | Diego Alberto Romero Quevedo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7775046512 |
| 02022033678 | Stephanie Cabrera Morgán | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7835815469 |
| 02022032494 | Rodolfo Ruíz Hernández | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3411228400 |
| 02022032650 | Adela Maria Rubio Cordero | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6121420560 |
| 02022032794 | Magdalena Monreal Estrada | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6647196140 |
| 02022034460 | Erick Romero Diaz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2461046192 |
| 00020240418 | José Francisco Ramírez Mandujano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3121883536 |
| 02022034078 | Fabiola Del Carmen Magaña Espinoza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141424668 |
| 02022034390 | Raquel Alejandra Valdez Gildo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141003676 |
| 02022032025 | Ivan Erick Hernandez Ruiz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141975941 |
| 02022034195 | Esmeralda Guadalupe Figueroa Rivera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 8671203047 |
| 02022031754 | Erasmo Noe Labra Vargas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7711444650 |
| 00202514101 | Daniel Alejandro Martinez Rivera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3121531847 |
| 02022031432 | Roberto Torres Laguna | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5544548513 |
| 02022032237 | Glenda Elizabeth Rico Ruiz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141708662 |
| 02022033652 | Martin Martinez Torres | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141436091 |
| 02022031555 | Aaron Amaya Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3411003975 |
| 02022031080 | Yurintzi Del Rosario Alfaro Galindo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141044966 |
| 02022034591 | Miguel Martin Rojas Bautista | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141025124 |
| 02022034498 | Juan Felipe Ayala Rochin | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3310204168 |
| 00020230823 | Humberto Antonio Cruz Juarez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5527468718 |
| 02022034229 | Jesus Sosa Orobio | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3143373308 |
| 02022031950 | Cesar Fabian Villegas Cabezas | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3143581462 |
| 02022031258 | Maria Elena Gomez Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3310278037 |
| 02022034364 | Ulises Diaz Vite | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7711244838 |
| 02022033046 | Daniel Lopez Roman | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6333377754 |
| 00020240417 | Miriam Odette Delgado Ventura | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3121963262 |
| 00020230713 | Francisco Eduardo Garcia Ramirez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141233158 |
| 00020230715 | Juan Francisco Zarate Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3344055955 |
| 00020231728 | Rigoberto Martinez Nogueda | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5565332862 |
| 00202221248 | Julio Alejandro Martinez Valdez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7831089232 |
| 00020230753 | Miguel Angel Morales Mendez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2292666854 |
| 00020230745 | Gustavo Israel Reyes Estrada | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5561607610 |
| 02022034279 | Sergio Jesus Ramirez Torres | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7531211018 |
| 00020251365 | Raul Hernandez Vazquez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 6461368876 |
| 00020230768 | Irais Torres Duran | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2292228618 |
| 00202612374 | Abraham Flores Mondragon | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5614309699 |
| 00202612593 | Abril Cruz Sánchez Espinosa | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 443 |
| 00202612744 | Alfredo Jocias Oseguera Herrera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612345 | Ali Josafat Padilla Rodriguez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3131516395 |
| 00020261296 | Andrea Cárdenas Montelongo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00202612773 | Andrea Elizabeth Blanco Hoyos | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00020261297 | Andrea Guadalupe Delgado Meza | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00202612363 | Angélica Guadalupe Solano Núñez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141814876 |
| 00202612365 | Angelica Pineda Madrid | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2414111530 |
| 00202612384 | Antonio de Jesús Hernández Solorzano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2321333639 |
| 00202612722 | Argemi Aguirre Toledo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 966 |
| 00202612797 | Blanca Estela Godinez Matias | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 962 |
| 00202612366 | Cruz Ángel Mendoza Santana | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 313 |
| 00202612382 | Daniel Enrique Rodríguez Muñoz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141657958 |
| 00202612771 | Daniel Garay Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612735 | Daniel Ortega Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612801 | Dayan Arath Hernandez Isais | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3121951672 |
| 00202612800 | Diana Elizabeth Fregoso Peña | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 322 |
| 00202612392 | Dulce MariaTeresa Ortiz Castro | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612796 | Elda Yenintzia Medina Contreras | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 669 |
| 00202612375 | Elizabeth Manrique Arroyo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 557 |
| 00202612805 | Erendida Valdez Acevedo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 951 |
| 00202612777 | Erick Jesús Roman Muñoz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 303 |
| 00202612368 | Ethna Andrea Medina Hernández | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612379 | Evelin Jazmin Camarillo Gonzalez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612193 | Fernanda Patricia Sanchez Trillo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3472 |
| 00202612770 | Heyssel Fernanda Rodriguez Gomez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612369 | Isela Guatemala Olivar | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7471847325 |
| 00202612806 | Janeth Martínez Contreras | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 669 |
| 00202612343 | Jenifer Inés Mejía Rivera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612377 | Jesus Santiago Camacho Chacon | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 712 |
| 00202612795 | John Matthew Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612388 | Jorge Alvaro Benitez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 7292859276 |
| 00202612370 | José Ángel Bermeo Luciano | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 722 |
| 00202215226 | Jose Francisco Lopez Villanueva | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612716 | José Roberto García Pérez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 921 |
| 00202612186 | Karen Anette Medrano Perez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2424 |
| 00202612371 | Kimberly Aranzazu Escamilla Pérez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141169471 |
| 00202612102 | Laura Estela Tristan Gonzalez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 00202612659 | Leidy Yaquelin Orcino Garcia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612814 | Litzy Guadalupe Acosta Oregel | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 921 |
| 00202612192 | Lluvia del Mar Valenzuela Rivera | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141021080 |
| 00202612372 | Luis Angel Garcia Garcia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612807 | Marco Antonio Lagunes Alvarado | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 9513420582 |
| 00202612779 | Maria Angelica Corona Alvarez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612380 | María Antonia Crisostomo Felix | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612195 | María José Vergara Guzmán | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 233 |
| 00202612761 | Martha Cecilia Silva Villa | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 314 |
| 00202612190 | Miguel Ángel Illescas Lerma | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 2223641278 |
| 00202612389 | Milka Sarai Gomez Lopez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 618 |
| 00202612364 | Mitzi Rubi Hernández García | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612101 | Osvaldo Ivan Lerma Wong | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 833 |
| 02022033357 | Pedro Jesus Angulo Hernandez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612378 | Pedro Orbelin Gomez Diaz | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612386 | Perla Cassandra Macías Saucedo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612769 | Porfirio López Vázquez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 313 |
| 00202612106 | Ramsés Cano Pérez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 1854 |
| 00202612373 | Raul Francisco Vega Morales | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 5547603991 |
| 00202612387 | Rosa Mariana Gutierrez Olivares | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3141431589 |
| 00202612730 | Selma Emperatriz Rodriguez Carrizales | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3142173586 |
| 00202612383 | Sergio Vargas Manzo | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 3131388310 |
| 00020261294 | Victor Angel Ruiz Gonzalez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 938 |
| 00202612390 | Yareth Betzaleel Ceja Pérez | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 312 |
| 00202612717 | Jose Mandujano Garcia | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 744 |
| 00202612827 | Cynthia Pizano Romero | Aduana de Manzanillo con sede en Colima | 55-8889-0400 | 221 |
| 00020251395 | Raul Ruiz Garcia | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 0254 |
| 02022032408 | Teresa Aranda Cruz | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4931 |
| 02022033963 | Ma. Janeth Reyes Mercado | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4909 |
| 02022031713 | Isela Duarte Marquez | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4916 |
| 02022035667 | Leticia Martinez Avendaño | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4915 |
| 00020241754 | Alberto Amezcua | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4910 |
| 00020222470 | Armando Martínez Hormiga | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4903 |
| 02022033003 | Jose Gustavo Amaro Gonzalez | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4911 |
| 00202203316 | Sandra Lorena Reyes Delgado | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4901 |
| 00202203895 | Ana Isabel Nivon Rivera | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4917 |
| 00202203356 | Raul Ángel Flores García | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4907 |
| 02022034170 | Carlos Christian Rosales Cuellar | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4912 |
| 02022034425 | Pedro Ivan Hernandez Infante | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 74109 |
| 00202203668 | Nora Velazquez Fuente | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4914 |
| 00202423145 | Ige. Silvia Viveros Garcia | Aduana de Matamoros con sede en Tamaulipas | 55-8889-0400 | 4904 |
| 00202515161 | Amador Tiburcio Bahena | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 0255 |
| 02022034385 | Erika deñCarmen Ramirez Ibarra | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3800 |
| 00020221717 | Ana Cristina Burgueño Morales | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3802 |
| 00020241755 | Francisco René Martínez Castellanos | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3817 |
| 00202423148 | Irma Guadalupe González González | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3804 |
| 00202203476 | Alfredo Javier Lopez De La Paz | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3803 |
| 02022031790 | Modesta Rios Maldonado | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3825 |
| 02022036076 | Ana Lourdes Vargas Hernandez | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3805 |
| 02022035977 | Humberto Eliseo Zatarain Jimenez | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3806 |
| 00020251853 | Bernabe Del Angel Jimenez | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3816 |
| 02022036050 | Haydee Liliana Trujillo Maldonado | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3807 |
| 02022032797 | Celiflora Sanchez Cortes | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3808 |
| 02022033240 | Juan Adolfo Chavez Carrasco | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3810 |
| 02022033602 | Amineh Avila Garcia | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3823 |
| 00202203303 | Maria Ajeaney Llamas Huerta | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3829 |
| 00202203558 | Evelyn Janett Villa Rodríguez | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3811 |
| 02022035250 | Gisela Osuna Martin Del Campo | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3814 |
| 00202203507 | Gustavo Mejia Valdez | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3812 |
| 02022033633 | Cynthia Guadalupe Herrera Aguirre | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3822 |
| 02022033242 | Carlos Herrera Valenzuela | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3809 |
| 00020252211 | Jorge Alberto Golarte Medina | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3828 |
| 02022033429 | Andrea Cobón Vallejo | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3824 |
| 02022035608 | Elsa Irigoyen Alvarado | Aduana de Mazatlán con sede en Sinaloa | 55-8889-0400 | 3801 |
| 00020220618 | Alberto Valero Padilla | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2721 |
| 00202515129 | Rafael López Román | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2723 |
| 02022034635 | Paulina Chiquete Astorga | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2710 |
| 00202208319 | Víctor Roberto Hernández Mendoza | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2706 |
| 02022032171 | Armida Berenice Olvera Mejía | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2706 |
| 00020240534 | Octavio Quintero Rodríguez | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2733 |
| 00020241756 | Carlos Felipe Cano Nuñez | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2741 |
| 00002025145 | Jose Miguel Morales Álvarez | Aduana de Mexicali con sede en Baja California | 55-8889-0400 | 2700 |
| 00002025162 | José de Jesús Barajas Santos | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 0258 |
| 02022032380 | Diana Irasema Bazaldua Linares | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3000 |
| 00020260524 | Jaime Briones Brandon | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3001 |
| 02022035343 | Veronica Yolanda Soria Tobias | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3002 |
| 00002022186 | Raquel Mercado Palacios | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3003 |
| 00202203407 | Rafael Zambrano Pedraza | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3004 |
| 00202221184 | Erick Daniel Urbina Perez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3005 |
| 00202224276 | Gloria Jazmin Aquino Diaz | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3006 |
| 00020221180 | Pedro Cepeda Salinas | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3007 |
| 00002024186 | Wilbert Edgardo Rodriguez Inostrosa | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3008 |
| 00002024188 | Juan Luis Rodriguez Lopez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3009 |
| 02022035306 | Mario Alberto Zavala Perez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3010 |
| 02022035465 | Lourdes Del Consuelo Ortiz Balandrano | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3011 |
| 02022035762 | Patricia Graciela Gonzalez Coronado | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3012 |
| 02022036158 | Yordi Yessael Celis Gamboa | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3013 |
| 00020241757 | Magdalena Mariano Escalante | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3014 |
| 02022035722 | Gabriel Alonso Miranda Menchaca | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3015 |
| 02022033197 | Yoselin Kristel Lara Gutierrez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3018 |
| 00202203982 | Elizabeth Reyes Rios | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3019 |
| 00202221177 | Jose Pablo Chagolla Gutierrez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3020 |
| 02022033619 | Yuridia Berenice Gutierrez Lozano | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3021 |
| 00020260780 | Juan Diego Pérez Pozo | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3022 |
| 00002024183 | Axel Alfredo Regalado Vargas | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3023 |
| 00202224301 | Luis Ángel Romero Reyna | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3025 |
| 00202221173 | Oscar Alejo Alonso | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3026 |
| 00020241823 | Juan Francisco Ruperto Ramirez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3027 |
| 00002024184 | Jorge Armando Rivera Martinez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3028 |
| 00020221568 | Mayra Abigail Morales Sánchez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3029 |
| 00020250740 | Mara Deyanira Loera Luna | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3030 |
| 00020232493 | Jose Humberto Champo Montejo | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3033 |
| 00020232472 | José Antonio De Jesús Hernández Gerezano | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3034 |
| 02022031588 | Julio López García | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3036 |
| 00202405192 | Juan Martin Mejia Cervantes | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3037 |
| 00202322161 | Jesus Antonio Espinoza Lopez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3038 |
| 02022032739 | Perla Guadalupe Velazquez Salas | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3039 |
| 00020241811 | Brenda Rodriguez Rojas | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3040 |
| 00202322148 | Jose Angel Hernandez Santiago | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3041 |
| 00020250826 | Lorena Margarita Carranza Galván | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3042 |
| 00020241818 | Erick Raul Ruiz Barrios | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3043 |
| 00202405190 | Dimas Maas Vazquez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3044 |
| 00020251320 | Rocio Edith Valdez Diaz | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3045 |
| 00202405189 | Ramiro Martinez Sanchez | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3046 |
| 00020241716 | Cristian Vicente Landeta Betanzos | Aduana de Monterrey con sede en Nuevo León | 55-8889-0400 | 3048 |
| 00020251185 | Gabriel Balcázar Silva | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 0280 |
| 02022032907 | Rocio Morales Guillén | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2400 |
| 00020251148 | Eusebio Sánchez Pérez | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2401 |
| 00002025092 | Julia Sánchez Arcos | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2418 |
| 00002023141 | Ana María Claustro Flores | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2421 |
| 00020251173 | Daniel Espinosa Domínguez | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2412 |
| 00002025061 | Jorge Juárez Grande | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2413 |
| 00020220771 | Ramón Efren Guexpal Arana | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2403 |
| 00020251146 | Carlos Osvaldo Vargas Ramírez | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2417 |
| 00202203745 | Alfonso Jesús Galarza Sánchez | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2425 |
| 02022033826 | Luis Roberto Sánchez Martinez | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2410 |
| 00020251467 | Héctor Iván Riubi Cuevas | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2407 |
| 00020241541 | Herminio Gois Sánchez | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2415 |
| 00020250741 | Gabriel Mejía González | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202423149 | Armando Aurelio Buendía Vigueras | Aduana de México con sede en la Ciudad de México | 55-8889-0400 | 2426 |
| 00002026111 | Rubén Solares Andrade | Aduana de Naco con sede en Sonora | 55-8889-0400 | 0259 |
| 00020222450 | Luis Ángel Rafael Velasquez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3102 |
| 02022032336 | Farah Iranie Arreola Perez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3105 |
| 00020250734 | Jose Loreto Mendez Peinado | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3109 |
| 00020241542 | Daniel Lopez Velasquez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3107 |
| 00202203573 | Luis armando Ojendiz Carbajal | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3104 |
| 00202203409 | Sarha Matia Gasca Gonzalez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3100 |
| 00202203750 | Veronica P. Martínez Yriki | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3101 |
| 00002025144 | Fernando Homero Romero Ortega | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3111 |
| 00202208214 | Javier Sanchez Gonzalez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3108 |
| 02022031943 | Jesus Alejandro Suarez Gonzalez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3106 |
| 00202215103 | Victor Manuel Suarez Perez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3110 |
| 02022032633 | Carmen Ballesteros Espinoza | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3103 |
| 00202224297 | Aldo Isaias Pérez | Aduana de Naco con sede en Sonora | 55-8889-0400 | 3112 |
| 00020232138 | Juan Rosas | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 0260 |
| 00202203869 | Gustavo Daniel Muñoz Pizaña | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4508 |
| 00202221106 | Adolfo Galdamez Ramos | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4504 |
| 02022031575 | Erik Morales Barrios | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4534 |
| 00020241027 | Moises Luis Jiménez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4546 |
| 00202324177 | Luis Enrique Cueto Pérez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4539 |
| 00202221139 | Darwi Jhovanny García Zamora | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4538 |
| 02022034272 | Diana Marcela Encinas Portillo | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4507 |
| 02022031938 | Jesús Adrian Murrieta Mondaca | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4536 |
| 00020241028 | José Luis Soto Duarte | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4540 |
| 00202203425 | Nancy Berenice Morales Flores | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4506 |
| 00202221146 | Juan Jesús de la Cruz Velazquez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4553 |
| 02022033247 | Francisco Adolfo Mariles Ruíz | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4535 |
| 00202423106 | Nestor González Pérez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4551 |
| 00202208237 | Javier Ceja Saucedo | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4502 |
| 02022031925 | Mabi Areli Calderon Verdugo | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4500 |
| 00002025242 | Joselyn Aisbet Osuna Talla | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4552 |
| 00202221128 | Aarón Hernández Marmolejo | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4554 |
| 00020221981 | América Jaramillo Aguilar | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4558 |
| 00202515183 | Flor Denira Villegas Lozania | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4519 |
| 00202203583 | José Ismael Maldonado Espinosa | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4512 |
| 00202208284 | Emilia Guadalupe Roque Juárez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4515 |
| 02022034251 | Hector Benitez Mendez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4517 |
| 02022035491 | Gina Grisel Rivera Limas | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4501 |
| 00202203746 | José Luis Federico Orozco | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4511 |
| 02022035499 | Arturo Prado Carvajal | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4509 |
| 00202423169 | Jaqueline Armenta Ruelas | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4505 |
| 02022035972 | Olivia Romero Gamez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4510 |
| 02022032309 | Arely Aleli Palacios Mendoza | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4514 |
| 00002022245 | Laura Elena Domínguez Santos | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4516 |
| 02022032919 | Gabriel René Flores Martínez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4524 |
| 00020231398 | Andrés González Mirafuentes | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4532 |
| 00202322160 | Jesús Daniel Díaz Silva | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4531 |
| 02022032445 | Arely Pérez Lugo | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4559 |
| 00020221996 | Kimberly Sarahi Castro Montes | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4526 |
| 00020241537 | Diana Gabriela Mapula Aispuro | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4518 |
| 00020261085 | José Manuel Montes Bibiano | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4530 |
| 00202208268 | Gaudencio Cobaxin Tome | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4533 |
| 00020231917 | Joel Lara Escarola | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4525 |
| 02022032198 | Jesús Beatriz Chavez Guevara | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4556 |
| 02022031842 | Myrna Dolores Ortega Yescas | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4521 |
| 00020231918 | José Manuel Moreno Peña | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4522 |
| 00202402121 | Karen Olivia Castillo Lazaro | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4555 |
| 00020241758 | Claudia Guadalupe Quiñones Ayala | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4527 |
| 00020242017 | Daniel Piña Osuna | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4528 |
| 00020242018 | Hiram Roberto Pérez | Aduana de Nogales con sede en Sonora | 55-8889-0400 | 4529 |
| 00202203124 | Eric Omar Salinas Flores | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3510 |
| 00020260532 | Alejandro Torres Aguilera | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3500 |
| 00202203953 | Juana Maria Banda Torres | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3505 |
| 00020260640 | Jacqueline Castillo Herrera | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3506 |
| 00202203670 | Nora Laura Jimenez Escobar | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3526 |
| 00020260739 | Arturo Vela Palacios | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3527 |
| 00020260740 | Raúl López Brito | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3528 |
| 00020231922 | Alfonso Rocky Castillo Avila | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3529 |
| 00202605135 | Fernando Ramos Rentería | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3537 |
| 02022032738 | Roberto Vazquez Salazar | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3538 |
| 02022034058 | Adrian Rodrigo Mendoza Lazalde | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3539 |
| 00202321137 | Luis Ernesto Sena Hernandez | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | [{"extension": "3502", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3503", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3509", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3520", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3521", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3522", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3524", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3525", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3530", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3531", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3540", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3542", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3544", "area": "Subdirección de Informática y Contabilidad"}, {"extension": "3546", "area": "Subdirección de Informática y Contabilidad"}] |
| 00020222479 | Uriel Eduardo Uribe Calderon | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | [{"extension": "3507", "area": "Subdirección de Supervisión Aduanera"}, {"extension": "3534", "area": "I Puente – Boletas"}, {"extension": "3535", "area": "II Turismo"}, {"extension": "3536", "area": "II Puente – Boletas"}] |
| 00202203943 | Karla Beatriz Rangel Hernandez | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | [{"extension": "3508", "area": "Subdirección de Supervisión Aduanera"}, {"extension": "3533", "area": "Módulo CIITEV"}] |
| 00202203756 | Graciela Sanchez Lopez | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3532 |
| 00020220629 | Anibal Mendez Escudero | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3501 |
| 00202203890 | Jorge Armando Facundo Banda | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3513 |
| 00202203682 | Israel Leopoldo Ginera Rojas | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3504 |
| 02022032266 | Nancy Araceli Zepeda Alvizo | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3543 |
| 02022032575 | Edna Edith Arechiga Merla | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3516 |
| 00202212241 | Diana Xochitl Sanchez Vidal | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3514 |
| 00020232494 | Severo Cruz Trinidad | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3541 |
| 00020222192 | Jose Eduardo Marin Villegas | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3518 |
| 00202423138 | Eduardo Alberto Medellín Ayala/Roberto Morantes Alvarez | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3519 |
| 00020242331 | Carlos Hernández Hernández | Aduana de Nuevo Laredo con sede en Tamaulipas | 55-8889-0400 | 3523 |
| 00002025141 | José Alfredo Ángeles Jiménez | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 0262 |
| 00002024242 | Camilo Contreras Viveros | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 4204 |
| 00020222453 | José Saudiel Hernández Ortiz | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 4203 |
| 00020240613 | Iván Aponte Jaimes | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 4205 |
| 02022034091 | Ricardo Iván Pastén González | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 4207 |
| 00020252371 | Javier Martínez Said | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 4203 |
| 02022035347 | Delia Ivonne Rivera Olivares | Aduana de Ojinaga con sede en Chihuahua | 55-8889-0400 | 4200 |
| 00202203298 | Marcos Marín Vázquez | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 0263 |
| 02022034959 | Rosario Ibeth Pérez Martínez | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4101 |
| 00202203143 | Mario Alberto García Mendoza | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4113 |
| 00002024236 | Jorge Iván Sánchez Núñez del Prado | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4104 |
| 00202203702 | Alberto Cortes Peña | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4103 |
| 00202203618 | Judith Lizette Huerta Tapia | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4117 |
| 00202203642 | Emmanuel López Santos | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4130 |
| 00202203894 | Rigoberto Castañeda Griego | Aduana de Piedras Negras con sede en Coahuila de Zaragoza | 55-8889-0400 | 4109 |
| 00020251959 | Alder Rendon Fuentes | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 0264 |
| 00020240849 | Elizabeth Bacilio Vázquez | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5900 |
| 00202203995 | Sahara Yaneth García Solís | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5907 |
| 00202215224 | Erik Salvador Aguilar Prado | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5912 |
| 00202203919 | Eva María Cámara Castillo | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5903 |
| 02022035941 | Susana Utrera Aguilar | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5909 |
| 02022031595 | Elsy Georgina Flores Acosta | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5927 |
| 00202203575 | María Estela Hernández Arceo | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5905 |
| 02022035053 | Fernando Lara Escobedo | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5926 |
| 02022034369 | Carlos Ismael Duarte Garcia | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5902 |
| 02022032383 | Mayte Salazar Rojo | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5908 |
| 00020231168 | Agustin Mireles Lopez | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5928 |
| 02022031552 | Elvia Guadalupe Ríos Aranda | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5929 |
| 02022034702 | Rafael José Ascañio Flores | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5930 |
| 02022034682 | Janet Flores Perez | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5906 |
| 02022032857 | Hilda Alejandra Salmean Sanchez | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5911 |
| 00020251316 | Esther Jemina Jimenez Mariscal | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5910 |
| 02022034868 | Luis Angel Giron Patron | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5904 |
| 00202203449 | José Roberto Achaval Guzman | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5917 |
| 02022036145 | José Martín Barahona Sánchez | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033277 | Jesús Erlindo Medina Contreras | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5919 |
| 00020220870 | Daniel Antonio Suarez Santos | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5920 |
| 02022034383 | Andrea Prado Higareda | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5921 |
| 02022034708 | Delfina de Jesús Rios Benitez | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5922 |
| 00202203741 | Marco Antonio Nuñez Callejas | Aduana de Progreso con sede en Yucatán | 55-8889-0400 | 5915 |
| 02022035741 | Dilia Isela Fernández Hernández | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2306 |
| 00202203715 | José Gerardo Moreno Veloz | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2300 |
| 00020251245 | José Manuel Condado Rosales | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2327 |
| 00020222426 | Gerardo Romero Hernández | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2304 |
| 02022035191 | Ma. del Pilar Tototzintle Tecpanecatl | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2305 |
| 02022035607 | Ricardo Solís Márquez | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2308 |
| 02022031230 | Claudia Rosa Cuaxiloa Gutiérrez | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2302 |
| 02022035397 | Beatriz Gil Hernández | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2326 |
| 00020251015 | Sandra Gabriela Aguilar Harkin | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2301 |
| 00202203768 | Araceli Morales Vázquez | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2309 |
| 02022035298 | Carlos Alberto Romero Martínez | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2303 |
| 02022031544 | Grecia Robles Ibarra | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2311 |
| 02022035149 | Edwin Mario Vázquez Aguirre | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2325 |
| 00202224232 | Alejandro Morales Hernández | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2310 |
| 00020221965 | Alfredo Contreras Santiago | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2317 |
| 00020221553 | Nazareth Guadalupe Vargas Velázquez | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2313 |
| 00020251014 | Osvaldo Gómez Bravo | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2315 |
| 00202208300 | Andres Manuel Castillo Castillo | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2323 |
| 00202203900 | Karla Yesenia González Castañeda | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2314 |
| 02022033501 | Ivan Torrealba Fuentes | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2318 |
| 02022032462 | Haydee Monserad González Madrid | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2319 |
| 02022035968 | Eva Gómez Trujillo | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2320 |
| 00020252127 | Rubén Francisco Arellano Reyes | Aduana de Puebla con sede en Puebla | 55-8889-0400 | 2321 |
| 00002025231 | Luis Alberto Medina Aranda | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 0266 |
| 02022031724 | Manuel Roman Hurtado | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5400 |
| 00020252116 | Jose Eduardo Herrera Flores | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5402 |
| 00020252115 | Miguel Angel Lerma Terrazas | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5403 |
| 00020252214 | Juan Ledezma Valles | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5402 |
| 00202515170 | Ana Berenice Diaz Rosas | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5417 |
| 00202515175 | Mario Gonzalez Macias | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324194 | Ma. Del Rosario Orozco Medina | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5410 |
| 02022036130 | Guadalupe Moraima Martinez Bisuaño | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5411 |
| 00202324245 | Misael Mauricio Martinez Perez | Aduana de Puerto Palomas con sede en Chihuahua | 55-8889-0400 | 5414 |
| 00020251019 | Luis Alonso Galindo Vazquez | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 0267 |
| 00020222185 | Lisset Itzayana Olvera Vallejo | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1731 |
| 00202224207 | Delmar Nemecio Pérez Santizo | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6600 |
| 00202224228 | Gustavo Ramirez Sanchez | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6617 |
| 02022033798 | Edgar Iván Cano Osorio | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6601 |
| 00202203322 | Ruby Selene Salazar Salazar Subdirectora de Asuntos y Trámites Legales | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1734 |
| 00202203862 | María del Carmen Vázquez Camacho Jefe de departamento de PAMA´S e Incidencias | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1735 |
| 00202203892 | Julio César Lozano Valerio | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6602 |
| 00020241866 | Cesar Serrano Valencia | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1737 |
| 02022031537 | Daniel Benítez Mondragón | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6619 |
| 02022031409 | Blanca Haydeé Delgado Martínez Jefe del Departamento de Destino de bienes | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1747 |
| 02022035487 | Karina Mendiola Islas | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6603 |
| 02022035557 | Karla Elena Ramírez Soto | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6604 |
| 02022034449 | Aurelio Ramírez Martínez | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6605 |
| 00202203806 | Gladys Jiménez Martínez Jefe de departamento de Recintos Fiscalizados | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1738 |
| 02022031075 | Oscar Keeint Torres Martínez | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6607 |
| 02022036045 | Ana Laura Ortíz Nieto | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1739 |
| 02022033881 | Areli Barranco Cruz | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6606 |
| 02022033049 | Maria del Carmen Ortiz Rivera | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1732 |
| 00202203816 | Amanda Carmona Pérez Subdirectora de Informática y Contabilidad | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1727 |
| 02022036074 | Ana María Guerrero Salas | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1740 |
| 00020241730 | Kipzia Viridiana Ordaz Díaz | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1730 |
| 00020232163 | Daniela Jocelyn Chávez Reyes | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6608 |
| 00020241870 | Leslie Verónica Soto Gallegos | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6624 |
| 02022035515 | María Elida Ortega Rodríguez | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6609 |
| 02022035399 | Alfonso Francisco Ahumada Maza | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6610 |
| 00020241872 | Juan Manuel Suárez San Emeterio | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1728 |
| 00202203838 | Ángel Guadalupe Salazar Olmos Jefe de Modulos PITA | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1729 |
| 00202224260 | Javier Rosete Bello | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1733 |
| 02022035426 | Juan Miguel Martínez Berumen | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1736 |
| 00020222169 | Adonias Lopez Praxedis | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6615 |
| 00020231914 | Arturo Zamora Zamora Subdirector de Operación Aduanera | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1744 |
| 00020221943 | Jose Emmanuel Morales Cruz Jefe de Departamento de Operación Aduanera | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1748 |
| 02022032115 | Martina Hernandez Flores | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6611 |
| 02022034318 | Javier Díaz Barriga Domínguez | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6612 |
| 02022031236 | Leopoldo Márquez Cruz | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 6613 |
| 00202313180 | Sargento Isaias Almaraz García Encargado de Sala de Pasajeros | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1746 |
| 00020222472 | Ismael Lara Ramirez Jefe de Sala de Pasajeros | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1745 |
| 02022032702 | Cristina Lizette Santiago Gallegos | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1749 |
| 00020241865 | Sargento Marcos Sanchez Vasquez Encargado de Sala de Pasajeros | Aduana de Querétaro con sede en Querétaro | 55-8889-0400 | 1741 |
| 00002024074 | Francisco Javier Garcia Ortiz | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 0268 |
| 02022035065 | Areli Olavarri Cervantes | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6010 |
| 00202203538 | Miriam Ferral Hipolito | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6000 |
| 02022032987 | Virgilio Giron López | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6008 |
| 02022033745 | William Isaid Hernandez Mijangos | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6005 |
| 02022033281 | Mariana Zamora Sosa | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6003 |
| 02022031584 | Carlos Valentin Villaveitia Pérez | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6004 |
| 00202203313 | Norma Ivette Palacios Leon | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6002 |
| 00202203633 | Mariela Hernandez Rodriguez | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6017 |
| 00202203479 | Adolfo Lopez Moreno | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324380 | Cayetano Cruz Lopez | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032588 | Juan Yasushi Jimenez Ordoñez | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033084 | Jaime Escudero Santos | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6007 |
| 00020250725 | Felipe Giuseppe Zuno Aranjo | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6019 |
| 00202515166 | Anderson Moscoso Antonio | Aduana de Salina Cruz con sede en Oaxaca | 55-8889-0400 | 6009 |
| 00020250926 | Alvaro Gabriel Martinez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4011 |
| 00202215176 | Magdiel Abraham Montuy Caraveo | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4013 |
| 02022034105 | Blanca Aide Vallejo Duarte | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4013 |
| 02022032908 | Kennya Jyzel Bohon Felix | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4008 |
| 02022031082 | Jessica Lizeth Santillan Cordova | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4001 |
| 00020241015 | Christian Daniel Ortiz Rodriguez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | [{"extension": "4020", "area": "Verificadores"}, {"extension": "4018", "area": "Almacen Fiscal"}] |
| 02022034791 | Ramon Gradilla Flores | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208296 | Mateo Cesar Hernandez Diaz | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032596 | Erick Vladimir Estrada Rodriguez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035492 | Maria De Los Angeles Heraz Hernandez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035172 | Gloria Lorenza Castellanos Sanchez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4003 |
| 00020222412 | Brenda Elizabeth Ayala Nuñez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4005 |
| 02022035323 | Guillermina Rico Gonzalez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4019 |
| 02022036060 | Alma Darizza Cabrera Felix | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4015 |
| 00020231344 | Jesus Ramos Santes | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4004 |
| 02022031357 | Blanca Aide Montoya Nuñez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4016 |
| 00002023061 | America Yolanda Casas Rodriguez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4009 |
| 02022035641 | Gerenarda Johnston Barba | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4014 |
| 02022035409 | Jose Maria Conde Lopez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4021 |
| 00202324218 | Mario Alberto Hernandez Sanchez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4022 |
| 00202324301 | Eduardo Manzo Rodriguez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4023 |
| 00020221957 | Zurisadai Vazquez Pineda | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4017 |
| 00002025177 | Iris Selene Garcia Hernandez | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4017 |
| 00020220840 | Azael Maldonado Calderon | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4007 |
| 00020241616 | Felipe Neri Moreno Imperial | Aduana de San Luis Río Colorado con sede en Sonora | 55-8889-0400 | 4006 |
| 00202203266 | Carlos Antonio Ortiz Nuñez | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4420 |
| 00202203367 | Edgar Escobedo Hernandez | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4402 |
| 00202203172 | Rodrigo Galindo Garcia | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4401 |
| 00020222477 | Cristihan Alberto Seberiano Marin | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4403 |
| 00202203923 | Nancy Guadalupe Hernandez Lopez | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4416 |
| 00202203506 | Arturo Granados Camacho | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4411 |
| 00202203739 | Priscila Dominguez Hernandez | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4407 |
| 00202219228 | Juan Antonio Pastrana Sanchez | Aduana de Subteniente López con sede en Quintana Roo | 55-8889-0400 | 4412 |
| 00020250747 | Antonio Morales Hernandez | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 0272 |
| 00020251530 | Francis Guadalupe Torres Estrada | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6210 |
| 00202203918 | Raul Sergio Mendoza Macias | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6204 |
| 02022031249 | Edgar Manuel Aguilera Cisneros | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6201 |
| 00020250682 | Tomas Edgar Noriega Larios | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6200 |
| 00202203686 | Yuridia Marcela Verdin Gonzalez | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6213 |
| 02022031359 | Ana Leticia Corona Lopez | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034718 | Edgar Manuel Calderon Cruz | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6205 |
| 02022033576 | Karen Iveth Hattem Olivera | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6203 |
| 02022031533 | Graciela De Los Angeles Hernandez Orta | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6206 |
| 02022032811 | Estefanía Katsouras Rivas | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6218 |
| 02022031299 | Nancy Cervantes Mc Cumber | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6212 |
| 00020251538 | Mauricio Adrian Perez De La Rosa | Aduana de Tampico con sede en Tamaulipas | 55-8889-0400 | 6225 |
| 00020232142 | Teodoro Jaimes Martínez | Aduana de Tecate con sede en Baja California | 55-8889-0400 | 0273 |
| 00202203148 | Manuel Javier Mata Hernández | Aduana de Tecate con sede en Baja California | 55-8889-0400 | 6513 |
| 00020240627 | Jesús Saúl Peña Castro | Aduana de Tecate con sede en Baja California | 55-8889-0400 | 6502 |
| 00020240535 | José Ignacio Ibarra Utrera | Aduana de Tecate con sede en Baja California | 55-8889-0400 | 6511 |
| 00202515125 | Rubén Medina Rodríguez | Aduana de Tecate con sede en Baja California | 55-8889-0400 | 6515 |
| 00202324127 | Aylin Alcántara Ruiz | Aduana de Tecate con sede en Baja California | 55-8889-0400 | 6504 |
| 00020220371 | Alejandro Eugenio Robles Segura | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 0274 |
| 02022032290 | Joana Hipólito González | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1600 |
| 00202203244 | Guillermo Valdivia Espinola | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1618 |
| 02022031131 | Kenia Anahy Peña Celis | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1619 |
| 02022034368 | Edilberto Altamirano Pedro | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1619 |
| 00020222476 | Juan Carlos Reyes de la Rosa | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1622 |
| 02022034430 | Angelica Medel Campis | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1622 |
| 02022034790 | María Guadalupe Almanza Cordero | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1612 |
| 02022032043 | Jesús Noriega Rojas | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1642 |
| 00202203118 | Verónica Mayte Verduzco Cañedo | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1615 |
| 00202203276 | Mario Rodríguez Robles | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1602 |
| 00202203398 | Ana Beariz Barrera Torres | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1604 |
| 00202515132 | Miguel Armando Saavedra García | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251883 | Alfonso Álvarez Martínez | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251965 | Mario Alberto Arias Miranda | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002022242 | Karina Sampedro Gutiérrez | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1607 |
| 02022033022 | Juana Paola Tinoco Pérez | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020241771 | Gustavo Aarón Enriquez Villegas | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1605 |
| 02022031849 | Efren Guadalupe Zepeda Vega | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1623 |
| 02022033093 | Brianda Villegas Delgado | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1625 |
| 00002024106 | Alberto Isaac Ibarra López | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1628 |
| 00202324240 | Sldo. Diego de Jesús Izquierdo de la Rosa | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1629 |
| 00020241040 | Sldo. Francisco Andres Garcia Vega | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202416142 | Javier Hernández Hernández | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1626 |
| 02022034205 | Mindy Moreno Rueda | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1627 |
| 00202203424 | Aleyda Guadalupe Valdez Payan | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | 1632 |
| 00020221923 | Melvin Eduardo Valencia Ramírez | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202416124 | Sgto. Ericel Ramos López | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324257 | Sgto. Norma Itzel García Salazar | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202416147 | María Fernanda Acevedo Santa Cruz | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020232222 | Alfredo Garruña Dominguez | Aduana de Tijuana con sede en Baja California | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020231515 | José Flores Oliva | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 0275 |
| 02022034972 | Fanny Morales Atilano | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2000 |
| 00202203899 | Edgar García Cisneros | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2006 |
| 02022035471 | Patricia Alejandra Vicencio Clemente | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2026 |
| 02022034497 | Alejandro Martínez Sánchez | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2007 |
| 00020221933 | Felipe Santiago Valencia | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2015 |
| 02022035446 | María Teresa Mears Félix | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2029 |
| 02022035486 | Jorge Luis Hermosillo Vallejo | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2017 |
| 00202203935 | Miguel Angel Hernández Cano | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2016 |
| 02022033969 | Hector Sosa Hinojosa | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2013 |
| 00202203317 | Montserrat Romero Santillan | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2012 |
| 02022031026 | Magali Guadarrama Medina | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2014 |
| 00202203848 | Edgar Aguilar Serrano | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | [{"extension": "2001", "area": "Operación Aduanera"}, {"extension": "2003", "area": "Puerta México San Cayetano"}] |
| 02022035754 | Mayra Yadira Escobar López | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2028 |
| 02022031809 | Miguel Angel Reyes Diaz | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2002 |
| 02022035636 | Diana Martínez Patricio | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2004 |
| 02022035574 | Rosario Adriana Carmona Gasca | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2027 |
| 00020222423 | José Manuel Gómez Vazquez | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2024 |
| 00202203209 | Rodrigo Gabriel Rojas Saldivar | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 2030 |
| 00020220727 | Angel Arreola Corona | Aduana de Toluca con sede en Estado de México | 55-8889-0400 | 1107 |
| 02022033589 | Adrian Hernández Hernández | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2624 |
| 00002023128 | Juan Manuel Sandoval Caballero | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 0276 |
| 00020222124 | Cinthya Ivette López Escobar | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2621 |
| 00202203421 | Veronica Loera De La Rosa | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2614 |
| 02022035474 | Paola del Carmen Monreal Rodríguez | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2612 |
| 00202612214 | Krishna Valeria López Ortiz | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2622 |
| 00020232240 | Yessica Koral Salcedo Carbajal | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2615 |
| 00202610143 | Francisco Javier Sánchez Morales | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2605 |
| 02022035071 | Alma Patricia Velázquez Gutiérrez | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2603 |
| 00202203617 | Miguel Angel López Carmona | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2608 |
| 00202221175 | Brian Massiel Cerna Camacho | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2602 |
| 00020222425 | Alberto Mendoza Morales | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2601 |
| 02022035351 | Lilia Ivette Morales Rodríguez | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2606 |
| 00002026092 | Jesús Daniel Reyna Cisneros | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2609 |
| 00202324102 | Vicente Valdés Torres | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2613 |
| 00202203834 | Jose Antonio Aguilera Orozco | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2617 |
| 00020222430 | Salvador Cardenas Flores | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2618 |
| 00020222490 | Miguel Angel Aguilar Montes | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2610 |
| 00202203426 | Emmanuel Noriega De Los Santos | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2619 |
| 02022031646 | Rodolfo Zambrano Yocupicio | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2620 |
| 02022032297 | Paloma Del Alba Mena Gómez | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2611 |
| 02022035164 | Estefania Ramírez Silveyra | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2604 |
| 00202612257 | Paola Del Carmen Arámbula Cardoza | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2623 |
| 00002024193 | Francisco Antonio Gómez Santoyo | Aduana de Torreón con sede en Coahuila de Zaragoza | 55-8889-0400 | 2616 |
| 00020261163 | Pedro Vilchis Huerta | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036070 | Raquel Andrea Hernandez Orona | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230529 | Francisco Saavedra Castillo | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203537 | Roberto Carlos De la Cruz Zárate | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612826 | Jose Luis Don Juan Reyes | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032491 | Marco Antonio Galindo Hernández | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203638 | Alfonso Jimenez Hernandez | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033075 | Elizabeth Silva Hernandez | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020242292 | Jose Alfredo Morales Cruz | Aduana de Tuxpan con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251560 | Cristina Hernandez Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020242451 | Luis Cuauhtemoc Guerra Chacón | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 0278 |
| 02022032416 | Monica Susana Martinez Gomez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4300 |
| 00202612616 | Martha Sofia Cervantes Cisneros | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4300 |
| 00020251876 | Alberto Martínez Sánchez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4394 |
| 00202203386 | Monserrat Solís Galindo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 02022032446 | Nathalie Córcega Loza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022032181 | Héctor Miguel Pérez Lucho | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4357 |
| 00202203475 | Maribel Galicia Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 00202612173 | Karina Yasbek Gómez Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 00202612600 | Margarita Lobos Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 00202612622 | José Omar Rubio Castro | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 00202612498 | Maria Del Carmen Verdejo Díaz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 00202612160 | Ilse Renee Lugo García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 00202612314 | Daniel Riquer Paredes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4308 |
| 02022034996 | Alfonso Hernández Alemán | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022033165 | Diego Armando Saucillo Guido | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022033832 | Claudia Sánchez Campos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022032553 | Antonio Angel Espinosa Flores | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022032925 | Aracely Gómez Mayoral | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022032856 | José Jesús Sagaste Terraza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4355 |
| 02022033132 | Irving Sánchez Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 02022035387 | Montserrat Marrugat Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 02022035464 | Javier Rogelio Ramírez Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 02022035656 | María Patricia Farpón Tapia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 02022035860 | Adriana Andrade Velasco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 00202612620 | José Antonio Rella Campos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4356 |
| 00202612312 | Cristian Yamil Castillo Varela | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4357 |
| 00202612614 | Jesús Ángel Roman Oliva Torres | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4357 |
| 00020251558 | Nancy Janeth Delgado García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4357 |
| 00020251576 | Inelda Vanessa Sánchez Barrañon | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4357 |
| 02022032585 | Jonathan Eliot Lozada Duran | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4357 |
| 02022032855 | Lucia Aulis Cabrera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4329 |
| 02022033550 | Germán Jimenez Jimenez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032357 | Betzy Beatriz Esquivel Velazquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036175 | Elvia Alicia Lopez Sanchez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035526 | Jaquelin Soto Velarde | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035198 | Raquel Consuelo Picazzo Barranco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4385 |
| 00020240423 | Angela Raquel Duarte Lopez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612503 | Oscar Andrés Alba Barrientos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612604 | Diana Laura Luna Ramirez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203979 | Beatriz Rosales Atilano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034992 | Claudia Susana Amador Gonzalez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035884 | Irma Miriam Ruiseco Pereda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240424 | Jashive Prado Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251824 | Itzel Ortega De La Torre | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612297 | Alessandro Garcia Peralta | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202324355 | Anahí Delgado Salgado | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251894 | Antonio Cumplido Vela | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612482 | Camelia Diaz Gonzalez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612484 | Carlos Alberto Castillo Garcia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612485 | Carlos Ignacio Toledo Ramirez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612492 | Cristiant Eligio Sanchez Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251575 | Damaris Rodriguez Rivera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022034217 | Daniela Paredes Jimenez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251553 | Danna Fabiola Marin Jimenez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022034025 | Diana Irais Valencia Rojas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612316 | Dioselyn Ramirez Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612157 | Esbeidy Marlen Vazquez Reyes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612608 | Fabiola Garnica Lara | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612169 | Fernando Ochoa Figueroa | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202324425 | Ingrid Danae Mares Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202203853 | Irene Imelda Barojas Santiago | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251580 | Isaac Benjamin Portugal Badillo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612613 | Ismael Ramirez Arias | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612161 | Ivonne Del Carmen Martinez Lagunes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612617 | Johana Sanchez Palomino | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202321145 | Jose Angel Barreda Garcia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612619 | Jose Antonio Gallegos Padilla | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612487 | José Rosas Carcamo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022033700 | Karen Saraiih Garcia Olascuaga | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251566 | Katia Jazmin Sosa Gamboa | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022033775 | Luis Emir Rosas Gonzalez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022033712 | Maciel Ramírez Ramírez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251961 | Martín Aparicio Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202215259 | Miguel Alejandro De Jesus Perez Castañeda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202224354 | Nancy Cruz Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022032340 | Octavio Mendoza Algarin | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020252313 | Rebeca Belén Castro Olmos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612505 | Rossana Machuca Osorio | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251577 | Ruben Vargas Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022032570 | Set Corona Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020252315 | Silvia Guadalupe Danay López Peña | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202612507 | Victor Alfonso Hernandez Javier | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022033100 | Wendy Leticia Viana Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251554 | Yocelin Vianney Perez Flores | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022034171 | Belinda Veronica Marin Reyes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022033065 | Laura Patricia Rodriguez Concilco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022032356 | Gabriel Herrera García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022035616 | Maribel Guatzozon Errasquin | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022036038 | Barbara Lizett Trivera Perez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202324481 | Luis Antonio Miranda Vazquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00002024212 | Bertha Rosalba Vazquez Montemayor | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022034378 | Laura Garcia Mendoza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022032063 | Ivonne Maria Guillermo Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022035898 | Raul Martin Paredes Zepeda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202324510 | Melina Islas Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020251354 | Enrique Alejandro Aguilar Rangel | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022034203 | Misael González Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515114 | Karen Naomi Montero Cosme | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 02022031042 | Franz Alejandro Méndez Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00020221749 | Elisa Anell Rodriguez Santibañez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4307 |
| 00202609164 | Elpidio Pedro Perdomo Salas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4313 |
| 00020230497 | Herman Lara Vázquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4351 |
| 00202612502 | Octavio Abdul Agama Tlaiye | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202208229 | Sabino Alfonso Aguirre Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202215210 | José Dagoberto Apodaca Raygoza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202215206 | Miguel De Jesús Arano Meneses | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022034983 | Miguel Iván Barradas Andrade | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202324553 | Vicente Bautista Sánchez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032830 | Héctor Antonio Béjar Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 00020231740 | Alejandro Bravo Inclán | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032432 | Lourdes Camargo Patiño | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 00020231742 | Georgina Canela González | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202215257 | Amado Castro Yépez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 00020261276 | Raciel Cepeda García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020252322 | Kevin Eduardo Chacón Reyes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00002023067 | Eduardo Enrique Claro Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020231743 | Daniel Coello Alemán | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202612301 | Ana Liz Colorado Delfín | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020232176 | Rafael Covarrubias Domínguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022031877 | Mónica Elena Cruz Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020231741 | Yenci Marisol Cruz Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020240821 | Pascual Cuatzozon Mortera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032126 | Guillermo Saulo De La Rosa Quiroz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 02022033763 | Nallely Dolores Salinas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 00020261279 | Raziel Domínguez Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020261280 | Roberto Pedro Eliosa Aparicio | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020252330 | Dalia Escobar Torrez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022031559 | Martha Selene Flores Ramírez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 00202215208 | Víctor Manuel Gamboa Ramírez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202610167 | Mario Daniel García Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022033974 | Yoni García Mendoza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022034100 | Richard García Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 00020240819 | Ramiro Gómez Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020231162 | Xochitl González Amaro | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4351 |
| 02022031543 | Claudia Iveth González González | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4313 |
| 00020240217 | Isaí Gutiérrez Del Angel | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 02022033058 | Mauricio Alejandro Haro De La Fuente | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 02022034760 | Emmanuel Hernández Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4351 |
| 00202612164 | Mauricio Hernández Quiroz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020240816 | Venancio Hernández Santiago | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202215256 | Martín Jiménez Guillén | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 02022031687 | Alejandra Jiménez Heredia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020240857 | Jesús Antonio Lara Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202422103 | Julio César Lara Vidaña | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 00020240213 | José Carlos León Carrasco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020251826 | José Eduardo Lorencez Vidal | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020251520 | Luis Fernando Martínez Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202208110 | Luis Arturo Marún Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020231745 | Angel May Formoso | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020240828 | Luis Mendoza Acosta | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 00020231738 | Raúl Antonio Meneses Polanco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032730 | Emmanuel Montaño Salazar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202224331 | María De La Luz Moran Díaz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020251033 | Porfirio Muñoz Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032906 | Cinthya Ivonne Nava Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022031926 | Miguel Ángel Ordoñez García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 00202612494 | Cristina Itzel Ordoñez Gutiérrez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202203985 | Nalleli Ortiz Toto | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022031761 | Irving Gerardo Peña Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 02022032263 | Jesús Enrique Pérez Indoval | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 00202612159 | Fredy Ramírez Márquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00020232160 | Remigio Reyes Cuellar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032534 | Vicente Reyna Ramírez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4315 |
| 00020251578 | Karen Yaritza Rodríguez Enríquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022034700 | Héctor Rojas Ferman | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022031363 | Eduardo César Ruíz López | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 02022034663 | Vianey Del Carmen Sánchez Domínguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 02022033837 | Anaid Sánchez Grappin | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 00020240428 | Marco Antonio Sánchez Ramos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022034407 | Eric Sánchez Solano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022032073 | María Guadalupe Sibaja González | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 02022031729 | Ezequiel Solano Bahena | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4354 |
| 00202402111 | Daniel Torres Domínguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4353 |
| 02022035008 | Marysol Utrera Solís | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00202612624 | Ariel Vazquez Escalante | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4352 |
| 00002025155 | Alberto Portugal Talavera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251160 | Inghrid Zulemmh Ortiz Meza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033698 | Felipe Hernández Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033914 | Ricardo De Jesús Palma Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034559 | Raymundo Chávez Carmona | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033834 | Ricardo Montiel Díaz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031788 | Pablo Yavne Cordero Bendimez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033211 | Joel Bracamontes Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034477 | José Antonio Hernández Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252321 | Samuel Ojeda Becerra | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034561 | Alexia Michelle Carrillo Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032134 | Isidro García Villaraus | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203992 | Andrés Santiago Luis | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032224 | Daniel Humberto Moysen Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034400 | Rodolfo Rosas González | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033664 | Miguel Angel Barragán Estévez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031223 | Alexis Alberto Rocha Mar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031274 | Susana Solis Licona | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031286 | Daniel Mejia Lucio | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034156 | Ilse Monserrat García Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002023069 | Guillermo Jesús García Olivares | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230630 | Guillermo Quiroz Sanchez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034445 | Gonzalo Palacios Castillo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032485 | Raúl Peredo Escarcega | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031539 | Kenia Yaneth Muñoz Basulto | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034510 | Obed Oropeza Gonzalez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324531 | Rebeca Valdez Tellez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324360 | Angel Manuel Quiroz Barcelata | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034241 | Luz Del Carmen Jarquin Alvarado | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033884 | Julio César Mecalco Guerrero | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240426 | Roberto Carlos Madrigal Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033690 | Gabriela Guevara Salamanca | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020231736 | Edith Hernández Gutierrez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034898 | Xavier Olvera Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031303 | Adriana Silvia López Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324504 | Martín Hernández Trujillo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230920 | Karla Paola Ceja Moran | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515109 | Jesus Amador Lobato | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515116 | Andres García López | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251574 | Michelle Garcia Solorzano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251573 | Gabriela Valenzuela Criollo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251551 | Dana Ivone Ramos Cuevas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202422101 | Miguel Angel Lira Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251825 | Martha María Aguirre Limas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251862 | Yareli Del Carmen García Cuevas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251860 | Israel Razo Salinas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251865 | Pablo Barraza Olvera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324454 | José Ignacio Soberanes Navarrete | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033398 | Areli Azcona Amayo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252319 | Andrea Lozano Castro | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002025237 | Manuel Rodriguez Vidaña Ancona | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252316 | Wendy Paola Carrillo Olmos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230736 | Maria Isabel Hernández Del Angel | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034328 | Luz Teresa Gil Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203939 | Rogelio Delfino Melendez Duran | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612307 | Carlos Gerardo Rovirosa Arellano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612504 | Patrick Erickpher Izquierdo Cerino | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612509 | Yazmin Libreros Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612508 | Yari Yazmin Lugo Cortes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612480 | Arely Jenzuny Lugo Rodríguez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612606 | Erick Alexander Martínez Flores | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612490 | Kevin Antonio Peralta Molina | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612618 | José Alfredo Vértiz Cardenas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261275 | José Luis Santos García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612500 | Monserrat García Escamilla | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612510 | Jesús Tadeo Morales Balcázar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612162 | Juan Antonio Yair Dorantes Landa | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612303 | Angela Paola Cartela Espinoza | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612168 | Abigail Espejo Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612310 | Claudio López Vela | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240639 | Gilma Marisol Ortega Ortiz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002024152 | José Francisco Rojas Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252336 | Yuliana Guadalupe Cobaxin Gutierrez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035014 | Victor Hugo Sanchez Romero | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020231739 | Arturo Covarrubias Gonzalez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202518102 | Said Fernando García Angli | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034712 | Julio Cesar Carranza Ramirez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251338 | Armando Castillejo Ortiz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002026059 | Marcos Hernández Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032662 | Saúl López Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4374 |
| 02022034636 | Pedro José Becerra Cue | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240427 | Manuel Eduardo Reyes Zepeda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031002 | Iris Analy Vargas Zurita | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4319 |
| 02022034942 | Abigail Hernández Aguilar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033340 | Adriana Aguilar Cordova | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251864 | Derek Román León | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033521 | Aguilar Medel Casimiro | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034208 | María Natalia Cárdenas García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4309 |
| 02022033776 | José Said Monroy Centurión | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202224335 | Josué Domingo Guerrero Zertuche | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020230612 | Alejo Caporal Merlín | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240851 | Erick Pinos Campechano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251161 | Juan Carlos Rodríguez Moreno | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251556 | Alejandro Burgos Villagomez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202208212 | Felipe De Jesús Martínez Quiroz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515147 | Armando Tule Agatón | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020221715 | Angelica Jimenez Gutierrez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4392 |
| 02022031738 | Jonathan Altamirano Santiago | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034522 | Geovani Arenas Saavedra | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4321 |
| 00202523125 | Sarai Atilano Velazquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252324 | Sofía Barrientos Hipólito | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031932 | Rosa Bartolo Alcántara | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261278 | Marco Antonio Bartolo Trujillo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261282 | Rubi Merari Becerra Serrano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612501 | Nayely Bonilla Romero | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612158 | Francisco Miguel Cano Rosalino | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612166 | Ruth Cegueda Aguilar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032161 | José Gerardo Cerón Castillo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612497 | Luz María Chanlaty Ortiz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035050 | Esmeralda Chávez Aquino | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612330 | César Alberto Cortés Tamez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033092 | Anel Cruz Lara | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515107 | Edith Cruz Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031899 | Daniel Cruz Valdez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4304 |
| 00202612170 | Alejandro Amador Cuevas Juárez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031416 | Rodrigo Jesus Elorza Santiago | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4314 |
| 00202203490 | Angel Gabriel Enciso Rebolledo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252338 | Cristina Magdalena Escobar Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612479 | Alma Daniela Espinosa Barragan | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031802 | Javier Enrique Espinosa López | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612605 | Edith Flores Flores | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032173 | Cecilio Fuentes Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031784 | Sabdi Deyanira Fuentes González | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034326 | Edgar Emmanuel Galvan Castañeda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032659 | Agustin Daniel Garcia Rueda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515108 | Jennifer Maureen Gastelum Leyva | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324445 | Jorge Luis González Jacome | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612156 | Andrea Granja Gorbea | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031031 | Alfredo Froylan Guerrero Delgado | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612299 | Ana Karen Hernandez Cordoba | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612481 | Arena Magnolia Hernández Girón | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031039 | Maria Fernanda Huerta Andrade | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002023147 | Esbeidi Lara De La Hoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261277 | Ramón López León | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033494 | Benita Del Carmen López Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251565 | Jose Arturo Mares Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032042 | Carlos Dario Marin Rivera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033237 | Lorenzo Medina Arrioja | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035623 | Miguel Mendez Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4360 |
| 02022033099 | Juan Jose Montero Solis | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612304 | Anilú Morales Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4360 |
| 00020251571 | Indira Mayra Morales Pineda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034087 | Antonio Murillo Utrera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251583 | Elia Paulina Oceguera Barojas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251248 | Martin Ortiz Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612305 | Arturo Oteo Tello | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261290 | Olga Sofia Peña Haussler Herreros | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612293 | Alejandra Pérez Barrán | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032169 | Abraham Pérez Carvajal | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324483 | Luis Enrique Pillot Rueda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032064 | Susana Pilotzi Ahuatzi | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261289 | Miriam Eduwiges Ramon Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612171 | Genaro Reyes Enriquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032854 | Mariela Reyes Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4319 |
| 02022031765 | Jennysey Didier Rivera Blanco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031305 | Ulises Alberto Rodriguez Gómez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612172 | Ana Gabriela Rogel Solis | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033831 | Flavio Alonso Rosario Aguirre | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202215209 | Mayte Ruiz Altamira | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032381 | José Luis Sampieri Croda | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031406 | Jesús Sanchez Zarate | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612493 | Luis Iván Santos Fontes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612496 | Diana Adeline Suárez Alvárez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033432 | Irene Estefania Tena Collins | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032291 | Jesús Carlos Teran Sotelo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261283 | Tania Del Carmen Utrera Gamboa | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035095 | Victor Manuel Utrera Ríos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035721 | Noe Vazquez Luna | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031383 | Keila Elizza Velasques Solis | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612154 | Diana Laura Zamudio Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034393 | Francisco Antonio Del Angel Chagolla | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4310 |
| 02022034967 | Juan Jose Rodriguez Balcazar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4310 |
| 02022032869 | Montserrat Landa Huerta | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4358 |
| 02022031013 | Jair Alvarado Bapo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4392 |
| 02022032712 | Luis Alfredo Cruz Bravo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4392 |
| 00202208239 | Osvaldo Delgado Rosas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4392 |
| 00202612476 | Axel Galindo Morgado | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4358 |
| 00020261274 | Jesus Manuel Hernandez Gonzalez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4358 |
| 00202612511 | Nicole Loeza Alarcon | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4358 |
| 00020261281 | Roxana Ibeth Morales Alcantara | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4358 |
| 00020240478 | Octavio Peña Jacobo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4301 |
| 02022032670 | Jaime Xolocotzi Peña | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4303 |
| 02022033643 | Luisa Yazmin Pacheco Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4377 |
| 02022034234 | Maria De Lourdes Luna Mayen | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4302 |
| 02022031425 | Sofia Leon Garcia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251821 | Ana Bianni Obaya Burgos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251581 | Carlos Enrique Blanco Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202515165 | Jose Eduardo Figueroa Hernandez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031149 | Leonardo Agustin Flores Araujo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032645 | Bibana Mendez Duran | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252312 | Karina Ibeth Cervantes Huerta | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612615 | Jesus Daniel Díaz Silva | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324502 | Maritza Cruz Gomez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4379 |
| 02022035018 | Claudia Ines Morales Yepez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4381 |
| 02022035685 | Jorge Arturo Rodriguez Perea | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4378 |
| 02022033355 | Delhi Iriri Castillo Alonso | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4380 |
| 02022034803 | Maribel Mendez Perez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032490 | Yunuen Salinas Toledo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324378 | Carlos Pavon Gomez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031144 | Ana Paola Espinoza Orantes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031853 | Karina Fabiola Tavera Zambrano | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002025239 | Arturo Ricardo Torres Rergis | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251827 | Karlo Mendoza Cardenas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035658 | Ana Laura Marquez Vidaña | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035782 | Rafael Artigas Salazar | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612483 | Carlos Alberto Barrientos Ibarra | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612318 | Edgar Neyif Field Peralta | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035758 | Carmen De La Paz Marquez Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002023151 | Rodrigo Medina Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035949 | Gabriel Gomez Garcia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035629 | Guadalupe Torres De La Hoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035909 | Lizeth Cabrera Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035532 | Beatriz Adriana Rella Campos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022036126 | Santos Hugo Cortes Toral | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251823 | Jesús David Arévalo Utrera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035001 | Victor Daniel Arrieta Mendez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033591 | Sylvia Leticia Barajas Tapia | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203998 | José Luis Bedian González | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612607 | Fabiola De María Beltrán García | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612155 | Diego Antonio Carrillo Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032190 | José Alfredo Cazares Guridi | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251960 | Lizbeth Chávez Martínez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252335 | Ángel Gabriel Contreras Valerio | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612335 | Francisco Culebro Sánchez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612612 | Isis Valeria Durante Guerrero | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031024 | Juliana Escobar Mayen | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031763 | Juan Alberto Escobedo Centeno | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031828 | Xeki Fevirg Fuentes Montaño | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031071 | Amando Alberto Galicia Reyes | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002025194 | Mónica González Jiménez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612506 | Sebastián Hernández Castillo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612609 | Genaro Hernández Cruz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240827 | Marcelina Lázaro Calixto | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00002025236 | Carla Iveth López | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033094 | Martin Eduardo López Méndez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324368 | Beatriz Martínez Lucero | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031721 | Felipe Mateos Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612611 | Iliana Yasmín Meneses Núñez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031933 | Elisa Morales Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033577 | Roshanik Moreno Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261272 | Gaspar Neme Rivera | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033735 | Hugo Enrique Ortega Yudo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022032671 | Petra Del Carmen Pacheco Pacheco | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251861 | Iliana Del Carmen Ponce Muñoz | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612610 | Guillermo Ramos Guevara | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022031375 | Humberto Ramos Hernández | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020252317 | Ximena Guadalupe Ramírez Prieto | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261285 | María Elena Reyes Velázquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034455 | Christopher Miguel Roque Rojas | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033102 | Arely Ruiz Bravo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612491 | Lesslye Ivette Sánchez Flores | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020260529 | Jesús Alberto Sánchez Palomares | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612165 | Mónica Yamilet Santiago Pereyra | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261287 | Michael Solís Galindo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034327 | Mariana Tenorio Pérez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034544 | Ileana Mariel Tronco Avendaño | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020240636 | Marli Mayre Tuyub Abnal | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612333 | Emmanuel Vega Santos | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034314 | Nidya Velasco Guerrero | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202612328 | Edgar Valencia Frías | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324497 | Maria Fernanda Vélez Lombardo | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202324446 | Jorge Octavio Vergara Morales | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020261271 | Lucía Alejandra Villalón Guevara | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203237 | Elvira Isabel Bonifacio Vázquez | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4311 |
| 02022032484 | Daniel Soto Flores | Aduana de Veracruz con sede en Veracruz | 55-8889-0400 | 4350 |
| 00020250917 | Eduardo Olvera Alcantara | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 0231 |
| 00202208199 | Alhely Viridiana San Elías Rueda | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1525 |
| 02022033267 | Luis Fernando Jiménez Montes de Oca | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1518 |
| 02022032558 | María Guadalupe Navarro Reyes | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1503 |
| 00020242266 | Omar Pastrana Beltran | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1510 |
| 00202322133 | Juan Daniel Pacheco Contreras | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1519 |
| 00202405162 | Jose Alfredo Jimenez Oropeza | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1534 |
| 00202405157 | Jesus Garcia Solorio | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1536 |
| 00202203562 | Juan Luis Hernandez Aguilar | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1532 |
| 00002024098 | Francisco Marin Moreno | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1516 |
| 00202405118 | Miguel Angel Gardea Bustillos | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1524 |
| 00020260526 | Alejandro Perez Espinoza de los Monteros | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1533 |
| 00020231223 | Lucia Marlene Martínez Cervantes | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1511 |
| 00020230425 | Guadalupe Valverde Morales | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1505 |
| 00202405153 | Raul Hernandez Sanchez | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1523 |
| 00002025113 | Jaime Hernandez Hernandez | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1502 |
| 00020251045 | Erika Ariadna Monje Garcia | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1531 |
| 00020221929 | Oscar Vargas Aguilar | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1515 |
| 00202203284 | Erick Dominguez Martinez | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1528 |
| 00020251018 | Karina Cruz Maldonado | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1507 |
| 00202215165 | Manuel Agustín Cab Chan | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1517 |
| 00202208193 | Alejandro Leonel Lopez Sanchez | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1535 |
| 00020251021 | Julie Geraldine Diaz Garcia | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1501 |
| 00020251020 | Erick Miranda Fernandez | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1520 |
| 00002024099 | Daniel Hernández Meneses | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1506 |
| 00202405102 | Cristian Iván Damián Aguilar | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1512 |
| 00020240556 | Luis Enrique Alvarez Cruz | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1521 |
| 00202511101 | Fernando Yair Carrasco Torres | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1508 |
| 00002024096 | Rigoberto Perea Garcia | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1527 |
| 00020251028 | Jose Portillo German | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1500 |
| 00202405112 | Melani Aide Escobedo Guerrero | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1522 |
| 00202423143 | Miriam Concepción Riveroll Díaz | Aduana del Aeropuerto Internacional Felipe Angeles con sede en Estado de México | 55-8889-0400 | 1514 |
| 00002025025 | Sacramento Morales Vazquez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 0230 |
| 02022034282 | Mabel Briones Ramos | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2129 |
| 02022035114 | Gema Malagon Garcia | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2130 |
| 02022032479 | Kenia Elizabeth Resendiz Romero | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2130 |
| 00202208314 | Brenda Corona Rea | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2160 |
| 02022035671 | Maria Del Rosio Herrera Rendon | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2152 |
| 00202203914 | Jose Luis Vega Velazquez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2101 |
| 00202203621 | Victor Manuel Pérez Pedraza | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2102 |
| 02022032611 | Jorge Rios Amaya | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2150 |
| 00202203708 | Israel Flores Claudio | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2151 |
| 02022032608 | Maria Gladis Garcia Miranda | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2147 |
| 02022031253 | Grecia Buendia Vargas | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2103 |
| 02022034851 | Adilene Zarate Reyes | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2104 |
| 02022032932 | Manuel Jimenez Torres | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2100 |
| 02022036177 | Francisco Manuel Hernandez Gonzalez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2163 |
| 00202203394 | Gabriel Reyes Perez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022035644 | Sandra Ruiz Fernandez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2134 |
| 00202203611 | Andrea Pamela Chavez Ramos | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2133 |
| 00202203381 | Monica Deyanira Medina Alvarez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2132 |
| 00202203383 | Nalleli Sanchez Vargas | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2135 |
| 00020221748 | Sara Sanchez Olivares | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2112 |
| 00202203509 | Montserrat Martinez Pavon | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2115 |
| 00002024126 | Yormelith Cruz Suarez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2114 |
| 00202203724 | Iliana Mendez Mazo | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2116 |
| 00202203751 | Gabriela Guadalquivier Suárez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2120 |
| 00202609152 | Pita | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2119 |
| 00202402114 | Jorge Luis Perez Durante | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2123 |
| 00202203503 | Cynthia Maria Lopez Peralta | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2122 |
| 00202203671 | Alma Karina Gomez Yañez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2121 |
| 00202203413 | Rosalia Madrid Hernandez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2124 |
| 00202203165 | Marisol Mijas Puig | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022033329 | Heber Maldonado Sanchez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2127 |
| 00202203196 | Elizabeth Barrón Urbina | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2143 |
| 02022035504 | Ilhui Bravo Aguilar | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203662 | Yaquelin Mirian Ramirez Rama | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2144 |
| 02022032429 | Luis Alberto Castillo Gomez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2145 |
| 00020251534 | Omar Humberto Cruz Marin | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2137 |
| 00202612178 | Paola Yanira Piña Hernández | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2139 |
| 00202203513 | Ricardo Aviña Gamboa | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202203581 | Maria Elizabeth Carmona Mendez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251337 | Luis Ivan Balcazar Moran | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202215203 | Jorge Ivan Colin González | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2140 |
| 02022035004 | Raquel Andrade Salinas / Viridiana Saucedo Ruiz | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2142 |
| 00202203614 | Miguel Angel Perez Capistran | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020251359 | Abraham Gomez Santes | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 02022034607 | Jose Oscar Perez Contreras | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2107 |
| 02022031394 | Cesar Alvarez Guzman | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00202511104 | Gustavo Arroniz Guzman | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2158 |
| 00202203673 | Jaime Adolfo Orozco Quintero | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2110 |
| 02022034265 | Itzel Montes De Oca Torres | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020220634 | Nav. Sia. Icomp. Pedro Manuel Fernández Jaillet | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2136 |
| 02022032957 | Alberto Palma Gomez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | _(vacio, no se inserta)_ |
| 00020241612 | Ariel Martinez Hernandez | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2146 |
| 00002022181 | Miriam Gomez Castelan / Ing. Luis Evangelista | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2131 |
| 00202515133 | Jesica Amairany Rincon Cruz / Ixchel Soledad Aguilar Montaño | Aduana del Aeropuerto Internacional de la Ciudad de México con sede en la Ciudad de México | 55-8889-0400 | 2161 |