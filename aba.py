import uuid

text = "БУБА"

client_message_id = uuid.uuid4().hex
text_to_send = f"{text}\n[{client_message_id}]"

print(text_to_send)
