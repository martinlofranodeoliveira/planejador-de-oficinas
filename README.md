# Planejador de oficinas

Uma biblioteca Python e uma CLI offline para associações, escolas e centros
culturais verificarem se oficinas cabem nas salas e horários disponíveis.
Considera capacidade, equipamentos, bloqueios, instrutores e grupos em conjunto.
Todos os exemplos deste projeto são fictícios.

O resultado é a primeira solução viável em uma ordem determinística. Não há
otimização de horários, reservas reais, persistência, serviço web ou integração
com calendários. A busca pode terminar sem resposta quando alcança seu limite.
Isso é diferente de listar horários livres: duas oficinas também podem disputar
um instrutor ou grupo mesmo em salas diferentes.

## Uso

Python 3.11 ou superior, sem dependências de execução. Na raiz do repositório:

```sh
python -m planejador_oficinas examples/viavel.json
python -m planejador_oficinas examples/inviavel.json
python -m planejador_oficinas examples/busca-limitada.json --max-nodes 1
python -m unittest discover -s tests -v
```

Para instalar em um ambiente Python local, use `python -m pip install .`.
O comando instalado é `planejador-de-oficinas INPUT.json [--max-nodes N]`.
O empacotamento usa setuptools; o programa em execução usa somente a biblioteca
padrão. Nenhum serviço, chave ou acesso à rede faz parte do planejamento.

```python
from planejador_oficinas import plan, InputError

document = {
    "slots": 2,
    "rooms": [{"id": "sala_a", "capacity": 12}],
    "workshops": [
        {"id": "leitura", "duration": 1, "attendees": 6}
    ],
}
result = plan(document, max_nodes=20000)
assert result == {
    "status": "scheduled",
    "assignments": [{"workshop": "leitura", "room": "sala_a", "start": 0, "end": 1}],
    "stats": {"nodes": 1, "limit": 20000},
}
```

## Contrato da API

`plan(document: dict, *, max_nodes: int = 20000) -> dict` não modifica a entrada,
não retém estado entre chamadas e retorna novos contêineres. `InputError` é uma
subclasse pública de `ValueError`, também disponível em `planejador_oficinas.core`.
Entradas inválidas levantam `InputError` com mensagem fixa, sem valores de entrada.
Não há leitura de arquivos, ambiente, rede, relógio, aleatoriedade ou processos
dentro do núcleo. Não há callbacks fornecidos pelo chamador.

Objetos e listas têm de ser os tipos built-in `dict` e `list`; números inteiros
são exatamente `int`, nunca `bool` ou `float`. IDs são exatamente `str` ASCII e
obedecem `[a-zA-Z0-9_-]{1,48}`. A ordenação dos IDs é a ordenação lexicográfica
normal do Python, sensível a maiúsculas. Campos desconhecidos, campos obrigatórios
ausentes, tipos inválidos, duplicatas e valores fora dos limites são erros.

O objeto raiz possui exatamente os campos obrigatórios `slots`, `rooms` e
`workshops`:

| Campo | Regra |
| --- | --- |
| `slots` | inteiro de 1 a 48; índices válidos de 0 a `slots - 1` |
| `rooms` | lista de 1 a 8 salas com IDs únicos |
| `workshops` | lista de 0 a 12 oficinas com IDs únicos |
| `max_nodes` | argumento nomeado inteiro de 1 a 200000; padrão 20000 |

Cada sala tem campos obrigatórios `id` e `capacity` (inteiro 1..100000), e pode
ter `resources` (lista de até 32 IDs distintos, padrão `[]`) e `blocked`
(lista de índices de slots distintos em 0..`slots-1`, padrão `[]`, até 48).

Cada oficina tem campos obrigatórios `id`, `duration` (inteiro 1..`slots`) e
`attendees` (inteiro 1..100000). Campos opcionais:

| Campo | Regra e padrão |
| --- | --- |
| `resources` | até 32 IDs distintos exigidos na sala; padrão `[]` |
| `instructors` | até 32 IDs distintos; padrão `[]` |
| `groups` | até 32 IDs distintos; padrão `[]` |
| `allowed_starts` | até 48 inteiros distintos em 0..`slots-duration`; ausente permite todos, `[]` não permite nenhum |
| `allowed_rooms` | até 8 IDs distintos de salas existentes; ausente permite todas, `[]` não permite nenhuma |

