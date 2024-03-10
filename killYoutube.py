import time
import datetime
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog = 'killYoutube',
                    description = 'Kills youtube, pass time as parameter',
                    epilog = 'Text at the bottom of help')
    parser.add_argument('--hour', type=int, nargs='+', help='hour',default=0)
    parser.add_argument('--minute', type=int, nargs='+', help='minute',default=0)
    args = parser.parse_args()
    hours_wait = int(args.hour[0])
    minutes_wait = int(args.minute[0])

    hour_minutes = hours_wait*60
    total_minutes = minutes_wait + hour_minutes
    total_seconds = total_minutes*60+3

    print(f"Killing Firefox in {total_seconds} seconds")
    time.sleep(int(total_seconds))
    os.system("killall firefox")
