from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

port = "11211"
host = "memcached"
memcached_uri = f"memcached://{host}:{port}"
limiter = Limiter(storage_uri=memcached_uri,
                  key_func=get_remote_address)
