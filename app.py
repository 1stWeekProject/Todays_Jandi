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
from apscheduler.schedulers.background import BackgroundScheduler

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


def get_daily_commit_count(github_nickname, specific_date):
    request_url = 'https://github.com/{}'.format(github_nickname)
    data = requests.get(request_url, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    daily_commit = soup.select_one("svg.js-calendar-graph-svg rect[data-date='{}']".format(specific_date))
    if daily_commit is None:
        yesterday = specific_date - timedelta(1)
        daily_commit = soup.select_one("svg.js-calendar-graph-svg rect[data-date='{}']".format(yesterday))

    daily_commit_count = daily_commit['data-count']
    return daily_commit_count


def rank_adjust():
    all_users = list(db.members.find({}, {'_id': False}))
    for user in all_users:
        nickname = user['nickname']
        github = user['github']

        continue_commit_days = 0
        check_day = date.today() - timedelta(1)
        while int(get_daily_commit_count(github, check_day)) > 0:
            continue_commit_days += 1
            check_day = check_day - timedelta(1)

        data = {
            'nickname': nickname,
            'commit_days': continue_commit_days,
        }

        rank = db.ranks.find_one({'nickname': nickname})
        if rank is None:
            db.ranks.insert_one(data)
        else:
            db.ranks.update_one({'nickname': nickname}, {'$set': {'commit_days': continue_commit_days}})


sched = BackgroundScheduler(daemon=True)
sched.add_job(rank_adjust, 'interval', minutes=1)
sched.start()

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
    login_user_id = login_user['id']
    is_user_in_team = False

    team = db.teams.find_one({'num': team_id})

    team_members = []
    for member_id in team['members']:
        if member_id == login_user_id:
            is_user_in_team = True
        team_member = db.members.find_one({'id': member_id}, {'_id': False})
        team_members.append(team_member)

    GITHUB_NICKNAME_KEY = 'github'
    github_nicknames = [i[GITHUB_NICKNAME_KEY] for i in team_members]
    member_commit_counts = []
    today = date.today()
    for github_nickname in github_nicknames:
        commit_counts = get_daily_commit_count(github_nickname, today)
        member_commit_counts.append(commit_counts)

    MEMBER_NICKNAME_KEY = 'nickname'
    member_nicknames = [i[MEMBER_NICKNAME_KEY] for i in team_members]

    member_infos = list(zip(member_nicknames, member_commit_counts, github_nicknames))

    return render_template('team.html',
                           member_infos=member_infos,
                           team_id=team_id,
                           is_team=is_user_in_team)


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

        # 회원의 팀정보를 response로 같이 반환
        joined_team = result['group']
        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token, 'team': joined_team})
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
    members_receive = ["member"]  # 임시정보
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        members_receive[0] = payload['id']
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

    team_list = list(db.teams.find({}, {'_id': False}))
    num = 0 if (len(team_list) == 0) else team_list[(len(team_list)) - 1]['num'] + 1

    doc = {
        'num': num,
        'access': access_receive,
        'TeamName': teamName_receive,
        'TeamPassword': teamPassword_receive,
        'members': members_receive
    }
    db.teams.insert_one(doc)

    db.members.update_one({"id": members_receive[0]}, {"$set": {"group": num}})
    return jsonify({'msg': '팀 생성 성공!', 'num': num})


@app.route('/teams/join_private_team', methods=['POST'])
def join_private_team():
    team_num_receive = int(request.form['team_num_give'])
    password_receive = request.form['password_give']
    token_receive = request.cookies.get('mytoken')
    user_name = ""

    data = db.teams.find_one({"num": team_num_receive})
    db_password = data['TeamPassword']

    if password_receive == db_password:
        try:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_name = payload['id']
        except jwt.ExpiredSignatureError:
            return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
        except jwt.exceptions.DecodeError:
            return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

        member_list = data['members']
        member_list.append(user_name)

        # 중복검사
        for i in member_list:
            if i == user_name:
                return jsonify({'result': 'fail', 'msg': '중복된 회원이 있습니다.'})

        db.members.update_one({"id": user_name}, {"$set": {"group": team_num_receive}})
        db.teams.update_one({"num": team_num_receive}, {"$set": {"members": member_list}}, upsert=True)
        # 이제 선택한 방으로 이동
        return jsonify({'result': 'success', 'msg': '성공'})
    else:
        return jsonify({'result': 'fail', 'msg': '잘못된 비밀번호 입니다.'})


