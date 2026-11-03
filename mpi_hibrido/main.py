"""MPI híbrido: distribución de tableros entre grupos y ramas dentro de cada grupo."""

import argparse
import sys
import time
from collections import deque
from pathlib import Path

from mpi4py import MPI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sudoku import puede_colocar, resolver_con_tiempo


TAG_TASK = 1
TAG_STOP = 2
TAG_FINISH = 3
TAG_RESULT = 4
TAG_SOLUTION = 5
TAG_STOPPED = 6
TAG_FINISHED = 7


def leer_seeds(ruta):
    """Lee líneas con formato id|81 caracteres (0 o . son vacíos)."""
    seeds = {}

    for texto in ruta.read_text(encoding="utf-8").splitlines():
        texto = texto.strip()

        if not texto or texto.startswith("#"):
            continue

        identificador, contenido = texto.split("|", 1)
        celdas = [int(c) for c in contenido.strip().replace(".", "0")]
        seeds[identificador.strip()] = [
            celdas[i:i + 9] for i in range(0, 81, 9)
        ]

    return seeds


def dividir_tableros(tableros, grupos):
    """Reparte los IDs de forma equilibrada entre los líderes de grupo."""
    return [tableros[i::grupos] for i in range(grupos)]


def numero_grupos(procesos):
    """Elige aproximadamente sqrt(N), dejando al menos dos procesos por grupo."""
    if procesos < 4:
        return 1

    return max(1, min(procesos // 2, round(procesos ** 0.5)))


def primera_vacia(tablero):
    for fila in range(9):
        for columna in range(9):
            if tablero[fila][columna] == 0:
                return fila, columna

    return None


def generar_ramas(tablero, minimo):
    """Expande las primeras casillas vacías hasta crear suficientes ramas."""
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
    """Resuelve una rama con backtracking y permite cancelación."""

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
    """Bucle persistente de trabajo de cada proceso no coordinador."""
    while True:
        estado = MPI.Status()
        tarea = comm.recv(source=0, tag=MPI.ANY_TAG, status=estado)
        etiqueta = estado.Get_tag()

        if etiqueta == TAG_FINISH:
            comm.send(None, dest=0, tag=TAG_FINISHED)
            return

        if etiqueta == TAG_STOP:
            comm.send(None, dest=0, tag=TAG_STOPPED)
            continue

        resultado = resolver_rama(tarea, comm)

        if resultado is None:
            comm.send(None, dest=0, tag=TAG_STOPPED)
        elif resultado:
            comm.send(tarea, dest=0, tag=TAG_SOLUTION)
        else:
            comm.send(None, dest=0, tag=TAG_RESULT)


def resolver_paralelo(tablero, comm):
    """El líder reparte ramas entre los trabajadores de su grupo."""
    trabajadores = comm.Get_size() - 1

    if trabajadores == 0:
        copia = [fila[:] for fila in tablero]
        resuelto, _ = resolver_con_tiempo(copia)
        return resuelto, copia if resuelto else None

    ramas = deque(generar_ramas(tablero, trabajadores * 2))
    activos = set()
    pendientes_stop = set()
    solucion = None

    for proceso in range(1, trabajadores + 1):
        if ramas:
            comm.send(ramas.popleft(), dest=proceso, tag=TAG_TASK)
            activos.add(proceso)
        else:
            comm.send(None, dest=proceso, tag=TAG_STOP)
            pendientes_stop.add(proceso)

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
            if origen not in activos:
                continue

            if ramas:
                comm.send(ramas.popleft(), dest=origen, tag=TAG_TASK)
            else:
                activos.remove(origen)
                comm.send(None, dest=origen, tag=TAG_STOP)
                pendientes_stop.add(origen)

        elif etiqueta == TAG_SOLUTION:
            if solucion is None:
                solucion = resultado

                # El trabajador que encontró la solución también espera
                # una nueva orden, por lo que debe recibir STOP.
                for proceso in range(1, trabajadores + 1):
                    if proceso not in pendientes_stop:
                        comm.send(None, dest=proceso, tag=TAG_STOP)
                        pendientes_stop.add(proceso)

                activos.clear()

        elif etiqueta == TAG_STOPPED:
            pendientes_stop.discard(origen)
            activos.discard(origen)

    return solucion is not None, solucion


def finalizar_trabajadores(comm):
    for proceso in range(1, comm.Get_size()):
        comm.send(None, dest=proceso, tag=TAG_FINISH)

    for _ in range(1, comm.Get_size()):
        comm.recv(source=MPI.ANY_SOURCE, tag=TAG_FINISHED)


def main():
    parser = argparse.ArgumentParser(
        description="MPI híbrido: reparto de tableros y ramas."
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
    parser.add_argument(
        "--grupos",
        type=int,
        help="número de grupos (por defecto, aproximadamente sqrt(N))"
    )
    args = parser.parse_args()

    mundo = MPI.COMM_WORLD
    rank = mundo.Get_rank()
    size = mundo.Get_size()

    if rank == 0:
        try:
            seeds = leer_seeds(args.archivo)

            if not seeds:
                raise ValueError(f"no se encontraron seeds en {args.archivo}")

            if args.id:
                if args.id not in seeds:
                    raise ValueError(
                        f"ID '{args.id}' no existe. "
                        f"Disponibles: {', '.join(seeds)}"
                    )

                seleccionados = [(args.id, seeds[args.id])]
            else:
                seleccionados = list(seeds.items())

            error = None

        except (OSError, ValueError) as exc:
            seleccionados = None
            error = str(exc)
    else:
        seleccionados = None
        error = None

    error = mundo.bcast(error, root=0)

    if error:
        if rank == 0:
            print(f"Error: {error}", file=sys.stderr, flush=True)
        return

    grupos = args.grupos if args.grupos is not None else numero_grupos(size)
    max_grupos = 1 if size < 2 else size // 2

    if grupos < 1 or grupos > max_grupos:
        if rank == 0:
            print(
                f"Error: --grupos debe estar entre 1 y {max_grupos} "
                f"para N={size}.",
                file=sys.stderr,
                flush=True
            )
        return

    # Los procesos se distribuyen equilibradamente entre los grupos.
    grupo_id = rank % grupos
    grupo = mundo.Split(color=grupo_id, key=rank)
    rank_grupo = grupo.Get_rank()

    # Solo los líderes forman este comunicador.
    lideres = mundo.Split(
        color=0 if rank_grupo == 0 else MPI.UNDEFINED,
        key=rank
    )

    # Inicia la medición antes de distribuir los tableros entre líderes.
    mundo.Barrier()
    inicio_total = MPI.Wtime() if rank == 0 else None

    if rank_grupo == 0:
        if rank == 0:
            distribucion = dividir_tableros(seleccionados, grupos)
        else:
            distribucion = None

        tableros_grupo = lideres.scatter(distribucion, root=0)
    else:
        tableros_grupo = None

    if rank_grupo == 0:
        print(
            f"Grupo {grupo_id} (líder global {rank}) recibe "
            f"{len(tableros_grupo)} tablero(s).",
            flush=True
        )

        for nombre, original in tableros_grupo:
            tablero = [fila[:] for fila in original]
            inicio = MPI.Wtime()

            resuelto, solucion = resolver_paralelo(tablero, grupo)

            segundos = MPI.Wtime() - inicio

            print(f"\n[{rank = }] ID: {nombre}", flush=True)
            print(
                f"[{rank = }] Resuelto" if resuelto
                else f"[{rank = }] Sin solución",
                flush=True
            )

            print(
                f"[{rank = }] Tiempo: {segundos:.6f} segundos",
                flush=True
            )

        # Solo el líder envía la orden de cierre y recoge las confirmaciones.
        finalizar_trabajadores(grupo)
    else:
        # Los demás procesos permanecen disponibles para recibir ramas.
        trabajador(grupo)

    # Todos los grupos deben terminar antes de medir el tiempo total.
    mundo.Barrier()

    if rank == 0 and not args.id:
        tiempo_total = MPI.Wtime() - inicio_total
        print(f"\nTiempo total: {tiempo_total:.6f} segundos", flush=True)

    if lideres != MPI.COMM_NULL:
        lideres.Free()

    grupo.Free()


if __name__ == "__main__":
    main()
