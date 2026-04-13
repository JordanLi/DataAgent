import asyncio
import aiomysql

async def test_conn():
    try:
        conn = await aiomysql.connect(host='127.0.0.1', port=3306, user='root', password='', db='ecommerce')
        print("Success")
        conn.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(test_conn())
