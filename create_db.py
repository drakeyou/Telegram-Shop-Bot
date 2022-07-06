import pymysql.cursors
from config import HOST, PORT, USER, PASSWORD, DB_NAME

users_scheme = "CREATE TABLE `users`(" \
               "username text," \
               "id int AUTO_INCREMENT NOT NULL PRIMARY KEY," \
               "user_id BIGINT NOT NULL UNIQUE KEY, " \
               "purchases BIGINT NOT NULL" \
               ");"

products_scheme = "CREATE TABLE `products`(" \
                  "id int NOT NULL PRIMARY KEY DEFAULT 1," \
                  "category text NOT NULL," \
                  "name text NOT NULL," \
                  "description text NOT NULL," \
                  "price BIGINT NOT NULL," \
                  "amount BIGINT NOT NULL," \
                  "content text NOT NULL" \
                  ");"

purchases_scheme = "CREATE TABLE `purchases`(" \
                   "user_id BIGINT NOT NULL," \
                   "bill_id BIGINT NOT NULL PRIMARY KEY," \
                   "content text NOT NULL," \
                   "product_category text NOT NULL," \
                   "product_name text NOT NULL," \
                   "paid bool NOT NULL" \
                   ");"


def connect(db_name=None):
    try:
        connection_ = pymysql.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )

        print("Connection Successful")
        return connection_
    except Exception as err:
        print("Connection was failed")
        print(err)


connection = connect()
cursor = connection.cursor()
cursor.execute(f"CREATE DATABASE {DB_NAME}")
cursor.close()

connection = connect(DB_NAME)
cursor = connection.cursor()

cursor.execute(users_scheme)
cursor.execute(products_scheme)
cursor.execute(purchases_scheme)

cursor.close()
