# Text to ER

Aplicação web que transforma requisitos em português em modelos conceituais de entidades e relacionamentos. Gere e visualize o diagrama, consulte o esquema em JSON e o relatório de validação. 

![Demonstração do Text to ER](docs/demo.png)

## Rodar a aplicação

Pré-requisitos para estes comandos: Python 3.13 e Node.js 22. Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ./backend[llm]
npm --prefix frontend ci
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

No macOS ou Linux, ative o ambiente com `source .venv/bin/activate`. Se `backend/.env` ainda não existir, crie-o com `cp backend/.env.example backend/.env`.

Em `backend/.env`, defina `MODEL` com o prefixo do provedor (por exemplo, `openai/<modelo>` ou `gemini/<modelo>`) e `API_KEY`. Se o arquivo já existir, edite-o e remova a configuração antiga `MODE`. A chave fica no backend.

Com o ambiente virtual ativo, inicie o backend:

```powershell
cd backend
python -m uvicorn app.main:app --env-file .env
```
Em outro terminal aberto na raiz, execute `npm --prefix frontend run dev`.

Abra a [aplicação](http://127.0.0.1:5173), edite os requisitos e escolha **Direta** ou **Com agentes** antes de clicar em **Gerar diagrama**

A validação estrutural não mede fidelidade ao requisito. O escopo é modelagem conceitual, com revisão humana das entidades e cardinalidades.

## Verificações

```powershell
python -m pip install -e ./backend[dev]
cd backend
python -m pytest
python -m ruff check .
python -m mypy
cd ../frontend
npm test
npm run build
```