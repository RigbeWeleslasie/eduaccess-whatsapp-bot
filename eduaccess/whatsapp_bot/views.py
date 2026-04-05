# eduaccess/whatsapp/views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse

from .ai import ask_ai

@csrf_exempt
def whatsapp_webhook(request):
    """
    Webhook to receive WhatsApp messages via Twilio,
    send them to OpenAI GPT, and return the response.
    """
    if request.method == "POST":
        incoming_msg = request.POST.get('Body', '').strip()
        from_number = request.POST.get('From', '')
        print(f"Message from {from_number}: {incoming_msg}")

        resp = MessagingResponse()
        msg = resp.message()

        if incoming_msg:
            try:
                reply = ask_ai(incoming_msg)
            except Exception as e:
                print("Gemini Error:", e)
                reply = "Sorry, I couldn't process your request at the moment."
        else:
            reply = "Hi! Please send a message so I can help you."

        msg.body(reply)
        return HttpResponse(str(resp), content_type="application/xml")

    # For GET requests or others
    return HttpResponse("Hello, this endpoint is for WhatsApp messages only.")
