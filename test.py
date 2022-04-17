import requests
import json
class Slack():
    def __init__(self):
        self.url = 'https://hooks.slack.com/services/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'
    def send(self, message):
        return requests.post(self.url, data=json.dumps({'text': message}, ensure_ascii=False).encode('utf-8'), headers={'Content-type': 'application/json'})

print(Slack().send('test'))
