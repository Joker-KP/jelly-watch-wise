import urllib

import i18n
from nicegui import app, ui
from nicegui.events import ValueChangeEventArguments

from config import Configuration, logger
from jellyfin.interact import ServerInteraction
from misc import setup_language, has_new_day_begun

# init
config = Configuration()
setup_language(config.language)
interact = ServerInteraction(config)
all_views = {}


@app.get('/trigger/{user_id}')
def trigger_given_user(user_id):
    logger.debug(f'trigger user with id {user_id}')
    username = 'unknown'
    if user_id in interact.select_users:
        interact.media_folders_locker(user_id)
        username = interact.select_users[user_id]
        for _, view in all_views.items():
            if user_id == view['user_id']:
                interact.refresh_view(view, user_id)
    return {'name': username}


@app.get('/trigger')
def trigger_all_users():
    logger.debug('trigger all users')
    if has_new_day_begun():
        logger.info('new day reset')
        interact.reset_altered_limits()
        interact.enable_accounts()
    for user_id in interact.select_users:
        interact.media_folders_locker(user_id)
    for _, view in all_views.items():
        interact.refresh_view(view, view['user_id'])
    return {'all done'}


@ui.page('/', title='JellyWatchWise')
async def index():
    view = {
        'user_id': None,
        'user_link': None,
        'folders': None,
        'time_left': 0,
        'time_watched_msg': None,
        'time_left_msg': None,
        'default_limit_msg': None,
        'altered_limit_msg': None,
        'active_msg': None,
        'progress': 0,
    }
    link = None

    class TimeLeftLabel(ui.label):
        def _handle_text_change(self, text: str) -> None:
            super()._handle_text_change(text)
            if view['time_left'] > 0:
                self.classes(replace='text-positive')
            else:
                self.classes(replace='text-negative')

    def change_user(event: ValueChangeEventArguments):
        user_id = event.value
        username = interact.select_users[user_id]
        ui.notify(i18n.t('selected', u=username))
        interact.refresh_view(view, user_id)
        link.props(f'href="{view["user_link"]}"')  # no official support to bind target

    def change_limit(diff):
        if diff != 0:
            msg = i18n.t('add', t=diff) if diff > 0 else i18n.t('sub', t=-diff)
            ui.notify(msg)
        user_id = view['user_id']
        logger.info(f'user {user_id} limit change: {diff}')
        interact.alter_limit(user_id, diff)
        interact.media_folders_locker(user_id)
        trigger_given_user(user_id)

    def disable_user(lock: bool):
        user_id = view['user_id']
        logger.info(f'user {user_id} is disabled: {lock}')
        ui.notify(i18n.t('locked') if lock else i18n.t('unlocked'))
        interact.disable_user(user_id, lock)
        trigger_given_user(user_id)

    def on_connect():
        logger.debug(f'client connected: ID {ui.context.client.id}')
        all_views[ui.context.client.id] = view
        interact.refresh_view(view, config.default_user)

    def on_disconnect():
        logger.debug(f'client disconnected: ID {ui.context.client.id}')
        del all_views[ui.context.client.id]

    ui.context.client.on_connect(lambda: on_connect())
    ui.context.client.on_disconnect(lambda: on_disconnect())

    try:
        await ui.context.client.connected()
        ip = ui.context.client.environ['asgi.scope']['client'][0]

        if not config.is_access_granted(ip):
            ui.label(i18n.t('restricted', ip=ip))
        else:
            with ui.row():
                with ui.column():
                    with ui.button_group():
                        props = "outlined dropdown-icon='img:https://cdn.quasar.dev/logo-v2/svg/logo.svg' prefix=' '"
                        ui.select(interact.select_users, value=config.default_user, on_change=change_user).props(props)

                with ui.card():
                    ui.label().bind_text_from(view, 'time_watched_msg')
                    ui.linear_progress(show_value=False).bind_value_from(view, 'progress').props('color=purple')
                    TimeLeftLabel().bind_text_from(view, 'time_left_msg')

            with ui.card():
                ui.label().bind_text_from(view, 'altered_limit_msg')
                with ui.button_group().props('outline rounded push'):
                    ui.button('-30', on_click=lambda: change_limit(-30))
                    ui.button('-10', on_click=lambda: change_limit(-10))
                    ui.button('-5', on_click=lambda: change_limit(-5))
                    ui.button('+5', on_click=lambda: change_limit(5)).props('outline')
                    ui.button('+10', on_click=lambda: change_limit(10)).props('outline')
                    ui.button('+30', on_click=lambda: change_limit(30)).props('outline')
                ui.label().bind_text_from(view, 'default_limit_msg').style('color:#CCC')

            with ui.card():
                ui.label().bind_text_from(view, 'active_msg')
                ui.button(i18n.t('lock'), on_click=lambda: disable_user(True)).props('color=red')
                ui.button(i18n.t('unlock'), on_click=lambda: disable_user(False)).props('color=green')

            with ui.expansion(i18n.t('tech'), icon='build').style('color:#CCC; font-size:-1'):
                link_style = 'color:#AAA; font-size:-1'
                url = f'{view["user_link"]}'
                link = ui.link(target=url, new_tab=True).bind_text_from(view, 'user_id').style(link_style)
                with ui.element('div').classes('p-2 bg-blue-100'):
                    ui.label().bind_text_from(view, 'folders').style('color:#AAA; font-size:-1; white-space: pre-wrap')

    except TimeoutError:  # ui.context.client.connected() may throw it
        pass


if config.polling_interval > 0:
    interval_sec = config.polling_interval * 60
    ui.timer(interval_sec, lambda: trigger_all_users())

ui.run(uvicorn_reload_includes='*.py, *.yaml')
