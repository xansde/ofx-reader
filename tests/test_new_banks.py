import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ofx_reader import categorize_transaction, is_entrada_sem_resgates, is_saida_sem_aplicacao

# CEF (104)
def test_cef_pix_recebido():
    assert categorize_transaction("CRE PIX CH", 7400.0, "104") == "PIX recebido"

def test_cef_tarifa():
    assert categorize_transaction("TAR PIX", -11.22, "104") == "Tarifa bancária"

def test_cef_emprestimo():
    assert categorize_transaction("PREST EMP", -7141.53, "104") == "Parcela de empréstimo"

def test_cef_transferencia():
    assert categorize_transaction("CPP CA CR", -8951.0, "104") == "Transferência/entre contas"

def test_cef_tarifa_cesta():
    assert categorize_transaction("DB T CESTA", -125.0, "104") == "Tarifa bancária"

# Itaú (341)
def test_itau_pix_recebido():
    assert categorize_transaction("PIX RECEBIDO JOSE RO02/01 | JOSE ROBERTO", 8000.0, "341") == "PIX recebido"

def test_itau_pix_enviado():
    assert categorize_transaction("PIX ENVIADO | ALEXANDRO MACHADO", -400.0, "341") == "PIX enviado"

def test_itau_boleto():
    assert categorize_transaction("BOLETO PAGO PREVENFIRE SISTEMAS DE", -2425.0, "341") == "Boleto pago"

def test_itau_tarifa():
    assert categorize_transaction("TAR PLANO ADAPT 1 12/25", -159.0, "341") == "Tarifa bancária"

def test_itau_rendimento():
    assert categorize_transaction("RENDIMENTOS | REND PAGO APLIC AUT MAIS", 0.05, "341") == "Rendimento de aplicação"

def test_itau_impostos():
    assert categorize_transaction("PAGAMENTOS TRIB COD BARRAS | SEFAZ-SC/DARE", -2058.64, "341") == "Impostos/tributos"

def test_itau_pix_qrcode():
    assert categorize_transaction("PAGAMENTOS PIX QR-CODE | CEF MATRIZ", -10594.55, "341") == "PIX enviado"

# BB (001)
def test_bb_pix_recebido():
    assert categorize_transaction("Pix - Recebido | 12/01 13:22 SANDRA", 500.0, "001") == "PIX recebido"

def test_bb_pix_enviado():
    assert categorize_transaction("Pix - Enviado | 15/01 14:50 VERA LUCIA", -15.0, "001") == "PIX enviado"

def test_bb_resgate():
    assert categorize_transaction("BB Rende Fácil | Rende Facil", 68.42, "001") == "Resgate de aplicação"

def test_bb_investimento():
    assert categorize_transaction("BB Rende Fácil | Rende Facil", -585.0, "001") == "Investimento em aplicação"

def test_bb_brasilprev():
    assert categorize_transaction("Brasilprev | BRASILPREV SEGUROS", -171.93, "001") == "Outros débitos"

def test_bb_tarifa():
    assert categorize_transaction("Cobrança de Juros | Juros Saldo Devedor", -1.84, "001") == "Tarifa bancária"

# Boolean columns with investment
def test_resgate_excluded_from_entrada():
    assert is_entrada_sem_resgates(68.42, "BB Rende Fácil | Rende Facil") == False

def test_investimento_excluded_from_saida():
    assert is_saida_sem_aplicacao(-585.0, "BB Rende Fácil | Rende Facil") == False

# Sicoob new patterns
def test_sicoob_pix_emit_abbreviated():
    assert categorize_transaction("PIX EMIT.OUTRA IF | Pagamento Pix", -500.0, "756") == "PIX enviado"

def test_sicoob_resgate_rdc():
    assert categorize_transaction("41 - 9 RESGATE RDC", 752.57, "756") == "Resgate de aplicação"

def test_sicoob_compe_abbreviated():
    assert categorize_transaction("DÉB.TIT.COMPE.EFETI | DOC.: 4014211", -145.95, "756") == "Boleto pago"
