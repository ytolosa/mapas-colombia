# Diccionario de datos

## Campos

### Capa municipal (`col_municipios_*`)

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `divipola_mun` | texto, 5 caracteres | `"05001"` | Código DIVIPOLA del municipio, con ceros a la izquierda. |
| `divipola_mun_n` | entero | `5001` | El mismo código casteado a entero. |
| `divipola_dep` | texto, 2 caracteres | `"05"` | Código DIVIPOLA del departamento, con cero a la izquierda. |
| `divipola_dep_n` | entero | `5` | El mismo código casteado a entero. |
| `mpio_nombre` | texto | `"MEDELLÍN"` | Nombre del municipio según el MGN. |
| `dpto_nombre` | texto | `"ANTIOQUIA"` | Nombre del departamento según el MGN. |
| `area_km2` | decimal | `374.7415` | Área oficial del MGN (`mpio_narea`), **no** recalculada tras simplificar. |

### Capa departamental (`col_departamentos_*`)

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `divipola_dep` | texto, 2 caracteres | `"05"` | Código DIVIPOLA del departamento. |
| `divipola_dep_n` | entero | `5` | El mismo código casteado a entero. |
| `dpto_nombre` | texto | `"ANTIOQUIA"` | Nombre del departamento según el MGN. |
| `area_km2` | decimal | `62788.7331` | Área oficial del MGN (`dpto_narea`). |

La capa departamental **no** lleva `divipola_mun` ni `divipola_mun_n`: no
existe un municipio por departamento, y un campo lleno de nulos rompe los joins
de varias herramientas de BI. Si necesitas fronteras departamentales derivadas
de la capa municipal, agrégalas por `divipola_dep`.

## Por qué existen las dos formas del código

`divipola_mun` / `divipola_dep` son texto y conservan el cero a la izquierda:
Antioquia es `"05"`, no `"5"`. Es la forma correcta para unir con datos del
DANE, del SISPRO o de Datos Abiertos, que publican el código como texto.

`divipola_mun_n` / `divipola_dep_n` son enteros. Existen porque muchas
herramientas (Excel, Power BI al importar CSV, pandas con `read_csv` sin
`dtype`) convierten silenciosamente el código a número y pierden el cero. Si tu
tabla de datos ya viene con el código como entero, une por el campo `_n` en vez
de andar reconstruyendo el cero con `zfill`.

Regla práctica: usa la versión de texto siempre que puedas; usa `_n` cuando el
otro lado del join ya perdió el cero.

## Verificación de integridad

`scripts/prepare.py` falla si alguna de estas condiciones no se cumple:

- `divipola_dep` tiene exactamente 2 dígitos y `divipola_mun` exactamente 5.
- El entero y el texto de cada código coinciden.
- Los primeros 2 caracteres de `divipola_mun` son iguales a `divipola_dep`.
- No hay códigos duplicados.
- Todas las geometrías de entrada son válidas.

## Cobertura

- 33 departamentos (32 más Bogotá D.C.).
- 1.122 municipios y áreas no municipalizadas.

## Sistema de referencia

EPSG:4326 (WGS 84), longitud/latitud en grados decimales, heredado del MGN.

En la variante `inset` las geometrías del departamento `88` **no** están en su
posición real: fueron desplazadas y ampliadas. No uses esa variante para
cálculos de distancia, área o vecindad. Para eso está la variante `real`.
