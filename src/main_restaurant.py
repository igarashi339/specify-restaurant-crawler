import os
import time
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
from selenium import webdriver
from line_handler import LineHandler
import urllib
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


TARGET_URL = os.environ["SCRAPING_TARGET_URL"]
WEEKDAY_LIST = ["月","火","水","木","金","土","日"]
CONTINUE_TIME_SECOND = 3600
RETRY_NUM = 6


def get_target_date_obj_list():
    """
    クローリング対象のdatetimeオブジェクトのリストを取得する。
    """
    # 7/23
    date_str_list = ["2022-7-23 12:00:00"]
    target_date_list = []
    for date_str in date_str_list:
        target_date = datetime(2022, 7, 23, 12, 0, 0, 0, tzinfo=timezone(timedelta(hours=9)))
        target_date_list.append(target_date)
    return target_date_list


def fetch_single_date_restaurant_info(driver, target_datetime_obj, line_handler):
    """
    予約可能なレストラン名称をリストにして返す。
    """
    path = "/sp/restaurant/list/"
    target_date_str = target_datetime_obj.strftime('%Y%m%d')
    param = f"useDate={target_date_str}&" \
            f"mealDivInform=&" \
            f"adultNum=2&" \
            f"childNum=0&" \
            f"childAgeInform=&" \
            f"restaurantTypeInform=&" \
            f"restaurantNameCd=&" \
            f"wheelchairCount=0&" \
            f"stretcherCount=0&" \
            f"showWay=&" \
            f"reservationStatus=1&" \
            f"beforeUrl=%2Finternalerror%2F&" \
            f"wayBack="
    url = TARGET_URL + path + "?" + param
    print(url)
    driver.get(url)
    time.sleep(5)
    icon_show_restaurant_list = []
    for i in range(RETRY_NUM):
        icon_show_restaurant_list = driver.find_elements_by_class_name("iconShowRestaurant")
        if len(icon_show_restaurant_list) != 0:
            break
        time.sleep(5)
    if len(icon_show_restaurant_list) == 0:
        raise Exception(f"{RETRY_NUM}回リトライしましたがアクセスできませんでした。")
    got_reservation_list = driver.find_elements_by_class_name("hasGotReservation")
    can_reserve_restaurant_name_list = []
    for got_reservation in got_reservation_list:
        name = got_reservation.find_elements_by_class_name("name")
        can_reserve_restaurant_name_list.append(name[0].text)
        # 7/23対応
        if "オチェーアノ" in name and "ブッフェ" in name:
            line_handler.broadcast(f"7/23(土) オチェーアノ／ブッフェ 予約できそう！\n{url}")
    return can_reserve_restaurant_name_list



def main():
    driver = webdriver.Remote(
            command_executor=os.environ["SELENIUM_URL"],
            desired_capabilities=DesiredCapabilities.FIREFOX.copy())
    driver.implicitly_wait(5)
    line_handler = LineHandler()
    target_date_obj_list = get_target_date_obj_list()

    time_start = time.time()
    while True:
        if time.time() - time_start > CONTINUE_TIME_SECOND:
            break
        for target_datetime_obj in target_date_obj_list:
            target_datetime_str = format(target_datetime_obj, '%Y/%m/%d')
            try:
                can_reserve_restaurant_list = fetch_single_date_restaurant_info(driver, target_datetime_obj, line_handler)
                print(can_reserve_restaurant_list)
            except Exception as e:
                print(f"クローリングに失敗しました: {target_datetime_str}")
                print(e)
    driver.quit()


if __name__ == "__main__":
    main()





