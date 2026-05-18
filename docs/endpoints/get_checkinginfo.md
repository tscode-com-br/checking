# Endpoint `checkinginfo` — Documentação de Integração

## Visão Geral

O endpoint `checkinginfo` fornece, em tempo real, o status de presença de todos os colaboradores ativos no sistema Checking. A resposta retorna os usuários atualmente registrados em **check-in** ou **check-out** — ou seja, aqueles que realizaram sua última atividade dentro da janela de atividade considerada válida pelo sistema.

| Atributo               | Valor                                |
|------------------------|--------------------------------------|
| **Método**             | `GET`                                |
| **URL**                | `https://api.checking.tscode.com.br/api/partner/checkinginfo` |
| **Autenticação**       | Chave secreta via header `X-API-Key` |
| **Formato de resposta**| `application/json`                   |
| **Versão**             | 1.0                                  |

---

## Autenticação

Toda requisição deve incluir o header `X-API-Key` contendo a chave secreta associada ao endpoint `checkinginfo`. Essa chave é gerenciada pelo administrador do sistema na aba **Cadastro → Endpoints** do painel administrativo.

```
X-API-Key: <sua_chave_secreta_de_32_caracteres>
```

> **Atenção:** A chave secreta deve ser mantida em sigilo. Nunca a exponha em código-fonte público, logs de aplicação ou variáveis de ambiente sem proteção adequada. Caso a chave seja comprometida, o administrador pode gerar uma nova chave pela interface administrativa — a chave anterior é imediatamente invalidada.

---

## Requisição

### URL completa

```
GET https://api.checking.tscode.com.br/api/partner/checkinginfo
```

### Headers obrigatórios

| Header         | Valor                                       |
|----------------|---------------------------------------------|
| `X-API-Key`    | Chave secreta do endpoint `checkinginfo`    |
| `Accept`       | `application/json` *(recomendado)*          |

### Parâmetros

Este endpoint **não aceita** parâmetros de query string ou corpo na requisição.

---

## Resposta

### Estrutura do JSON de resposta

```json
{
  "ok": true,
  "total": 3,
  "entries": [
    {
      "nome": "Ana Paula Ferreira",
      "chave": "APF1",
      "projeto": "PROJETO ALFA",
      "atividade": "check-in",
      "horario": "2026-05-12T08:14:32+08:00",
      "local": "co83",
      "assiduidade": "Normal"
    },
    {
      "nome": "Carlos Eduardo Lima",
      "chave": "CEL2",
      "projeto": "PROJETO BETA",
      "atividade": "check-out",
      "horario": "2026-05-12T17:02:05+08:00",
      "local": "un80",
      "assiduidade": "Retroativo"
    },
    {
      "nome": "Maria José Santos",
      "chave": "MJS3",
      "projeto": "PROJETO ALFA",
      "atividade": "check-in",
      "horario": "2026-05-12T07:58:11+08:00",
      "local": null,
      "assiduidade": "Normal"
    }
  ]
}
```

### Campos do objeto raiz

| Campo     | Tipo      | Descrição                                                                 |
|-----------|-----------|---------------------------------------------------------------------------|
| `ok`      | `boolean` | Sempre `true` quando a requisição é bem-sucedida.                         |
| `total`   | `integer` | Quantidade total de entradas retornadas no array `entries`.               |
| `entries` | `array`   | Lista de registros de presença de usuários ativos.                        |

### Campos de cada entrada (`entries[*]`)

| Campo        | Tipo                        | Descrição                                                                                   |
|--------------|-----------------------------|---------------------------------------------------------------------------------------------|
| `nome`       | `string`                    | Nome completo do usuário.                                                                   |
| `chave`      | `string`                    | Identificador único do usuário no sistema (código de 4 caracteres).                        |
| `projeto`    | `string`                    | Nome do projeto ao qual o usuário está vinculado.                                           |
| `atividade`  | `"check-in"` \| `"check-out"` | Última atividade registrada pelo usuário.                                                |
| `horario`    | `string` (ISO 8601) \| `null` | Data e hora da última atividade, com fuso horário. Pode ser `null` em casos excepcionais. |
| `local`      | `string` \| `null`          | Código de localização onde a atividade foi registrada. Pode ser `null`.                    |
| `assiduidade`| `"Normal"` \| `"Retroativo"` | Indica se o registro foi feito no prazo esperado (`"Normal"`) ou fora do prazo (`"Retroativo"`). |

