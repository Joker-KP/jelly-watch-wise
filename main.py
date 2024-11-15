# TODO
# dockerize


import i18n
from nicegui import app, ui
from nicegui.events import ValueChangeEventArguments

from config import Configuration
from jellyfin.interact import ServerInteraction
from misc import clip, init_language, get_today

model = {
    'user_id': None,
    'time_left': 0,
    'altered_limit': 0,
    'time_watched_msg': None,
    'time_left_msg': None,
    'default_limit_msg': None,
    'altered_limit_msg': None,
    'active_msg': None,
    'progress': 0
}

# init
config = Configuration()
interact = ServerInteraction(config)
init_language(config.language)
model['today'] = get_today()


class TimeLeftLabel(ui.label):
    def _handle_text_change(self, text: str) -> None:
        super()._handle_text_change(text)
        if model['time_left'] > 0:
            self.classes(replace='text-positive')
        else:
            self.classes(replace='text-negative')


def change_user(event: ValueChangeEventArguments):
    user_id = event.value
    username = interact.select_users[user_id]
    ui.notify(i18n.t('selected', u=username))
    interact.refresh_model(model, user_id)


def change_limit(diff):
    if diff != 0:
        msg = i18n.t('add', t=diff) if diff > 0 else i18n.t('sub', t=-diff)
        ui.notify(msg)
    user_id = model['user_id']
    model['altered_limit'] = clip(model['altered_limit'] + diff, 0, 360)
    interact.refresh_model(model, user_id)
    interact.media_folders_locker(user_id)


def disable_user(lock: bool):
    user_id = model['user_id']
    interact.disable_user(user_id, lock)
    ui.notify(i18n.t('locked') if lock else i18n.t('unlocked'))
    interact.refresh_model(model, user_id)


@app.get('/trigger/{user_id}')
def trigger_given_user(user_id):
    if user_id in interact.select_users:
        interact.media_folders_locker(user_id)
        username = interact.select_users[user_id]
        return {'name': username}
    return {'name': 'unknown'}


@app.get('/trigger')
def trigger_all_users():
    # print("trigger action")
    if model['today'] != get_today():  # new day detection
        model['today'] = get_today()
        interact.reset_altered_limits()
        interact.enable_accounts()
    for user_id in interact.select_users:
        interact.media_folders_locker(user_id)
    return {'all done'}


@ui.page('/', title='JellyWatchWise')
async def index():
    try:
        await ui.context.client.connected()
        ip = ui.context.client.environ['asgi.scope']['client'][0]

        if not config.is_access_granted(ip):
            ui.label(i18n.t('restricted'))
        else:
            with ui.row():
                with ui.column():
                    with ui.button_group():
                        props = "outlined dropdown-icon='img:https://cdn.quasar.dev/logo-v2/svg/logo.svg' prefix=' '"
                        ui.select(interact.select_users, value=config.default_user, on_change=change_user).props(props)

                with ui.card():
                    ui.label().bind_text_from(model, 'time_watched_msg')
                    ui.linear_progress(show_value=False).bind_value_from(model, 'progress').props('color=purple')
                    TimeLeftLabel().bind_text_from(model, 'time_left_msg')

            with ui.card():
                ui.label().bind_text_from(model, 'altered_limit_msg')
                with ui.button_group().props('outline rounded push'):
                    ui.button('-30', on_click=lambda: change_limit(-30))
                    ui.button('-10', on_click=lambda: change_limit(-10))
                    ui.button('-5', on_click=lambda: change_limit(-5))
                    ui.button('+5', on_click=lambda: change_limit(5)).props('outline')
                    ui.button('+10', on_click=lambda: change_limit(10)).props('outline')
                    ui.button('+30', on_click=lambda: change_limit(30)).props('outline')
                ui.label().bind_text_from(model, 'default_limit_msg').style('color:#CCC')

            with ui.card():
                ui.label().bind_text_from(model, 'active_msg')
                ui.button(i18n.t('lock'), on_click=lambda: disable_user(True)).props('color=red')
                ui.button(i18n.t('unlock'), on_click=lambda: disable_user(False)).props('color=green')

            ui.label().bind_text_from(model, 'user_id').style('color:#CCC; font-size:-1')

            interact.refresh_model(model, config.default_user)

    except TimeoutError:  # ui.context.client.connected() may throw it
        pass


if config.polling_interval > 0:
    interval_sec = config.polling_interval * 60
    ui.timer(interval_sec, lambda: trigger_all_users())
ui.run()
