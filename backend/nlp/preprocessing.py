"""
Sosyal medya metinleri için ön işleme (preprocessing) fonksiyonları.
URL, emoji, @kullanıcı etiketi ve gereksiz karakterleri temizler.
"""

import re
import unicodedata


# ── Derlenmiş Regex Desenleri ──

# URL deseni (http, https, www, kısa linkler)
_URL_PATTERN = re.compile(
    r"https?://\S+|www\.\S+|bit\.ly/\S+|t\.co/\S+",
    re.IGNORECASE,
)

# @kullanıcı etiketleri
_MENTION_PATTERN = re.compile(r"@[\w.]+")

# Hashtag sembolü (kelimeyi koru, # işaretini kaldır)
_HASHTAG_PATTERN = re.compile(r"#([\w]+)")

# Emoji ve diğer sembol blokları (Unicode)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"  # Enclosed chars
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
    "\U00002600-\U000026FF"  # Misc Symbols
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0000200D"             # Zero Width Joiner
    "]+",
    re.UNICODE,
)

# Birden fazla boşluk
_MULTI_SPACE_PATTERN = re.compile(r"\s+")

# RT (retweet) deseni
_RT_PATTERN = re.compile(r"^RT\s+", re.IGNORECASE)


def remove_urls(text: str) -> str:
    """URL'leri kaldırır."""
    return _URL_PATTERN.sub("", text)


def remove_mentions(text: str) -> str:
    """@kullanıcı etiketlerini kaldırır."""
    return _MENTION_PATTERN.sub("", text)


def remove_emojis(text: str) -> str:
    """Emoji ve özel Unicode sembollerini kaldırır."""
    return _EMOJI_PATTERN.sub("", text)


def normalize_hashtags(text: str) -> str:
    """#hashtag → hashtag (kelimeyi korur, sembolü kaldırır)."""
    return _HASHTAG_PATTERN.sub(r"\1", text)


def remove_rt_prefix(text: str) -> str:
    """Baştaki RT ifadesini kaldırır."""
    return _RT_PATTERN.sub("", text)


def normalize_whitespace(text: str) -> str:
    """Birden fazla boşluğu teke indirir, baş/son boşlukları siler."""
    return _MULTI_SPACE_PATTERN.sub(" ", text).strip()


def normalize_unicode(text: str) -> str:
    """Unicode normalizasyonu (NFC) — Türkçe karakterler korunur."""
    return unicodedata.normalize("NFC", text)


def preprocess_text(text: str) -> str:
    """
    Sosyal medya metnini model girdisi için temizler.

    İşlem sırası:
      1. Unicode normalizasyonu
      2. RT kaldırma
      3. URL kaldırma
      4. @mention kaldırma
      5. Emoji kaldırma
      6. Hashtag sembolü kaldırma (kelime korunur)
      7. Boşluk normalizasyonu

    Args:
        text: Ham sosyal medya metni.

    Returns:
        Temizlenmiş metin. Boşsa boş string döner.

    Example:
        >>> preprocess_text("RT @user Bu video fake! 🤯 https://t.co/abc #deepfake")
        'Bu video fake! deepfake'
    """
    if not text or not text.strip():
        return ""

    result = text
    result = normalize_unicode(result)
    result = remove_rt_prefix(result)
    result = remove_urls(result)
    result = remove_mentions(result)
    result = remove_emojis(result)
    result = normalize_hashtags(result)
    result = normalize_whitespace(result)

    return result
