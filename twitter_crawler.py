# Requirements
# - input: url của một tổ chức (twiter)
# - out: tweet id, tweet account, content, date, và location của các bài post của tổ chức đó trong năm đó
# Import Dependencies
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common import exceptions

import argparse
import os
import json
from time import sleep
import pandas as pd


user_data=dict()
tweet_data = dict()
un = 'xxxx'
pw = 'xxxx'

def launchBrowserToGetCookies():
    driver = webdriver.Chrome(ChromeDriverManager().install())
    driver.get("https://twitter.com/login")

    # Setup the log in
    sleep(3)

    username = driver.find_element(By.XPATH, "//input[@name='text']")
    username.send_keys(un)
    next_button = driver.find_element(By.XPATH, "//span[contains(text(),'Next')]")
    next_button.click()

    sleep(3)
    password = driver.find_element(By.XPATH, "//input[@name='password']")
    password.send_keys(pw)
    log_in = driver.find_element(By.XPATH, "//span[contains(text(),'Log in')]")
    log_in.click()


    sleep(3)
    cookies = driver.get_cookies()
    to_file("cookies.json", cookies)

def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

def launchBrowserWithCookies(cookies, src):
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    driver = webdriver.Chrome(ChromeDriverManager().install(), desired_capabilities=caps)

    # Get into destination page
    driver.get(src)
    # cookies = json.load(open('myfile.json'))
    for cookie in cookies:
        driver.add_cookie(cookie)
    sleep(3)
    driver.get(src)

    last_height = driver.execute_script("return document.body.scrollHeight")
    while(True):
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Wait to load page
        sleep(5)
        extractLog(driver)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def extractLog(driver):
    # extract requests from logs
    browser_log = driver.get_log('performance')
    events = [process_browser_log_entry(entry) for entry in browser_log]
    logs = [event for event in events if 'Network.response' in event['method']]
    global sum
    global user_data
    global tweet_data
    for log in filter(log_filter, logs):
        request_id = log["params"]["requestId"]
        resp_url = log["params"]["response"]["url"]
        if "UserTweets" in resp_url:
            try:
                response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                json_dict = json.loads(response["body"])
                instructions_index = len(json_dict['data']["user"]["result"]["timeline_v2"]["timeline"]["instructions"]) - 1
                entries = json_dict['data']["user"]["result"]["timeline_v2"]["timeline"]["instructions"][instructions_index]["entries"]

                tweet_data.update(get_tweet_data(entries))
                to_file("out/tweet_data.json", tweet_data)
            except exceptions.WebDriverException:
                print("Exception")
        if "UserByScreenName" in resp_url:
            try:
                response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                json_dict = json.loads(response["body"])
                json_dict = json_dict['data']["user"]["result"]["legacy"]
                user_data = get_user_data(json_dict)
                to_file("out/user_data.json", user_data)
            except exceptions.WebDriverException:
                print("")

def to_pd():
    with open('out/tweet_data.json', 'r') as f:
        data = json.load(f)
    result = [data[i] for i in data]
    result_1 = ((i["twitter_id"],
                 i["content"],
                 i["view"],
                 i["favorite_count"],
                 i["reply_count"],
                 i["retweet_count"],
                 i["quote_count"],
                 i["created_at"],
                 i["img_url"]) for i in result)

    df = pd.DataFrame(result_1
                      , columns=['Twitter id', 'Content', 'View', 'Favorite Count', 'Reply Count', 'Retweet Count',
                                 'Quote Count', 'Created At', "Image URL"])

    df.to_csv(r"out/tweet_data.csv", index=False)

def to_file(filename, obj):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # out_file = open(filename, "w")
    with open(filename, "w") as f:
        json.dump(obj, f, indent=6)
    # out_file.close()

list_key = ["content", "itemContent","tweet_results", "result", "legacy"]
def check(obj, list_key):
    for key in list_key:
        if key in obj:
            obj = obj[key]
        else:
            return False
    return True

def get_tweet_data(entries):
    objs = [{
        "twitter_id": i['entryId'].split('-')[1],
        "content": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"] if check(i, list_key) else None,
        "view": i["content"]["itemContent"]["tweet_results"]["result"]["views"]['count'] if check(i, list_key) and 'count' in i["content"]["itemContent"]["tweet_results"]["result"]["views"] else None,
        "favorite_count": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"] if check(i, list_key) else None,
        "reply_count": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"] if check(i, list_key) else None,
        "retweet_count": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"] if check(i, list_key) else None,
        "quote_count": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"] if check(i, list_key) else None,
        "created_at": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"] if check(i, list_key) else None,
        "img_url": i["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0][
            "media_url_https"] if check(i, list_key) and "media" in i["content"]["itemContent"]["tweet_results"]["result"]["legacy"][
            "entities"] else None
    } for i in entries if 'tweet' in i['entryId']]
    # } for i in entries if 'itemContent' in i['content'] and 'tweet' in i['entryId']]
    # } for i in entries]

    data = {i["twitter_id"]: i for i in objs}
    return data

def get_user_data(user_result):
    # user_result = entries[0]["content"]["itemContent"]["tweet_results"]["result"]["core"]["user_results"]["result"]
        return {
            # "rest_id": user_result["rest_id"],
            "name": user_result["name"],
            "screen_name": user_result["screen_name"],
            "friends_count": user_result["friends_count"],
            "created_at": user_result["created_at"],
            "favourites_count": user_result["favourites_count"],
            "followers_count": user_result["followers_count"],
            # "profile_banner_url": user_result["legacy"]["profile_banner_url"],
            "profile_image_url_https": user_result["profile_image_url_https"],
            "statuses_count": user_result["statuses_count"],
            "verified": user_result["verified"]
        }

def log_filter(log_):
    return (
        # is an actual response
            log_["method"] == "Network.responseReceived"
            # and json
            and "json" in log_["params"]["response"]["mimeType"]
            and( "UserTweets" in log_["params"]["response"]["url"]
            or "UserByScreenName" in log_["params"]["response"]["url"])
    )


def main():
    parser = argparse.ArgumentParser(description='Crawl tweets.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--cookies", action="store_true" , help="get cookies for the first time log-in")
    parser.add_argument("src", help="Twitter url")
    # parser.add_argument("dest", help="Destination location")
    args = parser.parse_args()
    config = vars(args)

    if (config["cookies"] == True):
        launchBrowserToGetCookies()
        cookies = json.load(open('cookies.json'))
        print("Cookies is created in cookies.json...")
        print(f'Starting crawl data from {config["src"]}')
        launchBrowserWithCookies(cookies, config["src"])
        to_pd()
    else:
        try:
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
                print("A cookies is loaded...")
                print(f'Starting crawl data from {config["src"]}')
                if cookies is not None:
                    launchBrowserWithCookies(cookies, config["src"])
                    to_pd()
        except Exception:
            msg = "Sorry, the file cookies.json does not exist. Please create cookies then run again."
            print(msg)


if __name__ == "__main__":
   main()

