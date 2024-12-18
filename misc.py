from datetime import datetime

import i18n


def setup_language(language_code):
    i18n.load_path.append('lang')
    i18n.set('file_format', 'json')
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('locale', language_code)
    i18n.set('fallback', 'en')


def clip(val, min_, max_):
    return min_ if val < min_ else max_ if val > max_ else val


def get_today():
    return datetime.today().strftime('%Y-%m-%d')


today = get_today()


def has_new_day_begun():
    global today
    if today != get_today():
        today = get_today()
        return True
    return False


def get_hours_of_today():
    return int(datetime.today().strftime('%-H'))
