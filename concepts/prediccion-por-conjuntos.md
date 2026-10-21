---
slug: prediccion-por-conjuntos
title: Predicción por conjuntos
short: Lanzar el modelo decenas de veces con condiciones de partida un poco distintas para saber cuánto fiarse de la previsión.
order: 26
level: intermedio
related: [modelos-numericos, borrasca, dana, bloqueo]
layers: [msl, z500]
---

## Qué es

La atmósfera es un **sistema caótico**: diferencias minúsculas en el estado de partida crecen con los días hasta cambiar por completo el resultado. Lo descubrió Edward Lorenz en los años sesenta. Como nunca conocemos el estado de la atmósfera con exactitud, un único [[modelos-numericos|modelo numérico]] puede dar una previsión muy precisa… y equivocada.

La solución es la **predicción por conjuntos** (*ensemble*): lanzar el modelo muchas veces, cada una con un estado inicial ligeramente distinto (y a veces con pequeñas variaciones en el propio modelo). Cada versión es un **miembro**. El conjunto del Centro Europeo (ENS) tiene **51 miembros**: uno de control y 50 perturbados.

- Si los miembros **coinciden**, la previsión es fiable.
- Si **divergen**, hay mucha incertidumbre, y la dispersión dice cuáles son los escenarios posibles y cómo de probables son.

## Cómo se ve en el mapa

Esta aplicación muestra **una sola pasada** del modelo IFS, así que no ves la incertidumbre. Ten en cuenta que:

- a +24 h la previsión suele ser muy fiable;
- a +72 h los grandes sistemas (borrascas, anticiclones) suelen estar bien, pero su posición exacta puede variar cientos de kilómetros;
- las [[dana|DANA]] y los [[bloqueo|bloqueos]] son de lo más difícil de prever: pequeños cambios mueven mucho su trayectoria.

En las webs del ECMWF y de AEMET verás los productos de los conjuntos: **diagramas de espaguetis** (la misma isolínea dibujada por cada miembro), **penachos** (*plumes*, la temperatura prevista por cada miembro en una ciudad) y **mapas de probabilidad** (por ejemplo, probabilidad de más de 20 mm de lluvia).

## Qué tiempo trae

No trae ningún tiempo: es una forma de medir la confianza. Pero cambia cómo se comunica la previsión: «probabilidad de lluvia del 70 %» sale de contar en cuántos miembros llueve.

## Un truco para reconocerlo

Compara la página de hoy con la de ayer. Si el modelo dibuja hoy la misma borrasca, en el mismo sitio y para el mismo día que ayer, la previsión es estable y probablemente fiable. Si cambia mucho de una pasada a otra, es señal de que los miembros del conjunto andan dispersos.
