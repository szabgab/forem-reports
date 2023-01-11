import datetime
import requests
import os
import json
import argparse
import time
import pathlib
import re
from jinja2 import Environment, FileSystemLoader

def collect(host, limit, sleep, api_key):
    print(f"collect({host}, {limit}, {sleep})")

    data = pathlib.Path.cwd().joinpath('data', host)
    if not data.exists():
        data.mkdir()
    print(f"Data dir: {data}")
    get_recent_articles(host, data, api_key)
    update_authors(host, limit, sleep, api_key)

def fetch(host, url, api_key):
    print(f"fetch({host}, {url})")
    headers = {'Accept': 'application/vnd.forem.api-v1+json'}

    url = f"https://{host}{url}"

    headers['api-key'] = api_key

    res = requests.get(url, headers = headers)
    if res.status_code != 200:
        print(f"Failed request. Status code {res.status_code}")
        print(res.text)
        exit(1)
    return res.json()

def update_authors(host, limit, sleep, api_key):
    data = pathlib.Path.cwd().joinpath('data', host)
    with open(data.joinpath('articles.json')) as fh:
        articles = json.load(fh)
    users = data.joinpath('users')
    if not users.exists():
        users.mkdir()
    per_page = 50

    # likely spammers: people who have signed up in the last 2 days and have more than one post
    # potential spammers or first time posters: people who have signed up in the last 2 days and have one post
    # first time posters: people who signed up more than 2 days ago and have a total of 1 post anf it is among the most recent N posts

    articles_by_author = {}

    for article in articles:
        limit -= 1
        #print(article["user"])
        uid = article["user"]["user_id"]
        username = article["user"]["username"]
        print(f"Author: username={username} uid={uid}")

        if uid not in articles_by_author:
            articles_by_author[uid] = []
        articles_by_author[uid].append(article)
        if len(articles_by_author[uid]) > 1:
            continue

        user_file = users.joinpath(f'{uid}.json')
        if user_file.exists():
            with user_file.open() as fh:
                user = json.load(fh)
                if user["article_count"] > 20:
                    continue

        user = fetch(host, f'/api/users/{uid}', api_key)
        #print(user)
        user_articles = fetch(host, f'/api/articles?username={username}&page=1&per_page={per_page}', api_key)
        time.sleep(sleep)
        #print(len(user_articles))
        user["article_count"] = len(user_articles)

        with open(user_file, 'w') as fh:
            json.dump(user, fh)

        if limit <= 0:
            break

def get_recent_articles(host, data, api_key):
    per_page = 100

    recent_articles = fetch(host, f'/api/articles/latest?page=1&per_page={per_page}', api_key)

    print(f"Number of elements in response: {len(recent_articles)}")
    if len(recent_articles) == 0:
       return
    articles_file = data.joinpath('articles.json')

    articles = []
    if os.path.exists(articles_file):
        with open(articles_file) as fh:
            articles = json.load(fh)

    seen = set(article['id'] for article in articles)
    # print(f"seen: {seen}")

    new_articles = []
    for article in recent_articles:
        if article['id'] in seen:
            continue
        new_articles.append(article)

    articles_to_save = []
    for article in new_articles + articles:
        ts = datetime.datetime.strptime(f'{article["published_at"][0:-1]}+0000', '%Y-%m-%dT%H:%M:%S%z')
        elapsed_time = now-ts
        if elapsed_time.total_seconds() < 60 * 60 * 24:
            articles_to_save.append(article)
    articles_to_save.sort(key=lambda article: article["published_at"], reverse=True)

    with open(articles_file, 'w') as fh:
        json.dump(articles_to_save, fh)
    filename = time.strftime("stats-%Y-%m-%d--%H-%M-%S.json")

    print(f"newly added articles: {len(new_articles)}")

    return

def update_stats(host):
    data = pathlib.Path.cwd().joinpath('data', host)
    with open(data.joinpath('articles.json')) as fh:
        articles = json.load(fh)
    last_hour = 0
    last_day = 0
    for article in articles:
        ts = datetime.datetime.strptime(f'{article["published_at"][0:-1]}+0000', '%Y-%m-%dT%H:%M:%S%z')
        elapsed_time = now-ts
        #print(elapsed_time)
        if elapsed_time.total_seconds() < 60 * 60:
            last_hour += 1
        if elapsed_time.total_seconds() < 60 * 60 * 24:
            last_day += 1
    print(f"last_hour: {last_hour} last_day: {last_day}")
    line = json.dumps({'timestamp': str(now), 'last_hour': last_hour, 'last_day': last_day})
    with open(data.joinpath('stats.json'), 'a') as fh:
        fh.write(f"{line}\n")

