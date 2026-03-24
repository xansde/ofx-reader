#!/usr/bin/env python3
"""Standalone OFX file reader — shows transactions in a formatted table."""

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


def parse_transactions(content: str) -> list[dict]:
    transactions = []
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL)

    for block in blocks:
        amount_str = extract_tag(block, "TRNAMT")
        try:
            amount = float(amount_str.replace(",", "."))
        except ValueError:
            amount = 0.0

        transactions.append({
            "date": parse_date(extract_tag(block, "DTPOSTED")),
            "category": "Entrada" if amount >= 0 else "Saída",
            "amount": amount,
            "memo": extract_tag(block, "MEMO"),
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
    print(f"\n{'=' * 72}")
    print(f"  Banco: {bank['bank_name']}  |  Conta: {bank['account']}")
    if bank["balance"] is not None:
        print(f"  Saldo: {format_brl(bank['balance'])}")
    print(f"{'=' * 72}")

    header = f"{'Data':<12} {'Categoria':<10} {'Valor':>16}  {'Descrição'}"
    print(f"\n{header}")
    print("-" * 72)

    total_in = 0.0
    total_out = 0.0

    for t in sorted(transactions, key=lambda x: x["date"]):
        cat_display = f"\033[32m{'Entrada':<10}\033[0m" if t["category"] == "Entrada" else f"\033[31m{'Saída':<10}\033[0m"
        print(f"{t['date']:<12} {cat_display} {format_brl(t['amount']):>16}  {t['memo']}")

        if t["amount"] >= 0:
            total_in += t["amount"]
        else:
            total_out += t["amount"]

    print("-" * 72)
    print(f"{'Total Entradas:':<24} \033[32m{format_brl(total_in):>16}\033[0m")
    print(f"{'Total Saídas:':<24} \033[31m{format_brl(total_out):>16}\033[0m")
    print(f"{'Resultado:':<24} {format_brl(total_in + total_out):>16}")
    print(f"{'=' * 72}\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python ofx_reader.py <arquivo.ofx>")
        sys.exit(1)

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
    transactions = parse_transactions(content)

    if not transactions:
        print("Nenhuma transação encontrada no arquivo.")
        sys.exit(1)

    print_table(bank, transactions)


if __name__ == "__main__":
    main()
