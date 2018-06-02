from datetime import timedelta
import logging

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, current_user
from esipy import App, EsiClient, EsiSecurity

from .shared import db
from .models import User
from .esi import get_affiliation


# Basic setup
app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=14)
app.config.from_json('config.json')
# Database connection
db.app = app
db.init_app(app)
# User management
login_manager = LoginManager(app)
login_manager.login_message = ''
login_manager.login_view = 'index'
# Application logging
app.logger.setLevel(app.config['LOGGING_LEVEL'])
handler = logging.FileHandler('log.log')
handler.setFormatter(logging.Formatter(style='{', fmt='{asctime} [{levelname}] {message}', datefmt='%Y-%m-%d %H:%M:%S'))
handler.setLevel(app.config['LOGGING_LEVEL'])
app.logger.addHandler(handler)
# ESI
esi_headers = {'User-Agent': 'github.com/Celeo/GETIN-Apply | celeodor@gmail.com'}
esi_app = App.create('https://esi.tech.ccp.is/latest/swagger.json?datasource=tranquility')
esi_security = EsiSecurity(
    app=esi_app,
    client_id=app.config['CLIENT_ID'],
    secret_key=app.config['SECRET_KEY'],
    redirect_uri=app.config['REDIRECT_URI'],
    headers=esi_headers
)
esi_client = EsiClient(
    security=esi_security,
    headers=esi_headers
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/sso_callback')
def sso_callback():
    code = request.args.get('code')
    if not code:
        flash('No code from EVE SSO found', 'error')
        return redirect(url_for('index'))
    esi_security.auth(code)
    char_info = esi_security.verify()
    corporation, alliance = get_affiliation(char_info['CharacterID'])
    user = User.query.filter_by(name=char_info['CharacterName']).first()
    new_user = True
    if user:
        new_user = False
        user.corporation = corporation
        user.alliance = alliance
    else:
        u = User(char_info['CharacterName'], corporation, alliance)
        db.session.add(u)
    db.session.commit()
    login_user(user)
    app.logger.info('{} logged in{}'.format(user.name, ' for the first time' if new_user else ''))
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    app.logger.info('{} logged out'.format(current_user.name if not current_user.is_anonymous else '<anon>'))
    return redirect(url_for('index'))


@app.context_processor
def context_processor():
    return {
        'sso_login_url': esi_security.get_auth_uri()
    }


@app.errorhandler(404)
def error_404(e):
    return render_template('error.html', code=404)


@app.errorhandler(500)
def error_500(e):
    return render_template('error.html', code=500)
