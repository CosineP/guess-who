import guess_who
# so pickle can read it
from guess_who import Conversation
from mastodon import Mastodon
import secret_live
import pickle

masto = Mastodon(access_token='guess_who.user.live.secret',
		api_base_url=secret_live.api_base_url,
		ratelimit_method='pace')

with open('status-old.pickle', 'rb') as f:
	status = pickle.load(f)
	conversations = status['conversations']

convos_new = {}

for account_id, convo in conversations.items():
	convo_id = guess_who.gen_id()
	toot_to = None
	# we want to toot only the one matching the key...
	if convo.one.id == account_id:
		toot_to = convo.one.acct
		# ONLY ON THE FIRST ONE do we add the conversation to the new convos dict
		convos_new[convo_id] = convo
	else:
		toot_to = convo.two.acct
	request_id = request = masto.status_post("""@{} i just added multiple-conversation \
support to Guess Who. as part of that, to continue your conversation you'll \
have to reply to this toot which contains the conversation ID. thank you

- {}""".format(toot_to, convo_id),
	spoiler_text='unsolicited DM', visibility='direct')
	convo.last_chains[account_id] = request_id

status = {
		'conversations': convos_new
		}
with open('status-migrated.pickle', 'wb') as pickle_file:
	pickle.dump(status, pickle_file)
pickle_count = 0

