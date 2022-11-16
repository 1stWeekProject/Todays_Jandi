import datetime

from flask import Flask, render_template, request
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from datetime import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}

client = MongoClient('mongodb+srv://test:sparta@cluster0.ds2cbhe.mongodb.net/Cluster0?retryWrites=true&w=majority')
db = client.dbjandi

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route("/teams/withdrawl", methods=["DELETE"])
def team_withdrwal():
    team_id = request.form['team_id']
    print("팀 멤버 삭제", team_id)
    user_id = 1
    db.team.update_one(
        {'num': int(team_id)},  # db에 있는 type 확인!
        {'$pull': {"member": {"num": str(user_id)}}}) # db에 있는 type 확인

    return "ok"


@app.route("/teams/grasses/<int:team_id>", methods=["GET"])
def team_info(team_id):
    team = db.team.find_one({'num': team_id})

    GITHUB_NICKNAME_KEY = 'github_name'
    github_nicknames = [i[GITHUB_NICKNAME_KEY] for i in team['member']]
    member_commit_counts = []
    for github_nickname in github_nicknames:
        commit_counts = get_daily_commit_count(github_nickname)
        member_commit_counts.append(commit_counts)

    MEMBER_NICKNAME_KEY = 'nickname'
    member_nicknames = [i[MEMBER_NICKNAME_KEY] for i in team['member']]

    member_infos = list(zip(member_nicknames, member_commit_counts, github_nicknames))

    return render_template('team.html',
                           member_infos=member_infos,
                           team_id=team_id)


def get_daily_commit_count(github_nickname):
    request_url = 'https://github.com/{}'.format(github_nickname)
    data = requests.get(request_url, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    today = datetime.today().strftime("%Y-%m-%d")
    print(today)

    daily_commit = soup.select_one("rect[data-date='{}']".format(today))
    if daily_commit is None:
        raise ValueError('잘못된 Github nickname')

    daily_commit_count = daily_commit['data-count']
    return daily_commit_count


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
