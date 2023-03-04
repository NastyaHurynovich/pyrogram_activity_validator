import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyrogram
from telethon.errors import FloodWaitError

CREDENTIALS = []
OUTPUT_FILE = "valid.txt"
CLIENTS_POOL = []


def setting_account():
    # При старте на каждый из аккаунтов в консоли будет запрос на номер телефона, на который придёт код (его нужно
    # тоже ввести). Для создания нескольких клиентов Вам нужно будет ввести уникальные номера телефонов
    account = []
    api_id = int(input("Введите данные аккаунта:\napi_id: "))
    account.append(api_id)
    api_hash = str(input("api_hash: "))
    account.append(api_hash)
    CREDENTIALS.append(account)
    client = pyrogram.Client(f"anon.session_{api_id}", api_hash=api_hash, api_id=api_id)
    CLIENTS_POOL.append(client)
    client.start()
    # client.disconnect()
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
        pool_client.get_chat_history(chat_id=link, limit=criteria, offset_date=datetime.now(tz=timezone.utc)))
    last_message = messages[-1]
    return last_message.date.timestamp() >= (datetime.now(tz=timezone.utc) - timedelta(hours=period)).timestamp()


def check_active_chat(links, pool_number, criteria, period):
    flood_errors_links = []
    links_handled_per_client = 0
    is_flood = False
    print(f"Берем из пула клиент с номером {pool_number + 1}")
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
            print(f"Берем из пула клиент с номером {pool_number + 1}")
            curr_client = CLIENTS_POOL[pool_number]
        try:
            is_valid = check_criteria(curr_client, link, criteria, period)
            print(link, ": ", is_valid)
            if is_valid:
                write_file(OUTPUT_FILE, link)
            links_handled_per_client += 1
        except FloodWaitError as flood_error:
            flood_errors_links.append(link)
            is_flood = True
            print("Flood error -> change client. Details: ", flood_error)
        except Exception as e:
            links_handled_per_client += 1
            print(f"Channel {link} is invalid or not exists. Details: ", e)
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
