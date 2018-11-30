# this requires a modified mastodon.py to work on pleroma, as all python
# projects do. i'll add that to source control in due time
from mastodon import Mastodon
import pickle
from time import sleep
import datetime
from bs4 import BeautifulSoup
import random
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
	last_chains = {}
	def __init__(self, one, two, one_toot, two_toot):
		self.one = one
		self.two = two
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
			api_base_url='https://beeping.town',
			to_file='guess_who.client.secret')

def register_account():
	masto = Mastodon(client_id='guess_who.client.secret',
			api_base_url='https://beeping.town')
	masto.log_in(secret.username, secret.password,
			to_file='guess_who.user.secret')

def convo_proxy(masto, noti):
	global conversations
	account = noti.account
	convo = conversations[account.id]
	other = convo.other(account.id)
	text = '@' + other.acct + ' ' + html_to_text(noti.status.content)
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
	# first, enumerate followers and follows, then select union
	# masto.account_follow(ing/ers) only returns those FROM MY INSTANCE
	# which is a no-go so weee are going to use the ACTIVITYPUB API!!!!
	url = account.url
	followers = activitypub_get_collection(url, 'followers')
	following = activitypub_get_collection(url, 'following')

	mutuals = list(following & followers)
	if mutuals:
		url = random.choice(mutuals)
		# search with masto-api the link to get account object
		return masto.account_search(url)[0]
	else:
		# return self for now. TODO: what should we do
		print('YOU LITERALLY HAVE NO MUTUALS. RIPPO (BUG?)')
		return account

def start_convo(masto, account, status_id):
	global conversations
	other = select_partner(masto, account)
	# TODO: Only send this introduction if someone is not following GuessWho bot
	request = masto.status_post("""hi @{}, one of your mutuals wants to play "Guess Who?"

if you'd rather not, you can reply with "+reject". \
if you're interested, reply to start the conversation!

to play Guess Who, you have a conversation through this bot by proxy, and if \
you want, you can try to guess which of your mutuals you're talking to!

reply "+reveal +silent" to reveal who sent this, especially if anyone is harassing you!
	""".format(other.acct), spoiler_text='unsolicited DM', visibility='direct')
	convo = Conversation(account, other, status_id, request.id)
	# we store it both ways so we can look up the convo from anywhere
	conversations[account.id] = convo
	conversations[other.id] = convo

def reject(masto, rejecter):
	global conversations
	if rejecter.id in conversations:
		convo = conversations[rejecter.id]
		other = convo.other(rejecter.id)
		del conversations[rejecter.id]
		if other.id in conversations:
			del conversations[other.id]
		# the "other" is the originator, they still want to find a conversation
		# let them know, doing it automatically is actually pretty problematic
		masto.status_post("""sorry @{}, the convo was rejected. reply to try another?
				""".format(other.acct), visibility='direct')
	else:
		no_conversation(masto, rejecter.acct, '+reject')

def reveal(masto, revealer, is_silent):
	global conversations
	if revealer.id in conversations:
		convo = conversations[revealer.id]
		other = convo.other(revealer.id)
		at_sign = '[at]' if is_silent else '@'
		masto.status_post("""the accounts, REVEALED! it was @{} and {}{}!!!"""
				.format(revealer.acct, at_sign, other.acct), visibility='direct')
	else:
		no_conversation(masto, revealer.acct, '+reveal')

def no_conversation(masto, acct, command):
	masto.status_post("""sorry {}, i don't have any conversations logged with you, \
so '{}' doesn't make sense to me. please message @cosine@anticapitalist.party for help"""
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
						print('rejecting a convo')
						reject(masto, account)
						dont_proxy = True
					elif command == '+reveal':
						print('revealing a convo')
						is_silent = '+silent' in noti.status.content
						reveal(masto, account, is_silent)
						dont_proxy = is_silent
			if not dont_proxy:
				if account.id in conversations:
					# TODO: Figure out how to uniquely identify multiple convos
					print('sending a toot')
					convo_proxy(masto, noti)
				else:
					# We use the status because sometimes a convo is started
					# with no noti (as in reject)
					print('logging a fuckin, convo')
					start_convo(masto, account, noti.status.id)
		# so we don't keep re and re reading
		masto.notifications_dismiss(noti.id)

def html_to_text(html):
	soup = BeautifulSoup(html)
	text = soup.get_text()
	text = text.replace('@GuessWho', '')
	return text

if __name__ == "__main__":
	masto = Mastodon(access_token='guess_who.user.secret',
			api_base_url='https://beeping.town')
	try:
		f = open('status.pickle', 'rb')
	except IOError as e:
		print('no status pickle')
	else:
		with f:
			status = pickle.load(f)
			conversations = status['conversations']
	sleep_time = 2
	pickle_frequency = 300 / sleep_time
	pickle_count = 0
	while True:
		# TODO: Stream notis instead of polling
		check_notis(masto)
		sleep(sleep_time)
		pickle_count += 1
		if pickle_count > pickle_frequency:
			print('pickling!')
			status = {
					'conversations': conversations
					}
			with open('status.pickle', 'wb') as pickle_file:
				pickle.dump(status, pickle_file)
			pickle_count = 0

