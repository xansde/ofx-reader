import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ofx_reader import categorize_transaction, derive_month, is_entrada_sem_resgates, is_saida_sem_aplicacao

def test_pix_recebido():
    assert categorize_transaction("Pix PIX RECEBIDO - OUTRA IF", 1200.0, "756") == "PIX recebido"

def test_pix_enviado():
    assert categorize_transaction("Pix PIX EMITIDO OUTRA IF", -500.0, "756") == "PIX enviado"

def test_boleto_pago():
    assert categorize_transaction("4002721 DÉB.TIT.COMPE EFETIVADO", -898.33, "756") == "Boleto pago"

def test_boleto_creditado():
    assert categorize_transaction("516275 CRÉD.LIQUIDAÇÃO COBRANÇA", 933.33, "756") == "Boleto creditado"

def test_ted_recebida():
    assert categorize_transaction("353683093 CRÉD.TED-STR | ESTALEIRO", 1962.89, "756") == "TED recebida"

def test_transferencia():
    assert categorize_transaction("4009615 DÉB.TRANSF.CONTAS DIF.TITULARIDADE", -1200.0, "756") == "Transferência/entre contas"

def test_transferencia_sem_acento():
    assert categorize_transaction("CRED.TRANSF.CONTAS INTERCREDIS", 3250.0, "756") == "Transferência/entre contas"

def test_folha_pagamento():
    assert categorize_transaction("4011265 DEBITO PAGAMENTO SALARIO", -42800.30, "756") == "Folha de pagamento"

def test_tarifa():
    assert categorize_transaction("516961 TARIFA COBRANÇA", -1.0, "756") == "Tarifa bancária"

def test_impostos():
    assert categorize_transaction("IOF/2-1 DÉB.IOF", -1.38, "756") == "Impostos/tributos"

def test_cartao_credito():
    assert categorize_transaction("MASTERCARD DÉB.CONV.DEMAIS EMPRESAS", -4708.37, "756") == "Pagamento Cartão de Crédito"

def test_outros_debitos():
    assert categorize_transaction("00390777 DÉB.EMPRÉSTIMO", -4894.53, "756") == "Outros débitos"

def test_fallback_credito():
    assert categorize_transaction("ALGO DESCONHECIDO", 100.0, "756") == "Outros créditos"

def test_fallback_debito():
    assert categorize_transaction("ALGO DESCONHECIDO", -100.0, "756") == "Outros débitos"

def test_derive_month():
    assert derive_month("02/01/2026") == "2026-01"
    assert derive_month("15/03/2026") == "2026-03"
    assert derive_month("invalid") == ""

def test_entrada_sem_resgates_normal():
    assert is_entrada_sem_resgates(1200.0, "PIX RECEBIDO") == True

def test_entrada_sem_resgates_resgate():
    assert is_entrada_sem_resgates(5000.0, "RESGATE APLICAÇÃO CDB") == False

def test_entrada_sem_resgates_saida():
    assert is_entrada_sem_resgates(-100.0, "PIX EMITIDO") == False

def test_saida_sem_aplicacao_normal():
    assert is_saida_sem_aplicacao(-500.0, "PIX EMITIDO") == True

def test_saida_sem_aplicacao_aplicacao():
    assert is_saida_sem_aplicacao(-10000.0, "APLICAÇÃO CDB") == False

def test_saida_sem_aplicacao_entrada():
    assert is_saida_sem_aplicacao(100.0, "PIX RECEBIDO") == False
