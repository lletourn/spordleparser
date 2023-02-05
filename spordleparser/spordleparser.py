import argparse
import bs4
import collections
import logging
import json
import re
import requests
import sys


logger = logging.getLogger(__name__)


def parse_game_page(page_data: str):
    soup = bs4.BeautifulSoup(page_data, "lxml")
    goals = soup.findAll('div', {"id": "goal_summary"})[0].findAll('div', {"class": "goal_container"})
    goal_scorers = collections.defaultdict(int)
    goal_assists = collections.defaultdict(int)
    for goal in goals:
        goal_scorer_name = goal.findAll('span', {'class': 'goal_scorer_name'})[0].get_text()
        goal_scorer_name = re.sub(' +', ' ', goal_scorer_name).replace('\n', '')
        goal_scorers[goal_scorer_name] = goal_scorers[goal_scorer_name] + 1
        goal_assists_names = goal.findAll('span', {'class': 'goal_assist_name'})
        for ga_name in goal_assists_names:
            goal_assists_name = ga_name.get_text()
            goal_assists_name = re.sub(' +', ' ', goal_assists_name).replace('\n', '')
            goal_assists[goal_assists_name] = goal_assists[goal_assists_name] + 1

    return goal_scorers, goal_assists


def main():
    parser = argparse.ArgumentParser(description='Run detection on hockey broadcast videos.')
    parser.add_argument("-l", "--log", help="log level (default: info)", choices=["debug", "info", "warning", "error", "critical"], default="info")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--subseason", type=int, required=True)
    parser.add_argument("--team", type=int, required=True)
    parser.add_argument("--category", type=int, required=True)
    args = parser.parse_args()

    logdatefmt = '%Y%m%dT%H:%M:%S'
    logformat = '%(asctime)s.%(msecs)03d [%(levelname)s] -%(name)s- -%(threadName)s- : %(message)s'
    logging.basicConfig(datefmt=logdatefmt, format=logformat, level=args.log.upper())

    season = args.season
    sub_season = args.subseason
    category = args.category
    team = args.team

    schedule_url = f'https://www.publicationsports.com/stats/ligue/lrhr/horaire_equipe.html?season={season}&subSeason={sub_season}&category={category}&team={team}'
    session = requests.Session()
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

    goal_scorers = collections.defaultdict(int)
    goal_assists = collections.defaultdict(int)
    for game_id, game in event_data['gamesInfo'].items():
        if not game['gameIsPlayed']:
            continue
        game_url = f'https://www.publicationsports.com/stats/ligue/lrhr/sommaire.html?season={season}&subSeason={sub_season}&category={category}&game={game_id}&team={team}'
        resp = session.get(game_url)
        if(resp.status_code >= 500):
            logger.error("Failed to fetch game. Code: {} URL: {}".format(resp.status_code, game_url))
            sys.exit(1)

        game_goal_scorers, game_goal_assists = parse_game_page(resp.text)
        for k, v in game_goal_scorers.items():
            goal_scorers[k] = goal_scorers[k] + v
        for k, v in game_goal_assists.items():
            goal_assists[k] = goal_assists[k] + v

    print("Goals: ")
    for k, v in sorted(goal_scorers.items(), key=lambda x: x[1], reverse=True):
        print(f'{k}: {v}')
    print("Assists: ")
    for k, v in sorted(goal_assists.items(), key=lambda x: x[1], reverse=True):
        print(f'{k}: {v}')


if __name__ == '__main__':
    main()
