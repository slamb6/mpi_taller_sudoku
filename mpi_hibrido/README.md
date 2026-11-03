# Tarea 3: combinar tableros y ramas

Como el n encontrado por `detectar_procesos_mpi.py` fue 4, se tienen 2 grupos de tamaño 2, de manera
general, se escogen raíz de (n) grupos. El tiempo total para resolver todos los tableros en las 3 ejecuciones
fue de 163.089, 161.926 y 167.021 segundos.

```powershell
docker run --rm -v "${PWD}:/app" augustosalazar/slim-mpi:2 mpiexec --allow-run-as-root --use-hwthread-cpus --oversubscribe -n 4 python /app/mpi_hibrido/main.py --all
```

