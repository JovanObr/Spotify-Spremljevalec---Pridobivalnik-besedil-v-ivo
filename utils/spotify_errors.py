def get_retry_delay(error) -> int | None:
    """
    Determine how the application should respond to a Spotify API error.

    Returns:
        Number of seconds to wait before retrying.
        None if the application should stop.
    """

    status = getattr(error, "http_status", None)

    if status == 401:
        print(
            "\nSpotify authentication failed. "
            "Please restart the application and authenticate again."
        )
        return None

    if status == 403:
        print(
            "\nSpotify denied access to this resource. "
            "Check your app permissions, authorized users, and account access."
        )
        return None

    if status == 429:
        headers = getattr(error, "headers", {}) or {}

        retry_after = (
            headers.get("Retry-After")
            or headers.get("retry-after")
        )

        try:
            delay = max(1, int(retry_after))
        except (TypeError, ValueError):
            delay = 30

        print(
            f"\nSpotify rate limit reached. "
            f"Retrying in {delay} seconds."
        )
        return delay

    if status is not None and status >= 500:
        print(
            f"\nSpotify server error ({status}). "
            "Retrying in 30 seconds."
        )
        return 30

    print(
        f"\nSpotify API error ({status}): {error}. "
        "Retrying in 15 seconds."
    )
    return 15