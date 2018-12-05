import pickle
from guess_who import Conversation

try:
        f = open('status.pickle', 'rb')
except IOError as e:
        print('no status pickle')
else:
        with f:
                status = pickle.load(f)
                conversations = status['conversations']

for (key, value) in conversations.items():
    print(value.one.acct)
    print(value.two.acct)

while True:
    eval(input())

