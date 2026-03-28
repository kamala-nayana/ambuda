/* global Sanscript */

/**
 * Convert a string from Devanagari to Harvard-Kyoto transliteration.
 * Returns the original string if Sanscript is not available.
 */
export function toHK(str) {
  if (!str || typeof Sanscript === 'undefined') return str;
  return Sanscript.t(str, 'devanagari', 'hk');
}

/**
 * Normalize an HK string for fuzzy matching by collapsing similar sounds.
 * Applied before lowercasing: z→s, RR→R, lR→l, G→n, J→n, M→n.
 */
export function normalizeHK(str) {
  return str.replace(/z/g, 's').replace(/sh/g, 's').replace(/([kgcjTDtdpb])h/g, '$1').replace(/RR/g, 'R').replace(/lR/g, 'l').replace(/G/g, 'n').replace(/J/g, 'n').replace(/M/g, 'n').replace(/m/g, 'n');
}

/**
 * A text matcher for Sanskrit text.
 */
export function createSearchMatcher(items, getText) {
  const entries = items.map((item) => {
    const original = getText(item);
    const text = original.toLowerCase();
    const hk = toHK(original).toLowerCase();
    return { item, text, hk };
  });

  return {
    filter(query) {
      if (!query) return items;
      const q = query.toLowerCase();
      return entries
        .filter((e) => e.text.includes(q) || e.hk.includes(q))
        .map((e) => e.item);
    },
  };
}
