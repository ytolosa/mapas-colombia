# Guía de niveles

Tres niveles del mismo mapa, cada uno con el nombre de **la escala a la que se
va a ver**. Esa es casi siempre la única pregunta que importa: no cuánto detalle
tiene el archivo por dentro, sino cuánto detalle se alcanza a ver en pantalla.

Todas las cifras salen de los archivos de `output/` y de comparar los PNG de
`output/previews/`.

## Respuesta rápida

| Lo que estás haciendo | Nivel | Formato |
|---|---|---|
| Coropleta de Colombia en Power BI (Shape map) | `nacional` | TopoJSON |
| Coropleta de Colombia en Tableau / Looker | `nacional` | GeoJSON |
| Mapa web de Colombia, móvil o miniatura | `nacional` | TopoJSON |
| Mapa de un departamento en pantalla | `departamental` | TopoJSON o GeoJSON |
| Tablero donde el usuario puede hacer zoom a un departamento | `departamental` | TopoJSON |
| Mapa de un municipio, o zoom urbano | `municipal` | GeoJSON |
| Impresión de gran formato, póster, trabajo vectorial | `municipal` | GeoJSON / SVG |
| Cálculo de áreas, distancias, vecindad, cruce con otras capas | `municipal`, variante `real` | GeoJSON |

Ante la duda a escala nacional, empieza por `nacional`: pesa 2,5 MB en
municipios y se ve igual que los 31 MB del nivel `municipal`.

## Los tres niveles

Sobre un maestro municipal de **6.212.672 vértices**:

| Nivel | Vértices | % | Municipios GeoJSON | Municipios TopoJSON | Departamentos GeoJSON | Departamentos TopoJSON |
|---|---|---|---|---|---|---|
| `municipal` | 1.563.799 | 25,2 % | 31,34 MB | 7,53 MB | 5,65 MB | 1,57 MB |
| `departamental` | 504.624 | 8,1 % | 9,29 MB | 2,43 MB | 1,65 MB | 0,47 MB |
| `nacional` | 131.364 | 2,1 % | 2,50 MB | 0,84 MB | 0,40 MB | 0,12 MB |

### `municipal` — 25 %

Detalle indistinguible del shapefile original a cualquier escala de
visualización, incluido el zoom a un municipio. Es el nivel de referencia del
proyecto: si necesitas más fidelidad que esta, lo que necesitas es el shapefile
del DANE, no otro nivel.

Es también el nivel para trabajo vectorial de verdad: el SVG nacional de
municipios pesa 39 MB y el de Boyacá 2 MB, tamaños que Illustrator o Inkscape
manejan. Los SVG no se versionan por su peso; se generan con
`python3 mapas.py render`.

No lo uses en una aplicación web ni en una herramienta de BI: 31 MB de GeoJSON
municipal son mucho más de lo que hace falta para lo que se va a ver.

### `departamental` — 8 %

El nivel para mapas de un departamento en pantalla. En el preview de Boyacá los
bordes se ven naturales, sin rastro de poligonización, y en el nacional es
idéntico a `municipal`.

Úsalo en tableros de escritorio donde el usuario puede acercarse a un
departamento, y como opción intermedia cuando no sabes a qué escala se va a ver
el mapa.

### `nacional` — 2 %

El nivel más útil del conjunto para visualización. A escala nacional es
indistinguible del original, con 2,5 MB de GeoJSON municipal (0,84 MB en
TopoJSON): cabe sin problema en un tablero o en una página web.

Úsalo para coropletas nacionales en Power BI, Tableau, Looker o Plotly, y para
mapas web. Aguanta razonablemente un zoom a un departamento; lo que ya se nota
es el zoom a un municipio, donde los bordes se ven angulosos.

## Por qué tres y no cinco

Comparando los previews de las tres escalas:

- **A escala nacional** los tres niveles se ven iguales. Ni la costa pacífica ni
  la frontera amazónica delatan la simplificación de `nacional`.
- **A escala departamental** (Boyacá) `municipal` y `departamental` son
  indistinguibles entre sí; `nacional` empieza a mostrar bordes rectos, poco,
  pero se nota si se comparan lado a lado.
