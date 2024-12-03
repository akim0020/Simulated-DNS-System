import socket

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
                response = serialize({"transaction_id": query["transaction_id"], "name": name, "type": query_type,
                                      "result": "Record not found", "ttl": None})
                connection.send_message(response, client_address)

            rr_table.display_table()
    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting...")
    finally:
        connection.close()


def main():
    rr_table = RRTable()
    connection = UDPConnection()

    rr_table.add_record("shop.amazone.com", "A", "3.33.147.88", None, 1)
    rr_table.add_record("cloud.amazone.com", "A", "15.197.140.28", None, 1)
    
    amazone_dns_address = ("127.0.0.1", 22000)
    connection.bind(amazone_dns_address)
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

    def add_record(self, name, record_type, result, ttl, is_static):
        self.records.append({
            "name": name,
            "type": record_type,
            "result": result,
            "ttl": ttl,
            "static": is_static
        })

    def get_record(self, name, record_type):
        for record in self.records:
            if record["name"] == name and record["type"] == record_type:
                return record
        return None

    def display_table(self):
        print("record_no,name,type,result,ttl,static")
        for i, record in enumerate(self.records):
            print(f"{i},{record['name']},{record['type']},{record['result']},{record['ttl']},{record['static']}")


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
