from dataclasses import dataclass


@dataclass
class AppSession:
    current_user: object | None = None

    def login(self, user_ctx: object) -> None:
        if self.current_user is not None:
            raise RuntimeError("A user is already logged in for this app session.")
        self.current_user = user_ctx

    def logout(self) -> None:
        self.current_user = None

    @property
    def is_authenticated(self) -> bool:
        return self.current_user is not None
