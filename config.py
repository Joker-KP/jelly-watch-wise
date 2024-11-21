import logging
from datetime import datetime
from os.path import isfile

import yaml

logger: logging.Logger = logging.getLogger('watchwise')

LOG_LEVELS = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
}


def setup_logging(log_level=logging.INFO):
    logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)7s] %(message)s'))
    file_handler = logging.FileHandler('config/watchwise.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.propagate = False
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def validate_limit_values(user_id, values):
    if isinstance(values, int):
        return
    if isinstance(values, list) and len(values) == 2:
        return
    if isinstance(values, list) and len(values) == 7:
        return
    logger.warning(f'Improper limit for {user_id}: type {type(values)}')


def get_limit(values):
    if isinstance(values, int):
        return values
    if isinstance(values, list):
        weekday = datetime.today().weekday()
        if len(values) == 2:
            return values[0] if weekday < 5 else values[1]
        if len(values) == 7:
            return values[weekday]
    return None


class Configuration:
    def __init__(self, config_files=['config.yaml', 'config/config.yaml', '/config/config.yaml']):
        self.config = None
        for config_file in config_files:
            if isfile(config_file):
                with open(config_file, 'r') as file:
                    self.config = yaml.safe_load(file)
                    self.log_level = self.get_key('general', 'log_level', 'info')
                    setup_logging(LOG_LEVELS[self.log_level])
                    logger.info(f'Configuration read from: {config_file}')
        if self.config is None:
            raise FileNotFoundError(", ".join(config_files) + " - not found")

        self.host = self.get_key('server', 'host', None)
        self.token = self.get_key('server', 'token', None)

        self.default_limit = self.get_key('limits', 'default_limit', 60)
        self.user_limits = self.get_key('limits', 'user_limits', {})
        self.no_limit_users = self.get_key('limits', 'no_limit_users', [])
        self.polling_interval = self.get_key('limits', 'polling_interval', 0)
        self.account_enable_on_day_reset = self.get_key('limits', 'account_enable_on_day_reset', False)

        self.default_user = self.get_key('view', 'default_user', None)
        self.language = self.get_key('view', 'language', 'en')

        self.stats_host = self.get_key('stats', 'host', None)
        self.stats_token = self.get_key('stats', 'token', None)

        self.limit_clients = self.get_key('access', 'limit_clients', False)
        self.accepted_clients = self.get_key('access', 'accepted_clients', ["127.0.0.", "192.168.", "10."])

        self.validate_limits()

    def get_key(self, primary_key, secondary_key, default_value):
        if primary_key in self.config:
            if secondary_key in self.config[primary_key]:
                value = self.config[primary_key][secondary_key]
                return value if value != "" else default_value
        return default_value

    def validate_config_users(self, users):
        ids = [self.default_user] + [x for x in self.user_limits] + [x for x in self.no_limit_users]
        for i in ids:
            if i not in users:
                print(f"Could not find user id <{i}>.")

    def fix_default_user(self, select_users):
        if not self.default_user:
            self.default_user = next(iter(select_users))

    def get_select_users(self, users):
        select_users = {k: v for k, v in users.items() if k not in self.no_limit_users}
        self.fix_default_user(select_users)
        return select_users

    def is_access_granted(self, ip):
        if not self.limit_clients:
            return True
        for accepted in self.accepted_clients:
            if ip.startswith(accepted):
                return True
        return False

    def validate_limits(self):
        validate_limit_values("default", self.default_limit)
        for user_id, values in self.user_limits.items():
            validate_limit_values(user_id, values)

    def get_limit(self, user_id):
        default_limit = get_limit(self.default_limit)
        user_limit = None
        if user_id in self.user_limits:
            user_limit = get_limit(self.user_limits[user_id])
        return user_limit if user_limit else default_limit
