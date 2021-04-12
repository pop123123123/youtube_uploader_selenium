"""This module implements uploading videos on YouTube via Selenium using metadata JSON file
    to extract its title, description etc."""

from typing import DefaultDict, Optional
from selenium_firefox.firefox import Firefox, By, Keys
from collections import defaultdict
import json
import time
import re
from .Constant import *
from pathlib import Path
import logging
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementClickInterceptedException
from dateparser import DateDataParser

logging.basicConfig()


def load_metadata(metadata_json_path: Optional[str] = None) -> DefaultDict[str, str]:
    if metadata_json_path is None:
        return defaultdict(str)
    with open(metadata_json_path) as metadata_json_file:
        return defaultdict(str, json.load(metadata_json_file))

class YoutubeWorker:
    def __init__(self, cookies_path: Optional[str] = None) -> None:
        current_working_dir = str(Path.cwd())
        if cookies_path is None:
            cookies_path = current_working_dir
        self.browser = Firefox(cookies_path, current_working_dir)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def login(self):
        self.browser.get(Constant.YOUTUBE_URL)
        time.sleep(Constant.USER_WAITING_TIME)

        if self.browser.has_cookies_for_current_website():
            self.browser.load_cookies()
            time.sleep(Constant.USER_WAITING_TIME)
            self.browser.refresh()
        else:
            self.logger.info('Please sign in and then press enter')
            input()
            self.browser.get(Constant.YOUTUBE_URL)
            time.sleep(Constant.USER_WAITING_TIME)
            self.browser.save_cookies()

    def quit(self):
        self.browser.driver.quit()

class YouTubeScheduler(YoutubeWorker):
    def __init__(self, timezone: str, cookies_path: Optional[str] = None) -> None:
        super().__init__(cookies_path)
        self.timezone = timezone

    def get_schedule(self):
        try:
            self.login()
            return self.__get_schedule()
        except Exception as e:
            print(e)
            self.quit()
            raise

    def __get_schedule(self) -> list:
        self.browser.get(Constant.YOUTUBE_URL)
        time.sleep(Constant.USER_WAITING_TIME)
        self.browser.get('https://studio.youtube.com/')
        time.sleep(Constant.USER_WAITING_TIME)
        base_url = self.browser.driver.current_url
        suffix = '/videos/upload?filter=[{"name"%3A"VISIBILITY"%2C"value"%3A["HAS_SCHEDULE"]}]&sort={"columnType"%3A"date"%2C"sortOrder"%3A"DESCENDING"}'
        self.browser.get(base_url + suffix)
        time.sleep(Constant.USER_WAITING_TIME)
        lang = self.browser.find(By.TAG_NAME, 'html').get_attribute('lang').split('-')[0]
        settings = {'TIMEZONE': self.timezone, 'RETURN_AS_TIMEZONE_AWARE': True}
        ddp = DateDataParser(languages=[lang], settings=settings)

        LIST_XPATH = '/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[3]/ytcp-content-section/ytcp-video-section/ytcp-video-section-content/div'
        TO_HOVER_CSS = 'ytcp-video-row.style-scope span.ytcp-video-row'
        HOVER_CSS = 'ytcp-paper-tooltip-body.ytcp-paper-tooltip-placeholder > p:nth-child(2) > yt-formatted-string:nth-child(1)'
        DAY_CSS = 'ytcp-video-row.style-scope div.ytcp-video-row.column-sorted'
        TIME_REGEX = r"\d\d:\d\d"

        videoList = self.browser.find(By.XPATH, LIST_XPATH)
        hover_list = self.browser.find_all(By.CSS_SELECTOR, TO_HOVER_CSS, videoList)
        day_list = self.browser.find_all(By.CSS_SELECTOR, DAY_CSS, videoList)

        scheduled_dates = []
        if hover_list is not None and day_list is not None:
            for hoverElement, dayElement in zip(hover_list, day_list):
                self.browser.driver.execute_script("arguments[0].scrollIntoView(true);", hoverElement)
                time.sleep(.2)
                actions = ActionChains(self.browser.driver)
                actions.move_to_element(hoverElement)
                actions.perform()
                time.sleep(Constant.USER_WAITING_TIME)

                hover = self.browser.find(By.CSS_SELECTOR, HOVER_CSS)
                t = re.search(TIME_REGEX, hover.text).group(0)

                d = dayElement.text.split('\n')[0]
                date = ddp.get_date_data(f'{d} {t}')['date_obj'].isoformat()
                scheduled_dates.append(date)

        suffix = '/videos/upload?filter=[{"name"%3A"VISIBILITY"%2C"value"%3A["PUBLIC"]}]&sort={"columnType"%3A"date"%2C"sortOrder"%3A"DESCENDING"}'
        self.browser.get(base_url + suffix)
        time.sleep(Constant.USER_WAITING_TIME)

        videoList = self.browser.find(By.XPATH, LIST_XPATH)
        day_list = self.browser.find_all(By.CSS_SELECTOR, DAY_CSS, videoList)
        if day_list is None:
            day_list = []
        public_dates = [ddp.get_date_data(e.text.split('\n')[0])['date_obj'].isoformat() for e in day_list]

        dates = {
            "scheduled": scheduled_dates,
            "public": public_dates,
        }

        self.quit()
        return dates


