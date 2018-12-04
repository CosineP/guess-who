import secret
from mastodon import Mastodon

masto = Mastodon(access_token='guess_who.user.secret',
		api_base_url=secret.api_base_url,
		ratelimit_method='pace')
masto.notifications_clear()