# 팀에 참가한다.
@app.route('/teams/join_public_team', methods=['POST'])
def join_public_team():
    team_num_receive = int(request.form['team_num_give'])
    token_receive = request.cookies.get('mytoken')
    user_name = ""

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
    for i in member_list:
        if (i == user_name):
            return jsonify({'result': 'fail', 'msg': '중복된 회원이 있습니다.'})

    member_list.append(user_name)
    db.members.update_one({"id": user_name}, {"$set": {"group": team_num_receive}})
    db.teams.update_one({"num": team_num_receive}, {"$set": {"members": member_list}}, upsert=True)
    return jsonify({'result': 'success', 'msg': '성공'})


@app.route('/cheer')
def cheer():
    return render_template('comment.html')


@app.route("/cheer/create", methods=["POST"])
def createComment():
    comment_receive = request.form['comment_give']
    time_receive = request.form['time_give']

    jandiComment_list = list(db.postings.find({}, {'_id': False}))
    cnt = len(jandiComment_list) + 1

    # 쿠키 닉네임 빼와서 저장
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    id_receive = db.members.find_one({'id': payload['id']}, {'_id': 0})
    nickname_receive = id_receive['nickname']
    num_receive = id_receive['num']
    valid_receive = id_receive['num']

    doc = {
        'nickname':nickname_receive,
        'comment':comment_receive,
        'time':time_receive,
        'num':num_receive,
        'valid':valid_receive
    }
    db.postings.insert_one(doc)

    return jsonify({'msg': '작성 완료'})


@app.route("/cheer/read", methods=["GET"])
def readComment():
    jandiComment_list = list(db.postings.find({}, {'_id': False}))
    return jsonify({'jandi_comment': jandiComment_list})


@app.route("/cheer/delete", methods=["POST"])
def deleteComment():
    num_receive = request.form['num_give']
    db.postings.delete_one({'num': int(num_receive)})
    return jsonify({'msg': "삭제 완료!"})


@app.route("/cheer/update", methods=["POST"])
def updateComment():
    # num_receive = request.form['num_give']
    # comment_receive = request.form['comment_give']
    # db.postings.update_one({'num': int(num_receive)}, {'$set': {'comment': comment_receive}})
    # return jsonify({'msg': "수정 완료!"})
    num_receive = request.form['num_give']
    comment_receive = request.form['comment_give']
    userinfo = db.postings.find_one({'valid': int(num_receive)})

    if userinfo['valid'] == int(num_receive):
        db.postings.update_one({'num': int(num_receive)}, {'$set': {'comment': comment_receive}})
        return jsonify({'result' : 'success', 'msg': "수정 완료!"})
    else:
        return jsonify({'result' : 'fail', 'msg' : "수정 권한이 없습니다."})

    # try:
    #     payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    #     print(payload)
    #
    #     # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
    #     # 여기에선 그 예로 닉네임을 보내주겠습니다.
    #     userinfo = db.members.find_one({'id': payload['id']}, {'_id': 0})
    #     return jsonify({'result': 'success', 'num': userinfo['num']})
    # except jwt.ExpiredSignatureError:
    #     # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
    #     return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    # except jwt.exceptions.DecodeError:
    #     return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
@app.route('/cheer/update', methods=['GET'])
def commentUpdate_valid():
    token_receive = request.cookies.get('mytoken')

    # try / catch 문?
    # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.members.find_one({'id': payload['id']}, {'_id': 0})

        return jsonify({'result': 'success', 'num': userinfo['num']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


@app.route('/cheer/delete', methods=['GET'])
def commentDelete_valid():
    token_receive = request.cookies.get('mytoken')

    # try / catch 문?
    # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.members.find_one({'id': payload['id']}, {'_id': 0})
        num_receive = userinfo['num']

        return jsonify({'result': 'success', 'num': num_receive})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


@app.route("/ranks", methods=["GET"])
def ranks():
    rank_list = list(db.ranks.find().sort('commit_days', -1).limit(10))
    idxs = []
    for i in range(len(rank_list)):
        idxs.append(i + 1)
    return render_template('rank.html', rank_list=zip(idxs, rank_list))


if __name__ == '__main__':
    app.run('0.0.0.0', port=8080, debug=True)
