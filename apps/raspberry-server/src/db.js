import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';

const dataDir = path.resolve(process.cwd(), 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'checkcheck.db');
const db = new Database(dbPath);

db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    matricula TEXT NOT NULL UNIQUE,
    chave_usuario TEXT NOT NULL,
    rfid_uid TEXT NOT NULL UNIQUE,
    ativo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS checkcheck (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    matricula TEXT NOT NULL,
    chave_usuario TEXT NOT NULL,
    data_hora_entrada_singapura TEXT NOT NULL,
    entrada INTEGER NOT NULL,
    rfid_uid TEXT NOT NULL,
    reader_id TEXT,
    created_at TEXT NOT NULL
  );
`);

export function normalizeUid(raw) {
  return String(raw || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-F0-9]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function timestampSingapore() {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Singapore',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });

  const parts = formatter.formatToParts(new Date());
  const map = Object.fromEntries(parts.filter((p) => p.type !== 'literal').map((p) => [p.type, p.value]));
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}:${map.second}`;
}

export function listEvents(limit = 200) {
  const stmt = db.prepare(`
    SELECT id, nome_completo, matricula, chave_usuario, data_hora_entrada_singapura, entrada, rfid_uid, reader_id
    FROM checkcheck
    ORDER BY id DESC
    LIMIT ?
  `);
  return stmt.all(limit);
}

export function listPresentUsers() {
  const stmt = db.prepare(`
    WITH ultimos AS (
      SELECT c1.*
      FROM checkcheck c1
      INNER JOIN (
        SELECT matricula, MAX(id) AS max_id
        FROM checkcheck
        GROUP BY matricula
      ) c2 ON c1.matricula = c2.matricula AND c1.id = c2.max_id
    )
    SELECT nome_completo, matricula, chave_usuario, data_hora_entrada_singapura
    FROM ultimos
    WHERE entrada = 1
    ORDER BY nome_completo ASC
  `);
  const users = stmt.all();
  return {
    total: users.length,
    users
  };
}

export function createUser({ nomeCompleto, matricula, chaveUsuario, rfidUid }) {
  if (!/^\d{7}$/.test(matricula)) {
    throw new Error('Matrícula inválida. Use exatamente 7 dígitos.');
  }

  if (!/^[A-Za-z0-9]{4}$/.test(chaveUsuario)) {
    throw new Error('Chave do usuário inválida. Use 4 caracteres alfanuméricos.');
  }

  const uid = normalizeUid(rfidUid);
  if (!uid) {
    throw new Error('UID RFID inválido.');
  }

  const now = timestampSingapore();
  const stmt = db.prepare(`
    INSERT INTO users (nome_completo, matricula, chave_usuario, rfid_uid, created_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  const result = stmt.run(nomeCompleto.trim(), matricula, chaveUsuario.toUpperCase(), uid, now);
  return {
    id: result.lastInsertRowid,
    nome_completo: nomeCompleto.trim(),
    matricula,
    chave_usuario: chaveUsuario.toUpperCase(),
    rfid_uid: uid
  };
}

export function registerScan({ rfidUid, readerId }) {
  const uid = normalizeUid(rfidUid);
  const user = db
    .prepare('SELECT nome_completo, matricula, chave_usuario, rfid_uid FROM users WHERE rfid_uid = ? AND ativo = 1')
    .get(uid);

  if (!user) {
    throw new Error('Cartão não cadastrado.');
  }

  let entrada;
  if (readerId === 'ENTRY') {
    entrada = 1;
  } else if (readerId === 'EXIT') {
    entrada = 0;
  } else {
    const last = db
      .prepare('SELECT entrada FROM checkcheck WHERE matricula = ? ORDER BY id DESC LIMIT 1')
      .get(user.matricula);
    entrada = last?.entrada === 1 ? 0 : 1;
  }

  const now = timestampSingapore();
  const stmt = db.prepare(`
    INSERT INTO checkcheck (
      nome_completo, matricula, chave_usuario, data_hora_entrada_singapura, entrada, rfid_uid, reader_id, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const result = stmt.run(
    user.nome_completo,
    user.matricula,
    user.chave_usuario,
    now,
    entrada,
    user.rfid_uid,
    readerId || null,
    now
  );

  return {
    id: result.lastInsertRowid,
    nome_completo: user.nome_completo,
    matricula: user.matricula,
    chave_usuario: user.chave_usuario,
    data_hora_entrada_singapura: now,
    entrada,
    rfid_uid: user.rfid_uid,
    reader_id: readerId || null
  };
}