- **A escala municipal** (Bogotá D.C.) los tres se distinguen: `municipal`
  conserva el microdentado del borde oriental, `departamental` lo suaviza —hay
  que comparar lado a lado para verlo— y `nacional` lo reduce a segmentos
  rectos evidentes. En vértices del polígono de Bogotá: 3.890, 1.177 y 294.

Una versión anterior tenía cinco niveles. Los dos que se quitaron eran los que
no se veían: uno sin simplificar (135 MB de GeoJSON municipal, idéntico en
pantalla a `municipal` a cualquier escala) y uno al 0,5 %, que solo aportaba
sobre `nacional` en tamaño de archivo y a costa de degradar el mapa
departamental. Cualquier nivel intermedio adicional produciría archivos
distintos en bytes e iguales en pantalla.

## GeoJSON o TopoJSON

Usa **TopoJSON** siempre que la herramienta lo acepte. Pesa entre 3 y 4 veces
menos porque guarda una sola vez cada frontera compartida entre municipios
vecinos, y además garantiza que esas fronteras encajen sin huecos.

Lo aceptan D3, Plotly, Highcharts, Observable y la mayoría de librerías web, y
también **Power BI**: el visual Shape map carga TopoJSON desde un archivo o
desde una URL.

Usa **GeoJSON** cuando la herramienta no entienda TopoJSON: Tableau, QGIS,
ArcGIS, geopandas, PostGIS, Leaflet sin plugin.

Un límite de Power BI que conviene tener presente: el visual Shape map dibuja
**como máximo 1.500 regiones**. Los 1.122 municipios caben, pero sin mucho
margen.

### Orientación de los anillos

En los dos formatos los anillos exteriores van en **sentido horario**, y los
huecos en sentido antihorario. Es la convención de TopoJSON, y la que esperan
los motores que tratan las coordenadas como puntos sobre la esfera: d3-geo y
todo lo construido encima, que es buena parte del ecosistema de visualización.

RFC 7946 pide la orientación contraria para GeoJSON, así que estos archivos no
la siguen en ese punto. Es deliberado: con la orientación de la especificación,
un motor esférico lee cada polígono como su complemento —el resto del planeta—
y lo dibuja como un rectángulo relleno que tapa el mapa entero. Boyacá, en vez
de 23.208 km², pasa a medir 510 millones.

No afecta a las herramientas que trabajan en el plano —QGIS, GDAL, PostGIS,
geopandas, Leaflet, Mapbox—, que ignoran la orientación. Si tu herramienta sí
aplica RFC 7946 al pie de la letra (por ejemplo el tipo `geography` de SQL
Server), invierte los anillos al cargar.

## Qué garantiza la simplificación

Todos los niveles se producen con mapshaper preservando topología, con
`keep-shapes` activo. En la práctica:

- Ningún municipio ni departamento desaparece: los 1.122 municipios y los 33
  departamentos están en los tres niveles.
- No aparecen huecos ni solapes entre municipios vecinos, porque la frontera
  compartida se simplifica una sola vez.
- Los niveles están anidados: los vértices de `nacional` son un subconjunto de
  los de `departamental`, y estos de los de `municipal`. Cambiar de nivel no
  desplaza fronteras, solo quita detalle.

Lo que sí se pierde son islotes muy pequeños. De los 6 polígonos del
archipiélago en el shapefile original quedan:

| Variante | `municipal` | `departamental` | `nacional` |
|---|---|---|---|
| `real` | 5 | 3 | 3 |
| `inset` | 6 | 6 | 5 |

La variante `inset` conserva más islotes porque están ampliados x15, así que
tardan más en caer por debajo del umbral de simplificación. En ambas variantes y
en los tres niveles sobreviven las dos islas principales, San Andrés y
Providencia.

## Un aviso sobre las áreas

El campo `area_km2` es el área oficial del MGN y **no** se recalcula al
simplificar. Es intencional: quieres que el área de Bogotá sea la misma sin
importar qué nivel cargaste. Si necesitas el área del polígono simplificado,
calcúlala tú, y hazlo sobre la variante `real` y en una proyección de áreas
iguales.
