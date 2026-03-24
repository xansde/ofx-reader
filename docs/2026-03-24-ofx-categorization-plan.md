# OFX Reader — Categorization & 8-Column Output

> **For agentic workers:** Use executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the OFX reader to auto-categorize transactions and output an 8-column table matching the reference spreadsheet.

**Architecture:** Add a categorization engine (dict-based pattern matching per bank) to both Python CLI and HTML frontend. Both produce identical output: Data, Mes, Tipo, Categoria, Valor, Conta_Entrada_sem_resgates, Conta_Saida_sem_aplicacao, Descricao. HTML gets an "Exportar CSV" button.

**Tech Stack:** Python 3 (stdlib only), vanilla HTML/JS (no dependencies)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ofx_reader.py` | Modify | Add categorization dict, update parser, 8-col output, CSV export |
| `index.html` | Modify | Mirror categorization in JS, 8-col table, CSV export button |
| `sample.ofx` | Keep | Test fixture |

---

## Task 1: Add Sicoob Categorization Rules to Python

**Files:**
- Modify: `ofx_reader.py:9-26` (after BANKS dict)

- [ ] **Step 1: Add CATEGORIES dict after BANKS dict**

```python
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
```

- [ ] **Step 2: Add categorize_transaction function**

```python
def categorize_transaction(memo: str, amount: float, bank_id: str) -> str:
    upper = memo.upper()
    for keywords, category in CARD_PATTERNS.get(bank_id, []):
        if all(k.upper() in upper for k in keywords):
            return category
    for pattern, category in CATEGORIES.get(bank_id, []):
        if pattern.upper() in upper:
            return category
    return "Outros créditos" if amount >= 0 else "Outros débitos"
```

- [ ] **Step 3: Add derive_month function**

```python
def derive_month(date_str: str) -> str:
    """dd/mm/yyyy -> yyyy-mm"""
    parts = date_str.split("/")
    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}"
    return ""
```

- [ ] **Step 4: Add boolean column helpers**

```python
INVESTMENT_KEYWORDS = ["RESGATE", "APLICAÇÃO", "APLICACAO"]

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
```

- [ ] **Step 5: Verify syntax**

Run: `python3 -c "exec(open('ofx_reader.py').read())"` from project dir
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add ofx_reader.py
git commit -m "feat: add Sicoob categorization rules and helpers"
```

---

## Task 2: Update Python Parser for 8-Column Output

**Files:**
- Modify: `ofx_reader.py:47-65` (parse_transactions)
- Modify: `ofx_reader.py:68-83` (parse_bank — need bank_id passed through)
- Modify: `ofx_reader.py:91-118` (print_table)

- [ ] **Step 1: Update parse_transactions to include all 8 fields**

Replace the function body to produce 8-column dicts:

```python
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
```

- [ ] **Step 2: Update main() to pass bank_id**

```python
    bank = parse_bank(content)
    transactions = parse_transactions(content, bank["bank_id"])
```

- [ ] **Step 3: Update print_table for 8 columns**

Replace print_table:

```python
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
```

- [ ] **Step 4: Test with real OFX**

Run: `python3 ofx_reader.py /mnt/c/Users/xansd/Downloads/extrato-conta-corrente-ofx-unix_202603_20260324194847.ofx`
Expected: 8-column table with categories like "PIX recebido", "Tarifa bancária", etc.

- [ ] **Step 5: Commit**

```bash
git add ofx_reader.py
git commit -m "feat: 8-column output with auto-categorization"
```

---

## Task 3: Add CSV Export to Python

**Files:**
- Modify: `ofx_reader.py` (add export_csv function + CLI flag)

- [ ] **Step 1: Add export_csv function**

```python
import csv
import io

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
```

- [ ] **Step 2: Add --csv flag to main()**

```python
def main():
    if len(sys.argv) < 2:
        print("Uso: python ofx_reader.py <arquivo.ofx> [--csv output.csv]")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    csv_path = None
    if "--csv" in sys.argv:
        idx = sys.argv.index("--csv")
        if idx + 1 < len(sys.argv):
            csv_path = Path(sys.argv[idx + 1])

    # ... (existing file reading code) ...

    bank = parse_bank(content)
    transactions = parse_transactions(content, bank["bank_id"])

    if not transactions:
        print("Nenhuma transação encontrada no arquivo.")
        sys.exit(1)

    print_table(bank, transactions)

    if csv_path:
        export_csv(transactions, csv_path)
        print(f"CSV exportado: {csv_path}")
```

