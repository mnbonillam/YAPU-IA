PRAGMA foreign_keys=ON;
CREATE TABLE users(id TEXT PRIMARY KEY, name TEXT, zone TEXT, crop TEXT, stage TEXT, mode TEXT, scene TEXT, plan TEXT DEFAULT 'Gratuito', phone TEXT UNIQUE, consent INTEGER DEFAULT 0, joined TEXT, last_inbound INTEGER, lat REAL, lon REAL, owner TEXT REFERENCES users(id) ON DELETE CASCADE);

CREATE TABLE chats(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,q TEXT,a TEXT,stamp TEXT);

CREATE TABLE alerts(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,ctx TEXT,kind TEXT,day TEXT,evidence TEXT,action TEXT,source TEXT,stamp TEXT,occurred INTEGER,useful INTEGER,sent INTEGER DEFAULT 0, ack TEXT, active INTEGER DEFAULT 0, UNIQUE(user,ctx,kind,day));

CREATE TABLE knowledge(id INTEGER PRIMARY KEY,title TEXT,crop TEXT,tags TEXT,body TEXT,source TEXT);

CREATE TABLE cases(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,question TEXT,stamp TEXT,status TEXT DEFAULT 'Pendiente');

CREATE TABLE inbox(id TEXT PRIMARY KEY,phone TEXT,reply TEXT,done INTEGER DEFAULT 0);

CREATE TABLE offers(
    id INTEGER PRIMARY KEY,seller TEXT REFERENCES users(id) ON DELETE CASCADE,
    buyer TEXT REFERENCES users(id) ON DELETE SET NULL,crop TEXT,description TEXT,zone TEXT,
    cents INTEGER,seller_ok INTEGER DEFAULT 0,buyer_ok INTEGER DEFAULT 0,status TEXT DEFAULT 'Abierta',fee INTEGER DEFAULT 0);

CREATE TRIGGER release_reserved BEFORE DELETE ON users BEGIN
    UPDATE offers SET buyer=NULL,buyer_ok=0,seller_ok=0,status='Abierta' WHERE buyer=OLD.id AND status='Reservada'; END;

CREATE TABLE channel_trials(owner TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,trial TEXT UNIQUE REFERENCES users(id) ON DELETE CASCADE);

CREATE TABLE meteo(user TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,data TEXT,error TEXT,checked TEXT);

CREATE TABLE timeline(id INTEGER PRIMARY KEY,user TEXT REFERENCES users(id) ON DELETE CASCADE,channel TEXT,direction TEXT,body TEXT,stamp TEXT,external TEXT UNIQUE);

CREATE TABLE receipts(external TEXT PRIMARY KEY,status TEXT,stamp INTEGER,detail TEXT);

CREATE INDEX tl_user ON timeline(user,id);

CREATE TABLE chat_productor(
        id INTEGER PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        pregunta TEXT NOT NULL,respuesta TEXT NOT NULL,fecha TEXT NOT NULL);

CREATE TABLE enlaces(parcela TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,clave TEXT UNIQUE,vence TEXT,receptor TEXT REFERENCES users(id) ON DELETE SET NULL);

CREATE TABLE atlas_spaces(owner TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE);

CREATE TABLE productores(id INTEGER PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,nombre TEXT NOT NULL,telefono TEXT NOT NULL DEFAULT '',comunidad TEXT NOT NULL,notas TEXT NOT NULL DEFAULT '',activo INTEGER DEFAULT 1,ejemplo INTEGER DEFAULT 0);

CREATE TABLE parcelas(user TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,productor INTEGER NOT NULL REFERENCES productores(id),area REAL CHECK(area>0),altitud REAL,caracteristicas TEXT DEFAULT '',activo INTEGER DEFAULT 1,ejemplo INTEGER DEFAULT 0);

CREATE TABLE registros_clima(user TEXT REFERENCES users(id) ON DELETE CASCADE,hora TEXT,fuente TEXT,temp REAL,hum REAL,lluvia REAL,viento REAL,direccion REAL,PRIMARY KEY(user,hora,fuente));

CREATE TABLE evaluaciones(user TEXT REFERENCES users(id) ON DELETE CASCADE,hora TEXT,contexto TEXT,resultado TEXT,PRIMARY KEY(user,hora,contexto));

CREATE TABLE auditoria(id INTEGER PRIMARY KEY,owner TEXT REFERENCES users(id) ON DELETE CASCADE,productor INTEGER,accion TEXT,fecha TEXT);

CREATE TABLE envios_prueba(ensayo INTEGER PRIMARY KEY REFERENCES ensayos(id) ON DELETE CASCADE,destinatario TEXT NOT NULL,recibido TEXT NOT NULL,acuse TEXT);

CREATE TABLE envios_fallidos(alerta INTEGER PRIMARY KEY REFERENCES alerts(id) ON DELETE CASCADE,intentos INTEGER NOT NULL,estado TEXT NOT NULL,fecha TEXT NOT NULL);

CREATE TABLE ensayos(id INTEGER PRIMARY KEY,owner TEXT REFERENCES users(id) ON DELETE CASCADE,parcela TEXT,escenario TEXT,resultado TEXT,fecha TEXT);
