import json
from abc import abstractmethod

import requests

from misc import get_hours_of_today


class AggregatedStatsSource:
    @abstractmethod
    def get_total_time_sec(self, user_id, date_start, date_end):
        pass


class PlaytimeReporting(AggregatedStatsSource):
    def __init__(self, server, token):
        self.server = server
        self.token = token
        self.headers = {'Authorization': f'MediaBrowser Token={self.token}',
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'}
        self.decoder = json.JSONDecoder()

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


class JellyStats(AggregatedStatsSource):
    def __init__(self, server, token):
        self.server = server
        self.token = token
        self.headers = {'accept': 'application/json',
                        'content-Type': 'application/json',
                        'x-api-token': f'{self.token}'}
        self.decoder = json.JSONDecoder()

    def get_total_time_sec(self, user_id, date_start, date_end):
        hours = get_hours_of_today()
        payload = {
            'hours': f'{hours}',
            'userid': f'{user_id}'
        }
        r = requests.post(f"{self.server}/stats/getGlobalUserStats", headers=self.headers, data=json.dumps(payload))
        time_sec = 0
        if r.status_code == 200:
            result_text = self.decoder.decode(r.text)["total_playback_duration"]
            if result_text:
                time_sec = int(result_text)
        return time_sec
