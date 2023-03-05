import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from io import StringIO
import sys
import tgcrypto
import pyrogram
from pyrogram.errors import FloodWait

OUTPUT_FILE = "valid.txt"
CLIENTS_POOL = []

api_id = "18028667"
api_hash = "9020cc8f73467f944b859c963519e5c5"


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


def setting_account():
    try:
        phone_number = input("Введите номер телефона: ")
        print("Введите код доступа: ")
        with Capturing() as output:
            client = pyrogram.Client(f"anon.session_{datetime.now(tz=timezone.utc).timestamp()}", api_hash=api_hash,
                                     api_id=api_id, phone_number=phone_number)
            client.start()
            CLIENTS_POOL.append(client)
    except FloodWait:
        print("Этот аккаунт забанен из-за флуда")
    except Exception as e:
        print("Ошибка при создании аккаунта: ", e)
    answer = input("Хотите ввести ещё один аккаунт? Y/n ")
    if answer.lower() == "y":
        setting_account()


def request_int(string):
    return int(input(string))


def read_file(path):
    with open(path, "r") as f:
        links = set(f.readlines())
    return links


def delete_duplicates(links):
    no_duplicate_links = set()
    for link in links:
        cleaned_link = link.replace("https://t.me/", "").replace("@", "").replace("\n", "")
        no_duplicate_links.add(cleaned_link)
    return no_duplicate_links


def check_criteria(pool_client, link, criteria, period):
    messages = list(
        pool_client.get_chat_history(chat_id=link, limit=(1 if criteria == 0 else criteria),
                                     offset_date=datetime.now(tz=timezone.utc)))
    last_message = messages[-1]
    return (last_message.date.timestamp() >= (datetime.now(tz=timezone.utc) - timedelta(hours=period)).timestamp()) or \
           (criteria == 0 and period == 0)


def check_active_chat(links, pool_number, criteria, period):
    flood_errors_links = []
    links_handled_per_client = 0
    is_flood = False
    curr_client = CLIENTS_POOL[pool_number]
    for link in links:
        # Меняем аккаунт каждые 20 каналов из списка или когда встречаем бан за Flood, а также если больше одного
        # аккаунта
        if links_handled_per_client == 20 or is_flood and len(CLIENTS_POOL) > 1:
            links_handled_per_client = 0
            is_flood = False
            if len(CLIENTS_POOL) - 1 == pool_number:
                pool_number = 0
            else:
                pool_number += 1
            curr_client = CLIENTS_POOL[pool_number]
        try:
            is_valid = check_criteria(curr_client, link, criteria, period)
            print("@" + link, ": ", "валидная ссылка" if is_valid else "невалидная ссылка")
            if is_valid:
                write_file(OUTPUT_FILE, link)
            links_handled_per_client += 1
        except FloodWait:
            flood_errors_links.append(link)
            is_flood = True
        except Exception:
            links_handled_per_client += 1
            print("@" + link, ": невалидная ссылка")
        # Симулируем поведение человека, ждем 10 секунд перед обработкой следующей ссылки
        time.sleep(10)

    return flood_errors_links


def write_file(file, link):
    with open(file, "a") as f:
        f.write(f"@{link}\n")


def main():
    try:
        os.remove(OUTPUT_FILE)
    except OSError:
        pass
    try:
        for p in list(Path(".").glob("anon*")):
            p.unlink()
    except Exception:
        pass
    setting_account()
    if len(CLIENTS_POOL) == 0:
        print("Аккаунт для работы не создан")
        sys.exit()
    count_criteria = request_int("Введите количество сообщений для проверки 'активности' канала? ")
    period = request_int("Введите количество часов, за которые просматриваются сообщения и проверятся 'активность' "
                         "каналов? ")
    path = input("Введите путь к файлу с ссылками: ")
    # Ожидаемый путь к файлу должен быть в таком формате: path = "C:/user/links.txt"
    links_for_processing = delete_duplicates(read_file(path))
    while True:
        error_links = check_active_chat(links_for_processing, 0, count_criteria, period)
        if len(error_links) == 0:
            break
        links_for_processing = error_links
    for client in CLIENTS_POOL:
        client.stop()
    input("Программа завершена введите Enter для завершения: ")


if __name__ == '__main__':
    main()
