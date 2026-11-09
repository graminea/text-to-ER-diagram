# Arquitetura

```text
Requisitos → FastAPI → serviço → geração direta ou com agentes (LiteLLM)
                         ↓
           Pydantic → validação ER → SQLite
                         ↓
              JSON e relatório → React Flow
```

| Código | Responsabilidade |
| --- | --- |
| [entrypoints/http.py](../backend/app/entrypoints/http.py) | Rotas, códigos HTTP e mapeamento de falhas |
| [bootstrap.py](../backend/app/bootstrap.py) | Seleção de adaptadores e ciclo de vida |
| [generations/service.py](../backend/app/generations/service.py) | Coordenação da geração, validação e histórico |
| [generations/ports.py](../backend/app/generations/ports.py) | Interfaces para injetar geradores e armazenamento em testes |
| [generations/adapters/llm.py](../backend/app/generations/adapters/llm.py) | Geração direta e transporte compartilhado via LiteLLM. `OUTPUT_MODE=json_object` é uma opção explícita para modelos sem suporte ao formato padrão `json_schema` |
| [generations/adapters/agents.py](../backend/app/generations/adapters/agents.py) | Rascunho do coordenador, revisão em paralelo e geração do modelo final |
| [er/models.py](../backend/app/er/models.py) e [er/validation.py](../backend/app/er/validation.py) | Contrato conceitual e regras determinísticas |
| [generations/adapters/sqlite.py](../backend/app/generations/adapters/sqlite.py) | Histórico e leitura de registros antigos |
| [diagram.ts](../frontend/src/diagram.ts) | Conversão do esquema para nós e arestas |

O contrato representa entidades, atributos identificadores, relacionamentos binários e cardinalidades. Relacionamentos recursivos usam nomes de papéis distintos. Ambiguidades geram avisos, permitindo que a pessoa que revisa o resultado decida como resolvê-las.

O backend configura o provedor na inicialização. Falhas do provedor e respostas fora do contrato viram erros da API e ficam fora do histórico. O serviço registra modelo, versão do prompt, tempo de execução e tokens quando o provedor os informa. A rota `POST /api/validate` verifica esquemas enviados diretamente, sem chamar um gerador.

`POST /api/generations` aceita `flow: "A"` para a geração direta em uma chamada e `flow: "B"` para a geração com agentes. O padrão é `"A"`. O coordenador produz o rascunho, recebe os pareceres de coerência e cardinalidade em paralelo e finaliza o modelo. As quatro chamadas compartilham o prazo de `TIMEOUT`. Uma revisão inválida interrompe a geração. Os [papéis em Markdown](../backend/app/generations/adapters/roles/) são independentes da interface e podem ser reutilizados em outros ambientes.

O núcleo ER independe de HTTP, do banco e do SDK. O serviço usa as interfaces em `ports.py`, e a composição liga essas interfaces aos adaptadores. Os [testes de dependências](../backend/tests/test_dependencies.py) verificam as fronteiras de importação. `app.main:app` e as reexportações antigas mantêm a compatibilidade com os pontos de entrada existentes.
