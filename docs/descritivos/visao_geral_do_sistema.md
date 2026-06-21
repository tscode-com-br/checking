## 0. INTRODUÇÃO

O sistema Checking começou a ser desenvolvido em março de 2026, graças à idealização do **Engenheiro Dilnei Schmidt**.

Houve a necessidade de identificar, rapidamente, todos os funcionários da Petrobras presentes, momentaneamente, no local em que os trabalhos de construção e montagem estavam acontecendo, caso um acidente viesse a ocorrer.

A primeira solução adotada pelo corpo gerencial de SMS foi a criação de um formulário online, onde cada funcionário deveria preencher no momento da chegada e no momento da saída do local de trabalho.

Esta solução mostrou-se satisfatória para a identificação de todos os funcionários presentes, porém, além de trabalhoso, muitos funcionários acabavam esquecendo de realizar o preenchimento ocasionalmente.

Então, visando aumentar a eficiência do processo, Dilnei desenvolveu um aplicativo capaz de:

- identificar, por localização GPS, a proximidade do usuário com o local do trabalho e avisá-lo da necessidade de realização de check-in, ou seja, preenchimento do formulário,

- pré-ajustar alarmes no dispositivo móvel em horários típicos de realização de check-in e check-out, visando lembrar ao usuário da necessidade de preenchimento do formulário e

- preenchimento automatizado do formulário com os dados salvos do usuário, e envio do formulário online.

Esta solução facilitou as atividades dos usuários, fazendo com que a frequência de preenchimento aumentasse.

Em março de 2026, o **Engenheiro Tamer Salmem** tomou conhecimento das soluções implementadas, e avançou no emprego das tecnologias atuais de programação, desenvolvendo um sistema inicialmente idealizado por Dilnei.

A intenção era fazer com que o usuário não precisasse se preocupar com a necessidade de abrir um aplicativo e realizar uma atividade de check-in ou check-out.

Além disso, também deveria desenvolver um controle em tempo real, para que os administradores pudessem acessar não apenas quem estivesse no local de trabalho, mas em qual das localizações cadastradas para cada projeto os usuário estariam em tempo real.

Isto aumenta ainda mais a capacidade de resposta em uma situação de emergência, pois é possível identificar, em tempo real, onde cada funcionário está, tendo como base as localizações registradas no sistema.

Desta forma, o sistema ganhou as seguintes funcionalidades:

- ativação de serviços por geofencing, ou seja, de acordo com a proximidade do usuário com o local de trabalho,

- execução de tarefas em segundo plano, realizando check-in a cada alteração de localização dentro das instalações do ambiente de trabalho, e realizando check-out quando o usuário se afasta do local de trabalho, sem que o usuário precise sequer desbloquear o dispositivo móvel,

- envio em tempo real das informações de localização dos usuário para a página do administrador,

- possibilidade de cadastrar quantos projetos forem necessários ao redor do mundo,

Além disso, o sistema também é capaz de entrar no 'Modo Acidente'. Caso haja um acidente, qualquer usuário poderá disparar um alarme, que informará, em tempo real, todos os usuários cadastrados no mesmo projeto em que o acidente ocorreu.  Caso o 'Modo Acidente' esteja ativo:

- uma nova tabela é criada no website do administrador, listando a situação de cada usuário do projeto afetado: 'em segurança', 'no local do acidente, mas em segurança' e 'no local do acidente e precisando de ajuda'.

- a possibilidade de utilizar o dispositivo para gravar um video e enviar, em tempo real, em forma de link na nova tabela criada no website do administrador, de forma que o administrador veja, em tempo real, cenas do local do acidente.

- botão 'Acionar Serviço de Emergência', que realiza uma ligação telefônica para o serviço local de emergência cadastrado, informando que houve um acidente, o local e o contato do responsável para maiores esclarecimentos, sendo falando no idioma local.

A robustez e confiabilidade do sistema tornaram-o útil para, finalmente, trazer segurança operacional e capacidade de resposta imediata por parte da equipe de SMS da Petrobras.

