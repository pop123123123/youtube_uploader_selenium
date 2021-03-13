"""This module implements uploading videos on YouTube via Selenium using metadata JSON file
    to extract its title, description etc."""

from typing import DefaultDict, Optional
from selenium_firefox.firefox import Firefox, By, Keys
from collections import defaultdict
import json
import time
from .Constant import *
from pathlib import Path
import logging

logging.basicConfig()


def load_metadata(metadata_json_path: Optional[str] = None) -> DefaultDict[str, str]:
    if metadata_json_path is None:
        return defaultdict(str)
    with open(metadata_json_path) as metadata_json_file:
        return defaultdict(str, json.load(metadata_json_file))


class YouTubeUploader:
    """A class for uploading videos on YouTube via Selenium using metadata JSON file
    to extract its title, description etc"""

    def __init__(self, video_path: str, metadata_json_path: Optional[str] = None, thumbnail_path: Optional[str] = None) -> None:
        self.video_path = video_path
        self.thumbnail_path = thumbnail_path
        self.metadata_dict = load_metadata(metadata_json_path)
        current_working_dir = str(Path.cwd())
        self.browser = Firefox(current_working_dir, current_working_dir)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
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
            self.__login()
            return self.__upload()
        except Exception as e:
            print(e)
            self.__quit()
            raise

    def __login(self):
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

        # public_main_button = self.browser.find(By.NAME, Constant.PUBLIC_BUTTON)
        # self.browser.find(By.ID, Constant.RADIO_LABEL, public_main_button).click()
        # self.logger.debug('Made the video {}'.format(Constant.PUBLIC_BUTTON))
        schedule_main_button = self.browser.find(By.NAME, Constant.SCHEDULE_BUTTON)
        self.browser.find(By.ID, Constant.RADIO_LABEL, schedule_main_button).click()
        self.logger.debug('Clicked schedule')

        # Opoen date widget
        self.browser.find(By.XPATH, Constant.SCHEDULE_DATE_DROPDOWN).click()
        schedule_date_field = self.browser.find(By.XPATH, Constant.SCHEDULE_DATE_INPUT)
        date = 'Mar 10, 2021'
        self.__write_in_field(schedule_date_field, date, True)
        schedule_date_field.send_keys(Keys.RETURN)
        self.logger.debug('Set date to ' + date)
        time.sleep(Constant.USER_WAITING_TIME)

        # Open time widget
        self.browser.find(By.XPATH, Constant.SCHEDULE_TIME_DROPDOWN).click()
        time.sleep(Constant.USER_WAITING_TIME)

        t = '15:15'
        def time_to_index(time):
            h, m = map(int, time.split(':'))
            return h * 4 + m // 15 + 1
        n = time_to_index(t)
        # time_list = self.browser.find(By.XPATH, Constant.SCHEDULE_TIME_LIST)
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
        self.__quit()
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

    def __quit(self):
        self.browser.driver.quit()
