import pytest
from vidyut.lipi import Scheme

from ambuda.utils.vidyut_shim import transliterate, _hk_to_tamil_superscript


class TestHkToTamilSuperscript:
    """Unit tests for the HK → Tamil superscript converter."""

    def test_basic_vowels(self):
        assert _hk_to_tamil_superscript("a") == "அ"
        assert _hk_to_tamil_superscript("A") == "ஆ"
        assert _hk_to_tamil_superscript("i") == "இ"
        assert _hk_to_tamil_superscript("I") == "ஈ"
        assert _hk_to_tamil_superscript("u") == "உ"
        assert _hk_to_tamil_superscript("U") == "ஊ"
        assert _hk_to_tamil_superscript("e") == "ஏ"
        assert _hk_to_tamil_superscript("o") == "ஓ"
        assert _hk_to_tamil_superscript("ai") == "ஐ"
        assert _hk_to_tamil_superscript("au") == "ஔ"

    def test_ka_varga_superscripts(self):
        """kA khA gA ghA → கா கா² கா³ கா⁴"""
        assert _hk_to_tamil_superscript("kA") == "கா"
        assert _hk_to_tamil_superscript("khA") == "கா²"
        assert _hk_to_tamil_superscript("gA") == "கா³"
        assert _hk_to_tamil_superscript("ghA") == "கா⁴"

    def test_ca_varga_superscripts(self):
        assert _hk_to_tamil_superscript("ca") == "ச"
        assert _hk_to_tamil_superscript("cha") == "ச²"
        assert _hk_to_tamil_superscript("ja") == "ஜ"
        assert _hk_to_tamil_superscript("jha") == "ஜ⁴"

    def test_Ta_varga_superscripts(self):
        assert _hk_to_tamil_superscript("Ta") == "ட"
        assert _hk_to_tamil_superscript("Tha") == "ட²"
        assert _hk_to_tamil_superscript("Da") == "ட³"
        assert _hk_to_tamil_superscript("Dha") == "ட⁴"

    def test_ta_varga_superscripts(self):
        assert _hk_to_tamil_superscript("ta") == "த"
        assert _hk_to_tamil_superscript("tha") == "த²"
        assert _hk_to_tamil_superscript("da") == "த³"
        assert _hk_to_tamil_superscript("dha") == "த⁴"

    def test_pa_varga_superscripts(self):
        assert _hk_to_tamil_superscript("pa") == "ப"
        assert _hk_to_tamil_superscript("pha") == "ப²"
        assert _hk_to_tamil_superscript("ba") == "ப³"
        assert _hk_to_tamil_superscript("bha") == "ப⁴"

    def test_nasals(self):
        assert _hk_to_tamil_superscript("Ga") == "ங"
        assert _hk_to_tamil_superscript("Ja") == "ஞ"
        assert _hk_to_tamil_superscript("Na") == "ண"
        assert _hk_to_tamil_superscript("ma") == "ம"

    def test_na_word_initial(self):
        """Word-initial n → ந (dental)."""
        assert _hk_to_tamil_superscript("na") == "ந"
        assert _hk_to_tamil_superscript("nAma") == "நாம"

    def test_na_before_dental(self):
        """n before dental consonant → ந."""
        # nda → ந்த³
        assert _hk_to_tamil_superscript("nda") == "ந்த³"
        # nta ��� ந்த
        assert _hk_to_tamil_superscript("nta") == "ந்த"
        # mukunda → முகுந்த³
        assert _hk_to_tamil_superscript("mukunda") == "முகுந்த³"
        # mantra → மந்த்ர (n before t)
        assert _hk_to_tamil_superscript("mantra") == "மந்த்ர"

    def test_na_elsewhere(self):
        """n in other positions → ன (alveolar)."""
        # janma → ஜன்ம (n before labial m)
        assert _hk_to_tamil_superscript("janma") == "ஜன்ம"
        # vinA → வினா (intervocalic)
        assert _hk_to_tamil_superscript("vinA") == "வினா"
        # jAne → ஜானே (before vowel)
        assert _hk_to_tamil_superscript("jAne") == "ஜானே"

    def test_semivowels(self):
        assert _hk_to_tamil_superscript("ya") == "ய"
        assert _hk_to_tamil_superscript("ra") == "ர"
        assert _hk_to_tamil_superscript("la") == "ல"
        assert _hk_to_tamil_superscript("va") == "வ"

    def test_sibilants_and_h(self):
        assert _hk_to_tamil_superscript("za") == "ஶ"
        assert _hk_to_tamil_superscript("Sa") == "ஷ"
        assert _hk_to_tamil_superscript("sa") == "ஸ"
        assert _hk_to_tamil_superscript("ha") == "ஹ"

    def test_consonant_with_virama(self):
        """A consonant not followed by a vowel should get virāma."""
        result = _hk_to_tamil_superscript("k")
        assert result == "க்"

    def test_aspirated_consonant_with_virama(self):
        """Superscript follows the virāma when no vowel is present."""
        result = _hk_to_tamil_superscript("kh")
        assert result == "க்²"

    def test_conjunct(self):
        """kta → க்த (ka-virāma + ta)."""
        assert _hk_to_tamil_superscript("kta") == "க்த"

    def test_aspirated_conjunct(self):
        """khya → க்²ய"""
        assert _hk_to_tamil_superscript("khya") == "க்²ய"

    def test_anusvara(self):
        assert _hk_to_tamil_superscript("aM") == "அம்ʼ"

    def test_visarga(self):
        assert _hk_to_tamil_superscript("aH") == "அ꞉"

    def test_spaces_passthrough(self):
        result = _hk_to_tamil_superscript("kA khA gA ghA")
        assert result == "கா கா² கா³ கா⁴"

    def test_single_danda(self):
        assert _hk_to_tamil_superscript("namaH.") == "நம꞉।"

    def test_double_danda(self):
        assert _hk_to_tamil_superscript("namaH..") == "நம꞉॥"

    def test_digits_passthrough(self):
        assert _hk_to_tamil_superscript("123") == "123"

    def test_superscript_after_matra(self):
        """For various vowels, superscript should follow the mātrā."""
        assert _hk_to_tamil_superscript("khi") == "கி²"
        assert _hk_to_tamil_superscript("ghU") == "கூ⁴"
        assert _hk_to_tamil_superscript("bhe") == "பே⁴"

    def test_word_mahAbhAratam(self):
        result = _hk_to_tamil_superscript("mahAbhAratam")
        # m→ம, a→(inherent), h→ஹ, A→ா, bh→ப⁴, A→ா, r→ர, a→(inherent),
        # t→த, a→(inherent), m→ம, (trailing virama? no, 'm' has no vowel after)
        # Wait: mahAbhAratam ends in 'm'. Let me trace:
        # ma=ம hA=ஹா bha=ப⁴ A? No...
        # m-a-h-A-bh-A-r-a-t-a-m (but last m has no vowel)
        # Actually HK: m+a, h+A, bh+A, r+a, t+a, m (no vowel → virāma)
        expected = "மஹாபா⁴ரதம்"
        assert result == expected


class TestTransliterateShim:
    """Test the top-level shim dispatches correctly."""

    def test_non_tamil_passthrough(self):
        """Non-Tamil destinations go straight to vidyut."""
        result = transliterate("saMskRtam", Scheme.HarvardKyoto, Scheme.Devanagari)
        assert result == "संस्कृतम्"

    def test_tamil_uses_superscript(self):
        """Tamil destination uses our custom superscript converter."""
        result = transliterate("saMskRtam", Scheme.HarvardKyoto, Scheme.Tamil)
        assert "²" not in result  # no aspirated consonants in this word
        # But the key thing is it doesn't crash and produces Tamil text
        assert "ஸ" in result

    def test_tamil_from_devanagari(self):
        """Source is Devanagari, dest is Tamil — should still work."""
        result = transliterate("भारत", Scheme.Devanagari, Scheme.Tamil)
        # bhArata → ப⁴ாரத
        assert "ப" in result
        assert "⁴" in result

    def test_kA_khA_gA_ghA(self):
        """The user's canonical example."""
        result = transliterate("kA khA gA ghA", Scheme.HarvardKyoto, Scheme.Tamil)
        assert result == "கா கா² கா³ கா⁴"
