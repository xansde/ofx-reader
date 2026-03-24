#!/usr/bin/env python3
"""Standalone OFX file reader — shows transactions in a formatted table."""

import csv
import io
import re
import sys
from datetime import datetime
from pathlib import Path

BANKS = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "104": "Caixa Econômica",
    "237": "Bradesco",
    "260": "Nubank",
    "341": "Itaú",
    "077": "Inter",
    "336": "C6 Bank",
    "212": "Original",
    "756": "Sicoob",
    "748": "Sicredi",
    "422": "Safra",
    "655": "Neon/Votorantim",
    "290": "PagSeguro",
    "380": "PicPay",
    "403": "Cora",
}

CATEGORIES = {
    "756": [  # Sicoob
        ("PIX RECEBIDO", "PIX recebido"),
        ("PIX EMITIDO", "PIX enviado"),
        ("CRÉD.LIQUIDAÇÃO COBRANÇA", "Boleto creditado"),
        ("CRÉD.TED-STR", "TED recebida"),
        ("DÉB.TIT.COMPE", "Boleto pago"),
        ("DÉB.CONV.EN.ELÉTRICA", "Boleto pago"),
        ("DÉB.CONV.GÁS", "Boleto pago"),
        ("DÉB.TRANSF.CONTAS", "Transferência/entre contas"),
        ("CRÉD.TRANSF.CONTAS", "Transferência/entre contas"),
        ("PAGAMENTO SALARIO", "Folha de pagamento"),
        ("TARIFA COBRANÇA", "Tarifa bancária"),
        ("DÉBITO PACOTE SERVIÇOS", "Tarifa bancária"),
        ("DÉB.IOF", "Impostos/tributos"),
        ("DÉB.EMPRÉSTIMO", "Outros débitos"),
        ("JUROS CONTA GARANTIDA", "Outros débitos"),
        ("DEB.PARCELAS", "Outros débitos"),
    ],
}

CARD_PATTERNS = {
    "756": [
        (["MASTERCARD", "DÉB.CONV"], "Pagamento Cartão de Crédito"),
        (["VISA", "DÉB.CONV"], "Pagamento Cartão de Crédito"),
    ],
}

INVESTMENT_KEYWORDS = ["RESGATE", "APLICAÇÃO", "APLICACAO"]


def categorize_transaction(memo: str, amount: float, bank_id: str) -> str:
    upper = memo.upper()
    for keywords, category in CARD_PATTERNS.get(bank_id, []):
        if all(k.upper() in upper for k in keywords):
            return category
    for pattern, category in CATEGORIES.get(bank_id, []):
        if pattern.upper() in upper:
            return category
    return "Outros créditos" if amount >= 0 else "Outros débitos"


def derive_month(date_str: str) -> str:
    parts = date_str.split("/")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}"
    return ""


def is_entrada_sem_resgates(amount: float, memo: str) -> bool:
    if amount < 0:
        return False
    upper = memo.upper()
    return not any(k in upper for k in INVESTMENT_KEYWORDS)


def is_saida_sem_aplicacao(amount: float, memo: str) -> bool:
    if amount >= 0:
        return False
    upper = memo.upper()
    return not any(k in upper for k in INVESTMENT_KEYWORDS)


def extract_tag(text: str, tag: str) -> str:
    pattern = rf"<{tag}>\s*(.+?)(?:\s*<|\s*$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_date(raw: str) -> str:
    clean = raw.split("[")[0].strip()
    try:
        dt = datetime.strptime(clean, "%Y%m%d%H%M%S")
    except ValueError:
        try:
            dt = datetime.strptime(clean, "%Y%m%d")
        except ValueError:
            return clean
    return dt.strftime("%d/%m/%Y")


def parse_transactions(content: str, bank_id: str) -> list[dict]:
    transactions = []
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL)

    for block in blocks:
        amount_str = extract_tag(block, "TRNAMT")
        try:
            amount = float(amount_str.replace(",", "."))
        except ValueError:
            amount = 0.0

        memo = extract_tag(block, "MEMO")
        date = parse_date(extract_tag(block, "DTPOSTED"))

        transactions.append({
            "date": date,
            "month": derive_month(date),
            "type": "Entrada" if amount >= 0 else "Saída",
            "category": categorize_transaction(memo, amount, bank_id),
            "amount": amount,
            "entrada_sem_resgates": is_entrada_sem_resgates(amount, memo),
            "saida_sem_aplicacao": is_saida_sem_aplicacao(amount, memo),
            "memo": memo,
        })

    return transactions


