# Licencia de los datos

Los archivos de `output/` —GeoJSON, TopoJSON y previews— se distribuyen bajo
**Creative Commons Atribución 4.0 Internacional (CC BY 4.0)**.

- Resumen legible: <https://creativecommons.org/licenses/by/4.0/deed.es>
- Texto legal completo: <https://creativecommons.org/licenses/by/4.0/legalcode.es>

## Qué puedes hacer

**Compartir**: copiar y redistribuir el material en cualquier medio o formato.
**Adaptar**: remezclar, transformar y construir a partir del material.

Para cualquier propósito, **incluido el uso comercial**. No hay que pedir
permiso, ni avisar, ni pagar.

## Qué se te pide a cambio

Solo una cosa: **dar crédito**. Basta con una línea, en el pie del mapa, en la
ficha del tablero o en el README de tu proyecto:

```
Cartografía: Marco Geoestadístico Nacional 2025, DANE
(Fuente: Departamento Administrativo Nacional de Estadística: www.dane.gov.co).
Simplificación: <URL de este repositorio>, CC BY 4.0.
```

Si el espacio no da para tanto, la parte que no puede faltar es la primera: la
cita al DANE. Es la condición que pone la fuente original.

## Por qué dos licencias

El repositorio distribuye dos cosas distintas y cada una tiene su licencia:

| Qué | Dónde | Licencia |
|---|---|---|
| Código del pipeline | `mapas.py`, `scripts/`, `docs/` | MIT ([LICENSE](LICENSE)) |
| Datos derivados | `output/` | CC BY 4.0 (este archivo) |

CC BY 4.0 es el estándar para datos geográficos abiertos y es la licencia que
Colombia adoptó para su información geográfica pública (IGAC, Resolución 616 de
2020). Creative Commons desaconseja expresamente usar sus licencias para
software, de ahí la separación.

## Relación con la fuente original

Estos archivos son **obra derivada** del Marco Geoestadístico Nacional 2025 del
DANE: las geometrías originales fueron simplificadas, los campos renombrados y,
en la variante `inset`, el archipiélago de San Andrés fue desplazado y ampliado.

Los shapefiles originales del DANE **no se redistribuyen** en este repositorio.
Hay que descargarlos del [geoportal del DANE](https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/?cod=111).

Los [términos de uso del DANE](https://www.dane.gov.co/index.php/servicios-al-ciudadano/tramites/transparencia-y-acceso-a-la-informacion-publica/terminos-y-condiciones)
autorizan «el uso, aprovechamiento, transformación y análisis» de su
información a condición de citar la fuente. Este proyecto es exactamente eso:
una transformación, publicada con la cita.

**El DANE no produce, avala ni respalda estos archivos derivados.** Cualquier
error de simplificación es de este repositorio, no de la fuente. Para uso
oficial o catastral, acude siempre al shapefile del DANE.

## Sin garantía

El material se ofrece tal cual, sin garantías de ningún tipo. La variante
`inset` contiene, por diseño, coordenadas que no corresponden a la posición
geográfica real del archipiélago de San Andrés: no la uses para cálculos
espaciales. Para eso está la variante `real`.
