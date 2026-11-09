# Text to ER

Transforma requisitos em português em um diagrama conceitual de entidades e relacionamentos. A aplicação mostra o diagrama, o JSON e o relatório de validação, além de guardar as últimas gerações em SQLite.

![Demonstração do Text to ER](docs/demo.png)

## Rodar a demonstração

Pré-requisitos para estes comandos: Python 3.13 e Node.js 22. Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ./backend
npm --prefix frontend ci
```

No macOS ou Linux, ative o ambiente com `source .venv/bin/activate`.

Em um terminal com o ambiente virtual ativo, inicie o backend:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```
Em outro terminal aberto na raiz, execute `npm --prefix frontend run dev`.

Abra a [aplicação](http://127.0.0.1:5173) e clique em **Gerar diagrama**. O modo padrão usa um exemplo fixo de clientes e pedidos e funciona sem chave de API. Um cliente pode ter zero ou muitos pedidos, e cada pedido pertence a um único cliente. A [documentação interativa da API](http://127.0.0.1:8000/docs) também fica disponível.

## Gerar a partir de requisitos próprios

Com o ambiente virtual ativo, instale o suporte a LLM e prepare a configuração local. Se `backend/.env` já existir, edite o arquivo existente.

```powershell
python -m pip install -e './backend[llm]'
Copy-Item backend/.env.example backend/.env
```

Em `backend/.env`, defina `MODE=llm`, `MODEL` com o prefixo do provedor (por exemplo, `openai/<modelo>` ou `gemini/<modelo>`) e `API_KEY`. A chave fica no backend. Reinicie o backend com:

```powershell
cd backend
python -m uvicorn app.main:app --env-file .env
```

Confirme que a interface mostra **LLM direta**. Tente “Uma loja cadastra produtos. Cada produto pertence a uma categoria, e uma categoria pode agrupar vários produtos.” Compare o diagrama e as suposições com o texto original. As chamadas usam a cota do provedor. Use requisitos fictícios na demonstração, pois o histórico local guarda o texto enviado.

## Como funciona

1. O FastAPI entrega o requisito ao serviço de geração. O adaptador LiteLLM faz uma chamada e solicita uma saída JSON estruturada.
2. O Pydantic verifica o formato. Regras em Python conferem identificadores, nomes duplicados e referências entre entidades. Saídas fora do contrato são rejeitadas. Esquemas legíveis com erros de integridade ficam disponíveis no histórico junto com o relatório.
3. O React Flow renderiza o esquema. O resultado inclui suposições e ambiguidades para revisão humana.

A validação estrutural não mede fidelidade ao requisito. O escopo é modelagem conceitual, com revisão humana das entidades e cardinalidades. A aplicação não gera nem executa SQL a partir do modelo. Veja os [pontos de entrada do código](docs/architecture.md).

Usei o Codex para apoiar o planejamento, a implementação e as verificações. Os testes simulam respostas do provedor e verificam o comportamento do pipeline. A qualidade semântica da geração ainda precisa de avaliação com casos de referência.

## Verificações

```powershell
python -m pip install -e './backend[dev]'
cd backend
python -m pytest
python -m ruff check .
python -m mypy
cd ../frontend
npm test
npm run build
```

A CI executa essas verificações sem credenciais. Para incluir os testes de transporte HTTP simulado do SDK, instale também o extra `llm`. Para verificar a aplicação no Chromium, rode `npx playwright install chromium` e `npm run test:e2e` em `frontend`, com o ambiente virtual ativo e as portas 5173 e 8000 livres.
