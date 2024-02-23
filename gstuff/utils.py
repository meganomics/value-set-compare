import logging

logger = logging.getLogger(__name__)


def handlify(text: str, sep: str = '_', max_len: int = 64) -> str:
    if not isinstance(text, str) or len(text.strip()) == 0:
        logger.warning('handlify: text is not a string or is empty')
        return ''
    rep_chars = (' ', '"', "'", '\\')
    h = text.strip().lower()
    for rc in rep_chars:
        h = h.replace(rc, sep)
    handle = ''
    curr_is_sep = False
    for c in h:
        if c == sep:
            if curr_is_sep:
                continue
            else:
                handle += c
                curr_is_sep = True
        else:
            handle += c
            curr_is_sep = False
    if max_len > 0:
        return handle[:max_len]
    return handle
