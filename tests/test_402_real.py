"""Validador 402 basado en el esquema del SQL de referencia del profesor.
Solo para repositorio de prueba controlado; no publicar la referencia en entregas reales.
"""
import json
import os
from pathlib import Path
import mysql.connector

BASE = Path(__file__).resolve().parent
EXPECTED = json.loads((BASE / "esquema_402.json").read_text(encoding="utf-8"))
OUT = Path("resultados/402.json")
WEIGHTS = {"Base de datos y codificación": 1.0, "Tablas": 2.0,
           "Columnas y tipos": 2.0, "Claves primarias": 1.5,
           "Claves ajenas": 2.0, "Restricciones y valores por defecto": 1.5}


def test_evaluacion_402():
    errores = []
    puntos = {k: 0.0 for k in WEIGHTS}
    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "root"),
            connection_timeout=10,
        )
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT DEFAULT_CHARACTER_SET_NAME AS charset FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='jardineria'")
        db = cursor.fetchone()
        if not db:
            errores.append("No existe la base de datos jardineria.")
        elif db['charset'] != 'utf8mb4':
            errores.append("La base de datos jardineria no utiliza utf8mb4.")
        else:
            puntos['Base de datos y codificación'] = 1.0

        cursor.execute("""SELECT TABLE_NAME AS nombre FROM information_schema.TABLES
            WHERE TABLE_SCHEMA='jardineria' AND TABLE_TYPE='BASE TABLE'""")
        actual_tables = {r['nombre'] for r in cursor.fetchall()}
        expected_tables = set(EXPECTED)
        for table in sorted(expected_tables - actual_tables):
            errores.append(f"Falta la tabla {table}.")
        puntos['Tablas'] = 2 * len(expected_tables & actual_tables) / len(expected_tables)

        cursor.execute("""SELECT TABLE_NAME AS tabla, COLUMN_NAME AS columna, COLUMN_TYPE AS tipo,
            IS_NULLABLE AS nullable, COLUMN_DEFAULT AS defecto
            FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='jardineria'""")
        actual_cols = {(r['tabla'], r['columna']): r for r in cursor.fetchall()}
        cursor.execute("""SELECT TABLE_NAME AS tabla, COLUMN_NAME AS columna, ORDINAL_POSITION AS pos
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA='jardineria' AND CONSTRAINT_NAME='PRIMARY'
            ORDER BY TABLE_NAME, ORDINAL_POSITION""")
        pk_map = {}
        for r in cursor.fetchall():
            pk_map.setdefault(r['tabla'], []).append(r['columna'])
        cursor.execute("""SELECT TABLE_NAME AS tabla, COLUMN_NAME AS columna,
            REFERENCED_TABLE_NAME AS destino, REFERENCED_COLUMN_NAME AS columna_destino
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA='jardineria' AND REFERENCED_TABLE_NAME IS NOT NULL""")
        fk_map = {}
        for r in cursor.fetchall():
            fk_map.setdefault(r['tabla'], set()).add((r['columna'], r['destino'], r['columna_destino']))

        col_ok = restr_ok = pk_ok = fk_ok = 0
        col_total = restr_total = pk_total = fk_total = 0
        for table, definition in EXPECTED.items():
            pk_total += 1
            if pk_map.get(table, []) == definition['pk']:
                pk_ok += 1
            else:
                errores.append(f"Clave primaria incorrecta en {table}: esperada {definition['pk']}.")
            for col, expected in definition['columns'].items():
                col_total += 1
                restr_total += 1
                found = actual_cols.get((table, col))
                if found is None:
                    errores.append(f"Falta la columna {table}.{col}.")
                    continue
                # MySQL puede mostrar int(11), smallint(6), decimal(15,2), etc.
                observed = found['tipo'].lower()
                observed = __import__('re').sub(r'^(int|smallint)\(\d+\)', r'\1', observed)
                if observed == expected['type']:
                    col_ok += 1
                else:
                    errores.append(f"Tipo incorrecto en {table}.{col}: {observed}, esperado {expected['type']}.")
                null_ok = (found['nullable'] == 'YES') == expected['nullable']
                # Para la referencia, todos los defaults son NULL o no especificados.
                default_ok = found['defecto'] is None
                if null_ok and default_ok:
                    restr_ok += 1
                else:
                    errores.append(f"Restricción NULL/DEFAULT incorrecta en {table}.{col}.")
            expected_fk = {tuple(x) for x in definition['fk']}
            actual_fk = fk_map.get(table, set())
            fk_total += len(expected_fk)
            fk_ok += len(expected_fk & actual_fk)
            for fk in sorted(expected_fk - actual_fk):
                errores.append(f"Falta la FK {table}.{fk[0]} -> {fk[1]}.{fk[2]}.")
        puntos['Columnas y tipos'] = 2 * col_ok / col_total
        puntos['Restricciones y valores por defecto'] = 1.5 * restr_ok / restr_total
        puntos['Claves primarias'] = 1.5 * pk_ok / pk_total
        puntos['Claves ajenas'] = 2 * fk_ok / fk_total
    except mysql.connector.Error as exc:
        errores.append(f"No se pudo consultar MySQL: {exc}")
    finally:
        if connection is not None:
            connection.close()

    nota = round(sum(puntos.values()), 2)
    result = {'actividad': 402, 'nota': nota, 'maximo': 10,
              'apartados': {k: {'obtenido': round(puntos[k], 2), 'maximo': v}
                            for k, v in WEIGHTS.items()}, 'errores': errores}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\n=== EVALUACIÓN 402 ===')
    for k, v in result['apartados'].items():
        print(f"{k}: {v['obtenido']:.2f}/{v['maximo']:.2f}")
    print(f"NOTA FINAL: {nota:.2f}/10")
    for error in errores[:50]:
        print(' -', error)
    assert nota == 10.0, f"Entrega incompleta o incorrecta: {nota:.2f}/10. Consulta el resumen de Actions."
