"""Shim around vidyut.lipi with custom Tamil superscript support.

For Tamil output, we use a custom converter that annotates aspiration and
voicing with Unicode superscript digits (², ³, ⁴) placed after the vowel
sign (or after virāma when no vowel follows).

For all other scripts, we delegate directly to vidyut.
"""

from vidyut.lipi import transliterate as _vidyut_transliterate
from vidyut.lipi import Scheme, detect  # noqa: F401 — re-export


def transliterate(text: str, source: Scheme, dest: Scheme) -> str:
    """Transliterate *text* from *source* to *dest* script.

    Intercepts ``Scheme.Tamil`` to produce superscript notation;
    all other schemes pass through to vidyut unchanged.
    """
    if dest == Scheme.Tamil:
        hk = _vidyut_transliterate(text, source, Scheme.HarvardKyoto)
        return _hk_to_tamil_superscript(hk)
    return _vidyut_transliterate(text, source, dest)


# ---------------------------------------------------------------------------
# Tamil superscript converter (HK → Tamil)
# ---------------------------------------------------------------------------

_VIRAMA = "\u0bcd"  # ்
_ANUSVARA = "ம\u0bcd\u02bc"  # ம்ʼ
_VISARGA = "\ua789"  # ꞉ (modifier letter colon)

# HK consonant → (Tamil character, superscript string — empty if none)
_CONSONANTS: dict[str, tuple[str, str]] = {
    # Velars
    "kh": ("க", "²"),
    "gh": ("க", "⁴"),
    "k": ("க", ""),
    "g": ("க", "³"),
    "G": ("ங", ""),
    # Palatals
    "ch": ("ச", "²"),
    "jh": ("ஜ", "⁴"),
    "c": ("ச", ""),
    "j": ("ஜ", ""),
    "J": ("ஞ", ""),
    # Retroflexes
    "Th": ("ட", "²"),
    "Dh": ("ட", "⁴"),
    "T": ("ட", ""),
    "D": ("ட", "³"),
    "N": ("ண", ""),
    # Dentals
    "th": ("த", "²"),
    "dh": ("த", "⁴"),
    "t": ("த", ""),
    "d": ("த", "³"),
    "n": ("ன", ""),
    # Labials
    "ph": ("ப", "²"),
    "bh": ("ப", "⁴"),
    "p": ("ப", ""),
    "b": ("ப", "³"),
    "m": ("ம", ""),
    # Semivowels
    "y": ("ய", ""),
    "r": ("ர", ""),
    "l": ("ல", ""),
    "v": ("வ", ""),
    # Sibilants & h (Grantha)
    "z": ("ஶ", ""),
    "S": ("ஷ", ""),
    "s": ("ஸ", ""),
    "h": ("ஹ", ""),
    # Retroflex lateral
    "L": ("ள", ""),
}

# Sorted longest-first for greedy matching.
_CONSONANT_TOKENS = sorted(_CONSONANTS, key=lambda x: -len(x))

# HK vowel → Tamil independent vowel character(s)
_VOWELS: dict[str, str] = {
    "ai": "ஐ",
    "au": "ஔ",
    "lRR": "லூʼ",
    "lR": "லுʼ",
    "RR": "ரூ",
    "A": "ஆ",
    "I": "ஈ",
    "U": "ஊ",
    "R": "ருʼ",
    "a": "அ",
    "i": "இ",
    "u": "உ",
    "e": "ஏ",
    "o": "ஓ",
}

# HK vowel → Tamil dependent vowel sign (mātrā).
# 'a' (inherent vowel) maps to the empty string.
_MATRAS: dict[str, str] = {
    "ai": "\u0bc8",  # ை
    "au": "\u0bcc",  # ௌ
    "lRR": _VIRAMA + "லூ",
    "lR": _VIRAMA + "லு",
    "RR": _VIRAMA + "ரூ",  # same as before, no ʼ
    "A": "\u0bbe",  # ா
    "I": "\u0bc0",  # ீ
    "U": "\u0bc2",  # ூ
    "R": _VIRAMA + "ரு",
    "a": "",
    "i": "\u0bbf",  # ி
    "u": "\u0bc1",  # ு
    "e": "\u0bc7",  # ே
    "o": "\u0bcb",  # ோ
}