- [ ] **Step 3: Test CSV export**

Run: `python3 ofx_reader.py /mnt/c/Users/xansd/Downloads/extrato-*.ofx --csv /tmp/test_export.csv && head -5 /tmp/test_export.csv`
Expected: CSV with header row and BRL-formatted values

- [ ] **Step 4: Commit**

```bash
git add ofx_reader.py
git commit -m "feat: add CSV export with --csv flag"
```

---

## Task 4: Update HTML — Categorization Engine in JS

**Files:**
- Modify: `index.html:194-261` (script section)

- [ ] **Step 1: Add categorization rules and helpers to JS (before parseOFX)**

```javascript
const CATEGORIES = {
  '756': [ // Sicoob
    ['PIX RECEBIDO', 'PIX recebido'],
    ['PIX EMITIDO', 'PIX enviado'],
    ['CRÉD.LIQUIDAÇÃO COBRANÇA', 'Boleto creditado'],
    ['CRÉD.TED-STR', 'TED recebida'],
    ['DÉB.TIT.COMPE', 'Boleto pago'],
    ['DÉB.CONV.EN.ELÉTRICA', 'Boleto pago'],
    ['DÉB.CONV.GÁS', 'Boleto pago'],
    ['DÉB.TRANSF.CONTAS', 'Transferência/entre contas'],
    ['CRÉD.TRANSF.CONTAS', 'Transferência/entre contas'],
    ['PAGAMENTO SALARIO', 'Folha de pagamento'],
    ['TARIFA COBRANÇA', 'Tarifa bancária'],
    ['DÉBITO PACOTE SERVIÇOS', 'Tarifa bancária'],
    ['DÉB.IOF', 'Impostos/tributos'],
    ['DÉB.EMPRÉSTIMO', 'Outros débitos'],
    ['JUROS CONTA GARANTIDA', 'Outros débitos'],
    ['DEB.PARCELAS', 'Outros débitos'],
  ],
};

const CARD_PATTERNS = {
  '756': [
    [['MASTERCARD', 'DÉB.CONV'], 'Pagamento Cartão de Crédito'],
    [['VISA', 'DÉB.CONV'], 'Pagamento Cartão de Crédito'],
  ],
};

const INVESTMENT_KW = ['RESGATE', 'APLICAÇÃO', 'APLICACAO'];

function categorize(memo, amount, bankId) {
  const upper = memo.toUpperCase();
  for (const [keywords, cat] of (CARD_PATTERNS[bankId] || [])) {
    if (keywords.every(k => upper.includes(k.toUpperCase()))) return cat;
  }
  for (const [pattern, cat] of (CATEGORIES[bankId] || [])) {
    if (upper.includes(pattern.toUpperCase())) return cat;
  }
  return amount >= 0 ? 'Outros créditos' : 'Outros débitos';
}

function deriveMonth(dateStr) {
  const p = dateStr.split('/');
  return p.length === 3 ? `${p[2]}-${p[1]}` : '';
}

function isEntradaSemResgates(amount, memo) {
  if (amount < 0) return false;
  const u = memo.toUpperCase();
  return !INVESTMENT_KW.some(k => u.includes(k));
}

function isSaidaSemAplicacao(amount, memo) {
  if (amount >= 0) return false;
  const u = memo.toUpperCase();
  return !INVESTMENT_KW.some(k => u.includes(k));
}
```

- [ ] **Step 2: Update parseOFX to use categorization**

Replace the transaction mapping inside parseOFX:

```javascript
function parseOFX(content) {
  const account = extractTag(content, 'ACCTID');
  const balanceStr = extractTag(content, 'BALAMT');
  const balance = parseFloat(balanceStr.replace(',', '.')) || 0;
  const bankId = document.getElementById('bank-select').value;

  const blocks = [...content.matchAll(/<STMTTRN>([\s\S]*?)<\/STMTTRN>/g)];
  const transactions = blocks.map(m => {
    const block = m[1];
    const amount = parseFloat(extractTag(block, 'TRNAMT').replace(',', '.')) || 0;
    const memo = extractTag(block, 'MEMO');
    const date = parseDate(extractTag(block, 'DTPOSTED'));
    return {
      date,
      month: deriveMonth(date),
      type: amount >= 0 ? 'Entrada' : 'Saída',
      category: categorize(memo, amount, bankId),
      amount,
      entradaSemResgates: isEntradaSemResgates(amount, memo),
      saidaSemAplicacao: isSaidaSemAplicacao(amount, memo),
      memo,
    };
  });

  transactions.sort((a, b) => a.date.localeCompare(b.date));
  render(account, balance, transactions);
}
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add categorization engine to HTML frontend"
```

