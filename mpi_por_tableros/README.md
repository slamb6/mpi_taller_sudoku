# Tarea 1: repartir tableros

Todos los ids se reparten entre la cantidad de nodos que haya. Si la división no es exacta, se reparten los IDs restantes entre los primeros
procesos. El programa no toma parámetros.

## Ejecución 

```powershell
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_por_tableros/solver.py
```

