from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)

from pymongo import MongoClient
import certifi

ca=certifi.where()

client = MongoClient('mongodb+srv://test:1111@cluster0.0euf5qj.mongodb.net/cluster0?retryWrites=true&w=majority')
db = client.TodaysJandi

SECRET_KEY ='TODAYJANDI'

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
# 그렇지 않으면, 개발자(=나)가 회원들의 비밀번호를 볼 수 있으니까요.^^;
import hashlib

@app.route('/')
def home():
    return render_template('members.html')

# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/members/join', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    github_receive = request.form['github_give']
    nickname_receive = request.form['nickname_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    # 비밀번호를 해쉬로 처리합니다. 암호화하여 저장, 단방향 암호화
    db.jandi.insert_one({'id': id_receive, 'pw': pw_hash, 'github' : github_receive ,'nickname': nickname_receive})

    return jsonify({'result': 'success'})

@app.route('/members/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.jandi.find_one({'id': id_receive, 'pw': pw_hash})
    print(result)

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
    result = db.jandi.find_one({'id': id_receive})
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
    team_list = list(db.jandiTeams.find({}, {'_id': False}))
    return jsonify({'teams': team_list})

# 팀을 생성한다.
@app.route('/teams/create', methods=["POST"])
def create_team():
    access_receive = request.form['access_give']
    teamName_receive = request.form['TeamName_give']
    teamPassword_receive = request.form['TeamPassword_give']
    members_receive = ["user1"] # 추후 만든 사람 닉네임으로 바꾸는 작업 해야됨

    team_list = list(db.jandiTeams.find({}, {'_id': False}))
    num = 0 if (len(team_list) == 0) else team_list[(len(team_list)) - 1]['num'] + 1

    doc = {
        'num': num,
        'access' : access_receive,
        'TeamName': teamName_receive,
        'TeamPassword': teamPassword_receive,
        'members': members_receive
    }
    db.jandiTeams.insert_one(doc)
    return jsonify({'msg': '팀 생성 성공!'})

# 팀에 참가한다.
# @app.route('teams/join', methods=['POST'])
# def join_team() :x

if __name__ == '__main__':
    app.run('0.0.0.0', port=8080, debug=True)