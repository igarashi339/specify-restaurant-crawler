import os
import time
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from db_handler import DBHandler
from line_handler import LineHandler
from datetime import datetime, timezone, timedelta

HOST = os.environ["SCRAPING_TARGET_URL"]
WEEKDAY_LIST = ["月","火","水","木","金","土","日"]
ROUND_PER_EXEC = 60  # Job1回あたりに何回転するか
MAX_RETRY = 4


def get_target_date_obj_list():
    """
    クローリング対象のdatetimeオブジェクトのリストを取得する。
    """
    target_date_list = [datetime(2022, 3, 12, tzinfo=timezone(timedelta(hours=9)))]
    return target_date_list


def fetch_all_restaurant_name(driver, target_datetime_obj):
    """
    すべてのレストランの名称を返却する。
    """
    path = "/sp/restaurant/list/"
    # クローリング当日に近い日付だとパークレストランが表示されないため10日後にしている
    ten_days_after_datetime = target_datetime_obj + timedelta(days=10)
    ten_days_after_datetime_str = ten_days_after_datetime.strftime('%Y%m%d')
    param = f"useDate={ten_days_after_datetime_str}&" \
            f"mealDivInform=&" \
            f"adultNum=2&" \
            f"childNum=0&" \
            f"childAgeInform=&" \
            f"restaurantTypeInform=&" \
            f"restaurantNameCd=&" \
            f"wheelchairCount=0&" \
            f"stretcherCount=0&" \
            f"showWay=&" \
            f"reservationStatus=0&" \
            f"beforeUrl=%2Finternalerror%2F&" \
            f"wayBack="
    url = HOST + path + "?" + param
    driver.get(url)
    time.sleep(5)
    icon_show_restaurant_list = []
    for i in range(MAX_RETRY):
        icon_show_restaurant_list = driver.find_elements_by_class_name("iconShowRestaurant")
        if len(icon_show_restaurant_list) != 0:
            break
        time.sleep(5)
    if len(icon_show_restaurant_list) == 0:
        raise Exception(f"{MAX_RETRY}回リトライしましたがアクセスできませんでした。")

    # ディズニーランド
    disney_land_restaurant_list = [name.text for name in driver.find_elements_by_css_selector(".location4 .name")]
    # ディズニーシー
    disney_sea_restaurant_list = [name.text for name in driver.find_elements_by_css_selector(".location5 .name")]
    # アンバサダーホテル
    ambassador_restaurant_list = [name.text for name in driver.find_elements_by_css_selector(".location1 .name")]
    # ホテルミラコスタ
    miracosta_restaurant_list = [name.text for name in driver.find_elements_by_css_selector(".location2 .name")]
    # ディズニーランドホテル
    disney_land_hotel_restaurant_list = [name.text for name in driver.find_elements_by_css_selector(".location3 .name")]
    # トイストーリーホテル
    toy_story_hotel_restaurant_list = [name.text for name in driver.find_elements_by_css_selector(".location7 .name")]

    park_restaurant_list = disney_land_restaurant_list + disney_sea_restaurant_list
    hotel_restaurant_list = ambassador_restaurant_list + miracosta_restaurant_list + \
                            disney_land_hotel_restaurant_list + toy_story_hotel_restaurant_list
    all_restaurant_list = park_restaurant_list + hotel_restaurant_list

    return all_restaurant_list, park_restaurant_list, hotel_restaurant_list


def fetch_single_date_restaurant_info(driver, target_datetime_obj):
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
    url = HOST + path + "?" + param
    driver.get(url)
    time.sleep(5)
    icon_show_restaurant_list = []
    for i in range(MAX_RETRY):
        icon_show_restaurant_list = driver.find_elements_by_class_name("iconShowRestaurant")
        if len(icon_show_restaurant_list) != 0:
            break
        time.sleep(5)
    if len(icon_show_restaurant_list) == 0:
        raise Exception(f"{MAX_RETRY}回リトライしましたがアクセスできませんでした。")
    got_reservation_list = driver.find_elements_by_class_name("hasGotReservation")
    can_reserve_restaurant_name_list = []
    for got_reservation in got_reservation_list:
        name = got_reservation.find_elements_by_class_name("name")
        can_reserve_restaurant_name_list.append(name[0].text)
    return can_reserve_restaurant_name_list


