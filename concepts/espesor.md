---
slug: espesor
title: Espesor de la capa 1000–500 hPa
short: La distancia en altura entre los niveles de 1000 y 500 hPa, un termómetro de la media de los primeros 5 km de atmósfera.
order: 23
level: intermedio
related: [geopotencial-500, masas-de-aire, presion-atmosferica, vaguada-y-dorsal]
layers: [z500, msl, t850]
---

## Qué es

El **espesor** es la diferencia de altura entre dos niveles de presión. El más usado es el de **1000 a 500 hPa**: la distancia vertical entre el nivel donde la presión es de 1000 hPa (casi a ras de suelo) y el de 500 hPa (hacia los 5,5 km).

El aire caliente es menos denso y ocupa más volumen, así que una capa caliente es **más gruesa** que una fría con el mismo peso de aire. Por eso el espesor es, en realidad, una medida de la **temperatura media** de toda esa capa, no de un solo nivel. Se mide en decámetros (dam):

- unos **528 dam** o menos: aire frío; en zonas bajas, la precipitación puede ser de nieve;
- unos **546 a 552 dam**: aire templado, valores corrientes en la Península en primavera u otoño;
- **576 dam** o más: aire muy cálido, típico de las olas de calor o del aire sahariano.

El umbral de nieve depende de la altitud, de la humedad y de la intensidad de la precipitación, así que tómalo como orientación.

## Cómo se ve en el mapa

Esta aplicación no dibuja el espesor, pero puedes calcularlo a ojo con dos capas:

- La [[geopotencial-500|altura de 500 hPa]] (capa *Geopotencial 500 hPa*), en dam.
- La altura de 1000 hPa, que se deduce de la [[presion-atmosferica|presión en superficie]]: cerca del suelo, 1 hPa equivale a unos 8 m. Con 1020 hPa, el nivel de 1000 hPa está a unos 160 m (16 dam); con 990 hPa, está unos 80 m *bajo* el nivel del mar (−8 dam).

Espesor ≈ altura de 500 hPa − altura de 1000 hPa. Con 564 dam en 500 hPa y 1020 hPa en superficie: 564 − 16 = 548 dam.

## Qué tiempo trae

El espesor ayuda a separar las dos razones por las que la altura de 500 hPa puede ser baja: porque hay aire frío o porque hay una borrasca en superficie. También sirve para seguir las [[masas-de-aire|masas de aire]]: las líneas de igual espesor se aprietan donde chocan aire frío y cálido, que es donde se forman los frentes y las borrascas.

## Un truco para reconocerlo

La capa *Temperatura 850 hPa* cuenta casi la misma historia y es más fácil de leer: donde baja el espesor, bajan también las temperaturas a 850 hPa. Usa el espesor como comprobación cuando dudes si un frío previsto llegará de verdad a toda la columna de aire.
