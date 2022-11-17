# 오늘의 잔디

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Jinja](https://img.shields.io/badge/jinja-white.svg?style=for-the-badge&logo=jinja&logoColor=black)
![jQuery](https://img.shields.io/badge/jquery-%230769AD.svg?style=for-the-badge&logo=jquery&logoColor=white)
![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)

### [오늘의 잔디 링크](http://52.79.227.227:5000/)

## 오늘의 잔디는?
![Untitled 1](https://user-images.githubusercontent.com/28504937/202376922-91a2a938-32d3-4fa5-ba57-76c46f9c47d4.png)
어떠한 일을 꾸준히 실행하는 것은 쉽지 않은 일입니다. 아프리카 속담 중 **“혼자 가면 빨리가지만 함께 하면 멀리간다.”** 라는 말이 있습니다. 저희팀은 꾸준히, 코딩을 할 수 있도록 하는 비법을  바로 이 속담에서 찾을 수 있었습니다. 저희는 서비스 사용자에게 같이 잔디를 심을 팀을 만들어 서로 응원을 하고 때로는 경쟁을 할 수 있도록 하는 서비스 “**오늘의 잔디**”을 기획해보았습니다.

# 1. 팀 소개
- [백재현](https://github.com/elderanni)
- [이한주](https://github.com/yanJuicy)
- [한교진](https://github.com/hangj97)
- [김재현](https://github.com/tjvm0877)

# 2. 오늘의 잔디
## 잔디란?
![Untitled](https://user-images.githubusercontent.com/28504937/202376814-a690cf68-e0f7-4f0a-b065-0ce38cac73a6.png)
GitHub에서 제공하는 그동안  얼마나 열심히 코딩을 했는지 볼 수 있도록 해주는 기능이 있습니다. 말그대로 얼마나 내가 1년동안 개발한 순간들을 볼 수 있는데 바로 이 기능을 사람들은 **잔디**라고 부릅니다. 

그리고 이 1일 1커밋을 통해 위 그림의 표를 모두 초록색으로 까는 행위를 **‘잔디를 심는다.’** 라고 합니다.

사람들은 이 잔디의 기능을 통하여 자신의 근면 성실함을 보여준다고 합니다. 하지만 저희 팀이 생각하는 1일 1커밋 자체는 무언가 엄청난 일을 해냈다고 생각하지 않습니다. 막말로 `README.MD`에 엔터만 치고 커밋해도 할 수 있는 일이니까요.

저희팀이 생각하는 잔디를 심는 행위를 함으로써 얻을 수 있는 가장 큰 가치는 바로 **꾸준함을 통한 학습의 습관화**입니다.


# 3. ****프로젝트 기능 및 구조****
## 와이어 프레임 / 프로토타입
![Untitled 2](https://user-images.githubusercontent.com/28504937/202376953-05fccc12-339f-49c6-9d73-1f9a429fa7d1.png)


# 4. ****개발 환경 설정****
```python
pip3 install -r requirements.txt
```
### config.json 작성 
예시
```json
{
  "DATABASE" : {
      "DB_HOST": "mongodb_host"
  },
  "JWT": {
      "SECRET_KEY": "secret_key"
  },
  "BS4": {
      "USER_AGENT": "user_agent"
  }
}
```
