import argparse
import sys
from collections import deque
from pathlib import Path

from mpi4py import MPI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baseline_secuencial import leer_seeds
from sudoku import puede_colocar, resolver_con_tiempo


TAG_TASK = 1
TAG_STOP = 2
TAG_FINISH = 3
TAG_RESULT = 4
TAG_SOLUTION = 5
TAG_STOPPED = 6
TAG_FINISHED = 7


def primera_vacia(tablero):
    for fila in range(9):
        for columna in range(9):
            if tablero[fila][columna] == 0:
                return fila, columna
    return None


def generar_ramas(tablero, minimo):
    """Divide el árbol hasta obtener al menos 'minimo' estados independientes."""
    ramas = [[fila[:] for fila in tablero]]

    while ramas and len(ramas) < minimo:
        nuevas = []

        for estado in ramas:
            vacia = primera_vacia(estado)

            if vacia is None:
                return [estado]

            fila, columna = vacia

            for valor in range(1, 10):
                if puede_colocar(estado, fila, columna, valor):
                    nueva = [r[:] for r in estado]
                    nueva[fila][columna] = valor
                    nuevas.append(nueva)

        ramas = nuevas

    return ramas


def resolver_rama(tablero, comm):
    """Backtracking cancelable. Devuelve True, False o None si fue cancelado."""

    def cancelado():
        if comm.Iprobe(source=0, tag=TAG_STOP):
            comm.recv(source=0, tag=TAG_STOP)
            return True
        return False

    def buscar():
        if cancelado():
            return None

        vacia = primera_vacia(tablero)
        if vacia is None:
            return True

        fila, columna = vacia

        for valor in range(1, 10):
            if puede_colocar(tablero, fila, columna, valor):
                tablero[fila][columna] = valor
                resultado = buscar()

                if resultado is True:
                    return True

                tablero[fila][columna] = 0

                if resultado is None:
                    return None

        return False

    return buscar()


def trabajador(comm):
    """Recibe ramas, las resuelve y espera nuevas instrucciones."""
    while True:
        estado = MPI.Status()
        tarea = comm.recv(source=0, tag=MPI.ANY_TAG, status=estado)

        if estado.Get_tag() == TAG_FINISH:
            comm.send(None, dest=0, tag=TAG_FINISHED)
            return

        if estado.Get_tag() == TAG_STOP:
            comm.send(None, dest=0, tag=TAG_STOPPED)
            continue

        resultado = resolver_rama(tarea, comm)

        if resultado is None:
            comm.send(None, dest=0, tag=TAG_STOPPED)
        elif resultado:
            comm.send(tarea, dest=0, tag=TAG_SOLUTION)
        else:
            comm.send(None, dest=0, tag=TAG_RESULT)


def resolver_paralelo(tablero, comm, procesos):
    """Coordina las ramas de un tablero y devuelve si tiene solución."""
    if procesos == 1:
        copia = [fila[:] for fila in tablero]
        resuelto, _ = resolver_con_tiempo(copia)
        return resuelto

    ramas = deque(generar_ramas(tablero, max(procesos * 2, procesos)))
    activos = set()
    pendientes_stop = set()

    for proceso in range(1, procesos + 1):
        if ramas:
            comm.send(ramas.popleft(), dest=proceso, tag=TAG_TASK)
            activos.add(proceso)
        else:
            comm.send(None, dest=proceso, tag=TAG_STOP)
            pendientes_stop.add(proceso)

    solucion = None

    while activos or pendientes_stop:
        estado = MPI.Status()
        resultado = comm.recv(
            source=MPI.ANY_SOURCE,
            tag=MPI.ANY_TAG,
            status=estado
        )
        origen = estado.Get_source()
        etiqueta = estado.Get_tag()

        if etiqueta == TAG_RESULT:
            if solucion is None and origen in activos:
                if ramas:
                    comm.send(ramas.popleft(), dest=origen, tag=TAG_TASK)
                else:
                    activos.remove(origen)
                    comm.send(None, dest=origen, tag=TAG_STOP)
                    pendientes_stop.add(origen)

        elif etiqueta == TAG_SOLUTION:
            if solucion is None:
                solucion = resultado
                for proceso in activos:
                    comm.send(None, dest=proceso, tag=TAG_STOP)
                    pendientes_stop.add(proceso)
                activos.clear()

        elif etiqueta == TAG_STOPPED:
            pendientes_stop.discard(origen)
            activos.discard(origen)

    return solucion is not None


def main():
    parser = argparse.ArgumentParser(
        description="Resuelve Sudokus con MPI repartiendo ramas de cada tablero."
    )
    parser.add_argument(
        "--archivo",
        type=Path,
        default=ROOT / "seeds.txt",
        help="archivo de seeds (por defecto: seeds.txt en la raíz)"
    )
    seleccion = parser.add_mutually_exclusive_group()
    seleccion.add_argument("--id", "--seed", dest="id")
    seleccion.add_argument("--all", action="store_true")
    args = parser.parse_args()

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank != 0:
        trabajador(comm)
        return

    try:
        seeds = leer_seeds(args.archivo)
        if not seeds:
            raise ValueError(f"no se encontraron seeds en {args.archivo}")

        if args.id:
            if args.id not in seeds:
                raise ValueError(
                    f"ID '{args.id}' no existe. Disponibles: {', '.join(seeds)}"
                )
            seleccionados = [(args.id, seeds[args.id])]
        else:
            seleccionados = list(seeds.items())

    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr, flush=True)
        comm.Abort(1)
        return

    tiempo_total = 0.0

    for nombre, original in seleccionados:
        tablero = [fila[:] for fila in original]
        inicio = MPI.Wtime()

        resuelto = resolver_paralelo(tablero, comm, size - 1)

        segundos = MPI.Wtime() - inicio
        tiempo_total += segundos

        print(f"\nID: {nombre}")
        print("Resuelto" if resuelto else "Sin solución")
        etiqueta = "Tiempo" if args.id else "Tiempo parcial"
        print(f"{etiqueta}: {segundos:.6f} segundos", flush=True)

    if not args.id:
        print(f"\nTiempo total: {tiempo_total:.6f} segundos", flush=True)

    for proceso in range(1, size):
        comm.send(None, dest=proceso, tag=TAG_FINISH)

    for _ in range(1, size):
        comm.recv(source=MPI.ANY_SOURCE, tag=TAG_FINISHED)


if __name__ == "__main__":
    main()
