"""Registro piloto de venta. Importes enteros en centavos y confirmación bilateral."""
from decimal import Decimal,InvalidOperation
from core import clean,choice,CROPS,rows

def install(c):
    c.executescript("""CREATE TABLE IF NOT EXISTS offers(
    id INTEGER PRIMARY KEY,seller TEXT REFERENCES users(id) ON DELETE CASCADE,
    buyer TEXT REFERENCES users(id) ON DELETE SET NULL,crop TEXT,description TEXT,zone TEXT,
    cents INTEGER,seller_ok INTEGER DEFAULT 0,buyer_ok INTEGER DEFAULT 0,status TEXT DEFAULT 'Abierta',fee INTEGER DEFAULT 0);
    CREATE TRIGGER IF NOT EXISTS release_reserved BEFORE DELETE ON users BEGIN
    UPDATE offers SET buyer=NULL,buyer_ok=0,seller_ok=0,status='Abierta' WHERE buyer=OLD.id AND status='Reservada'; END;""")

def listing(c,uid):
    return rows(c,"""SELECT id,crop,description,zone,cents,status,seller_ok,buyer_ok,fee,
    seller=? AS mine,buyer IS ? AS buying FROM offers WHERE status='Abierta' OR seller=? OR buyer=?
    ORDER BY id DESC LIMIT 300""",(uid,uid,uid,uid))

def mutate(c,p,d):
    if not p['consent']: raise ValueError('Primero guarda tu parcela y confirma el consentimiento.')
    action=d.get('action'); uid=p['id']
    if action=='offer':
        try: val=Decimal(str(d.get('price')))
        except InvalidOperation: raise ValueError('Precio inválido')
        if not val.is_finite() or not Decimal('0.01')<=val<=10000000 or val*100!=int(val*100): raise ValueError('Ingresa un precio positivo de hasta dos decimales.')
        c.execute('INSERT INTO offers(seller,crop,description,zone,cents) VALUES(?,?,?,?,?)',(uid,choice(d.get('crop'),CROPS),clean(d.get('description'),160),p['zone'],int(val*100)));return
    o=c.execute('SELECT * FROM offers WHERE id=?',(d.get('id'),)).fetchone()
    if not o: raise ValueError('Oferta desconocida')
    seller=o['seller']==uid; buyer=o['buyer']==uid
    if action=='reserve' and not seller and o['status']=='Abierta':
        c.execute("UPDATE offers SET buyer=?,status='Reservada' WHERE id=?",(uid,o['id']))
    elif action=='withdraw' and seller and o['status']=='Abierta':
        c.execute("UPDATE offers SET status='Retirada' WHERE id=?",(o['id'],))
    elif action=='cancel' and (buyer or seller) and o['status']=='Reservada':
        c.execute("UPDATE offers SET buyer=NULL,seller_ok=0,buyer_ok=0,status='Abierta' WHERE id=?",(o['id'],))
    elif action=='confirm' and (buyer or seller) and o['status']=='Reservada':
        key='seller_ok' if seller else 'buyer_ok'
        c.execute('UPDATE offers SET '+key+'=1 WHERE id=?',(o['id'],))
        c.execute("UPDATE offers SET status='Confirmada',fee=(cents*2+50)/100 WHERE id=? AND seller_ok=1 AND buyer_ok=1",(o['id'],))
    else: raise ValueError('La oferta cambió o la acción no está disponible.')
