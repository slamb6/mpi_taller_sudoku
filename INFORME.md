# Informe de resultados

Completa este informe después de implementar las tres tareas MPI. Ejecuta las comparaciones con el mismo archivo `seeds.txt`, en el mismo equipo y con el contenedor del taller.

## Entorno

- Equipo: Samuel Lambertino
- Versión del contenedor: 2
- Cantidad de repeticiones por medición: 3
- Valor común de `N` elegido: 4

## Comparación final con el mismo `N`

Repite tres veces cada ejecución y registra la mediana. Mantén fijo el `N` elegido en todas las filas MPI. Incluye `--allow-run-as-root --use-hwthread-cpus --oversubscribe` en `mpiexec`, igual que en la calibración, para permitir valores de `N` mayores que los slots detectados.

| Implementación | Caso | Procesos | Mediana del tiempo total (s) | Aceleración frente a secuencial |
| --- | --- | ---: | ---: | ---: |
| Secuencial | Todos los IDs | 1 | 362.696 | 1,00 |
| MPI por tableros | Todos los IDs | N | 85.569 | 4.238 |
| MPI por ramas | Todos los IDs, uno después de otro | N | 105.01 | 3.453 |
| MPI híbrido | Todos los IDs | N | 163.089 | 2.223 |

Calcula la aceleración como `tiempo secuencial / tiempo MPI`. Mide el tiempo MPI desde el inicio del reparto hasta recibir todos los resultados necesarios.

## Conclusiones

- ¿Qué estrategia obtuvo el menor tiempo para los 30 tableros? ¿Cuánto mejoró respecto a la versión secuencial?

Por tableros. Fue 4 veces más rápido que la versión secuencial.

- ¿Cómo afectaron la comunicación y las diferencias de duración entre tableros?

La comunicación incurre en un costo adicional, en todos los casos sigue siendo más eficiente que hacerlo
secuencialmente. La duración de los tableros dependiendo de su dificultad para ser resueltos por el backtracking
puede resultar en desbalanceo de carga y en nodos inactivos.

- ¿Cómo se comparó repartir tableros con resolverlos en orden y repartir las ramas de cada uno?

Repartir los tableros tiene menor complejidad de implementación que el reparto de ramas así como también un
menor sobrecosto de comunicación; sin embargo, ante dificultades desbalanceadas puede aprovechar mejor los recursos.
