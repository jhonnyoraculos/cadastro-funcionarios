from __future__ import annotations

import base64
import os
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # Local fallback when Postgres support is not installed yet.
    psycopg = None
    dict_row = None


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "funcionarios.db"
LOGO_PATH = APP_DIR / "logo-jr.png"

STATUS_OPTIONS = ["Ativo", "Afastado", "Férias", "Inativo", "Desligado"]
ESTADO_CIVIL_OPTIONS = [
    "Não informado",
    "Solteiro(a)",
    "Casado(a)",
    "União estável",
    "Divorciado(a)",
    "Viúvo(a)",
]
CONTRATO_OPTIONS = [
    "CLT",
    "Experiência",
    "Temporário",
    "Aprendiz",
    "Estágio",
    "Prestador",
    "Outro",
]
UF_OPTIONS = [
    "",
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]
PARENTESCO_OPTIONS = [
    "",
    "Cônjuge",
    "Pai",
    "Mãe",
    "Filho(a)",
    "Irmão/Irmã",
    "Avô/Avó",
    "Tio(a)",
    "Primo(a)",
    "Amigo(a)",
    "Outro",
]
VACATION_STATUS_OPTIONS = ["Programada", "Em férias", "Concluída", "Cancelada"]
LEAVE_TYPE_OPTIONS = [
    "Atestado médico",
    "Afastamento INSS",
    "Licença médica",
    "Licença maternidade",
    "Licença paternidade",
    "Acidente de trabalho",
    "Licença sem remuneração",
    "Outro",
]
LEAVE_STATUS_OPTIONS = ["Programado", "Ativo", "Encerrado", "Cancelado"]
TERMINATION_REASON_OPTIONS = [
    "Pedido de demissão",
    "Dispensa sem justa causa",
    "Dispensa com justa causa",
    "Fim de contrato",
    "Acordo",
    "Outro",
]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


