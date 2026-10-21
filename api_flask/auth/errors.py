class AuthError(Exception):
    """An authentication/authorization failure (401 or 403).

    `error` is a dict with a stable machine-readable `code` and a human
    `description`, so every endpoint reports failures the same way.
    """

    def __init__(self, error, status_code):
        super().__init__(error.get("description"))
        self.error = error
        self.status_code = status_code
