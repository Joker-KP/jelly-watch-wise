import os.path
from datetime import datetime, timedelta

import i18n
import yaml

from config import logger
from jellyfin.api import ServerApi
from jellyfin.stats import PlaytimeReporting, JellyStats


class FoldersBackup:
    def __init__(self):
        self.folder_backup_name = 'config/user-folders.bck'

    def keep_user_folders(self, user_id, folders):
        count = len(folders)
        logger.debug(f'keep folders of user {user_id}, total {count}')
        if count > 0:
            folders_collection = {}
            if os.path.isfile(self.folder_backup_name):
                with open(self.folder_backup_name, 'r') as file:
                    folders_collection = yaml.safe_load(file)
            folders_collection[user_id] = folders
            with open(self.folder_backup_name, 'w') as file:
                yaml.dump(folders_collection, file)

    def restore_user_folders(self, user_id):
        logger.debug(f'restore user folders {user_id}')
        if os.path.isfile(self.folder_backup_name):
            with open(self.folder_backup_name, 'r') as file:
                backup = yaml.safe_load(file)
                if user_id in backup:
                    return backup[user_id]
        return []


class ServerInteraction:
    def __init__(self, config):
        self.config = config
        self.backup = FoldersBackup()
        if config.stats_host:
            stats = JellyStats(config.stats_host, config.stats_token)
        else:
            stats = PlaytimeReporting(config.host, config.token)
        self.api = ServerApi(config.host, config.token, stats)
        self.select_users = config.get_select_users(self.api.get_users())
        self.user_data = self.get_user_data()

    def get_user_data(self):
        user_data = {}
        for user_id in self.select_users:
            limit = self.config.get_limit(user_id)
            folders = self.api.get_enabled_folders(user_id)
            self.backup.keep_user_folders(user_id, folders)
            user_data[user_id] = {'folders': folders, 'altered_limit': limit}
        return user_data

    def media_folders_locker(self, user_id):
        logger.debug('media folders lock/unlock')
        time = self.get_today_watched_min(user_id)
        time_left = self.user_data[user_id]['altered_limit'] - time
        folders = self.api.get_enabled_folders(user_id)
        self.backup.keep_user_folders(user_id, folders)
        if time_left > 0:
            prev_folders = self.user_data[user_id]['folders']
            if len(prev_folders) == 0:
                prev_folders = self.backup.restore_user_folders(user_id)
            if len(folders) == 0 and len(prev_folders) > 0:
                self.api.set_enabled_folders(user_id, prev_folders)
                logger.info('folders restored')
        else:
            if len(folders) > 0:
                self.user_data[user_id]['folders'] = folders  # keep folders for later restore
                self.api.set_enabled_folders(user_id, [])
                logger.info('folders disabled - soft lock action')

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
            self.user_data[user_id]['altered_limit'] = self.config.get_limit(user_id)

    def enable_accounts(self):
        if self.config.account_enable_on_day_reset:
            for user_id in self.select_users:
                self.disable_user(user_id, False)

    def refresh_model(self, model, user_id):
        if model['user_id'] != user_id:
            model['altered_limit'] = self.user_data[user_id]['altered_limit']
            model['user_id'] = user_id
        is_disabled = self.api.is_user_disabled(user_id)
        time_watched = self.get_today_watched_min(user_id)
        time_left = model['altered_limit'] - time_watched
        default_limit = self.config.get_limit(user_id)
        self.user_data[user_id]['altered_limit'] = model['altered_limit']  # keep on changing users
        folders = self.user_data[user_id]['folders']

        model['time_left'] = time_left
        model['time_watched_msg'] = i18n.t('watched', t=time_watched)
        model['time_left_msg'] = i18n.t('left', t=time_left) if time_left > 0 else i18n.t('exceed', t=-time_left)
        model['default_limit_msg'] = i18n.t('default', t=default_limit)
        model['altered_limit_msg'] = i18n.t('today', t=model['altered_limit'])
        model['active_msg'] = i18n.t('disabled') if is_disabled else i18n.t('enabled')
        model['progress'] = time_watched / model['altered_limit']
        model['folders'] = "Folders:\n" + " \n".join(folders)