---

## Task 5: Update HTML — 8-Column Table + Export CSV

**Files:**
- Modify: `index.html` (thead, render function, add export button + styles)

- [ ] **Step 1: Update table header (line 176-183)**

```html
<thead>
  <tr>
    <th>Data</th>
    <th>Mês</th>
    <th>Tipo</th>
    <th>Categoria</th>
    <th>Valor</th>
    <th>Ent.s/R</th>
    <th>Saí.s/A</th>
    <th>Descrição</th>
  </tr>
</thead>
```

- [ ] **Step 2: Add export button after controls div**

```html
<button id="export-csv" style="display:none;" class="file-label">Exportar CSV</button>
```

- [ ] **Step 3: Update render function for 8 columns**

```javascript
function render(account, balance, transactions) {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('results').style.display = 'block';
  document.getElementById('export-csv').style.display = 'inline-block';

  document.getElementById('account').textContent = account || '—';

  let totalIn = 0, totalOut = 0;
  transactions.forEach(t => {
    if (t.amount >= 0) totalIn += t.amount;
    else totalOut += t.amount;
  });

  document.getElementById('total-in').textContent = formatBRL(totalIn);
  document.getElementById('total-out').textContent = formatBRL(totalOut);
  document.getElementById('balance').textContent = formatBRL(balance || totalIn + totalOut);

  const tbody = document.getElementById('tbody');
  tbody.innerHTML = transactions.map(t => `
    <tr>
      <td>${t.date}</td>
      <td>${t.month}</td>
      <td><span class="tag ${t.type === 'Entrada' ? 'entrada' : 'saida'}">${t.type}</span></td>
      <td>${t.category}</td>
      <td>${formatBRL(t.amount)}</td>
      <td>${t.entradaSemResgates ? 'TRUE' : ''}</td>
      <td>${t.saidaSemAplicacao ? 'TRUE' : ''}</td>
      <td>${t.memo}</td>
    </tr>
  `).join('');

  // Store for CSV export
  window._transactions = transactions;
}
```

- [ ] **Step 4: Add CSV export handler**

```javascript
document.getElementById('export-csv').addEventListener('click', () => {
  const t = window._transactions;
  if (!t || !t.length) return;

  const header = 'Data,Mês,Tipo,Categoria,Valor,Conta_Entrada_sem_resgates,Conta_Saida_sem_aplicação,Descricao\n';
  const rows = t.map(r =>
    `${r.date},${r.month},${r.type},${r.category},"${r.amount.toFixed(2).replace('.', ',')}",${r.entradaSemResgates},${r.saidaSemAplicacao},"${r.memo.replace(/"/g, '""')}"`
  ).join('\n');

  const blob = new Blob(['\uFEFF' + header + rows], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'extrato.csv';
  a.click();
  URL.revokeObjectURL(url);
});
```

- [ ] **Step 5: Add CSS for wider table**

Update `.container` max-width to `1200px` and add `th:nth-child(5)` right-align for Valor column.

- [ ] **Step 6: Test in browser**

Open `index.html`, upload the real OFX file.
Verify: 8 columns rendered, categories correct, export CSV downloads valid file.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "feat: 8-column table with CSV export in frontend"
```

---

## Task 6: Final Verification

- [ ] **Step 1: Test Python CLI 8-col output**

```bash
python3 ofx_reader.py /mnt/c/Users/xansd/Downloads/extrato-*.ofx
```

Verify categories match reference spreadsheet.

- [ ] **Step 2: Test Python CSV export**

```bash
python3 ofx_reader.py /mnt/c/Users/xansd/Downloads/extrato-*.ofx --csv /tmp/extrato.csv
```

Open CSV and compare against Google Sheets reference.

- [ ] **Step 3: Test HTML frontend**

Open in browser, upload OFX, verify 8 columns, click "Exportar CSV".

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete 8-column OFX reader with categorization"
```
