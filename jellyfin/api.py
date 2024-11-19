import json

import requests


class ServerApi:
    def __init__(self, server, token):
        self.server = server
        self.token = token
        self.headers = {'Authorization': f'MediaBrowser Token={self.token}',
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'}
        self.decoder = json.JSONDecoder()

    def get_users(self):
        users = {}
        r = requests.get(f'{self.server}/Users', headers=self.headers)
        if r.status_code == 200:
            users = self.decoder.decode(r.text)
            users = {x["Id"]: x["Name"] for x in users}
        return users

    def get_total_time_sec(self, user_id, date_start, date_end):
        sql = f"SELECT SUM(PlayDuration) AS TotalTime FROM PlaybackActivity WHERE UserId='{user_id}'" \
              f" AND DateCreated > '{date_start}' AND DateCreated < '{date_end}'"
        payload = {'CustomQueryString': sql}
        r = requests.post(f"{self.server}/user_usage_stats/submit_custom_query", headers=self.headers,
                          data=json.dumps(payload))
        time_sec = 0
        if r.status_code == 200:
            result_text = self.decoder.decode(r.text)["results"][0][0]
            if result_text:
                time_sec = int(result_text)
        return time_sec

    def get_user_policy(self, user_id):
        user = requests.get(f'{self.server}/Users/{user_id}', headers=self.headers)
        if user.status_code != 200:
            print("Error fetching user data")
            return None
        return self.decoder.decode(user.text)["Policy"]

    def set_user_policy(self, user_id, policy):
        r = requests.post(f'{self.server}/Users/{user_id}/Policy', headers=self.headers, data=json.dumps(policy))
        if r.status_code != 204:
            print("Error on updating user policy")

    def disable_user(self, user_id, is_disabled: bool):
        policy = self.get_user_policy(user_id)
        policy["IsDisabled"] = is_disabled
        self.set_user_policy(user_id, policy)

    def is_user_disabled(self, user_id):
        policy = self.get_user_policy(user_id)
        return policy["IsDisabled"]

    def get_enabled_folders(self, user_id):
        return self.get_user_policy(user_id)["EnabledFolders"]

    def set_enabled_folders(self, user_id, folders):
        policy = self.get_user_policy(user_id)
        policy["EnabledFolders"] = folders
        self.set_user_policy(user_id, policy)
