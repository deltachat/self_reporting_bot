import os.path
import simplebot

@simplebot.filter
def process(bot, message, replies):
    """Echoes back received message."""
    try:
        text = message.text
        bot.account.delete_messages([message])

        if not text.startswith("core_version "):
            raise ValueError("Message doesn't start with core_version")

        statistics = {}
        for l in text.splitlines():
            parts = l.split()
            statistics[parts[0]] = parts[1]

        filename = statistics["self_reporting_id"]
        version = 1
        while os.path.exists(filename + "." + str(version)):
            version += 1
        filename = filename + "." + str(version)

        with open(filename, "w") as file:
            file.write(text)

        replies.add(text="Thanks for sending statistics about your usage of Delta Chat to us! We will use it to get a feeling of how people use Delta Chat, and to improve often-occuring issues.")
    except Exception as e:
        print("Could not parse self_reporting message:", e)
        replies.add(text="Sorry, I couldn't understand your message.\n\nI am a bot for receiving statistics about your usage of Delta Chat. All other messages will be ignored.")
        