class YouTubeUploader(YoutubeWorker):
    """A class for uploading videos on YouTube via Selenium using metadata JSON file
    to extract its title, description etc"""

    def __init__(self, video_path: str, metadata_json_path: Optional[str] = None, thumbnail_path: Optional[str] = None, cookies_path: Optional[str] = None) -> None:
        super().__init__(cookies_path)
        self.video_path = video_path
        self.thumbnail_path = thumbnail_path
        self.metadata_dict = load_metadata(metadata_json_path)
        self.__validate_inputs()

    def __validate_inputs(self):
        if not self.metadata_dict[Constant.VIDEO_TITLE]:
            self.logger.warning("The video title was not found in a metadata file")
            self.metadata_dict[Constant.VIDEO_TITLE] = Path(self.video_path).stem
            self.logger.warning("The video title was set to {}".format(Path(self.video_path).stem))
        if not self.metadata_dict[Constant.VIDEO_DESCRIPTION]:
            self.logger.warning("The video description was not found in a metadata file")

    def upload(self):
        try:
            self.login()
            return self.__upload()
        except Exception as e:
            print(e)
            self.quit()
            raise

    def __write_in_field(self, field, string, select_all=False):
        field.click()
        time.sleep(Constant.USER_WAITING_TIME)
        if select_all:
            for _ in range(150):
                field.send_keys(Keys.BACKSPACE)
                time.sleep(.02)
                field.send_keys(Keys.DELETE)
                time.sleep(.02)
            time.sleep(Constant.USER_WAITING_TIME)
        field.send_keys(string)
        time.sleep(Constant.USER_WAITING_TIME)

    def __upload(self) -> (bool, Optional[str]):
        self.browser.get(Constant.YOUTUBE_URL)
        time.sleep(Constant.USER_WAITING_TIME)
        self.browser.get(Constant.YOUTUBE_UPLOAD_URL)
        time.sleep(Constant.USER_WAITING_TIME)
        absolute_video_path = str(Path.cwd() / self.video_path)
        if self.browser.find(By.XPATH, Constant.INPUT_FILE_VIDEO) is None:
            exit(11)
        self.browser.find(By.XPATH, Constant.INPUT_FILE_VIDEO).send_keys(absolute_video_path)
        self.logger.debug('Attached video {}'.format(self.video_path))

        if self.thumbnail_path is not None:
            absolute_thumbnail_path = str(Path.cwd() / self.thumbnail_path)
            self.browser.find(By.XPATH, Constant.INPUT_FILE_THUMBNAIL).send_keys(absolute_thumbnail_path)
            change_display = "document.getElementById('file-loader').style = 'display: block! important'"
            self.browser.driver.execute_script(change_display)
            self.logger.debug('Attached thumbnail {}'.format(self.thumbnail_path))

        title_field = self.browser.find(By.ID, Constant.TEXTBOX, timeout=10)
        self.__write_in_field(title_field, self.metadata_dict[Constant.VIDEO_TITLE], select_all=True)
        self.logger.debug('The video title was set to \"{}\"'.format(self.metadata_dict[Constant.VIDEO_TITLE]))

        video_description = self.metadata_dict[Constant.VIDEO_DESCRIPTION]
        if video_description:
            description_container = self.browser.find(By.ID, 'description-container')
            description_field = self.browser.find(By.ID, Constant.TEXTBOX, element=description_container)
            self.__write_in_field(description_field, self.metadata_dict[Constant.VIDEO_DESCRIPTION], select_all=True)
            self.logger.debug(
                'The video description was set to \"{}\"'.format(self.metadata_dict[Constant.VIDEO_DESCRIPTION]))

        kids_section = self.browser.find(By.NAME, Constant.NOT_MADE_FOR_KIDS_LABEL)
        self.browser.find(By.ID, Constant.RADIO_LABEL, kids_section).click()
        self.logger.debug('Selected \"{}\"'.format(Constant.NOT_MADE_FOR_KIDS_LABEL))

        if Constant.VIDEO_TAGS in self.metadata_dict:
            # Advanced options
            self.browser.find(By.ID, Constant.MORE_BUTTON_ID).click()
            self.logger.debug('Clicked MORE OPTIONS')

            tags_container = self.browser.find(By.XPATH, Constant.TAGS_INPUT_CONTAINER)
            tags_field = self.browser.find(By.ID, Constant.TAGS_INPUT, element=tags_container)
            self.browser.driver.execute_script("arguments[0].scrollIntoView(true);", tags_container)
            time.sleep(0.5)
            try:
                self.__write_in_field(tags_field, ','.join(self.metadata_dict[Constant.VIDEO_TAGS]))
            except ElementClickInterceptedException as e:
                clear_button = self.browser.find(By.ID, 'clear-button', element=tags_container)
                clear_button.click()
                time.sleep(0.5)
                self.__write_in_field(tags_field, ','.join(self.metadata_dict[Constant.VIDEO_TAGS]))
            self.logger.debug(
                'The tags were set to \"{}\"'.format(self.metadata_dict[Constant.VIDEO_TAGS]))

        self.browser.find(By.ID, Constant.NEXT_BUTTON).click()
        self.logger.debug('Clicked {}'.format(Constant.NEXT_BUTTON))

        self.browser.find(By.ID, Constant.NEXT_BUTTON).click()
        self.logger.debug('Clicked another {}'.format(Constant.NEXT_BUTTON))

        self.browser.find(By.ID, Constant.NEXT_BUTTON).click()
        self.logger.debug('Clicked another {}'.format(Constant.NEXT_BUTTON))

        schedule_main_button = self.browser.find(By.NAME, Constant.SCHEDULE_BUTTON)
        self.browser.find(By.ID, Constant.RADIO_LABEL, schedule_main_button).click()
        self.logger.debug('Clicked schedule')

        # Open date widget
        self.browser.find(By.XPATH, Constant.SCHEDULE_DATE_DROPDOWN).click()
        time.sleep(0.5)
        schedule_date_field = self.browser.driver.switch_to.active_element

        if 'schedule' in self.metadata_dict:
            date = self.metadata_dict['schedule'][0]
            self.__write_in_field(schedule_date_field, date, True)
            schedule_date_field.send_keys(Keys.RETURN)
            self.logger.debug('Set date to ' + date)
            time.sleep(Constant.USER_WAITING_TIME)

            # Open time widget
            self.browser.find(By.XPATH, Constant.SCHEDULE_TIME_DROPDOWN).click()
            time.sleep(Constant.USER_WAITING_TIME)

            t = self.metadata_dict['schedule'][1]
            def time_to_index(time):
                h, m = map(int, time.split(':'))
                return h * 4 + m // 15 + 1
            n = time_to_index(t)
            time_element = self.browser.find(By.XPATH, Constant.SCHEDULE_TIME_ELEMENT + f'[{n}]')
            self.browser.driver.execute_script("arguments[0].scrollIntoView(true);", time_element)
            time.sleep(0.5)
            time_element.click()
            self.logger.debug('Set time to ' + t)


        video_id = self.__get_video_id()

        status_container = self.browser.find(By.XPATH,
                                             Constant.STATUS_CONTAINER)
        while True:
            in_process = status_container.text.find(Constant.UPLOADED) != -1
            if in_process:
                time.sleep(Constant.USER_WAITING_TIME)
            else:
                break

        done_button = self.browser.find(By.ID, Constant.DONE_BUTTON)

        # Catch such error as
        # "File is a duplicate of a video you have already uploaded"
        if done_button.get_attribute('aria-disabled') == 'true':
            error_message = self.browser.find(By.XPATH,
                                              Constant.ERROR_CONTAINER).text
            self.logger.error(error_message)
            return False, None

        done_button.click()
        self.logger.debug("Published the video with video_id = {}".format(video_id))
        time.sleep(Constant.USER_WAITING_TIME)
        self.browser.get(Constant.YOUTUBE_URL)
        self.quit()
        return True, video_id

    def __get_video_id(self) -> Optional[str]:
        video_id = None
        try:
            video_url_container = self.browser.find(By.XPATH, Constant.VIDEO_URL_CONTAINER)
            video_url_element = self.browser.find(By.XPATH, Constant.VIDEO_URL_ELEMENT,
                                                  element=video_url_container)
            video_id = video_url_element.get_attribute(Constant.HREF).split('/')[-1]
        except:
            self.logger.warning(Constant.VIDEO_NOT_FOUND_ERROR)
            pass
        return video_id
