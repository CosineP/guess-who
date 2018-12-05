# this requires a modified mastodon.py to work on pleroma, as all python
# projects do. i'll add that to source control in due time
from mastodon import Mastodon
import pickle
from time import sleep
import datetime
from bs4 import BeautifulSoup
import datetime
import logging
import random
import random_emoji
import secret
# to get followers properly we need to go to each instance's API, which means
# we need some raw requests :(
import requests

conversations = {}
# TODO: mutuals cache

class Conversation():
	one = None
	two = None
	# contains the id to reply to in each chain
	# don't initialize this in the class cause otherwise they all reference the
	# same object
	last_chains = None
	def __init__(self, one, two, one_toot, two_toot):
		self.one = one
		self.two = two
		self.last_chains = {}
		self.last_chains[one.id] = one_toot
		self.last_chains[two.id] = two_toot
	def other(self, account_id):
		if type(account_id) == type({}):
			account_id = account_id.id
		if account_id == self.one.id:
			return self.two
		else:
			return self.one

class MutualsList():
	last_follow = None
	last_follower = None
	mutuals = []

def register_app():
	Mastodon.create_app('guess_who',
			api_base_url=secret.api_base_url,
			to_file='guess_who.client.secret')

def register_account():
	masto = Mastodon(client_id='guess_who.client.secret',
			api_base_url=secret.api_base_url)
	masto.log_in(secret.username, secret.password,
			to_file='guess_who.user.secret')

def gen_id():
	return "".join([random_emoji.random_emoji() for _ in range(2)])

def get_id(masto, original_status):
	context = masto.status_context(original_status.id)
	# look in reverse ordor for an ID in the thread
	context.ancestors.reverse()
	for toot in context.ancestors:
		text = html_to_text(toot.content)
		split = text.split(' ')
		after_space = split[-1].strip()
		if len(after_space) == 2 and split[-2][-1] == '-':
			# A proper ID
			return after_space
	# No ID was found in the whole context :(
	return None

def convo_proxy(masto, noti):
	global conversations
	account = noti.account
	convo_id = get_id(masto, noti.status)
	convo = conversations[convo_id]
	other = convo.other(account.id)
	text = """@{} {}

- {}""".format(
			other.acct, html_to_text(noti.status.content), convo_id)
	post = masto.status_post(text,
			in_reply_to_id=convo.last_chains[other.id],
			spoiler_text=noti.status.spoiler_text,
			visibility='direct')
	convo.last_chains[account.id] = noti.status.id
	convo.last_chains[other.id] = post.id

def activitypub_get_collection(url, collection):
	page = 1
	rv = []
	while True:
		params = {'page': page}
		headers = {'Accept': 'application/activity+json'}
		# TODO: don't assume location at /collection and look it up
		r = requests.get(url+'/'+collection, params=params, headers=headers)
		if r.text == '':
			# reaching the last page on pleroma gives an empty string
			break
		json = r.json()
		items = json['orderedItems']
		# reaching the last page on mastodon gives a fine object with no items
		if len(items) == 0:
			break
		page += 1
		rv += items
	return set(rv)

def select_partner(masto, account):
	# TODO: select people who follow the bot more likely
	# first, enumerate followers and follows, then select union
	# masto.account_follow(ing/ers) only returns those FROM MY INSTANCE
	# which is a no-go so weee are going to use the ACTIVITYPUB API!!!!
	# TODO: cache these
	url = account.url
	followers = activitypub_get_collection(url, 'followers')
	following = activitypub_get_collection(url, 'following')

	mutuals = list(following & followers)
	if mutuals:
		url = random.choice(mutuals)
		# search with masto-api the link to get account object
		return masto.account_search(url)[0]
	else:
		return None

