"""Lee seeds, ejecuta el resolvedor serial y muestra los tiempos."""
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

import argparse
import time
from pathlib import Path

from sudoku import resolver_con_tiempo


def leer_seeds(ruta):
    """Lee líneas con formato id|81 caracteres (0 o . son vacíos)."""
    seeds = {}
    for texto in ruta.read_text(encoding="utf-8").splitlines():
        texto = texto.strip()
        if not texto or texto.startswith("#"):
            continue
        identificador, contenido = texto.split("|", 1)
        celdas = [int(c) for c in contenido.strip().replace(".", "0")]
        seeds[identificador.strip()] = [celdas[i:i + 9] for i in range(0, 81, 9)]
    return seeds


def main():
    if rank == 0:
        parser = argparse.ArgumentParser(description="Resuelve Sudokus por backtracking (paralelización por tableros).")
        parser.add_argument("--archivo", type=Path, default=Path(__file__).with_name("seeds.txt"),
                            help="archivo de seeds (por defecto: seeds.txt)")
        args = parser.parse_args()

        try:
            seeds = leer_seeds(args.archivo)
            if not seeds:
                parser.error(f"no se encontraron seeds en {args.archivo}")
            seleccionados = list(seeds.items())

            m = len(seleccionados) // size
            remaining = len(seleccionados) % size

            inicio = time.perf_counter() # Desde inicio de reparto
            tableros_por_nodo = [seleccionados[(i-1)*m:i*m] for i in range(1,size+1)]
            for index, board in enumerate(seleccionados[-remaining:]):
                tableros_por_nodo[index].append(board)
            data = tableros_por_nodo
            # data = [10,20,30,40]
        except OSError as error:
            parser.error(f"no se pudo leer {args.archivo}: {error}")

    else:
        data = None
    data = comm.scatter(data, root=0)
    print(f"{rank} received: {len(data)}")
    # tiempo_total = 0.0
    for nombre, original in data:
        tablero = [fila[:] for fila in original]
        resuelto, segundos = resolver_con_tiempo(tablero)
        # tiempo_total += segundos
        print(f"\n[{rank = }] ID: {nombre}")
        print(f"[{rank = }] Resuelto" if resuelto else "Sin solución")
        comm.send(nombre, dest=0)
        # etiqueta = "Tiempo" if args.id else "Tiempo parcial"
        # print(f"{etiqueta}: {segundos:.6f} segundos", flush=True)
    # if not args.id:
        # print(f"\nTiempo total: {tiempo_total:.6f} segundos")
    if rank == 0:
        confirmed = []
        for i in range(len(seleccionados)):
            confirmed.append(comm.recv(source=MPI.ANY_SOURCE))
        assert(len(confirmed) == len(seleccionados))
        print("Todos los tableros resueltos")
        print(f"Tiempo total: {time.perf_counter() - inicio:.6f} segundos")

if __name__ == "__main__":
    main()
