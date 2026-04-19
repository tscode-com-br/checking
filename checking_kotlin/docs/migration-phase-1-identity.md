# Migracao Kotlin - Fase 1 Identidade

Atualizado em: 2026-04-19

## Decisao

O app Kotlin continuara como aplicativo Android separado do app Flutter.

Identidade final desta fase:

- applicationId: `com.br.checkingnative`
- namespace: `com.br.checkingnative`
- package Flutter de referencia: `com.br.checking`
- modo de coexistencia: app separado
- politica de migracao: onboarding manual

## Implicacoes

O app Kotlin nao sera instalado como atualizacao direta do app Flutter.

Consequencias praticas:

- nao ha troca de `applicationId`
- nao ha exigencia de usar a mesma assinatura do Flutter para upgrade
- o Android mantera sandboxes separados para Flutter e Kotlin
- dados internos do Flutter nao serao importados automaticamente
- a chave do usuario, permissoes e configuracoes operacionais deverao ser refeitas no Kotlin
- o catalogo de localizacoes devera ser resincronizado pela API no app Kotlin

## O Que Foi Conferido

Configuracao atual em `app/build.gradle.kts`:

```kotlin
namespace = "com.br.checkingnative"
applicationId = "com.br.checkingnative"
versionCode = 1
versionName = "0.1.0"
```

Esta configuracao esta alinhada com a decisao da fase.

## Migracao Manual

Como o app Kotlin e separado, a migracao automatica dos dados internos do app
Flutter fica bloqueada pelo sandbox Android.

Fluxo esperado para o usuario/operador:

1. instalar o app Kotlin separado
2. informar novamente a chave Petrobras
3. conceder permissoes Android novamente
4. habilitar busca por localizacao/automacao novamente, quando desejado
5. sincronizar historico e catalogo pela API

Dados que nao devem ser prometidos como importacao automatica:

- SharedPreferences do Flutter
- `flutter_secure_storage`
- banco interno `checking_locations.db` do package Flutter
- permissoes ja concedidas ao app Flutter
- estado local de automacao/background do Flutter

## Banco Local

Como o app Kotlin ficara em outro package, o arquivo `checking_locations.db`
do Flutter nao sera acessado diretamente.

O uso do mesmo nome de banco no Kotlin e aceitavel para manter o mesmo schema
logico, mas ele existira dentro do sandbox de `com.br.checkingnative`.

Decisao para esta fase:

- manter o nome `checking_locations.db`
- manter a tabela `locations`
- tratar o catalogo como cache resincronizavel pela API
- nao criar migracao in-place do banco Flutter nesta fase

Risco remanescente:

- `fallbackToDestructiveMigration` ainda pode apagar o cache proprio do app
  Kotlin em mudancas futuras de schema. Como o catalogo vem da API, isso nao
  bloqueia a Fase 1, mas deve ser revisado antes de release.

## Shared Key

O Flutter usa secure storage com backup em preferences para permitir operacao
em background.

Decisao para esta fase:

- manter a shared key do Kotlin no proprio DataStore do app separado
- nao tentar ler a shared key do Flutter
- reavaliar armazenamento seguro e fallback de background na fase de servico
  Android/background

## Criterio De Saida

Fase 1 e considerada concluida quando:

- `applicationId` e `namespace` permanecem `com.br.checkingnative`
- documentacao registra o app Kotlin como separado
- migracao automatica do sandbox Flutter esta explicitamente fora de escopo
- onboarding manual esta descrito
- tela/bootstrap nao sugere importacao automatica como caminho esperado

Status atual:

- decisao registrada
- configuracao conferida
- onboarding manual documentado
- pronto para Fase 2
