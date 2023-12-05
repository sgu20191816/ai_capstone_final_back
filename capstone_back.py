from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from flask import make_response
import time

app = Flask(__name__)
app.config['DEBUG'] = True
CORS(app)  # CORS 설정 추가

@app.route('/')
def home():
    return "Welcome to the Flask App!"

# 전역 변수로 저장된 데이터를 보관
stored_data = {}

# 기초대사량 계산 함수
def calculate_bmr(height, weight, age, gender):
    if gender == 'male':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    return bmr

# 하루 권장 칼로리 섭취량 계산 함수
def calculate_daily_calorie_intake(bmr, activity_level):
    if activity_level == '매우 낮음':
        return bmr * 1.2
    elif activity_level == '낮음':
        return bmr * 1.375
    elif activity_level == '보통':
        return bmr * 1.55
    elif activity_level == '높음':
        return bmr * 1.725
    elif activity_level == '매우 높음':
        return bmr * 1.9
    else:
        return bmr # 기본값
    
# 지정된 위치의 맛집 리스트와 각 맛집의 추천 메뉴 칼로리를 계산하는 함수
def get_dining_options(location):
    # 엑셀 파일 로드
    dining_data = pd.read_excel('C:\\Users\\82109\\Documents\\카카오톡 받은 파일\\diningcode_seoulyummy.xlsx', sheet_name=location)
    menu_calories = pd.read_excel('C:\\Users\\82109\\Documents\\카카오톡 받은 파일\\search_results1202최종.xlsx')

    # 메뉴 칼로리 정보를 딕셔너리로 변환
    calories_dict = menu_calories.set_index('검색어')['평균 칼로리'].to_dict()

    # 맛집 리스트에 칼로리 정보 추가
    dining_data['추천메뉴 칼로리'] = dining_data['추천메뉴'].map(calories_dict)

    # 위도와 경도 정보를 추가하기 위한 geolocator 객체 생성
    geolocator = Nominatim(user_agent="South Korea")

    # 맛집 리스트에 칼로리 정보와 위도, 경도 정보 추가
    dining_data['추천메뉴 칼로리'] = dining_data['추천메뉴'].map(calories_dict)
    dining_data['latitude'] = None
    dining_data['longitude'] = None

    for index, row in dining_data.iterrows():
        try:
            location = geolocator.geocode(row['주소'])
            if location:
                dining_data.at[index, 'latitude'] = location.latitude
                dining_data.at[index, 'longitude'] = location.longitude
        except Exception as e:
            print(f"Error in geocoding: {e}")
        print('success!')
    print(dining_data)
    return dining_data

# 역지오코딩을 통해 위도와 경도를 한국 지역명으로 변환하는 함수
def get_korean_location_name(latitude, longitude):
    geolocator = Nominatim(user_agent="South Korea")
    try:
        location = geolocator.reverse((latitude, longitude), timeout=10)  # 타임아웃 설정
        if location:
            return location.address  # 전체 주소 반환
        else:
            return "주소를 찾을 수 없음"
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return f"역지오코딩 오류: {e}"

@app.route('/calculate', methods=['POST'])
def calculate_calories():
    global stored_data  # 전역 변수 사용
    data = request.json
    height = float(data['height'])
    weight = float(data['weight'])
    age = float(data['age'])
    gender = data['gender']
    activity_level = data['activityLevel']
    #consumed_calories = data['consumed_calories']
    consumed_calories = 573
    latitude = data['location']['latitude']
    longitude = data['location']['longitude']
    # 위치 정보를 한국 지역명으로 변환
    location = get_korean_location_name(latitude, longitude)
    location = location.split(',')
    location = location[6]
    location += '맛집'
    location = location.lstrip(' ')

    bmr = calculate_bmr(height, weight, age, gender)
    daily_calorie_intake = calculate_daily_calorie_intake(bmr, activity_level)
    remaining_calories = daily_calorie_intake - consumed_calories

    #지정된 위치의 맛집 리스트 가져오기
    dining_options = get_dining_options(location)

    #사용자의 남은 칼로리에 맞는 맛집 필터링
    recommended_dining = dining_options[dining_options['추천메뉴 칼로리'] <= remaining_calories]

    # 필터링된 맛집 데이터에서 '맛집명'과 '주소' 열만 선택
    selected_columns = recommended_dining[['음식점명','latitude','longitude']]

    # 이 데이터를 to_dict 메서드를 사용하여 딕셔너리로 변환
    selected_data_dict = selected_columns.to_dict(orient='records')

    # 변환된 딕셔너리를 stored_data에 저장
    # stored_data = {
    #     "remaining_calories": remaining_calories,
    #     "recommended_dining": selected_data_dict
    # }
    stored_data = selected_data_dict

    return jsonify({"message": "Data processed and stored."})
    #return jsonify({"remaining_calories": remaining_calories, "recommended_dining": recommended_dining.to_dict(orient='records')})

@app.route('/get-calories', methods=['GET'])
def get_calories():
    # 저장된 데이터 반환
    global stored_data
    response = make_response(jsonify(stored_data))
    print(response.headers)  # 응답 헤더 출력
    print(stored_data)
    s = jsonify(stored_data)
    return jsonify(stored_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')