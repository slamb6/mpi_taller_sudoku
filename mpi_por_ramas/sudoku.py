"""Resuelve un tablero de Sudoku por backtracking."""

import time


def puede_colocar(tablero, fila, columna, valor):
    """Indica si valor puede ir en la casilla sin romper las reglas."""
    if any(tablero[fila][c] == valor for c in range(9)):
        return False
    if any(tablero[f][columna] == valor for f in range(9)):
        return False
    inicio_fila, inicio_columna = (fila // 3) * 3, (columna // 3) * 3
    for f in range(inicio_fila, inicio_fila + 3):
        for c in range(inicio_columna, inicio_columna + 3):
            if tablero[f][c] == valor:
                return False
    return True


def resolver(tablero):
    """Resuelve el tablero in situ. Devuelve False si no tiene solución."""
    for fila in range(9):
        for columna in range(9):
            if tablero[fila][columna] != 0:
                continue
            for valor in range(1, 10):
                if puede_colocar(tablero, fila, columna, valor):
                    tablero[fila][columna] = valor
                    if resolver(tablero):
                        return True
                    tablero[fila][columna] = 0  # retroceso: probar otro valor
            return False
    return True  # no quedan casillas vacías


def resolver_con_tiempo(tablero):
    """Resuelve un tablero in situ y devuelve (resuelto, segundos)."""
    inicio = time.perf_counter()
    resuelto = resolver(tablero)
    segundos = time.perf_counter() - inicio
    return resuelto, segundos
