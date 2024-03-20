import time
import argparse
import sqlite3
import schedule


def set_retain_indefinitely_to_1(duration=120):

    connect = sqlite3.connect("/config/frigate.db")
    cursor = connect.cursor()

    # cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    # print(cursor.fetchall())

    # cursor.execute("SELECT * FROM event WHERE retain_indefinitely=True;")
    # cursor.fetchall()
    # names = list(map(lambda x: x[0], cursor.description))
    # print(names)

    # Set star in event (retain_indefinitely = 1)
    cursor.execute(
        f"UPDATE event SET retain_indefinitely = 1 WHERE end_time - start_time > {duration};")
    connect.commit()

    # cursor.execute("")
    # print(cursor.fetchall())

    connect.close()


def scheduler(duration):
    schedule.every(1).minutes.do(set_retain_indefinitely_to_1, duration)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('duration')
    args = parser.parse_args()
    duration = int(args.duration)
    # print(duration)

    scheduler(duration)