st.set_page_config(
    page_title="Cadastro de Funcionários | JR Ferragens e Madeiras",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --jr-red: #c8102e;
            --jr-red-dark: #990d23;
            --jr-blue: #243f91;
            --jr-blue-soft: #edf3ff;
            --jr-navy: #071b3a;
            --jr-ink: #10213f;
            --jr-muted: #64748b;
            --jr-line: #d8e0ee;
            --jr-bg: #f5f7fb;
            --jr-surface: #ffffff;
            --jr-soft-red: #fff0f3;
            --jr-soft-green: #ecfdf3;
            --jr-green: #047857;
            --jr-warning: #a16207;
            --jr-soft-warning: #fff7ed;
        }

        .stApp {
            background: var(--jr-bg);
            color: var(--jr-ink);
        }

        .block-container {
            padding-top: 0.85rem;
            padding-bottom: 2.25rem;
            max-width: 1240px;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        #MainMenu,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stDeployButton {
            display: none !important;
            visibility: hidden !important;
        }

        section[data-testid="stSidebar"] {
            display: none !important;
        }

        [data-testid="collapsedControl"] {
            display: none !important;
        }

        h1, h2, h3, h4, h5, h6, p, label {
            letter-spacing: 0;
        }

        .jr-header {
            display: grid;
            grid-template-columns: auto 1fr auto;
            align-items: center;
            gap: 0.95rem;
            padding: 0.82rem 1rem;
            margin-bottom: 0.85rem;
            background: linear-gradient(135deg, var(--jr-navy) 0%, #12346d 63%, var(--jr-red) 100%);
            border: 1px solid rgba(16, 33, 63, 0.12);
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(7, 27, 58, 0.10);
        }

        .jr-title {
            color: #ffffff;
            font-size: clamp(1.28rem, 1.7vw, 1.72rem);
            line-height: 1.15;
            font-weight: 800;
            margin: 0;
        }

        .jr-subtitle {
            color: rgba(255, 255, 255, 0.78);
            margin: 0.16rem 0 0 0;
            font-size: 0.86rem;
        }

        .jr-kicker {
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 0.14rem;
        }

        .jr-header-actions {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 0.4rem;
        }

        .jr-header-logo {
            width: 54px;
            height: 54px;
            border-radius: 10px;
            object-fit: contain;
            background: #ffffff;
            padding: 0.18rem;
        }

        .jr-section-title {
            color: var(--jr-ink);
            font-weight: 800;
            font-size: 0.96rem;
            margin: 0.92rem 0 0.5rem 0;
            padding-left: 0.55rem;
            border-left: 3px solid var(--jr-red);
        }

        .jr-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.25rem 0.65rem;
            font-weight: 700;
            font-size: 0.75rem;
            border: 1px solid rgba(255, 255, 255, 0.20);
            color: #ffffff;
            background: rgba(255, 255, 255, 0.13);
        }

        .jr-pill-red {
            color: var(--jr-red-dark);
            border-color: rgba(200, 16, 46, 0.25);
            background: var(--jr-soft-red);
        }

        .jr-pill-green {
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.20);
            background: rgba(4, 120, 87, 0.32);
        }

        .jr-kpi-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.68rem;
            margin: 0.15rem 0 0.75rem 0;
        }

        .jr-kpi-card {
            background: #ffffff;
            border: 1px solid var(--jr-line);
            border-radius: 10px;
            padding: 0.72rem 0.82rem;
            min-height: 74px;
            box-shadow: 0 8px 20px rgba(16, 33, 63, 0.045);
        }

        .jr-kpi-label {
            color: var(--jr-muted);
            font-size: 0.75rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .jr-kpi-value {
            color: var(--jr-ink);
            font-size: 1.45rem;
            font-weight: 850;
            line-height: 1.1;
            margin-top: 0.35rem;
        }

        .jr-notice {
            background: #fff8e8;
            color: #7c4a03;
            border: 1px solid #f4db9b;
            border-radius: 9px;
            padding: 0.65rem 0.8rem;
            margin: 0.2rem 0 0.85rem 0;
            font-size: 0.9rem;
            font-weight: 650;
        }

        .jr-sidebar-title {
            color: var(--jr-ink);
            font-size: 1.02rem;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 0.35rem;
        }

        .jr-sidebar-subtitle {
            color: var(--jr-muted);
            font-size: 0.84rem;
            margin-bottom: 0.5rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.3rem;
            background: #ffffff;
            border: 1px solid var(--jr-line);
            border-radius: 10px;
            padding: 0.24rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 8px 20px rgba(16, 33, 63, 0.045);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: var(--jr-muted);
            font-weight: 700;
            min-height: 2.2rem;
            padding: 0 0.95rem;
        }

        .stTabs [aria-selected="true"] {
            background: var(--jr-red);
            color: #ffffff;
        }

        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stAlert"]) {
            gap: 0.55rem;
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
            border: 1px solid var(--jr-line);
        }

        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid var(--jr-line);
            border-radius: 10px;
            padding: 0.9rem 1rem 1rem 1rem;
            box-shadow: 0 10px 24px rgba(16, 33, 63, 0.045);
        }

        div[data-testid="stForm"] [data-testid="stVerticalBlock"] {
            gap: 0.42rem;
        }

        div.stButton > button[kind="primary"],
        div.stDownloadButton > button[kind="primary"] {
            background: var(--jr-red);
            border-color: var(--jr-red);
            color: #ffffff;
            font-weight: 700;
            border-radius: 8px;
            min-height: 2.55rem;
        }

        div.stButton > button[kind="primary"]:hover,
        div.stDownloadButton > button[kind="primary"]:hover {
            background: var(--jr-red-dark);
            border-color: var(--jr-red-dark);
            color: #ffffff;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--jr-line);
            border-radius: 8px;
            padding: 0.72rem 0.82rem;
        }

        div[data-testid="stMetric"] label {
            color: var(--jr-muted);
            font-weight: 700;
        }

        div[data-testid="stMetricValue"] {
            color: var(--jr-ink);
            font-weight: 800;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--jr-line);
            border-radius: 8px;
            overflow: hidden;
        }

        [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1.5px solid #9fb0ca !important;
            border-radius: 7px !important;
            box-shadow: inset 0 0 0 1px rgba(16, 33, 63, 0.03) !important;
        }

        [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-baseweb="select"] > div {
            min-height: 2.45rem;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTextArea"] textarea {
            color: var(--jr-ink) !important;
            caret-color: var(--jr-red);
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stDateInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #6f7f99 !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
        [data-testid="stNumberInput"] [data-baseweb="input"]:focus-within,
        [data-testid="stDateInput"] [data-baseweb="input"]:focus-within,
        [data-testid="stTextArea"] textarea:focus,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--jr-red) !important;
            box-shadow: 0 0 0 2px rgba(200, 16, 46, 0.16) !important;
        }

        hr {
            border-color: var(--jr-line);
        }

        @media (max-width: 760px) {
            .jr-header {
                grid-template-columns: 1fr;
            }

            .jr-header-actions {
                justify-content: flex-start;
            }

            .jr-header-logo {
                width: 64px;
                height: 64px;
            }

            .jr-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (min-width: 761px) and (max-width: 1100px) {
            .jr-kpi-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url
    try:
        return str(st.secrets.get("DATABASE_URL", "")).strip()
    except Exception:
        return ""


def using_postgres() -> bool:
    return bool(get_database_url())


def convert_sql(sql: str) -> str:
    if not using_postgres():
        return sql
    converted = re.sub(r"\s+COLLATE\s+NOCASE", "", sql, flags=re.IGNORECASE)
    converted = re.sub(r"CHAR\s*\(\s*10\s*\)", "CHR(10)", converted, flags=re.IGNORECASE)
    converted = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"%(\1)s", converted)
    converted = converted.replace("?", "%s")
    return converted


class DbConnection:
    def __init__(self) -> None:
        self.backend = "postgres" if using_postgres() else "sqlite"
        if self.backend == "postgres":
            if psycopg is None:
                raise RuntimeError("Instale psycopg[binary] para usar DATABASE_URL/Postgres.")
            self.raw = psycopg.connect(get_database_url(), row_factory=dict_row)
        else:
            self.raw = sqlite3.connect(DB_PATH)
            self.raw.row_factory = sqlite3.Row
            self.raw.execute("PRAGMA foreign_keys = ON")

    def __enter__(self) -> "DbConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if exc_type:
            self.raw.rollback()
        else:
            self.raw.commit()
        self.raw.close()

    def execute(self, sql: str, params: Any = None) -> Any:
        sql = convert_sql(sql)
        if params is None:
            return self.raw.execute(sql)
        return self.raw.execute(sql, params)

    def executemany(self, sql: str, params: Any) -> Any:
        return self.raw.executemany(convert_sql(sql), params)

    def executescript(self, script: str) -> None:
        if self.backend == "sqlite":
            self.raw.executescript(script)
            return
        for statement in [part.strip() for part in script.split(";") if part.strip()]:
            self.execute(statement)


def get_connection() -> DbConnection:
    return DbConnection()


def read_sql(sql: str, conn: DbConnection, params: Any = None) -> pd.DataFrame:
    return pd.read_sql_query(convert_sql(sql), conn.raw, params=params)


def db_cache_key() -> str:
    return "postgres" if using_postgres() else str(DB_PATH)


@st.cache_resource(show_spinner=False)
def init_db_once(cache_key: str) -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf TEXT NOT NULL UNIQUE,
                rg TEXT,
                data_nascimento TEXT,
                estado_civil TEXT,
                email TEXT,
                celular TEXT,
                telefone TEXT,
                cep TEXT,
                endereco TEXT,
                numero TEXT,
                complemento TEXT,
                bairro TEXT,
                cidade TEXT,
                uf TEXT,
                cargo TEXT NOT NULL,
                setor TEXT,
                matricula TEXT,
                data_admissao TEXT,
                tipo_contrato TEXT,
                jornada TEXT,
                salario TEXT,
                gestor TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo',
                data_desligamento TEXT,
                motivo_desligamento TEXT,
                observacoes TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS family_contacts (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                parentesco TEXT,
                telefone TEXT NOT NULL,
                telefone_alt TEXT,
                email TEXT,
                endereco TEXT,
                prioridade INTEGER NOT NULL DEFAULT 1,
                observacoes TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS vacations (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                periodo_aquisitivo TEXT,
                data_inicio TEXT NOT NULL,
                data_fim TEXT NOT NULL,
                data_retorno TEXT,
                dias INTEGER,
                status TEXT NOT NULL DEFAULT 'Programada',
                aviso_dias INTEGER NOT NULL DEFAULT 30,
                observacoes TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS leave_records (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                tipo TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                data_previsao_retorno TEXT,
                data_retorno TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo',
                aviso_dias INTEGER NOT NULL DEFAULT 7,
                motivo TEXT,
                documento TEXT,
                observacoes TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employee_history (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                evento TEXT NOT NULL,
                descricao TEXT NOT NULL,
                detalhes TEXT,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_employees_nome ON employees(nome);
            CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
            CREATE INDEX IF NOT EXISTS idx_contacts_employee ON family_contacts(employee_id);
            CREATE INDEX IF NOT EXISTS idx_vacations_employee ON vacations(employee_id);
            CREATE INDEX IF NOT EXISTS idx_vacations_dates ON vacations(data_inicio, data_fim);
            CREATE INDEX IF NOT EXISTS idx_leave_records_employee ON leave_records(employee_id);
            CREATE INDEX IF NOT EXISTS idx_leave_records_dates ON leave_records(data_inicio, data_previsao_retorno);
            CREATE INDEX IF NOT EXISTS idx_employee_history_employee ON employee_history(employee_id);
            """
        )
        ensure_employee_columns(conn)


def init_db() -> None:
    init_db_once(db_cache_key())


def ensure_employee_columns(conn: DbConnection) -> None:
    if using_postgres():
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'employees'
            """
        ).fetchall()
        existing = {row["column_name"] for row in rows}
    else:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(employees)").fetchall()}
    columns = {
        "data_desligamento": "TEXT",
        "motivo_desligamento": "TEXT",
    }
    for column, definition in columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE employees ADD COLUMN {column} {definition}")


def add_history(
    conn: DbConnection,
    employee_id: str,
    evento: str,
    descricao: str,
    detalhes: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO employee_history (id, employee_id, evento, descricao, detalhes, criado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            employee_id,
            evento,
            descricao,
            detalhes,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def only_digits(value: Any) -> str:
    return re.sub(r"\D", "", clean_text(value))


def format_cpf(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) != 11:
        return clean_text(value)
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def is_valid_cpf(value: Any) -> bool:
    digits = only_digits(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    first = sum(int(digits[i]) * (10 - i) for i in range(9))
    first_digit = (first * 10) % 11
    first_digit = 0 if first_digit == 10 else first_digit

    second = sum(int(digits[i]) * (11 - i) for i in range(10))
    second_digit = (second * 10) % 11
    second_digit = 0 if second_digit == 10 else second_digit

    return first_digit == int(digits[9]) and second_digit == int(digits[10])


def format_phone(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    if len(digits) == 9:
        return f"{digits[:5]}-{digits[5:]}"
    return clean_text(value)


def format_cep(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return clean_text(value)


def parse_iso_date(value: Any) -> date | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def date_to_db(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return clean_text(value)


def format_date_br(value: Any) -> str:
    parsed = parse_iso_date(value)
    return parsed.strftime("%d/%m/%Y") if parsed else ""


def pick_index(options: list[str], value: Any) -> int:
    text = clean_text(value)
    return options.index(text) if text in options else 0


def clear_cached_data() -> None:
    st.cache_data.clear()


def cpf_exists(cpf: str, exclude_id: str | None = None) -> bool:
    with get_connection() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT id FROM employees WHERE cpf = ? AND id <> ?",
                (cpf, exclude_id),
            ).fetchone()
        else:
            row = conn.execute("SELECT id FROM employees WHERE cpf = ?", (cpf,)).fetchone()
    return row is not None


@st.cache_data(show_spinner=False, ttl=60)
def load_employees() -> pd.DataFrame:
    with get_connection() as conn:
        return read_sql(
            """
            SELECT
                e.*,
                COUNT(c.id) AS contatos_familiares
            FROM employees e
            LEFT JOIN family_contacts c ON c.employee_id = e.id
            GROUP BY e.id
            ORDER BY e.nome COLLATE NOCASE
            """,
            conn,
        )


@st.cache_data(show_spinner=False, ttl=60)
def load_employee_history(employee_id: str) -> pd.DataFrame:
    with get_connection() as conn:
        return read_sql(
            """
            SELECT evento, descricao, detalhes, criado_em
            FROM employee_history
            WHERE employee_id = ?
            ORDER BY criado_em DESC
            """,
            conn,
            params=(employee_id,),
        )


def update_employee_status(employee_id: str, status: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        old = conn.execute("SELECT status FROM employees WHERE id = ?", (employee_id,)).fetchone()
        conn.execute(
            "UPDATE employees SET status = ?, atualizado_em = ? WHERE id = ?",
            (status, now, employee_id),
        )
        old_status = clean_text(old["status"]) if old else ""
        if old_status != status:
            add_history(
                conn,
                employee_id,
                "Status",
                f"Status alterado para {status}",
                f"Status anterior: {old_status or '-'}",
            )
    clear_cached_data()


def terminate_employee(employee_id: str, data_desligamento: date, motivo: str, observacoes: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE employees
            SET status = 'Desligado',
                data_desligamento = ?,
                motivo_desligamento = ?,
                observacoes = CASE
                    WHEN COALESCE(observacoes, '') = '' THEN ?
                    ELSE observacoes || CHAR(10) || ?
                END,
                atualizado_em = ?
            WHERE id = ?
            """,
            (
                date_to_db(data_desligamento),
                clean_text(motivo),
                clean_text(observacoes),
                clean_text(observacoes),
                now,
                employee_id,
            ),
        )
        add_history(
            conn,
            employee_id,
            "Desligamento",
            f"Funcionário desligado em {format_date_br(data_desligamento)}",
            f"Motivo: {motivo}. {clean_text(observacoes)}",
        )
    clear_cached_data()


def days_between_today(value: Any) -> int | None:
    parsed = parse_iso_date(value)
    if not parsed:
        return None
    return (parsed - date.today()).days


def add_vacation_alert_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    enriched = df.copy()
    enriched["dias_para_inicio"] = enriched["data_inicio"].apply(days_between_today)
    enriched["dias_para_fim"] = enriched["data_fim"].apply(days_between_today)
    enriched["situacao_calculada"] = enriched.apply(calculated_vacation_situation, axis=1)
    return enriched


def calculated_vacation_situation(row: pd.Series | dict[str, Any]) -> str:
    status = clean_text(row.get("status"))
    if status in ["Cancelada", "Concluída"]:
        return status

    start = parse_iso_date(row.get("data_inicio"))
    end = parse_iso_date(row.get("data_fim"))
    today = date.today()
    if start and end and start <= today <= end:
        return "Em férias"
    if start and start > today:
        return "Vai entrar"
    if end and end < today:
        return "Retorno pendente"
    return status or "Programada"


def filter_open_vacations(vacations: pd.DataFrame) -> pd.DataFrame:
    if vacations.empty:
        return vacations
    return vacations[~vacations["status"].isin(["Concluída", "Cancelada"])].copy()


def add_leave_alert_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    enriched = df.copy()
    enriched["dias_para_inicio"] = enriched["data_inicio"].apply(days_between_today)
    enriched["dias_para_retorno"] = enriched["data_previsao_retorno"].apply(days_between_today)
    enriched["situacao_calculada"] = enriched.apply(calculated_leave_situation, axis=1)
    return enriched


def calculated_leave_situation(row: pd.Series | dict[str, Any]) -> str:
    status = clean_text(row.get("status"))
    if status in ["Cancelado", "Encerrado"]:
        return status

    start = parse_iso_date(row.get("data_inicio"))
    expected_return = parse_iso_date(row.get("data_previsao_retorno"))
    actual_return = parse_iso_date(row.get("data_retorno"))
    today = date.today()
    if actual_return:
        return "Encerrado"
    if start and start > today:
        return "Programado"
    if expected_return and expected_return < today:
        return "Retorno vencido"
    return "Ativo"


@st.cache_data(show_spinner=False, ttl=60)
def load_vacations() -> pd.DataFrame:
    with get_connection() as conn:
        df = read_sql(
            """
            SELECT
                v.*,
                e.nome AS funcionario,
                e.cpf,
                e.cargo,
                e.setor,
                e.status AS status_funcionario
            FROM vacations v
            JOIN employees e ON e.id = v.employee_id
            ORDER BY v.data_inicio DESC, e.nome COLLATE NOCASE
            """,
            conn,
        )
    return add_vacation_alert_columns(df)


@st.cache_data(show_spinner=False, ttl=60)
def load_leave_records() -> pd.DataFrame:
    with get_connection() as conn:
        df = read_sql(
            """
            SELECT
                l.*,
                e.nome AS funcionario,
                e.cpf,
                e.cargo,
                e.setor,
                e.status AS status_funcionario
            FROM leave_records l
            JOIN employees e ON e.id = l.employee_id
            ORDER BY l.data_inicio DESC, e.nome COLLATE NOCASE
            """,
            conn,
        )
    return add_leave_alert_columns(df)


def insert_vacation(payload: dict[str, Any]) -> str:
    vacation_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO vacations (
                id, employee_id, periodo_aquisitivo, data_inicio, data_fim,
                data_retorno, dias, status, aviso_dias, observacoes,
                criado_em, atualizado_em
            )
            VALUES (
                :id, :employee_id, :periodo_aquisitivo, :data_inicio, :data_fim,
                :data_retorno, :dias, :status, :aviso_dias, :observacoes,
                :criado_em, :atualizado_em
            )
            """,
            {
                **payload,
                "id": vacation_id,
                "criado_em": now,
                "atualizado_em": now,
            },
        )
        add_history(
            conn,
            payload["employee_id"],
            "Férias",
            f"Férias lançadas: {format_date_br(payload.get('data_inicio'))} a {format_date_br(payload.get('data_fim'))}",
            f"Status: {payload.get('status')}. Retorno: {format_date_br(payload.get('data_retorno')) or '-'}.",
        )
    clear_cached_data()
    return vacation_id


def update_vacation(vacation_id: str, payload: dict[str, Any]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        old = conn.execute("SELECT employee_id FROM vacations WHERE id = ?", (vacation_id,)).fetchone()
        conn.execute(
            """
            UPDATE vacations
            SET
                employee_id = :employee_id,
                periodo_aquisitivo = :periodo_aquisitivo,
                data_inicio = :data_inicio,
                data_fim = :data_fim,
                data_retorno = :data_retorno,
                dias = :dias,
                status = :status,
                aviso_dias = :aviso_dias,
                observacoes = :observacoes,
                atualizado_em = :atualizado_em
            WHERE id = :id
            """,
            {
                **payload,
                "id": vacation_id,
                "atualizado_em": now,
            },
        )
        target_employee_id = payload["employee_id"]
        add_history(
            conn,
            target_employee_id,
            "Férias",
            f"Férias atualizadas: {format_date_br(payload.get('data_inicio'))} a {format_date_br(payload.get('data_fim'))}",
            f"Status: {payload.get('status')}.",
        )
        if old and old["employee_id"] != target_employee_id:
            add_history(
                conn,
                old["employee_id"],
                "Férias",
                "Lançamento de férias movido para outro funcionário",
                f"Novo funcionário vinculado: {target_employee_id}",
            )
    clear_cached_data()


def insert_leave_record(payload: dict[str, Any]) -> str:
    leave_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO leave_records (
                id, employee_id, tipo, data_inicio, data_previsao_retorno,
                data_retorno, status, aviso_dias, motivo, documento,
                observacoes, criado_em, atualizado_em
            )
            VALUES (
                :id, :employee_id, :tipo, :data_inicio, :data_previsao_retorno,
                :data_retorno, :status, :aviso_dias, :motivo, :documento,
                :observacoes, :criado_em, :atualizado_em
            )
            """,
            {
                **payload,
                "id": leave_id,
                "criado_em": now,
                "atualizado_em": now,
            },
        )
        add_history(
            conn,
            payload["employee_id"],
            "Afastamento",
            f"Afastamento lançado: {payload.get('tipo')}",
            f"Início: {format_date_br(payload.get('data_inicio'))}. Retorno previsto: {format_date_br(payload.get('data_previsao_retorno')) or '-'}.",
        )
    clear_cached_data()
    return leave_id


def update_leave_record(leave_id: str, payload: dict[str, Any]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        old = conn.execute("SELECT employee_id FROM leave_records WHERE id = ?", (leave_id,)).fetchone()
        conn.execute(
            """
            UPDATE leave_records
            SET
                employee_id = :employee_id,
                tipo = :tipo,
                data_inicio = :data_inicio,
                data_previsao_retorno = :data_previsao_retorno,
                data_retorno = :data_retorno,
                status = :status,
                aviso_dias = :aviso_dias,
                motivo = :motivo,
                documento = :documento,
                observacoes = :observacoes,
                atualizado_em = :atualizado_em
            WHERE id = :id
            """,
            {
                **payload,
                "id": leave_id,
                "atualizado_em": now,
            },
        )
        target_employee_id = payload["employee_id"]
        add_history(
            conn,
            target_employee_id,
            "Afastamento",
            f"Afastamento atualizado: {payload.get('tipo')}",
            f"Status: {payload.get('status')}. Retorno: {format_date_br(payload.get('data_retorno')) or '-'}",
        )
        if old and old["employee_id"] != target_employee_id:
            add_history(
                conn,
                old["employee_id"],
                "Afastamento",
                "Lançamento de afastamento movido para outro funcionário",
                f"Novo funcionário vinculado: {target_employee_id}",
            )
    clear_cached_data()


@st.cache_data(show_spinner=False, ttl=60)
def get_employee(employee_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    return dict(row) if row else None


@st.cache_data(show_spinner=False, ttl=60)
def get_contacts(employee_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM family_contacts
            WHERE employee_id = ?
            ORDER BY prioridade ASC, nome COLLATE NOCASE
            """,
            (employee_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def normalize_contacts(raw_contacts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    contacts: list[dict[str, Any]] = []
    errors: list[str] = []

    for index, raw in enumerate(raw_contacts, start=1):
        contact = {
            "nome": clean_text(raw.get("nome")),
            "parentesco": clean_text(raw.get("parentesco")),
            "telefone": only_digits(raw.get("telefone")),
            "telefone_alt": only_digits(raw.get("telefone_alt")),
            "email": clean_text(raw.get("email")).lower(),
            "endereco": clean_text(raw.get("endereco")),
            "prioridade": index,
            "observacoes": clean_text(raw.get("observacoes")),
        }

        has_any_value = any(contact[key] for key in ["nome", "parentesco", "telefone", "telefone_alt", "email", "endereco", "observacoes"])
        if not has_any_value:
            continue

        if not contact["nome"] or not contact["telefone"]:
            errors.append(f"Preencha nome e telefone do contato familiar {index}.")
        if contact["telefone"] and not 8 <= len(contact["telefone"]) <= 13:
            errors.append(f"O telefone do contato familiar {index} parece incompleto.")
        if contact["telefone_alt"] and not 8 <= len(contact["telefone_alt"]) <= 13:
            errors.append(f"O telefone alternativo do contato familiar {index} parece incompleto.")
        if contact["email"] and not EMAIL_RE.match(contact["email"]):
            errors.append(f"O e-mail do contato familiar {index} não parece válido.")

        contacts.append(contact)

    if not contacts:
        errors.append("Cadastre pelo menos um contato familiar ou de emergência.")

    return contacts, errors


def normalize_employee(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: clean_text(value) for key, value in payload.items()}
    normalized["cpf"] = only_digits(payload.get("cpf"))
    normalized["celular"] = only_digits(payload.get("celular"))
    normalized["telefone"] = only_digits(payload.get("telefone"))
    normalized["cep"] = only_digits(payload.get("cep"))
    normalized["email"] = clean_text(payload.get("email")).lower()
    normalized["data_nascimento"] = date_to_db(payload.get("data_nascimento"))
    normalized["data_admissao"] = date_to_db(payload.get("data_admissao"))
    normalized["uf"] = clean_text(payload.get("uf")).upper()
    normalized["status"] = clean_text(payload.get("status")) or "Ativo"
    normalized["salario"] = ""
    return normalized


def validate_employee(payload: dict[str, Any], contacts: list[dict[str, Any]], exclude_id: str | None = None) -> list[str]:
    errors: list[str] = []
    employee = normalize_employee(payload)
    _, contact_errors = normalize_contacts(contacts)
    errors.extend(contact_errors)

    if not employee["nome"]:
        errors.append("Informe o nome completo.")
    if not is_valid_cpf(employee["cpf"]):
        errors.append("Informe um CPF válido.")
    elif cpf_exists(employee["cpf"], exclude_id=exclude_id):
        errors.append("Já existe um funcionário cadastrado com este CPF.")
    if employee["email"] and not EMAIL_RE.match(employee["email"]):
        errors.append("O e-mail do funcionário não parece válido.")
    if employee["celular"] and not 8 <= len(employee["celular"]) <= 13:
        errors.append("O celular parece incompleto.")
    if employee["telefone"] and not 8 <= len(employee["telefone"]) <= 13:
        errors.append("O telefone parece incompleto.")
    if employee["cep"] and len(employee["cep"]) != 8:
        errors.append("O CEP deve ter 8 números.")
    if not employee["cargo"]:
        errors.append("Informe a função/cargo.")
    if employee["data_admissao"]:
        admission = parse_iso_date(employee["data_admissao"])
        if admission and admission > date.today():
            errors.append("A data de admissão não pode ficar no futuro.")
    if employee["data_nascimento"]:
        birth = parse_iso_date(employee["data_nascimento"])
        if birth and birth >= date.today():
            errors.append("A data de nascimento deve ser anterior a hoje.")

    return errors


def insert_employee(payload: dict[str, Any], contacts: list[dict[str, Any]]) -> str:
    employee = normalize_employee(payload)
    normalized_contacts, _ = normalize_contacts(contacts)
    employee_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO employees (
                id, nome, cpf, rg, data_nascimento, estado_civil, email, celular,
                telefone, cep, endereco, numero, complemento, bairro, cidade, uf,
                cargo, setor, matricula, data_admissao, tipo_contrato, jornada,
                salario, gestor, status, observacoes, criado_em, atualizado_em
            )
            VALUES (
                :id, :nome, :cpf, :rg, :data_nascimento, :estado_civil, :email, :celular,
                :telefone, :cep, :endereco, :numero, :complemento, :bairro, :cidade, :uf,
                :cargo, :setor, :matricula, :data_admissao, :tipo_contrato, :jornada,
                :salario, :gestor, :status, :observacoes, :criado_em, :atualizado_em
            )
            """,
            {
                **employee,
                "id": employee_id,
                "criado_em": now,
                "atualizado_em": now,
            },
        )
        for contact in normalized_contacts:
            conn.execute(
                """
                INSERT INTO family_contacts (
                    id, employee_id, nome, parentesco, telefone, telefone_alt,
                    email, endereco, prioridade, observacoes
                )
                VALUES (
                    :id, :employee_id, :nome, :parentesco, :telefone, :telefone_alt,
                    :email, :endereco, :prioridade, :observacoes
                )
                """,
                {
                    **contact,
                    "id": str(uuid.uuid4()),
                    "employee_id": employee_id,
                },
            )
        add_history(
            conn,
            employee_id,
            "Cadastro",
            "Funcionário cadastrado",
            f"Cargo: {employee.get('cargo') or '-'} | Setor: {employee.get('setor') or '-'}",
        )

    clear_cached_data()
    return employee_id


def update_employee(employee_id: str, payload: dict[str, Any], contacts: list[dict[str, Any]]) -> None:
    employee = normalize_employee(payload)
    normalized_contacts, _ = normalize_contacts(contacts)
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        old = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        conn.execute(
            """
            UPDATE employees
            SET
                nome = :nome,
                cpf = :cpf,
                rg = :rg,
                data_nascimento = :data_nascimento,
                estado_civil = :estado_civil,
                email = :email,
                celular = :celular,
                telefone = :telefone,
                cep = :cep,
                endereco = :endereco,
                numero = :numero,
                complemento = :complemento,
                bairro = :bairro,
                cidade = :cidade,
                uf = :uf,
                cargo = :cargo,
                setor = :setor,
                matricula = :matricula,
                data_admissao = :data_admissao,
                tipo_contrato = :tipo_contrato,
                jornada = :jornada,
                salario = :salario,
                gestor = :gestor,
                status = :status,
                observacoes = :observacoes,
                atualizado_em = :atualizado_em
            WHERE id = :id
            """,
            {
                **employee,
                "id": employee_id,
                "atualizado_em": now,
            },
        )
        conn.execute("DELETE FROM family_contacts WHERE employee_id = ?", (employee_id,))
        for contact in normalized_contacts:
            conn.execute(
                """
                INSERT INTO family_contacts (
                    id, employee_id, nome, parentesco, telefone, telefone_alt,
                    email, endereco, prioridade, observacoes
                )
                VALUES (
                    :id, :employee_id, :nome, :parentesco, :telefone, :telefone_alt,
                    :email, :endereco, :prioridade, :observacoes
                )
                """,
                {
                    **contact,
                    "id": str(uuid.uuid4()),
                    "employee_id": employee_id,
                },
            )
        details: list[str] = []
        if old:
            for field, label in [
                ("cargo", "Função"),
                ("setor", "Setor"),
                ("status", "Status"),
                ("gestor", "Gestor"),
            ]:
                before = clean_text(old[field])
                after = clean_text(employee.get(field))
                if before != after:
                    details.append(f"{label}: {before or '-'} -> {after or '-'}")
        add_history(
            conn,
            employee_id,
            "Cadastro",
            "Cadastro atualizado",
            "; ".join(details) if details else "Dados cadastrais revisados.",
        )
    clear_cached_data()


@st.cache_data(show_spinner=False)
def logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_header() -> None:
    logo = logo_data_uri()
    logo_html = f'<img class="jr-header-logo" src="{logo}" alt="JR Ferragens e Madeiras">' if logo else ""
    today = date.today().strftime("%d/%m/%Y")
    header_html = (
        '<div class="jr-header">'
        '<div>'
        '<div class="jr-kicker">Sistema interno de RH</div>'
        '<div class="jr-title" style="color:#ffffff !important;">Cadastro de Funcionários</div>'
        '<div class="jr-subtitle" style="color:rgba(255,255,255,.82) !important;">JR Ferragens e Madeiras</div>'
        '</div>'
        '<div class="jr-header-actions">'
        f'<span class="jr-pill">Hoje: {today}</span>'
        '<span class="jr-pill jr-pill-green">Banco local</span>'
        '</div>'
        f'{logo_html}'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def render_overview(
    df: pd.DataFrame,
    vacations: pd.DataFrame,
    leaves: pd.DataFrame,
) -> None:
    active_count = int((df["status"] == "Ativo").sum()) if not df.empty else 0
    family_contacts = int(df["contatos_familiares"].sum()) if not df.empty else 0

    upcoming_vacations = 0
    on_vacation = 0
    pending_vacation_return = 0
    if not vacations.empty:
        work_vacations = vacations.copy()
        work_vacations["dias_para_inicio"] = pd.to_numeric(work_vacations["dias_para_inicio"], errors="coerce")
        work_vacations["aviso_dias"] = pd.to_numeric(work_vacations["aviso_dias"], errors="coerce").fillna(30)
        upcoming_vacations = len(
            work_vacations[
                (work_vacations["situacao_calculada"] == "Vai entrar")
                & (work_vacations["dias_para_inicio"] >= 0)
                & (work_vacations["dias_para_inicio"] <= work_vacations["aviso_dias"])
            ]
        )
        on_vacation = int((work_vacations["situacao_calculada"] == "Em férias").sum())
        pending_vacation_return = int((work_vacations["situacao_calculada"] == "Retorno pendente").sum())

    active_leaves = 0
    overdue_leave_returns = 0
    if not leaves.empty:
        active_leaves = int(leaves["situacao_calculada"].isin(["Ativo", "Retorno vencido"]).sum())
        overdue_leave_returns = int((leaves["situacao_calculada"] == "Retorno vencido").sum())

    cards = [
        ("Funcionários", len(df)),
        ("Ativos", active_count),
        ("Contatos", family_contacts),
        ("Férias próximas", upcoming_vacations),
        ("Em férias", on_vacation),
        ("Afastados", active_leaves),
    ]
    cols = st.columns(6)
    for col, (label, value) in zip(cols, cards):
        col.markdown(
            f'<div class="jr-kpi-card"><div class="jr-kpi-label">{label}</div><div class="jr-kpi-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    if pending_vacation_return or overdue_leave_returns:
        st.markdown(
            f'<div class="jr-notice">Há {pending_vacation_return} retorno de férias pendente e {overdue_leave_returns} retorno de afastamento vencido.</div>',
            unsafe_allow_html=True,
        )


def contact_defaults(contacts: list[dict[str, Any]] | None, index: int) -> dict[str, Any]:
    if contacts and len(contacts) > index:
        return contacts[index]
    return {}


def render_contact_fields(prefix: str, number: int, default: dict[str, Any] | None = None) -> dict[str, Any]:
    default = default or {}
    st.markdown(f"**Contato familiar {number}**")
    col1, col2, col3 = st.columns([1.3, 0.8, 1])
    nome = col1.text_input(
        "Nome",
        value=clean_text(default.get("nome")),
        key=f"{prefix}_contato_{number}_nome",
    )
    parentesco = col2.selectbox(
        "Parentesco",
        PARENTESCO_OPTIONS,
        index=pick_index(PARENTESCO_OPTIONS, default.get("parentesco")),
        key=f"{prefix}_contato_{number}_parentesco",
    )
    telefone = col3.text_input(
        "Telefone principal",
        value=format_phone(default.get("telefone")),
        key=f"{prefix}_contato_{number}_telefone",
    )

    col4, col5, col6 = st.columns([1, 1.2, 1.4])
    telefone_alt = col4.text_input(
        "Telefone alternativo",
        value=format_phone(default.get("telefone_alt")),
        key=f"{prefix}_contato_{number}_telefone_alt",
    )
    email = col5.text_input(
        "E-mail",
        value=clean_text(default.get("email")),
        key=f"{prefix}_contato_{number}_email",
    )
    endereco = col6.text_input(
        "Endereço",
        value=clean_text(default.get("endereco")),
        key=f"{prefix}_contato_{number}_endereco",
    )
    observacoes = st.text_input(
        "Observações",
        value=clean_text(default.get("observacoes")),
        key=f"{prefix}_contato_{number}_observacoes",
    )

    return {
        "nome": nome,
        "parentesco": parentesco,
        "telefone": telefone,
        "telefone_alt": telefone_alt,
        "email": email,
        "endereco": endereco,
        "observacoes": observacoes,
    }


def render_employee_fields(
    prefix: str,
    employee: dict[str, Any] | None = None,
    contacts: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    employee = employee or {}
    contacts = contacts or []

    st.markdown('<div class="jr-section-title">Dados pessoais</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.6, 0.9, 0.7])
    nome = col1.text_input("Nome completo *", value=clean_text(employee.get("nome")), key=f"{prefix}_nome")
    cpf = col2.text_input("CPF *", value=format_cpf(employee.get("cpf")), key=f"{prefix}_cpf")
    rg = col3.text_input("RG", value=clean_text(employee.get("rg")), key=f"{prefix}_rg")

    col4, col5, col6, col7 = st.columns([0.9, 0.9, 1.1, 1.1])
    data_nascimento = col4.date_input(
        "Data de nascimento",
        value=parse_iso_date(employee.get("data_nascimento")),
        min_value=date(1900, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
        key=f"{prefix}_data_nascimento",
    )
    estado_civil = col5.selectbox(
        "Estado civil",
        ESTADO_CIVIL_OPTIONS,
        index=pick_index(ESTADO_CIVIL_OPTIONS, employee.get("estado_civil")),
        key=f"{prefix}_estado_civil",
    )
    celular = col6.text_input("Celular", value=format_phone(employee.get("celular")), key=f"{prefix}_celular")
    telefone = col7.text_input("Telefone", value=format_phone(employee.get("telefone")), key=f"{prefix}_telefone")

    email = st.text_input("E-mail", value=clean_text(employee.get("email")), key=f"{prefix}_email")

    st.markdown('<div class="jr-section-title">Endereço</div>', unsafe_allow_html=True)
    col8, col9, col10 = st.columns([0.75, 1.7, 0.55])
    cep = col8.text_input("CEP", value=format_cep(employee.get("cep")), key=f"{prefix}_cep")
    endereco = col9.text_input("Endereço", value=clean_text(employee.get("endereco")), key=f"{prefix}_endereco")
    numero = col10.text_input("Número", value=clean_text(employee.get("numero")), key=f"{prefix}_numero")

    col11, col12, col13, col14 = st.columns([1, 1, 1, 0.45])
    complemento = col11.text_input("Complemento", value=clean_text(employee.get("complemento")), key=f"{prefix}_complemento")
    bairro = col12.text_input("Bairro", value=clean_text(employee.get("bairro")), key=f"{prefix}_bairro")
    cidade = col13.text_input("Cidade", value=clean_text(employee.get("cidade")), key=f"{prefix}_cidade")
    uf = col14.selectbox("UF", UF_OPTIONS, index=pick_index(UF_OPTIONS, employee.get("uf")), key=f"{prefix}_uf")

    st.markdown('<div class="jr-section-title">Dados profissionais</div>', unsafe_allow_html=True)
    col15, col16, col17, col18 = st.columns([1.25, 1, 0.75, 0.85])
    cargo = col15.text_input("Função/Cargo *", value=clean_text(employee.get("cargo")), key=f"{prefix}_cargo")
    setor = col16.text_input("Setor", value=clean_text(employee.get("setor")), key=f"{prefix}_setor")
    matricula = col17.text_input("Matrícula", value=clean_text(employee.get("matricula")), key=f"{prefix}_matricula")
    status = col18.selectbox(
        "Status",
        STATUS_OPTIONS,
        index=pick_index(STATUS_OPTIONS, employee.get("status") or "Ativo"),
        key=f"{prefix}_status",
    )

    col19, col20, col21 = st.columns([0.95, 1, 1])
    data_admissao = col19.date_input(
        "Data de admissão",
        value=parse_iso_date(employee.get("data_admissao")) or date.today(),
        min_value=date(1990, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
        key=f"{prefix}_data_admissao",
    )
    tipo_contrato = col20.selectbox(
        "Tipo de contrato",
        CONTRATO_OPTIONS,
        index=pick_index(CONTRATO_OPTIONS, employee.get("tipo_contrato") or "CLT"),
        key=f"{prefix}_tipo_contrato",
    )
    jornada = col21.text_input("Jornada", value=clean_text(employee.get("jornada")), placeholder="Ex.: 44h semanais", key=f"{prefix}_jornada")

    gestor = st.text_input("Gestor responsável", value=clean_text(employee.get("gestor")), key=f"{prefix}_gestor")
    observacoes = st.text_area(
        "Observações internas",
        value=clean_text(employee.get("observacoes")),
        height=95,
        key=f"{prefix}_observacoes",
    )

    st.markdown('<div class="jr-section-title">Contatos familiares e emergência</div>', unsafe_allow_html=True)
    contact_one = render_contact_fields(prefix, 1, contact_defaults(contacts, 0))
    st.divider()
    contact_two = render_contact_fields(prefix, 2, contact_defaults(contacts, 1))

    payload = {
        "nome": nome,
        "cpf": cpf,
        "rg": rg,
        "data_nascimento": data_nascimento,
        "estado_civil": estado_civil,
        "email": email,
        "celular": celular,
        "telefone": telefone,
        "cep": cep,
        "endereco": endereco,
        "numero": numero,
        "complemento": complemento,
        "bairro": bairro,
        "cidade": cidade,
        "uf": uf,
        "cargo": cargo,
        "setor": setor,
        "matricula": matricula,
        "data_admissao": data_admissao,
        "tipo_contrato": tipo_contrato,
        "jornada": jornada,
        "gestor": gestor,
        "status": status,
        "observacoes": observacoes,
    }
    return payload, [contact_one, contact_two]


def show_errors(errors: list[str]) -> None:
    for error in errors:
        st.error(error)


def safe_next_birthday(birth: date, today: date) -> date:
    try:
        candidate = date(today.year, birth.month, birth.day)
    except ValueError:
        candidate = date(today.year, 2, 28)
    if candidate < today:
        try:
            candidate = date(today.year + 1, birth.month, birth.day)
        except ValueError:
            candidate = date(today.year + 1, 2, 28)
    return candidate


def build_birthdays(df: pd.DataFrame, days_limit: int | None = None, current_month_only: bool = False) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    today = date.today()
    if df.empty:
        return pd.DataFrame(rows)

    for _, row in df.iterrows():
        birth = parse_iso_date(row.get("data_nascimento"))
        if not birth:
            continue
        next_birthday = safe_next_birthday(birth, today)
        days = (next_birthday - today).days
        if days_limit is not None and days > days_limit:
            continue
        if current_month_only and birth.month != today.month:
            continue
        rows.append(
            {
                "Funcionário": row.get("nome"),
                "Setor": row.get("setor"),
                "Função": row.get("cargo"),
                "Aniversário": birth.strftime("%d/%m"),
                "Próximo aniversário": next_birthday.strftime("%d/%m/%Y"),
                "Dias": days,
            }
        )
    return pd.DataFrame(rows).sort_values("Dias") if rows else pd.DataFrame(rows)


def build_recent_admissions(df: pd.DataFrame, days_limit: int = 90) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    today = date.today()
    if df.empty:
        return pd.DataFrame(rows)

    for _, row in df.iterrows():
        admission = parse_iso_date(row.get("data_admissao"))
        if not admission:
            continue
        days = (today - admission).days
        if 0 <= days <= days_limit:
            rows.append(
                {
                    "Funcionário": row.get("nome"),
                    "Setor": row.get("setor"),
                    "Função": row.get("cargo"),
                    "Admissão": admission.strftime("%d/%m/%Y"),
                    "Dias na empresa": days,
                }
            )
    return pd.DataFrame(rows).sort_values("Dias na empresa") if rows else pd.DataFrame(rows)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def ensure_report_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    report = df.copy()
    for column in columns:
        if column not in report.columns:
            report[column] = ""
    return report[columns]


@st.cache_data(show_spinner=False, ttl=600)
def make_pdf_bytes(title: str, df: pd.DataFrame, columns: list[str]) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"JR Ferragens e Madeiras - emitido em {date.today().strftime('%d/%m/%Y')}", styles["Normal"]),
        Spacer(1, 12),
    ]

    table_df = ensure_report_columns(df, columns)
    if table_df.empty:
        table_data = [["Sem registros"]]
    else:
        table_data = [columns]
        for _, row in table_df.fillna("").astype(str).iterrows():
            table_data.append([value[:80] for value in row.tolist()])

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c8102e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8e0ee")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fb")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def render_summary_tab(
    df: pd.DataFrame,
    vacations: pd.DataFrame,
    leaves: pd.DataFrame,
) -> None:
    st.markdown('<div class="jr-section-title">Resumo do dia</div>', unsafe_allow_html=True)

    birthdays = build_birthdays(df, days_limit=30)
    recent_admissions = build_recent_admissions(df)
    open_vacations = filter_open_vacations(vacations)
    upcoming_vacations = open_vacations[open_vacations["situacao_calculada"] == "Vai entrar"].copy() if not open_vacations.empty else pd.DataFrame()
    active_leaves = leaves[leaves["situacao_calculada"].isin(["Ativo", "Retorno vencido"])].copy() if not leaves.empty else pd.DataFrame()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Aniversariantes nos próximos 30 dias**")
        if birthdays.empty:
            st.info("Nenhum aniversário próximo.")
        else:
            st.dataframe(birthdays[["Funcionário", "Setor", "Aniversário", "Dias"]], hide_index=True, width="stretch")

        st.markdown("**Férias próximas**")
        if upcoming_vacations.empty:
            st.info("Nenhuma férias próxima.")
        else:
            view = upcoming_vacations.copy()
            view["Início"] = view["data_inicio"].apply(format_date_br)
            view["Fim"] = view["data_fim"].apply(format_date_br)
            view = view.rename(columns={"funcionario": "Funcionário", "setor": "Setor"})
            st.dataframe(view[["Funcionário", "Setor", "Início", "Fim"]], hide_index=True, width="stretch")

    with col2:
        st.markdown("**Afastamentos ativos**")
        if active_leaves.empty:
            st.info("Nenhum afastamento ativo.")
        else:
            view = active_leaves.copy()
            view["Início"] = view["data_inicio"].apply(format_date_br)
            view["Retorno previsto"] = view["data_previsao_retorno"].apply(format_date_br)
            view = view.rename(columns={"funcionario": "Funcionário", "tipo": "Tipo"})
            st.dataframe(view[["Funcionário", "Tipo", "Início", "Retorno previsto"]], hide_index=True, width="stretch")

    st.markdown("**Admissões recentes**")
    if recent_admissions.empty:
        st.info("Nenhuma admissão nos últimos 90 dias.")
    else:
        st.dataframe(recent_admissions, hide_index=True, width="stretch")


def render_create_tab() -> None:
    with st.form("create_employee_form", clear_on_submit=False):
        payload, contacts = render_employee_fields("create")
        submitted = st.form_submit_button("Cadastrar funcionário", type="primary", width="stretch")

    if submitted:
        errors = validate_employee(payload, contacts)
        if errors:
            show_errors(errors)
            return
        employee_id = insert_employee(payload, contacts)
        st.success(f"Funcionário cadastrado com sucesso. Código interno: {employee_id[:8].upper()}")


def employee_label(row: pd.Series | dict[str, Any]) -> str:
    return f"{clean_text(row.get('nome'))} | {format_cpf(row.get('cpf'))} | {clean_text(row.get('cargo')) or 'Sem cargo'}"


def filter_employees(df: pd.DataFrame, term: str, statuses: list[str], sectors: list[str]) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()
    if statuses:
        filtered = filtered[filtered["status"].isin(statuses)]
    if sectors:
        filtered = filtered[filtered["setor"].fillna("").isin(sectors)]
    if term:
        term_clean = term.lower().strip()
        term_digits = only_digits(term)

        def matches(row: pd.Series) -> bool:
            searchable = " ".join(
                clean_text(row.get(field)).lower()
                for field in ["nome", "cpf", "cargo", "setor", "matricula", "cidade", "telefone", "celular"]
            )
            if term_clean in searchable:
                return True
            return bool(term_digits and term_digits in only_digits(row.get("cpf")))

        filtered = filtered[filtered.apply(matches, axis=1)]

    return filtered


def render_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Nenhum funcionário encontrado.")
        return

    view = df.copy()
    view["CPF"] = view["cpf"].apply(format_cpf)
    view["Celular"] = view["celular"].apply(format_phone)
    view["Admissão"] = view["data_admissao"].apply(format_date_br)
    view = view.rename(
        columns={
            "nome": "Nome",
            "cargo": "Função",
            "setor": "Setor",
            "status": "Status",
            "contatos_familiares": "Contatos",
        }
    )
    st.dataframe(
        view[["Nome", "CPF", "Função", "Setor", "Celular", "Admissão", "Status", "Contatos"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Nome": st.column_config.TextColumn(width="large"),
            "Função": st.column_config.TextColumn(width="medium"),
            "Setor": st.column_config.TextColumn(width="medium"),
            "Contatos": st.column_config.NumberColumn(width="small"),
        },
    )


def render_employee_details(employee_id: str) -> None:
    employee = get_employee(employee_id)
    if not employee:
        st.warning("Cadastro não encontrado.")
        return

    contacts = get_contacts(employee_id)
    status_class = "jr-pill" if employee["status"] == "Ativo" else "jr-pill jr-pill-red"
    st.markdown(
        f"<span class='{status_class}'>{clean_text(employee['status'])}</span>",
        unsafe_allow_html=True,
    )
    st.subheader(clean_text(employee["nome"]))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CPF", format_cpf(employee["cpf"]))
    col2.metric("Função", clean_text(employee["cargo"]) or "-")
    col3.metric("Setor", clean_text(employee["setor"]) or "-")
    col4.metric("Admissão", format_date_br(employee["data_admissao"]) or "-")

    details = {
        "RG": employee["rg"],
        "Nascimento": format_date_br(employee["data_nascimento"]),
        "Estado civil": employee["estado_civil"],
        "E-mail": employee["email"],
        "Celular": format_phone(employee["celular"]),
        "Telefone": format_phone(employee["telefone"]),
        "Endereço": " ".join(
            part
            for part in [
                employee["endereco"],
                employee["numero"],
                employee["complemento"],
                employee["bairro"],
                employee["cidade"],
                employee["uf"],
                format_cep(employee["cep"]),
            ]
            if clean_text(part)
        ),
        "Matrícula": employee["matricula"],
        "Contrato": employee["tipo_contrato"],
        "Jornada": employee["jornada"],
        "Gestor": employee["gestor"],
        "Data de desligamento": format_date_br(employee.get("data_desligamento")),
        "Motivo do desligamento": employee.get("motivo_desligamento"),
        "Observações": employee["observacoes"],
    }

    detail_df = pd.DataFrame(
        [{"Campo": key, "Informação": value or "-"} for key, value in details.items()]
    )
    st.dataframe(detail_df, hide_index=True, width="stretch")

    if contacts:
        contacts_df = pd.DataFrame(contacts)
        contacts_df["Telefone"] = contacts_df["telefone"].apply(format_phone)
        contacts_df["Telefone alternativo"] = contacts_df["telefone_alt"].apply(format_phone)
        contacts_df = contacts_df.rename(
            columns={
                "nome": "Nome",
                "parentesco": "Parentesco",
                "email": "E-mail",
                "endereco": "Endereço",
                "observacoes": "Observações",
            }
        )
        st.markdown("**Contatos familiares**")
        st.dataframe(
            contacts_df[["Nome", "Parentesco", "Telefone", "Telefone alternativo", "E-mail", "Endereço", "Observações"]],
            hide_index=True,
            width="stretch",
        )

    history = load_employee_history(employee_id)
    st.markdown("**Histórico**")
    if history.empty:
        st.info("Nenhum histórico registrado ainda.")
    else:
        history_view = history.copy()
        history_view["Data"] = history_view["criado_em"].apply(lambda value: value.replace("T", " ") if value else "")
        history_view = history_view.rename(
            columns={
                "evento": "Evento",
                "descricao": "Descrição",
                "detalhes": "Detalhes",
            }
        )
        st.dataframe(
            history_view[["Data", "Evento", "Descrição", "Detalhes"]],
            hide_index=True,
            width="stretch",
        )


def render_search_tab(df: pd.DataFrame) -> None:
    col1, col2, col3 = st.columns([1.5, 1.1, 1])
    term = col1.text_input("Buscar", placeholder="Nome, CPF, função, setor ou matrícula")
    statuses = col2.multiselect("Status", STATUS_OPTIONS, default=["Ativo"])
    sector_options = sorted([sector for sector in df["setor"].dropna().unique().tolist() if clean_text(sector)])
    sectors = col3.multiselect("Setor", sector_options)

    filtered = filter_employees(df, term, statuses, sectors)
    m1, m2, m3 = st.columns(3)
    m1.metric("Resultado", len(filtered))
    m2.metric("Ativos no resultado", int((filtered["status"] == "Ativo").sum()) if not filtered.empty else 0)
    m3.metric("Contatos no resultado", int(filtered["contatos_familiares"].sum()) if not filtered.empty else 0)

    render_table(filtered)

    if not filtered.empty:
        export = filtered.copy()
        export["cpf"] = export["cpf"].apply(format_cpf)
        export["celular"] = export["celular"].apply(format_phone)
        export["telefone"] = export["telefone"].apply(format_phone)
        export["cep"] = export["cep"].apply(format_cep)
        if "salario" in export.columns:
            export = export.drop(columns=["salario"])
        csv_bytes = export.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar CSV",
            data=csv_bytes,
            file_name="funcionarios_jr.csv",
            mime="text/csv",
            type="primary",
        )

        labels = {row["id"]: employee_label(row) for _, row in filtered.iterrows()}
        selected_id = st.selectbox(
            "Abrir cadastro",
            options=filtered["id"].tolist(),
            format_func=lambda value: labels.get(value, value),
        )
        render_employee_details(selected_id)


def pop_flash(key: str) -> None:
    message = st.session_state.pop(key, None)
    if message:
        st.success(message)


def build_vacation_payload(
    employee_id: str,
    periodo_aquisitivo: str,
    data_inicio: date,
    data_fim: date,
    data_retorno: date | None,
    status: str,
    aviso_dias: int,
    observacoes: str,
) -> dict[str, Any]:
    days = (data_fim - data_inicio).days + 1 if data_inicio and data_fim else 0
    return {
        "employee_id": employee_id,
        "periodo_aquisitivo": clean_text(periodo_aquisitivo),
        "data_inicio": date_to_db(data_inicio),
        "data_fim": date_to_db(data_fim),
        "data_retorno": date_to_db(data_retorno),
        "dias": max(days, 0),
        "status": status,
        "aviso_dias": int(aviso_dias),
        "observacoes": clean_text(observacoes),
    }


def validate_vacation(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    start = parse_iso_date(payload.get("data_inicio"))
    end = parse_iso_date(payload.get("data_fim"))
    return_date = parse_iso_date(payload.get("data_retorno"))

    if not clean_text(payload.get("employee_id")):
        errors.append("Selecione um funcionário.")
    if not start:
        errors.append("Informe a data de início das férias.")
    if not end:
        errors.append("Informe a data final das férias.")
    if start and end and start > end:
        errors.append("A data final das férias não pode ser anterior ao início.")
    if end and return_date and return_date < end:
        errors.append("A data de retorno não pode ser anterior ao fim das férias.")
    if int(payload.get("aviso_dias") or 0) < 0:
        errors.append("O aviso em dias não pode ser negativo.")
    return errors


def render_vacation_alerts(vacations: pd.DataFrame) -> None:
    if vacations.empty:
        st.info("Ainda não há férias lançadas.")
        return

    work = vacations.copy()
    work["dias_para_inicio"] = pd.to_numeric(work["dias_para_inicio"], errors="coerce")
    work["dias_para_fim"] = pd.to_numeric(work["dias_para_fim"], errors="coerce")
    work["aviso_dias"] = pd.to_numeric(work["aviso_dias"], errors="coerce").fillna(30)

    upcoming = work[
        (work["situacao_calculada"] == "Vai entrar")
        & (work["dias_para_inicio"] >= 0)
        & (work["dias_para_inicio"] <= work["aviso_dias"])
    ]
    on_vacation = work[work["situacao_calculada"] == "Em férias"]
    returning = on_vacation[
        (on_vacation["dias_para_fim"] >= 0)
        & (on_vacation["dias_para_fim"] <= 7)
    ]
    overdue = work[work["situacao_calculada"] == "Retorno pendente"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vão entrar", len(upcoming))
    col2.metric("Em férias", len(on_vacation))
    col3.metric("Retornam em até 7 dias", len(returning))
    col4.metric("Retorno pendente", len(overdue))

    if not upcoming.empty:
        st.markdown("**Aviso de férias próximas**")
        for _, row in upcoming.sort_values("data_inicio").head(8).iterrows():
            days = int(row["dias_para_inicio"])
            when = "hoje" if days == 0 else f"em {days} dia(s)"
            st.warning(
                f"{row['funcionario']} entra de férias {when}, em {format_date_br(row['data_inicio'])}."
            )

    if not on_vacation.empty:
        st.markdown("**Já estão em férias**")
        for _, row in on_vacation.sort_values("data_fim").head(8).iterrows():
            st.info(
                f"{row['funcionario']} está em férias até {format_date_br(row['data_fim'])}. "
                f"Retorno previsto: {format_date_br(row['data_retorno']) or '-'}."
            )

    if not returning.empty:
        st.markdown("**Retorno próximo**")
        for _, row in returning.sort_values("data_fim").head(8).iterrows():
            days = int(row["dias_para_fim"])
            when = "hoje" if days == 0 else f"em {days} dia(s)"
            st.warning(f"{row['funcionario']} termina as férias {when}.")

    if not overdue.empty:
        st.markdown("**Atenção: conferir retorno**")
        for _, row in overdue.sort_values("data_fim").head(8).iterrows():
            st.error(
                f"{row['funcionario']} tinha férias até {format_date_br(row['data_fim'])}; "
                "confira se já retornou e marque como concluída."
            )


def render_vacation_table(vacations: pd.DataFrame) -> None:
    if vacations.empty:
        st.info("Nenhum lançamento de férias encontrado.")
        return

    view = vacations.copy()
    view["CPF"] = view["cpf"].apply(format_cpf)
    view["Início"] = view["data_inicio"].apply(format_date_br)
    view["Fim"] = view["data_fim"].apply(format_date_br)
    view["Retorno"] = view["data_retorno"].apply(format_date_br)
    view = view.rename(
        columns={
            "funcionario": "Funcionário",
            "cargo": "Função",
            "setor": "Setor",
            "periodo_aquisitivo": "Período aquisitivo",
            "dias": "Dias",
            "situacao_calculada": "Situação",
            "status": "Status informado",
            "observacoes": "Observações",
        }
    )
    st.dataframe(
        view[
            [
                "Funcionário",
                "CPF",
                "Função",
                "Setor",
                "Início",
                "Fim",
                "Retorno",
                "Dias",
                "Situação",
                "Status informado",
                "Observações",
            ]
        ],
        hide_index=True,
        width="stretch",
    )

    export = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar férias em CSV",
        data=export,
        file_name="ferias_jr.csv",
        mime="text/csv",
        type="primary",
    )


def render_vacation_form(
    df: pd.DataFrame,
    prefix: str,
    vacation: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    vacation = vacation or {}
    labels = {row["id"]: employee_label(row) for _, row in df.iterrows()}
    employee_ids = df["id"].tolist()
    default_employee = clean_text(vacation.get("employee_id"))
    default_employee_index = employee_ids.index(default_employee) if default_employee in employee_ids else 0

    selected_employee = st.selectbox(
        "Funcionário",
        options=employee_ids,
        index=default_employee_index,
        format_func=lambda value: labels.get(value, value),
        key=f"{prefix}_vacation_employee",
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 0.8])
    start_default = parse_iso_date(vacation.get("data_inicio")) or date.today()
    end_default = parse_iso_date(vacation.get("data_fim")) or (start_default + timedelta(days=29))
    return_default = parse_iso_date(vacation.get("data_retorno")) or (end_default + timedelta(days=1))
    data_inicio = col1.date_input(
        "Vai sair/entrar em",
        value=start_default,
        format="DD/MM/YYYY",
        key=f"{prefix}_vacation_start",
    )
    data_fim = col2.date_input(
        "Último dia de férias",
        value=end_default,
        format="DD/MM/YYYY",
        key=f"{prefix}_vacation_end",
    )
    data_retorno = col3.date_input(
        "Retorno ao trabalho",
        value=return_default,
        format="DD/MM/YYYY",
        key=f"{prefix}_vacation_return",
    )
    aviso_dias = col4.number_input(
        "Avisar antes",
        min_value=0,
        max_value=180,
        value=int(vacation.get("aviso_dias") or 30),
        step=1,
        key=f"{prefix}_vacation_notice",
    )

    col5, col6 = st.columns([1, 0.7])
    periodo_aquisitivo = col5.text_input(
        "Período aquisitivo",
        value=clean_text(vacation.get("periodo_aquisitivo")),
        placeholder="Ex.: 2025/2026",
        key=f"{prefix}_vacation_period",
    )
    status = col6.selectbox(
        "Status",
        VACATION_STATUS_OPTIONS,
        index=pick_index(VACATION_STATUS_OPTIONS, vacation.get("status") or "Programada"),
        key=f"{prefix}_vacation_status",
    )
    observacoes = st.text_area(
        "Observações",
        value=clean_text(vacation.get("observacoes")),
        height=90,
        key=f"{prefix}_vacation_notes",
    )
    update_status = st.checkbox(
        "Atualizar status do funcionário se ele estiver em férias ou concluir o período",
        value=False,
        key=f"{prefix}_vacation_update_employee_status",
    )

    payload = build_vacation_payload(
        selected_employee,
        periodo_aquisitivo,
        data_inicio,
        data_fim,
        data_retorno,
        status,
        int(aviso_dias),
        observacoes,
    )
    return payload, update_status


def sync_employee_status_from_vacation(payload: dict[str, Any]) -> None:
    situation = calculated_vacation_situation(payload)
    if payload.get("status") in ["Concluída", "Cancelada"]:
        update_employee_status(payload["employee_id"], "Ativo")
    elif situation == "Em férias":
        update_employee_status(payload["employee_id"], "Férias")


def should_sync_employee_status_from_vacation(payload: dict[str, Any], update_status: bool) -> bool:
    return update_status or payload.get("status") in ["Concluída", "Cancelada"]


def render_vacations_tab(df: pd.DataFrame, vacations: pd.DataFrame) -> None:
    if df.empty:
        st.info("Cadastre o primeiro funcionário para lançar férias.")
        return

    pop_flash("vacation_message")
    open_vacations = filter_open_vacations(vacations)
    tab_alerts, tab_create, tab_edit = st.tabs(["Avisos", "Lançar férias", "Editar férias"])

    with tab_alerts:
        render_vacation_alerts(open_vacations)
        st.divider()
        render_vacation_table(open_vacations)

    with tab_create:
        with st.form("create_vacation_form", clear_on_submit=False):
            payload, update_status = render_vacation_form(df, "create")
            submitted = st.form_submit_button("Salvar férias", type="primary", width="stretch")

        if submitted:
            errors = validate_vacation(payload)
            if errors:
                show_errors(errors)
                return
            insert_vacation(payload)
            if should_sync_employee_status_from_vacation(payload, update_status):
                sync_employee_status_from_vacation(payload)
            st.session_state["vacation_message"] = "Férias lançadas com sucesso."
            st.rerun()

    with tab_edit:
        if open_vacations.empty:
            st.info("Nenhum lançamento de férias para editar.")
            return

        labels = {
            row["id"]: f"{row['funcionario']} | {format_date_br(row['data_inicio'])} a {format_date_br(row['data_fim'])}"
            for _, row in open_vacations.iterrows()
        }
        selected_id = st.selectbox(
            "Lançamento",
            options=open_vacations["id"].tolist(),
            format_func=lambda value: labels.get(value, value),
            key="edit_vacation_selected",
        )
        vacation = open_vacations[open_vacations["id"] == selected_id].iloc[0].to_dict()
        with st.form("edit_vacation_form", clear_on_submit=False):
            payload, update_status = render_vacation_form(df, "edit", vacation)
            submitted = st.form_submit_button("Salvar alterações das férias", type="primary", width="stretch")

        if submitted:
            errors = validate_vacation(payload)
            if errors:
                show_errors(errors)
                return
            update_vacation(selected_id, payload)
            if should_sync_employee_status_from_vacation(payload, update_status):
                sync_employee_status_from_vacation(payload)
            st.session_state["vacation_message"] = "Férias atualizadas com sucesso."
            st.rerun()


def build_leave_payload(
    employee_id: str,
    tipo: str,
    data_inicio: date,
    data_previsao_retorno: date | None,
    data_retorno: date | None,
    status: str,
    aviso_dias: int,
    motivo: str,
    documento: str,
    observacoes: str,
) -> dict[str, Any]:
    return {
        "employee_id": employee_id,
        "tipo": tipo,
        "data_inicio": date_to_db(data_inicio),
        "data_previsao_retorno": date_to_db(data_previsao_retorno),
        "data_retorno": date_to_db(data_retorno),
        "status": status,
        "aviso_dias": int(aviso_dias),
        "motivo": clean_text(motivo),
        "documento": clean_text(documento),
        "observacoes": clean_text(observacoes),
    }


def validate_leave(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    start = parse_iso_date(payload.get("data_inicio"))
    expected_return = parse_iso_date(payload.get("data_previsao_retorno"))
    actual_return = parse_iso_date(payload.get("data_retorno"))

    if not clean_text(payload.get("employee_id")):
        errors.append("Selecione um funcionário.")
    if not clean_text(payload.get("tipo")):
        errors.append("Selecione o tipo de afastamento.")
    if not start:
        errors.append("Informe a data de início.")
    if start and expected_return and expected_return < start:
        errors.append("A previsão de retorno não pode ser anterior ao início.")
    if start and actual_return and actual_return < start:
        errors.append("A data de retorno não pode ser anterior ao início.")
    if int(payload.get("aviso_dias") or 0) < 0:
        errors.append("O aviso em dias não pode ser negativo.")
    return errors


def render_leave_alerts(leaves: pd.DataFrame) -> None:
    if leaves.empty:
        st.info("Ainda não há afastamentos lançados.")
        return

    work = leaves.copy()
    work["dias_para_inicio"] = pd.to_numeric(work["dias_para_inicio"], errors="coerce")
    work["dias_para_retorno"] = pd.to_numeric(work["dias_para_retorno"], errors="coerce")
    work["aviso_dias"] = pd.to_numeric(work["aviso_dias"], errors="coerce").fillna(7)

    active = work[work["situacao_calculada"].isin(["Ativo", "Retorno vencido"])]
    scheduled = work[work["situacao_calculada"] == "Programado"]
    returning = active[
        (active["dias_para_retorno"] >= 0)
        & (active["dias_para_retorno"] <= active["aviso_dias"])
    ]
    overdue = work[work["situacao_calculada"] == "Retorno vencido"]
    no_return_date = active[active["data_previsao_retorno"].fillna("") == ""]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Afastados agora", len(active))
    col2.metric("Programados", len(scheduled))
    col3.metric("Retorno próximo", len(returning))
    col4.metric("Sem previsão", len(no_return_date))

    if not overdue.empty:
        st.markdown("**Atenção: retorno vencido**")
        for _, row in overdue.sort_values("data_previsao_retorno").head(8).iterrows():
            st.error(
                f"{row['funcionario']} tinha retorno previsto para "
                f"{format_date_br(row['data_previsao_retorno'])}."
            )

    if not returning.empty:
        st.markdown("**Retorno próximo**")
        for _, row in returning.sort_values("data_previsao_retorno").head(8).iterrows():
            days = int(row["dias_para_retorno"])
            when = "hoje" if days == 0 else f"em {days} dia(s)"
            st.warning(f"{row['funcionario']} tem retorno previsto {when}.")

    if not active.empty:
        st.markdown("**Afastados ativos**")
        for _, row in active.sort_values("data_inicio").head(8).iterrows():
            st.info(
                f"{row['funcionario']} está em {row['tipo']} desde "
                f"{format_date_br(row['data_inicio'])}. Retorno previsto: "
                f"{format_date_br(row['data_previsao_retorno']) or '-'}."
            )


def render_leave_table(leaves: pd.DataFrame) -> None:
    if leaves.empty:
        st.info("Nenhum afastamento encontrado.")
        return

    view = leaves.copy()
    view["CPF"] = view["cpf"].apply(format_cpf)
    view["Início"] = view["data_inicio"].apply(format_date_br)
    view["Previsão retorno"] = view["data_previsao_retorno"].apply(format_date_br)
    view["Retorno realizado"] = view["data_retorno"].apply(format_date_br)
    view = view.rename(
        columns={
            "funcionario": "Funcionário",
            "cargo": "Função",
            "setor": "Setor",
            "tipo": "Tipo",
            "situacao_calculada": "Situação",
            "status": "Status informado",
            "motivo": "Motivo",
            "documento": "Documento",
            "observacoes": "Observações",
        }
    )
    st.dataframe(
        view[
            [
                "Funcionário",
                "CPF",
                "Função",
                "Setor",
                "Tipo",
                "Início",
                "Previsão retorno",
                "Retorno realizado",
                "Situação",
                "Status informado",
                "Motivo",
                "Documento",
                "Observações",
            ]
        ],
        hide_index=True,
        width="stretch",
    )

    export = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar afastamentos em CSV",
        data=export,
        file_name="afastamentos_jr.csv",
        mime="text/csv",
        type="primary",
    )


def render_leave_form(
    df: pd.DataFrame,
    prefix: str,
    leave: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    leave = leave or {}
    labels = {row["id"]: employee_label(row) for _, row in df.iterrows()}
    employee_ids = df["id"].tolist()
    default_employee = clean_text(leave.get("employee_id"))
    default_employee_index = employee_ids.index(default_employee) if default_employee in employee_ids else 0

    selected_employee = st.selectbox(
        "Funcionário",
        options=employee_ids,
        index=default_employee_index,
        format_func=lambda value: labels.get(value, value),
        key=f"{prefix}_leave_employee",
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 0.8])
    tipo = col1.selectbox(
        "Tipo",
        LEAVE_TYPE_OPTIONS,
        index=pick_index(LEAVE_TYPE_OPTIONS, leave.get("tipo") or "Atestado médico"),
        key=f"{prefix}_leave_type",
    )
    start_default = parse_iso_date(leave.get("data_inicio")) or date.today()
    data_inicio = col2.date_input(
        "Início",
        value=start_default,
        format="DD/MM/YYYY",
        key=f"{prefix}_leave_start",
    )
    status = col3.selectbox(
        "Status",
        LEAVE_STATUS_OPTIONS,
        index=pick_index(LEAVE_STATUS_OPTIONS, leave.get("status") or "Ativo"),
        key=f"{prefix}_leave_status",
    )
    aviso_dias = col4.number_input(
        "Avisar antes",
        min_value=0,
        max_value=180,
        value=int(leave.get("aviso_dias") or 7),
        step=1,
        key=f"{prefix}_leave_notice",
    )

    col5, col6 = st.columns(2)
    expected_default = parse_iso_date(leave.get("data_previsao_retorno"))
    has_expected_return = col5.checkbox(
        "Tem previsão de retorno",
        value=expected_default is not None or not leave,
        key=f"{prefix}_leave_has_expected",
    )
    data_previsao_retorno = None
    if has_expected_return:
        data_previsao_retorno = col5.date_input(
            "Previsão de retorno",
            value=expected_default or (start_default + timedelta(days=7)),
            format="DD/MM/YYYY",
            key=f"{prefix}_leave_expected_return",
        )

    actual_default = parse_iso_date(leave.get("data_retorno"))
    has_actual_return = col6.checkbox(
        "Já retornou",
        value=actual_default is not None,
        key=f"{prefix}_leave_has_actual",
    )
    data_retorno = None
    if has_actual_return:
        data_retorno = col6.date_input(
            "Data do retorno",
            value=actual_default or date.today(),
            format="DD/MM/YYYY",
            key=f"{prefix}_leave_actual_return",
        )

    col7, col8 = st.columns([1.4, 1])
    motivo = col7.text_input(
        "Motivo",
        value=clean_text(leave.get("motivo")),
        placeholder="Ex.: cirurgia, tratamento, atestado de 3 dias",
        key=f"{prefix}_leave_reason",
    )
    documento = col8.text_input(
        "Documento/CID/Protocolo",
        value=clean_text(leave.get("documento")),
        key=f"{prefix}_leave_document",
    )
    observacoes = st.text_area(
        "Observações",
        value=clean_text(leave.get("observacoes")),
        height=90,
        key=f"{prefix}_leave_notes",
    )
    update_status = st.checkbox(
        "Atualizar status do funcionário para Afastado ou Ativo conforme este lançamento",
        value=False,
        key=f"{prefix}_leave_update_employee_status",
    )

    payload = build_leave_payload(
        selected_employee,
        tipo,
        data_inicio,
        data_previsao_retorno,
        data_retorno,
        status,
        int(aviso_dias),
        motivo,
        documento,
        observacoes,
    )
    return payload, update_status


def sync_employee_status_from_leave(payload: dict[str, Any]) -> None:
    situation = calculated_leave_situation(payload)
    if situation in ["Ativo", "Retorno vencido"]:
        update_employee_status(payload["employee_id"], "Afastado")
    elif situation == "Encerrado":
        update_employee_status(payload["employee_id"], "Ativo")


def render_leaves_tab(df: pd.DataFrame, leaves: pd.DataFrame) -> None:
    if df.empty:
        st.info("Cadastre o primeiro funcionário para lançar afastamentos.")
        return

    pop_flash("leave_message")
    tab_alerts, tab_create, tab_edit = st.tabs(["Avisos", "Lançar afastamento", "Editar afastamento"])

    with tab_alerts:
        render_leave_alerts(leaves)
        st.divider()
        render_leave_table(leaves)

    with tab_create:
        with st.form("create_leave_form", clear_on_submit=False):
            payload, update_status = render_leave_form(df, "create")
            submitted = st.form_submit_button("Salvar afastamento", type="primary", width="stretch")

        if submitted:
            errors = validate_leave(payload)
            if errors:
                show_errors(errors)
                return
            insert_leave_record(payload)
            if update_status:
                sync_employee_status_from_leave(payload)
            st.session_state["leave_message"] = "Afastamento lançado com sucesso."
            st.rerun()

    with tab_edit:
        if leaves.empty:
            st.info("Nenhum afastamento para editar.")
            return

        labels = {
            row["id"]: f"{row['funcionario']} | {row['tipo']} | {format_date_br(row['data_inicio'])}"
            for _, row in leaves.iterrows()
        }
        selected_id = st.selectbox(
            "Lançamento",
            options=leaves["id"].tolist(),
            format_func=lambda value: labels.get(value, value),
            key="edit_leave_selected",
        )
        leave = leaves[leaves["id"] == selected_id].iloc[0].to_dict()
        with st.form("edit_leave_form", clear_on_submit=False):
            payload, update_status = render_leave_form(df, "edit", leave)
            submitted = st.form_submit_button("Salvar alterações do afastamento", type="primary", width="stretch")

        if submitted:
            errors = validate_leave(payload)
            if errors:
                show_errors(errors)
                return
            update_leave_record(selected_id, payload)
            if update_status:
                sync_employee_status_from_leave(payload)
            st.session_state["leave_message"] = "Afastamento atualizado com sucesso."
            st.rerun()


def build_employee_report(df: pd.DataFrame) -> pd.DataFrame:
    report = df.copy()
    report["CPF"] = report["cpf"].apply(format_cpf)
    report["Celular"] = report["celular"].apply(format_phone)
    report["Admissão"] = report["data_admissao"].apply(format_date_br)
    report["Desligamento"] = report["data_desligamento"].apply(format_date_br) if "data_desligamento" in report.columns else ""
    return report.rename(
        columns={
            "nome": "Funcionário",
            "cargo": "Função",
            "setor": "Setor",
            "status": "Status",
            "matricula": "Matrícula",
            "gestor": "Gestor",
        }
    )


def build_vacation_report(vacations: pd.DataFrame) -> pd.DataFrame:
    report = vacations.copy()
    if report.empty:
        return report
    report["CPF"] = report["cpf"].apply(format_cpf)
    report["Início"] = report["data_inicio"].apply(format_date_br)
    report["Fim"] = report["data_fim"].apply(format_date_br)
    report["Retorno"] = report["data_retorno"].apply(format_date_br)
    return report.rename(
        columns={
            "funcionario": "Funcionário",
            "cargo": "Função",
            "setor": "Setor",
            "status": "Status",
            "situacao_calculada": "Situação",
        }
    )


def build_leave_report(leaves: pd.DataFrame) -> pd.DataFrame:
    report = leaves.copy()
    if report.empty:
        return report
    report["CPF"] = report["cpf"].apply(format_cpf)
    report["Início"] = report["data_inicio"].apply(format_date_br)
    report["Previsão retorno"] = report["data_previsao_retorno"].apply(format_date_br)
    report["Retorno"] = report["data_retorno"].apply(format_date_br)
    return report.rename(
        columns={
            "funcionario": "Funcionário",
            "cargo": "Função",
            "setor": "Setor",
            "tipo": "Tipo",
            "status": "Status",
            "situacao_calculada": "Situação",
        }
    )


def render_report_downloads(title: str, df: pd.DataFrame, columns: list[str], filename: str) -> None:
    st.markdown(f"**{title}**")
    col1, col2 = st.columns(2)
    report_df = ensure_report_columns(df, columns)
    col1.download_button(
        "CSV",
        data=dataframe_to_csv_bytes(report_df),
        file_name=f"{filename}.csv",
        mime="text/csv",
        width="stretch",
    )
    col2.download_button(
        "PDF",
        data=make_pdf_bytes(title, report_df, columns),
        file_name=f"{filename}.pdf",
        mime="application/pdf",
        width="stretch",
    )


def render_reports_tab(
    df: pd.DataFrame,
    vacations: pd.DataFrame,
    leaves: pd.DataFrame,
) -> None:
    employee_report = build_employee_report(df)
    vacation_report = build_vacation_report(vacations)
    leave_report = build_leave_report(leaves)
    birthdays = build_birthdays(df, days_limit=365)

    col1, col2 = st.columns(2)
    with col1:
        render_report_downloads(
            "Funcionários",
            employee_report,
            ["Funcionário", "CPF", "Função", "Setor", "Matrícula", "Admissão", "Status", "Gestor", "Desligamento"],
            "relatorio_funcionarios_jr",
        )
        render_report_downloads(
            "Férias",
            vacation_report,
            ["Funcionário", "CPF", "Função", "Setor", "Início", "Fim", "Retorno", "Status", "Situação"],
            "relatorio_ferias_jr",
        )
        render_report_downloads(
            "Aniversariantes",
            birthdays,
            ["Funcionário", "Setor", "Função", "Aniversário", "Próximo aniversário", "Dias"],
            "relatorio_aniversariantes_jr",
        )

    with col2:
        render_report_downloads(
            "Afastamentos",
            leave_report,
            ["Funcionário", "CPF", "Função", "Setor", "Tipo", "Início", "Previsão retorno", "Retorno", "Status", "Situação"],
            "relatorio_afastamentos_jr",
        )


def render_termination_form(employee_id: str, employee: dict[str, Any]) -> None:
    st.markdown('<div class="jr-section-title">Desligamento</div>', unsafe_allow_html=True)
    if employee.get("status") == "Desligado":
        st.info(
            f"Funcionário desligado em {format_date_br(employee.get('data_desligamento')) or '-'} "
            f"({employee.get('motivo_desligamento') or 'motivo não informado'})."
        )
        return

    with st.expander("Desligar funcionário"):
        with st.form("termination_form", clear_on_submit=False):
            col1, col2 = st.columns([0.8, 1.2])
            data_desligamento = col1.date_input(
                "Data de desligamento",
                value=date.today(),
                max_value=date.today(),
                format="DD/MM/YYYY",
            )
            motivo = col2.selectbox("Motivo", TERMINATION_REASON_OPTIONS)
            observacoes = st.text_area("Observações do desligamento", height=90)
            confirmacao = st.text_input("Digite DESLIGAR para confirmar")
            submitted = st.form_submit_button("Confirmar desligamento", type="primary", width="stretch")

        if submitted:
            if confirmacao.strip().upper() != "DESLIGAR":
                st.error("Digite DESLIGAR para confirmar o desligamento.")
                return
            terminate_employee(employee_id, data_desligamento, motivo, observacoes)
            st.success("Funcionário desligado com sucesso.")
            st.rerun()


def render_edit_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Cadastre o primeiro funcionário para habilitar a edição.")
        return

    labels = {row["id"]: employee_label(row) for _, row in df.iterrows()}
    selected_id = st.selectbox(
        "Funcionário",
        options=df["id"].tolist(),
        format_func=lambda value: labels.get(value, value),
        key="edit_selected_employee",
    )
    employee = get_employee(selected_id)
    if not employee:
        st.warning("Cadastro não encontrado.")
        return
    contacts = get_contacts(selected_id)

    with st.form("edit_employee_form", clear_on_submit=False):
        payload, contact_payload = render_employee_fields("edit", employee, contacts)
        submitted = st.form_submit_button("Salvar alterações", type="primary", width="stretch")

    if submitted:
        errors = validate_employee(payload, contact_payload, exclude_id=selected_id)
        if errors:
            show_errors(errors)
            return
        update_employee(selected_id, payload, contact_payload)
        st.success("Cadastro atualizado com sucesso.")

    render_termination_form(selected_id, employee)


def main() -> None:
    apply_theme()
    init_db()
    df = load_employees()
    vacations = load_vacations()
    leaves = load_leave_records()

    render_header()
    render_overview(df, vacations, leaves)

    tab_summary, tab_create, tab_search, tab_vacations, tab_leaves, tab_reports, tab_edit = st.tabs(
        ["Resumo", "Cadastrar", "Consultar", "Férias", "Afastamentos", "Relatórios", "Editar"]
    )
    with tab_summary:
        render_summary_tab(df, vacations, leaves)
    with tab_create:
        render_create_tab()
    with tab_search:
        render_search_tab(df)
    with tab_vacations:
        render_vacations_tab(df, vacations)
    with tab_leaves:
        render_leaves_tab(df, leaves)
    with tab_reports:
        render_reports_tab(df, vacations, leaves)
    with tab_edit:
        render_edit_tab(df)


if __name__ == "__main__":
    main()
