import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg2
from psycopg2 import OperationalError

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERRO: python-dotenv não instalado. Rode: pip install python-dotenv")
    sys.exit(1)


def load_env_from_project_root() -> Path:
    """
    Garante que o .env será carregado a partir da raiz do projeto
    (mesmo se você executar o script de dentro de outra pasta).
    """
    # Diretório do arquivo atual (onde está test_pg_psycopg2.py)
    here = Path(__file__).resolve().parent

    # Procura um .env subindo a árvore (até 5 níveis)
    candidates = [here] + list(here.parents)[:5]
    for p in candidates:
        env_path = p / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
            return env_path

    # Fallback: tenta load_dotenv padrão (pode funcionar dependendo do CWD)
    load_dotenv(override=True)
    return Path("(não encontrado explicitamente)")


def mask_db_url(url: str) -> str:
    """
    Mascara user:password@ na URL pra print seguro.
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if "@" in netloc:
            # mantém apenas host:port
            hostpart = netloc.split("@", 1)[1]
            masked = f"{parsed.scheme}://***@{hostpart}{parsed.path}"
            if parsed.query:
                masked += f"?{parsed.query}"
            return masked
        return url
    except Exception:
        return "postgresql://*** (não foi possível mascarar)"


def ensure_sslmode_require(url: str) -> str:
    """
    Neon exige SSL. Garante sslmode=require na querystring.
    """
    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if qs.get("sslmode", "").lower() != "require":
        qs["sslmode"] = "require"
    new_query = urlencode(qs)
    return urlunparse(parsed._replace(query=new_query))


def normalize_psycopg2_url(url: str) -> str:
    """
    Converte esquemas SQLAlchemy -> psycopg2 e garante sslmode=require.
    """
    u = (url or "").strip()

    # Esquemas comuns vindos do SQLAlchemy
    if u.startswith("postgresql+psycopg2://"):
        u = u.replace("postgresql+psycopg2://", "postgresql://", 1)
    elif u.startswith("postgres://"):
        # algumas libs antigas usavam postgres://
        u = u.replace("postgres://", "postgresql://", 1)

    u = ensure_sslmode_require(u)
    return u


def connect_via_url(pg_url: str):
    """
    Conecta usando URL.
    """
    pg_url = normalize_psycopg2_url(pg_url)
    print("USANDO DATABASE_URL (sem senha):", mask_db_url(pg_url))
    return psycopg2.connect(pg_url)


def connect_via_envvars():
    """
    Conecta usando variáveis separadas (mais robusto, evita senha quebrar URL).
    """
    host = (os.getenv("PGHOST") or "").strip()
    dbname = (os.getenv("PGDATABASE") or os.getenv("PGDB") or "").strip()
    user = (os.getenv("PGUSER") or "").strip()
    password = os.getenv("PGPASSWORD")  # não strip aqui (às vezes a senha é sensível)
    port = (os.getenv("PGPORT") or "5432").strip()
    sslmode = (os.getenv("PGSSLMODE") or "require").strip()

    missing = [
        k
        for k, v in {
            "PGHOST": host,
            "PGDATABASE": dbname,
            "PGUSER": user,
            "PGPASSWORD": password,
        }.items()
        if not v
    ]

    print(
        "USANDO ENVVARS:",
        f"host={host or '(vazio)'}",
        f"db={dbname or '(vazio)'}",
        f"user={user or '(vazio)'}",
        f"port={port}",
        f"sslmode={sslmode}",
        sep="\n  - ",
    )

    if missing:
        raise RuntimeError(
            "Faltam variáveis para conexão via ENVVARS: "
            + ", ".join(missing)
            + "\nPreencha no .env, por exemplo:\n"
            "PGHOST=...\nPGDATABASE=...\nPGUSER=...\nPGPASSWORD=...\nPGPORT=5432\nPGSSLMODE=require\n"
        )

    # Diagnóstico sem vazar senha
    pwd_len = len(password) if password is not None else 0
    last_char = repr(password[-1:]) if password else "''"
    print(
        f"Diagnóstico senha: tamanho={pwd_len} | último_char={last_char} (se for ' ' tem espaço no fim)"
    )

    return psycopg2.connect(
        host=host,
        dbname=dbname,
        user=user,
        password=password,
        port=int(port),
        sslmode=sslmode,
    )


def main():
    env_path = load_env_from_project_root()
    print(f".env carregado de: {env_path}")

    # Preferência: se tiver PGHOST etc, usa ENVVARS (mais estável com senha)
    has_envvars = any(
        os.getenv(k) for k in ["PGHOST", "PGUSER", "PGPASSWORD", "PGDATABASE"]
    )
    url = (os.getenv("DATABASE_URL") or "").strip()

    try:
        if has_envvars:
            conn = connect_via_envvars()
        elif url:
            conn = connect_via_url(url)
        else:
            raise RuntimeError(
                "Nenhuma configuração encontrada.\n"
                "- Defina DATABASE_URL no .env, ou\n"
                "- Defina PGHOST/PGDATABASE/PGUSER/PGPASSWORD no .env."
            )

        with conn.cursor() as cur:
            cur.execute("select now(), current_user, current_database(), version();")
            row = cur.fetchone()
            print("\n✅ CONECTOU COM SUCESSO!")
            print("  - now():", row[0])
            print("  - current_user:", row[1])
            print("  - current_database:", row[2])
            print("  - version():", row[3].splitlines()[0])

        conn.close()

    except OperationalError as e:
        msg = str(e)

        print("\n❌ FALHA NA CONEXÃO (OperationalError)")
        print(msg)

        # Dicas diretas para o erro mais comum no Neon
        if "password authentication failed" in msg.lower():
            print("\n➡️ Diagnóstico: SENHA/USUÁRIO incorretos OU senha quebrando a URL.")
            print(
                "   1) Confirme no Neon se o usuário é realmente 'neondb_owner' (ou o que está na string)."
            )
            print(
                "   2) Resete/copie a senha novamente no Neon e cole no .env (sem espaços)."
            )
            print(
                "   3) Se a senha tiver caracteres especiais (@ : / # % & ?), use ENVVARS (PGPASSWORD etc)."
            )
        if "ssl" in msg.lower():
            print(
                "\n➡️ Diagnóstico: SSL obrigatório. Este script já força sslmode=require, então revise se está usando URL diferente no app."
            )
        if "could not translate host name" in msg.lower():
            print(
                "\n➡️ Diagnóstico: HOST incorreto ou DNS. Confira PGHOST/host da URL no Neon."
            )
        if "timeout" in msg.lower():
            print(
                "\n➡️ Diagnóstico: rede/firewall. Teste outra rede ou verifique se o endpoint está ativo."
            )

        raise

    except Exception as e:
        print("\n❌ ERRO:", type(e).__name__, str(e))
        raise


if __name__ == "__main__":
    main()
