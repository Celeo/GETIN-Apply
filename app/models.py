from .shared import db


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    corporation = db.Column(db.String)
    alliance = db.Column(db.String)
    refresh_token = db.Column(db.String)
    recruiter = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)

    def __init__(self, name: str, corporation: str, alliance: str, refresh_token: str = None,
                 recruiter: bool = False, admin: bool = False) -> None:
        self.name = name
        self.corporation = corporation
        self.alliance = alliance
        self.refresh_token = refresh_token
        self.recruiter = recruiter
        self.admin = admin

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def is_in_alliance(self) -> bool:
        return self.alliance == 'The Society For Unethical Treatment Of Sleepers'
