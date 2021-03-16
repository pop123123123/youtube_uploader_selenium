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

        LIST_XPATH = '/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[3]/ytcp-content-section/ytcp-video-section/ytcp-video-section-content/div'
        TO_HOVER_CSS = 'ytcp-video-row.style-scope span.ytcp-video-row'
        HOVER_CSS = 'ytcp-paper-tooltip-body.ytcp-paper-tooltip-placeholder > p:nth-child(2) > yt-formatted-string:nth-child(1)'
        DAY_CSS = 'ytcp-video-row.style-scope div.ytcp-video-row.column-sorted'
        TIME_REGEX = r"\d\d:\d\d"

        videoList = self.browser.find(By.XPATH, LIST_XPATH)
        hover_list = self.browser.find_all(By.CSS_SELECTOR, TO_HOVER_CSS, videoList)
        day_list = self.browser.find_all(By.CSS_SELECTOR, DAY_CSS, videoList)

        scheduled_texts = []
        for hoverElement, dayElement in zip(hover_list, day_list):
            actions = ActionChains(self.browser.driver)
            actions.move_to_element(hoverElement)
            actions.perform()
            time.sleep(Constant.USER_WAITING_TIME)

            hover = self.browser.find(By.CSS_SELECTOR, HOVER_CSS)
            t = re.search(TIME_REGEX, hover.text).group(0)

            d = dayElement.text.split('\n')[0]
            scheduled_texts.append((d, t))

        suffix = '/videos/upload?filter=[{"name"%3A"VISIBILITY"%2C"value"%3A["PUBLIC"]}]&sort={"columnType"%3A"date"%2C"sortOrder"%3A"DESCENDING"}'
        self.browser.get(base_url + suffix)
        time.sleep(Constant.USER_WAITING_TIME)


        videoList = self.browser.find(By.XPATH, LIST_XPATH)
        day_list = self.browser.find_all(By.CSS_SELECTOR, DAY_CSS, videoList)
        public_texts = [e.text.split('\n')[0] for e in day_list]

        print(*scheduled_texts, 'PUBLIC', *public_texts, sep='\n')

        self.quit()


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
            field.send_keys(Keys.COMMAND + 'a')
            time.sleep(Constant.USER_WAITING_TIME)
        field.send_keys(string)

    def __upload(self) -> (bool, Optional[str]):
        self.browser.get(Constant.YOUTUBE_URL)
        time.sleep(Constant.USER_WAITING_TIME)
        self.browser.get(Constant.YOUTUBE_UPLOAD_URL)
        time.sleep(Constant.USER_WAITING_TIME)
        absolute_video_path = str(Path.cwd() / self.video_path)
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
            description_container = self.browser.find(By.XPATH,
                                                      Constant.DESCRIPTION_CONTAINER)
            description_field = self.browser.find(By.ID, Constant.TEXTBOX, element=description_container)
            self.__write_in_field(description_field, self.metadata_dict[Constant.VIDEO_DESCRIPTION])
            self.logger.debug(
                'The video description was set to \"{}\"'.format(self.metadata_dict[Constant.VIDEO_DESCRIPTION]))

        kids_section = self.browser.find(By.NAME, Constant.NOT_MADE_FOR_KIDS_LABEL)
        self.browser.find(By.ID, Constant.RADIO_LABEL, kids_section).click()
        self.logger.debug('Selected \"{}\"'.format(Constant.NOT_MADE_FOR_KIDS_LABEL))

        # Advanced options
        self.browser.find(By.XPATH, Constant.MORE_BUTTON).click()
        self.logger.debug('Clicked MORE OPTIONS')

        tags_container = self.browser.find(By.XPATH,
                                                    Constant.TAGS_INPUT_CONTAINER)
        tags_field = self.browser.find(By.ID, Constant.TAGS_INPUT, element=tags_container)
        self.__write_in_field(tags_field, ','.join(self.metadata_dict[Constant.VIDEO_TAGS]))
        self.logger.debug(
            'The tags were set to \"{}\"'.format(self.metadata_dict[Constant.VIDEO_TAGS]))

        self.browser.find(By.ID, Constant.NEXT_BUTTON).click()
        self.logger.debug('Clicked {}'.format(Constant.NEXT_BUTTON))

        self.browser.find(By.ID, Constant.NEXT_BUTTON).click()
        self.logger.debug('Clicked another {}'.format(Constant.NEXT_BUTTON))

        public_main_button = self.browser.find(By.NAME, Constant.PUBLIC_BUTTON)
        self.browser.find(By.ID, Constant.RADIO_LABEL, public_main_button).click()
        self.logger.debug('Made the video {}'.format(Constant.PUBLIC_BUTTON))

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
