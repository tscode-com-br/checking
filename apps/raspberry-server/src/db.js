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

function tableColumns(tableName) {
  const rows = db.prepare(`PRAGMA table_info(${tableName})`).all();
  return rows.map((row) => row.name);
}

function createUsersV2(tableName = 'users') {
  db.exec(`
    CREATE TABLE IF NOT EXISTS ${tableName} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      rfid_uid TEXT NOT NULL UNIQUE,
      chave_usuario TEXT NOT NULL,
      nome_completo TEXT,
      matricula TEXT,
      projeto TEXT,
      ativo INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      CHECK (projeto IN ('P80', 'P82', 'P83') OR projeto IS NULL)
    );
  `);
}

function createCheckcheckV2(tableName = 'checkcheck') {
  db.exec(`
    CREATE TABLE IF NOT EXISTS ${tableName} (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      rfid_uid TEXT NOT NULL,
      chave_usuario TEXT NOT NULL,
      entrada INTEGER NOT NULL CHECK (entrada IN (0,1)),
      data_hora_evento_singapura TEXT NOT NULL,
      reader_id TEXT,
      device_id TEXT,
      created_at TEXT NOT NULL
    );
  `);
}

function migrateSchemaIfNeeded() {
  const userCols = tableColumns('users');
  const checkCols = tableColumns('checkcheck');

  if (!userCols.length) {
    createUsersV2('users');
  } else {
    const usersIsV2 = userCols.includes('rfid_uid') && userCols.includes('updated_at');
    if (!usersIsV2) {
      createUsersV2('users_v2');
      db.exec(`
        INSERT INTO users_v2 (rfid_uid, chave_usuario, nome_completo, matricula, projeto, ativo, created_at, updated_at)
        SELECT
          rfid_uid,
          chave_usuario,
          nome_completo,
          matricula,
          NULL,
          COALESCE(ativo, 1),
          created_at,
          created_at
        FROM users;
      `);
      db.exec('DROP TABLE users;');
      db.exec('ALTER TABLE users_v2 RENAME TO users;');
    }
  }

  if (!checkCols.length) {
    createCheckcheckV2('checkcheck');
  } else {
    const checkIsV2 = checkCols.includes('data_hora_evento_singapura') && checkCols.includes('device_id');
    if (!checkIsV2) {
      createCheckcheckV2('checkcheck_v2');
      db.exec(`
        INSERT INTO checkcheck_v2 (rfid_uid, chave_usuario, entrada, data_hora_evento_singapura, reader_id, device_id, created_at)
        SELECT
          rfid_uid,
          chave_usuario,
          entrada,
          data_hora_entrada_singapura,
          reader_id,
          NULL,
          created_at
        FROM checkcheck;
      `);
      db.exec('DROP TABLE checkcheck;');
      db.exec('ALTER TABLE checkcheck_v2 RENAME TO checkcheck;');
    }
  }
}

migrateSchemaIfNeeded();

export function normalizeUid(raw) {
  return String(raw || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '');
}

function normalizeProjeto(raw) {
  if (!raw) {
    return null;
  }
  const value = String(raw).trim().toUpperCase();
  if (!['P80', 'P82', 'P83'].includes(value)) {
    throw new Error('Projeto inválido. Valores permitidos: P80, P82, P83.');
  }
  return value;
}

function normalizeMatricula(raw) {
  if (raw == null || raw === '') {
    return null;
  }
  const value = String(raw).trim();
  if (!/^\d{7,10}$/.test(value)) {
    throw new Error('Matrícula inválida. Use de 7 a 10 dígitos numéricos.');
  }
  return value;
}

function normalizeUserKey(raw) {
  const value = String(raw || '').trim().toUpperCase();
  if (!/^[A-Z0-9]{4}$/.test(value)) {
    throw new Error('Chave do usuário inválida. Use 4 caracteres alfanuméricos.');
  }
  return value;
}

