"""Lee seeds, ejecuta el resolvedor serial y muestra los tiempos."""
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

import argparse
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
    parser = argparse.ArgumentParser(description="Resuelve Sudokus por backtracking (versión serial).")
    parser.add_argument("--archivo", type=Path, default=Path(__file__).with_name("seeds.txt"),
                        help="archivo de seeds (por defecto: seeds.txt junto a este programa)")
    seleccion = parser.add_mutually_exclusive_group()
    seleccion.add_argument("--id", "--seed", dest="id", help="resolver solo la seed con este ID")
    seleccion.add_argument("--all", action="store_true", help="resolver todos los seeds")
    args = parser.parse_args()

    try:
        seeds = leer_seeds(args.archivo)
        if not seeds:
            parser.error(f"no se encontraron seeds en {args.archivo}")
        if args.id:
            if args.id not in seeds:
                parser.error(f"ID '{args.id}' no existe. Disponibles: {', '.join(seeds)}")
            seleccionados = [(args.id, seeds[args.id])]
        else:
            # Sin --id se resuelven todos, igual que con --all.
            seleccionados = list(seeds.items())

        tiempo_total = 0.0
        for nombre, original in seleccionados:
            tablero = [fila[:] for fila in original]
            resuelto, segundos = resolver_con_tiempo(tablero)
            tiempo_total += segundos
            print(f"\nID: {nombre}")
            print("Resuelto" if resuelto else "Sin solución")
            etiqueta = "Tiempo" if args.id else "Tiempo parcial"
            print(f"{etiqueta}: {segundos:.6f} segundos", flush=True)
        if not args.id:
            print(f"\nTiempo total: {tiempo_total:.6f} segundos")
    except OSError as error:
        parser.error(f"no se pudo leer {args.archivo}: {error}")


if __name__ == "__main__":
    main()
