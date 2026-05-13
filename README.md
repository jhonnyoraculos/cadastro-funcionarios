# Cadastro de Funcionários

Aplicativo Streamlit para cadastrar e consultar funcionários da JR Ferragens e Madeiras.

## Como rodar

```bat
python -m streamlit run app.py
```

Ou abra o arquivo `rodar_site.bat`.

## Dados

O app cria automaticamente o banco local `funcionarios.db` na mesma pasta. Ele salva:

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
