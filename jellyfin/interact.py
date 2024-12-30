import os.path
from datetime import datetime, timedelta

import i18n
import yaml

from config import logger
from jellyfin.api import ServerApi
from jellyfin.stats import PlaytimeReporting, JellyStats
from misc import clip


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
            if not self.are_only_unlimited_folders(folders):
                self.backup.keep_user_folders(user_id, folders)
            user_data[user_id] = {'folders': folders, 'altered_limit': limit}
        return user_data

    def are_only_unlimited_folders(self, folders):
        return len(folders) == 0 or all(x in self.config.no_limit_folders for x in folders)

    def keep_unlimited_folders(self, folders):
        return [x for x in folders if x in self.config.no_limit_folders]

    def media_folders_locker(self, user_id):
        logger.debug('media folders lock/unlock')
        time = self.get_today_watched_min(user_id)
        time_left = self.user_data[user_id]['altered_limit'] - time
        folders = self.api.get_enabled_folders(user_id)
        if not self.are_only_unlimited_folders(folders):
            self.backup.keep_user_folders(user_id, folders)
        if time_left > 0:
            prev_folders = self.user_data[user_id]['folders']
            if self.are_only_unlimited_folders(prev_folders):
                prev_folders = self.backup.restore_user_folders(user_id)
            if len(prev_folders) > 0 and len(prev_folders) > len(folders):
                self.api.set_enabled_folders(user_id, prev_folders)
                logger.info('folders restored')
        else:
            if not self.are_only_unlimited_folders(folders):
                self.user_data[user_id]['folders'] = folders  # store all folders for later restore
                kept_folders = self.keep_unlimited_folders(folders)
                self.api.set_enabled_folders(user_id, kept_folders)
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

    def alter_limit(self, user_id, diff):
        current_limit = self.user_data[user_id]['altered_limit']
        self.user_data[user_id]['altered_limit'] = clip(current_limit + diff, 0, 360)

    def get_altered_limit(self, user_id):
        return self.user_data[user_id]['altered_limit']

    def enable_accounts(self):
        if self.config.account_enable_on_day_reset:
            for user_id in self.select_users:
                self.disable_user(user_id, False)

    def refresh_view(self, view, user_id):
        logger.debug('refresh_view started for {}'.format(self.select_users[user_id]))
        is_disabled = self.api.is_user_disabled(user_id)
        time_watched = self.get_today_watched_min(user_id)
        altered_limit = self.get_altered_limit(user_id)
        default_limit = self.config.get_limit(user_id)
        time_left = altered_limit - time_watched
        folders = self.user_data[user_id]['folders']

        if view['user_id'] != user_id:
            view['user_id'] = user_id
            view['user_link'] = f'{self.config.host}/web/#/dashboard/users/access?userId={user_id}'
            logger.debug('user changed for {}, limit: {}'.format(self.select_users[user_id], altered_limit))
        view['time_left'] = time_left
        view['time_watched_msg'] = i18n.t('watched', t=time_watched)
        view['time_left_msg'] = i18n.t('left', t=time_left) if time_left > 0 else i18n.t('exceed', t=-time_left)
        view['default_limit_msg'] = i18n.t('default', t=default_limit)
        view['altered_limit_msg'] = i18n.t('today', t=altered_limit)
        view['active_msg'] = i18n.t('disabled') if is_disabled else i18n.t('enabled')
        view['progress'] = time_watched / altered_limit
        view['folders'] = "Folders:\n" + " \n".join(folders)
