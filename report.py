import datetime
import requests
import os
import json
import argparse
import time
import pathlib
from jinja2 import Environment, FileSystemLoader

def collect(host, limit, sleep):
    print(f"collect({host}, {limit})")

    data = pathlib.Path.cwd().joinpath('data')
    if not data.exists():
        data.mkdir()
    print(f"Data dir: {data}")
    get_recent_articles(host, data)
    update_authors(host, limit, sleep)

def fetch(host, url):
    print(url)
    headers = {'Accept': 'application/vnd.forem.api-v1+json'}

    url = f"https://{host}{url}"

    if host == 'dev.to':
        api_key = os.environ.get('DEV_TO_API_KEY')

    if api_key:
        headers['api-key'] = api_key

    res = requests.get(url, headers = headers)
    if res.status_code != 200:
        print(f"Failed request. Status code {res.status_code}")
        print(res.text)
        exit(1)
    return res.json()


def update_authors(host, limit, sleep):
    data = pathlib.Path.cwd().joinpath('data')
    with open(data.joinpath('articles.json')) as fh:
        articles = json.load(fh)
    users = data.joinpath('users')
    if not users.exists():
        users.mkdir()
    per_page = 50

    for article in articles:
        limit -= 1
        #print(article["user"])
        uid = article["user"]["user_id"]
        username = article["user"]["username"]
        print(f"{username} {uid}")
        user_file = users.joinpath(f'{uid}.json')
        if user_file.exists():
            with user_file.open() as fh:
                user = json.load(fh)
                if user["article_count"] > 20:
                    continue

        user = fetch(host, f'/api/users/{uid}')
        #print(user)
        user_articles = fetch(host, f'/api/articles?username={username}&page=1&per_page={per_page}')
        time.sleep(sleep)
        #print(len(user_articles))
        user["article_count"] = len(user_articles)

        with open(user_file, 'w') as fh:
            json.dump(user, fh)

        if limit <= 0:
            break

def get_recent_articles(host, data):
    per_page = 100

    articles = fetch(host, f'/api/articles/latest?page=1&per_page={per_page}')

    print(f"Number of elements in response: {len(articles)}")
    if len(articles) == 0:
       return

    with open(data.joinpath('articles.json'), 'w') as fh:
        json.dump(articles, fh)
    filename = time.strftime("stats-%Y-%m-%d--%H-%M-%S.json")

def generate_html():
    print("generate_html")
    now = datetime.datetime.now(datetime.timezone.utc)
    # print(now)

    data = pathlib.Path.cwd().joinpath('data')
    users = data.joinpath('users')

    with open(data.joinpath('articles.json')) as fh:
        articles = json.load(fh)
    for article in articles:
        #print(article["published_at"]) # "2022-12-25T16:44:28Z"
        ts = datetime.datetime.strptime(f'{article["published_at"][0:-1]}+0000', '%Y-%m-%dT%H:%M:%S%z')
        elapsed_time = now-ts
        article["elapsed_time"] = elapsed_time
        uid = article["user"]["user_id"]
        user_file = users.joinpath(f"{uid}.json")
        if user_file.exists():
            with user_file.open() as fh:
                article["usr"] = json.load(fh)
        else:
            article["usr"] = {}

    html = pathlib.Path.cwd().joinpath('_site')
    if not html.exists():
        html.mkdir()

    template = 'index.html'

    templates_dir = pathlib.Path(__file__).parent.joinpath('templates')
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    html_template = env.get_template(template)
    html_content = html_template.render(
        articles = articles,
    )

    with open(html.joinpath('index.html'), 'w') as fh:
        fh.write(html_content)

def get_args():
    main_parser = argparse.ArgumentParser(add_help=False)
    main_parser.add_argument('--html',    help='Generate the HTML report', action='store_true')
    main_parser.add_argument('--collect', help='Get the data from the Forem API', action='store_true')
    main_parser.add_argument('--sleep',   help='How much to sleep between calls', type=int, default=0)
    main_args, _ = main_parser.parse_known_args()
    if not main_args.html and not main_args.collect:
        main_parser.print_help()
        exit()

    parser = argparse.ArgumentParser(parents=[main_parser])
    if main_args.collect:
        #parser.add_argument('--username',  help='The username on the Forem site', required=main_args.collect)
        parser.add_argument('--host',      help='The hostname of the Forem site', required=main_args.collect)
        parser.add_argument('--limit',     help='Max number of people to check', type=int, default=2)

    args = parser.parse_args()

    return args

def main():
    args = get_args()

    if args.collect:
        hosts = ('dev.to', 'community.codenewbie.org')
        if args.host not in hosts:
            exit('Invalid host')
        collect(args.host, args.limit, args.sleep)

    if args.html:
        generate_html()

main()

