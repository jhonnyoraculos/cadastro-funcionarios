# Cadastro de Funcionários

Aplicativo Streamlit para cadastrar e consultar funcionários da JR Ferragens e Madeiras.

## Como rodar

```bat
python -m streamlit run app.py
```

Ou abra o arquivo `rodar_site.bat`.

## Dados

O app usa Postgres/Neon quando `DATABASE_URL` estiver configurada nos Secrets do Streamlit.
Sem `DATABASE_URL`, ele usa o banco local `funcionarios.db` como fallback.

No Streamlit Cloud, configure em **Settings > Secrets**:

```toml
DATABASE_URL = "postgresql://usuario:senha@host/neondb?sslmode=require"
```

Depois reinicie o app.

Ele salva:

- dados pessoais;
- CPF com validação;
- endereço;
- função, setor, matrícula e contrato;
- contatos familiares e de emergência;
- status do funcionário;
- histórico automático de alterações;
- aniversariantes e resumo inicial;
- controle de férias com avisos de entrada, retorno e pendências;
- controle de afastamentos, atestados e licenças com previsão de retorno;
- desligamento com data e motivo;
- relatórios em CSV e PDF;
- exportação em CSV.
