import os
import psycopg2
import pika
from pika.exceptions import StreamLostError, AMQPConnectionError
import time
import select
import logging
from datetime import timedelta
from multiprocessing import Process

def get_logger(name):
    log_lvl = os.environ.get("LOG_LVL", "debug")
    if log_lvl == 'info':
        log_lvl = logging.INFO
    elif log_lvl == 'warning':
        log_lvl = logging.WARNING
    else:
        log_lvl = logging.DEBUG
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(log_lvl)
    logger.info(f"Logger started on log level: {log_lvl}")
    return logger

class PsqlConn():

    def __init__(self, channel, *args, **kwargs):
        self._psql_uri = os.environ.get("POSTGRESQL_URI")
        self._channel = channel
        self._logger = get_logger(f"PSQL - {self._channel}")
        self._connect()

    def _connect(self):
        self._conn = psycopg2.connect(self._psql_uri)
        self._conn.autocommit = True
        logging.info(f"Succesfully connected to PostgresDB.")

    def listen(self):
        seconds_passed = 0
        while True:
            if self._conn.closed:
                self._connect()
            cur = self._conn.cursor()
            try:
                cur.execute("LISTEN {}".format(self._channel))
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                self._logger.Error(f"{e}Trying to reconnect...")
            else:
                if select.select([self._conn],[],[],5) == ([],[],[]):
                    seconds_passed += 5
                    self._logger.debug(f"{timedelta(seconds=seconds_passed)} since last notification.")
                else:
                    seconds_passed = 0
                    self._conn.poll()
                    self._conn.commit()
                    while self._conn.notifies:
                        yield self._conn.notifies.pop()
                cur.close()

class AmqpConn():

    def __init__(self, routing_key, *args, **kwargs):
        uri = os.environ.get("AMQP_URI")
        self._amqp_uri = pika.connection.URLParameters(uri)
        self._exchange = uri.split("/")[-1]
        self._channel = None
        self._routing_key = routing_key
        self._logger = get_logger(f"AMQP - {self._routing_key}")
        self._connect()
        try:
            self._max_retry = int(os.environ.get("MAX_RETRY", 10))
        except TypeError:
            self._logger.error(f"{os.environ.get('MAX_RETRY')} is not an int value. max_retry set to 10 by default.")
            self._max_retry = 10

    def _connect(self):
        self._conn = pika.BlockingConnection(self._amqp_uri)  
        self._channel = self._conn.channel()
        self._logger.info(f"Connected to rmq with routing key '{self._routing_key}'")

    def _close(self):
        self._conn.close()

    def write(self, msg):
        self._logger.debug(f"Channel {self._routing_key}: '{msg.payload}'")
        message = msg.payload
        if self._conn and self._conn.is_open:
            try:
                self._channel.basic_publish(routing_key=self._routing_key, exchange=self._exchange, body=message)
            except (ConnectionResetError, StreamLostError) as e: 
                self._logger.warning(f"Lost connection due to {e} for routing_key {self._routing_key}.\n Reconnecting...")
                retry_count = 0
                while retry_count<=10:
                    time.sleep(5)
                    try:
                        self._connect()
                        break
                    except AMQPConnectionError:
                        self._logger.info(f"Retry: {retry_count}/{self._max_retry}")
                        retry_count+=1
                self.write(msg)
        else:
            self._logger.warning(f"Lost connection for routing_key {self._routing_key}. Reconnecting...")
            self._connect()
            self.write(msg)

def spawn_lister(psql_chann, rmq_key):
    psql = PsqlConn(psql_chann)
    rmq = AmqpConn(rmq_key)
    for msg in psql.listen():
        rmq.write(msg)

def main():
    channels = os.environ.get("BRIDGE_CHANNELS").split(",")

    if not channels:
        raise ValueError("No BRIDGE_CHANNELS defined in env, please set Channel Mapping!")
    processes = []
    for conn in channels:
        psql_chann, rmq_key = conn.split(":")
        processes.append(Process(target=spawn_lister, args=(psql_chann, rmq_key)))
    [p.start() for p in processes]
    [p.join() for p in processes]

if __name__ == "__main__":
    main()

