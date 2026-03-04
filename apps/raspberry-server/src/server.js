import 'dotenv/config';
import http from 'node:http';
import express from 'express';
import { Server } from 'socket.io';
import { checkCard, createOrUpdateUserByCard, listEvents, listPresentUsers, registerScan } from './db.js';

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*'
  }
});

const PORT = Number(process.env.PORT || 3000);
const DEVICE_API_KEY = process.env.DEVICE_API_KEY || '';
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || '';
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '*';
const TRUST_PROXY = String(process.env.TRUST_PROXY || 'false').toLowerCase() === 'true';

if (TRUST_PROXY) {
  app.set('trust proxy', 1);
}

app.use(express.json());
app.use((_req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-device-key, x-admin-key');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  if (_req.method === 'OPTIONS') {
    return res.sendStatus(204);
  }
  return next();
});
app.use(express.static('public'));

function requireDeviceKey(req, res, next) {
  if (!DEVICE_API_KEY) {
    return res.status(500).json({ error: 'DEVICE_API_KEY não configurada no servidor.' });
  }
  const provided = req.header('x-device-key');
  if (provided !== DEVICE_API_KEY) {
    return res.status(401).json({ error: 'Chave de dispositivo inválida.' });
  }
  return next();
}

function requireAdminKey(req, res, next) {
  if (!ADMIN_API_KEY) {
    return res.status(500).json({ error: 'ADMIN_API_KEY não configurada no servidor.' });
  }
  const provided = req.header('x-admin-key');
  if (provided !== ADMIN_API_KEY) {
    return res.status(401).json({ error: 'Chave admin inválida.' });
  }
  return next();
}

app.get('/api/status', (_req, res) => {
  const present = listPresentUsers();
  const events = listEvents(300);
  res.json({
    totalPresentes: present.total,
    presentes: present.users,
    registros: events
  });
});

app.post('/api/users', requireAdminKey, (req, res) => {
  try {
    const { rfidUid, chaveUsuario, nomeCompleto, matricula, projeto } = req.body || {};
    if (!rfidUid) {
      return res.status(400).json({ error: 'Campo obrigatório: rfidUid.' });
    }
    if (!chaveUsuario && !matricula) {
      return res.status(400).json({ error: 'Informe chaveUsuario ou matrícula (7-10 dígitos).' });
    }

    const user = createOrUpdateUserByCard({ rfidUid, chaveUsuario, nomeCompleto, matricula, projeto });

    return res.status(201).json({ ok: true, user });
  } catch (error) {
    return res.status(400).json({ error: error.message || 'Falha ao cadastrar usuário.' });
  }
});

app.post('/api/cards/check', requireDeviceKey, (req, res) => {
  try {
    const { rfidUid } = req.body || {};
    if (!rfidUid) {
      return res.status(400).json({ ok: false, error: 'rfidUid é obrigatório.' });
    }

    const result = checkCard(rfidUid);
    return res.json({
      ok: true,
      exists: result.exists,
      needsMatricula: !result.exists,
      rfidUid: result.uid
    });
  } catch (error) {
    return res.status(400).json({ ok: false, error: error.message || 'Falha ao consultar cartão.' });
  }
});

app.post('/api/scan', requireDeviceKey, (req, res) => {
  try {
    const { rfidUid, entrada, matricula, chaveUsuario, readerId, deviceId } = req.body || {};
    if (!rfidUid) {
      return res.status(400).json({ ok: false, error: 'rfidUid é obrigatório.' });
    }

    const entradaFinal = entrada ?? (readerId === 'ENTRY' ? true : readerId === 'EXIT' ? false : null);
    if (entradaFinal == null) {
      return res.status(400).json({ ok: false, error: 'entrada é obrigatória (true/false) ou readerId válido.' });
    }

    const evento = registerScan({
      rfidUid,
      entrada: entradaFinal,
      matricula,
      chaveUsuario,
      readerId,
      deviceId
    });
    const present = listPresentUsers();

    io.emit('scan:created', {
      evento,
      totalPresentes: present.total,
      presentes: present.users,
      deviceId: deviceId || null
    });

    return res.json({ ok: true, evento, totalPresentes: present.total });
  } catch (error) {
    return res.status(400).json({ ok: false, error: error.message || 'Falha ao registrar leitura.' });
  }
});

io.on('connection', (socket) => {
  const present = listPresentUsers();
  const events = listEvents(300);
  socket.emit('bootstrap', {
    totalPresentes: present.total,
    presentes: present.users,
    registros: events
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`CheckCheck server ativo em http://0.0.0.0:${PORT}`);
});
