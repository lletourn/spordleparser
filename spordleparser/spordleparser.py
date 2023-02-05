import argparse
import bs4
import collections
import logging
import json
import re
import requests
import sys


logger = logging.getLogger(__name__)


class PlayerStats:
    __slots__ = 'jersey_number', 'name', 'goals', 'assists', 'penalty_minutes'

    def __init__(self):
        self.jersey_number = -1
        self.name = ""
        self.goals = 0
        self.assists = 0
        self.penalty_minutes = 0


def parse_game_page(page_data: str):
    soup = bs4.BeautifulSoup(page_data, "html5lib")
    player_summary = soup.findAll('div', {"id": "player_summary"})[0]

    team_players_table = None
    for team_player_summary_table in player_summary.findAll('div', {'class': 'table_container'}):
        team_name = team_player_summary_table.findAll('caption', {'class': 'team_name'})[0].findAll('span')[0].get_text()
        if 'HAWKS' in team_name:
            team_players_table = team_player_summary_table
            break
    if team_players_table is None:
        raise Exception("Couldn't find team table")

    players_stats = collections.defaultdict(PlayerStats)
    for row in team_players_table.findAll('tbody')[0].findAll('tr'):
        columns = row.findAll('td')
        name = columns[1].get_text()
        name = re.sub(' +', ' ', name).replace('\n', '')
        players_stats[name].name = columns[0].get_text()
        players_stats[name].jersey_number = columns[0].get_text()
        players_stats[name].goals += int(columns[2].get_text())
        players_stats[name].assists += int(columns[3].get_text())
        players_stats[name].penalty_minutes += int(columns[5].get_text())

    return players_stats


def main():
    parser = argparse.ArgumentParser(description='Run detection on hockey broadcast videos.')
    parser.add_argument("-l", "--log", help="log level (default: info)", choices=["debug", "info", "warning", "error", "critical"], default="info")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--subseasons", type=int, nargs="+", required=True)
    parser.add_argument("--team", type=int, required=True)
    parser.add_argument("--category", type=int, required=True)
    args = parser.parse_args()

    logdatefmt = '%Y%m%dT%H:%M:%S'
    logformat = '%(asctime)s.%(msecs)03d [%(levelname)s] -%(name)s- -%(threadName)s- : %(message)s'
    logging.basicConfig(datefmt=logdatefmt, format=logformat, level=args.log.upper())

    season = args.season
    category = args.category
    team = args.team

    players_stats = collections.defaultdict(PlayerStats)
    session = requests.Session()
    for sub_season in args.subseasons:
        schedule_url = f'https://www.publicationsports.com/stats/ligue/lrhr/horaire_equipe.html?season={season}&subSeason={sub_season}&category={category}&team={team}'
        resp = session.get(schedule_url)
        if(resp.status_code >= 500):
            logger.error("Failed to fetch: {}".format(resp.text))
            sys.exit(1)

        data = resp.text
        event_data = None
        for line in data.splitlines():
            if 'eventsInfo' in line:
                s = line.find('{')
                e = line.rfind('}')
                event_data = json.loads(line[s:e+1])
                break

        for game_id, game in event_data['gamesInfo'].items():
            if not game['gameIsPlayed']:
                continue
            game_url = f'https://www.publicationsports.com/stats/ligue/lrhr/sommaire.html?season={season}&subSeason={sub_season}&category={category}&game={game_id}&team={team}'
            resp = session.get(game_url)
            if(resp.status_code >= 500):
                logger.error("Failed to fetch game. Code: {} URL: {}".format(resp.status_code, game_url))
                sys.exit(1)

            game_players_stats = parse_game_page(resp.text)
            for player_name, game_player_stats in game_players_stats.items():
                players_stats[player_name].name = game_player_stats.name
                players_stats[player_name].jersey_number = game_player_stats.jersey_number
                players_stats[player_name].goals += game_player_stats.goals
                players_stats[player_name].assists += game_player_stats.assists
                players_stats[player_name].penalty_minutes += game_player_stats.penalty_minutes

    print("Stats: ")
    for k, player_stats in sorted(players_stats.items(), key=lambda x: x[1].goals+x[1].assists, reverse=True):
        print(f'{k}: {player_stats.goals}, {player_stats.assists}, {player_stats.penalty_minutes}, {player_stats.goals + player_stats.assists}')


if __name__ == '__main__':
    main()
