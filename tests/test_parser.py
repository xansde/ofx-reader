import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_OFX = """
<BANKACCTFROM>
<BANKID>756
<ACCTID>12345-6
</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260301120000[-3:BRT]
<TRNAMT>5500.00
<FITID>1
<MEMO>Pix PIX RECEBIDO - OUTRA IF
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260302120000[-3:BRT]
<TRNAMT>-150.00
<FITID>2
<MEMO>516961 TARIFA COBRANÇA
</STMTTRN>
</BANKTRANLIST>
"""

from ofx_reader import parse_transactions, parse_bank

def test_parse_transactions_8_fields():
    txns = parse_transactions(SAMPLE_OFX, "756")
    assert len(txns) == 2
    t = txns[0]
    assert "date" in t
    assert "month" in t
    assert "type" in t
    assert "category" in t
    assert "amount" in t
    assert "entrada_sem_resgates" in t
    assert "saida_sem_aplicacao" in t
    assert "memo" in t

def test_parse_transactions_categorization():
    txns = parse_transactions(SAMPLE_OFX, "756")
    pix = [t for t in txns if t["amount"] == 5500.0][0]
    assert pix["category"] == "PIX recebido"
    assert pix["type"] == "Entrada"
    assert pix["month"] == "2026-03"
    assert pix["entrada_sem_resgates"] == True
    assert pix["saida_sem_aplicacao"] == False

def test_parse_transactions_saida():
    txns = parse_transactions(SAMPLE_OFX, "756")
    tarifa = [t for t in txns if t["amount"] == -150.0][0]
    assert tarifa["category"] == "Tarifa bancária"
    assert tarifa["type"] == "Saída"
    assert tarifa["entrada_sem_resgates"] == False
    assert tarifa["saida_sem_aplicacao"] == True

def test_parse_bank():
    bank = parse_bank(SAMPLE_OFX)
    assert bank["bank_id"] == "756"
    assert bank["bank_name"] == "Sicoob"
    assert bank["account"] == "12345-6"