def parse_bank(content: str) -> dict:
    bank_id = extract_tag(content, "BANKID")
    account = extract_tag(content, "ACCTID")
    balance_str = extract_tag(content, "BALAMT")

    try:
        balance = float(balance_str.replace(",", "."))
    except ValueError:
        balance = None

    return {
        "bank_id": bank_id,
        "bank_name": BANKS.get(bank_id, f"Banco {bank_id}"),
        "account": account,
        "balance": balance,
    }


def format_brl(value: float) -> str:
    sign = "-" if value < 0 else " "
    return f"{sign}R$ {abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def print_table(bank: dict, transactions: list[dict]) -> None:
    print(f"\n{'=' * 110}")
    print(f"  Banco: {bank['bank_name']}  |  Conta: {bank['account']}")
    if bank["balance"] is not None:
        print(f"  Saldo: {format_brl(bank['balance'])}")
    print(f"{'=' * 110}")

    header = f"{'Data':<12} {'Mês':<8} {'Tipo':<8} {'Categoria':<30} {'Valor':>14}  {'E.s/R':>5} {'S.s/A':>5}  {'Descrição'}"
    print(f"\n{header}")
    print("-" * 110)

    total_in = 0.0
    total_out = 0.0

    for t in sorted(transactions, key=lambda x: x["date"]):
        tipo = f"\033[32m{'Entrada':<8}\033[0m" if t["type"] == "Entrada" else f"\033[31m{'Saída':<8}\033[0m"
        e_flag = "TRUE" if t["entrada_sem_resgates"] else ""
        s_flag = "TRUE" if t["saida_sem_aplicacao"] else ""
        desc = t["memo"][:40]
        print(f"{t['date']:<12} {t['month']:<8} {tipo} {t['category']:<30} {format_brl(t['amount']):>14}  {e_flag:>5} {s_flag:>5}  {desc}")

        if t["amount"] >= 0:
            total_in += t["amount"]
        else:
            total_out += t["amount"]

    print("-" * 110)
    print(f"{'Total Entradas:':<24} \033[32m{format_brl(total_in):>14}\033[0m")
    print(f"{'Total Saídas:':<24} \033[31m{format_brl(total_out):>14}\033[0m")
    print(f"{'Resultado:':<24} {format_brl(total_in + total_out):>14}")
    print(f"{'=' * 110}\n")


def export_csv(transactions: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Data", "Mês", "Tipo", "Categoria", "Valor",
            "Conta_Entrada_sem_resgates", "Conta_Saida_sem_aplicação", "Descricao"
        ])
        for t in sorted(transactions, key=lambda x: x["date"]):
            writer.writerow([
                t["date"],
                t["month"],
                t["type"],
                t["category"],
                f'{t["amount"]:.2f}'.replace(".", ","),
                t["entrada_sem_resgates"],
                t["saida_sem_aplicacao"],
                t["memo"],
            ])


def main():
    if len(sys.argv) < 2:
        print("Uso: python ofx_reader.py <arquivo.ofx>")
        sys.exit(1)

    csv_path = None
    if "--csv" in sys.argv:
        idx = sys.argv.index("--csv")
        if idx + 1 < len(sys.argv):
            csv_path = Path(sys.argv[idx + 1])

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Arquivo não encontrado: {filepath}")
        sys.exit(1)

    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            content = filepath.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    else:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    bank = parse_bank(content)
    transactions = parse_transactions(content, bank["bank_id"])

    if not transactions:
        print("Nenhuma transação encontrada no arquivo.")
        sys.exit(1)

    print_table(bank, transactions)

    if csv_path:
        export_csv(transactions, csv_path)
        print(f"CSV exportado: {csv_path}")


if __name__ == "__main__":
    main()