Os namespaces de IDs de recursos, instrutores e grupos são independentes. IDs de
salas e oficinas só precisam ser únicos dentro de sua própria lista. A ordem das
listas de entrada não altera a ordem da busca. Intervalos são `[start, end)`:
oficinas adjacentes podem compartilhar sala, instrutor ou grupo.

## Busca e contagem exatas

1. Ordene as salas e oficinas por ID. Para cada oficina, forme os candidatos
   `(start, room)` que atendem às restrições estáticas: horários e salas
   permitidos, capacidade, recursos, duração e ausência de slots bloqueados.
   Ordene os candidatos por `start` crescente e depois ID da sala.
2. Fixe a ordem de atribuição das oficinas por quantidade de candidatos crescente
   e depois ID da oficina. Essa ordem é estática, sem reordenar durante a busca.
3. Faça busca em profundidade nessa ordem. Antes de tentar cada candidato,
   incremente `nodes` uma vez, inclusive se ele conflitar com uma atribuição
   anterior. Há conflito se intervalos se sobrepõem e a sala coincide ou existe
   instrutor ou grupo em comum. Recursos são requisitos da sala, não objetos
   compartilhados entre salas.
4. Retorne a primeira atribuição completa. Ao esgotar todas as alternativas,
   retorne `unsatisfiable`. Antes de tentar outro candidato, se `nodes` já for
   `max_nodes`, retorne `budget_exhausted`, exceto se uma solução ou o esgotamento
   completo já estiverem provados. Não transforme busca interrompida em
   inviabilidade. Uma oficina sem candidatos comprova inviabilidade com zero nós;
   lista vazia de oficinas é solução com zero nós.

## Resultado e erros

O resultado tem exatamente `status`, `assignments` e `stats`. `status` é
`scheduled`, `unsatisfiable` ou `budget_exhausted`. `stats` contém exatamente
`nodes` (tentativas de candidato) e `limit` (o argumento `max_nodes`).

Em uma solução, `assignments` está ordenado por ID da oficina. Cada item tem
exatamente `workshop`, `room`, `start` e `end`, com `end = start + duration`.
Nos outros dois resultados, `assignments` é `[]`; não há solução parcial.
Todos os contadores são inteiros, nunca booleanos. `unsatisfiable` só afirma
inviabilidade para a entrada finita fornecida e a busca documentada.

A CLI aceita `INPUT.json [--max-nodes N]`, ou `--help`/`-h`. `N` usa dígitos ASCII,
sem sinal ou zeros iniciais, em 1..200000. A entrada é UTF-8 estrito, até 1048576
bytes inclusive; chaves JSON duplicadas e números não finitos são recusados.
A CLI lê no máximo 1048577 bytes do único arquivo indicado. Não busca URLs,
não percorre diretórios e não aplica configuração do ambiente. Um caminho local
explicitamente fornecido pode apontar para um symlink; não há recursão.

Resultados válidos produzem uma linha JSON em stdout e nada em stderr. Os códigos
de saída são `0` para solução, `1` para inviabilidade, `3` para limite de busca e
`2` para entrada, argumentos, leitura ou execução inválida. Erros produzem somente
`INVALID_INPUT` em stderr, sem dados de entrada, caminhos ou traceback; stdout
fica vazio antes da tentativa de emissão do resultado. `--help` imprime somente
a linha de uso e não lê a entrada.

Os exemplos `viavel.json`, `inviavel.json` e `busca-limitada.json --max-nodes 1`
demonstram os três resultados. O primeiro aloca desenho no slot 0 e leitura no
slot 1; o segundo tem capacidade insuficiente; o terceiro interrompe a busca
por conflito entre instrutores sem afirmar inviabilidade.

## Desenvolvimento e limites

`python scripts/checks-offline.py` executa testes públicos numa cópia somente
leitura, sem rede, diretório pessoal, credenciais ou capacidades Linux. Exige
Linux, Bubblewrap e util-linux. O mantenedor executa um oráculo independente
separado; esse oráculo não integra o pacote nem a entrada do gerador.

O limite de nós não limita diretamente a construção dos candidatos. Os limites
de salas, oficinas e slots tornam essa etapa finita. Não há promessa de ótimo,
de tempo máximo, de adequação de uma sala real ou de conformidade institucional.

Licença MIT. Consulte CONTRIBUTING.md e SECURITY.md.
