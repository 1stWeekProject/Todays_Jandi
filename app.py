from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)

from pymongo import MongoClient
import certifi

ca=certifi.where()

client = MongoClient("mongodb+srv://test:sparta@cluster0.clu05af.mongodb.net/Cluster0?retryWrites=true&w=majority", tlsCAFile=ca)
db = client.dbsparta

SECRET_KEY ='TODAYJANDI'

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
# 그렇지 않으면, 개발자(=나)가 회원들의 비밀번호를 볼 수 있으니까요.^^;
import hashlib
#################################
##  HTML을 주는 부분             ##
#################################

#################################
##  로그인을 위한 API            ##
#################################
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
    group = ""
    id_list = list(db.jandi.find({}, {'_id': False}))
    num = len(id_list)



    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
# 비밀번호를 해쉬로 처리합니다. 암호화하여 저장, 단방향 암호화
    db.jandi.insert_one({'id': id_receive, 'pw': pw_hash, 'github' : github_receive ,'nickname': nickname_receive, 'group' : group,'num' : num})

    return jsonify({'result': 'success'})

@app.route('/members/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.jandi.find_one({'id': id_receive, 'pw': pw_hash})


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




if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)