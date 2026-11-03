# Tarea 2: repartir ramas de cada tablero

El proceso 0 recorre recursivamente hasta generar 2 ramas para cada trabajador

Implementa una versión MPI en esta carpeta. Con `--all`, el proceso coordinador lee los 30 IDs de `seeds.txt` en orden. Para cada tablero, crea tareas a partir de opciones válidas de las primeras casillas vacías y reparte esas ramas entre procesos. Espera a que termine ese tablero antes de comenzar el siguiente: **los tableros se procesan secuencialmente y las ramas de cada tablero en paralelo**.

Cada proceso explora su rama con backtracking y comunica el resultado. Cuando se encuentra una solución, los demás deben dejar de buscar ese tablero. Muestra el estado y el tiempo parcial de cada ID al terminarlo, además del tiempo total de los 30. Conserva la opción `--id` para resolver un solo tablero.

Añade aquí los comandos para ejecutar `--id` y `--all` con el contenedor. Incluye `--allow-run-as-root --use-hwthread-cpus --oversubscribe` en `mpiexec`, como en la calibración. Compara el tiempo total de `--all` con la versión secuencial y registra los resultados en `../INFORME.md`.

```powershell
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_ramas/main.py --all
```
