from datetime import datetime

import i18n


def init_language(language_code):
    i18n.load_path.append('lang')
    i18n.set('file_format', 'json')
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('locale', language_code)
    i18n.set('fallback', 'en')


def clip(val, min_, max_):
    return min_ if val < min_ else max_ if val > max_ else val


def get_today():
    return datetime.today().strftime('%Y-%m-%d')