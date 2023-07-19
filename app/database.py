import psycopg2

user = "lightwing"
password = "canton0520"
host = "localhost"
database = "beingRich"
port = 5432


def connect_to_db():
    cnx = psycopg2.connect(
        user=user,
        password=password,
        host=host,
        database=database,
        port=port)
    return cnx
