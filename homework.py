import logging
import os
import time
from datetime import datetime, timedelta
from http import HTTPStatus
from pprint import pprint

import requests
import telegram
from dotenv import load_dotenv
from requests import RequestException


load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_HW_PR')
TELEGRAM_TOKEN = os.getenv('TOKEN_HW')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
TIME_RANGE = {
    'from_date': int(
        (datetime.today() - timedelta(seconds=RETRY_PERIOD)).timestamp()
    )
}

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger()
formatter = logging.Formatter(
    "%(asctime)s, %(name)s, %(levelname)s, %(message)s"
)
handler = logging.FileHandler('homework_bot.log', mode='a')

handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def check_tokens():
    """Check tokens."""
    if not PRACTICUM_TOKEN:
        logger.critical('No PRACTICUM_TOKEN')
        raise ImportError('No token PRACTICUM_TOKEN')

    if not TELEGRAM_TOKEN:
        logger.critical('No TELEGRAM_TOKEN')
        raise ImportError('No token TELEGRAM_TOKEN')

    if not TELEGRAM_CHAT_ID:
        logger.critical('No TELEGRAM_CHAT_ID')
        raise ImportError('No token TELEGRAM_CHAT_ID')


def send_message(bot, message):
    """Send message."""
    try:
        logger.debug(f'Sending message')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Send message: {message}')
    except telegram.TelegramError:
        logger.error(f'Do not send message: {message}')


def get_api_answer(timestamp):
    """Get response, heck status == 200 and return json."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
    except RequestException as err:
        raise IOError(err)

    if response.status_code != HTTPStatus.OK:
        raise RequestException

    return response.json()


def check_response(homeworks):
    """Check keys in response."""
    if isinstance(homeworks, dict):
        if 'homeworks' not in homeworks.keys():
            raise KeyError('No homeworks in homeworks')
        if 'current_date' not in homeworks.keys():
            raise KeyError('No current_date in homeworks')

        homeworks = homeworks['homeworks']
        if isinstance(homeworks, list):
            return homeworks

    raise TypeError('Invalid type homeworks')


def parse_status(homework):
    """Get status homework and return message for user."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if 'homework_name' not in homework.keys():
        raise KeyError('homework_name not in homework')
    if 'status' not in homework.keys():
        raise KeyError('homework_status not in homework')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('homework_status not in HOMEWORK_VERDICTS')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Bot start."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    last_status = None

    while True:
        try:
            response = get_api_answer(TIME_RANGE)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_status:
                    send_message(bot, message)
                    last_status = message
            else:
                logger.debug('No changes status homework')

        except Exception as error:
            send_message(bot, f'Сбой в работе программы: {error}')
            raise Exception(error)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
