from tap_kit import main_method
from .executor import Listen360Executor
from .client import BaseClient
from .customers import CustomersStream
from .memberships import MembershipsStream
from .reviews import ReviewsStream


REQUIRED_CONFIG_KEYS = [
	"start_date",
	"api_key"
]

STREAMS = [
	CustomersStream,
	MembershipsStream,
	ReviewsStream
]

def main():
	main_method(
		REQUIRED_CONFIG_KEYS,
		Listen360Executor,
		BaseClient,
		STREAMS
	)

if __name__ == '__main__':
	main()