function generateUserKeyFromMatricula(matricula) {
  const value = normalizeMatricula(matricula);
  if (!value) {
    throw new Error('Matrícula é obrigatória para gerar chave interna.');
  }
  return value.slice(-4);
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

export function checkCard(rfidUid) {
  const uid = normalizeUid(rfidUid);
  if (!uid) {
    throw new Error('UID RFID inválido.');
  }

  const user = db
    .prepare('SELECT rfid_uid, chave_usuario, nome_completo, matricula, projeto FROM users WHERE rfid_uid = ? AND ativo = 1')
    .get(uid);

  if (!user) {
    return { exists: false, uid };
  }

  return {
    exists: true,
    uid,
    user
  };
}

export function createOrUpdateUserByCard({ rfidUid, chaveUsuario, nomeCompleto, matricula, projeto }) {
  const uid = normalizeUid(rfidUid);
  if (!uid) {
    throw new Error('UID RFID inválido.');
  }

  const matriculaNormalizada = normalizeMatricula(matricula);
  const chave = chaveUsuario
    ? normalizeUserKey(chaveUsuario)
    : matriculaNormalizada
      ? generateUserKeyFromMatricula(matriculaNormalizada)
      : null;
  if (!chave) {
    throw new Error('Informe chaveUsuario ou matrícula (7-10 dígitos).');
  }

  const nome = nomeCompleto ? String(nomeCompleto).trim() : null;
  const projetoNormalizado = normalizeProjeto(projeto);
  const now = timestampSingapore();

  const existing = db.prepare('SELECT id FROM users WHERE rfid_uid = ?').get(uid);

  if (!existing) {
    const result = db
      .prepare(
        `INSERT INTO users (rfid_uid, chave_usuario, nome_completo, matricula, projeto, ativo, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, 1, ?, ?)`
      )
      .run(uid, chave, nome, matriculaNormalizada, projetoNormalizado, now, now);

    return {
      id: result.lastInsertRowid,
      rfid_uid: uid,
      chave_usuario: chave,
      nome_completo: nome,
      matricula: matriculaNormalizada,
      projeto: projetoNormalizado
    };
  }

  db.prepare(
    `UPDATE users
     SET chave_usuario = ?,
         nome_completo = COALESCE(?, nome_completo),
         matricula = COALESCE(?, matricula),
         projeto = COALESCE(?, projeto),
         ativo = 1,
         updated_at = ?
     WHERE rfid_uid = ?`
  ).run(chave, nome, matriculaNormalizada, projetoNormalizado, now, uid);

  return db
    .prepare('SELECT id, rfid_uid, chave_usuario, nome_completo, matricula, projeto FROM users WHERE rfid_uid = ?')
    .get(uid);
}

export function registerScan({ rfidUid, entrada, matricula, chaveUsuario, readerId, deviceId }) {
  const uid = normalizeUid(rfidUid);
  if (!uid) {
    throw new Error('UID RFID inválido.');
  }

  const entradaFlag = entrada === true || entrada === 1 || entrada === 'true' ? 1 : entrada === false || entrada === 0 || entrada === 'false' ? 0 : null;
  if (entradaFlag == null) {
    throw new Error('Campo entrada inválido. Envie true ou false.');
  }

  let user = db
    .prepare('SELECT id, rfid_uid, chave_usuario, nome_completo, matricula, projeto FROM users WHERE rfid_uid = ? AND ativo = 1')
    .get(uid);

  const now = timestampSingapore();
  let createdUser = false;
  let chaveFinal;

  if (!user) {
    const matriculaNormalizada = normalizeMatricula(matricula);
    if (!matriculaNormalizada) {
      throw new Error('Cartão não cadastrado. Envie matrícula (7-10 dígitos) para o primeiro registro.');
    }

    chaveFinal = chaveUsuario ? normalizeUserKey(chaveUsuario) : generateUserKeyFromMatricula(matriculaNormalizada);
    const result = db
      .prepare(
        `INSERT INTO users (rfid_uid, chave_usuario, nome_completo, matricula, projeto, ativo, created_at, updated_at)
         VALUES (?, ?, NULL, ?, NULL, 1, ?, ?)`
      )
      .run(uid, chaveFinal, matriculaNormalizada, now, now);

    user = {
      id: result.lastInsertRowid,
      rfid_uid: uid,
      chave_usuario: chaveFinal,
      nome_completo: null,
      matricula: matriculaNormalizada,
      projeto: null
    };
    createdUser = true;
  } else {
    chaveFinal = user.chave_usuario;
    if (chaveUsuario != null && String(chaveUsuario).trim() !== '') {
      const chaveInformada = normalizeUserKey(chaveUsuario);
      if (chaveInformada !== user.chave_usuario) {
        throw new Error('Chave informada não confere com a chave cadastrada para este cartão.');
      }
    }

    if (matricula != null && String(matricula).trim() !== '') {
      const matriculaInformada = normalizeMatricula(matricula);
      if (!user.matricula) {
        db.prepare('UPDATE users SET matricula = ?, updated_at = ? WHERE id = ?').run(matriculaInformada, now, user.id);
        user.matricula = matriculaInformada;
      } else if (user.matricula !== matriculaInformada) {
        throw new Error('Matrícula informada não confere com a matrícula cadastrada para este cartão.');
      }
    }
  }

  const result = db
    .prepare(
      `INSERT INTO checkcheck (rfid_uid, chave_usuario, entrada, data_hora_evento_singapura, reader_id, device_id, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .run(uid, chaveFinal, entradaFlag, now, readerId || null, deviceId || null, now);

  return {
    id: result.lastInsertRowid,
    rfid_uid: uid,
    chave_usuario: chaveFinal,
    entrada: entradaFlag,
    data_hora_evento_singapura: now,
    reader_id: readerId || null,
    device_id: deviceId || null,
    created_user: createdUser,
    user
  };
}

export function listEvents(limit = 200) {
  const stmt = db.prepare(`
    SELECT
      c.id,
      c.rfid_uid,
      c.chave_usuario,
      c.entrada,
      c.data_hora_evento_singapura,
      c.reader_id,
      c.device_id,
      u.nome_completo,
      u.matricula,
      u.projeto
    FROM checkcheck c
    LEFT JOIN users u ON u.rfid_uid = c.rfid_uid
    ORDER BY c.id DESC
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
        SELECT rfid_uid, MAX(id) AS max_id
        FROM checkcheck
        GROUP BY rfid_uid
      ) c2 ON c1.rfid_uid = c2.rfid_uid AND c1.id = c2.max_id
    )
    SELECT
      u.rfid_uid,
      u.chave_usuario,
      u.nome_completo,
      u.matricula,
      u.projeto,
      ultimos.data_hora_evento_singapura
    FROM ultimos
    LEFT JOIN users u ON u.rfid_uid = ultimos.rfid_uid
    WHERE ultimos.entrada = 1
    ORDER BY COALESCE(u.nome_completo, u.rfid_uid) ASC
  `);
  const users = stmt.all();
  return {
    total: users.length,
    users
  };
}
