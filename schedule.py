from youtube_uploader_selenium import YouTubeScheduler
import sys, json

time_zone = sys.argv[1]

cookies_path = None
if len(sys.argv) > 2:
  cookies_path = sys.argv[2]

uploader = YouTubeScheduler(time_zone, cookies_path=cookies_path)
print(json.dumps(uploader.get_schedule()))
