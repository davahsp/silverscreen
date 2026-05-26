def serialize_messages(messages):
    return [
        {
            "message": str(message),
            "level": message.level,
            "tags": message.tags,
        }
        for message in messages
    ]