### Ordenação

As entradas são retornadas em **ordem decrescente de horário** — as atividades mais recentes aparecem primeiro.

### Usuários inativos

Usuários cuja última atividade ultrapassa a janela de inatividade configurada no sistema **não são incluídos** na resposta. Apenas atividades recentes e válidas são retornadas.

---

## Códigos de status HTTP

| Código | Significado                                                                          |
|--------|--------------------------------------------------------------------------------------|
| `200`  | Sucesso. O body contém o JSON de resposta.                                           |
| `403`  | Chave inválida ou ausente. Verifique o header `X-API-Key`.                           |
| `422`  | Requisição malformada (ex.: header `X-API-Key` não informado).                       |
| `500`  | Erro interno do servidor. Em caso de persistência, entre em contato com o suporte.   |

### Exemplo de erro 403

```json
{
  "detail": "Chave de acesso invalida."
}
```

### Exemplo de erro 422 (header ausente)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "X-API-Key"],
      "msg": "Field required"
    }
  ]
}
```

---

## Exemplos de Implementação

### Python (requests)

```python
import requests

API_URL = "https://api.checking.tscode.com.br/api/partner/checkinginfo"
API_KEY = "sua_chave_secreta_aqui"  # Nunca inclua em código-fonte público

def get_checking_info():
    response = requests.get(
        API_URL,
        headers={"X-API-Key": API_KEY},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    data = get_checking_info()
    print(f"Total de usuários ativos: {data['total']}")
    for entry in data["entries"]:
        print(
            f"  {entry['nome']} ({entry['chave']}) — "
            f"{entry['atividade']} em {entry['horario']} — "
            f"Assiduidade: {entry['assiduidade']}"
        )
```

---

### JavaScript / Node.js (fetch nativo)

```javascript
const API_URL = "https://api.checking.tscode.com.br/api/partner/checkinginfo";
const API_KEY = process.env.CHECKING_API_KEY; // Leia a chave de uma variável de ambiente

async function getCheckingInfo() {
  const response = await fetch(API_URL, {
    method: "GET",
    headers: {
      "X-API-Key": API_KEY,
      "Accept": "application/json",
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Erro ${response.status}: ${body}`);
  }

  return response.json();
}

getCheckingInfo()
  .then((data) => {
    console.log(`Total de usuários ativos: ${data.total}`);
    data.entries.forEach((entry) => {
      console.log(
        `  ${entry.nome} (${entry.chave}) — ${entry.atividade} em ${entry.horario}`
      );
    });
  })
  .catch(console.error);
```

---

### PHP (cURL)

```php
<?php

$apiUrl = 'https://api.checking.tscode.com.br/api/partner/checkinginfo';
$apiKey = getenv('CHECKING_API_KEY'); // Leia a chave de uma variável de ambiente

$ch = curl_init($apiUrl);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => [
        "X-API-Key: {$apiKey}",
        "Accept: application/json",
    ],
    CURLOPT_TIMEOUT        => 15,
    CURLOPT_SSL_VERIFYPEER => true,
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200) {
    throw new RuntimeException("Erro HTTP {$httpCode}: {$response}");
}

$data = json_decode($response, true);
echo "Total de usuários ativos: {$data['total']}\n";
foreach ($data['entries'] as $entry) {
    echo "  {$entry['nome']} ({$entry['chave']}) — {$entry['atividade']} em {$entry['horario']}\n";
}
```

---

### C# (.NET HttpClient)

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Threading.Tasks;

class CheckingInfoClient
{
    private static readonly HttpClient _httpClient = new HttpClient
    {
        BaseAddress = new Uri("https://api.checking.tscode.com.br"),
        Timeout = TimeSpan.FromSeconds(15),
    };

    public static async Task Main()
    {
        string apiKey = Environment.GetEnvironmentVariable("CHECKING_API_KEY")
            ?? throw new InvalidOperationException("CHECKING_API_KEY não definida.");

        _httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        _httpClient.DefaultRequestHeaders.Accept.Add(
            new MediaTypeWithQualityHeaderValue("application/json")
        );

        HttpResponseMessage response = await _httpClient.GetAsync("/api/partner/checkinginfo");
        response.EnsureSuccessStatusCode();

        string json = await response.Content.ReadAsStringAsync();
        using JsonDocument doc = JsonDocument.Parse(json);
        JsonElement root = doc.RootElement;

        int total = root.GetProperty("total").GetInt32();
        Console.WriteLine($"Total de usuários ativos: {total}");

        foreach (JsonElement entry in root.GetProperty("entries").EnumerateArray())
        {
            string nome      = entry.GetProperty("nome").GetString()!;
            string chave     = entry.GetProperty("chave").GetString()!;
            string atividade = entry.GetProperty("atividade").GetString()!;
            string horario   = entry.GetProperty("horario").GetString() ?? "-";
            Console.WriteLine($"  {nome} ({chave}) — {atividade} em {horario}");
        }
    }
}
```

---

### Java (HttpClient — Java 11+)

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class CheckingInfoExample {

    private static final String API_URL =
        "https://api.checking.tscode.com.br/api/partner/checkinginfo";

    public static void main(String[] args) throws Exception {
        String apiKey = System.getenv("CHECKING_API_KEY");
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException("Variável de ambiente CHECKING_API_KEY não definida.");
        }

        HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_URL))
            .header("X-API-Key", apiKey)
            .header("Accept", "application/json")
            .GET()
            .build();

        HttpResponse<String> response =
            client.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new RuntimeException("Erro HTTP " + response.statusCode() + ": " + response.body());
        }

        // Processar o JSON com a biblioteca de sua preferência (Gson, Jackson, etc.)
        System.out.println("Resposta recebida:");
        System.out.println(response.body());
    }
}
```

---

### cURL (linha de comando)

```bash
curl -s \
  -H "X-API-Key: sua_chave_secreta_aqui" \
  -H "Accept: application/json" \
  https://api.checking.tscode.com.br/api/partner/checkinginfo | python3 -m json.tool
```

---

## Gerenciamento da Chave Secreta

### Como visualizar a chave atual

1. Acesse o painel administrativo do Checking.
2. Navegue até a aba **Cadastro**.
3. Localize a seção **Endpoints**.
4. A chave aparece parcialmente mascarada na coluna **Chave Secreta** (os primeiros 6 e últimos 4 caracteres são exibidos).

> Para ver a chave completa, é necessário consultar o banco de dados diretamente ou gerar uma nova chave via botão **Alterar** e anotar o valor exibido imediatamente após a geração.

### Como alterar a chave secreta

1. Acesse o painel administrativo do Checking.
2. Navegue até **Cadastro → Endpoints**.
3. Na linha do endpoint `checkinginfo`, clique no botão **Alterar**.
4. Uma nova chave de 32 caracteres hexadecimais é gerada imediatamente e salva no banco de dados.
5. **A chave anterior é invalidada imediatamente.** Atualize a chave em todos os sistemas integrados antes de clicar em **Alterar**.

---

## Boas Práticas de Segurança

1. **Armazene a chave como variável de ambiente** — nunca em código-fonte ou arquivos de configuração versionados.
2. **Use HTTPS** — todas as requisições devem usar `https://`. Requisições via `http://` não são aceitas em produção.
3. **Implemente timeout** — configure um timeout de no mínimo 10 segundos para evitar que falhas de rede bloqueiem sua aplicação.
4. **Trate erros graciosamente** — verifique sempre o código HTTP da resposta antes de processar o JSON.
5. **Não exponha a chave em logs** — certifique-se de que o header `X-API-Key` não seja registrado nos logs da sua aplicação.
6. **Rotacione a chave periodicamente** — recomendamos trocar a chave a cada 90 dias ou imediatamente após qualquer suspeita de comprometimento.

---

## Referência Rápida

```
GET https://api.checking.tscode.com.br/api/partner/checkinginfo
Header: X-API-Key: <chave_de_32_chars>

200 OK → { "ok": true, "total": N, "entries": [...] }
403    → { "detail": "Chave de acesso invalida." }
422    → { "detail": [...] }   # Header X-API-Key ausente
```

---

## Suporte

Em caso de dúvidas ou problemas na integração, entre em contato com a equipe técnica do Checking.
