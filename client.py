import socket
import threading
import time

#In this file, all code that we have added has been created or modified by GenAI

def handle_request(hostname, query_code, rr_table, connection):
    # Check RR table for record
    record = rr_table.get_record(hostname, query_code)

    if record:
        # Display RR table
        rr_table.display_table()
    else:
        # If not found, ask the local DNS server
        local_dns_address = ("127.0.0.1", 21000)
        query = serialize({"transaction_id": 1, "name": hostname, "type": query_code})
        connection.send_message(query, local_dns_address)
        response, _ = connection.receive_message()

        # Deserialize and update the cache
        record = deserialize(response)
        if record["result"] != "Record not found":
            rr_table.add_record(record["name"], record["type"], record["result"], record["ttl"], 0)

        # Display RR table
        rr_table.display_table()


def main():
    rr_table = RRTable()
    connection = UDPConnection()

    try:
        while True:
            input_value = input("Enter the hostname (or type 'quit' to exit) ")
            if input_value.lower() == "quit":
                break
            elif len(input_value.split()) == 1: 
                hostname = input_value
                query_code = 'A'
            else:     
                hostname, query_code = input_value.split()
            handle_request(hostname, query_code, rr_table, connection)
            

    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting...")
    finally:
        connection.close()


def serialize(record):
    # Safely access keys with defaults for missing keys
    return f"{record.get('transaction_id', 1)},{record.get('name', '')},{record.get('type', '')},{record.get('result', 'None')},{record.get('ttl', 'None')}"


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

    def close(self):
        self.socket.close()


if __name__ == "__main__":
    main()
