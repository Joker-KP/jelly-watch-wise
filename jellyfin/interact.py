from datetime import datetime, timedelta

import i18n

from jellyfin.api import ServerApi


class ServerInteraction:
    def __init__(self, config):
        self.config = config
        self.api = ServerApi(config.host, config.token)
        self.select_users = config.get_select_users(self.api.get_users())
        self.user_data = self.get_user_data()

    def get_user_data(self):
        user_data = {}
        for user_id in self.select_users:
            limit = self.config.user_limits[
                user_id] if user_id in self.config.user_limits else self.config.default_limit
            folders = self.api.get_enabled_folders(user_id)
            user_data[user_id] = {"limit": limit, "folders": folders, "altered_limit": limit}
        return user_data

    def media_folders_locker(self, user_id):
        time = self.get_today_watched_min(user_id)
        time_left = self.user_data[user_id]["altered_limit"] - time
        folders = self.api.get_enabled_folders(user_id)
        if time_left > 0:
            prev_folders = self.user_data[user_id]["folders"]
            if len(folders) == 0 and len(prev_folders) > 0:
                # print('restore folders')
                self.api.set_enabled_folders(user_id, prev_folders)
                pass
        else:
            if len(folders) > 0:
                # print('soft lock action - disable folders')
                self.user_data[user_id]["folders"] = folders  # keep folders for later restore
                self.api.set_enabled_folders(user_id, [])

    def get_today_watched_min(self, user_id):
        now = datetime.today()
        date_start = now.strftime('%Y-%m-%d')
        date_end = (now + timedelta(1)).strftime('%Y-%m-%d')
        # date_start = '2024-11-09'
        # date_end = '2024-11-10'
        time = self.api.get_total_time_sec(user_id, date_start, date_end) // 60
        return time

    def disable_user(self, user_id, is_disabled: bool = False):
        self.api.disable_user(user_id, is_disabled)

    def reset_altered_limits(self):
        for user_id in self.select_users:
            self.user_data[user_id]["altered_limit"] = self.user_data[user_id]["limit"]

    def enable_accounts(self):
        if self.config.account_enable_on_day_reset:
            for user_id in self.select_users:
                self.disable_user(user_id, False)

    def refresh_model(self, model, user_id):
        if model['user_id'] != user_id:
            model['altered_limit'] = self.user_data[user_id]["altered_limit"]
            model['user_id'] = user_id
        is_disabled = self.api.is_user_disabled(user_id)
        time_watched = self.get_today_watched_min(user_id)
        time_left = model['altered_limit'] - time_watched
        default_limit = self.user_data[user_id]["limit"]
        self.user_data[user_id]["altered_limit"] = model['altered_limit']  # keep on changing users

        model['time_left'] = time_left
        model['time_watched_msg'] = i18n.t('watched', t=time_watched)
        model['time_left_msg'] = i18n.t('left', t=time_left) if time_left > 0 else i18n.t('exceed', t=-time_left)
        model['default_limit_msg'] = i18n.t('default', t=default_limit)
        model['altered_limit_msg'] = i18n.t('today', t=model['altered_limit'])
        model['active_msg'] = i18n.t('disabled') if is_disabled else i18n.t('enabled')
        model['progress'] = time_watched / model['altered_limit']