Para finalizar, o **Engenheiro Thiago Soares do Nascimento** foi o responsável por integrar as informações geradas pelo sistema com os dashboards gerenciais existentes, de forma que o sistema atue junto com o antigo preenchimento dos formulários, mantendo os controles gerenciais atualizados, mesmo com o novo sistema implementado.

Assim, nasceu o CHECKING, melhor detalhado nas seções abaixo.


## 1. DETALHAMENTO DAS PARTES QUE COMPÕEM O SISTEMA CHECKING

O **Checking** é um sistema de controle de presença que registra a entrada e saída de colaboradores nos locais de trabalho. Funciona por diferentes canais — leitores de cartão RFID instalados fisicamente no local, um aplicativo Android, uma página web acessível pelo celular e um painel de administração — e reúne tudo em um único lugar.

O conjunto é formado por:

- Uma **API**, desenvolvida em Python/FastAPI,
- Um **website** dedicado aos administradores do sistema (https://www.tscode.com.br/checking/admin),
- Uma **aplicação Web**, responsiva para dispositivos móveis e desktops (https://www.tscode.com.br/checking/user),
- Um **dashboard** para controle de transporte de pessoal (https://www.tscode.com.br/checking/transport) e
- Um **aplicativo exclusivo para Android**, desenvolvido em Kotlin.

---

## 1.1. API

A API é o cérebro do sistema. Toda vez que alguém faz um check-in ou check-out — seja passando o cartão no leitor físico, pelo aplicativo ou pela página web — é ela quem recebe essa informação, verifica se está correta, salva no banco de dados e avisa os demais componentes do sistema em tempo real.

Além de registrar a presença, a API também é responsável por preencher automaticamente o formulário corporativo no Microsoft Forms após cada registro, por coordenar o sistema de transporte de pessoal, por disparar alertas de emergência em caso de acidente e por garantir que nenhum dado se perca mesmo quando há instabilidade na conexão.

Em resumo: é ela quem faz o sistema funcionar de ponta a ponta, por baixo dos panos.

---

## 1.2. Website

O website é o painel de controle dos administradores. Por ele, é possível ver em tempo real quais colaboradores estão em check-in e quais estão em check-out, além de gerenciar todos os aspectos do sistema sem precisar de conhecimento técnico.

Entre as principais funções estão: cadastrar e editar colaboradores, criar projetos e configurar suas regras, definir as áreas geográficas que o sistema reconhece, consultar relatórios de presença por período e exportar dados. O website também é o ponto central para acionar e acompanhar o **Modo Acidente** — quando um incidente é declarado, o administrador consegue ver a situação de cada colaborador em tempo real e coordenar a resposta de emergência.

---

## 1.3. Aplicação Web

A aplicação web é a ferramenta dos colaboradores. Funciona no navegador do celular ou do computador, sem precisar instalar nada, e permite que cada pessoa registre sua entrada ou saída, consulte seu histórico e solicite transporte.

Quando o colaborador ativa as **atividades automáticas**, o próprio celular detecta a localização e faz o check-in ou check-out automaticamente ao entrar ou sair das áreas cadastradas — sem que a pessoa precise fazer nada manualmente. Em caso de acidente, a interface muda e passa a solicitar que o colaborador informe sua situação e zona de segurança.

A aplicação está disponível em seis idiomas (português, inglês, chinês, malaio, indonésio e tagalo) para atender equipes internacionais.

---

## 1.4. Dashboard de Transportes

O dashboard de transportes é a ferramenta do responsável pela logística de deslocamento dos colaboradores. Por ele é possível cadastrar os veículos disponíveis, visualizar e organizar as solicitações de transporte feitas pelos colaboradores e alocar cada pessoa em um veículo para o dia.

O sistema conta com um **motor de inteligência artificial** que analisa os endereços e horários e sugere automaticamente como agrupar os passageiros e ordenar as paradas de forma otimizada — reduzindo o tempo de deslocamento e o número de viagens. O responsável pode aceitar a sugestão como está, ajustá-la ou montar a alocação manualmente.

---

## 1.5. Aplicativo Android

O aplicativo Android oferece as mesmas funções da aplicação web, mas com uma experiência mais completa para quem usa o celular Android no dia a dia. A principal vantagem é a **automação por geolocalização**: o aplicativo roda em segundo plano e registra o check-in ou check-out automaticamente conforme o colaborador entra e sai das áreas cadastradas, sem depender do navegador.

O app também funciona **sem internet**: quando não há conexão, os registros ficam salvos no celular e são enviados ao sistema assim que a conexão é restaurada, sempre com o horário original da ocorrência. Inclui ainda o histórico de registros com data, hora e local de cada evento, o módulo de solicitação de transporte e o modo de emergência para situações de acidente.

---

## 2. SITUAÇÕES PARA A REALIZAÇÃO DE ATIVIDADES

As situações abaixo são simulações típicas que definem as atividades que o sistema deve desempenhar para cada usuário: check-in ou check-out.

---

## 2.1. SITUAÇõES DEFINIDAS PARA A APLICAÇÃO WEB

REGRAS PARA REALIZAÇÃO DE CHECK-IN E CHECK-OUT:

Confirme que as regras estão funcionando exatamente como as situações abaixo.

Situação 1:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-in;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está na localização 'Zona de CheckOut' ou está a mais de 2 km distante de qualquer local cadastrado, exceto da Zona de CheckOut';
- a aplicação web 'Checking Web', então, realiza o check-out do usuário, pois a última atividade foi um check-in;

Situação 2:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-out;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está na localização 'Zona de CheckOut' ou está a mais de 2 km distante de qualquer local cadastrado, exceto da Zona de CheckOut';
- a aplicação web 'Checking Web' não toma nenhuma ação, mesmo que tenha havido troca de localização, pois o check-out não precisa ser repetido em função da alteração de localização.

Situação 3:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-out;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está DENTRO de alguma localização cadastrada na API diferente da localização 'Zona de CheckOut' (correspondência efetiva com a área, não apenas proximidade);
- Nesta situação, o usuário está efetivamente no ambiente de trabalho, inclusive no primeiro check-in ao sair de casa e chegar ao trabalho;
- a aplicação web 'Checking Web', então, realiza o check-in do usuário, pois a última atividade foi um check-out;
- Ao realizar esse check-in, a aplicação web 'Checking Web' atualiza a localização do usuário para a localização cadastrada na API correspondente.
- IMPORTANTE (comportamento real da aplicação web e do app Kotlin): se o usuário NÃO estiver DENTRO de nenhuma localização cadastrada — ainda que esteja próximo (por exemplo, a menos de 2 km de alguma coordenada cadastrada, desconsiderando a 'Zona de CheckOut') —, a aplicação NÃO realiza check-in automático. Apenas atualiza a exibição da localização para 'Localização não Cadastrada', exatamente como na Situação 5. Ou seja, o check-in automático só ocorre quando a posição corresponde, de fato, a uma área cadastrada (estar dentro dela), e não por mera proximidade.

Situação 4:
- O usuário abre a aplicação web 'Checking Web', recarrega a aplicação web 'Checking Web' ou a traz para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-in;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está em alguma localização cadastrada na API diferente da localização 'Zona de CheckOut';
- a aplicação web 'Checking Web', então, realiza um novo check-in do usuário, INDEPENDENTEMENTE de a localização ter mudado ou não em relação ao check-in anterior;
- ou seja, mesmo que o usuário esteja no MESMO local do último check-in, um novo check-in deve ser realizado nesse mesmo local;
- esse novo check-in serve para registrar/atualizar a localização e o horário do usuário na API.

Situação 5:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-in;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário não está em nenhuma localização cadastrada na API e também não está a mais de 2 km distante de alguma coordenada cadastrada na API, desconsiderando a localização 'Zona de CheckOut' nesta verificação. Ou seja, o usuário está próximo do local de trabalho.
- a aplicação web 'Checking Web', então, não toma nenhuma ação, pois o usuário não está distante o suficiente para realizar um check-out e nem está na zona de checkout. a aplicação web 'Checking Web' apenas atualiza a exibição da localização como 'Localização não Cadastrada'.

Situação 6:
- A aplicação web 'Checking Web' já está em primeiro plano;
- A última atividade do usuário foi um check-in;
- A checkbox 'Atividades Automáticas' está habilitada;
- O usuário pressiona o botão 'Atualizar' para atualizar a sua localização;
- A aplicação web 'Checking Web' atualiza a localização do usuário, que pode coincidir ou não com a localização registrada no check-in imediatamente anterior.
- Nesta situação, a aplicação web 'Checking Web' deve realizar um novo check-in do usuário, INDEPENDENTEMENTE de a localização ter mudado ou não;
- ou seja, mesmo que o usuário esteja no MESMO local do último check-in, um novo check-in deve ser realizado nesse mesmo local, para registrar/atualizar a localização e o horário do usuário na API.

Situação 7:
- A aplicação web 'Checking Web' já está em primeiro plano;
- A última atividade do usuário foi um check-out;
- A checkbox 'Atividades Automáticas' está habilitada;
- A aplicação web 'Checking Web' atualiza a localização do usuário e percebe que ele está na localização 'Zona de CheckOut';
- A aplicação web 'Checking Web', então, não toma nenhuma ação, pois a última atividade já foi um check-out;
- Em seguida, o usuário pressiona o botão 'Atualizar' apenas para atualizar a sua localização;
- A aplicação web 'Checking Web' atualiza a localização do usuário para uma destas duas condições:
- Variante 7A: alguma localização cadastrada na API diferente de 'Zona de CheckOut';
- Variante 7B: nenhuma localização cadastrada na API, mas o usuário também não está a mais de 2 km distante de alguma coordenada cadastrada na API, desconsiderando a localização 'Zona de CheckOut' nesta verificação. Ou seja, o usuário continua próximo do local de trabalho;
- A aplicação web 'Checking Web' percebe que o usuário saiu da 'Zona de CheckOut';
- Nesta situação, a aplicação web 'Checking Web' deve realizar imediatamente um check-in do usuário;
- Ao realizar esse check-in, a aplicação web 'Checking Web' atualiza a localização do usuário para a localização cadastrada na API ou, quando não houver correspondência exata com um local cadastrado, para 'Localização não Cadastrada'.

Situação 8:
- O usuário carrega a aplicação web 'Checking Web', ou o usuário pressiona 'Refresh' para atualizar o link da aplicação web 'Checking Web', ou o usuário traz o navegador para primeiro plano com a URL da aplicação web 'Checking Web' aberta, ou o usuário alterna para a aba onde a aplicação web 'Checking Web' está aberta;
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web';
- A aplicação web 'Checking Web' atualiza a localização do usuário (isto sempre deve ocorrer);
- A aplicação web 'Checking Web' identifica que a posição atual do usuário corresponde à localização 'Zona Mista'. Esta identificação pode acontecer tanto na primeira entrada do usuário na 'Zona Mista' quanto em uma nova leitura consecutiva ainda dentro dela;
- Se a leitura atual apontar 'Zona Mista' e a última atividade relevante do usuário não tiver sido realizada na própria 'Zona Mista', então a alternância automática deve ser imediata:
- Variante 8A: se a última atividade do usuário foi um check-in, a aplicação web 'Checking Web' deve realizar imediatamente um check-out do usuário na localização 'Zona Mista';
- Variante 8B: se a última atividade do usuário foi um check-out, a aplicação web 'Checking Web' deve realizar imediatamente um check-in do usuário na localização 'Zona Mista';
- O campo 'Intervalo de Tempo para Zona Mista', na aba 'Cadastro' do website do administrador ('sistema\app\static\admin'), define o cooldown aplicável apenas às leituras consecutivas na própria 'Zona Mista' depois que a última atividade automática relevante também aconteceu nela;
- Se a última atividade automática realizada na própria 'Zona Mista' foi um check-in e a nova leitura continuar apontando 'Zona Mista', então a aplicação web 'Checking Web' só deve bloquear um novo check-out enquanto `tempo_decorrido < intervalo`;
- Se a última atividade automática realizada na própria 'Zona Mista' foi um check-out e a nova leitura continuar apontando 'Zona Mista', então a aplicação web 'Checking Web' só deve bloquear um novo check-in enquanto `tempo_decorrido < intervalo`;
- Quando `tempo_decorrido >= intervalo`, a aplicação web 'Checking Web' volta a permitir a alternância automática na própria 'Zona Mista', mesmo que a localização atual continue sendo 'Zona Mista';
- Exceção imediata após check-in em 'Zona Mista': se o usuário for localizado na 'Zona de CheckOut' ou em um ponto mais distante de qualquer área cadastrada na API do que a distância definida na tabela 'Distância mínima para check-out automático' para o projeto em que o usuário está alocado, desconsiderando a 'Zona de CheckOut', então a aplicação web 'Checking Web' deve realizar o check-out do usuário imediatamente, sem aguardar o cooldown da 'Zona Mista';
- Exceção imediata após check-out em 'Zona Mista': se o usuário for localizado em qualquer outra localização cadastrada na API, exceto 'Zona de CheckOut' e 'Zona Mista', ou se o usuário não estiver em nenhuma localização cadastrada, mas ainda estiver a uma distância menor ou igual à definida na tabela 'Distância mínima para check-out automático' para o projeto em que o usuário está alocado, desconsiderando a 'Zona de CheckOut', então a aplicação web 'Checking Web' deve realizar imediatamente um novo check-in do usuário. Neste caso, o cooldown configurado para a 'Zona Mista' deve ser descartado;
- Ou seja, a repetição consecutiva da 'Zona Mista' só bloqueia uma nova alternância automática enquanto `tempo_decorrido < intervalo`, e a alternância volta a ser permitida quando `tempo_decorrido >= intervalo`.

Situação 9:
- O usuário carrega a aplicação web 'Checking Web', ou o usuário pressiona 'Refresh' para atualizar o link da aplicação web 'Checking Web', ou o usuário traz o navegador para primeiro plano com a URL da aplicação web 'Checking Web' aberta, ou o usuário alterna para a aba onde a aplicação web 'Checking Web' está aberta;
- O usuário já está cadastrado no sistema, com senha. Quando abre a aplicação web 'Checking Web', o usuário é autenticado com sucesso.
- A checkbox 'Atividades Automáticas' está DESABILITADA. Não importa se a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web', ou se a permissão foi negada;
- A aplicação web 'Checking Web' atualiza a localização do usuário (isto sempre deve ocorrer) se houver permissão para isso. Se não houver, apenas mostre a mensagem 'Permissão negada' como já está implementado;
- O usuário seleciona 'check-in' ou 'check-out';
- O usuário seleciona 'Normal' ou 'Retroativo';
- A dropdown box 'Local' deve estar disponível sempre que a checkbox 'Atividades Automáticas' estiver desabilitada. O usuário então seleciona o local onde deseja realizar a atividade.
- O usuário clica em 'Registrar';
- A aplicação web 'Checking Web' deve seguir o fluxo normal existente e realizar a atividade conforme as seleções do usuário.

---

## 2.2. SITUAÇõES DEFINIDAS PARA O APLICATIVO NATIVO (iOS E ANDROID)

REGRAS PARA REALIZAÇÃO DE CHECK-IN E CHECK-OUT:

Confirme que as regras estão funcionando exatamente como as situações abaixo.

Situação 1:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-in;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está na localização 'Zona de CheckOut' ou está a mais de 2 km distante de qualquer local cadastrado, exceto da Zona de CheckOut';
- a aplicação web 'Checking Web', então, realiza o check-out do usuário, pois a última atividade foi um check-in;

Situação 2:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-out;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está na localização 'Zona de CheckOut' ou está a mais de 2 km distante de qualquer local cadastrado, exceto da Zona de CheckOut';
- a aplicação web 'Checking Web' não toma nenhuma ação, mesmo que tenha havido troca de localização, pois o check-out não precisa ser repetido em função da alteração de localização.

Situação 3:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-out;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está DENTRO de alguma localização cadastrada na API diferente da localização 'Zona de CheckOut' (correspondência efetiva com a área, não apenas proximidade);
- Nesta situação, o usuário está efetivamente no ambiente de trabalho, inclusive no primeiro check-in ao sair de casa e chegar ao trabalho;
- a aplicação web 'Checking Web', então, realiza o check-in do usuário, pois a última atividade foi um check-out;
- Ao realizar esse check-in, a aplicação web 'Checking Web' atualiza a localização do usuário para a localização cadastrada na API correspondente.
- IMPORTANTE (comportamento real do app Kotlin): nesta situação a última atividade foi um CHECK-OUT. Se o usuário NÃO estiver DENTRO de nenhuma localização cadastrada — ainda que esteja próximo (por exemplo, a menos de 2 km de alguma coordenada cadastrada, desconsiderando a 'Zona de CheckOut') —, a aplicação NÃO realiza check-in automático; apenas atualiza a exibição da localização para 'Localização não Cadastrada'. Ou seja, partindo de um check-out, o check-in automático só ocorre quando a posição corresponde, de fato, a uma área cadastrada (estar dentro dela), e não por mera proximidade (ver também a Variante 7B). ATENÇÃO: quando a última atividade foi um CHECK-IN e o usuário fica próximo, porém fora de área, o comportamento é diferente — a aplicação realiza um check-in com 'Localização não Cadastrada' como mudança (ver Situação 5).

Situação 4:
- O usuário abre a aplicação web 'Checking Web', recarrega a aplicação web 'Checking Web' ou a traz para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-in;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário está em alguma localização cadastrada na API diferente da localização 'Zona de CheckOut';
- a aplicação web 'Checking Web', então, realiza um novo check-in do usuário APENAS se a localização cadastrada for DIFERENTE da localização do último check-in;
- ou seja, se o usuário estiver no MESMO local do último check-in, NENHUMA ação é realizada (não há novo check-in no mesmo local). Isto elimina o check-in duplicado: o check-in automático só ocorre quando há mudança de localização;
- quando a localização muda para outra área cadastrada (diferente da 'Zona de CheckOut'), o novo check-in registra/atualiza a localização e o horário do usuário na API.

Situação 5:
- O usuário abre a aplicação web 'Checking Web' ou traz a aplicação web 'Checking Web' para primeiro plano.
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web'.
- A última atividade do usuário foi um check-in;
- a aplicação web 'Checking Web' atualiza a localização (isto sempre deve ocorrer);
- a aplicação web 'Checking Web' percebe que o usuário não está em nenhuma localização cadastrada na API e também não está a mais de 2 km distante de alguma coordenada cadastrada na API, desconsiderando a localização 'Zona de CheckOut' nesta verificação. Ou seja, o usuário está próximo do local de trabalho.
- como a última atividade foi um check-in e o usuário saiu da área cadastrada (está próximo, porém fora de qualquer área), a aplicação web 'Checking Web' realiza um check-in com a localização 'Localização não Cadastrada', registrando a continuidade do deslocamento do usuário;
- este check-in só ocorre como MUDANÇA: se o último check-in já foi 'Localização não Cadastrada', NENHUMA ação é realizada (não se repete);
- o usuário não está distante o suficiente para um check-out automático nem está na 'Zona de CheckOut'.

Situação 6:
- A aplicação web 'Checking Web' já está em primeiro plano;
- A última atividade do usuário foi um check-in;
- A checkbox 'Atividades Automáticas' está habilitada;
- O usuário pressiona o botão 'Atualizar' para atualizar a sua localização;
- A aplicação web 'Checking Web' atualiza a localização do usuário, que pode coincidir ou não com a localização registrada no check-in imediatamente anterior.
- Nesta situação, a aplicação web 'Checking Web' deve realizar um novo check-in do usuário APENAS se a localização for DIFERENTE da do último check-in;
- ou seja, se o usuário estiver no MESMO local do último check-in, NENHUMA ação é realizada (não há novo check-in no mesmo local) — mesma regra de mudança de localização da Situação 4. Quando a localização muda, o novo check-in registra/atualiza a localização e o horário do usuário na API.

Situação 7:
- A aplicação web 'Checking Web' já está em primeiro plano;
- A última atividade do usuário foi um check-out;
- A checkbox 'Atividades Automáticas' está habilitada;
- A aplicação web 'Checking Web' atualiza a localização do usuário e percebe que ele está na localização 'Zona de CheckOut';
- A aplicação web 'Checking Web', então, não toma nenhuma ação, pois a última atividade já foi um check-out;
- Em seguida, o usuário pressiona o botão 'Atualizar' apenas para atualizar a sua localização;
- A aplicação web 'Checking Web' atualiza a localização do usuário para uma destas duas condições:
- Variante 7A: o usuário ingressa em alguma localização cadastrada na API diferente de 'Zona de CheckOut';
- Variante 7B: o usuário não está em nenhuma localização cadastrada na API, mas também não está a mais de 2 km distante de alguma coordenada cadastrada na API, desconsiderando a localização 'Zona de CheckOut' nesta verificação. Ou seja, o usuário continua próximo do local de trabalho, porém fora de qualquer área cadastrada;
- Na Variante 7A, como a última atividade foi um check-out, a aplicação web 'Checking Web' realiza imediatamente o check-in do usuário na localização cadastrada correspondente;
- Na Variante 7B, como o usuário está em check-out e NÃO se encontra dentro de nenhuma área cadastrada, a aplicação web 'Checking Web' NÃO realiza check-in (mesma regra da nota IMPORTANTE da Situação 3, linha 30): apenas atualiza a exibição da localização para 'Localização não Cadastrada';
- Ou seja, o check-in de um usuário que está em check-out só ocorre quando ele ingressa, de fato, em uma área CADASTRADA na API diferente da 'Zona de CheckOut' (Variante 7A); a mera saída da 'Zona de CheckOut' para uma posição próxima, porém não cadastrada, não dispara check-in.

Situação 8:
- O usuário carrega a aplicação web 'Checking Web', ou o usuário pressiona 'Refresh' para atualizar o link da aplicação web 'Checking Web', ou o usuário traz o navegador para primeiro plano com a URL da aplicação web 'Checking Web' aberta, ou o usuário alterna para a aba onde a aplicação web 'Checking Web' está aberta;
- A checkbox 'Atividades Automáticas' está habilitada e a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web';
- A aplicação web 'Checking Web' atualiza a localização do usuário (isto sempre deve ocorrer);
- A aplicação web 'Checking Web' identifica que a posição atual do usuário corresponde à localização 'Zona Mista'. Esta identificação pode acontecer tanto na primeira entrada do usuário na 'Zona Mista' quanto em uma nova leitura consecutiva ainda dentro dela;
- Se a leitura atual apontar 'Zona Mista' e a última atividade relevante do usuário não tiver sido realizada na própria 'Zona Mista', então a alternância automática deve ser imediata:
- Variante 8A: se a última atividade do usuário foi um check-in, a aplicação web 'Checking Web' deve realizar imediatamente um check-out do usuário na localização 'Zona Mista';
- Variante 8B: se a última atividade do usuário foi um check-out, a aplicação web 'Checking Web' deve realizar imediatamente um check-in do usuário na localização 'Zona Mista';
- O campo 'Intervalo de Tempo para Zona Mista', na aba 'Cadastro' do website do administrador ('sistema\app\static\admin'), define o cooldown aplicável apenas às leituras consecutivas na própria 'Zona Mista' depois que a última atividade automática relevante também aconteceu nela;
- Se a última atividade automática realizada na própria 'Zona Mista' foi um check-in e a nova leitura continuar apontando 'Zona Mista', então a aplicação web 'Checking Web' só deve bloquear um novo check-out enquanto `tempo_decorrido < intervalo`;
- Se a última atividade automática realizada na própria 'Zona Mista' foi um check-out e a nova leitura continuar apontando 'Zona Mista', então a aplicação web 'Checking Web' só deve bloquear um novo check-in enquanto `tempo_decorrido < intervalo`;
- Quando `tempo_decorrido >= intervalo`, a aplicação web 'Checking Web' volta a permitir a alternância automática na própria 'Zona Mista', mesmo que a localização atual continue sendo 'Zona Mista';
- Exceção imediata após check-in em 'Zona Mista': se o usuário for localizado na 'Zona de CheckOut' ou em um ponto mais distante de qualquer área cadastrada na API do que a distância definida na tabela 'Distância mínima para check-out automático' para o projeto em que o usuário está alocado, desconsiderando a 'Zona de CheckOut', então a aplicação web 'Checking Web' deve realizar o check-out do usuário imediatamente, sem aguardar o cooldown da 'Zona Mista';
- Exceção imediata após check-out em 'Zona Mista': se o usuário for localizado em qualquer outra localização cadastrada na API, exceto 'Zona de CheckOut' e 'Zona Mista', ou se o usuário não estiver em nenhuma localização cadastrada, mas ainda estiver a uma distância menor ou igual à definida na tabela 'Distância mínima para check-out automático' para o projeto em que o usuário está alocado, desconsiderando a 'Zona de CheckOut', então a aplicação web 'Checking Web' deve realizar imediatamente um novo check-in do usuário. Neste caso, o cooldown configurado para a 'Zona Mista' deve ser descartado;
- Ou seja, a repetição consecutiva da 'Zona Mista' só bloqueia uma nova alternância automática enquanto `tempo_decorrido < intervalo`, e a alternância volta a ser permitida quando `tempo_decorrido >= intervalo`.

Situação 9:
- O usuário carrega a aplicação web 'Checking Web', ou o usuário pressiona 'Refresh' para atualizar o link da aplicação web 'Checking Web', ou o usuário traz o navegador para primeiro plano com a URL da aplicação web 'Checking Web' aberta, ou o usuário alterna para a aba onde a aplicação web 'Checking Web' está aberta;
- O usuário já está cadastrado no sistema, com senha. Quando abre a aplicação web 'Checking Web', o usuário é autenticado com sucesso.
- A checkbox 'Atividades Automáticas' está DESABILITADA. Não importa se a localização do usuário está com permissão total de compartilhamento com a aplicação web 'Checking Web', ou se a permissão foi negada;
- A aplicação web 'Checking Web' atualiza a localização do usuário (isto sempre deve ocorrer) se houver permissão para isso. Se não houver, apenas mostre a mensagem 'Permissão negada' como já está implementado;
- O usuário seleciona 'check-in' ou 'check-out';
- O usuário seleciona 'Normal' ou 'Retroativo';
- A dropdown box 'Local' deve estar disponível sempre que a checkbox 'Atividades Automáticas' estiver desabilitada. O usuário então seleciona o local onde deseja realizar a atividade.
- O usuário clica em 'Registrar';
- A aplicação web 'Checking Web' deve seguir o fluxo normal existente e realizar a atividade conforme as seleções do usuário.


OBSERVAÇÕES GERAIS (comportamento do app Kotlin — mudanças "A", "C" e "E"):

- Gatilho de primeiro plano (abertura/foreground): abrir o app ou trazê-lo para primeiro plano, com 'Atividades Automáticas' habilitada e usuário autenticado, dispara a avaliação automática (o motor decide check-in OU check-out conforme as situações acima). O mesmo vale para o geofencing e para a verificação periódica de 15 em 15 minutos. NÃO há check-in periódico "às cegas": a verificação de 15 em 15 minutos sempre confere a localização e mantém o "skip-if-unchanged".

- Check-in apenas por mudança de localização: o check-in automático só ocorre quando a localização resolvida é DIFERENTE da localização do último check-in. Mesma localização → nenhuma ação. Esta regra (Situações 4 e 6) é o que ELIMINA o check-in duplicado — NÃO existe regra de "deduplicação por janela de 10 minutos"; a duplicação é evitada na raiz pela exigência de mudança de localização.

- FORMS por projeto: no primeiro check-in do dia e em cada check-out, o FORMS é preenchido e enviado UMA VEZ POR PROJETO em que o usuário está cadastrado (respeitando o 'forms habilitado' de cada projeto). Ex.: usuário nos projetos P80 e P83 → duas submissões. Antes: apenas um projeto. O gatilho (primeiro check-in do dia / check-out) permanece inalterado; apenas o número de submissões é multiplicado por projeto. Usuário de projeto único → exatamente uma submissão, como antes.

- Invariantes de check-out (PRESERVADAS, inalteradas): o check-out automático ocorre em todos os casos descritos (Zona de CheckOut, distância além do limite, alternância da 'Zona Mista'); nunca há dois check-outs consecutivos; após um check-out, a próxima atividade automática é sempre um check-in. As regras de check-out por distância / 'Zona de CheckOut' e a alternância da 'Zona Mista' não foram alteradas.

---