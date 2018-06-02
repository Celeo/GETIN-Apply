from datetime import timedelta
import logging

from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_htmlmin import HTMLMIN
from esipy import App, EsiClient, EsiSecurity

from .shared import db
from .models import User, Application
from .explorer import all_esi_read_scopes, CharacterExplorer


# Basic setup
app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=14)
app.config.from_json('config.json')
HTMLMIN(app)
# Database connection
db.app = app
db.init_app(app)
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

# User management
login_manager = LoginManager(app)
login_manager.login_message = ''
login_manager.login_view = 'index'


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=int(user_id)).first()


# ====================================================
# Routes
# ====================================================

@app.route('/')
def index():
    app_status = None
    if not current_user.is_anonymous:
        if not current_user.is_in_alliance:
            app = Application.query.filter_by(user_id=current_user.id).first()
            if app:
                app_status = app.status
    return render_template('index.html', app_status=app_status)


@app.route('/sso_callback')
def sso_callback():
    code = request.args.get('code')
    if not code:
        flash('No code from EVE SSO found', 'error')
        return redirect(url_for('index'))
    tokens = esi_security.auth(code)
    char_info = esi_security.verify()
    if request.args.get('state') == 'apply':
        session['apply_token'] = tokens['refresh_token']
        return redirect(url_for('apply'))
    corporation, alliance = get_affiliation(esi_app, esi_client, char_info['CharacterID'])
    user = User.query.filter_by(name=char_info['CharacterName']).first()
    new_user = True
    if user:
        new_user = False
        user.corporation = corporation
        user.alliance = alliance
    else:
        user = User(char_info['CharacterName'], corporation, alliance)
        db.session.add(user)
    db.session.commit()
    login_user(user)
    app.logger.info('{} logged in{}'.format(user.name, ' for the first time' if new_user else ''))
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    app.logger.info('{} logged out'.format(current_user.name if not current_user.is_anonymous else '<anon>'))
    return redirect(url_for('index'))


@app.route('/apply')
@login_required
def apply():
    if current_user.is_in_alliance:
        return redirect(url_for('index'))
    scopes_sso_login = esi_security.get_auth_uri(scopes=all_esi_read_scopes, state='apply')
    step = 1
    if session.get('apply_token'):
        step = 2
    return render_template('apply.html', scopes_sso_login=scopes_sso_login, step=step)


@app.route('/apply/submit')
@login_required
def submit_apply():
    current_user.refresh_token = session.pop('apply_token')
    db.session.commit()
    db.session.add(Application(current_user.id, request.form.get('note')))
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/processing')
@login_required
def processing():
    if not current_user.recruiter or current_user.admin:
        return redirect(url_for('index'))
    return render_template('processing.html', applications=Application.query.all())


@app.route('/processing/<int:app_id>/status', methods=['POST'])
@login_required
def processing_change_status(app_id):
    if not current_user.recruiter or current_user.admin:
        return redirect(url_for('index'))
    if not request.method == 'POST':
        return redirect(url_for('processing'))
    application = Application.query.filter_by(id=app_id).first()
    if not application:
        flash('Unknown app id', 'error')
        return redirect(url_for('processing'))
    new_status = request.form.get('status')
    if not new_status:
        flash('No new status set', 'error')
        return redirect(url_for('processing'))
    application.status = new_status
    db.session.commit()
    return redirect(url_for('processing'))


@app.route('/api_view/<int:character_id>')
@login_required
def view_api(character_id: int):
    if not current_user.recruiter or current_user.admin:
        return redirect(url_for('index'))
    user = User.query.filter_by(id=character_id).first()
    if not user:
        flash('No user with that ID found', 'error')
        return redirect(url_for('processing'))
    if not user.refresh_token:
        flash('That user doesn\'t have a refresh token on file', 'error')
        return redirect(url_for('processing'))
    return render_template('api_view.html', explorer=CharacterExplorer(esi_app, esi_security, esi_client, user.refresh_token))


@app.route('/api_view/mail/<token>/<int:mail_id>')
def get_mail_body(token, mail_id):
    explorer = CharacterExplorer(esi_app, esi_security, esi_client, token, load_now=False)
    return explorer.get_mail_body(mail_id)


@app.route('/admin')
@login_required
def admin():
    if not current_user.admin:
        return redirect(url_for('index'))
    return 'admin'


@app.errorhandler(404)
def error_404(e):
    return render_template('error.html', code=404)


@app.errorhandler(500)
def error_500(e):
    return render_template('error.html', code=500)


# ====================================================
# Template add-ins
# ====================================================

@app.context_processor
def context_processor():
    return {
        'sso_login_url': esi_security.get_auth_uri()
    }


@app.template_filter('mail_recipients')
def filter_mail_recipients(data):
    return ', '.join([r['recipient_name'] for r in data])


# ====================================================
# Util
# ====================================================

def get_affiliation(app: 'esipy.App', client: 'esipy.EsiClient', character_id: int) -> (str, str):
    result = client.request(app.op['get_characters_character_id'](character_id=character_id)).data
    corp_id, alliance_id = result['corporation_id'], result.get('alliance_id')
    ids = [i for i in [corp_id, alliance_id] if i]
    result = client.request(app.op['post_universe_names'](ids=ids)).data
    corp_name = result[0]['name']
    alliance_name = result[1]['name'] if len(ids) == 2 else None
    return corp_name, alliance_name
