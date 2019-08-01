import json

from worker import log
from worker.constants import URL
from worker.parser.profile import extract_pseudo
from worker.parser.stats import extract_stats
from worker.redis_interface import session, redis_app


def set_user_stats(username):
    r = session.get(URL + username + '?inc=statistiques')
    if r.status_code != 200:
        log.warning(f'HTTP {r.status_code} for username {username}.')
        return

    txt = r.text.replace('\n', '')
    txt = txt.replace('&nbsp;', '')

    pseudo = extract_pseudo(txt)
    solved_challenges = extract_stats(txt)

    response = {
        'pseudo': pseudo,
        'solved_challenges': solved_challenges,
    }

    redis_app.set(f'{username}.stats', json.dumps(response))
