import os
import time
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from line_handler import LineHandler
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


TARGET_URL = os.environ["SCRAPING_TARGET_URL"]
WEEKDAY_LIST = ["月","火","水","木","金","土","日"]
EXEC_PER_HOUR = 2 # 何回転させるか
RETRY_NUM = 6


def get_target_date_obj_list():
    """
    クローリング対象のdatetimeオブジェクトのリストを取得する。
    本日から2か月間を対象とする。
    """
    dt = datetime(2022, 6, 11, 5, 0, 30, 1000, tzinfo=timezone(timedelta(hours=9)))
    target_date_list = []
    for i in range(60):
        target_date_list.append(dt)
    return target_date_list


def fetch_single_date_ticket_info(driver, target_date_obj, line_handler):
    target_url = f"{TARGET_URL}/ticket/search/?parkTicketGroupCd=020&numOfAdult=2&numOfJunior=0&numOfChild=0&parkTicketSalesForm=1&useDays=1&route=1&useDateFrom=20220611&selectParkDay1=01"
    driver.get(target_url)
    time.sleep(9)
    # tdl_str_list = driver.find_elements_by_xpath("//*[@id=\"search-ticket-group\"]/div/section/div[2]/section[1]/div[1]/div/ul/li[1]/span")
    tdl_str_list = driver.find_elements_by_xpath("//*[@id=\"search-ticket-group\"]/div/section/section[1]/div/div[1]/div/ul/li[1]/span")                                   
    tdl_str = tdl_str_list[0].text
    tdl_is_available = False
    if "運営時間" in tdl_str:
        tdl_is_available = True
    print("------------------")
    print(f"tdl_str: {tdl_str}")
    print(f"tdl_is_available: {tdl_is_available}")
    if tdl_is_available:
        line_handler.broadcast(f"5/11のチケットとれそう！\n{target_url}")


def main():
    driver = webdriver.Remote(
            command_executor=os.environ["SELENIUM_URL"],
            desired_capabilities=DesiredCapabilities.FIREFOX.copy())
    driver.implicitly_wait(5)
    line_handler = LineHandler()
    target_date_obj_list = get_target_date_obj_list()
    for counter in range(EXEC_PER_HOUR):
        for target_datetime_obj in target_date_obj_list:
            target_datetime_str = format(target_datetime_obj, '%Y/%m/%d')
            try:
                fetch_single_date_ticket_info(driver, target_datetime_obj, line_handler)
            except Exception as e:
                print(f"クローリングに失敗しました: {target_datetime_str}")
                print(e)
    driver.quit()


if __name__ == "__main__":
    main()





