from quart import Quart
from quart_rate_limiter import RateLimiter


app = Quart(__name__)
limiter = RateLimiter(app)