def generate_html(host, title):
    print(f"generate_html({host}, {title})")
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # print(now)

    data = pathlib.Path.cwd().joinpath('data', host)
    users = data.joinpath('users')

    with open(data.joinpath('stats.json')) as fh:
        all_stats = fh.readlines()
    stats = json.loads(all_stats[-1])

    with open(data.joinpath('articles.json')) as fh:
        articles = json.load(fh)
    for article in articles:
        #print(article["published_at"]) # "2022-12-25T16:44:28Z"
        ts = datetime.datetime.strptime(f'{article["published_at"][0:-1]}+0000', '%Y-%m-%dT%H:%M:%S%z')
        elapsed_time = now-ts
        elapsed_time = elapsed_time - datetime.timedelta(microseconds=elapsed_time.microseconds)
        article["elapsed_time"] = elapsed_time
        uid = article["user"]["user_id"]
        user_file = users.joinpath(f"{uid}.json")
        if user_file.exists():
            with user_file.open() as fh:
                article["usr"] = json.load(fh)
                joined_at = article["usr"]["joined_at"] # Aug 7, 2021
                joined_ts = datetime.datetime.strptime(f"{joined_at} +0000", '%b %d, %Y %z')
                #print(joined_ts)
                diff = today-joined_ts
                #print(diff)
                #print(diff.days)
                article["usr"]["days_since_signup"] = diff.days
                #print(joined_ts.tzinfo)
        else:
            article["usr"] = {}

    html = pathlib.Path.cwd().joinpath('_site')
    if not html.exists():
        html.mkdir()

    html = html.joinpath(host)
    if not html.exists():
        html.mkdir()

    template = 'index.html'

    templates_dir = pathlib.Path(__file__).parent.joinpath('templates')
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    html_template = env.get_template(template)
    html_content = html_template.render(
        articles = articles,
        stats    = stats,
        host     = host,
        title    = title,
        now      = now,
    )
    html_content = re.sub(r'^\s+', '', html_content, flags=re.MULTILINE)

    with open(html.joinpath('index.html'), 'w') as fh:
        fh.write(html_content)

def generate_main_html(hosts):

    html = pathlib.Path.cwd().joinpath('_site')
    if not html.exists():
        html.mkdir()

    stats = {}
    for host in hosts.keys():
        data = pathlib.Path.cwd().joinpath('data', host)
        with data.joinpath('stats.json').open() as fh:
            lines = fh.readlines()
        stats[host] = json.loads(lines[-1])

    template = 'main.html'
    templates_dir = pathlib.Path(__file__).parent.joinpath('templates')
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    html_template = env.get_template(template)
    html_content = html_template.render(
        hosts = hosts,
        stats = stats,
        title = 'Forem-based sites',
        now = now,
    )

    with open(html.joinpath('index.html'), 'w') as fh:
        fh.write(html_content)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html',    help='Generate the HTML report', action='store_true')
    parser.add_argument('--stats',   help='Generate stats', action='store_true')
    parser.add_argument('--collect', help='Get the data from the Forem API', action='store_true')
    parser.add_argument('--sleep',   help='How much to sleep between calls', type=int, default=0)
    parser.add_argument('--host',    help='The hostname of the Forem site', required=True)
    parser.add_argument('--limit',   help='Max number of people to check', type=int, default=2)
    parser.add_argument('--public',  help='No need for API_KEY', action='store_true')
    args = parser.parse_args()

    if not args.html and not args.collect and not args.stats:
        parser.print_help()
        exit()

    return args

def main():
    args = get_args()
    hosts = {
        'dev.to':                    'DEV.to',
        'community.codenewbie.org': 'CodeNewbie',
    }

    if args.host not in hosts:
        exit('Invalid host')

    if args.collect:
        env_variable = re.sub(r'\.', '_', args.host).upper() + "_API_KEY"
        #print(f"env_variable: {env_variable}")
        api_key = os.environ.get(env_variable)
        if not args.public and api_key is None:
            exit(f"Environment variable {env_variable} with the API key is missing you can get one from https://{args.host}/settings/extensions")

        collect(args.host, args.limit, args.sleep, api_key)

    if args.stats:
        update_stats(args.host)

    if args.html:
        generate_html(args.host, hosts[args.host])

    generate_main_html(hosts)

if __name__ == "__main__":
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    main()

