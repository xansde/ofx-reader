import sys, os, csv, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from ofx_reader import export_csv

def test_export_csv_creates_file():
    transactions = [
        {"date": "01/03/2026", "month": "2026-03", "type": "Entrada", "category": "PIX recebido",
         "amount": 5500.0, "entrada_sem_resgates": True, "saida_sem_aplicacao": False, "memo": "PIX RECEBIDO"},
        {"date": "02/03/2026", "month": "2026-03", "type": "Saída", "category": "Tarifa bancária",
         "amount": -25.0, "entrada_sem_resgates": False, "saida_sem_aplicacao": True, "memo": "TARIFA COBRANÇA"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = Path(f.name)
    export_csv(transactions, path)
    assert path.exists()
    content = path.read_text(encoding="utf-8-sig")
    assert "Data" in content
    assert "PIX recebido" in content
    assert "5500,00" in content
    path.unlink()

def test_export_csv_header():
    transactions = []
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = Path(f.name)
    export_csv(transactions, path)
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == ["Data", "Mês", "Tipo", "Categoria", "Valor", "Conta_Entrada_sem_resgates", "Conta_Saida_sem_aplicação", "Descricao"]
    path.unlink()

def test_export_csv_row_count():
    transactions = [
        {"date": "01/03/2026", "month": "2026-03", "type": "Entrada", "category": "PIX recebido",
         "amount": 100.0, "entrada_sem_resgates": True, "saida_sem_aplicacao": False, "memo": "TEST"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = Path(f.name)
    export_csv(transactions, path)
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) == 2  # header + 1 row
    path.unlink()
