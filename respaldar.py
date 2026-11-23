"""Copia SQLite consistente. Acepta origen y carpeta destino opcionales."""
import argparse
from datetime import datetime
from pathlib import Path
import sqlite3
from core import DATA
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--origen',type=Path,default=DATA/'yapu.sqlite')
p.add_argument('--destino',type=Path,default=Path(__file__).resolve().parent/'respaldos')
args=p.parse_args()
origin=args.origen.resolve(strict=True)
args.destino.mkdir(parents=True,exist_ok=True)
dest=args.destino/('yapu-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite')
with sqlite3.connect(origin.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(dest) as target:
    src.backup(target)
    if target.execute('pragma integrity_check').fetchone()[0]!='ok':raise RuntimeError('Copia inválida')
print('Respaldo verificado:',dest)
