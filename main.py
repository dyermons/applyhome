from flask import Flask
import os
import requests
import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)


def get_period_range():
    today = datetime.date.today()
    one_month_ago = today - relativedelta(months=1)
    start_of_week = one_month_ago - datetime.timedelta(
        days=one_month_ago.weekday())
    return start_of_week.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')


def get_monday_of_current_week():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    return monday.strftime('%Y-%m-%d')


def get_apt_detail(start_date, end_date, api_key):
    BASE_URL = 'https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail'
    params = {
        'page': 1,
        'perPage': 100,
        'serviceKey': api_key,
        'cond[RCRIT_PBLANC_DE::GTE]': start_date,
        'cond[RCRIT_PBLANC_DE::LTE]': end_date
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()


def create_message(apt_data, start_date):
    if not apt_data.get('data'):
        return "다음 주 청약 접수 예정 아파트가 없습니다."

    message = f"*조회 기간*: {start_date} 이후\n\n*이번 주 이후 청약 접수 예정 아파트:*\n\n"

    for item in apt_data['data']:
        rcept_bgnde = item.get('RCEPT_BGNDE') or ''
        if rcept_bgnde and start_date > rcept_bgnde:
            continue

        house_secd_nm = item.get('HOUSE_DTL_SECD_NM') or '정보 없음'
        house_nm = item.get('HOUSE_NM') or '정보 없음'
        rcept_endde = item.get('RCEPT_ENDDE') or '정보 없음'
        region = item.get('SUBSCRPT_AREA_CODE_NM') or '정보 없음'
        home_page = item.get('PBLANC_URL') or 'https://www.applyhome.co.kr/'

        house_nm = house_nm.replace('[', '').replace(']', '')

        message += (f"*주택구분*: {house_secd_nm}\n"
                    f"*주택명*: {house_nm}\n"
                    f"*청약접수*: {rcept_bgnde} ~ {rcept_endde}\n"
                    f"*지역명*: {region}\n"
                    f"*청약홈 보기*: [상세보기]({home_page})\n\n")
    return message


def send_telegram_message(message, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    response = requests.post(url, params=params)
    print("텔레그램 응답:", response.text)
    return response.json()


@app.route('/')
def run_script():
    # 오늘 요일 체크
    today = datetime.date.today()
    print(f"[실행됨] 호출 시간: {today}, 요일: {today.weekday()}")
    if today.weekday() != 0:  # 0 = 월요일
        print("➡ 월요일 아님. 실행 안 함")
        return "오늘은 월요일이 아니에요! 실행 안 함 😊"

    print("✅ 월요일이라서 실행 시작!")
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    API_KEY = os.environ['API_KEY']

    this_week_monday = get_monday_of_current_week()
    start_date, end_date = get_period_range()
    apt_data = get_apt_detail(start_date, end_date, API_KEY)
    message = create_message(apt_data, this_week_monday)
    send_telegram_message(message, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return "청약 알림 전송 완료!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
