import socket
import threading
import time

#In this file, all code that we have added has been created or modified by GenAI

def listen(rr_table, connection):
    try:
        while True:
            data, client_address = connection.receive_message()

            query = deserialize(data)
            name, query_type = query["name"], query["type"]

            record = rr_table.get_record(name, query_type)

            if record:
                response = serialize(record)
                connection.send_message(response, client_address)
            else:
                authoritative_dns_address = ("127.0.0.1", 22000)
                connection.send_message(data, authoritative_dns_address)
                authoritative_response, _ = connection.receive_message()
                authoritative_record = deserialize(authoritative_response)

                if authoritative_record["result"] != "Record not found":
                    rr_table.add_record(authoritative_record["name"], authoritative_record["type"],
                                        authoritative_record["result"], authoritative_record["ttl"], 0)
                connection.send_message(authoritative_response, client_address)

            rr_table.display_table()
    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting...")
    finally:
        connection.close()


def main():
    rr_table = RRTable()
    connection = UDPConnection()

    rr_table.add_record("www.csusm.edu", "A", "144.37.5.45", None, 1)
    rr_table.add_record("my.csusm.edu", "A", "144.37.5.150", None, 1)
    rr_table.add_record("amazone.com", "NS", "dns.amazone.com", None, 1)
    rr_table.add_record("dns.amazone.com", "A", "127.0.0.1", None, 1)

    local_dns_address = ("127.0.0.1", 21000)
    connection.bind(local_dns_address)
    listen(rr_table, connection)


def serialize(record):
    # Safely access keys with defaults for missing keys
    return f"{record.get('transaction_id', 1)},{record.get('name', '')},{record.get('type', '')},{record.get('result', 'None')},{60},{record.get('static', 0)}"


def deserialize(data):
    parts = data.split(",")
    return {
        "transaction_id": int(parts[0]),
        "name": parts[1],
        "type": parts[2],
        "result": parts[3],
        "ttl": int(parts[4]) if parts[4] != "None" else None,
    }


class RRTable:
    def __init__(self):
        self.records = []
        self.record_number = 0 
        # Start the background thread
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._decrement_ttl, daemon=True)
        self.thread.start()

    def add_record(self, name, record_type, result, ttl, is_static):
        with self.lock:
            self.records.append({
                "name": name,
                "type": record_type,
                "result": result,
                "ttl": ttl,
                "static": is_static
            })
            self.record_number += 1        

    def get_record(self, name, record_type):
        with self.lock:
            for record in self.records:
                if record["name"] == name and record["type"] == record_type:
                    return record
            return None

    def display_table(self):
        with self.lock:
            print("record_no,name,type,result,ttl,static")
            for i, record in enumerate(self.records):
                print(f"{i},{record['name']},{record['type']},{record['result']},{record['ttl']},{record['static']}")
    
    def _decrement_ttl(self):
        while True:
            with self.lock:
                # Decrement ttl
                for record in self.records: 
                    if record["ttl"] is not None and record["ttl"] > 0: 
                        record["ttl"] -= 1
                    else:
                        self.__remove_expired_records()
            time.sleep(1)
    
    def __remove_expired_records(self):
        # This method is only called within a locked context
        # Remove expired records
        for record in self.records:
            if record['static'] == 0 and record['ttl'] is not None:
                if record['ttl'] <= 0:
                    self.records.remove(record)
        # Update record numbers
        self.record_number = len(self.records)

class UDPConnection:
    def __init__(self, timeout=1):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)

    def send_message(self, message, address):
        self.socket.sendto(message.encode(), address)

    def receive_message(self):
        while True:
            try:
                data, address = self.socket.recvfrom(4096)
                return data.decode(), address
            except socket.timeout:
                continue

    def bind(self, address):
        self.socket.bind(address)

    def close(self):
        self.socket.close()


if __name__ == "__main__":
    main()
