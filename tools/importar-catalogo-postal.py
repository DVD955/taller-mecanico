"""Descarga el TXT nacional oficial de SEPOMEX e importa el catálogo en MySQL."""
import csv
import hashlib
import io
import json
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import insert, select, func
from app.database import engine
from app.models import PostalSettlement
from app.migrations import initialize_database, normalize_postal_catalog

URL = 'https://www.correosdemexico.gob.mx/sslservicios/consultacp/CodigoPostal_Exportar.aspx'


class Fields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        item = dict(attrs)
        if tag == 'input' and item.get('type') == 'hidden':
            self.values[item['name']] = item.get('value', '')


def main():
    initialize_database()
    with engine.connect() as connection:
        if connection.scalar(select(func.count()).select_from(PostalSettlement)):
            print('El catálogo ya está cargado. Se conserva la versión existente.')
            loaded = True
        else:
            loaded = False
    if loaded:
        normalize_postal_catalog()
        return
    if len(sys.argv) > 1:
        data = Path(sys.argv[1]).read_bytes()
    else:
        opener = build_opener(HTTPCookieProcessor())
        parser = Fields()
        parser.feed(opener.open(URL, timeout=30).read().decode('utf-8', errors='replace'))
        parser.values.update(cboEdo='00', rblTipo='txt', **{'btnDescarga.x': '20', 'btnDescarga.y': '12'})
        with opener.open(URL, urlencode(parser.values).encode(), timeout=60) as response:
            data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        name = next(name for name in archive.namelist() if name.lower().endswith('.txt'))
        raw = archive.read(name)
    try:
        content = raw.decode('utf-8')
    except UnicodeDecodeError:
        content = raw.decode('cp1252')
    content = content[content.index('d_codigo|'):]
    reader = csv.DictReader(io.StringIO(content), delimiter='|')
    rows, seen = [], set()
    for item in reader:
        key = (item['d_codigo'], item['d_estado'], item['D_mnpio'] if 'D_mnpio' in item else item['d_mnpio'], item['d_asenta'])
        if key not in seen:
            seen.add(key)
            rows.append(dict(zip(('postal_code', 'state', 'municipality', 'neighborhood'), key)))
    if len(rows) < 100_000:
        raise RuntimeError('El archivo no contiene el catálogo nacional completo; no se importó.')
    with engine.begin() as connection:
        for start in range(0, len(rows), 2000):
            connection.execute(insert(PostalSettlement), rows[start:start + 2000])
    normalize_postal_catalog()
    metadata = dict(source=URL, source_sha256=hashlib.sha256(raw).hexdigest(), settlements=len(rows),
                    coverage='Catálogo nacional SEPOMEX', header=content.splitlines()[0])
    (ROOT / 'database' / 'postal_catalog-source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Catálogo nacional importado: {len(rows)} asentamientos. SHA256: {metadata["source_sha256"]}')


if __name__ == '__main__':
    main()