def get_status_updated_restaurant_info(db_handler, target_datetime_obj, all_restaurant_name_list, can_reserve_restaurant_name_list):
    """
    予約可能情報の差分を返却する。
    """
    cannot_reserve_to_reserve = []  # 予約不可 -> 予約可
    reserve_to_cannot_reserve = []  # 予約可 -> 予約不可
    restaurant_status_dict = db_handler.select_from_drestaurant_status_dict(target_datetime_obj)
    for restaurant_name in all_restaurant_name_list:
        previous_status = restaurant_status_dict.get(restaurant_name)
        current_status = (restaurant_name in can_reserve_restaurant_name_list)
        # 予約不可 -> 予約可
        if not previous_status and current_status:
            cannot_reserve_to_reserve.append(restaurant_name)
        # 予約可 -> 予約不可
        if previous_status and not current_status:
            reserve_to_cannot_reserve.append(restaurant_name)
    return cannot_reserve_to_reserve, reserve_to_cannot_reserve


def update_db(db_handler, target_datetime_obj, cannot_reserve_to_reserve, reserve_to_cannot_reserve):
    """
    クローリンクした結果をDBに格納する。
    """
    for restaurant_name in cannot_reserve_to_reserve:
        db_handler.update_drestaurant_status(target_datetime_obj, restaurant_name, True)
    for restaurant_name  in reserve_to_cannot_reserve:
        db_handler.delete_drestaurant_status(target_datetime_obj, restaurant_name)


def post_to_media(target_date_obj, cannot_reserve_to_reserve, park_restaurant_list, hotel_restaurant_list, line_handler):
    """
    メディアに投稿する。
    """
    # ツイートにのせるURLを生成
    path = "/sp/restaurant/list/"
    target_date_str = target_date_obj.strftime('%Y%m%d')
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
    url = HOST + path + "?" + param

    dt_now_utc_aware = datetime.now(timezone(timedelta(hours=9)))
    weekday_str = WEEKDAY_LIST[target_date_obj.weekday()]

    # パークレストラン、ホテルレストランごとにツイートする
    tweet_target_park_restaurant_set = set(cannot_reserve_to_reserve) & set(park_restaurant_list)
    tweet_target_hotel_restaurant_set = set(cannot_reserve_to_reserve) & set(hotel_restaurant_list)
    # 個人的にほしいやつ
    if format(target_date_obj, '%Y/%m/%d') == "2022/03/12" and "シェフ・ミッキー" in tweet_target_park_restaurant_set:
        line_handler.broadcast(f"2022/03/12 シェフミッキー空いてるよ！\n{url}")


def main():
    driver = webdriver.Remote(
        command_executor=os.environ["SELENIUM_URL"],
        desired_capabilities=DesiredCapabilities.FIREFOX.copy())
    driver.implicitly_wait(5)
    db_handler = DBHandler()
    line_handler = LineHandler()
    target_date_obj_list = get_target_date_obj_list()
    all_restaurant_name, park_restaurant_list, hotel_restaurant_list \
        = fetch_all_restaurant_name(driver, target_date_obj_list[0])
    for counter in range(ROUND_PER_EXEC):
        for target_datetime_obj in target_date_obj_list:
            time.sleep(5)
            target_datetime_str = format(target_datetime_obj, '%Y/%m/%d')
            try:
                can_reserve_restaurant_name_list = fetch_single_date_restaurant_info(driver, target_datetime_obj)
            except Exception as e:
                print(f"クローリングに失敗しました：{target_datetime_str}")
                print(e)
                continue
            cannot_reserve_to_reserve, reserve_to_cannot_reserve \
                = get_status_updated_restaurant_info(db_handler,
                                                     target_datetime_obj,
                                                     all_restaurant_name,
                                                     can_reserve_restaurant_name_list)
            update_db(db_handler, target_datetime_obj, cannot_reserve_to_reserve, reserve_to_cannot_reserve)
            try:
                if len(cannot_reserve_to_reserve) != 0:
                    post_to_media(target_datetime_obj,
                                  cannot_reserve_to_reserve,
                                  park_restaurant_list,
                                  hotel_restaurant_list,
                                  line_handler)
                print(target_datetime_str, cannot_reserve_to_reserve, reserve_to_cannot_reserve)
            except Exception as e:
                print(f"メディアへの投稿に失敗しました：{target_datetime_str}")
                print(e)
    driver.quit()


if __name__ == "__main__":
    main()