_VOWEL_TOKENS = sorted(_VOWELS, key=lambda x: -len(x))


def _match(text: str, pos: int, tokens: list[str]) -> tuple[str, int] | None:
    """Return the first (longest) token that matches at *pos*, or None."""
    for tok in tokens:
        if text[pos : pos + len(tok)] == tok:
            return tok, len(tok)
    return None


_DENTAL_NA = "ந"
_ALVEOLAR_NA = "ன"
# Tamil dental consonants that trigger ந before them.
_DENTALS = {"த"}


_COMBINING = {
    _VIRAMA,
    "²",
    "³",
    "⁴",
    "\u0bbe",
    "\u0bbf",
    "\u0bc0",
    "\u0bc1",
    "\u0bc2",  # ா ி ீ ு ூ
    "\u0bc6",
    "\u0bc7",
    "\u0bc8",  # ெ ே ை
    "\u0bca",
    "\u0bcb",
    "\u0bcc",  # ொ ோ ௌ
    "\u0b82",
}  # ஂ


def _fix_na(result: str) -> str:
    """Apply Tamil ந/ன distribution rules.

    Use ந (dental) at word-initial position and before dental consonants (த-class).
    Use ன (alveolar) everywhere else.  The converter emits ன throughout; this
    function promotes the appropriate ones to ந.
    """
    chars = list(result)
    n = len(chars)
    for i, ch in enumerate(chars):
        if ch != _ALVEOLAR_NA:
            continue
        # Word-initial: first char, or preceded by a space/punctuation.
        # Skip back over combining marks to find the base character.
        j = i - 1
        while j >= 0 and chars[j] in _COMBINING:
            j -= 1
        if j < 0 or not chars[j].isalpha():
            chars[i] = _DENTAL_NA
            continue
        # Before a dental consonant (skip over virāma and superscripts).
        j = i + 1
        while j < n and chars[j] in _COMBINING:
            j += 1
        if j < n and chars[j] in _DENTALS:
            chars[i] = _DENTAL_NA
    return "".join(chars)


def _hk_to_tamil_superscript(text: str) -> str:
    """Convert Harvard-Kyoto text to Tamil with superscript aspiration markers."""
    parts: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        # 1. Try consonant (longest match first).
        cm = _match(text, i, _CONSONANT_TOKENS)
        if cm:
            hk_cons, clen = cm
            tamil_char, superscript = _CONSONANTS[hk_cons]
            i += clen

            # Look ahead for a vowel.
            vm = _match(text, i, _VOWEL_TOKENS)
            if vm:
                hk_vowel, vlen = vm
                parts.append(tamil_char)
                parts.append(_MATRAS[hk_vowel])
                parts.append(superscript)
                i += vlen
            else:
                # No vowel → add virāma (with superscript after it).
                parts.append(tamil_char)
                parts.append(_VIRAMA)
                parts.append(superscript)
            continue

        # 2. Try independent vowel (longest match first).
        vm = _match(text, i, _VOWEL_TOKENS)
        if vm:
            hk_vowel, vlen = vm
            parts.append(_VOWELS[hk_vowel])
            i += vlen
            continue

        # 3. Special HK characters.
        ch = text[i]
        if ch == "." and i + 1 < n and text[i + 1] == ".":
            parts.append("॥")
            i += 2
        elif ch == ".":
            parts.append("।")
            i += 1
        elif ch == "M":
            parts.append(_ANUSVARA)
            i += 1
        elif ch == "H":
            parts.append(_VISARGA)
            i += 1
        elif ch == "'":
            parts.append("(அ)")
            i += 1
        else:
            # Pass through spaces, digits, punctuation, etc.
            parts.append(ch)
            i += 1

    return _fix_na("".join(parts))
