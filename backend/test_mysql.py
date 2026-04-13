import asyncio
import aiomysql

async def test():
    try:
        pool = await aiomysql.create_pool(
            host='127.0.0.1', 
            port=3306, 
            user='root', 
            password='root', 
            db='ecommerce',
            autocommit=True
        )
        print('Success!')
        pool.close()
        await pool.wait_closed()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
