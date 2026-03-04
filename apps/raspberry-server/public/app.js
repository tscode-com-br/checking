const totalPresentesEl = document.getElementById('totalPresentes');
const presentesListEl = document.getElementById('presentesList');
const registrosTableBodyEl = document.getElementById('registrosTableBody');

function renderPresentes(presentes) {
  presentesListEl.innerHTML = '';
  if (!presentes.length) {
    const li = document.createElement('li');
    li.textContent = 'Nenhum usuário presente.';
    presentesListEl.appendChild(li);
    return;
  }

  presentes.forEach((pessoa) => {
    const li = document.createElement('li');
    const nome = pessoa.nome_completo || 'Sem nome';
    const matricula = pessoa.matricula || '-';
    const projeto = pessoa.projeto || '-';
    li.textContent = `${nome} | Matrícula: ${matricula} | Projeto: ${projeto} | UID: ${pessoa.rfid_uid}`;
    presentesListEl.appendChild(li);
  });
}

function renderRegistros(registros) {
  registrosTableBodyEl.innerHTML = '';
  registros.forEach((registro) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${registro.rfid_uid}</td>
      <td>${registro.chave_usuario}</td>
      <td>${registro.entrada ? 'true' : 'false'}</td>
      <td>${registro.data_hora_evento_singapura}</td>
      <td>${registro.nome_completo || '-'}</td>
      <td>${registro.matricula || '-'}</td>
      <td>${registro.projeto || '-'}</td>
      <td>${registro.reader_id || '-'}</td>
    `;
    registrosTableBodyEl.appendChild(tr);
  });
}

function renderAll(payload) {
  totalPresentesEl.textContent = String(payload.totalPresentes || 0);
  renderPresentes(payload.presentes || []);
  renderRegistros(payload.registros || []);
}

async function bootstrap() {
  const response = await fetch('/api/status');
  const data = await response.json();
  renderAll(data);
}

bootstrap();

const socket = io();
socket.on('bootstrap', (payload) => {
  renderAll(payload);
});

socket.on('scan:created', async () => {
  await bootstrap();
});
