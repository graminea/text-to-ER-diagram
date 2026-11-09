# Text to ER

Aplicação web que transforma requisitos em português em diagramas conceituais de entidades e relacionamentos (ER).

O projeto faz parte do meu TCC sobre o uso de LLMs para gerar e validar esquemas conceituais a partir de requisitos em linguagem natural.

![Demonstração do Text to ER](docs/demo.png)

## Rodar com Docker Compose

Com o Docker em execução, copie `backend/.env.example` para `backend/.env` se o arquivo ainda não existir. Preencha `MODEL` com o prefixo do provedor (por exemplo, `openai/<modelo>`) e `API_KEY`.

### Primeira execução

Na raiz do repositório, construa as imagens e inicie a aplicação.

```sh
docker compose up --build --wait
```

Use a geração **Direta** ou **Com agentes** no [Text to ER](http://127.0.0.1:8080).

### Desligar

```sh
docker compose down
```

O histórico de gerações do Docker é preservado.

### Rodar novamente

```sh
docker compose up
```
