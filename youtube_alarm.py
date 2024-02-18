from selenium.webdriver.common.by import By
from selenium import webdriver
import time
import datetime
import argparse
import os



def main():

    #Close firefox
    os.system("killall firefox")

    #open firefox
    api = webdriver.Firefox()
    
    #Set adblock
    try :
        api.install_addon("./addons/uBlock0@raymondhill.net.xpi")
        api.install_addon("./addons/YouTube_NonStop@lawfx.xpi")
    except Exception as e:
        print("No adblock or no Youtube Non Stop")

    #Get page
    api.get("https://www.youtube.com/playlist?list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7") #
    time.sleep(.9)


    #Accept cookies
    try :
        buttons = api.find_elements(By.XPATH, "//button")
        texts = [butt.text for butt in buttons]
        accept_button = buttons[texts.index('ACCEPT ALL')]
        accept_button.click()
        time.sleep(.9)
    except Exception as e :
        print("No accept cookies page ?")

    

    #Now on youtube page
    # Finding shuffle / play button...
    try :
        elem = api.find_element(By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse/ytd-playlist-header-renderer/div/div[2]/div[1]/div/div[2]/ytd-button-renderer[2]/yt-button-shape/a/yt-touch-feedback-shape/div/div[2]")
        elem.click()
    except Exception as e :
        print("Error :\n", e)
        print("Launching playlist in order")
        api.get("https://www.youtube.com/watch?v=fQDEUU1lyZQ&list=PL8FvEtnALTbRjuG8qcoMqstD5MDwV00f7")
        time.sleep(.3)

    # Finding repeat and shuffle button and clicking
    try :
        #repeat
        time.sleep(3)
        elem = api.find_element(By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[2]/div/ytd-playlist-panel-renderer/div/div[1]/div/div[2]/div[1]/div[1]/ytd-menu-renderer/div[1]/ytd-playlist-loop-button-renderer/div/ytd-button-renderer/yt-button-shape/button/yt-touch-feedback-shape/div/div[2]")
        elem.click()
        #shuffle
        time.sleep(3)
        #elem = api.find_element(By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[2]/div/ytd-playlist-panel-renderer/div/div[1]/div/div[2]/div[1]/div[1]/ytd-menu-renderer/div[1]/ytd-toggle-button-renderer/yt-button-shape/button/yt-touch-feedback-shape/div/div[2]")
        #elem.click()


    except Exception as e : 
        print("Didn't find repeat button :", e)







if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog = 'YoutubeAlarm',
                    description = 'Launches youtube with an alarm, pass time as parameter',
                    epilog = 'Text at the bottom of help')
    parser.add_argument('--hour', type=int, nargs='+', help='hour')
    parser.add_argument('--minute', type=int, nargs='+', help='minute')
    args = parser.parse_args()
    hour_alarm = int(args.hour[0])
    minute_alarm = int(args.minute[0])
    
    now = datetime.datetime.now()
    wake_up_time =datetime.datetime(now.year,
                                    now.month,
                                    now.day,
                                    hour_alarm,
                                    minute_alarm)
    has_launched = False
    n_l = 0
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",]
    while (now.hour != hour_alarm and now.minute != args.minute) or has_launched==False:
        if n_l%5==0:
            td = wake_up_time-now
            l_hours = int(td.seconds/3600)
            l_minutes = int(td.seconds/60)-l_hours*60
            print("{}, {} {} {}. ".format(days[now.weekday()], now.day, months[now.month], now.year), 
                  "\n\tAlarm in {} hours and {} minutes\n\n".format(l_hours, l_minutes))
        if now.hour == hour_alarm and now.minute == minute_alarm :
            main()
            print("Alarm should have launched! ")
            has_launched=True
            break
        time.sleep(15)
        now = datetime.datetime.now()
        wake_up_time =datetime.datetime(now.year,
                                        now.month,
                                        now.day,
                                        hour_alarm,
                                        minute_alarm)
        n_l+=1

