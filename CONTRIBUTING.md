# Como contribuir

Use apenas dados fictícios nos exemplos e testes. Preserve o contrato público
do README: ordenação, contagem de nós, limites, erros e ausência de efeitos.

Execute `python -m unittest discover -s tests -v`. Em Linux com Bubblewrap e
util-linux disponíveis, execute também `python scripts/checks-offline.py`.
Esse segundo comando testa em fonte somente leitura e sem rede ou diretório pessoal.
As verificações independentes do mantenedor são executadas separadamente.

Inclua um caso que reproduza o comportamento antes de propor uma correção.
Não envie informações pessoais, credenciais ou agendas de terceiros.
