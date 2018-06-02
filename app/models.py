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

    def get_id(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return f'<User-{self.id}-{self.name}>'


class Application(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('applications', lazy=True))
    note = db.Column(db.String)
    status = db.Column(db.String)

    def __init__(self, user_id: int, note: str, status: str = 'New') -> None:
        self.user_id = user_id
        self.note = note
        self.status = status

    def __repr__(self) -> str:
        return f'<Application-{self.id}-{self.user_id}>'
