import logging


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # TODO(phase11): expand logging policy without recording secrets, JWTs,
    # API keys, resume tokens, completion codes, or free-text originals.
