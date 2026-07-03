"""Confidence-language tracker: bilingual hedging/certainty (FR-6 signal)."""
from castor.confidence import certainty_signal, inflation_delta


def test_hedging_english():
    signal = certainty_signal("The revenue might possibly increase next quarter.")
    assert signal.hedge_hits == 2
    assert signal.certainty_hits == 0
    assert signal.score < 0


def test_certainty_english():
    signal = certainty_signal("This definitely proves the strategy works.")
    assert signal.certainty_hits == 2
    assert signal.score > 0


def test_hedging_indonesian():
    signal = certainty_signal("Pendapatan mungkin akan naik, diperkirakan sekitar sepuluh persen.")
    assert signal.hedge_hits >= 2
    assert signal.score < 0


def test_certainty_indonesian():
    signal = certainty_signal("Sudah pasti strategi ini terbukti berhasil.")
    assert signal.certainty_hits >= 2
    assert signal.score > 0


def test_belum_pasti_is_hedge_not_certainty():
    # Phrase must be consumed before token matching: "belum pasti" != "pasti".
    signal = certainty_signal("Hasil akhirnya belum pasti.")
    assert signal.hedge_hits == 1
    assert signal.certainty_hits == 0


def test_conclusive_markers_bilingual():
    assert certainty_signal("Therefore, we must double the budget.").conclusive
    assert certainty_signal("Maka anggaran harus dilipatgandakan.").conclusive
    assert not certainty_signal("The report covers March sales.").conclusive


def test_inflation_delta_positive_only():
    hedged = certainty_signal("It might work, perhaps.")
    certain = certainty_signal("It definitely works, proven and confirmed.")
    assert inflation_delta(hedged, certain) > 0
    assert inflation_delta(certain, hedged) == 0.0
