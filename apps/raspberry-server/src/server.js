import 'dotenv/config';
import http from 'node:http';
import express from 'express';
import { Server } from 'socket.io';
import { createUser, listEvents, listPresentUsers, registerScan } from './db.js';

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

app.use(express.json());
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
    const { nomeCompleto, matricula, chaveUsuario, rfidUid } = req.body || {};
    if (!nomeCompleto || !matricula || !chaveUsuario || !rfidUid) {
      return res.status(400).json({ error: 'Campos obrigatórios: nomeCompleto, matricula, chaveUsuario, rfidUid.' });
    }

    const user = createUser({
      nomeCompleto,
      matricula,
      chaveUsuario,
      rfidUid
    });

    return res.status(201).json({ ok: true, user });
  } catch (error) {
    return res.status(400).json({ error: error.message || 'Falha ao cadastrar usuário.' });
  }
});

app.post('/api/scan', requireDeviceKey, (req, res) => {
  try {
    const { rfidUid, readerId, deviceId } = req.body || {};
    if (!rfidUid) {
      return res.status(400).json({ ok: false, error: 'rfidUid é obrigatório.' });
    }

    const evento = registerScan({ rfidUid, readerId });
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
