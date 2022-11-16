from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

# # 현재 사용중인 몽고디비로 바꿔주세요~
# client = MongoClient()
# db = client.bs4db

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)