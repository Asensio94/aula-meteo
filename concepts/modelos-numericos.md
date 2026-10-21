---
slug: modelos-numericos
title: Qué es un modelo meteorológico
short: Un programa que aplica las leyes de la física a una malla de puntos para calcular el tiempo de las próximas horas y días.
order: 16
level: basico
related: [carta-de-analisis, precipitacion, inestabilidad-y-cape, satelite, prediccion-por-conjuntos]
layers: [msl, z500, t850, jet250, precip, cape]
---

## Qué es

Un **modelo meteorológico** es un programa que calcula cómo evolucionará la atmósfera aplicando las leyes de la física: el movimiento del aire, la termodinámica y la conservación de la masa y del agua. Divide el planeta en una **malla** de puntos, a muchos niveles de altura, y avanza el cálculo en pequeños pasos de tiempo.

Los mapas de esta aplicación proceden del modelo **IFS** del **Centro Europeo de Previsiones Meteorológicas a Plazo Medio** (ECMWF, por sus siglas en inglés), uno de los más precisos del mundo. Su versión de alta resolución calcula con una malla de unos **9 km**, pero los datos abiertos que usa esta aplicación se publican a 0,25° (unos **28 km**): sirven para ver borrascas, frentes y el chorro, no tormentas concretas. El modelo se lanza cuatro veces al día, a las **00, 06, 12 y 18 UTC**; cada lanzamiento se llama **pasada** (*run*), y las de 00 y 12 UTC llegan más lejos en el tiempo.

## Cómo se ve en el mapa

Todas las capas salvo *Satélite* y *Carta de análisis* salen del modelo: *Presión en superficie*, *Geopotencial 500 hPa*, *Temperatura 850 hPa*, *Viento 250 hPa (chorro)*, *Precipitación 12 h* y *CAPE*. Fíjate en dos datos:

- **La pasada**: cuándo empezó el cálculo (por ejemplo, las 00 UTC de hoy).
- **El alcance**: cuántas horas después de la pasada es válido el mapa (+0 h, +12 h, +24 h…).

El mapa a +0 h es el **análisis**: la mejor estimación del estado actual, construida combinando millones de observaciones (satélites, estaciones, globos sonda, aviones) con una predicción previa muy corta. Todo lo demás es **predicción**.

## Qué tiempo trae

Un modelo no es un oráculo. La atmósfera es un sistema caótico: pequeños errores en el estado inicial crecen con el tiempo. Como regla general:

- a 2–3 días, la situación general suele ser bastante fiable;
- entre 4 y 7 días, la tendencia es útil, pero los detalles cambian;
- más allá de una semana, solo es orientativo.

Por eso el ECMWF también calcula un **conjunto** (*ensemble*): unas 50 pasadas con condiciones iniciales ligeramente distintas. Si todas se parecen, hay confianza; si divergen, hay incertidumbre.

Además, una malla de 9 km no captura una tormenta concreta ni el viento de un valle estrecho: la [[precipitacion|lluvia]] de tormenta y la [[inestabilidad-y-cape|inestabilidad]] se representan solo de forma aproximada.

## Un truco para reconocerlo

Traduce siempre la hora. Los modelos usan **UTC**; en la Península y Baleares la hora oficial es UTC+1 en invierno y UTC+2 en verano, y en Canarias, una hora menos (UTC+0 y UTC+1). Así, un mapa válido a las 12 UTC corresponde a las 13:00 peninsulares en invierno y a las 14:00 en verano. Y compara el análisis del modelo con la [[carta-de-analisis]] del DWD: si coinciden, vas por buen camino.
