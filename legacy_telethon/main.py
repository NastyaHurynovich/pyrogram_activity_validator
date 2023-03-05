import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError

CREDENTIALS = []
OUTPUT_FILE = "valid.txt"
CLIENTS_POOL = []

active_pool = -1


def setting_account():
    # При старте на каждый из аккаунтов в консоли будет запрос на номер телефона, на который придёт код (его нужно
    # тоже ввести). Для создания нескольких клиентов Вам нужно будет ввести уникальные номера телефонов
    account = []
    api_id = int(input("Введите данные аккаунта:\napi_id: "))
    account.append(api_id)
    api_hash = str(input("api_hash: "))
    account.append(api_hash)
    CREDENTIALS.append(account)
    client = TelegramClient(f"anon.session_{api_id}", api_id, api_hash)
    CLIENTS_POOL.append(client)
    client.start()
    client.disconnect()
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


def get_messages_count(pool_client, link, criteria, period):
    generator = pool_client.iter_messages(entity=link, limit=criteria,
                                          offset_date=datetime.now(tz=timezone.utc) - timedelta(hours=period),
                                          reverse=True)
    return len(list(generator))


def get_client_from_pool(pool_number):
    global active_pool
    if CLIENTS_POOL[active_pool].is_connected():
        CLIENTS_POOL[active_pool].disconnect()
    active_pool = pool_number
    CLIENTS_POOL[pool_number].start()
    return CLIENTS_POOL[pool_number]


def check_active_chat(links, pool_number, criteria, period):
    flood_errors_links = []
    links_handled_per_client = 0
    is_flood = False
    curr_client = get_client_from_pool(pool_number)
    for link in links:
        # Меняем аккаунт каждые 20 каналов из списка или когда встречаем бан за Flood, а также если больше одного
        # аккаунта
        if links_handled_per_client == 20 or is_flood and len(CLIENTS_POOL) > 1:
            links_handled_per_client = 0
            is_flood = False
            if len(CLIENTS_POOL) - 1 == active_pool:
                pool_number = 0
            else:
                pool_number += 1
            curr_client = get_client_from_pool(pool_number)
        try:
            generator_list_count = get_messages_count(curr_client, link, criteria, period)
            print(link, ": ", generator_list_count)
            if generator_list_count >= criteria:
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
        error_links = check_active_chat(links_for_processing, active_pool + 1, count_criteria, period)
        if len(error_links) == 0:
            break
        links_for_processing = error_links
    input("Программа завершена введите Enter для завершения: ")


if __name__ == '__main__':
    main()
