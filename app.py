from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
import datetime
from datetime import date, timedelta
import certifi
import jwt
import hashlib
import json

with open('config.json', 'r') as f:
    config = json.loads(f.read())

USER_AGENT = config['BS4']['USER_AGENT']
DB_HOST = config['DATABASE']['DB_HOST']
SECRET_KEY = config['JWT']['SECRET_KEY']

headers = {
    'User-Agent': USER_AGENT
}

ca = certifi.where()
client = MongoClient(DB_HOST, tlsCAFile=ca)
db = client.TodaysJandi

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('members.html')


@app.route("/teams/withdrawl", methods=["DELETE"])
def team_withdrwal():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

    login_user = db.members.find_one({'id': user_id}, {'_id': False})
    login_user_nickname = login_user['nickname']

    team_id = request.form['team_id']
    db.teams.update_one(
        {'num': int(team_id)},  # db에 있는 type 확인!
        {'$pull': {"members": {"$in": [login_user_nickname]}}})  # db에 있는 type 확인

    return "ok"


@app.route("/teams/grasses/<int:team_id>", methods=["GET"])
def team_info(team_id):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

    login_user = db.members.find_one({'id': user_id}, {'_id': False})
    login_user_nickname = login_user['nickname']
    is_team = False

    team = db.teams.find_one({'num': team_id})

    team_members = []
    for member_nickname in team['members']:
        if member_nickname == login_user_nickname:
            is_team = True
        team_member = db.members.find_one({'nickname': member_nickname}, {'_id': False})
        team_members.append(team_member)

    GITHUB_NICKNAME_KEY = 'github'
    github_nicknames = [i[GITHUB_NICKNAME_KEY] for i in team_members]
    member_commit_counts = []
    for github_nickname in github_nicknames:
        commit_counts = get_daily_commit_count(github_nickname)
        member_commit_counts.append(commit_counts)

    MEMBER_NICKNAME_KEY = 'nickname'
    member_nicknames = [i[MEMBER_NICKNAME_KEY] for i in team_members]

    member_infos = list(zip(member_nicknames, member_commit_counts, github_nicknames))

    return render_template('team.html',
                           member_infos=member_infos,
                           team_id=team_id,
                           is_team=is_team)


def get_daily_commit_count(github_nickname):
    request_url = 'https://github.com/{}'.format(github_nickname)
    data = requests.get(request_url, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')
    print(soup)

    today = datetime.datetime.today().strftime("%Y-%m-%d")
    print(today)
    print(date.today())
    daily_commit = soup.select_one("rect[data-date='{}']".format(today))
    if daily_commit is None:
        yesterday = date.today() - timedelta(1)
        daily_commit = soup.select_one("rect[data-date='{}']".format(yesterday))

    daily_commit_count = daily_commit['data-count']
    return daily_commit_count


# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/members/join', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    github_receive = request.form['github_give']
    nickname_receive = request.form['nickname_give']
    group = ""
    id_list = list(db.members.find({}, {'_id': False}))
    num = len(id_list)

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    # 비밀번호를 해쉬로 처리합니다. 암호화하여 저장, 단방향 암호화
    db.members.insert_one(
        {'id': id_receive, 'pw': pw_hash, 'github': github_receive, 'nickname': nickname_receive, 'group': group,
         'num': num})

    return jsonify({'result': 'success'})


@app.route('/members/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.

    result = db.members.find_one({'id': id_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=36000)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/members/duplicate', methods=["POST"])
def api_duplicate():
    id_receive = request.form['id_give']
    # id를 가져와 동일한 id를 찾습니다. 찾습니다.
    result = db.members.find_one({'id': id_receive})
    print(result)

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        return jsonify({'result': 'success', 'msg': '중복된 아이디가 있습니다.'})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '사용하셔도 좋은 아이디입니다.'})


@app.route('/search_team')
def serch_team():
    return render_template('search_team.html')


# 현재 생성된 팀 정보들을 가져온다.
@app.route('/teams/get', methods=["GET"])
def get_teams_info():
    # 토큰 확인은 일단 패스
    team_list = list(db.teams.find({}, {'_id': False}))
    return jsonify({'teams': team_list})

# 팀을 생성한다.
@app.route('/teams/create', methods=["POST"])
def create_team():
    access_receive = request.form['access_give']
    teamName_receive = request.form['TeamName_give']
    teamPassword_receive = request.form['TeamPassword_give']
    members_receive = ["member"] # 임시정보
    token_receive = request.cookies.get('mytoken')

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        members_receive[0] = payload['id']
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

    team_list = list(db.teams.find({}, {'_id': False}))
    num = 0 if (len(team_list) == 0) else team_list[(len(team_list)) - 1]['num'] + 1

    doc = {
        'num': num,
        'access' : access_receive,
        'TeamName': teamName_receive,
        'TeamPassword': teamPassword_receive,
        'members': members_receive
    }
    db.teams.insert_one(doc)
    return jsonify({'msg': '팀 생성 성공!'})


@app.route('/teams/join_private_team', methods=['POST'])
def join_private_team() :
    team_num_receive = int(request.form['team_num_give'])
    password_receive = request.form['password_give']
    token_receive = request.cookies.get('mytoken')
    user_name = ""

    data = db.teams.find_one({"num": team_num_receive})
    db_password = data['TeamPassword']

    if (password_receive == db_password):
        try:
            # token을 시크릿키로 디코딩합니다.
            # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_name = payload['id']
        except jwt.ExpiredSignatureError:
            # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
            return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
        except jwt.exceptions.DecodeError:
            return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})
        data = db.teams.find_one({"num": team_num_receive})
        member_list = data['members']
        member_list.append(user_name)

        db.teams.update_one({"num": team_num_receive}, {"$set": {"members": member_list}}, upsert=True)
        # 이제 선택한 방으로 이동
        return jsonify({'result': 'success', 'msg': '성공'})
    else:
        return jsonify({'result': 'success', 'msg': '잘못된 비밀번호 입니다.'})



# 팀에 참가한다.
@app.route('/teams/join_public_team', methods=['POST'])
def join_public_team() :
    team_num_receive = int(request.form['team_num_give'])
    token_receive = request.cookies.get('mytoken')
    user_name = ""

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_name= payload['id']
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

    data = db.teams.find_one({"num": team_num_receive})
    member_list = data['members']
    member_list.append(user_name)

    db.teams.update_one({"num": team_num_receive}, {"$set": {"members": member_list}}, upsert=True)
    # 이제 선택한 방으로 이동
    return jsonify({'result': 'success', 'msg': '성공'})

# 로그아웃 추가 필요

if __name__ == '__main__':
    app.run('0.0.0.0', port=8080, debug=True)
