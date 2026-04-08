from urllib.parse import quote

from django.conf import settings


def _normalized_whatsapp_digits(number):
    return "".join(ch for ch in (number or "") if ch.isdigit())


def whatsapp_cta(request):
    number = settings.WHATSAPP_SANDBOX_NUMBER.strip()
    join_code = settings.WHATSAPP_SANDBOX_JOIN_CODE.strip()
    digits = _normalized_whatsapp_digits(number)

    join_url = f"https://wa.me/{digits}?text={quote(join_code)}" if digits and join_code else ""
    chat_url = f"https://wa.me/{digits}" if digits else ""

    return {
        "whatsapp_cta": {
            "number": number,
            "join_code": join_code,
            "join_url": join_url,
            "chat_url": chat_url,
            "is_configured": bool(number and join_code and digits),
        }
    }
