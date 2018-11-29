import guess_who
from mastodon import Mastodon

masto = Mastodon(access_token='guess_who.user.secret',
		api_base_url='https://beeping.town')

class FakeUser():
	url = None
fake_user = FakeUser()
fake_user.url = 'https://anticapitalist.party/users/cosine'
print(guess_who.select_partner(masto, fake_user))

