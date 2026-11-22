"""Comprobaciones de estructura: NO son corrección académica de SQL."""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('numero', [402, 403, 404, 405, 406])
def test_plantilla_de_actividad(numero):
    carpeta = ROOT / f'actividad{numero}'
    assert carpeta.is_dir(), f'Falta {carpeta.name}/'
    assert (carpeta / 'README.md').is_file(), f'Falta README en {carpeta.name}'
    archivos = list(carpeta.glob(f'{numero}_*.sql'))
    assert archivos, f'Falta entrega SQL para actividad {numero}'
    for archivo in archivos:
        assert re.fullmatch(rf'{numero}_[A-Za-zÀ-ÿ0-9_-]+\.sql', archivo.name), f'Nombre inválido: {archivo.name}'
        assert archivo.read_text(encoding='utf-8').strip(), f'Archivo vacío: {archivo.name}'
