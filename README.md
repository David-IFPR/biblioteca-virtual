# Acervo — Biblioteca virtual

Sistema web para uma instituição de ensino. O aluno consulta o catálogo, solicita empréstimos e acompanha as locações. Professores e administradores gerenciam o acervo, os alunos e as movimentações. A devolução só fica concluída quando a biblioteca confirma o recebimento.

## O que você precisa

- Python 3.12
- Node.js 20 ou superior
- npm

O desenvolvimento usa SQLite. Para PostgreSQL, preencha as variáveis indicadas em `.env.example`.

## Primeira execução

No PowerShell, a partir da pasta do projeto:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo
```

O comando `seed_demo` cria o acervo de demonstração e o primeiro administrador. Se o banco já tiver livros, use `seed_demo --reset` para recriar essa demonstração.

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra http://127.0.0.1:5173

A API fica em http://127.0.0.1:8000

## Contas de demonstração

| Perfil | Acesso | Senha |
| --- | --- | --- |
| Administrador | admin@acervo.escola | Admin@12345 |
| Aluna Helena Duarte | matrícula 20260001 | Aluno@12345 |
| Aluno Miguel Alves | matrícula 20260002 | Aluno@12345 |
| Aluna Lívia Ramos | matrícula 20260003 | Aluno@12345 |

## Criar outro administrador

Com o ambiente virtual ativo, na pasta `backend`:

```powershell
.\.venv\Scripts\python manage.py create_admin --email professor@acervo.escola --name "Nome do professor" --password "Senha@12345"
```

Não existe cadastro público de administrador. A área da biblioteca usa e-mail e senha. A área do aluno usa matrícula e senha.

## Recuperação de senha

O aluno informa a matrícula, ou a conta informa o e-mail, em **Recuperar senha**. Com `DJANGO_DEBUG=true`, a resposta da API inclui um código para concluir a troca na tela de redefinição. Em produção, deixe o debug desligado e configure o envio de e-mail pelas variáveis `EMAIL_BACKEND` e `DEFAULT_FROM_EMAIL`. O backend já envia a mensagem; no desenvolvimento o destino padrão é o console do Django.

## Testes

Na pasta `backend`, com o ambiente virtual ativo:

```powershell
.\.venv\Scripts\python manage.py test apps.accounts apps.catalog apps.circulation
```

## Variáveis de ambiente

Copie `.env.example` para `.env` na raiz do projeto e ajuste os valores. O Django lê esse arquivo. O frontend usa `http://127.0.0.1:8000/api` se `VITE_API_URL` não estiver definido. Para mudar a API, crie `frontend/.env` com:

```
VITE_API_URL=http://127.0.0.1:8000/api
```

## Documentação

A organização do registro técnico está em `docs/DOCUMENTACAO.md`. O PDF no formato do registro de atividade está em `docs/Documento_Registro_Biblioteca_Virtual_Acervo.pdf`.
