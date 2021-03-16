from youtube_uploader_selenium import YouTubeScheduler
import sys
cookies_path = None
if len(sys.argv) > 1:
  cookies_path = sys.argv[1]

uploader = YouTubeScheduler(cookies_path)
uploader.get_schedule()