def start_convo(masto, account, status_id):
	global conversations
	other = select_partner(masto, account)
	if not other:
		print('no mutuals situation')
		masto.status_post("""i couldn't find any mutuals. the most common \
reason for this is you have the mastodon "Hide your Network" option enabled. if \
you disable that option for just a moment, then mention me again, you can \
enable it again right after i start the convo""",
			visibility='direct')
		return
	convo_id = gen_id()
	# TODO: Only send this introduction if someone is not following GuessWho bot
	request = masto.status_post("""hi @{}, one of your mutuals wants to play "Guess Who?"

if you'd rather not, reply with "+reject". \
if you're interested, reply to start the conversation!

to play, you have a conversation through this bot by proxy, and if \
you want, you can try to guess which of your mutuals you're talking to!

reply "+reveal +silent" to reveal who sent this, especially if anyone is harassing you!

- {}""".format(other.acct, convo_id), spoiler_text='unsolicited DM', visibility='direct')
	feedback = masto.status_post("""okay @{}, i've sent a message to your \
partner... ill let you know what they say!

- {}""".format(account.id, convo_id),
		in_reply_to_id=status_id, visibility='direct')
	# also give some feedback to the sender
	convo = Conversation(account, other, feedback.id, request.id)
	# we store it both ways so we can look up the convo from anywhere
	conversations[convo_id] = convo

def reject(masto, noti):
	global conversations
	rejecter = noti.account
	convo_id = get_id(masto, noti.status)
	if convo_id in conversations:
		convo = conversations[convo_id]
		other = convo.other(rejecter.id)
		del conversations[convo_id]
		# the "other" is the originator, they still want to find a conversation
		# let them know, doing it automatically is actually pretty problematic
		masto.status_post("""sorry @{}, the convo was rejected. reply to try another?
				""".format(other.acct), visibility='direct')
	else:
		no_conversation(masto, rejecter.acct, '+reject')

def reveal(masto, status, revealer, is_silent):
	global conversations
	convo_id = get_id(masto, status)
	if convo_id in conversations:
		convo = conversations[convo_id]
		other = convo.other(revealer.id)
		at_sign = '[at]' if is_silent else '@'
		masto.status_post("""the accounts, REVEALED! it was @{} and {}{}!!!

- {}""".format(revealer.acct, at_sign, other.acct, convo_id), visibility='direct')
	else:
		no_conversation(masto, revealer.acct, '+reveal')

def no_conversation(masto, acct, command):
	# TODO: Update to id-thread
	masto.status_post("""sorry @{}, i couldn't find a conversation ID in the thread, \
so '{}' doesn't make sense to me. please reply to the message (with the emojis). \
message [at]cosine@anticapitalist.party for help"""
			.format(acct, command), visibility='direct')

def check_notis(masto):
	global conversations
	notis = masto.notifications()
	# for now we'll assume proper pagination because ugh
	for noti in notis:
		account = noti.account
		if noti.type == 'mention':
			commands = ['+reject', '+reveal']
			dont_proxy = False
			for command in commands:
				if command in noti.status.content:
					if command == '+reject':
						log(logging.INFO, 'rejecting a convo')
						reject(masto, noti)
						dont_proxy = True
					elif command == '+reveal':
						log(logging.INFO, 'revealing a convo')
						is_silent = '+silent' in noti.status.content
						reveal(masto, noti.status, account, is_silent)
						dont_proxy = is_silent
			if not dont_proxy:
				if get_id(masto, noti.status) in conversations:
					# TODO: Figure out how to uniquely identify multiple convos
					log(logging.INFO, 'sending a toot')
					convo_proxy(masto, noti)
				else:
					# We use the status because sometimes a convo is started
					# with no noti (as in reject)
					log(logging.INFO, 'logging a fuckin, convo')
					start_convo(masto, account, noti.status.id)
		# so we don't keep re and re reading
		masto.notifications_dismiss(noti.id)

def html_to_text(html):
	soup = BeautifulSoup(html)
	text = soup.get_text()
	text = text.replace('@GuessWho', '')
	return text

def log(level, text):
	logging.log(level, text)

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

	masto = Mastodon(access_token='guess_who.user.secret',
			api_base_url=secret.api_base_url,
			ratelimit_method='pace')
	try:
		f = open('status.pickle', 'rb')
	except IOError as e:
		logging.warning('no status pickle')
	else:
		with f:
			status = pickle.load(f)
			conversations = status['conversations']
	sleep_time = 1
	pickle_frequency = 20 * 60 / sleep_time
	pickle_count = 0
	while True:
		# TODO: Stream notis instead of polling
		check_notis(masto)
		pickle_count += 1
		if pickle_count > pickle_frequency:
			# print the pickle line again
			print('last pickled: ', datetime.datetime.now(), '\r', end='')
			status = {
					'conversations': conversations
					}
			with open('status.pickle', 'wb') as pickle_file:
				pickle.dump(status, pickle_file)
			pickle_count = 0

